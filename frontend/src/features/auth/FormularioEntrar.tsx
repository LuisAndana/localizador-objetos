import { useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { ErrorSesion, iniciarSesion } from "@/core/auth/cognito";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Campo } from "@/shared/components/Campo";
import { AvisoError } from "@/features/auth/AvisoError";
import { ESQUEMA_CORREO } from "@/features/auth/politica";

const MAX_INTENTOS = 5;
const ESPERA_MS = 30_000;

// Esta limitación es de la interfaz: frena a quien prueba a mano. La protección
// real está en Cognito, que bloquea los intentos fallidos en el servidor.
const esquema = z.object({
  correo: ESQUEMA_CORREO,
  contrasena: z.string().min(1, "Escribe tu contraseña."),
});
type Datos = z.infer<typeof esquema>;

const mensajeDe = (e: unknown) =>
  e instanceof ErrorSesion ? e.message : "No se pudo iniciar sesión. Inténtalo de nuevo.";

export function FormularioEntrar({
  alPedirNueva,
  alRecuperar,
}: {
  alPedirNueva: (p: { sesion: string; correo: string }) => void;
  alRecuperar: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [intentos, setIntentos] = useState(0);
  const [bloqueado, setBloqueado] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    mode: "onTouched",
    defaultValues: { correo: "", contrasena: "" },
  });

  useEffect(() => {
    if (!bloqueado) return;
    const pausa = setTimeout(() => {
      setBloqueado(false);
      setIntentos(0);
    }, ESPERA_MS);
    return () => clearTimeout(pausa);
  }, [bloqueado]);

  const enviar = async (datos: Datos) => {
    setError(null);
    try {
      const r = await iniciarSesion(datos.correo, datos.contrasena);
      // "listo": la sesión quedó guardada y la app cambia sola de pantalla.
      if (r.tipo === "nueva_contrasena") alPedirNueva({ sesion: r.sesion, correo: r.correo });
    } catch (err) {
      const siguiente = intentos + 1;
      setIntentos(siguiente);
      if (siguiente >= MAX_INTENTOS) {
        setBloqueado(true);
        setError("Demasiados intentos. Espera 30 segundos antes de volver a intentarlo.");
      } else {
        setError(mensajeDe(err));
      }
    }
  };

  const deshabilitado = isSubmitting || bloqueado;

  return (
    <form onSubmit={handleSubmit(enviar)} className="grid gap-5" noValidate>
      <Campo id="correo" etiqueta="Correo" error={errors.correo?.message}>
        <Input
          id="correo"
          type="email"
          autoComplete="username"
          inputMode="email"
          spellCheck={false}
          aria-invalid={!!errors.correo}
          {...register("correo")}
        />
      </Campo>
      <Campo id="contrasena" etiqueta="Contraseña" error={errors.contrasena?.message}>
        <Input
          id="contrasena"
          type="password"
          autoComplete="current-password"
          aria-invalid={!!errors.contrasena}
          {...register("contrasena")}
        />
      </Campo>
      {error && <AvisoError mensaje={error} />}
      <Button type="submit" disabled={deshabilitado}>
        {isSubmitting && <Loader2 className="size-4 animate-spin" aria-hidden />}
        Entrar
      </Button>
      <div className="flex justify-between text-sm">
        <Button type="button" variant="link" className="h-auto p-0" onClick={alRecuperar}>
          ¿Olvidaste tu contraseña?
        </Button>
      </div>
    </form>
  );
}
