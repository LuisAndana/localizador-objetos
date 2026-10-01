import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";
import {
  AlertCircle,
  ArrowDownToLine,
  ArrowLeft,
  ArrowUpFromLine,
  Check,
  Cpu,
  Lightbulb,
  Loader2,
  MapPinned,
  PackageSearch,
  Pencil,
  Trash2,
} from "lucide-react";
import { cn } from "cn";
import { ApiError } from "@/core/api/client";
import { useEsAdministrador } from "@/core/auth/useSesion";
import { DEMO_LOCAL } from "@/core/config";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { EmptyState } from "@/shared/components/EmptyState";
import { PuntoColor } from "@/shared/components/PuntoColor";
import { TiraSegmento } from "@/shared/components/TiraLed";
import { useRestante } from "@/shared/hooks/useRestante";
import { formatearFecha } from "@/shared/lib/formato";
import { nombreDeCategoria, useCategorias } from "@/features/categorias/api";
import { Input } from "@/shared/components/ui/input";
import { useConfirmarBusqueda } from "@/features/metricas/api";
import { useEliminarObjeto, useLocalizar, useMovimientos, useObjeto, useRegistrarMovimiento } from "../api";
import type { Objeto, RespuestaLocalizar, TipoMovimiento } from "../tipos";

const DURACIONES = [15, 30, 60];

function DetalleCargando() {
  return (
    <div className="grid gap-6" aria-busy="true">
      <Skeleton className="h-9 w-28" />
      <Skeleton className="h-8 w-72 max-w-full" />
      <div className="grid gap-4 md:grid-cols-5">
        <Skeleton className="h-56 md:col-span-3" />
        <Skeleton className="h-56 md:col-span-2" />
      </div>
    </div>
  );
}

