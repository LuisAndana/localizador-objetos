/** Si el texto coincide salvo por mayúsculas con algo que ya existe, se usa esa escritura. */
export function ajustarAExistente(valor: string, opciones: string[]): string {
  const limpio = valor.trim();
  const existente = opciones.find((o) => o.toLowerCase() === limpio.toLowerCase());
  return existente ?? limpio;
}
