import { AlertCircle } from "lucide-react";

export function AvisoError({ mensaje }: { mensaje: string }) {
  return (
    <p role="alert" className="flex items-start gap-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
      <AlertCircle className="mt-0.5 size-4 shrink-0" aria-hidden />
      {mensaje}
    </p>
  );
}

export function AvisoOk({ mensaje }: { mensaje: string }) {
  return (
    <p role="status" className="rounded-lg bg-emerald-600/10 p-3 text-sm text-emerald-800 dark:text-emerald-300">
      {mensaje}
    </p>
  );
}
