import { useState, type FormEvent } from "react";
import { Link } from "react-router";
import {
  AlertCircle,
  ChevronRight,
  Cog,
  Cpu,
  Loader2,
  Package,
  Pencil,
  Plus,
  Tags,
  Trash2,
  Wrench,
  type LucideIcon,
} from "lucide-react";
import { useEsAdministrador } from "@/core/auth/useSesion";
import { Button } from "@/shared/components/ui/button";
import { Input } from "@/shared/components/ui/input";
import { Skeleton } from "@/shared/components/ui/skeleton";
import { Campo } from "@/shared/components/Campo";
import { EmptyState } from "@/shared/components/EmptyState";
import { PageHeader } from "@/shared/components/PageHeader";
import {
  idDesdeNombre,
  useActualizarCategoria,
  useCategorias,
  useCrearCategoria,
  useEliminarCategoria,
  type Categoria,
} from "../api";

// Iconos para las categorías de la demo; cualquier otra usa el genérico.
const ICONOS: Record<string, LucideIcon> = {
  herramientas: Wrench,
  refacciones: Cog,
  consumibles: Package,
  electronica: Cpu,
};

const REGEX_ID = /^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$/;

function FormCategoria({
  inicial,
  enviando,
  alGuardar,
  alCancelar,
}: {
  inicial?: Categoria;
  enviando: boolean;
  alGuardar: (c: Categoria) => void;
  alCancelar: () => void;
}) {
  const editando = Boolean(inicial);
  const [nombre, setNombre] = useState(inicial?.nombre ?? "");
  const [descripcion, setDescripcion] = useState(inicial?.descripcion ?? "");
  // El id se propone a partir del nombre hasta que alguien lo toque.
  const [id, setId] = useState(inicial?.categoria_id ?? "");
  const [idTocado, setIdTocado] = useState(editando);
  const idFinal = idTocado ? id : idDesdeNombre(nombre);

  const errorNombre = nombre.trim() === "" ? "Escribe un nombre." : nombre.trim().length > 60 ? "Máximo 60 caracteres." : null;
  const errorId = !editando && !REGEX_ID.test(idFinal) ? "Solo letras, números, guion y guion bajo." : null;

  const enviar = (e: FormEvent) => {
    e.preventDefault();
    if (errorNombre || errorId) return;
    alGuardar({ categoria_id: idFinal, nombre: nombre.trim(), descripcion: descripcion.trim() });
  };

  return (
    <form onSubmit={enviar} className="grid gap-4 rounded-xl border bg-card p-5 shadow-xs" noValidate>
      <h2 className="font-semibold">{editando ? `Editar “${inicial?.nombre}”` : "Nueva categoría"}</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        <Campo id="cat-nombre" etiqueta="Nombre" error={nombre ? (errorNombre ?? undefined) : undefined}>
          <Input id="cat-nombre" value={nombre} maxLength={60} autoFocus onChange={(e) => setNombre(e.target.value)} />
        </Campo>
        <Campo
          id="cat-id"
          etiqueta="Código"
          error={idFinal ? (errorId ?? undefined) : undefined}
          ayuda={editando ? "El código no cambia: lo usan los objetos de esta categoría." : "Se propone a partir del nombre."}
        >
          <Input
            id="cat-id"
            value={idFinal}
            disabled={editando}
            maxLength={64}
            className="font-mono"
            onChange={(e) => {
              setIdTocado(true);
              setId(e.target.value);
            }}
          />
        </Campo>
      </div>
      <Campo id="cat-desc" etiqueta="Descripción (opcional)">
        <Input id="cat-desc" value={descripcion} maxLength={200} onChange={(e) => setDescripcion(e.target.value)} />
      </Campo>
      <div className="flex flex-wrap gap-2">
        <Button type="submit" disabled={enviando || !!errorNombre || !!errorId}>
          {enviando && <Loader2 className="size-4 animate-spin" aria-hidden />}
          {editando ? "Guardar cambios" : "Crear categoría"}
        </Button>
        <Button type="button" variant="ghost" onClick={alCancelar} disabled={enviando}>
          Cancelar
        </Button>
      </div>
    </form>
  );
}

