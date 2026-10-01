import type { ReactNode } from "react";

export function PageHeader({ titulo, descripcion, accion }: {
  titulo: string; descripcion?: string; accion?: ReactNode;
}) {
  return (
    <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{titulo}</h1>
        {descripcion && <p className="text-sm text-muted-foreground">{descripcion}</p>}
      </div>
      {accion}
    </header>
  );
}
