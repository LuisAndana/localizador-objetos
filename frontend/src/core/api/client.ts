import { AUTENTICACION_ACTIVA, descartarSesion, tokenVigente } from "@/core/auth/cognito";

// En local es "/api" (FastAPI o proxy de Vite); en AWS será la UrlApi del stack.
const API_URL: string = import.meta.env.VITE_API_URL ?? "/api";

export type Pagina<T> = {
  elementos: T[];
  total_en_pagina: number;
  siguiente_cursor: string | null;
};

// Campos declarados a mano: la plantilla de Vite activa `erasableSyntaxOnly`.
export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  readonly details?: unknown;

  constructor(status: number, message: string, code?: string, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

const MENSAJES: Record<number, string> = {
  0: "Sin conexión con el servidor. Revisa tu conexión e inténtalo de nuevo.",
  400: "Revisa los datos enviados.",
  401: "Tu sesión terminó. Vuelve a iniciar sesión.",
  403: "No tienes permiso para hacer esto.",
  404: "No se encontró lo que buscabas.",
  409: "El registro ya existe.",
  429: "Demasiadas peticiones. Espera un momento.",
  503: "El servicio está saturado. Inténtalo en unos segundos.",
};

function extraerMensaje(status: number, body: unknown): string {
  if (body && typeof body === "object") {
    const b = body as Record<string, unknown>;
    if (typeof b.mensaje === "string") return b.mensaje;
    if (typeof b.detail === "string") return b.detail;
  }
  return MENSAJES[status] ?? "Ocurrió un error inesperado. Inténtalo de nuevo.";
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body) headers.set("Content-Type", "application/json");
  if (AUTENTICACION_ACTIVA) {
    const token = await tokenVigente();
    if (!token) throw new ApiError(401, MENSAJES[401]);
    headers.set("Authorization", token);
  }

  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(0, MENSAJES[0]);
  }

  if (!res.ok) {
    // El token ya no vale (revocado o caducado): la app vuelve a la pantalla de entrada.
    if (res.status === 401 && AUTENTICACION_ACTIVA) descartarSesion();
    const body = await res.json().catch(() => null);
    throw new ApiError(res.status, extraerMensaje(res.status, body), body?.error, body?.detalles);
  }
  return res.status === 204 ? (undefined as T) : ((await res.json()) as T);
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) }),
  put: <T>(path: string, body: unknown) => request<T>(path, { method: "PUT", body: JSON.stringify(body) }),
  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),
};
