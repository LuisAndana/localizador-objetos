import { z } from "zod";

// Mismas reglas que layers/common/localizador/validacion.py: el usuario ve el
// error antes de enviar, pero el backend sigue siendo quien decide.
const REGEX_IDENTIFICADOR = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;
export const REGEX_COLOR = /^#[0-9A-Fa-f]{6}$/;

const identificador = (campo: string) =>
  z
    .string()
    .trim()
    .min(1, `${campo} es obligatorio`)
    .regex(REGEX_IDENTIFICADOR, "Solo letras, números, guion y guion bajo; empieza con letra o número.");

const textoUbicacion = (campo: string) =>
  z.string().trim().min(1, `${campo} es obligatorio`).max(30, "Máximo 30 caracteres");

export const objetoSchema = z.object({
  object_id: z.union([z.literal(""), identificador("El código")]).optional(),
  nombre: z.string().trim().min(1, "El nombre es obligatorio").max(120, "Máximo 120 caracteres"),
  categoria: z.string().min(1, "Elige una categoría"),
  almacen_id: identificador("El almacén"),
  pasillo: textoUbicacion("El pasillo"),
  anaquel: textoUbicacion("El anaquel"),
  nivel: textoUbicacion("El nivel"),
  posicion_led: z
    .number({ error: "Indica la posición del LED" })
    .int("Debe ser un número entero")
    .min(0, "Mínimo 0")
    .max(65535, "Máximo 65535"),
  color_indicador: z.string().regex(REGEX_COLOR, "Usa el formato #RRGGBB"),
});

export type ObjetoFormulario = z.infer<typeof objetoSchema>;
