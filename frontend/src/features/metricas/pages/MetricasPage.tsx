import { useState } from "react";
import { AlertCircle, Check, Gauge, Timer, TrendingDown } from "lucide-react";
import { cn } from "cn";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { EmptyState } from "@/shared/components/EmptyState";
import { PageHeader } from "@/shared/components/PageHeader";
import { formatearDuracion, formatearFecha } from "@/shared/lib/formato";
import { useObjetos } from "@/features/objetos/api";
import { useMetricas, useRegistrarMedicionManual, type Estadisticas } from "../api";

function TarjetaTiempo({
  titulo,
  descripcion,
  datos,
  acento,
}: {
  titulo: string;
  descripcion: string;
  datos: Estadisticas;
  acento: "muted" | "primary";
}) {
  return (
    <section
      className={cn(
        "grid gap-3 rounded-xl border bg-card p-5 shadow-xs",
        acento === "primary" && "border-primary/50",
      )}
    >
      <div className="space-y-1">
        <h2 className="font-semibold">{titulo}</h2>
        <p className="text-sm text-muted-foreground">{descripcion}</p>
      </div>
      <p className="text-3xl font-semibold tabular">
        {datos.muestras ? formatearDuracion(datos.promedio_ms) : "—"}
      </p>
      <dl className="grid grid-cols-3 gap-2 border-t pt-3 text-sm">
        {[
          ["Mediciones", String(datos.muestras)],
          ["Mediana", datos.muestras ? formatearDuracion(datos.mediana_ms) : "—"],
          ["P90", datos.muestras ? formatearDuracion(datos.p90_ms) : "—"],
        ].map(([etiqueta, valor]) => (
          <div key={etiqueta}>
            <dt className="text-xs text-muted-foreground">{etiqueta}</dt>
            <dd className="font-medium tabular">{valor}</dd>
          </div>
        ))}
      </dl>
    </section>
  );
}

function Resultado({ reduccion, meta, cumple }: { reduccion: number | null; meta: number; cumple: boolean | null }) {
  if (reduccion === null) {
    return (
      <section className="flex items-start gap-3 rounded-xl border border-dashed p-5">
        <Gauge className="mt-0.5 size-5 shrink-0 text-muted-foreground" aria-hidden />
        <div className="space-y-1">
          <h2 className="font-semibold">Todavía no se puede calcular</h2>
          <p className="text-sm text-muted-foreground">
            Hacen falta mediciones de los dos métodos: busca objetos con el sistema y registra abajo
            cuánto tardaban a mano. Con ambas muestras aparece aquí el porcentaje de reducción.
          </p>
        </div>
      </section>
    );
  }

  return (
    <section
      aria-live="polite"
      className={cn(
        "flex flex-wrap items-center justify-between gap-4 rounded-xl border p-5",
        cumple ? "border-success/50 bg-success/5" : "border-warning/50 bg-warning/5",
      )}
    >
      <div className="flex items-center gap-3">
        <span
          className={cn(
            "grid size-11 place-items-center rounded-lg",
            cumple ? "bg-success/15 text-success" : "bg-warning/15 text-warning",
          )}
          aria-hidden
        >
          {cumple ? <Check className="size-5" /> : <TrendingDown className="size-5" />}
        </span>
        <div>
          <p className="text-2xl font-semibold tabular">{reduccion} % menos tiempo</p>
          <p className="text-sm text-muted-foreground">
            {cumple ? "La meta del acta se cumple" : `Todavía por debajo de la meta`} · meta {meta} %
          </p>
        </div>
      </div>
    </section>
  );
}

