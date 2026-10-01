import { useEffect, useRef, useState } from "react";
import { AlertCircle, Camera, Check, Loader2, Sparkles, X } from "lucide-react";
import { cn } from "cn";
import { ApiError } from "@/core/api/client";
import { Button } from "@/shared/components/ui/button";
import { nombreDeCategoria, type Categoria } from "@/features/categorias/api";
import { ErrorIdentificacion, identificarFoto, type Propuesta } from "./api";

type Estado =
  | { fase: "inicio" }
  | { fase: "subiendo" | "analizando" }
  | { fase: "lista"; propuesta: Propuesta }
  | { fase: "error"; mensaje: string };

const ESTILO_NIVEL: Record<Propuesta["nivel"], { clase: string; texto: string }> = {
  alta: { clase: "bg-success/15 text-success", texto: "Confianza alta" },
  media: { clase: "bg-warning/15 text-warning", texto: "Revísala" },
  baja: { clase: "bg-muted text-muted-foreground", texto: "Confianza baja" },
};

/**
 * La IA solo propone: "Usar sugerencia" llena el nombre y la categoría, y la
 * persona revisa y guarda. Nada se registra sin pulsar "Registrar objeto".
 */
export function IdentificarConFoto({
  categorias,
  alUsar,
}: {
  categorias: Categoria[];
  alUsar: (datos: { nombre?: string; categoria?: string }) => void;
}) {
  const entrada = useRef<HTMLInputElement>(null);
  const [estado, setEstado] = useState<Estado>({ fase: "inicio" });
  const [vista, setVista] = useState<string | null>(null);

  useEffect(() => () => {
    if (vista) URL.revokeObjectURL(vista);
  }, [vista]);

  const elegir = async (archivo: File | undefined) => {
    if (!archivo) return;
    setVista(URL.createObjectURL(archivo));
    try {
      const propuesta = await identificarFoto(archivo, (fase) => setEstado({ fase }));
      setEstado({ fase: "lista", propuesta });
    } catch (e) {
      const mensaje =
        e instanceof ErrorIdentificacion || e instanceof ApiError ? e.message : "No se pudo identificar el objeto.";
      setEstado({ fase: "error", mensaje });
    } finally {
      if (entrada.current) entrada.current.value = "";
    }
  };

  const ocupado = estado.fase === "subiendo" || estado.fase === "analizando";

  return (
    <section className="grid gap-4 rounded-xl border border-dashed bg-card p-5">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h2 className="flex items-center gap-2 font-semibold">
            <Sparkles className="size-4 text-primary" aria-hidden />
            Identificar con foto
          </h2>
          <p className="text-sm text-muted-foreground">
            Toma una foto del objeto y su etiqueta: se propone el nombre y la categoría. Tú decides si los usas.
          </p>
        </div>
        <input
          ref={entrada}
          type="file"
          accept="image/*"
          capture="environment"
          className="sr-only"
          tabIndex={-1}
          aria-hidden
          onChange={(e) => elegir(e.target.files?.[0])}
        />
        <Button type="button" variant="outline" disabled={ocupado} onClick={() => entrada.current?.click()}>
          {ocupado ? <Loader2 className="size-4 animate-spin" aria-hidden /> : <Camera className="size-4" aria-hidden />}
          {estado.fase === "inicio" ? "Tomar foto" : "Otra foto"}
        </Button>
      </div>

      {estado.fase !== "inicio" && (
        <div className="grid gap-4 sm:grid-cols-[8rem_1fr]" aria-live="polite">
          {vista && (
            <img src={vista} alt="Foto del objeto" className="aspect-square w-32 rounded-lg border object-cover" />
          )}

          {ocupado && (
            <p className="flex items-center gap-2 self-center text-sm text-muted-foreground">
              <Loader2 className="size-4 animate-spin" aria-hidden />
              {estado.fase === "subiendo" ? "Subiendo la foto…" : "Analizando la foto…"}
            </p>
          )}

          {estado.fase === "error" && (
            <p className="flex items-start gap-2 self-center text-sm text-destructive">
              <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
              {estado.mensaje}
            </p>
          )}

          {estado.fase === "lista" && (
            <Resultado
              propuesta={estado.propuesta}
              categorias={categorias}
              alUsar={() => {
                alUsar({
                  nombre: estado.propuesta.nombre_sugerido ?? undefined,
                  categoria: estado.propuesta.categoria_sugerida ?? undefined,
                });
                setEstado({ fase: "inicio" });
                setVista(null);
              }}
              alDescartar={() => {
                setEstado({ fase: "inicio" });
                setVista(null);
              }}
            />
          )}
        </div>
      )}
    </section>
  );
}

function Resultado({
  propuesta,
  categorias,
  alUsar,
  alDescartar,
}: {
  propuesta: Propuesta;
  categorias: Categoria[];
  alUsar: () => void;
  alDescartar: () => void;
}) {
  if (!propuesta.nombre_sugerido) {
    return (
      <div className="grid content-center gap-2 text-sm">
        <p>No se reconoció el objeto. Prueba con más luz y el objeto centrado, o escribe los datos a mano.</p>
        <Button type="button" variant="ghost" className="justify-self-start" onClick={alDescartar}>
          Cerrar
        </Button>
      </div>
    );
  }

  const nivel = ESTILO_NIVEL[propuesta.nivel];
  return (
    <div className="grid content-start gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-lg font-semibold">{propuesta.nombre_sugerido}</span>
        <span className={cn("rounded-full px-2 py-0.5 text-xs font-medium tabular", nivel.clase)}>
          {nivel.texto} · {propuesta.confianza}%
        </span>
      </div>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 text-sm">
        <dt className="text-muted-foreground">Categoría</dt>
        <dd>
          {propuesta.categoria_sugerida
            ? nombreDeCategoria(categorias, propuesta.categoria_sugerida)
            : "Sin sugerencia: elígela tú"}
        </dd>
        {propuesta.codigo_detectado && (
          <>
            <dt className="text-muted-foreground">Código leído</dt>
            <dd className="font-mono">{propuesta.codigo_detectado}</dd>
          </>
        )}
      </dl>
      {propuesta.etiquetas.length > 1 && (
        <p className="text-xs text-muted-foreground">
          También vio: {propuesta.etiquetas.slice(1).map((e) => e.nombre).join(", ")}
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button type="button" onClick={alUsar}>
          <Check className="size-4" aria-hidden />
          Usar sugerencia
        </Button>
        <Button type="button" variant="ghost" onClick={alDescartar}>
          <X className="size-4" aria-hidden />
          Descartar
        </Button>
      </div>
    </div>
  );
}
