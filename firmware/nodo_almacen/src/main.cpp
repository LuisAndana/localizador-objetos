// Nodo ESP32 del almacen.
//
// Se conecta a AWS IoT Core por MQTT con TLS mutuo (certificado propio del nodo),
// escucha almacen/{ALMACEN_ID}/led y enciende el LED de la posicion que indica
// cada orden durante los segundos indicados. Si se cae el Wi-Fi o el broker, se
// reconecta solo; los LEDs ya encendidos se apagan a su hora aunque no haya red.

#include <Adafruit_NeoPixel.h>
#include <PubSubClient.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <time.h>

#if __has_include("config.h")
#include "config.h"
#else
#error "Falta include/config.h: copia include/config.example.h y llenalo con los datos de este nodo."
#endif

#include "orden_led.h"

static const char* TOPIC = "almacen/" ALMACEN_ID "/led";
static const uint16_t PUERTO_MQTT = 8883;
static const uint32_t ESPERA_MINIMA_MS = 2000;
static const uint32_t ESPERA_MAXIMA_MS = 60000;
static const uint32_t REVISION_LEDS_MS = 50;

Adafruit_NeoPixel tira(NUM_LEDS, PIN_TIRA, NEO_GRB + NEO_KHZ800);
WiFiClientSecure conexionTls;
PubSubClient mqtt(conexionTls);
TemporizadorLeds<NUM_LEDS> temporizador;

bool tiraCambio = false;
uint32_t esperaReconexionMs = ESPERA_MINIMA_MS;
uint32_t ultimoIntentoMs = 0;
uint32_t ultimaRevisionMs = 0;

// --- Tira ---------------------------------------------------------------------------

void alRecibirOrden(char* topic, uint8_t* payload, unsigned int largo) {
  OrdenLed orden;
  ResultadoOrden resultado = interpretarOrden(payload, largo, NUM_LEDS, orden);
  if (resultado != ResultadoOrden::Ok) {
    Serial.printf("[orden] descartada: %s\n", describir(resultado));
    return;
  }
  tira.setPixelColor(orden.posicion, tira.Color(orden.rojo, orden.verde, orden.azul));
  temporizador.encender(orden.posicion, millis(), orden.duracionMs);
  tiraCambio = true;
  Serial.printf("[orden] LED %u encendido %lu s\n", orden.posicion,
                static_cast<unsigned long>(orden.duracionMs / 1000));
}

void apagarVencidos() {
  uint16_t apagados = temporizador.apagarVencidos(millis(), [](uint16_t posicion) {
    tira.setPixelColor(posicion, 0);
  });
  if (apagados > 0) tiraCambio = true;
  if (tiraCambio) {
    tira.show();
    tiraCambio = false;
  }
}

// --- Conexion -------------------------------------------------------------------------

// TLS valida la vigencia del certificado: sin la hora real, la conexion falla.
void sincronizarHora() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("[hora] sincronizando");
  time_t ahora = time(nullptr);
  uint32_t inicio = millis();
  while (ahora < 1700000000 && millis() - inicio < 20000) {
    delay(250);
    Serial.print(".");
    ahora = time(nullptr);
  }
  Serial.println(ahora >= 1700000000 ? " ok" : " sin respuesta (se reintentara)");
}

bool asegurarWifi() {
  if (WiFi.status() == WL_CONNECTED) return true;
  Serial.printf("[wifi] conectando a %s\n", WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  uint32_t inicio = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - inicio < 15000) {
    apagarVencidos();  // los LEDs se siguen apagando a su hora mientras tanto
    delay(100);
  }
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[wifi] sin conexion");
    return false;
  }
  Serial.printf("[wifi] conectado, IP %s\n", WiFi.localIP().toString().c_str());
  sincronizarHora();
  return true;
}

bool conectarMqtt() {
  // El clientId tiene que ser el nombre del Thing: la politica IoT lo exige.
  Serial.printf("[mqtt] conectando como %s\n", ALMACEN_ID);
  if (!mqtt.connect(ALMACEN_ID)) {
    Serial.printf("[mqtt] fallo, estado %d\n", mqtt.state());
    return false;
  }
  if (!mqtt.subscribe(TOPIC, 1)) {
    Serial.println("[mqtt] no se pudo suscribir (revisa la politica IoT y el ALMACEN_ID)");
    mqtt.disconnect();
    return false;
  }
  Serial.printf("[mqtt] escuchando %s\n", TOPIC);
  return true;
}

// Reintenta con espera creciente (2 s, 4 s, ... hasta 60 s) para no saturar el
// broker ni la red si el problema dura.
void mantenerConexion() {
  if (mqtt.connected()) return;
  uint32_t ahora = millis();
  if (ahora - ultimoIntentoMs < esperaReconexionMs && ultimoIntentoMs != 0) return;
  ultimoIntentoMs = ahora;

  if (asegurarWifi() && conectarMqtt()) {
    esperaReconexionMs = ESPERA_MINIMA_MS;
    digitalWrite(PIN_ESTADO, HIGH);
    return;
  }
  digitalWrite(PIN_ESTADO, LOW);
  esperaReconexionMs = min(esperaReconexionMs * 2, ESPERA_MAXIMA_MS);
  Serial.printf("[mqtt] siguiente intento en %lu s\n", static_cast<unsigned long>(esperaReconexionMs / 1000));
}

// --- Arranque y ciclo -----------------------------------------------------------------

void setup() {
  Serial.begin(115200);
  pinMode(PIN_ESTADO, OUTPUT);
  digitalWrite(PIN_ESTADO, LOW);

  tira.begin();
  tira.setBrightness(BRILLO);
  tira.clear();
  tira.show();

  conexionTls.setCACert(AWS_ROOT_CA);
  conexionTls.setCertificate(CERTIFICADO_NODO);
  conexionTls.setPrivateKey(CLAVE_PRIVADA_NODO);

  mqtt.setServer(IOT_ENDPOINT, PUERTO_MQTT);
  mqtt.setCallback(alRecibirOrden);
  mqtt.setBufferSize(1024);  // el payload ronda 150 bytes; sobra margen
  mqtt.setKeepAlive(60);

  Serial.printf("\nNodo %s: %u LEDs en GPIO %u\n", ALMACEN_ID, NUM_LEDS, PIN_TIRA);
}

void loop() {
  mantenerConexion();
  mqtt.loop();

  uint32_t ahora = millis();
  if (ahora - ultimaRevisionMs >= REVISION_LEDS_MS) {
    ultimaRevisionMs = ahora;
    apagarVencidos();
  }
}