function TarjetaCategoria({
  categoria,
  administrar,
  alEditar,
}: {
  categoria: Categoria;
  administrar: boolean;
  alEditar: () => void;
}) {
  const eliminar = useEliminarCategoria();
  const [confirmando, setConfirmando] = useState(false);
  const Icono = ICONOS[categoria.categoria_id] ?? Tags;

  return (
    <li className="flex h-full flex-col rounded-xl border bg-card shadow-xs">
      <Link
        to={`/objetos?categoria=${encodeURIComponent(categoria.categoria_id)}`}
        className="group flex flex-1 items-start gap-4 rounded-xl p-5 transition-colors hover:bg-muted/30"
      >
        <span className="grid size-10 shrink-0 place-items-center rounded-lg bg-primary/10 text-primary">
          <Icono className="size-5" aria-hidden />
        </span>
        <span className="min-w-0 flex-1 space-y-1">
          <span className="block font-semibold">{categoria.nombre}</span>
          <span className="block text-sm text-muted-foreground">{categoria.descripcion || "Sin descripción"}</span>
        </span>
        <ChevronRight
          className="size-4 shrink-0 self-center text-muted-foreground transition-transform group-hover:translate-x-0.5"
          aria-hidden
        />
      </Link>

      {administrar && (
        <div className="flex flex-wrap items-center gap-1 border-t px-3 py-2">
          {confirmando ? (
            <>
              <span className="mr-auto text-sm">¿Eliminarla?</span>
              <Button
                size="sm"
                variant="destructive"
                disabled={eliminar.isPending}
                onClick={() => eliminar.mutate(categoria.categoria_id, { onSettled: () => setConfirmando(false) })}
              >
                {eliminar.isPending && <Loader2 className="size-3.5 animate-spin" aria-hidden />}
                Sí, eliminar
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirmando(false)} disabled={eliminar.isPending}>
                Cancelar
              </Button>
            </>
          ) : (
            <>
              <span className="mr-auto font-mono text-xs text-muted-foreground">{categoria.categoria_id}</span>
              <Button size="sm" variant="ghost" onClick={alEditar}>
                <Pencil aria-hidden />
                Editar
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setConfirmando(true)}>
                <Trash2 aria-hidden />
                Eliminar
              </Button>
            </>
          )}
        </div>
      )}
    </li>
  );
}

export default function CategoriasPage() {
  const categorias = useCategorias();
  const administrar = useEsAdministrador();
  const crear = useCrearCategoria();
  const actualizar = useActualizarCategoria();
  // null: sin formulario; "nueva": alta; un id: edición de esa categoría.
  const [formulario, setFormulario] = useState<string | null>(null);
  const editada = categorias.data?.find((c) => c.categoria_id === formulario);

  const guardar = (c: Categoria) => {
    const opciones = { onSuccess: () => setFormulario(null) };
    if (formulario === "nueva") crear.mutate(c, opciones);
    else actualizar.mutate(c, opciones);
  };

  return (
    <div className="grid gap-6">
      <PageHeader
        titulo="Categorías"
        descripcion="Así están organizados los objetos del almacén."
        accion={
          administrar &&
          formulario === null && (
            <Button onClick={() => setFormulario("nueva")}>
              <Plus className="size-4" aria-hidden />
              Nueva categoría
            </Button>
          )
        }
      />

      {formulario !== null && (formulario === "nueva" || editada) && (
        <FormCategoria
          key={formulario}
          inicial={editada}
          enviando={crear.isPending || actualizar.isPending}
          alGuardar={guardar}
          alCancelar={() => setFormulario(null)}
        />
      )}

      {categorias.isPending ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-busy="true">
          {Array.from({ length: 4 }, (_, i) => (
            <Skeleton key={i} className="h-32" />
          ))}
        </div>
      ) : categorias.isError ? (
        <EmptyState
          icono={AlertCircle}
          titulo="No se pudieron cargar las categorías"
          descripcion={categorias.error.message}
          accion={
            <Button variant="outline" onClick={() => categorias.refetch()}>
              Reintentar
            </Button>
          }
        />
      ) : categorias.data.length === 0 ? (
        <EmptyState
          icono={Tags}
          titulo="No hay categorías"
          descripcion={
            administrar
              ? "Crea la primera para poder registrar objetos."
              : "Pide a un administrador que dé de alta las categorías."
          }
        />
      ) : (
        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {categorias.data.map((c) => (
            <TarjetaCategoria
              key={c.categoria_id}
              categoria={c}
              administrar={administrar}
              alEditar={() => setFormulario(c.categoria_id)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}
