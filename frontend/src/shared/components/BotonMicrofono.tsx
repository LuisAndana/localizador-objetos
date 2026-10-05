import { Mic, Square } from "lucide-react";
import { cn } from "cn";

/**
 * Micrófono para buscar por voz. Va dentro del campo de búsqueda, a la derecha:
 * se ve de inmediato (círculo con el color principal) sin agregar otra fila a la
 * pantalla. Mientras escucha, una onda lo rodea y el ícono cambia a "detener".
 */
export function BotonMicrofono({
  escuchando,
  onIniciar,
  onDetener,
  className,
}: {
  escuchando: boolean;
  onIniciar: () => void;
  onDetener: () => void;
  className?: string;
}) {
  return (
    <button
      type="button"
      onClick={escuchando ? onDetener : onIniciar}
      aria-pressed={escuchando}
      aria-label={escuchando ? "Dejar de escuchar" : "Buscar por voz"}
      title={escuchando ? "Dejar de escuchar" : "Buscar por voz"}
      className={cn(
        "group/mic absolute top-1/2 right-1.5 grid size-9 -translate-y-1/2 place-items-center rounded-full md:size-7",
        "bg-primary text-primary-foreground shadow-sm shadow-primary/30 transition-[transform,background-color] duration-200",
        "hover:scale-105 hover:bg-primary/90 focus-visible:ring-3 focus-visible:ring-ring/50 focus-visible:outline-none active:scale-95",
        escuchando && "bg-destructive shadow-destructive/40 hover:bg-destructive/90",
        className,
      )}
    >
      {escuchando && (
        <span
          className="pointer-events-none absolute inset-0 animate-ping rounded-full bg-destructive/50"
          aria-hidden
        />
      )}
      {escuchando ? (
        <Square className="relative size-3.5 fill-current md:size-3" aria-hidden />
      ) : (
        <Mic className="relative size-4 md:size-3.5" aria-hidden />
      )}
    </button>
  );
}
