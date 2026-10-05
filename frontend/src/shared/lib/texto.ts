/** Minúsculas y sin acentos: "Multímetro" y "multimetro" deben coincidir al buscar. */
export function normalizar(texto: string): string {
  return texto.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase().trim();
}
