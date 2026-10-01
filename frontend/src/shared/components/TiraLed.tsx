import type { CSSProperties } from "react";
import { cn } from "cn";

export type LedEncendido = { posicion_led: number; color_indicador: string; nombre?: string | null };

const LEDS_POR_FILA = 30;

// El color viene del dato de cada objeto, por eso va en estilo en línea y no en un token.
const brillo = (color: string): CSSProperties => ({
  backgroundColor: color,
  boxShadow: `0 0 6px 1px ${color}, 0 0 16px 4px ${color}80`,
});

/** Tira WS2812B completa, en filas de 30 LEDs como un segmento físico de 50 cm. */
export function TiraLed({ total, activos }: { total: number; activos: LedEncendido[] }) {
  const encendidos = new Map(activos.map((a) => [a.posicion_led, a]));
  const filas = Math.ceil(total / LEDS_POR_FILA);

  return (
    <div
      role="img"
      aria-label={`Tira LED de ${total} posiciones con ${activos.length} encendidas`}
      className="rounded-xl bg-tira p-3 sm:p-4"
    >
      <div className="grid gap-2.5">
        {Array.from({ length: filas }, (_, f) => {
          const inicio = f * LEDS_POR_FILA;
          const cantidad = Math.min(LEDS_POR_FILA, total - inicio);
          return (
            <div key={inicio} className="flex items-start gap-3">
              <span className="w-7 shrink-0 pt-px text-right text-[10px] font-medium text-tira-texto tabular">
                {inicio}
              </span>
              <div className="grid flex-1 grid-cols-15 gap-x-1.5 gap-y-2 sm:grid-cols-30">
                {Array.from({ length: cantidad }, (_, k) => {
                  const i = inicio + k;
                  const led = encendidos.get(i);
                  return (
                    <span
                      key={i}
                      title={led ? `LED ${i}${led.nombre ? ` · ${led.nombre}` : ""}` : `LED ${i}`}
                      className={cn(
                        "mx-auto aspect-square w-full max-w-3 rounded-full transition-all duration-300",
                        led ? "scale-125" : "bg-led-apagado",
                      )}
                      style={led ? brillo(led.color_indicador) : undefined}
                    />
                  );
                })}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

/** Ventana de la tira alrededor de una posición: lo que vería quien está frente al anaquel. */
export function TiraSegmento({
  centro,
  color,
  encendido,
  radio = 6,
}: {
  centro: number;
  color: string;
  encendido: boolean;
  radio?: number;
}) {
  const desde = Math.max(0, centro - radio);
  const indices = Array.from({ length: radio * 2 + 1 }, (_, k) => desde + k);

  return (
    <div className="rounded-xl bg-tira px-3 py-5 sm:px-5" aria-hidden>
      <div className="flex items-end justify-between gap-1 sm:gap-2">
        {indices.map((i) => {
          const activo = encendido && i === centro;
          return (
            <div key={i} className="flex flex-1 flex-col items-center gap-2">
              <span
                className={cn(
                  "aspect-square w-full max-w-5 rounded-full transition-all duration-500",
                  activo ? "scale-125 animate-pulse" : "bg-led-apagado",
                )}
                style={activo ? brillo(color) : undefined}
              />
              <span
                className={cn(
                  "text-[10px] text-tira-texto tabular",
                  i === centro && "font-bold",
                  // En móvil solo se rotulan el centro y los extremos para que no se amontonen.
                  i !== centro && i !== indices[0] && i !== indices.at(-1) && "max-sm:invisible",
                )}
              >
                {i}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
