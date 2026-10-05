import { cn } from "cn";
import type { LedEncendido } from "../hooks/useLedsEnPlano";
import type { AnaquelPlano, PasilloPlano, Plano } from "../tipos";

export type Seleccion = { pasillo: string; anaquel: string };

/** El LED encendido que cae dentro de este grupo de objetos, si lo hay. */
function ledDelNivel(objetos: { posicion_led: number }[], encendidos: Map<number, LedEncendido>) {
  for (const objeto of objetos) {
    const led = encendidos.get(objeto.posicion_led);
    if (led) return led;
  }
  return undefined;
}

function BloqueAnaquel({
  anaquel,
  seleccionado,
  contieneBuscado,
  encendidos,
  onSeleccionar,
}: {
  anaquel: AnaquelPlano;
  seleccionado: boolean;
  contieneBuscado: boolean;
  encendidos: Map<number, LedEncendido>;
  onSeleccionar: () => void;
}) {
  // De arriba hacia abajo, como se ve el anaquel de frente: el nivel más alto primero.
  const niveles = [...anaquel.niveles].reverse();
  const ledDelAnaquel = ledDelNivel(
    anaquel.niveles.flatMap((n) => n.objetos),
    encendidos,
  );

  return (
    <button
      type="button"
      onClick={onSeleccionar}
      aria-pressed={seleccionado}
      aria-label={`Anaquel ${anaquel.anaquel}, ${anaquel.total_objetos} objetos${
        ledDelAnaquel ? ", con un LED encendido" : ""
      }`}
      className={cn(
        "relative w-24 shrink-0 rounded-md border border-anaquel-borde bg-anaquel p-2 text-left transition-transform duration-200",
        "hover:-translate-y-0.5 focus-visible:-translate-y-0.5",
        seleccionado && "ring-2 ring-primary",
        contieneBuscado && !seleccionado && "ring-1 ring-anaquel-texto/40",
      )}
      style={
        ledDelAnaquel
          ? {
              boxShadow: `0 0 0 1px ${ledDelAnaquel.color_indicador}, 0 0 20px 3px ${ledDelAnaquel.color_indicador}66`,
            }
          : undefined
      }
    >
      <span className="flex items-baseline justify-between gap-1">
        <span className="text-xs font-semibold text-anaquel-texto">{anaquel.anaquel}</span>
        <span className="text-[10px] text-anaquel-texto/60 tabular">{anaquel.total_objetos}</span>
      </span>

      {/* La cuadrícula del anaquel en miniatura: una fila por nivel y un hueco por
          columna. El hueco con el LED encendido se ilumina con su color. */}
      <span className="mt-2 grid gap-1">
        {niveles.map((nivel) => (
          <span
            key={nivel.nivel}
            className="grid gap-0.5"
            style={{ gridTemplateColumns: `repeat(${anaquel.columnas.length}, minmax(0, 1fr))` }}
          >
            {nivel.celdas.map((celda) => {
              const led = ledDelNivel(celda.objetos, encendidos);
              return (
                <span
                  key={celda.columna}
                  className={cn(
                    "block h-1.5 rounded-sm transition-colors duration-300",
                    led ? "animate-pulse" : celda.objetos.length > 0 ? "bg-anaquel-texto/55" : "bg-anaquel-apagado",
                  )}
                  style={
                    led
                      ? {
                          backgroundColor: led.color_indicador,
                          boxShadow: `0 0 8px 1px ${led.color_indicador}`,
                        }
                      : undefined
                  }
                />
              );
            })}
          </span>
        ))}
      </span>
    </button>
  );
}

function Pasillo({
  pasillo,
  seleccion,
  objetoBuscado,
  encendidos,
  onSeleccionar,
}: {
  pasillo: PasilloPlano;
  seleccion: Seleccion | null;
  objetoBuscado: string | null;
  encendidos: Map<number, LedEncendido>;
  onSeleccionar: (s: Seleccion) => void;
}) {
  return (
    <section className="grid gap-2">
      <div className="-mx-1 flex gap-2 overflow-x-auto px-1 pb-1 [scrollbar-width:thin]">
        {pasillo.anaqueles.map((anaquel) => (
          <BloqueAnaquel
            key={anaquel.anaquel}
            anaquel={anaquel}
            encendidos={encendidos}
            seleccionado={seleccion?.pasillo === pasillo.pasillo && seleccion?.anaquel === anaquel.anaquel}
            contieneBuscado={anaquel.niveles.some((n) => n.objetos.some((o) => o.object_id === objetoBuscado))}
            onSeleccionar={() => onSeleccionar({ pasillo: pasillo.pasillo, anaquel: anaquel.anaquel })}
          />
        ))}
      </div>

      {/* El pasillo por donde se camina: el espacio entre filas de anaqueles. */}
      <div className="flex items-center gap-3 rounded-lg bg-pasillo px-3 py-2">
        <span className="text-[11px] font-semibold uppercase tracking-wider text-anaquel-texto">
          Pasillo {pasillo.pasillo}
        </span>
        <span className="h-px flex-1 border-t border-dashed border-piso-marca" />
        <span className="text-[11px] text-anaquel-texto/60 tabular">
          {pasillo.anaqueles.length} anaqueles · {pasillo.total_objetos} obj.
        </span>
      </div>
    </section>
  );
}

/** El almacén visto desde arriba: filas de anaqueles separadas por sus pasillos. */
export function PlantaAlmacen({
  plano,
  seleccion,
  objetoBuscado,
  encendidos,
  onSeleccionar,
}: {
  plano: Plano;
  seleccion: Seleccion | null;
  objetoBuscado: string | null;
  encendidos: Map<number, LedEncendido>;
  onSeleccionar: (s: Seleccion) => void;
}) {
  return (
    <div className="grid gap-4 rounded-xl bg-piso p-3 shadow-xs sm:p-4">
      <p className="flex items-center justify-between gap-2 text-[11px] uppercase tracking-wider text-anaquel-texto/70">
        <span>Almacén {plano.almacen_id} · vista en planta</span>
        <span className="tabular">{plano.total_objetos} objetos</span>
      </p>
      {plano.pasillos.map((pasillo) => (
        <Pasillo
          key={pasillo.pasillo}
          pasillo={pasillo}
          seleccion={seleccion}
          objetoBuscado={objetoBuscado}
          encendidos={encendidos}
          onSeleccionar={onSeleccionar}
        />
      ))}
    </div>
  );
}