export default function MetricasPage() {
  const metricas = useMetricas();
  const objetos = useObjetos();
  const registrar = useRegistrarMedicionManual();
  const [objectId, setObjectId] = useState("");
  const [segundos, setSegundos] = useState(60);

  const opciones = objetos.data?.pages.flatMap((p) => p.elementos) ?? [];
  const seleccionado = objectId || opciones[0]?.object_id || "";

  const enviar = () =>
    registrar.mutate(
      { object_id: seleccionado, duracion_ms: Math.round(segundos * 1000) },
      { onSuccess: () => setSegundos(60) },
    );

  if (metricas.isError) {
    return (
      <EmptyState
        icono={AlertCircle}
        titulo="No se pudieron cargar las métricas"
        descripcion={metricas.error.message}
        accion={
          <Button variant="outline" onClick={() => metricas.refetch()}>
            Reintentar
          </Button>
        }
      />
    );
  }

  return (
    <div className="grid gap-6">
      <PageHeader
        titulo="Tiempo de localización"
        descripcion="El indicador del acta: reducir 40 % el tiempo de encontrar un material. El cronómetro arranca al pulsar Localizar y se detiene cuando el operador confirma o registra la salida."
      />

      {metricas.isPending ? (
        <Skeleton className="h-24" />
      ) : (
        <Resultado
          reduccion={metricas.data.reduccion_pct}
          meta={metricas.data.meta_pct}
          cumple={metricas.data.cumple_meta}
        />
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {metricas.isPending ? (
          <>
            <Skeleton className="h-48" />
            <Skeleton className="h-48" />
          </>
        ) : (
          <>
            <TarjetaTiempo
              titulo="Método manual"
              descripcion="Buscar sin el sistema, cronometrado a mano."
              datos={metricas.data.manual}
              acento="muted"
            />
            <TarjetaTiempo
              titulo="Con el sistema"
              descripcion="Desde Localizar hasta la confirmación del retiro."
              datos={metricas.data.con_sistema}
              acento="primary"
            />
          </>
        )}
      </div>

      <section className="grid gap-4 rounded-xl border bg-card p-5 shadow-xs">
        <div className="space-y-1">
          <h2 className="font-semibold">Registrar una medición manual</h2>
          <p className="text-sm text-muted-foreground">
            Cronometren una búsqueda sin el sistema y captúrenla aquí. Son las mediciones de
            referencia contra las que se compara.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-[1fr_8rem_auto] sm:items-end">
          <div className="grid gap-1.5">
            <label htmlFor="objeto-medicion" className="text-xs font-medium text-muted-foreground">
              Objeto
            </label>
            <select
              id="objeto-medicion"
              value={seleccionado}
              onChange={(e) => setObjectId(e.target.value)}
              className="h-11 w-full rounded-lg border bg-background px-3 text-sm md:h-9"
            >
              {opciones.map((o) => (
                <option key={o.object_id} value={o.object_id}>
                  {o.nombre}
                </option>
              ))}
            </select>
          </div>
          <div className="grid gap-1.5">
            <label htmlFor="segundos-medicion" className="text-xs font-medium text-muted-foreground">
              Segundos
            </label>
            <Input
              id="segundos-medicion"
              type="number"
              min={1}
              max={3600}
              value={segundos}
              onChange={(e) => setSegundos(Math.max(1, Number(e.target.value) || 1))}
              className="tabular"
            />
          </div>
          <Button onClick={enviar} disabled={registrar.isPending || !seleccionado}>
            <Timer className="size-4" aria-hidden />
            Registrar
          </Button>
        </div>
      </section>

      {metricas.data && metricas.data.recientes.length > 0 && (
        <section className="grid gap-3">
          <h2 className="font-semibold">Últimas mediciones</h2>
          <ul className="grid gap-2">
            {metricas.data.recientes.map((b) => (
              <li
                key={b.busqueda_id}
                className="flex items-center justify-between gap-3 rounded-lg border bg-card p-3 text-sm"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className={cn(
                      "rounded-full px-2 py-0.5 text-xs font-medium",
                      b.modo === "sistema"
                        ? "bg-primary/10 text-primary"
                        : "bg-muted text-muted-foreground",
                    )}
                  >
                    {b.modo === "sistema" ? "Con el sistema" : "Manual"}
                  </span>
                  <span className="truncate text-muted-foreground">{b.object_id}</span>
                </span>
                <span className="flex shrink-0 items-center gap-3">
                  <span className="font-semibold tabular">{formatearDuracion(b.duracion_ms)}</span>
                  <span className="hidden text-xs text-muted-foreground sm:inline">
                    {formatearFecha(b.confirmada_en)}
                  </span>
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {metricas.data && metricas.data.busquedas_abiertas > 0 && (
        <p className="rounded-lg bg-muted/60 p-3 text-sm text-muted-foreground">
          Hay {metricas.data.busquedas_abiertas} búsqueda
          {metricas.data.busquedas_abiertas === 1 ? "" : "s"} sin confirmar. No entran al promedio
          hasta que alguien confirme el hallazgo o registre la salida del material.
        </p>
      )}
    </div>
  );
}
