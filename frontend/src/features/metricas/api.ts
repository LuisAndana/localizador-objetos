import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/core/api/client";
import { notify } from "@/core/notify";
import { formatearDuracion } from "@/shared/lib/formato";
import type { Busqueda } from "@/features/objetos/tipos";

export type Estadisticas = {
  muestras: number;
  promedio_ms: number;
  mediana_ms: number;
  p90_ms: number;
  minimo_ms: number;
  maximo_ms: number;
};

export type Metricas = {
  con_sistema: Estadisticas;
  manual: Estadisticas;
  busquedas_abiertas: number;
  reduccion_pct: number | null;
  meta_pct: number;
  cumple_meta: boolean | null;
  recientes: Busqueda[];
};

export const clavesMetricas = {
  localizacion: ["metricas", "localizacion"] as const,
};

export function useMetricas() {
  return useQuery({
    queryKey: clavesMetricas.localizacion,
    queryFn: () => api.get<Metricas>("/metricas/localizacion"),
  });
}

/** Cierra el cronómetro de una búsqueda: el operador confirma que ya lo encontró. */
export function useConfirmarBusqueda() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (busquedaId: string) =>
      api.post<Busqueda>(`/busquedas/${encodeURIComponent(busquedaId)}/confirmar`),
    onSuccess: (busqueda) => {
      qc.invalidateQueries({ queryKey: clavesMetricas.localizacion });
      notify.success(`Encontrado en ${formatearDuracion(busqueda.duracion_ms)}.`);
    },
  });
}

/** Medición manual de referencia: el método anterior, cronometrado a mano. */
export function useRegistrarMedicionManual() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (datos: { object_id: string; duracion_ms: number }) =>
      api.post<Busqueda>("/busquedas", datos),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: clavesMetricas.localizacion });
      notify.success("Medición manual registrada.");
    },
  });
}
