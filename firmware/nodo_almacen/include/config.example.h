// Configuracion del nodo. Copia este archivo como include/config.h y llenalo.
// config.h esta en .gitignore: lleva la clave privada del certificado y la
// contrasena del Wi-Fi, y NUNCA debe subirse al repositorio.
#pragma once

// --- Wi-Fi -------------------------------------------------------------------
#define WIFI_SSID "nombre-de-la-red"
#define WIFI_PASSWORD "contrasena-de-la-red"

// --- Identidad del nodo --------------------------------------------------------
// Debe ser EXACTAMENTE el nombre del Thing en IoT Core y el almacen_id que usa el
// backend (ej. "almacen-01"). La politica IoT del stack solo deja conectarse con
// ese clientId y escuchar almacen/<este valor>/led.
#define ALMACEN_ID "almacen-01"

// Host de datos de IoT Core, sin https:// (aws iot describe-endpoint --endpoint-type iot:Data-ATS)
#define IOT_ENDPOINT "xxxxxxxxxxxxxx-ats.iot.us-east-1.amazonaws.com"

// --- Tira LED ----------------------------------------------------------------------
#define PIN_TIRA 5          // GPIO al DIN de la tira (con resistencia de 330 ohm en serie)
#define NUM_LEDS 150        // LEDs fisicos de la tira de este almacen
#define BRILLO 80           // 0-255. Limita el consumo: cada LED a 255 en blanco pide ~60 mA
#define PIN_ESTADO 2        // LED integrado de la placa: indica el estado de la conexion

// --- Certificados (los genera IoT Core al registrar el Thing) ----------------------
// Amazon Root CA 1: https://www.amazontrust.com/repository/AmazonRootCA1.pem
static const char AWS_ROOT_CA[] = R"EOF(
-----BEGIN CERTIFICATE-----
...pega aqui AmazonRootCA1.pem...
-----END CERTIFICATE-----
)EOF";

// Certificado del dispositivo (xxxx-certificate.pem.crt)
static const char CERTIFICADO_NODO[] = R"EOF(
-----BEGIN CERTIFICATE-----
...pega aqui el certificado del Thing...
-----END CERTIFICATE-----
)EOF";

// Clave privada del dispositivo (xxxx-private.pem.key). Secreta.
static const char CLAVE_PRIVADA_NODO[] = R"EOF(
-----BEGIN RSA PRIVATE KEY-----
...pega aqui la clave privada del Thing...
-----END RSA PRIVATE KEY-----
)EOF";
