import { useState } from "react";
import { useForm, useWatch } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { Check, Loader2 } from "lucide-react";
import { ErrorSesion, registrarse } from "@/core/auth/cognito";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Campo } from "@/shared/components/Campo";
import { AvisoError } from "@/features/auth/AvisoError";
import { ESQUEMA_CORREO, faltasContrasena, fuerzaContrasena } from "@/features/auth/politica";
import { cn } from "cn";

const esquema = z
  .object({
    nombre: z
      .string()
      .trim()
      .min(2, "Escribe tu nombre completo.")
      .max(80, "Usa menos de 80 caracteres."),
    correo: ESQUEMA_CORREO,
    contrasena: z.string(),
    repetir: z.string(),
    aviso: z.boolean().refine((v) => v === true, {
      message: "Acepta el aviso de privacidad para crear tu cuenta.",
    }),
  })
  .superRefine((datos, ctx) => {
    const faltan = faltasContrasena(datos.contrasena, datos.correo);
    if (faltan.length > 0) {
      ctx.addIssue({ code: "custom", path: ["contrasena"], message: `Falta: ${faltan.join(", ")}.` });
    }
    if (datos.repetir !== datos.contrasena) {
      ctx.addIssue({ code: "custom", path: ["repetir"], message: "Las contraseñas no coinciden." });
    }
  });
type Datos = z.infer<typeof esquema>;

const mensajeDe = (e: unknown) =>
  e instanceof ErrorSesion ? e.message : "No se pudo crear la cuenta. Inténtalo de nuevo.";

const ETIQUETAS_FUERZA = ["Muy débil", "Débil", "Aceptable", "Buena", "Fuerte"];

export function FormularioRegistro({ alConfirmar }: { alConfirmar: (correo: string) => void }) {
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    control,
    formState: { errors, isSubmitting },
  } = useForm<Datos>({
    resolver: zodResolver(esquema),
    mode: "onTouched",
    defaultValues: { nombre: "", correo: "", contrasena: "", repetir: "", aviso: false },
  });

  const contrasena = useWatch({ control, name: "contrasena" }) ?? "";
  const correo = useWatch({ control, name: "correo" }) ?? "";
  const fuerza = fuerzaContrasena(contrasena, correo);

  const enviar = async (datos: Datos) => {
    setError(null);
    try {
      await registrarse(datos.correo, datos.nombre, datos.contrasena);
      // La misma pantalla exista o no el correo: no se revela si ya tenía cuenta.
      alConfirmar(datos.correo);
    } catch (err) {
      setError(mensajeDe(err));
    }
  };

  return (
    <form onSubmit={handleSubmit(enviar)} className="grid gap-5" noValidate>
      <Campo id="nombre" etiqueta="Nombre completo" error={errors.nombre?.message}>
        <Input
          id="nombre"
          autoComplete="name"
          aria-invalid={!!errors.nombre}
          {...register("nombre")}
        />
      </Campo>
      <Campo
        id="correo-registro"
        etiqueta="Correo del almacén"
        error={errors.correo?.message}
        ayuda="Solo se aceptan correos de la empresa. Te enviaremos un código para confirmarlo."
      >
        <Input
          id="correo-registro"
          type="email"
          autoComplete="email"
          inputMode="email"
          spellCheck={false}
          aria-invalid={!!errors.correo}
          {...register("correo")}
        />
      </Campo>
      <Campo id="contrasena-registro" etiqueta="Contraseña" error={errors.contrasena?.message}>
        <Input
          id="contrasena-registro"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.contrasena}
          {...register("contrasena")}
        />
        <div className="grid grid-cols-4 gap-1" aria-hidden>
          {[0, 1, 2, 3].map((i) => (
            <span
              key={i}
              className={cn("h-1.5 rounded-full bg-muted", i < fuerza && "bg-emerald-600")}
            />
          ))}
        </div>
        <p className="text-xs text-muted-foreground" aria-live="polite">
          {contrasena ? ETIQUETAS_FUERZA[fuerza] : "Al menos 10 caracteres, con mayúsculas, minúsculas y números."}
        </p>
      </Campo>
      <Campo id="repetir" etiqueta="Repite la contraseña" error={errors.repetir?.message}>
        <Input
          id="repetir"
          type="password"
          autoComplete="new-password"
          aria-invalid={!!errors.repetir}
          {...register("repetir")}
        />
      </Campo>
      <label htmlFor="aviso" className="flex items-start gap-3 text-sm leading-snug">
        <input
          id="aviso"
          type="checkbox"
          className="mt-0.5 size-4 accent-primary"
          aria-invalid={!!errors.aviso}
          {...register("aviso")}
        />
        <span>
          Acepto el aviso de privacidad y el uso del sistema para el inventario de Mamagui.
          {errors.aviso && <span className="mt-1 block text-destructive">{errors.aviso.message}</span>}
        </span>
      </label>
      {error && <AvisoError mensaje={error} />}
      <Button type="submit" disabled={isSubmitting}>
        {isSubmitting ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Check className="size-4" aria-hidden />}
        Crear cuenta
      </Button>
    </form>
  );
}
