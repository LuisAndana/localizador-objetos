const fechaHora = new Intl.DateTimeFormat("es-MX", { dateStyle: "medium", timeStyle: "short" });

export function formatearFecha(iso: string): string {
  const fecha = new Date(iso);
  return Number.isNaN(fecha.getTime()) ? iso : fechaHora.format(fecha);
}

/** Duraciones legibles: "840 ms", "3.4 s", "2 min 05 s". */
export function formatearDuracion(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "—";
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const segundos = ms / 1000;
  if (segundos < 60) return `${segundos.toFixed(1)} s`;
  const minutos = Math.floor(segundos / 60);
  return `${minutos} min ${String(Math.round(segundos % 60)).padStart(2, "0")} s`;
}
