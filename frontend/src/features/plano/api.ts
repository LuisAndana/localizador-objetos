import { useQuery } from "@tanstack/react-query";
import { api } from "@/core/api/client";
import type { Almacen, Plano, UbicacionDeObjeto } from "./tipos";

export const clavesPlano = {
  almacenes: ["almacenes"] as const,
  plano: (almacenId: string | undefined) => ["almacenes", almacenId ?? "", "plano"] as const,
};

export function useAlmacenes() {
  return useQuery({
    queryKey: clavesPlano.almacenes,
    queryFn: () => api.get<{ elementos: Almacen[] }>("/almacenes"),
    select: (r) => r.elementos,
  });
}

export function usePlano(almacenId: string | undefined) {
  return useQuery({
    queryKey: clavesPlano.plano(almacenId),
    queryFn: () => api.get<Plano>(`/almacenes/${encodeURIComponent(almacenId ?? "")}/plano`),
    enabled: Boolean(almacenId),
    // La pantalla muestra su propio estado de error (incluido el 404).
    meta: { silencioso: true },
  });
}

/** Aplana el plano para encontrar un objeto y saber en qué nivel y columna quedó dibujado. */
export function ubicarEnPlano(plano: Plano | undefined, objectId: string | null): UbicacionDeObjeto | undefined {
  if (!plano || !objectId) return undefined;
  for (const pasillo of plano.pasillos) {
    for (const anaquel of pasillo.anaqueles) {
      for (const nivel of anaquel.niveles) {
        const objeto = nivel.objetos.find((o) => o.object_id === objectId);
        if (objeto) {
          return {
            objeto,
            pasillo: pasillo.pasillo,
            anaquel: anaquel.anaquel,
            nivel: nivel.nivel,
            columna: objeto.columna,
          };
        }
      }
    }
  }
  return undefined;
}
