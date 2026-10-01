import { keepPreviousData, useInfiniteQuery, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, type Pagina } from "@/core/api/client";
import { notify } from "@/core/notify";
import type {
  CuerpoObjeto,
  Movimiento,
  Objeto,
  RespuestaLocalizar,
  RespuestaMovimiento,
  TipoMovimiento,
} from "./tipos";

const TAMANO_PAGINA = 20;

export const clavesObjetos = {
  todas: ["objetos"] as const,
  listas: ["objetos", "lista"] as const,
  lista: (categoria?: string, q?: string) => ["objetos", "lista", categoria ?? "todas", q ?? ""] as const,
  detalle: (id: string) => ["objetos", "detalle", id] as const,
};

const ruta = (id: string) => `/objetos/${encodeURIComponent(id)}`;

/**
 * Lista paginada. Con `q`, el servidor busca por nombre (sin distinguir
 * mayúsculas ni acentos) o por código en todo el catálogo, no solo en lo cargado.
 */
export function useObjetos(categoria?: string, q?: string) {
  return useInfiniteQuery({
    queryKey: clavesObjetos.lista(categoria, q),
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams({ limite: String(TAMANO_PAGINA) });
      if (categoria) params.set("categoria", categoria);
      if (q) params.set("q", q);
      if (pageParam) params.set("cursor", pageParam);
      return api.get<Pagina<Objeto>>(`/objetos?${params}`);
    },
    initialPageParam: null as string | null,
    getNextPageParam: (ultima) => ultima.siguiente_cursor,
    // Mientras llega el resultado de la nueva búsqueda se sigue viendo el anterior,
    // en vez de parpadear al esqueleto con cada letra.
    placeholderData: keepPreviousData,
  });
}

const TAMANO_CATALOGO = 100;
const MAXIMO_PAGINAS_CATALOGO = 20;

/**
 * El catálogo completo, no solo la página visible. Lo usa la hoja de etiquetas,
 * que imprime todo; para buscar, `useObjetos(categoria, q)` busca en el servidor.
 */
export function useCatalogo(habilitado: boolean) {
  return useQuery({
    queryKey: ["objetos", "catalogo"],
    enabled: habilitado,
    staleTime: 60_000,
    queryFn: async () => {
      const todos: Objeto[] = [];
      let cursor: string | null = null;
      for (let vuelta = 0; vuelta < MAXIMO_PAGINAS_CATALOGO; vuelta += 1) {
        const params = new URLSearchParams({ limite: String(TAMANO_CATALOGO) });
        if (cursor) params.set("cursor", cursor);
        const pagina = await api.get<Pagina<Objeto>>(`/objetos?${params}`);
        todos.push(...pagina.elementos);
        cursor = pagina.siguiente_cursor;
        if (!cursor) break;
      }
      return todos;
    },
  });
}

export function useObjeto(id: string, habilitado = true) {
  return useQuery({
    queryKey: clavesObjetos.detalle(id),
    queryFn: () => api.get<Objeto>(ruta(id)),
    enabled: habilitado && id !== "",
    // La página muestra su propio estado de error (incluido el 404).
    meta: { silencioso: true },
  });
}

export function useCrearObjeto() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (datos: CuerpoObjeto & { object_id?: string }) => api.post<Objeto>("/objetos", datos),
    onSuccess: (objeto) => {
      notify.success(`“${objeto.nombre}” quedó registrado.`);
      qc.invalidateQueries({ queryKey: clavesObjetos.listas });
    },
  });
}

export function useActualizarObjeto(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (cambios: CuerpoObjeto) => api.put<Objeto>(ruta(id), cambios),
    onSuccess: (objeto) => {
      qc.setQueryData(clavesObjetos.detalle(id), objeto);
      qc.invalidateQueries({ queryKey: clavesObjetos.listas });
      notify.success("Ubicación actualizada.");
    },
  });
}

export function useEliminarObjeto(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.delete<Objeto>(ruta(id)),
    onSuccess: (objeto) => {
      // Solo las listas: invalidar también el detalle haría que la página, aún
      // montada, lo volviera a pedir y recibiera un 404.
      qc.removeQueries({ queryKey: clavesObjetos.detalle(id) });
      qc.invalidateQueries({ queryKey: clavesObjetos.listas });
      qc.invalidateQueries({ queryKey: ["objetos", "catalogo"] });
      notify.success(`“${objeto.nombre}” se eliminó del catálogo.`);
    },
  });
}

export function useLocalizar(id: string) {
  return useMutation({
    mutationFn: (duracion_segundos: number) =>
      api.post<RespuestaLocalizar>(`${ruta(id)}/localizar`, { duracion_segundos }),
  });
}

/** Igual que `useLocalizar`, pero el objeto se elige al momento: lo usa el mapa. */
export function useLocalizarEnMapa() {
  return useMutation({
    mutationFn: ({ id, duracion_segundos }: { id: string; duracion_segundos: number }) =>
      api.post<RespuestaLocalizar>(`${ruta(id)}/localizar`, { duracion_segundos }),
  });
}

export const clavesMovimientos = {
  lista: (id: string) => ["movimientos", id] as const,
};

const MOVIMIENTOS_VISIBLES = 20;

export function useMovimientos(id: string) {
  return useQuery({
    queryKey: clavesMovimientos.lista(id),
    queryFn: () => {
      const params = new URLSearchParams({ object_id: id, limite: String(MOVIMIENTOS_VISIBLES) });
      return api.get<Pagina<Movimiento>>(`/movimientos?${params}`);
    },
    enabled: id !== "",
    select: (r) => r.elementos,
  });
}

export function useRegistrarMovimiento(id: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (datos: { tipo: TipoMovimiento; cantidad: number; motivo?: string }) =>
      api.post<RespuestaMovimiento>("/movimientos", { object_id: id, ...datos }),
    onSuccess: ({ movimiento, objeto }) => {
      // El backend devuelve el objeto ya actualizado: se usa tal cual en vez de
      // recalcular la cantidad en el cliente.
      qc.setQueryData(clavesObjetos.detalle(id), objeto);
      qc.invalidateQueries({ queryKey: clavesMovimientos.lista(id) });
      qc.invalidateQueries({ queryKey: clavesObjetos.listas });
      const verbo = movimiento.tipo === "entrada" ? "Entrada" : "Salida";
      notify.success(`${verbo} de ${movimiento.cantidad} registrada. Quedan ${objeto.cantidad}.`);
    },
  });
}
