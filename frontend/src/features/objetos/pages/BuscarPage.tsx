import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { AlertCircle, Loader2, PackageSearch, Plus, Printer, Search, Tags } from "lucide-react";
import { cn } from "cn";
import { Button, buttonVariants } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { EmptyState } from "@/shared/components/EmptyState";
import { PageHeader } from "@/shared/components/PageHeader";
import { PuntoColor } from "@/shared/components/PuntoColor";
import { ResponsiveList, type Columna } from "@/shared/components/ResponsiveList";
import { useDebounced } from "@/shared/hooks/useDebounced";
import { nombreDeCategoria, useCategorias } from "@/features/categorias/api";
import { useObjetos } from "../api";
import type { Objeto } from "../tipos";

const claseChip = (activo: boolean) =>
  cn(
    "inline-flex h-11 shrink-0 items-center rounded-full border px-4 text-sm font-medium transition-colors md:h-9",
    activo
      ? "border-primary bg-primary text-primary-foreground"
      : "bg-card text-muted-foreground hover:bg-muted hover:text-foreground",
  );

export default function BuscarPage() {
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const categoria = params.get("categoria") ?? undefined;
  const [filtro, setFiltro] = useState("");
  const texto = useDebounced(filtro.trim());

  const categorias = useCategorias();
  // El servidor busca en todo el catálogo (sin acentos ni mayúsculas), no solo
  // en la página cargada. Con un solo carácter se sigue mostrando la lista.
  const buscando = texto.length >= 2;
  const consulta = useObjetos(categoria, buscando ? texto : undefined);

  const visibles = consulta.data?.pages.flatMap((p) => p.elementos) ?? [];
  const cargando = consulta.isPending;
  const fallo = consulta.isError;

  const elegirCategoria = (id?: string) => {
    setParams(id ? { categoria: id } : {});
    setFiltro("");
  };

  const columnas: Columna<Objeto>[] = [
    {
      clave: "nombre",
      titulo: "Nombre",
      principal: true,
      celda: (o) => (
        <span className="flex items-center gap-2 font-medium">
          <PuntoColor color={o.color_indicador} />
          {o.nombre}
        </span>
      ),
    },
    { clave: "categoria", titulo: "Categoría", celda: (o) => nombreDeCategoria(categorias.data, o.categoria) },
    { clave: "almacen", titulo: "Almacén", celda: (o) => o.almacen_id },
    {
      clave: "ubicacion",
      titulo: "Ubicación",
      celda: (o) => `Pasillo ${o.pasillo} · Anaq. ${o.anaquel} · Niv. ${o.nivel}`,
    },
    {
      clave: "cantidad",
      titulo: "En existencia",
      className: "tabular md:text-right",
      celda: (o) => String(o.cantidad),
    },
  ];

  const botonRegistrar = (
    <Link to="/objetos/nuevo" className={buttonVariants()}>
      <Plus className="size-4" aria-hidden />
      Registrar objeto
    </Link>
  );

  const acciones = (
    <div className="flex flex-wrap gap-2">
      <Link to="/etiquetas" className={buttonVariants({ variant: "outline" })}>
        <Printer className="size-4" aria-hidden />
        Etiquetas
      </Link>
      {botonRegistrar}
    </div>
  );

  return (
    <div className="grid gap-6">
      <PageHeader
        titulo="Objetos"
        descripcion="Encuentra un objeto y enciende su LED en el anaquel."
        accion={acciones}
      />

      <div className="grid gap-3">
        <div
          role="group"
          aria-label="Filtrar por categoría"
          className="-mx-4 flex gap-2 overflow-x-auto px-4 [scrollbar-width:none] md:mx-0 md:flex-wrap md:px-0 [&::-webkit-scrollbar]:hidden"
        >
          <button type="button" aria-pressed={!categoria} onClick={() => elegirCategoria()} className={claseChip(!categoria)}>
            Todas
          </button>
          {categorias.isPending
            ? Array.from({ length: 4 }, (_, i) => <Skeleton key={i} className="h-11 w-28 shrink-0 rounded-full md:h-9" />)
            : categorias.data?.map((c) => (
                <button
                  key={c.categoria_id}
                  type="button"
                  aria-pressed={categoria === c.categoria_id}
                  onClick={() => elegirCategoria(c.categoria_id)}
                  className={claseChip(categoria === c.categoria_id)}
                >
                  {c.nombre}
                </button>
              ))}
          {/* Categorías salió de la navegación principal: se entra desde aquí. */}
          <Link
            to="/categorias"
            className="inline-flex h-11 shrink-0 items-center gap-1.5 rounded-full px-3 text-sm font-medium text-muted-foreground underline-offset-4 hover:text-foreground hover:underline md:h-9"
          >
            <Tags className="size-4" aria-hidden />
            Ver por categoría
          </Link>
        </div>

        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="relative w-full sm:max-w-sm">
            <Search
              className="pointer-events-none absolute top-1/2 left-3 size-4 -translate-y-1/2 text-muted-foreground"
              aria-hidden
            />
            <Input
              type="search"
              placeholder="Buscar por nombre o código…"
              aria-label="Buscar por nombre o código"
              value={filtro}
              onChange={(e) => setFiltro(e.target.value)}
              className="pl-9"
            />
          </div>
          {!cargando && !fallo && (
            <p className="text-sm text-muted-foreground tabular">
              {visibles.length} {visibles.length === 1 ? "objeto" : "objetos"}
              {consulta.hasNextPage && " en pantalla"}
            </p>
          )}
        </div>
      </div>

      {cargando ? (
        <div className="grid gap-3" aria-busy="true">
          {Array.from({ length: 6 }, (_, i) => (
            <Skeleton key={i} className="h-14 w-full" />
          ))}
        </div>
      ) : fallo ? (
        <EmptyState
          icono={AlertCircle}
          titulo="No se pudo cargar la lista"
          descripcion="No hubo respuesta del servidor. Vuelve a intentarlo en un momento."
          accion={
            <Button variant="outline" onClick={() => consulta.refetch()}>
              Reintentar
            </Button>
          }
        />
      ) : visibles.length === 0 ? (
        <EmptyState
          icono={PackageSearch}
          titulo={buscando ? "Sin coincidencias" : "Aún no hay objetos aquí"}
          descripcion={
            buscando
              ? `Ningún objeto del almacén coincide con “${texto}”.`
              : "Registra el primero para empezar a localizarlo."
          }
          accion={!buscando && botonRegistrar}
        />
      ) : (
        <>
          <ResponsiveList
            filas={visibles}
            columnas={columnas}
            obtenerId={(o) => o.object_id}
            alSeleccionar={(o) => navigate(`/objetos/${encodeURIComponent(o.object_id)}`)}
          />
          {consulta.hasNextPage && (
            <Button
              variant="outline"
              className="justify-self-center"
              onClick={() => consulta.fetchNextPage()}
              disabled={consulta.isFetchingNextPage}
            >
              {consulta.isFetchingNextPage && <Loader2 className="size-4 animate-spin" aria-hidden />}
              Cargar más
            </Button>
          )}
        </>
      )}
    </div>
  );
}