function PanelMovimientos({ objeto }: { objeto: Objeto }) {
  const [cantidad, setCantidad] = useState(1);
  const [motivo, setMotivo] = useState("");
  const movimientos = useMovimientos(objeto.object_id);
  const registrar = useRegistrarMovimiento(objeto.object_id);

  const registrarMovimiento = (tipo: TipoMovimiento) =>
    registrar.mutate(
      { tipo, cantidad, motivo: motivo.trim() || undefined },
      {
        onSuccess: () => {
          setCantidad(1);
          setMotivo("");
        },
      },
    );

  return (
    <section className="grid gap-4 rounded-xl border bg-card p-5 shadow-xs">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="text-lg font-semibold">Entradas y salidas</h2>
          <p className="text-sm text-muted-foreground">
            Cada movimiento ajusta las existencias en el momento.
          </p>
        </div>
        <div className="rounded-lg bg-muted/60 px-3 py-2 text-center">
          <span className="block text-xs font-medium text-muted-foreground">En existencia</span>
          <span className="text-2xl font-semibold tabular" aria-live="polite">
            {objeto.cantidad}
          </span>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-[7rem_1fr] sm:items-end">
        <div className="grid gap-1.5">
          <label htmlFor="cantidad-movimiento" className="text-xs font-medium text-muted-foreground">
            Cantidad
          </label>
          <Input
            id="cantidad-movimiento"
            type="number"
            min={1}
            max={10000}
            value={cantidad}
            onChange={(e) => setCantidad(Math.max(1, Number(e.target.value) || 1))}
            className="tabular"
          />
        </div>
        <div className="grid gap-1.5">
          <label htmlFor="motivo-movimiento" className="text-xs font-medium text-muted-foreground">
            Motivo <span className="font-normal">(opcional)</span>
          </label>
          <Input
            id="motivo-movimiento"
            value={motivo}
            maxLength={120}
            placeholder="Pedido 118, devolución, ajuste de inventario…"
            onChange={(e) => setMotivo(e.target.value)}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <Button
          variant="outline"
          onClick={() => registrarMovimiento("entrada")}
          disabled={registrar.isPending}
        >
          {registrar.isPending ? (
            <Loader2 className="size-4 animate-spin" aria-hidden />
          ) : (
            <ArrowDownToLine className="size-4" aria-hidden />
          )}
          Registrar entrada
        </Button>
        <Button
          variant="outline"
          onClick={() => registrarMovimiento("salida")}
          disabled={registrar.isPending || objeto.cantidad === 0}
          title={objeto.cantidad === 0 ? "No hay existencias que sacar" : undefined}
        >
          <ArrowUpFromLine className="size-4" aria-hidden />
          Registrar salida
        </Button>
      </div>

      <div className="grid gap-2 border-t pt-4">
        <h3 className="text-sm font-semibold">Historial</h3>
        {movimientos.isPending ? (
          <Skeleton className="h-20" />
        ) : movimientos.data && movimientos.data.length > 0 ? (
          <ul className="grid gap-2">
            {movimientos.data.map((m) => (
              <li
                key={m.movimiento_id}
                className="flex items-center justify-between gap-3 rounded-lg border p-2.5 text-sm"
              >
                <span className="flex min-w-0 items-center gap-2">
                  <span
                    className={cn(
                      "grid size-7 shrink-0 place-items-center rounded-md",
                      m.tipo === "entrada" ? "bg-success/15 text-success" : "bg-warning/15 text-warning",
                    )}
                    aria-hidden
                  >
                    {m.tipo === "entrada" ? (
                      <ArrowDownToLine className="size-4" />
                    ) : (
                      <ArrowUpFromLine className="size-4" />
                    )}
                  </span>
                  <span className="font-semibold tabular">
                    {m.tipo === "entrada" ? "+" : "−"}
                    {m.cantidad}
                  </span>
                  {m.motivo && <span className="truncate text-muted-foreground">{m.motivo}</span>}
                </span>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatearFecha(m.registrado_en)}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-muted-foreground">
            Todavía no hay movimientos registrados para este objeto.
          </p>
        )}
      </div>
    </section>
  );
}

function PanelEliminar({ objeto, alEliminar }: { objeto: Objeto; alEliminar: () => void }) {
  const navigate = useNavigate();
  const eliminar = useEliminarObjeto(objeto.object_id);
  const [confirmando, setConfirmando] = useState(false);
  const conExistencias = objeto.cantidad > 0;

  return (
    <section className="grid gap-3 rounded-xl border border-destructive/30 p-5">
      <div className="space-y-1">
        <h2 className="font-semibold">Eliminar del catálogo</h2>
        <p className="text-sm text-muted-foreground">
          {conExistencias
            ? `Aún quedan ${objeto.cantidad} en existencia. Registra su salida antes de eliminarlo, para que el inventario no pierda material real.`
            : "Su posición de LED queda libre. El historial de entradas, salidas y búsquedas se conserva."}
        </p>
      </div>
      {confirmando ? (
        <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Confirmar eliminación">
          <span className="text-sm font-medium">¿Eliminar “{objeto.nombre}”? No se puede deshacer.</span>
          <Button
            variant="destructive"
            disabled={eliminar.isPending}
            onClick={() =>
              eliminar.mutate(undefined, {
                onSuccess: () => {
                  alEliminar();
                  navigate("/objetos", { replace: true });
                },
              })
            }
          >
            {eliminar.isPending && <Loader2 className="size-4 animate-spin" aria-hidden />}
            Sí, eliminar
          </Button>
          <Button variant="ghost" onClick={() => setConfirmando(false)} disabled={eliminar.isPending}>
            Cancelar
          </Button>
        </div>
      ) : (
        <Button
          variant="destructive"
          className="justify-self-start"
          disabled={conExistencias}
          onClick={() => setConfirmando(true)}
        >
          <Trash2 className="size-4" aria-hidden />
          Eliminar objeto
        </Button>
      )}
    </section>
  );
}

export default function DetallePage() {
  const { id = "" } = useParams();
  // Tras eliminarlo, la consulta se apaga: si no, la página (aún montada mientras
  // navega) volvería a pedir el objeto y recibiría un 404.
  const [eliminado, setEliminado] = useState(false);
  const consulta = useObjeto(id, !eliminado);
  const categorias = useCategorias();
  const localizar = useLocalizar(id);
  const [duracion, setDuracion] = useState(30);
  const [ultima, setUltima] = useState<{ respuesta: RespuestaLocalizar; hasta: number } | null>(null);
  const [confirmada, setConfirmada] = useState<string | null>(null);
  const restante = useRestante(ultima?.hasta ?? null);
  const confirmar = useConfirmarBusqueda();
  const esAdministrador = useEsAdministrador();

  if (consulta.isPending) return <DetalleCargando />;

  if (consulta.isError) {
    const noExiste = consulta.error instanceof ApiError && consulta.error.status === 404;
    return (
      <EmptyState
        icono={noExiste ? PackageSearch : AlertCircle}
        titulo={noExiste ? "Este objeto no existe" : "No se pudo cargar el objeto"}
        descripcion={
          noExiste ? "Puede que el enlace esté mal escrito o que el código haya cambiado." : consulta.error.message
        }
        accion={
          noExiste ? (
            <Link to="/objetos" className={buttonVariants({ variant: "outline" })}>
              Ver todos los objetos
            </Link>
          ) : (
            <Button variant="outline" onClick={() => consulta.refetch()}>
              Reintentar
            </Button>
          )
        }
      />
    );
  }

  const objeto = consulta.data;
  const encendido = ultima !== null && restante > 0;
  const ubicacion = [
    ["Almacén", objeto.almacen_id],
    ["Pasillo", objeto.pasillo],
    ["Anaquel", objeto.anaquel],
    ["Nivel", objeto.nivel],
  ];

  const encender = () =>
    localizar.mutate(duracion, {
      onSuccess: (respuesta) =>
        setUltima({ respuesta, hasta: Date.now() + respuesta.orden_led.duracion_segundos * 1000 }),
    });

  return (
    <div className="grid gap-6">
      <Link
        to="/objetos"
        className={cn(buttonVariants({ variant: "ghost" }), "-ml-3 justify-self-start text-muted-foreground")}
      >
        <ArrowLeft className="size-4" aria-hidden />
        Objetos
      </Link>

      <header className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-2">
          <h1 className="text-2xl font-semibold tracking-tight">{objeto.nombre}</h1>
          <div className="flex flex-wrap items-center gap-2">
            <span className="rounded-full bg-secondary px-2.5 py-0.5 text-xs font-medium text-secondary-foreground">
              {nombreDeCategoria(categorias.data, objeto.categoria)}
            </span>
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <Link
            to={`/?almacen=${encodeURIComponent(objeto.almacen_id)}&objeto=${encodeURIComponent(objeto.object_id)}`}
            className={cn(buttonVariants({ variant: "outline" }), "self-start")}
          >
            <MapPinned className="size-4" aria-hidden />
            Ver en el mapa
          </Link>
          <Link
            to={`/objetos/${encodeURIComponent(objeto.object_id)}/editar`}
            className={cn(buttonVariants({ variant: "outline" }), "self-start")}
          >
            <Pencil className="size-4" aria-hidden />
            Editar ubicación
          </Link>
        </div>
      </header>

      <div className="grid gap-4 md:grid-cols-5">
        <section className="rounded-xl border bg-card p-5 shadow-xs md:col-span-3">
          <h2 className="text-lg font-semibold">Ubicación</h2>
          <dl className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
            {ubicacion.map(([etiqueta, valor]) => (
              <div key={etiqueta} className="min-w-0 rounded-lg bg-muted/60 p-3">
                <dt className="text-xs font-medium text-muted-foreground">{etiqueta}</dt>
                <dd className="mt-1 truncate text-lg font-semibold tabular" title={valor}>
                  {valor}
                </dd>
              </div>
            ))}
          </dl>
          <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t pt-4 text-sm">
            <span className="flex items-center gap-2 text-xs text-muted-foreground">
              <PuntoColor color={objeto.color_indicador} />
              Luz de este objeto: posición <span className="tabular">{objeto.posicion_led}</span> de la tira
            </span>
            <span className="text-xs text-muted-foreground">
              Actualizado {formatearFecha(objeto.ultima_actualizacion)}
            </span>
          </div>
        </section>

        <section className="flex flex-col gap-4 rounded-xl border bg-card p-5 shadow-xs md:col-span-2">
          <div className="space-y-1">
            <h2 className="text-lg font-semibold">Localizar físicamente</h2>
            <p className="text-sm text-muted-foreground">Enciende el LED del anaquel donde está este objeto.</p>
          </div>
          <fieldset>
            <legend className="mb-2 text-xs font-medium text-muted-foreground">Tiempo encendido</legend>
            <div className="grid grid-cols-3 gap-1 rounded-lg bg-muted p-1">
              {DURACIONES.map((s) => (
                <button
                  key={s}
                  type="button"
                  aria-pressed={duracion === s}
                  onClick={() => setDuracion(s)}
                  className={cn(
                    "h-11 rounded-md text-sm font-medium tabular transition-colors md:h-8",
                    duracion === s
                      ? "bg-background text-foreground shadow-xs"
                      : "text-muted-foreground hover:text-foreground",
                  )}
                >
                  {s} s
                </button>
              ))}
            </div>
          </fieldset>
          <Button className="mt-auto w-full" onClick={encender} disabled={localizar.isPending}>
            {localizar.isPending ? (
              <Loader2 className="size-4 animate-spin" aria-hidden />
            ) : (
              <Lightbulb className="size-4" aria-hidden />
            )}
            {encendido ? "Encender otra vez" : "Localizar"}
          </Button>
        </section>
      </div>

      <PanelMovimientos objeto={objeto} />

      {ultima && (
        <section
          key={ultima.hasta}
          aria-live="polite"
          className="grid gap-4 rounded-xl border bg-card p-5 shadow-xs animate-in fade-in-0 slide-in-from-bottom-2 duration-200"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <span
                className={cn("size-2.5 rounded-full", encendido ? "animate-pulse bg-success" : "bg-muted-foreground/40")}
                aria-hidden
              />
              <h2 className="font-semibold">
                {encendido ? `LED #${ultima.respuesta.orden_led.posicion_led} encendido` : "El LED ya se apagó"}
              </h2>
            </div>
            {encendido && <span className="text-sm text-muted-foreground tabular">Se apaga en {restante} s</span>}
          </div>

          <TiraSegmento
            centro={ultima.respuesta.orden_led.posicion_led}
            color={ultima.respuesta.orden_led.color_indicador}
            encendido={encendido}
          />

          <p className="text-sm text-muted-foreground">
            Busca la luz en{" "}
            <strong className="font-medium text-foreground">
              pasillo {ultima.respuesta.ubicacion.pasillo}, anaquel {ultima.respuesta.ubicacion.anaquel}, nivel{" "}
              {ultima.respuesta.ubicacion.nivel}
            </strong>{" "}
            de {ultima.respuesta.ubicacion.almacen_id}. Orden publicada en{" "}
            <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">{ultima.respuesta.topic}</code>.
          </p>

          <div className="flex flex-wrap gap-2">
            {/* Detiene el cronómetro del indicador de tiempo. La otra forma de
                cerrarlo es registrar la salida del material. */}
            <Button
              variant="outline"
              onClick={() =>
                confirmar.mutate(ultima.respuesta.busqueda_id, {
                  onSuccess: () => setConfirmada(ultima.respuesta.busqueda_id),
                })
              }
              disabled={confirmar.isPending || confirmada === ultima.respuesta.busqueda_id}
            >
              <Check className="size-4" aria-hidden />
              {confirmada === ultima.respuesta.busqueda_id ? "Hallazgo confirmado" : "Ya lo encontré"}
            </Button>

            {DEMO_LOCAL && (
              <Link
                to={`/simulador?almacen=${encodeURIComponent(ultima.respuesta.ubicacion.almacen_id)}`}
                className={buttonVariants({ variant: "outline" })}
              >
                <Cpu className="size-4" aria-hidden />
                Ver la tira completa en el simulador
              </Link>
            )}
          </div>
        </section>
      )}

      {esAdministrador && <PanelEliminar objeto={objeto} alEliminar={() => setEliminado(true)} />}
    </div>
  );
}
