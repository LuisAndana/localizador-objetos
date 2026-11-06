import { z } from "zod";

/** Las mismas reglas que la política del user pool (template.yaml), más una: no usar tu correo. */
export const LONGITUD_MINIMA = 10;

export function faltasContrasena(valor: string, correo = ""): string[] {
  const faltan: string[] = [];
  if (valor.length < LONGITUD_MINIMA) faltan.push(`al menos ${LONGITUD_MINIMA} caracteres`);
  if (!/[a-z]/.test(valor)) faltan.push("una minúscula");
  if (!/[A-Z]/.test(valor)) faltan.push("una mayúscula");
  if (!/[0-9]/.test(valor)) faltan.push("un número");
  const parteLocal = correo.split("@")[0]?.toLowerCase() ?? "";
  if (parteLocal.length >= 4 && valor.toLowerCase().includes(parteLocal)) faltan.push("que no incluya tu correo");
  return faltan;
}

/** Fuerza orientativa de 0 a 4 para el medidor. No sustituye las reglas. */
export function fuerzaContrasena(valor: string, correo = ""): number {
  if (!valor) return 0;
  // Una punto por cada grupo cumplido: longitud, minúscula, mayúscula y número.
  const grupos = [
    valor.length >= LONGITUD_MINIMA,
    /[a-z]/.test(valor),
    /[A-Z]/.test(valor),
    /[0-9]/.test(valor),
  ].filter(Boolean).length;
  const usaCorreo = faltasContrasena(valor, correo).includes("que no incluya tu correo");
  return usaCorreo ? Math.min(grupos, 2) : grupos;
}

/** Correo en minúsculas y sin espacios; luego se valida el formato. */
export const ESQUEMA_CORREO = z
  .string()
  .trim()
  .toLowerCase()
  .pipe(z.email("Escribe un correo válido, por ejemplo nombre@empresa.com."));

export const ESQUEMA_CODIGO = z
  .string()
  .trim()
  .regex(/^\d{6}$/, "El código tiene 6 números.");
