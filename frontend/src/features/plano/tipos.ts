export type Almacen = {
  almacen_id: string;
  total_objetos: number;
  total_pasillos: number;
};

export type ObjetoEnPlano = {
  object_id: string;
  nombre: string;
  categoria: string;
  posicion_led: number;
  color_indicador: string;
  columna: string;
};

/** Un hueco del anaquel: la intersección de un nivel (fila) y una columna. */
export type CeldaPlano = {
  columna: string;
  objetos: ObjetoEnPlano[];
};

export type NivelPlano = {
  nivel: string;
  objetos: ObjetoEnPlano[];
  /** Una celda por cada columna del anaquel, incluidas las vacías. */
  celdas: CeldaPlano[];
};

export type AnaquelPlano = {
  anaquel: string;
  total_objetos: number;
  /** Columnas de izquierda a derecha, incluidas las vacías (mínimo tres). */
  columnas: string[];
  niveles: NivelPlano[];
};

export type PasilloPlano = {
  pasillo: string;
  total_objetos: number;
  anaqueles: AnaquelPlano[];
};

export type Plano = {
  almacen_id: string;
  total_objetos: number;
  total_pasillos: number;
  pasillos: PasilloPlano[];
};

export type UbicacionDeObjeto = {
  objeto: ObjetoEnPlano;
  pasillo: string;
  anaquel: string;
  nivel: string;
  columna: string;
};
