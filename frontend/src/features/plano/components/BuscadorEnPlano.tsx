import { useMemo, useState } from "react";
import { Search } from "lucide-react";
import { Input } from "@/shared/components/ui/input";
import { PuntoColor } from "@/shared/components/PuntoColor";
import { BotonMicrofono } from "@/shared/components/BotonMicrofono";
import { useBusquedaPorVoz } from "@/shared/hooks/useBusquedaPorVoz";
import { useDebounced } from "@/shared/hooks/useDebounced";
import { normalizar } from "@/shared/lib/texto";
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
          columna: objeto.columna,
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
  const consulta = useDebounced(normalizar(texto), 200);
  const objetos = useMemo(() => aplanar(plano), [plano]);

  // Sin acentos ni mayúsculas: el dictado devuelve "multímetro" y el catálogo
  // puede decir "Multimetro", o al revés.
  const buscar = (termino: string) =>
    termino === ""
      ? []
      : objetos
          .filter(
            (u) => normalizar(u.objeto.nombre).includes(termino) || normalizar(u.objeto.categoria).includes(termino),
          )
          .slice(0, MAXIMO_RESULTADOS);

  const resultados = buscar(consulta);

  const elegir = (ubicacion: UbicacionDeObjeto) => {
    setTexto("");
    onElegir(ubicacion);
  };

  // Por voz: si lo dicho coincide con un solo objeto, se elige (y se enciende su
  // LED) sin tener que tocar nada más. Si hay varios, quedan en la lista.
  const voz = useBusquedaPorVoz({
    alEscuchar: setTexto,
    alTerminar: (dicho) => {
      setTexto(dicho);
      const coincidencias = buscar(normalizar(dicho));
      if (coincidencias.length === 1) elegir(coincidencias[0]);
    },
  });

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
          placeholder={
            voz.escuchando ? "Escuchando… di el nombre del objeto" : "Nombre o categoría: taladro, herramienta…"
          }
          autoComplete="off"
          className={voz.soportado ? "h-11 pr-12 pl-9" : "h-11 pl-9"}
        />
        {voz.soportado && (
          <BotonMicrofono
            escuchando={voz.escuchando}
            onIniciar={voz.iniciar}
            onDetener={voz.detener}
            className="md:size-8"
          />
        )}
      </div>
      {voz.error && (
        <p role="alert" className="text-sm text-destructive">
          {voz.error}
        </p>
      )}

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
                    {u.pasillo}-{u.anaquel} · N{u.nivel} · C{u.columna} · LED {u.objeto.posicion_led}
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
