import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api/client";
import { DEMO_LOCAL } from "@/core/config";

export type AlmacenSimulado = {
  almacen_id: string;
  topic: string;
  total_objetos: number;
  total_leds: number;
};

export type LedActivo = {
  posicion_led: number;
  color_indicador: string;
  object_id: string;
  nombre: string | null;
  duracion_segundos: number;
  emitido_en: string;
  segundos_restantes: number;
};

export type EstadoTira = {
  almacen_id: string;
  topic: string;
  total_leds: number;
  activos: LedActivo[];
};

export function useAlmacenesSimulados() {
  return useQuery({
    queryKey: ["simulador", "almacenes"],
    queryFn: () => api.get<{ elementos: AlmacenSimulado[] }>("/simulador/almacenes"),
    select: (r) => r.elementos,
    enabled: DEMO_LOCAL,
  });
}

/**
 * Sondea cada segundo: hace el papel de la suscripción MQTT del nodo.
 * Solo existe con el backend local; en AWS el suscriptor real es el ESP32.
 */
export function useEstadoTira(almacenId: string | undefined) {
  return useQuery({
    queryKey: ["simulador", "tira", almacenId],
    queryFn: () => api.get<EstadoTira>(`/simulador/almacenes/${encodeURIComponent(almacenId ?? "")}/led`),
    enabled: DEMO_LOCAL && Boolean(almacenId),
    refetchInterval: 1000,
    staleTime: 0,
    // Sondeo continuo: el error se muestra en la pantalla, no como un toast por segundo.
    meta: { silencioso: true },
  });
}
