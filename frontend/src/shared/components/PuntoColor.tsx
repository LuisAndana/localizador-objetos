export function PuntoColor({ color }: { color: string }) {
  return (
    <span
      className="inline-block size-3 shrink-0 rounded-full ring-1 ring-border"
      style={{ backgroundColor: color }}
      aria-hidden
    />
  );
}
