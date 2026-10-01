import { Lightbulb, Loader2 } from "lucide-react";
import { cn } from "cn";
import { PuntoColor } from "@/shared/components/PuntoColor";
import type { LedEncendido } from "../hooks/useLedsEnPlano";
import type { AnaquelPlano, ObjetoEnPlano } from "../tipos";

/** El tramo de tira WS2812B que corre por el borde de un nivel. */
function RielLed({
  objetos,
  encendidos,
}: {
  objetos: ObjetoEnPlano[];
  encendidos: Map<number, LedEncendido>;
}) {
  const leds = [...objetos].sort((a, b) => a.posicion_led - b.posicion_led);

  return (
    <div className="mt-2 flex items-end gap-2 rounded-md bg-tira px-2 py-1.5" aria-hidden>
      {leds.length === 0
        ? Array.from({ length: 8 }, (_, i) => (
            <span key={i} className="h-1.5 flex-1 rounded-full bg-led-apagado" />
          ))
        : leds.map((objeto) => {
            const led = encendidos.get(objeto.posicion_led);
            return (
              <span key={objeto.object_id} className="flex flex-1 flex-col items-center gap-1">
                <span
                  className={cn(
                    "size-2.5 rounded-full transition-all duration-300",
                    led ? "scale-125 animate-pulse" : "bg-led-apagado",
                  )}
                  style={
                    led
                      ? {
                          backgroundColor: led.color_indicador,
                          boxShadow: `0 0 8px 2px ${led.color_indicador}, 0 0 16px 4px ${led.color_indicador}66`,
                        }
                      : undefined
                  }
                />
                <span className="text-[9px] text-tira-texto tabular">{objeto.posicion_led}</span>
              </span>
            );
          })}
    </div>
  );
}

function ObjetoEnNivel({
  objeto,
  led,
  buscado,
  encendiendo,
  onEncender,
}: {
  objeto: ObjetoEnPlano;
  led: LedEncendido | undefined;
  buscado: boolean;
  encendiendo: boolean;
  onEncender: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onEncender}
      disabled={encendiendo}
      title={`Encender el LED #${objeto.posicion_led} de ${objeto.nombre}`}
      className={cn(
        "flex min-h-11 w-full items-center gap-2 rounded-lg border border-anaquel-borde bg-anaquel/70 px-2.5 py-2 text-left text-sm text-anaquel-texto transition-colors",
        "hover:bg-anaquel disabled:opacity-70",
        buscado && "border-primary",
      )}
      style={led ? { boxShadow: `0 0 0 1px ${led.color_indicador}, 0 0 14px 1px ${led.color_indicador}55` } : undefined}
    >
      <PuntoColor color={objeto.color_indicador} />
      <span className="min-w-0 flex-1 truncate font-medium">{objeto.nombre}</span>
      {led ? (
        <span className="shrink-0 text-xs tabular" style={{ color: led.color_indicador }}>
          {Math.ceil(led.segundos_restantes)} s
        </span>
      ) : encendiendo ? (
        <Loader2 className="size-4 shrink-0 animate-spin" aria-hidden />
      ) : (
        <Lightbulb className="size-4 shrink-0 opacity-60" aria-hidden />
      )}
    </button>
  );
}

/** El anaquel visto de frente: sus niveles, lo que guarda cada uno y su tira LED. */
export function AnaquelAlzado({
  pasillo,
  anaquel,
  encendidos,
  objetoBuscado,
  encendiendoId,
  onEncender,
}: {
  pasillo: string;
  anaquel: AnaquelPlano;
  encendidos: Map<number, LedEncendido>;
  objetoBuscado: string | null;
  encendiendoId: string | null;
  onEncender: (objeto: ObjetoEnPlano) => void;
}) {
  // El nivel más alto arriba, como está en el almacén.
  const niveles = [...anaquel.niveles].reverse();

  return (
    <section className="grid gap-3 rounded-xl border bg-card p-4 shadow-xs">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold tracking-tight">Anaquel {anaquel.anaquel}</h2>
        <p className="text-sm text-muted-foreground">
          Pasillo {pasillo} · <span className="tabular">{anaquel.total_objetos}</span>{" "}
          {anaquel.total_objetos === 1 ? "objeto" : "objetos"}
        </p>
      </header>

      <div className="grid gap-2 rounded-lg bg-piso p-3">
        {niveles.map((nivel) => (
          <div key={nivel.nivel} className="rounded-lg bg-anaquel/40 p-2">
            <div className="flex items-start gap-2">
              <span className="grid size-7 shrink-0 place-items-center rounded-md bg-anaquel text-xs font-semibold text-anaquel-texto tabular">
                {nivel.nivel}
              </span>
              <div className="grid min-w-0 flex-1 gap-1.5">
                {nivel.objetos.length === 0 ? (
                  <span className="flex min-h-11 items-center rounded-lg border border-dashed border-anaquel-borde px-2.5 text-xs text-anaquel-texto/60">
                    Nivel libre
                  </span>
                ) : (
                  nivel.objetos.map((objeto) => (
                    <ObjetoEnNivel
                      key={objeto.object_id}
                      objeto={objeto}
                      led={encendidos.get(objeto.posicion_led)}
                      buscado={objeto.object_id === objetoBuscado}
                      encendiendo={encendiendoId === objeto.object_id}
                      onEncender={() => onEncender(objeto)}
                    />
                  ))
                )}
              </div>
            </div>
            <RielLed objetos={nivel.objetos} encendidos={encendidos} />
          </div>
        ))}
      </div>

      <p className="text-xs text-muted-foreground">
        Toca un objeto para encender su LED durante 30 segundos.
      </p>
    </section>
  );
}
