import { cn } from "cn";

export type PosicionOcupada = { nombre: string; color_indicador: string };

const MINIMO_POSICIONES = 60;
const HOLGURA = 12;

/** Hasta dónde dibujar la tira: lo que ya se usa, más holgura, en decenas. */
function totalPosiciones(ocupadas: Map<number, PosicionOcupada>, valor: number | null) {
  const mayor = Math.max(-1, ...ocupadas.keys(), valor ?? -1);
  return Math.max(MINIMO_POSICIONES, Math.ceil((mayor + HOLGURA) / 10) * 10);
}

/**
 * La posición del LED se elige tocándola en la tira, no escribiendo un número.
 *
 * Las posiciones ocupadas se ven ocupadas: dos objetos en la misma se
 * encenderían juntos, así que el servidor las rechaza (409) y aquí ni siquiera
 * se pueden pulsar.
 */
export function SelectorLed({
  valor,
  color,
  ocupadas,
  onElegir,
}: {
  valor: number | null;
  color: string;
  ocupadas: Map<number, PosicionOcupada>;
  onElegir: (posicion: number) => void;
}) {
  const total = totalPosiciones(ocupadas, valor);

  return (
    <div className="grid gap-2">
      <div className="rounded-xl bg-tira p-3">
        <div className="grid grid-cols-10 gap-1.5 sm:grid-cols-20">
          {Array.from({ length: total }, (_, i) => {
            const ocupada = ocupadas.get(i);
            const elegida = valor === i;
            return (
              <button
                key={i}
                type="button"
                disabled={Boolean(ocupada)}
                onClick={() => onElegir(i)}
                aria-pressed={elegida}
                title={ocupada ? `Posición ${i}: ocupada por ${ocupada.nombre}` : `Posición ${i}: libre`}
                className={cn(
                  "grid aspect-square place-items-center rounded-full text-[9px] transition-all duration-200",
                  elegida && "scale-110 font-bold text-tira",
                  !elegida && ocupada && "cursor-not-allowed text-tira opacity-70",
                  !elegida && !ocupada && "bg-led-apagado text-tira-texto hover:scale-110 hover:bg-tira-texto/40",
                )}
                style={
                  elegida
                    ? { backgroundColor: color, boxShadow: `0 0 10px 2px ${color}` }
                    : ocupada
                      ? { backgroundColor: ocupada.color_indicador }
                      : undefined
                }
              >
                {i % 10 === 0 ? i : ""}
              </button>
            );
          })}
        </div>
      </div>

      <p className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-led-apagado" aria-hidden />
          Libre
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full bg-muted-foreground" aria-hidden />
          Ya ocupada por otro objeto
        </span>
        <span className="flex items-center gap-1.5">
          <span className="size-2.5 rounded-full" style={{ backgroundColor: color }} aria-hidden />
          La de este objeto
        </span>
      </p>
    </div>
  );
}
