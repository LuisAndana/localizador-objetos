export type Objeto = {
  object_id: string;
  nombre: string;
  categoria: string;
  almacen_id: string;
  pasillo: string;
  anaquel: string;
  nivel: string;
  columna: string;
  posicion_led: number;
  color_indicador: string;
  cantidad: number;
  ultima_actualizacion: string;
};

// La cantidad no se teclea al registrar: nace en 0 y la mueven las entradas y salidas.
export type CuerpoObjeto = Omit<Objeto, "object_id" | "ultima_actualizacion" | "cantidad">;

export type TipoMovimiento = "entrada" | "salida";

export type Movimiento = {
  movimiento_id: string;
  object_id: string;
  tipo: TipoMovimiento;
  cantidad: number;
  origen: string;
  motivo?: string;
  referencia?: string;
  registrado_en: string;
};

export type Busqueda = {
  busqueda_id: string;
  object_id: string;
  modo: "sistema" | "control";
  iniciada_en: string;
  confirmada_en: string;
  duracion_ms: number;
  cerrada_por: string;
};

export type RespuestaMovimiento = {
  movimiento: Movimiento;
  objeto: Objeto;
  /** Solo en las salidas: la búsqueda que ese retiro cerró. */
  busqueda?: Busqueda;
};

export type RespuestaLocalizar = {
  mensaje: string;
  object_id: string;
  nombre: string;
  topic: string;
  /** Cronómetro abierto para el indicador de tiempo; se cierra al confirmar. */
  busqueda_id: string;
  ubicacion: {
    almacen_id: string;
    pasillo: string;
    anaquel: string;
    nivel: string;
    columna: string;
    descripcion: string;
  };
  orden_led: {
    posicion_led: number;
    color_indicador: string;
    duracion_segundos: number;
    object_id: string;
    emitido_en: string;
  };
};
