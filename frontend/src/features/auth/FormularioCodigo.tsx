import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2, MailCheck } from "lucide-react";
import { ErrorSesion, confirmarRegistro, reenviarCodigoRegistro } from "@/core/auth/cognito";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Campo } from "@/shared/components/Campo";
import { AvisoError, AvisoOk } from "@/features/auth/AvisoError";
import { ESQUEMA_CODIGO } from "@/features/auth/politica";

const esquema = z.object({ codigo: ESQUEMA_CODIGO });
type Datos = z.infer<typeof esquema>;

const mensajeDe = (e: unknown) =>
  e instanceof ErrorSesion ? e.message : "No se pudo confirmar el correo. Inténtalo de nuevo.";

export function FormularioCodigo({
  correo,
  alConfirmado,
}: {
  correo: string;
  alConfirmado: () => void;
}) {
  const [error, setError] = useState<string | null>(null);
  const [aviso, setAviso] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    mode: "onTouched",
    defaultValues: { codigo: "" },
  });

  const enviar = async (datos: Datos) => {
    setError(null);
    setAviso(null);
    try {
      await confirmarRegistro(correo, datos.codigo);
      alConfirmado();
    } catch (err) {
      setError(mensajeDe(err));
    }
  };

  const reenviar = async () => {
    setError(null);
    await reenviarCodigoRegistro(correo);
    setAviso("Si el correo es válido, te enviamos un código nuevo.");
  };

  return (
    <form onSubmit={handleSubmit(enviar)} className="grid gap-5" noValidate>
      <div className="flex items-start gap-3 rounded-lg bg-muted/60 p-3 text-sm">
        <MailCheck className="mt-0.5 size-4 shrink-0" aria-hidden />
        <p>
          Enviamos un código de 6 números a <b className="break-all">{correo}</b>. Caduca en 15 minutos.
        </p>
      </div>
      <Campo id="codigo" etiqueta="Código de verificación" error={errors.codigo?.message}>
        <Input
          id="codigo"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          aria-invalid={!!errors.codigo}
          className="text-center text-lg tracking-[0.4em]"
          {...register("codigo")}
        />
      </Campo>
      {error && <AvisoError mensaje={error} />}
      {aviso && <AvisoOk mensaje={aviso} />}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="size-4 animate-spin" aria-hidden />}
        Confirmar correo
      </Button>
      <Button type="button" variant="ghost" onClick={reenviar}>
        No llegó el código: enviar otro
      </Button>
    </form>
  );
}
