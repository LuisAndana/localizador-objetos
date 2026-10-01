import { useState } from "react";
import { NavLink, Outlet } from "react-router";
import { useQueryClient } from "@tanstack/react-query";
import { Gauge, Lightbulb, LogOut, MapPinned, Moon, PlusCircle, Search, Sun, type LucideIcon } from "lucide-react";
import { cn } from "cn";
import { AUTENTICACION_ACTIVA, cerrarSesion } from "@/core/auth/cognito";
import { useUsuario } from "@/core/auth/useSesion";
import { DEMO_LOCAL } from "@/core/config";
import { Button } from "@/shared/components/ui/button";
import InicioSesionPage from "@/features/auth/InicioSesionPage";

type Enlace = { to: string; etiqueta: string; icono: LucideIcon; exacto?: boolean };

// Tres tareas reales (encontrar, dar de alta, ver como va) y nada mas.
// Categorias se alcanza desde la lista de objetos; el simulador, desde el mapa.
const NAVEGACION: Enlace[] = [
  { to: "/", etiqueta: "Mapa", icono: MapPinned, exacto: true },
  { to: "/objetos", etiqueta: "Objetos", icono: Search },
  { to: "/objetos/nuevo", etiqueta: "Registrar", icono: PlusCircle },
  { to: "/metricas", etiqueta: "Métricas", icono: Gauge },
];

function BotonTema() {
  const [oscuro, setOscuro] = useState(() => document.documentElement.classList.contains("dark"));

  const alternar = () => {
    const siguiente = !oscuro;
    document.documentElement.classList.toggle("dark", siguiente);
    try {
      localStorage.setItem("tema", siguiente ? "oscuro" : "claro");
    } catch {
      /* sin almacenamiento: el cambio dura solo esta sesión */
    }
    setOscuro(siguiente);
  };

  return (
    <Button variant="ghost" size="icon" onClick={alternar} aria-label={oscuro ? "Usar tema claro" : "Usar tema oscuro"}>
      {oscuro ? <Sun className="size-4" aria-hidden /> : <Moon className="size-4" aria-hidden />}
    </Button>
  );
}

function MenuUsuario({ email }: { email: string }) {
  const qc = useQueryClient();
  const salir = async () => {
    await cerrarSesion();
    // Lo que estaba en caché era de este usuario: no debe verlo el siguiente.
    qc.clear();
  };
  return (
    <div className="flex items-center gap-1">
      <span className="hidden max-w-48 truncate text-sm text-muted-foreground lg:inline" title={email}>
        {email}
      </span>
      <Button variant="ghost" size="icon" onClick={salir} aria-label="Cerrar sesión" title="Cerrar sesión">
        <LogOut className="size-4" aria-hidden />
      </Button>
    </div>
  );
}

export function AppLayout() {
  const usuario = useUsuario();
  if (AUTENTICACION_ACTIVA && !usuario) return <InicioSesionPage />;

  return (
    <div className="min-h-dvh">
      <header className="no-imprimir sticky top-0 z-20 border-b bg-background/85 backdrop-blur">
        <div className="mx-auto flex h-14 w-full max-w-6xl items-center gap-6 px-4 md:px-6">
          <NavLink to="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <span className="grid size-8 place-items-center rounded-lg bg-primary text-primary-foreground">
              <Lightbulb className="size-4" aria-hidden />
            </span>
            Localizador
          </NavLink>

          <nav aria-label="Principal" className="hidden items-center gap-1 md:flex">
            {NAVEGACION.map(({ to, etiqueta, icono: Icono, exacto }) => (
              <NavLink
                key={to}
                to={to}
                end={exacto}
                className={({ isActive }) =>
                  cn(
                    "inline-flex h-9 items-center gap-2 rounded-lg px-3 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground",
                  )
                }
              >
                <Icono className="size-4" aria-hidden />
                {etiqueta}
              </NavLink>
            ))}
          </nav>

          <div className="ml-auto flex items-center gap-2">
            {DEMO_LOCAL && (
              <span
                className="hidden items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium text-muted-foreground sm:inline-flex"
                title="Backend local: datos en SQLite y LEDs simulados. Aún sin AWS."
              >
                <span className="size-1.5 rounded-full bg-warning" aria-hidden />
                Demo local
              </span>
            )}
            <BotonTema />
            {usuario && <MenuUsuario email={usuario.email} />}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-6xl p-4 pb-28 md:p-6 md:pb-10 lg:p-8">
        <Outlet />
      </main>

      <nav
        aria-label="Principal"
        className="no-imprimir fixed inset-x-0 bottom-0 z-20 border-t bg-background/95 pb-[env(safe-area-inset-bottom)] backdrop-blur md:hidden"
      >
        <ul className="grid" style={{ gridTemplateColumns: `repeat(${NAVEGACION.length}, minmax(0, 1fr))` }}>
          {NAVEGACION.map(({ to, etiqueta, icono: Icono, exacto }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={exacto}
                className={({ isActive }) =>
                  cn(
                    "flex h-16 flex-col items-center justify-center gap-1 text-xs font-medium transition-colors",
                    isActive ? "text-primary" : "text-muted-foreground",
                  )
                }
              >
                <Icono className="size-5" aria-hidden />
                {etiqueta}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
    </div>
  );
}
