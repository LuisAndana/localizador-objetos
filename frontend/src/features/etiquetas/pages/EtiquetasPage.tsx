import { useEffect, useState } from "react";
import { Link } from "react-router";
import { AlertCircle, PackageSearch, Printer } from "lucide-react";
import QRCode from "qrcode";
import { cn } from "cn";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { EmptyState } from "@/shared/components/EmptyState";
import { PageHeader } from "@/shared/components/PageHeader";
import { useCatalogo } from "@/features/objetos/api";
import type { Objeto } from "@/features/objetos/tipos";

const claseChip = (activo: boolean) =>
  cn(
    "inline-flex h-11 shrink-0 items-center rounded-full border px-4 text-sm font-medium transition-colors md:h-9",
    activo
      ? "border-primary bg-primary text-primary-foreground"
      : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
  );

/** El QR lleva a la ficha del objeto: cualquier cámara de teléfono la abre. */
function enlaceDelObjeto(objeto: Objeto) {
  return `${window.location.origin}/objetos/${encodeURIComponent(objeto.object_id)}`;
}

function CodigoQr({ valor }: { valor: string }) {
  const [imagen, setImagen] = useState<string | null>(null);

  useEffect(() => {
    let vigente = true;
    QRCode.toDataURL(valor, { margin: 0, width: 220, errorCorrectionLevel: "M" })
      .then((url) => {
        if (vigente) setImagen(url);
      })
      .catch(() => {
        if (vigente) setImagen(null);
      });
    return () => {
      vigente = false;
    };
  }, [valor]);

  if (!imagen) return <div className="size-[88px] shrink-0 rounded bg-muted" aria-hidden />;
  return <img src={imagen} alt="" className="size-[88px] shrink-0" />;
}

function Etiqueta({ objeto }: { objeto: Objeto }) {
  return (
    <article className="flex break-inside-avoid items-center gap-3 rounded-lg border border-foreground/25 bg-card p-3">
      <CodigoQr valor={enlaceDelObjeto(objeto)} />
      <div className="min-w-0 flex-1">
        <p className="truncate font-semibold leading-tight" title={objeto.nombre}>
          {objeto.nombre}
        </p>
        <p className="mt-1 text-sm">
          Pasillo {objeto.pasillo} · Anaquel {objeto.anaquel} · Nivel {objeto.nivel} · Columna {objeto.columna}
        </p>
        <p className="mt-0.5 text-xs text-muted-foreground">
          {objeto.almacen_id} · <span className="font-mono">{objeto.object_id}</span>
        </p>
      </div>
    </article>
  );
}

export default function EtiquetasPage() {
  const catalogo = useCatalogo(true);
  const [almacen, setAlmacen] = useState<string | null>(null);

  const objetos = catalogo.data ?? [];
  const almacenes = [...new Set(objetos.map((o) => o.almacen_id))].sort();
  const visibles = almacen ? objetos.filter((o) => o.almacen_id === almacen) : objetos;

  return (
    <div className="grid gap-6">
      <div className="no-imprimir grid gap-6">
        <PageHeader
          titulo="Etiquetas para imprimir"
          descripcion="Una etiqueta por objeto, con su código QR y su ubicación. Pégalas en el material: al escanearlas se abre su ficha."
          accion={
            <Button onClick={() => window.print()} disabled={visibles.length === 0}>
              <Printer className="size-4" aria-hidden />
              Imprimir
            </Button>
          }
        />

        {almacenes.length > 1 && (
          <div role="group" aria-label="Elegir almacén" className="flex flex-wrap gap-2">
            <button type="button" aria-pressed={!almacen} onClick={() => setAlmacen(null)} className={claseChip(!almacen)}>
              Todos
            </button>
            {almacenes.map((id) => (
              <button
                key={id}
                type="button"
                aria-pressed={almacen === id}
                onClick={() => setAlmacen(id)}
                className={claseChip(almacen === id)}
              >
                {id}
              </button>
            ))}
          </div>
        )}
      </div>

      {catalogo.isPending ? (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
      ) : catalogo.isError ? (
        <EmptyState
          icono={AlertCircle}
          titulo="No se pudieron cargar los objetos"
          descripcion="No hubo respuesta del servidor. Vuelve a intentarlo en un momento."
          accion={
            <Button variant="outline" onClick={() => catalogo.refetch()}>
              Reintentar
            </Button>
          }
        />
      ) : visibles.length === 0 ? (
        <EmptyState
          icono={PackageSearch}
          titulo="No hay nada que etiquetar"
          descripcion="Registra un objeto y aquí aparecerá su etiqueta lista para imprimir."
          accion={
            <Link to="/objetos/nuevo" className={buttonVariants()}>
              Registrar objeto
            </Link>
          }
        />
      ) : (
        <div className="hoja-etiquetas grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {visibles.map((objeto) => (
            <Etiqueta key={objeto.object_id} objeto={objeto} />
          ))}
        </div>
      )}
    </div>
  );
}
