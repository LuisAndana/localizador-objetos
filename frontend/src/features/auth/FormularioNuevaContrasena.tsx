import { useState, type FormEvent } from "react";
import { Loader2 } from "lucide-react";
import { ErrorSesion, fijarNuevaContrasena } from "@/core/auth/cognito";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Campo } from "@/shared/components/Campo";
import { AvisoError } from "@/features/auth/AvisoError";
import { faltasContrasena } from "@/features/auth/politica";

const mensajeDe = (e: unknown) =>
  e instanceof ErrorSesion ? e.message : "No se pudo cambiar la contraseña. Inténtalo de nuevo.";

/** Primer ingreso con contraseña temporal creada por el administrador. */
export function FormularioNuevaContrasena({
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

  const faltan = nueva ? faltasContrasena(nueva, correo) : [];
  const distintas = repetida !== "" && repetida !== nueva;
  const valida = faltasContrasena(nueva, correo).length === 0 && nueva === repetida;

  const enviar = async (e: FormEvent) => {
    e.preventDefault();
    if (!valida) return;
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
    <form onSubmit={enviar} className="grid gap-5" noValidate>
      <Campo
        id="nueva"
        etiqueta="Nueva contraseña"
        error={faltan.length > 0 ? `Falta: ${faltan.join(", ")}.` : undefined}
        ayuda="Al menos 10 caracteres, con mayúsculas, minúsculas y números."
      >
        <Input
          id="nueva"
          type="password"
          autoComplete="new-password"
          aria-invalid={faltan.length > 0}
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
      <Button type="submit" disabled={enviando || !valida}>
        {enviando && <Loader2 className="size-4 animate-spin" aria-hidden />}
        Guardar y entrar
      </Button>
      <Button type="button" variant="ghost" onClick={alCancelar}>
        Volver
      </Button>
    </form>
  );
}
