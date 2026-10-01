import { useCallback, useEffect, useState } from "react";
import { useEstadoTira } from "@/shared/api/tira";

export type LedEncendido = {
  posicion_led: number;
  color_indicador: string;
  object_id: string;
  nombre: string | null;
  segundos_restantes: number;
};

type OrdenLocal = {
  almacen_id: string;
  posicion_led: number;
  color_indicador: string;
  object_id: string;
  nombre: string | null;
  hasta: number;
};

/**
 * Qué LEDs están encendidos ahora mismo en un almacén.
 *
 * Dos fuentes que se complementan:
 * - El simulador del backend local, que se sondea cada segundo y es la verdad: el
 *   mismo estado que leería el ESP32 en su topic MQTT.
 * - La orden que acaba de emitir esta pantalla, que se pinta al instante sin esperar
 *   al siguiente sondeo. Es también lo único que hay en AWS, donde quien se suscribe
 *   es el nodo físico y el navegador no puede leer la tira.
 */
export function useLedsEnPlano(almacenId: string | undefined) {
  const tira = useEstadoTira(almacenId);
  const [locales, setLocales] = useState<OrdenLocal[]>([]);
  // El reloj vive en estado: así el render es una función pura de props y estado.
  const [ahora, setAhora] = useState(0);

  const vigentes = locales.filter((o) => o.hasta > ahora && o.almacen_id === almacenId);
  const hayVigentes = vigentes.length > 0;

  // Solo corre mientras queda algo encendido; al apagarse todo, el reloj se detiene.
  useEffect(() => {
    if (!hayVigentes) return;
    const intervalo = setInterval(() => setAhora(Date.now()), 250);
    return () => clearInterval(intervalo);
  }, [hayVigentes]);

  const registrarOrden = useCallback(
    (orden: Omit<OrdenLocal, "hasta"> & { duracion_segundos: number }) => {
      const instante = Date.now();
      const hasta = instante + orden.duracion_segundos * 1000;
      setAhora(instante);
      setLocales((previas) => [
        ...previas.filter((o) => o.hasta > instante && o.posicion_led !== orden.posicion_led),
        { ...orden, hasta },
      ]);
    },
    [],
  );

  const encendidos = new Map<number, LedEncendido>();
  for (const o of vigentes) {
    encendidos.set(o.posicion_led, {
      posicion_led: o.posicion_led,
      color_indicador: o.color_indicador,
      object_id: o.object_id,
      nombre: o.nombre,
      segundos_restantes: Math.max(0, (o.hasta - ahora) / 1000),
    });
  }
  // El backend manda sobre la estimación local cuando el simulador está disponible.
  for (const a of tira.data?.activos ?? []) {
    encendidos.set(a.posicion_led, {
      posicion_led: a.posicion_led,
      color_indicador: a.color_indicador,
      object_id: a.object_id,
      nombre: a.nombre,
      segundos_restantes: a.segundos_restantes,
    });
  }

  return {
    encendidos,
    registrarOrden,
    escuchando: tira.isSuccess,
    topic: tira.data?.topic,
    totalLeds: tira.data?.total_leds,
  };
}
