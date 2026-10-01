import { useState, type FormEvent } from "react";
import { AlertCircle, KeyRound, Lightbulb, Loader2 } from "lucide-react";
import { ErrorSesion, fijarNuevaContrasena, iniciarSesion } from "@/core/auth/cognito";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Campo } from "@/shared/components/Campo";

const LONGITUD_MINIMA = 10;

/** Las mismas reglas que la política del user pool, para avisar antes de enviar. */
function problemaContrasena(valor: string): string | null {
  if (valor.length < LONGITUD_MINIMA) return `Debe tener al menos ${LONGITUD_MINIMA} caracteres.`;
  if (!/[a-z]/.test(valor) || !/[A-Z]/.test(valor)) return "Debe combinar mayúsculas y minúsculas.";
  if (!/[0-9]/.test(valor)) return "Debe incluir al menos un número.";
  return null;
}

const mensajeDe = (e: unknown) =>
  e instanceof ErrorSesion ? e.message : "No se pudo iniciar sesión. Inténtalo de nuevo.";

export default function InicioSesionPage() {
  const [paso, setPaso] = useState<{ sesion: string; correo: string } | null>(null);

  return (
    <div className="grid min-h-dvh place-items-center bg-muted/30 p-4">
      <div className="w-full max-w-sm rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
        <div className="mb-6 flex items-center gap-3">
          <span className="grid size-10 place-items-center rounded-xl bg-primary text-primary-foreground">
            {paso ? <KeyRound className="size-5" aria-hidden /> : <Lightbulb className="size-5" aria-hidden />}
          </span>
          <div>
            <h1 className="text-lg font-semibold tracking-tight">
              {paso ? "Crea tu contraseña" : "Localizador"}
            </h1>
            <p className="text-sm text-muted-foreground">
              {paso ? "Es tu primer ingreso: reemplaza la contraseña temporal." : "Inicia sesión para continuar."}
            </p>
          </div>
        </div>
        {paso ? (
          <FormNuevaContrasena correo={paso.correo} sesion={paso.sesion} alCancelar={() => setPaso(null)} />
        ) : (
          <FormInicio alPedirNueva={setPaso} />
        )}
      </div>
    </div>
  );
}

function AvisoError({ mensaje }: { mensaje: string }) {
  return (
    <p role="alert" className="flex items-start gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
      {mensaje}
    </p>
  );
}

function FormInicio({ alPedirNueva }: { alPedirNueva: (p: { sesion: string; correo: string }) => void }) {
  const [correo, setCorreo] = useState("");
  const [contrasena, setContrasena] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setEnviando(true);
    try {
      const r = await iniciarSesion(correo.trim(), contrasena);
      // "listo": la sesión quedó guardada y la app cambia sola de pantalla.
      if (r.tipo === "nueva_contrasena") alPedirNueva({ sesion: r.sesion, correo: r.correo });
    } catch (err) {
      setError(mensajeDe(err));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={enviar} className="grid gap-4" noValidate>
      <Campo id="correo" etiqueta="Correo">
        <Input
          id="correo"
          type="email"
          autoComplete="username"
          required
          value={correo}
          onChange={(e) => setCorreo(e.target.value)}
        />
      </Campo>
      <Campo id="contrasena" etiqueta="Contraseña">
        <Input
          id="contrasena"
          type="password"
          autoComplete="current-password"
          required
          value={contrasena}
          onChange={(e) => setContrasena(e.target.value)}
        />
      </Campo>
      {error && <AvisoError mensaje={error} />}
      <Button type="submit" disabled={enviando || !correo.trim() || !contrasena}>
        {enviando && <Loader2 className="size-4 animate-spin" aria-hidden />}
        Entrar
      </Button>
      <p className="text-center text-xs text-muted-foreground">
        ¿Sin cuenta o sin acceso? Pídela al administrador del almacén.
      </p>
    </form>
  );
}

function FormNuevaContrasena({
  correo,
  sesion,
  alCancelar,
}: {
  correo: string;
  sesion: string;
  alCancelar: () => void;
}) {
  const [nueva, setNueva] = useState("");
  const [repetida, setRepetida] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const problema = nueva ? problemaContrasena(nueva) : null;
  const distintas = repetida !== "" && repetida !== nueva;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    if (problemaContrasena(nueva) || nueva !== repetida) return;
    setError(null);
    setEnviando(true);
    try {
      await fijarNuevaContrasena(correo, sesion, nueva);
    } catch (err) {
      setError(mensajeDe(err));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <form onSubmit={enviar} className="grid gap-4" noValidate>
      <Campo
        id="nueva"
        etiqueta="Nueva contraseña"
        error={problema ?? undefined}
        ayuda="Al menos 10 caracteres, con mayúsculas, minúsculas y números."
      >
        <Input
          id="nueva"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!problema}
          value={nueva}
          onChange={(e) => setNueva(e.target.value)}
        />
      </Campo>
      <Campo id="repetida" etiqueta="Repítela" error={distintas ? "Las contraseñas no coinciden." : undefined}>
        <Input
          id="repetida"
          type="password"
          autoComplete="new-password"
          aria-invalid={distintas}
          value={repetida}
          onChange={(e) => setRepetida(e.target.value)}
        />
      </Campo>
      {error && <AvisoError mensaje={error} />}
      <Button type="submit" disabled={enviando || !!problemaContrasena(nueva) || nueva !== repetida}>
        {enviando && <Loader2 className="size-4 animate-spin" aria-hidden />}
        Guardar y entrar
      </Button>
      <Button type="button" variant="ghost" onClick={alCancelar}>
        Volver
      </Button>
    </form>
  );
}
