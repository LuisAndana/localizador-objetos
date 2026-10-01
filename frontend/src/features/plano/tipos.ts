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
};

export type NivelPlano = {
  nivel: string;
  objetos: ObjetoEnPlano[];
};

export type AnaquelPlano = {
  anaquel: string;
  total_objetos: number;
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
};
