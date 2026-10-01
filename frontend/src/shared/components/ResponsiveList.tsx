import type { ReactNode } from "react";
import { cn } from "cn";

export type Columna<T> = {
  clave: string;
  titulo: string;
  celda: (fila: T) => ReactNode;
  className?: string;
  principal?: boolean; // en móvil se muestra como título de la tarjeta
};

type Props<T> = {
  filas: T[];
  columnas: Columna<T>[];
  obtenerId: (fila: T) => string | number;
  alSeleccionar?: (fila: T) => void;
};

export function ResponsiveList<T>({ filas, columnas, obtenerId, alSeleccionar }: Props<T>) {
  const principal = columnas.find((c) => c.principal) ?? columnas[0];
  const resto = columnas.filter((c) => c !== principal);

  return (
    <>
      <div className="hidden overflow-hidden rounded-lg border md:block">
        <table className="w-full text-sm">
          <thead className="bg-muted/50 text-left text-xs font-medium text-muted-foreground">
            <tr>
              {columnas.map((c) => (
                <th key={c.clave} className={cn("px-4 py-3", c.className)}>{c.titulo}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {filas.map((fila) => (
              <tr
                key={obtenerId(fila)}
                onClick={() => alSeleccionar?.(fila)}
                className={cn("transition-colors", alSeleccionar && "cursor-pointer hover:bg-muted/40")}
              >
                {columnas.map((c) => (
                  <td key={c.clave} className={cn("px-4 py-3", c.className)}>{c.celda(fila)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <ul className="grid gap-3 md:hidden">
        {filas.map((fila) => (
          <li key={obtenerId(fila)}>
            <button
              type="button"
              onClick={() => alSeleccionar?.(fila)}
              className="w-full rounded-lg border bg-card p-4 text-left shadow-xs active:bg-muted/40"
            >
              <div className="font-medium">{principal.celda(fila)}</div>
              <dl className="mt-2 grid grid-cols-2 gap-x-4 gap-y-1 text-sm">
                {resto.map((c) => (
                  <div key={c.clave} className="min-w-0">
                    <dt className="text-xs text-muted-foreground">{c.titulo}</dt>
                    <dd className="truncate">{c.celda(fila)}</dd>
                  </div>
                ))}
              </dl>
            </button>
          </li>
        ))}
      </ul>
    </>
  );
}
