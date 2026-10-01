import { Link, useSearchParams } from "react-router";
import { AlertCircle, Info, LightbulbOff } from "lucide-react";
import { cn } from "cn";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { EmptyState } from "@/shared/components/EmptyState";
import { PageHeader } from "@/shared/components/PageHeader";
import { PuntoColor } from "@/shared/components/PuntoColor";
import { TiraLed } from "@/shared/components/TiraLed";
import { useAlmacenes, useEstadoTira } from "../api";

const claseChip = (activo: boolean) =>
  cn(
    "inline-flex h-11 shrink-0 items-center gap-2 rounded-full border px-4 text-sm font-medium transition-colors md:h-9",
    activo
      ? "border-primary bg-primary text-primary-foreground"
      : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
  );

export default function SimuladorPage() {
  const [params, setParams] = useSearchParams();
  const almacenes = useAlmacenes();
  const seleccionado = params.get("almacen") ?? almacenes.data?.[0]?.almacen_id;
  const tira = useEstadoTira(seleccionado);
  const activos = tira.data?.activos ?? [];

  return (
    <div className="grid gap-6">
      <PageHeader
        titulo="Simulador del nodo ESP32"
        descripcion="Así vería su tira WS2812B el nodo de cada almacén. En producción, este papel lo cumple el ESP32 real suscrito a AWS IoT Core."
      />

      <div role="group" aria-label="Elegir almacén" className="-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none] md:mx-0 md:px-0 [&::-webkit-scrollbar]:hidden">
        {almacenes.isPending
          ? Array.from({ length: 2 }, (_, i) => <Skeleton key={i} className="h-11 w-36 shrink-0 rounded-full md:h-9" />)
          : almacenes.data?.map((a) => (
              <button
                key={a.almacen_id}
                type="button"
                aria-pressed={seleccionado === a.almacen_id}
                onClick={() => setParams({ almacen: a.almacen_id })}
                className={claseChip(seleccionado === a.almacen_id)}
              >
                {a.almacen_id}
                <span className="text-xs opacity-70 tabular">{a.total_objetos} obj.</span>
              </button>
            ))}
      </div>

      {almacenes.isError ? (
        <EmptyState
          icono={AlertCircle}
          titulo="El simulador no responde"
          descripcion="Solo funciona con el backend local encendido (python -m uvicorn main:app --reload)."
          accion={
            <Button variant="outline" onClick={() => almacenes.refetch()}>
              Reintentar
            </Button>
          }
        />
      ) : (
        <section className="grid gap-4 rounded-xl border bg-card p-4 shadow-xs sm:p-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="flex items-center gap-2 font-medium">
                <span
                  className={cn("size-2 rounded-full", tira.isError ? "bg-destructive" : "animate-pulse bg-success")}
                  aria-hidden
                />
                {tira.isError ? "Sin conexión" : "Escuchando"}
              </span>
              {tira.data && (
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{tira.data.topic}</code>
              )}
            </div>
            {tira.data && (
              <span className="text-sm text-muted-foreground tabular">
                {activos.length} encendido{activos.length === 1 ? "" : "s"} · {tira.data.total_leds} LEDs
              </span>
            )}
          </div>

          {tira.data ? <TiraLed total={tira.data.total_leds} activos={activos} /> : <Skeleton className="h-40" />}
        </section>
      )}

      {tira.data &&
        (activos.length === 0 ? (
          <EmptyState
            icono={LightbulbOff}
            titulo="La tira está apagada"
            descripcion="Abre un objeto de este almacén y pulsa Localizar: su LED se encenderá aquí en menos de un segundo."
            accion={
              <Link to="/objetos" className={buttonVariants()}>
                Ir a objetos
              </Link>
            }
          />
        ) : (
          <section className="grid gap-3" aria-live="polite">
            <h2 className="font-semibold">Órdenes activas</h2>
            <ul className="grid gap-2">
              {activos.map((a) => (
                <li key={a.posicion_led}>
                  <Link
                    to={`/objetos/${encodeURIComponent(a.object_id)}`}
                    className="grid gap-2 rounded-lg border bg-card p-3 shadow-xs transition-colors hover:bg-muted/30"
                  >
                    <div className="flex items-center justify-between gap-3 text-sm">
                      <span className="flex min-w-0 items-center gap-2">
                        <PuntoColor color={a.color_indicador} />
                        <span className="font-semibold tabular">LED #{a.posicion_led}</span>
                        <span className="truncate text-muted-foreground">{a.nombre ?? a.object_id}</span>
                      </span>
                      <span className="shrink-0 text-muted-foreground tabular">{Math.ceil(a.segundos_restantes)} s</span>
                    </div>
                    <div className="h-1.5 overflow-hidden rounded-full bg-muted">
                      <div
                        className="h-full rounded-full transition-[width] duration-1000 ease-linear"
                        style={{
                          width: `${Math.min(100, (a.segundos_restantes / a.duracion_segundos) * 100)}%`,
                          backgroundColor: a.color_indicador,
                        }}
                      />
                    </div>
                  </Link>
                </li>
              ))}
            </ul>
          </section>
        ))}

      <p className="flex gap-2 rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
        <Info className="mt-0.5 size-4 shrink-0" aria-hidden />
        Prueba: abre esta pantalla en otra pestaña (o en tu teléfono) y localiza un objeto desde la otra. Verás el LED
        encenderse aquí, igual que en el anaquel.
      </p>
    </div>
  );
}
