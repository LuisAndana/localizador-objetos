import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router";
import { AlertCircle, Boxes, Cpu, Lightbulb, MapPinned, PackageSearch } from "lucide-react";
import { cn } from "cn";
import { DEMO_LOCAL } from "@/core/config";
import { useLocalizarEnMapa } from "@/features/objetos/api";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { EmptyState } from "@/shared/components/EmptyState";
import { PageHeader } from "@/shared/components/PageHeader";
import { TiraLed } from "@/shared/components/TiraLed";
import { useAlmacenes, ubicarEnPlano, usePlano } from "../api";
import { AnaquelAlzado } from "../components/AnaquelAlzado";
import { BuscadorEnPlano } from "../components/BuscadorEnPlano";
import { PlantaAlmacen, type Seleccion } from "../components/PlantaAlmacen";
import { useLedsEnPlano } from "../hooks/useLedsEnPlano";
import type { AnaquelPlano, ObjetoEnPlano, Plano } from "../tipos";

/** Cuánto dura el encendido que se pide desde el mapa. */
const DURACION_SEGUNDOS = 30;

const claseChip = (activo: boolean) =>
  cn(
    "inline-flex h-11 shrink-0 items-center gap-2 rounded-full border px-4 text-sm font-medium transition-colors md:h-9",
    activo
      ? "border-primary bg-primary text-primary-foreground"
      : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
  );

function primerAnaquel(plano: Plano | undefined): Seleccion | null {
  const pasillo = plano?.pasillos[0];
  const anaquel = pasillo?.anaqueles[0];
  return pasillo && anaquel ? { pasillo: pasillo.pasillo, anaquel: anaquel.anaquel } : null;
}

function buscarAnaquel(plano: Plano | undefined, seleccion: Seleccion | null): AnaquelPlano | undefined {
  if (!plano || !seleccion) return undefined;
  return plano.pasillos
    .find((p) => p.pasillo === seleccion.pasillo)
    ?.anaqueles.find((a) => a.anaquel === seleccion.anaquel);
}

