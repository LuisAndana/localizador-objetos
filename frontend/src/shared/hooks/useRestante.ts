import { useEffect, useState } from "react";

/** Segundos que faltan hasta `hasta` (epoch en ms), actualizados en vivo. */
export function useRestante(hasta: number | null): number {
  const [ahora, setAhora] = useState(() => Date.now());

  useEffect(() => {
    if (hasta === null) return;
    const tic = () => setAhora(Date.now());
    const primero = setTimeout(tic, 0);
    const intervalo = setInterval(tic, 250);
    return () => {
      clearTimeout(primero);
      clearInterval(intervalo);
    };
  }, [hasta]);

  // Acotado a >= 0; entre que cambia `hasta` y el primer tic se muestra como máximo el valor redondeado.
  return hasta === null ? 0 : Math.max(0, Math.ceil((hasta - ahora) / 1000));
}
