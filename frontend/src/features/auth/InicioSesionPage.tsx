import { useState } from "react";
import { ArrowLeft, Lightbulb } from "lucide-react";
import { Button } from "@/shared/components/ui/button";
import { BienvenidaAcceso } from "@/features/auth/BienvenidaAcceso";
import { FormularioEntrar } from "@/features/auth/FormularioEntrar";
import { FormularioRegistro } from "@/features/auth/FormularioRegistro";
import { FormularioCodigo } from "@/features/auth/FormularioCodigo";
import { FormularioRecuperar } from "@/features/auth/FormularioRecuperar";
import { FormularioNuevaContrasena } from "@/features/auth/FormularioNuevaContrasena";
import { AvisoOk } from "@/features/auth/AvisoError";
import { cn } from "cn";

type Vista =
  | { tipo: "entrar"; aviso?: string }
  | { tipo: "registro" }
  | { tipo: "confirmar"; correo: string }
  | { tipo: "recuperar" }
  | { tipo: "nueva"; sesion: string; correo: string };

const TITULOS: Record<Vista["tipo"], { titulo: string; detalle: string }> = {
  entrar: { titulo: "Inicia sesión", detalle: "Usa tu cuenta del almacén." },
  registro: { titulo: "Crea tu cuenta", detalle: "Solo correos de la empresa." },
  confirmar: { titulo: "Confirma tu correo", detalle: "Último paso antes de entrar." },
  recuperar: { titulo: "Recupera tu contraseña", detalle: "Te enviamos un código por correo." },
  nueva: { titulo: "Crea tu contraseña", detalle: "Es tu primer ingreso: reemplaza la temporal." },
};

/** Pantalla de acceso: presentación de la app y, a la derecha, el paso que toque. */
export default function InicioSesionPage() {
  const [vista, setVista] = useState<Vista>({ tipo: "entrar" });
  const pestanas = vista.tipo === "entrar" || vista.tipo === "registro";
  const cabecera = TITULOS[vista.tipo];

  return (
    <div className="min-h-dvh bg-background">
      <header className="flex items-center gap-3 px-6 py-5 md:px-12">
        <span className="grid size-10 place-items-center rounded-xl bg-primary text-primary-foreground font-bold">
          M
        </span>
        <div>
          <p className="font-semibold leading-tight">Mamagui Ferretería</p>
          <p className="text-xs text-muted-foreground">Sistema de localización de material</p>
        </div>
      </header>

      <main className="mx-auto grid max-w-6xl items-center gap-12 px-6 pb-12 md:grid-cols-[1.1fr_0.9fr] md:px-12">
        <BienvenidaAcceso />

        <section aria-labelledby="titulo-acceso" className="rounded-2xl border bg-card p-6 shadow-sm sm:p-8">
          {pestanas && (
            <div role="tablist" className="mb-6 grid grid-cols-2 border-b">
              <button
                type="button"
                role="tab"
                aria-selected={vista.tipo === "entrar"}
                onClick={() => setVista({ tipo: "entrar" })}
                className={cn(
                  "-mb-px border-b-2 py-3 text-sm font-semibold",
                  vista.tipo === "entrar" ? "border-foreground" : "border-transparent text-muted-foreground",
                )}
              >
                Iniciar sesión
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={vista.tipo === "registro"}
                onClick={() => setVista({ tipo: "registro" })}
                className={cn(
                  "-mb-px border-b-2 py-3 text-sm font-semibold",
                  vista.tipo === "registro" ? "border-foreground" : "border-transparent text-muted-foreground",
                )}
              >
                Crear cuenta
              </button>
            </div>
          )}

          {!pestanas && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="mb-4 -ml-2"
              onClick={() => setVista({ tipo: "entrar" })}
            >
              <ArrowLeft className="size-4" aria-hidden />
              Volver a iniciar sesión
            </Button>
          )}

          <div className="mb-6 flex items-center gap-3">
            <span className="grid size-10 place-items-center rounded-xl bg-primary text-primary-foreground">
              <Lightbulb className="size-5" aria-hidden />
            </span>
            <div>
              <h2 id="titulo-acceso" className="text-lg font-semibold tracking-tight">
                {cabecera.titulo}
              </h2>
              <p className="text-sm text-muted-foreground">{cabecera.detalle}</p>
            </div>
          </div>

          {vista.tipo === "entrar" && (
            <>
              {vista.aviso && <AvisoOk mensaje={vista.aviso} />}
              <FormularioEntrar
                alPedirNueva={(p) => setVista({ tipo: "nueva", ...p })}
                alRecuperar={() => setVista({ tipo: "recuperar" })}
              />
            </>
          )}
          {vista.tipo === "registro" && (
            <FormularioRegistro alConfirmar={(correo) => setVista({ tipo: "confirmar", correo })} />
          )}
          {vista.tipo === "confirmar" && (
            <FormularioCodigo
              correo={vista.correo}
              alConfirmado={() => setVista({ tipo: "entrar", aviso: "Correo confirmado. Ya puedes entrar." })}
            />
          )}
          {vista.tipo === "recuperar" && (
            <FormularioRecuperar
              alTerminar={(mensaje) => setVista({ tipo: "entrar", aviso: mensaje })}
              alVolver={() => setVista({ tipo: "entrar" })}
            />
          )}
          {vista.tipo === "nueva" && (
            <FormularioNuevaContrasena
              correo={vista.correo}
              sesion={vista.sesion}
              alCancelar={() => setVista({ tipo: "entrar" })}
            />
          )}

          <p className="mt-8 text-xs leading-relaxed text-muted-foreground">
            Conexión cifrada. Tras 5 intentos fallidos la cuenta se bloquea temporalmente. Nunca te pediremos tu
            contraseña por correo.
          </p>
        </section>
      </main>
    </div>
  );
}
