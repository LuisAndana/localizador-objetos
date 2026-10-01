import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { PuntoColor } from "@/shared/components/PuntoColor";
import { useDebounced } from "@/shared/hooks/useDebounced";
import type { Plano, UbicacionDeObjeto } from "../tipos";

const MAXIMO_RESULTADOS = 6;

/** Todos los objetos del plano con su ubicación, para buscarlos sin ir al servidor. */
function aplanar(plano: Plano): UbicacionDeObjeto[] {
  return plano.pasillos.flatMap((pasillo) =>
    pasillo.anaqueles.flatMap((anaquel) =>
      anaquel.niveles.flatMap((nivel) =>
        nivel.objetos.map((objeto) => ({
          objeto,
          pasillo: pasillo.pasillo,
          anaquel: anaquel.anaquel,
          nivel: nivel.nivel,
        })),
      ),
    ),
  );
}

export function BuscadorEnPlano({
  plano,
  onElegir,
}: {
  plano: Plano;
  onElegir: (ubicacion: UbicacionDeObjeto) => void;
}) {
  const [texto, setTexto] = useState("");
  const consulta = useDebounced(texto.trim().toLowerCase(), 200);
  const objetos = useMemo(() => aplanar(plano), [plano]);

  const resultados = useMemo(() => {
    if (consulta === "") return [];
    return objetos
      .filter(
        (u) =>
          u.objeto.nombre.toLowerCase().includes(consulta) ||
          u.objeto.categoria.toLowerCase().includes(consulta),
      )
      .slice(0, MAXIMO_RESULTADOS);
  }, [objetos, consulta]);

  const elegir = (ubicacion: UbicacionDeObjeto) => {
    setTexto("");
    onElegir(ubicacion);
  };

  return (
    <div className="grid gap-2">
      <label htmlFor="buscar-en-plano" className="text-sm font-medium">
        Buscar un objeto en este almacén
      </label>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" aria-hidden />
        <Input
          id="buscar-en-plano"
          value={texto}
          onChange={(e) => setTexto(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && resultados[0]) elegir(resultados[0]);
          }}
          placeholder="Nombre o categoría: taladro, herramienta…"
          autoComplete="off"
          className="h-11 pl-9"
        />
      </div>

      {consulta !== "" && (
        <ul aria-live="polite" className="grid gap-1.5">
          {resultados.length === 0 ? (
            <li className="rounded-lg border border-dashed px-3 py-2.5 text-sm text-muted-foreground">
              Nada con ese nombre en este almacén. Prueba con otra palabra o cambia de almacén.
            </li>
          ) : (
            resultados.map((u) => (
              <li key={u.objeto.object_id}>
                <button
                  type="button"
                  onClick={() => elegir(u)}
                  className="flex min-h-11 w-full items-center gap-2 rounded-lg border bg-card px-3 py-2 text-left text-sm transition-colors hover:bg-muted/40"
                >
                  <PuntoColor color={u.objeto.color_indicador} />
                  <span className="min-w-0 flex-1 truncate font-medium">{u.objeto.nombre}</span>
                  <span className="shrink-0 text-xs text-muted-foreground tabular">
                    {u.pasillo}-{u.anaquel} · N{u.nivel} · LED {u.objeto.posicion_led}
                  </span>
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}
