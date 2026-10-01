// El estado de la tira lo comparten el simulador y el mapa del almacén, así que vive
// en `shared/api/tira`. Aquí solo se reexporta con los nombres que usa esta pantalla.
export type { AlmacenSimulado, EstadoTira, LedActivo } from "@/shared/api/tira";
export { useAlmacenesSimulados as useAlmacenes, useEstadoTira } from "@/shared/api/tira";
