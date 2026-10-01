import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Pagina } from "@/core/api/client";
import { notify } from "@/core/notify";

export type Categoria = { categoria_id: string; nombre: string; descripcion: string };

const CLAVE = ["categorias"] as const;
const ruta = (id: string) => `/categorias/${encodeURIComponent(id)}`;

export function useCategorias() {
  return useQuery({
    queryKey: CLAVE,
    queryFn: () => api.get<Pagina<Categoria>>("/categorias?limite=200"),
    select: (r) => r.elementos,
    staleTime: 5 * 60_000,
  });
}

export function nombreDeCategoria(categorias: Categoria[] | undefined, id: string): string {
  return categorias?.find((c) => c.categoria_id === id)?.nombre ?? id;
}

/** "Equipo de protección" -> "equipo-de-proteccion": el id que acepta el backend. */
export function idDesdeNombre(nombre: string): string {
  return nombre
    .normalize("NFKD")
    .replace(/[̀-ͯ]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 64);
}

export function useCrearCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (datos: Categoria) => api.post<Categoria>("/categorias", datos),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: CLAVE });
      notify.success(`Categoría “${c.nombre}” creada.`);
    },
  });
}

export function useActualizarCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ categoria_id, ...cambios }: Categoria) => api.put<Categoria>(ruta(categoria_id), cambios),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: CLAVE });
      notify.success(`Categoría “${c.nombre}” actualizada.`);
    },
  });
}

export function useEliminarCategoria() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.delete<Categoria>(ruta(id)),
    onSuccess: (c) => {
      qc.invalidateQueries({ queryKey: CLAVE });
      notify.success(`Categoría “${c.nombre}” eliminada.`);
    },
  });
}
