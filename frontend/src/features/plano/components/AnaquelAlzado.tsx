import { Loader2 } from "lucide-react";
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

function ObjetoEnCelda({
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
      title={`${objeto.nombre} · columna ${objeto.columna} · LED #${objeto.posicion_led}`}
      className={cn(
        "grid min-h-11 w-full min-w-0 content-start gap-0.5 overflow-hidden rounded-md border border-anaquel-borde bg-anaquel/80 px-2 py-1.5 text-left text-xs leading-snug text-anaquel-texto transition-colors",
        "hover:bg-anaquel disabled:opacity-70",
        buscado && "border-primary",
      )}
      style={led ? { boxShadow: `0 0 0 1px ${led.color_indicador}, 0 0 14px 1px ${led.color_indicador}55` } : undefined}
    >
      {/* Sin ícono al lado: en un hueco angosto el nombre necesita todo el ancho. */}
      <span lang="es" className="line-clamp-2 font-medium hyphens-auto">
        <span className="mr-1 inline-block align-middle">
          <PuntoColor color={objeto.color_indicador} />
        </span>
        {objeto.nombre}
      </span>
      {led ? (
        <span className="text-[11px] tabular" style={{ color: led.color_indicador }}>
          Encendido · {Math.ceil(led.segundos_restantes)} s
        </span>
      ) : (
        encendiendo && <Loader2 className="size-3.5 animate-spin" aria-hidden />
      )}
    </button>
  );
}

/**
 * El anaquel visto de frente, como una estantería real: postes a los lados, una
 * repisa por nivel (filas) y los huecos de cada repisa (columnas). Debajo de cada
 * repisa corre su tramo de tira LED.
 */
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
  // Columna de la etiqueta del nivel + una por columna del anaquel. Con muchas
  // columnas la estantería se desplaza de lado en vez de aplastar los nombres.
  const columnasGrid = { gridTemplateColumns: `1.5rem repeat(${anaquel.columnas.length}, minmax(4.25rem, 1fr))` };

  return (
    <section className="grid gap-3 rounded-xl border bg-card p-4 shadow-xs">
      <header className="flex flex-wrap items-baseline justify-between gap-2">
        <h2 className="text-lg font-semibold tracking-tight">Anaquel {anaquel.anaquel}</h2>
        <p className="text-sm text-muted-foreground">
          Pasillo {pasillo} · <span className="tabular">{anaquel.niveles.length}</span> niveles ×{" "}
          <span className="tabular">{anaquel.columnas.length}</span> columnas ·{" "}
          <span className="tabular">{anaquel.total_objetos}</span> {anaquel.total_objetos === 1 ? "objeto" : "objetos"}
        </p>
      </header>

      <div className="overflow-x-auto rounded-lg bg-piso p-2 sm:p-3 [scrollbar-width:thin]">
        <div className="grid min-w-fit gap-0">
          {/* Rótulos de las columnas, como los que lleva el travesaño de arriba. */}
          <div className="grid gap-1 px-1 pb-1.5 sm:gap-1.5 sm:px-1.5" style={columnasGrid}>
            <span />
            {anaquel.columnas.map((columna) => (
              <span
                key={columna}
                className="text-center text-[11px] font-semibold uppercase tracking-wider text-anaquel-texto/70"
              >
                {columna}
              </span>
            ))}
          </div>

          {/* Los postes del anaquel son los bordes laterales del marco. */}
          <div className="grid gap-0 rounded-md border-x-4 border-t-4 border-anaquel-borde">
            {niveles.map((nivel) => (
              <div key={nivel.nivel} className="border-b-4 border-anaquel-borde bg-anaquel/25">
                <div className="grid items-stretch gap-1 p-1 sm:gap-1.5 sm:p-1.5" style={columnasGrid}>
                  <span
                    className="grid size-6 place-items-center self-center rounded-md bg-anaquel text-xs font-semibold text-anaquel-texto tabular"
                    title={`Nivel ${nivel.nivel}`}
                  >
                    {nivel.nivel}
                  </span>
                  {nivel.celdas.map((celda) => (
                    <div
                      key={celda.columna}
                      className="grid min-h-14 min-w-0 content-start gap-1 rounded-md border border-anaquel-borde/40 bg-piso/40 p-1"
                      aria-label={`Nivel ${nivel.nivel}, columna ${celda.columna}`}
                    >
                      {celda.objetos.length === 0 ? (
                        <span className="grid min-h-11 place-items-center rounded-md border border-dashed border-anaquel-borde/60 text-[11px] text-anaquel-texto/50">
                          Libre
                        </span>
                      ) : (
                        celda.objetos.map((objeto) => (
                          <ObjetoEnCelda
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
                  ))}
                </div>
                <div className="px-1 pb-1 pl-[2.25rem] sm:px-1.5 sm:pb-1.5 sm:pl-[2.625rem]">
                  <RielLed objetos={nivel.objetos} encendidos={encendidos} />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <p className="text-xs text-muted-foreground">
        Toca un objeto para encender su LED durante 30 segundos.
      </p>
    </section>
  );
}
