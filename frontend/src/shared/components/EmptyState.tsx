import type { LucideIcon } from "lucide-react";
import type { ReactNode } from "react";

export function EmptyState({ icono: Icono, titulo, descripcion, accion }: {
  icono: LucideIcon; titulo: string; descripcion: string; accion?: ReactNode;
}) {
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed px-6 py-12 text-center">
      <Icono className="size-10 text-muted-foreground" aria-hidden />
      <div className="space-y-1">
        <p className="font-medium">{titulo}</p>
        <p className="max-w-sm text-sm text-muted-foreground">{descripcion}</p>
      </div>
      {accion}
    </div>
  );
}