export default function PlanoPage() {
  const [params, setParams] = useSearchParams();
  const almacenes = useAlmacenes();
  const objetoBuscado = params.get("objeto");
  const almacenId = params.get("almacen") ?? almacenes.data?.[0]?.almacen_id;
  const plano = usePlano(almacenId);
  const { encendidos, registrarOrden, escuchando, topic, totalLeds } = useLedsEnPlano(almacenId);
  const localizar = useLocalizarEnMapa();

  const [seleccion, setSeleccion] = useState<Seleccion | null>(null);
  const panel = useRef<HTMLDivElement>(null);

  const ubicacion = ubicarEnPlano(plano.data, objetoBuscado);
  const seleccionEfectiva = seleccion ?? primerAnaquel(plano.data);
  const anaquelAbierto = buscarAnaquel(plano.data, seleccionEfectiva);
  const ledDelBuscado = ubicacion ? encendidos.get(ubicacion.objeto.posicion_led) : undefined;

  // Al llegar con ?objeto= (o al elegirlo en el buscador) se abre su anaquel.
  const idUbicado = ubicacion?.objeto.object_id;
  useEffect(() => {
    if (ubicacion) setSeleccion({ pasillo: ubicacion.pasillo, anaquel: ubicacion.anaquel });
    // `ubicacion` se recalcula en cada render; el objeto ubicado es lo que de verdad cambia.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [idUbicado]);

  // Cambiar de almacén no debe dejar abierto un anaquel del anterior.
  useEffect(() => {
    setSeleccion(null);
  }, [almacenId]);

  const encender = (objeto: ObjetoEnPlano) => {
    if (!almacenId) return;
    localizar.mutate(
      { id: objeto.object_id, duracion_segundos: DURACION_SEGUNDOS },
      {
        onSuccess: () =>
          registrarOrden({
            almacen_id: almacenId,
            posicion_led: objeto.posicion_led,
            color_indicador: objeto.color_indicador,
            object_id: objeto.object_id,
            nombre: objeto.nombre,
            duracion_segundos: DURACION_SEGUNDOS,
          }),
      },
    );
  };

  return (
    <div className="grid gap-6">
      <PageHeader
        titulo="Mapa del almacén"
        descripcion="El almacén visto desde arriba: pasillos, anaqueles y lo que guarda cada hueco (nivel y columna). Busca un objeto y su LED se enciende en el anaquel donde está."
      />

      <div
        role="group"
        aria-label="Elegir almacén"
        className="-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none] md:mx-0 md:px-0 [&::-webkit-scrollbar]:hidden"
      >
        {almacenes.isPending
          ? Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-11 w-40 shrink-0 rounded-full md:h-9" />)
          : almacenes.data?.map((a) => (
              <button
                key={a.almacen_id}
                type="button"
                aria-pressed={almacenId === a.almacen_id}
                onClick={() => setParams({ almacen: a.almacen_id })}
                className={claseChip(almacenId === a.almacen_id)}
              >
                {a.almacen_id}
                <span className="text-xs opacity-70 tabular">
                  {a.total_pasillos} pasillos · {a.total_objetos} obj.
                </span>
              </button>
            ))}
      </div>

      {almacenes.isError || plano.isError ? (
        <EmptyState
          icono={AlertCircle}
          titulo="No se pudo cargar el mapa"
          descripcion="No hubo respuesta del servidor. Vuelve a intentarlo en un momento."
          accion={
            <Button variant="outline" onClick={() => (plano.isError ? plano.refetch() : almacenes.refetch())}>
              Reintentar
            </Button>
          }
        />
      ) : plano.isPending ? (
        <div className="grid gap-4" aria-busy="true">
          <Skeleton className="h-11" />
          <Skeleton className="h-64" />
        </div>
      ) : plano.data.pasillos.length === 0 ? (
        <EmptyState
          icono={PackageSearch}
          titulo="Este almacén está vacío"
          descripcion="Registra un objeto con su pasillo, anaquel, nivel y columna para que aparezca en el mapa."
          accion={
            <Link to="/objetos/nuevo" className={buttonVariants()}>
              Registrar objeto
            </Link>
          }
        />
      ) : (
        <>
          <BuscadorEnPlano
            plano={plano.data}
            onElegir={(u) => {
              setParams({ almacen: almacenId ?? "", objeto: u.objeto.object_id });
              setSeleccion({ pasillo: u.pasillo, anaquel: u.anaquel });
              encender(u.objeto);
              panel.current?.scrollIntoView({ block: "nearest", behavior: "smooth" });
            }}
          />

          {ubicacion && (
            <section
              aria-live="polite"
              className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-primary/50 bg-primary/5 p-4"
            >
              <p className="flex min-w-0 items-center gap-2 text-sm">
                <MapPinned className="size-4 shrink-0 text-primary" aria-hidden />
                <span className="min-w-0">
                  <strong className="font-semibold">{ubicacion.objeto.nombre}</strong> está en pasillo{" "}
                  {ubicacion.pasillo}, anaquel {ubicacion.anaquel}, nivel {ubicacion.nivel}, columna{" "}
                  {ubicacion.columna}
                </span>
              </p>
              <div className="flex shrink-0 items-center gap-3">
                {ledDelBuscado ? (
                  <span className="text-sm text-muted-foreground tabular">
                    Se apaga en {Math.ceil(ledDelBuscado.segundos_restantes)} s
                  </span>
                ) : (
                  <Button size="sm" onClick={() => encender(ubicacion.objeto)} disabled={localizar.isPending}>
                    <Lightbulb className="size-4" aria-hidden />
                    Encender LED
                  </Button>
                )}
                <Link
                  to={`/objetos/${encodeURIComponent(ubicacion.objeto.object_id)}`}
                  className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
                >
                  Ver ficha
                </Link>
              </div>
            </section>
          )}

          {DEMO_LOCAL && (
            <details className="group rounded-xl border bg-card p-4 shadow-xs">
              <summary className="flex cursor-pointer flex-wrap items-center gap-2 text-sm font-medium">
                <Cpu className="size-4 text-muted-foreground" aria-hidden />
                Ver la tira completa del nodo
                <span className="flex items-center gap-1.5 text-xs font-normal text-muted-foreground">
                  <span
                    className={cn(
                      "size-2 rounded-full",
                      escuchando ? "animate-pulse bg-success" : "bg-muted-foreground/50",
                    )}
                    aria-hidden
                  />
                  {escuchando ? "conectado" : "sin conexión"}
                </span>
              </summary>
              <div className="mt-4 grid gap-3">
                {totalLeds ? (
                  <TiraLed total={totalLeds} activos={[...encendidos.values()]} />
                ) : (
                  <Skeleton className="h-28" />
                )}
                <p className="flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-muted-foreground">
                  Esto es lo que recibe el nodo ESP32 del almacén.
                  {topic && <code className="rounded bg-muted px-1.5 py-0.5 font-mono">{topic}</code>}
                  <Link to="/simulador" className="underline underline-offset-4 hover:text-foreground">
                    Abrir el simulador completo
                  </Link>
                </p>
              </div>
            </details>
          )}

          <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1fr)_440px]">
            <PlantaAlmacen
              plano={plano.data}
              seleccion={seleccionEfectiva}
              objetoBuscado={objetoBuscado}
              encendidos={encendidos}
              onSeleccionar={setSeleccion}
            />

            <div ref={panel}>
              {anaquelAbierto && seleccionEfectiva ? (
                <AnaquelAlzado
                  pasillo={seleccionEfectiva.pasillo}
                  anaquel={anaquelAbierto}
                  encendidos={encendidos}
                  objetoBuscado={objetoBuscado}
                  encendiendoId={localizar.isPending ? (localizar.variables?.id ?? null) : null}
                  onEncender={encender}
                />
              ) : (
                <EmptyState
                  icono={Boxes}
                  titulo="Elige un anaquel"
                  descripcion="Toca un anaquel del plano para ver sus niveles y encender el LED de lo que guarda."
                />
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
