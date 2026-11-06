import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Loader2 } from "lucide-react";
import { ErrorSesion, pedirCodigoRecuperacion, restablecerContrasena } from "@/core/auth/cognito";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Campo } from "@/shared/components/Campo";
import { AvisoError } from "@/features/auth/AvisoError";
import {
  ESQUEMA_CODIGO,
  ESQUEMA_CORREO,
  faltasContrasena,
} from "@/features/auth/politica";

const mensajeDe = (e: unknown) =>
  e instanceof ErrorSesion ? e.message : "No se pudo completar la operación. Inténtalo de nuevo.";

const esquemaCorreo = z.object({ correo: ESQUEMA_CORREO });

const esquemaNueva = z
  .object({
    codigo: ESQUEMA_CODIGO,
    contrasena: z.string(),
    repetir: z.string(),
  })
  .superRefine((datos, ctx) => {
    const faltan = faltasContrasena(datos.contrasena);
    if (faltan.length > 0) {
      ctx.addIssue({ code: "custom", path: ["contrasena"], message: `Falta: ${faltan.join(", ")}.` });
    }
    if (datos.repetir !== datos.contrasena) {
      ctx.addIssue({ code: "custom", path: ["repetir"], message: "Las contraseñas no coinciden." });
    }
  });

/** Dos pasos: pedir el código por correo y luego escribir la nueva contraseña. */
export function FormularioRecuperar({
  alTerminar,
  alVolver,
}: {
  alTerminar: (mensaje: string) => void;
  alVolver: () => void;
}) {
  const [correo, setCorreo] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const paso1 = useForm<{ correo: string }>({
    resolver: zodResolver(esquemaCorreo),
    mode: "onTouched",
    defaultValues: { correo: "" },
  });
  const paso2 = useForm<{ codigo: string; contrasena: string; repetir: string }>({
    resolver: zodResolver(esquemaNueva),
    mode: "onTouched",
    defaultValues: { codigo: "", contrasena: "", repetir: "" },
  });

  const enviarCorreo = async (datos: { correo: string }) => {
    setError(null);
    try {
      await pedirCodigoRecuperacion(datos.correo);
      // La misma respuesta exista o no el correo.
      setCorreo(datos.correo);
    } catch (err) {
      setError(mensajeDe(err));
    }
  };

  const enviarNueva = async (datos: { codigo: string; contrasena: string }) => {
    if (!correo) return;
    setError(null);
    try {
      await restablecerContrasena(correo, datos.codigo, datos.contrasena);
      alTerminar("Contraseña actualizada. Ya puedes entrar.");
    } catch (err) {
      setError(mensajeDe(err));
    }
  };

  if (!correo) {
    return (
      <form onSubmit={paso1.handleSubmit(enviarCorreo)} className="grid gap-5" noValidate>
        <Campo id="correo-recuperar" etiqueta="Correo del almacén" error={paso1.formState.errors.correo?.message}>
          <Input
            id="correo-recuperar"
            type="email"
            autoComplete="username"
            inputMode="email"
            aria-invalid={!!paso1.formState.errors.correo}
            {...paso1.register("correo")}
          />
        </Campo>
        {error && <AvisoError mensaje={error} />}
        <Button type="submit" disabled={paso1.formState.isSubmitting}>
          {paso1.formState.isSubmitting && <Loader2 className="size-4 animate-spin" aria-hidden />}
          Enviar código
        </Button>
        <Button type="button" variant="ghost" onClick={alVolver}>
          Volver
        </Button>
      </form>
    );
  }

  const { errors, isSubmitting } = paso2.formState;
  return (
    <form onSubmit={paso2.handleSubmit(enviarNueva)} className="grid gap-5" noValidate>
      <p className="text-sm text-muted-foreground">
        Si <b className="break-all">{correo}</b> tiene cuenta, recibirá un código de 6 números.
      </p>
      <Campo id="codigo-recuperar" etiqueta="Código" error={errors.codigo?.message}>
        <Input
          id="codigo-recuperar"
          inputMode="numeric"
          autoComplete="one-time-code"
          maxLength={6}
          aria-invalid={!!errors.codigo}
          {...paso2.register("codigo")}
        />
      </Campo>
      <Campo
        id="nueva-recuperar"
        etiqueta="Nueva contraseña"
        error={errors.contrasena?.message}
        ayuda="Al menos 10 caracteres, con mayúsculas, minúsculas y números."
      >
        <Input
          id="nueva-recuperar"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.contrasena}
          {...paso2.register("contrasena")}
        />
      </Campo>
      <Campo id="repetir-recuperar" etiqueta="Repite la contraseña" error={errors.repetir?.message}>
        <Input
          id="repetir-recuperar"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.repetir}
          {...paso2.register("repetir")}
        />
      </Campo>
      {error && <AvisoError mensaje={error} />}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting && <Loader2 className="size-4 animate-spin" aria-hidden />}
        Guardar contraseña
      </Button>
    </form>
  );
}
