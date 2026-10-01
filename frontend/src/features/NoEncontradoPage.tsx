import { Link } from "react-router";
import { MapPinOff } from "lucide-react";
import { buttonVariants } from "@/shared/components/ui/button";
import { EmptyState } from "@/shared/components/EmptyState";

export default function NoEncontradoPage() {
  return (
    <EmptyState
      icono={MapPinOff}
      titulo="Esta página no existe"
      descripcion="Revisa la dirección o vuelve al listado de objetos."
      accion={
        <Link to="/" className={buttonVariants({ variant: "outline" })}>
          Ir a objetos
        </Link>
      }
    />
  );
}
