// Logica pura del nodo: interpretar la orden MQTT y llevar los temporizadores
// de cada LED. No depende de Wi-Fi, MQTT ni de la tira, asi que se puede probar
// por separado del hardware.
//
// Contrato con el backend (ver ESTADO_DEL_PROYECTO.md, "Contrato con el firmware"):
//   topic   almacen/{almacen_id}/led   (QoS 1)
//   payload {"posicion_led": 42, "color_indicador": "#00FF00",
//            "duracion_segundos": 30, "object_id": "...", "emitido_en": "..."}
#pragma once

#include <ArduinoJson.h>
#include <stddef.h>
#include <stdint.h>

// El backend limita la duracion a 300 s; se acepta hasta una hora por si el
// limite crece, pero nunca un LED encendido indefinidamente.
static const uint32_t DURACION_MAXIMA_S = 3600;

struct OrdenLed {
  uint16_t posicion;
  uint8_t rojo;
  uint8_t verde;
  uint8_t azul;
  uint32_t duracionMs;
};

enum class ResultadoOrden {
  Ok,
  JsonInvalido,
  PosicionInvalida,
  ColorInvalido,
  DuracionInvalida,
};

inline const char* describir(ResultadoOrden r) {
  switch (r) {
    case ResultadoOrden::Ok: return "ok";
    case ResultadoOrden::JsonInvalido: return "el payload no es JSON valido";
    case ResultadoOrden::PosicionInvalida: return "posicion_led fuera de la tira";
    case ResultadoOrden::ColorInvalido: return "color_indicador no es #RRGGBB";
    case ResultadoOrden::DuracionInvalida: return "duracion_segundos fuera de rango";
  }
  return "desconocido";
}

inline int valorHex(char c) {
  if (c >= '0' && c <= '9') return c - '0';
  if (c >= 'a' && c <= 'f') return c - 'a' + 10;
  if (c >= 'A' && c <= 'F') return c - 'A' + 10;
  return -1;
}

// "#RRGGBB" -> componentes. Cualquier otro formato se rechaza.
inline bool colorDesdeHex(const char* texto, uint8_t& r, uint8_t& g, uint8_t& b) {
  if (texto == nullptr || texto[0] != '#') return false;
  uint8_t partes[3];
  for (int i = 0; i < 3; i++) {
    int alto = valorHex(texto[1 + 2 * i]);
    int bajo = valorHex(texto[2 + 2 * i]);
    if (alto < 0 || bajo < 0) return false;
    partes[i] = static_cast<uint8_t>(alto * 16 + bajo);
  }
  if (texto[7] != '\0') return false;
  r = partes[0];
  g = partes[1];
  b = partes[2];
  return true;
}

// Valida todo antes de tocar la tira: un mensaje mal formado o malicioso nunca
// enciende un LED ni escribe fuera del arreglo.
inline ResultadoOrden interpretarOrden(const uint8_t* payload, size_t largo, uint16_t numLeds,
                                       OrdenLed& orden) {
  JsonDocument doc;
  if (deserializeJson(doc, payload, largo)) return ResultadoOrden::JsonInvalido;

  JsonVariant posicion = doc["posicion_led"];
  if (!posicion.is<long>()) return ResultadoOrden::PosicionInvalida;
  long valorPosicion = posicion.as<long>();
  if (valorPosicion < 0 || valorPosicion >= numLeds) return ResultadoOrden::PosicionInvalida;

  if (!colorDesdeHex(doc["color_indicador"].as<const char*>(), orden.rojo, orden.verde, orden.azul)) {
    return ResultadoOrden::ColorInvalido;
  }

  JsonVariant duracion = doc["duracion_segundos"];
  if (!duracion.is<long>()) return ResultadoOrden::DuracionInvalida;
  long segundos = duracion.as<long>();
  if (segundos < 1 || segundos > static_cast<long>(DURACION_MAXIMA_S)) return ResultadoOrden::DuracionInvalida;

  orden.posicion = static_cast<uint16_t>(valorPosicion);
  orden.duracionMs = static_cast<uint32_t>(segundos) * 1000UL;
  return ResultadoOrden::Ok;
}

// Cuando se apaga cada LED. Varios pueden estar encendidos a la vez (dos
// personas buscando objetos distintos); una orden nueva para el mismo LED
// reemplaza a la anterior, igual que en el simulador del backend.
template <uint16_t N>
class TemporizadorLeds {
 public:
  void encender(uint16_t posicion, uint32_t ahora, uint32_t duracionMs) {
    if (posicion >= N) return;
    expira_[posicion] = ahora + duracionMs;
    activo_[posicion] = true;
  }

  // Llama a `apagar(posicion)` por cada LED vencido. Devuelve cuantos apago.
  // La resta en uint32_t con cast a int32_t sigue siendo correcta cuando
  // millis() da la vuelta (cada ~49 dias).
  template <typename Funcion>
  uint16_t apagarVencidos(uint32_t ahora, Funcion apagar) {
    uint16_t apagados = 0;
    for (uint16_t i = 0; i < N; i++) {
      if (activo_[i] && static_cast<int32_t>(ahora - expira_[i]) >= 0) {
        activo_[i] = false;
        apagar(i);
        apagados++;
      }
    }
    return apagados;
  }

  bool activo(uint16_t posicion) const { return posicion < N && activo_[posicion]; }

 private:
  uint32_t expira_[N] = {};
  bool activo_[N] = {};
};
