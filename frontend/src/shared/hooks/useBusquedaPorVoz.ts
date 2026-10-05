import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react";

/**
 * Dictado con el reconocimiento de voz del navegador (Web Speech API).
 *
 * No manda el audio a nuestro backend: lo procesa el navegador (Chrome y Edge
 * usan el servicio de voz de Google; Safari, el de Apple). Firefox no lo trae,
 * así que ahí el micrófono simplemente no se muestra. El navegador solo permite
 * el micrófono en https o en localhost.
 */

type ResultadoVoz = { transcript: string };
type EventoResultado = { results: ArrayLike<ArrayLike<ResultadoVoz> & { isFinal: boolean }> };
type EventoError = { error: string };

type Reconocedor = {
  lang: string;
  interimResults: boolean;
  maxAlternatives: number;
  continuous: boolean;
  onresult: ((e: EventoResultado) => void) | null;
  onerror: ((e: EventoError) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
};

type ConstructorReconocedor = new () => Reconocedor;

function constructorDisponible(): ConstructorReconocedor | undefined {
  if (typeof window === "undefined") return undefined;
  const w = window as unknown as {
    SpeechRecognition?: ConstructorReconocedor;
    webkitSpeechRecognition?: ConstructorReconocedor;
  };
  return w.SpeechRecognition ?? w.webkitSpeechRecognition;
}

export const VOZ_SOPORTADA = Boolean(constructorDisponible());

// Lo que la gente dice antes del nombre del objeto: "busca el taladro",
// "¿dónde está la llave de torque?". Se quita para buscar solo el objeto.
const MULETILLAS =
  /^(?:(?:oye|por favor|quiero|necesito|me puedes)\s+)*(?:(?:busca(?:r|me)?|encuentra(?:me)?|localiza(?:r|me)?|d[oó]nde\s+(?:est[aá]n?|hay|queda)|mu[eé]strame|ens[eé][ñn]ame)\s+)?(?:(?:el|la|los|las|un|una|unos|unas)\s+)?/i;

/** "¿Dónde está el taladro percutor?" -> "taladro percutor". */
export function limpiarDictado(texto: string): string {
  const sinSignos = texto.replace(/[¿?¡!.,;:]/g, " ").replace(/\s+/g, " ").trim();
  return sinSignos.replace(MULETILLAS, "").trim() || sinSignos;
}

const MENSAJES_ERROR: Record<string, string> = {
  "not-allowed": "Permite el uso del micrófono en tu navegador para buscar por voz.",
  "service-not-allowed": "Permite el uso del micrófono en tu navegador para buscar por voz.",
  "audio-capture": "No se encontró un micrófono conectado.",
  network: "La búsqueda por voz necesita conexión a internet.",
  "no-speech": "No se escuchó nada. Toca el micrófono e inténtalo de nuevo.",
};

export function useBusquedaPorVoz({
  alEscuchar,
  alTerminar,
}: {
  /** Texto mientras la persona habla, para que vea lo que se va entendiendo. */
  alEscuchar: (texto: string) => void;
  /** Texto final ya limpio de muletillas. */
  alTerminar: (texto: string) => void;
}) {
  const [escuchando, setEscuchando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const reconocedor = useRef<Reconocedor | null>(null);
  // Las funciones más recientes, sin reiniciar el reconocimiento cuando cambian.
  const callbacks = useRef({ alEscuchar, alTerminar });
  useLayoutEffect(() => {
    callbacks.current = { alEscuchar, alTerminar };
  });

  useEffect(() => () => reconocedor.current?.abort(), []);

  const detener = useCallback(() => reconocedor.current?.stop(), []);

  const iniciar = useCallback(() => {
    const Constructor = constructorDisponible();
    if (!Constructor) return;
    reconocedor.current?.abort();

    const r = new Constructor();
    r.lang = "es-MX";
    r.interimResults = true;
    r.maxAlternatives = 1;
    r.continuous = false;

    let final = "";
    r.onresult = (e) => {
      let parcial = "";
      for (let i = 0; i < e.results.length; i += 1) {
        const resultado = e.results[i];
        if (resultado.isFinal) final += resultado[0].transcript;
        else parcial += resultado[0].transcript;
      }
      callbacks.current.alEscuchar(limpiarDictado(final + parcial));
    };
    r.onerror = (e) => {
      if (e.error !== "aborted") setError(MENSAJES_ERROR[e.error] ?? "No se pudo usar el micrófono.");
    };
    r.onend = () => {
      setEscuchando(false);
      reconocedor.current = null;
      const texto = limpiarDictado(final);
      if (texto) callbacks.current.alTerminar(texto);
    };

    reconocedor.current = r;
    setError(null);
    setEscuchando(true);
    try {
      r.start();
    } catch {
      setEscuchando(false);
      setError("No se pudo usar el micrófono.");
    }
  }, []);

  return { soportado: VOZ_SOPORTADA, escuchando, error, iniciar, detener };
}
