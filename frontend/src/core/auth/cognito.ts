/**
 * Sesión con Amazon Cognito, sin SDK: la API de Cognito es un POST JSON.
 *
 * Solo se activa si la app se compila con VITE_COGNITO_REGION y
 * VITE_COGNITO_CLIENT_ID (salidas RegionCognito e IdClienteApp del stack).
 * En el modo local no hay usuarios y la API no pide token.
 */

const REGION = import.meta.env.VITE_COGNITO_REGION as string | undefined;
const CLIENT_ID = import.meta.env.VITE_COGNITO_CLIENT_ID as string | undefined;

export const AUTENTICACION_ACTIVA = Boolean(REGION && CLIENT_ID);
export const GRUPO_ADMINISTRADORES = "administradores";

const CLAVE_SESION = "localizador.sesion";
// Se renueva un minuto antes de que caduque, para no mandar un token que
// expire en el camino.
const MARGEN_RENOVACION_MS = 60_000;

type Tokens = { idToken: string; refreshToken: string; expiraEn: number };

export type Usuario = { email: string; grupos: string[] };

export type ResultadoInicio =
  | { tipo: "listo" }
  | { tipo: "nueva_contrasena"; sesion: string; correo: string };

export class ErrorSesion extends Error {
  constructor(message: string) {
    super(message);
    this.name = "ErrorSesion";
  }
}

// --- Almacenamiento -------------------------------------------------------------------
// localStorage para que la sesión sirva en todas las pestañas (el mapa se abre a
// menudo en otra). El token de renovación caduca a los 7 días y se revoca al salir.

function leerTokens(): Tokens | null {
  try {
    const crudo = localStorage.getItem(CLAVE_SESION);
    return crudo ? (JSON.parse(crudo) as Tokens) : null;
  } catch {
    return null;
  }
}

function guardarTokens(tokens: Tokens | null) {
  try {
    if (tokens) localStorage.setItem(CLAVE_SESION, JSON.stringify(tokens));
    else localStorage.removeItem(CLAVE_SESION);
  } catch {
    /* sin almacenamiento: la sesión dura lo que la pestaña */
  }
  memoria = tokens;
  avisar();
}

let memoria: Tokens | null = leerTokens();
const oyentes = new Set<() => void>();
const avisar = () => oyentes.forEach((f) => f());

export function suscribir(oyente: () => void): () => void {
  oyentes.add(oyente);
  // Otra pestaña inició o cerró sesión.
  const alCambiar = (e: StorageEvent) => {
    if (e.key === CLAVE_SESION) {
      memoria = leerTokens();
      oyente();
    }
  };
  window.addEventListener("storage", alCambiar);
  return () => {
    oyentes.delete(oyente);
    window.removeEventListener("storage", alCambiar);
  };
}

// --- Token y usuario ------------------------------------------------------------------

function cargaUtil(jwt: string): Record<string, unknown> {
  const parte = jwt.split(".")[1] ?? "";
  const base64 = parte.replace(/-/g, "+").replace(/_/g, "/").padEnd(Math.ceil(parte.length / 4) * 4, "=");
  const bytes = Uint8Array.from(atob(base64), (c) => c.charCodeAt(0));
  return JSON.parse(new TextDecoder().decode(bytes)) as Record<string, unknown>;
}

let usuarioCache: { token: string; usuario: Usuario } | null = null;

/** El usuario se lee del token de identidad. Solo sirve para la interfaz:
 *  quien decide de verdad es la API, que valida el token. */
export function usuarioActual(): Usuario | null {
  if (!memoria) return null;
  if (usuarioCache?.token === memoria.idToken) return usuarioCache.usuario;
  try {
    const datos = cargaUtil(memoria.idToken);
    const grupos = Array.isArray(datos["cognito:groups"]) ? (datos["cognito:groups"] as string[]) : [];
    const usuario = { email: String(datos.email ?? ""), grupos };
    usuarioCache = { token: memoria.idToken, usuario };
    return usuario;
  } catch {
    return null;
  }
}

// --- Llamadas a Cognito ---------------------------------------------------------------

const MENSAJES: Record<string, string> = {
  NotAuthorizedException: "Correo o contraseña incorrectos.",
  UserNotFoundException: "Correo o contraseña incorrectos.",
  PasswordResetRequiredException: "Tu contraseña fue restablecida. Pide al administrador una nueva temporal.",
  UserNotConfirmedException: "Tu cuenta aún no está confirmada. Avisa al administrador.",
  InvalidPasswordException:
    "La contraseña no cumple las reglas: al menos 10 caracteres, con mayúsculas, minúsculas y números.",
  TooManyRequestsException: "Demasiados intentos. Espera un momento y vuelve a intentarlo.",
  LimitExceededException: "Demasiados intentos. Espera un momento y vuelve a intentarlo.",
};

