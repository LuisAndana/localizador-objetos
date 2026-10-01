import { cn } from "cn";

/**
 * Los valores que ya existen para un campo de texto libre.
 *
 * Teclear la ubicación a mano creaba pasillos fantasma por una mayúscula o un
 * cero de más. Mostrar lo que ya hay evita el error sin impedir dar de alta un
 * sitio nuevo: el campo sigue siendo escribible.
 */
export function ChipsSugerencia({
  etiqueta,
  opciones,
  valor,
  onElegir,
}: {
  etiqueta: string;
  opciones: string[];
  valor: string | undefined;
  onElegir: (valor: string) => void;
}) {
  if (opciones.length === 0) return null;

  return (
    <div className="flex flex-wrap items-center gap-1.5" role="group" aria-label={etiqueta}>
      {opciones.map((opcion) => {
        const activo = valor?.trim() === opcion;
        return (
          <button
            key={opcion}
            type="button"
            aria-pressed={activo}
            onClick={() => onElegir(opcion)}
            className={cn(
              "inline-flex h-11 min-w-11 items-center justify-center rounded-md border px-2.5 text-xs font-medium transition-colors md:h-7 md:min-w-7",
              activo
                ? "border-primary bg-primary/10 text-primary"
                : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {opcion}
          </button>
        );
      })}
    </div>
  );
}
