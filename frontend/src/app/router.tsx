import type { ComponentType } from "react";
import { createBrowserRouter, type RouteObject } from "react-router";
import { DEMO_LOCAL } from "@/core/config";
import { AppLayout } from "@/shared/components/AppLayout";

const lazyPage = (loader: () => Promise<{ default: ComponentType }>) => async () => ({
  Component: (await loader()).default,
});

const formulario = lazyPage(() => import("@/features/objetos/pages/FormularioObjetoPage"));

const rutas: RouteObject[] = [
  { index: true, lazy: lazyPage(() => import("@/features/plano/pages/PlanoPage")) },
  { path: "objetos", lazy: lazyPage(() => import("@/features/objetos/pages/BuscarPage")) },
  { path: "objetos/nuevo", lazy: formulario },
  { path: "objetos/:id", lazy: lazyPage(() => import("@/features/objetos/pages/DetallePage")) },
  { path: "objetos/:id/editar", lazy: formulario },
  { path: "etiquetas", lazy: lazyPage(() => import("@/features/etiquetas/pages/EtiquetasPage")) },
  { path: "categorias", lazy: lazyPage(() => import("@/features/categorias/pages/CategoriasPage")) },
  // El mapa vivia en /plano: la ruta se conserva para los enlaces ya repartidos.
  { path: "plano", lazy: lazyPage(() => import("@/features/plano/pages/PlanoPage")) },
  { path: "metricas", lazy: lazyPage(() => import("@/features/metricas/pages/MetricasPage")) },
  ...(DEMO_LOCAL
    ? [{ path: "simulador", lazy: lazyPage(() => import("@/features/simulador/pages/SimuladorPage")) }]
    : []),
  { path: "*", lazy: lazyPage(() => import("@/features/NoEncontradoPage")) },
];

export const router = createBrowserRouter([{ element: <AppLayout />, children: rutas }]);