async function llamarCognito<T>(accion: string, cuerpo: object): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`https://cognito-idp.${REGION}.amazonaws.com/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": `AWSCognitoIdentityProviderService.${accion}`,
      },
      body: JSON.stringify(cuerpo),
    });
  } catch {
    throw new ErrorSesion("Sin conexión. Revisa tu conexión e inténtalo de nuevo.");
  }
  const datos = (await res.json().catch(() => ({}))) as Record<string, unknown>;
  if (!res.ok) {
    const tipo = String(datos.__type ?? "").split("#").pop() ?? "";
    throw new ErrorSesion(MENSAJES[tipo] ?? "No se pudo iniciar sesión. Inténtalo de nuevo.");
  }
  return datos as T;
}

type RespuestaAuth = {
  AuthenticationResult?: { IdToken: string; RefreshToken?: string; ExpiresIn: number };
  ChallengeName?: string;
  Session?: string;
};

function aceptar(resultado: NonNullable<RespuestaAuth["AuthenticationResult"]>, refreshAnterior?: string) {
  guardarTokens({
    idToken: resultado.IdToken,
    // Al renovar, Cognito no devuelve un refresh token nuevo: se conserva el anterior.
    refreshToken: resultado.RefreshToken ?? refreshAnterior ?? "",
    expiraEn: Date.now() + resultado.ExpiresIn * 1000,
  });
}

export async function iniciarSesion(correo: string, contrasena: string): Promise<ResultadoInicio> {
  const r = await llamarCognito<RespuestaAuth>("InitiateAuth", {
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: CLIENT_ID,
    AuthParameters: { USERNAME: correo, PASSWORD: contrasena },
  });
  if (r.AuthenticationResult) {
    aceptar(r.AuthenticationResult);
    return { tipo: "listo" };
  }
  if (r.ChallengeName === "NEW_PASSWORD_REQUIRED" && r.Session) {
    // Cuenta creada por un administrador: hay que cambiar la contraseña temporal.
    return { tipo: "nueva_contrasena", sesion: r.Session, correo };
  }
  throw new ErrorSesion("Este tipo de inicio de sesión no está soportado por la app.");
}

export async function fijarNuevaContrasena(correo: string, sesion: string, nueva: string): Promise<void> {
  const r = await llamarCognito<RespuestaAuth>("RespondToAuthChallenge", {
    ChallengeName: "NEW_PASSWORD_REQUIRED",
    ClientId: CLIENT_ID,
    Session: sesion,
    ChallengeResponses: { USERNAME: correo, NEW_PASSWORD: nueva },
  });
  if (!r.AuthenticationResult) throw new ErrorSesion("No se pudo cambiar la contraseña. Inicia sesión de nuevo.");
  aceptar(r.AuthenticationResult);
}

let renovando: Promise<string | null> | null = null;

async function renovar(tokens: Tokens): Promise<string | null> {
  try {
    const r = await llamarCognito<RespuestaAuth>("InitiateAuth", {
      AuthFlow: "REFRESH_TOKEN_AUTH",
      ClientId: CLIENT_ID,
      AuthParameters: { REFRESH_TOKEN: tokens.refreshToken },
    });
    if (!r.AuthenticationResult) throw new ErrorSesion("Sin token");
    aceptar(r.AuthenticationResult, tokens.refreshToken);
    return memoria?.idToken ?? null;
  } catch {
    guardarTokens(null);
    return null;
  }
}

/** Token de identidad vigente para la API, renovado si está por caducar. */
export async function tokenVigente(): Promise<string | null> {
  const tokens = memoria;
  if (!tokens) return null;
  if (tokens.expiraEn - Date.now() > MARGEN_RENOVACION_MS) return tokens.idToken;
  // Varias peticiones a la vez comparten una sola renovación.
  renovando ??= renovar(tokens).finally(() => {
    renovando = null;
  });
  return renovando;
}

export async function cerrarSesion(): Promise<void> {
  const tokens = memoria;
  guardarTokens(null);
  if (tokens?.refreshToken) {
    // Revoca el token de renovación en Cognito: aunque alguien lo hubiera
    // copiado, ya no sirve. Si falla (sin red), la sesión local ya se cerró.
    await llamarCognito("RevokeToken", { ClientId: CLIENT_ID, Token: tokens.refreshToken }).catch(() => {});
  }
}

/** La API respondió 401: el token ya no vale. */
export function descartarSesion(): void {
  guardarTokens(null);
}
