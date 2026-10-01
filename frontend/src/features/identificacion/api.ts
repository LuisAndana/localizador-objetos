import { api } from "@/core/api/client";

/**
 * Identificación de objetos por foto (Amazon Rekognition). Solo existe en AWS:
 * se activa al compilar con VITE_VISION=true. En el modo local no hay S3 ni
 * Rekognition, así que el panel no se muestra.
 */
export const VISION_ACTIVA = import.meta.env.VITE_VISION === "true";

export type Propuesta = {
  nombre_sugerido: string | null;
  categoria_sugerida: string | null;
  codigo_detectado: string | null;
  confianza: number;
  nivel: "alta" | "media" | "baja";
  etiquetas: { nombre: string; original: string; confianza: number }[];
  textos: string[];
};

type Identificacion = {
  identificacion_id: string;
  estado: "pendiente" | "lista" | "error";
  propuesta?: Propuesta;
  motivo?: string;
};

type Solicitud = {
  identificacion_id: string;
  subida: { url: string; campos: Record<string, string>; tamano_maximo: number };
};

const LADO_MAXIMO = 1600;
const CALIDAD_JPEG = 0.85;
const INTERVALO_CONSULTA_MS = 1500;
const ESPERA_MAXIMA_MS = 45_000;

export class ErrorIdentificacion extends Error {}

/**
 * Reduce la foto a 1600 px de lado y la convierte a JPEG. Una foto de teléfono
 * pasa de 4-8 MB a unos 300 KB: sube rápido con datos móviles y Rekognition no
 * necesita más resolución para reconocer el objeto.
 */
async function prepararFoto(archivo: File): Promise<Blob> {
  const imagen = await createImageBitmap(archivo).catch(() => {
    throw new ErrorIdentificacion("No se pudo leer la imagen. Usa una foto JPG o PNG.");
  });
  const escala = Math.min(1, LADO_MAXIMO / Math.max(imagen.width, imagen.height));
  const lienzo = document.createElement("canvas");
  lienzo.width = Math.round(imagen.width * escala);
  lienzo.height = Math.round(imagen.height * escala);
  lienzo.getContext("2d")?.drawImage(imagen, 0, 0, lienzo.width, lienzo.height);
  imagen.close();
  const blob = await new Promise<Blob | null>((ok) => lienzo.toBlob(ok, "image/jpeg", CALIDAD_JPEG));
  if (!blob) throw new ErrorIdentificacion("No se pudo preparar la foto.");
  return blob;
}

const esperar = (ms: number) => new Promise((ok) => setTimeout(ok, ms));

export async function identificarFoto(archivo: File, alAvanzar: (fase: "subiendo" | "analizando") => void) {
  alAvanzar("subiendo");
  const foto = await prepararFoto(archivo);
  const solicitud = await api.post<Solicitud>("/identificaciones");
  if (foto.size > solicitud.subida.tamano_maximo) {
    throw new ErrorIdentificacion("La foto es demasiado grande incluso reducida.");
  }

  // Directo a S3 con el POST prefirmado. No lleva el token de la API: la firma
  // de la URL es la autorización, y S3 rechaza otro tipo o tamaño de archivo.
  const formulario = new FormData();
  Object.entries(solicitud.subida.campos).forEach(([k, v]) => formulario.append(k, v));
  formulario.append("file", foto, "foto.jpg");
  const subida = await fetch(solicitud.subida.url, { method: "POST", body: formulario }).catch(() => null);
  if (!subida?.ok) throw new ErrorIdentificacion("No se pudo subir la foto. Revisa tu conexión.");

  alAvanzar("analizando");
  const limite = Date.now() + ESPERA_MAXIMA_MS;
  while (Date.now() < limite) {
    await esperar(INTERVALO_CONSULTA_MS);
    const r = await api.get<Identificacion>(`/identificaciones/${encodeURIComponent(solicitud.identificacion_id)}`);
    if (r.estado === "lista" && r.propuesta) return r.propuesta;
    if (r.estado === "error") throw new ErrorIdentificacion(r.motivo ?? "No se pudo analizar la foto.");
  }
  throw new ErrorIdentificacion("El análisis tardó demasiado. Inténtalo con otra foto.");
}
