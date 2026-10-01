# Nodo del almacén (ESP32 + tira WS2812B)

Firmware del nodo que vive en cada almacén. Se conecta a **AWS IoT Core** por MQTT con TLS mutuo, escucha `almacen/{ALMACEN_ID}/led` y enciende el LED que indica cada orden durante los segundos indicados.

- Varias órdenes a la vez: cada LED tiene su propio temporizador.
- Una orden nueva para un LED que ya está encendido reemplaza a la anterior.
- Si se cae el Wi-Fi o el broker, se reconecta solo, con espera creciente de 2 s hasta 60 s. Mientras tanto, los LEDs encendidos se apagan a su hora.
- Toda orden se valida antes de tocar la tira. Una posición fuera de la tira, un color que no sea `#RRGGBB` o una duración fuera de 1 a 3600 s se descartan y se registran en el puerto serie.

> **Estado:** compila para `esp32dev` sin advertencias: 14 % de RAM y 70 % de flash. **Todavía no se ha probado en una placa real** ni contra IoT Core.

## Material

| Pieza | Nota |
|---|---|
| ESP32 DevKit (esp32dev) | Cualquier placa con ESP32 clásico |
| Tira WS2812B a 5 V | `NUM_LEDS` en `config.h` debe coincidir con los LEDs reales |
| Fuente de 5 V | Calcula unos 60 mA por LED encendido al máximo. Con `BRILLO 80` y pocos LEDs a la vez, 2 A sobran para una tira de 150 |
| Resistencia de 330 Ω | En serie entre el GPIO y el DIN de la tira |
| Capacitor de 1000 µF | Entre 5 V y GND, en la entrada de la tira |
| Convertidor de nivel 74AHCT125 (recomendado) | El ESP32 da 3.3 V y la tira espera 5 V. Muchas tiras funcionan sin él, pero con cables largos falla |

## Conexiones

```
Fuente 5V (+) ──┬──────────────── 5V  tira
                └── 1000 µF ──┐
Fuente 5V (-) ──┴─────────────┴── GND tira ── GND ESP32   (tierra común, obligatoria)
ESP32 GPIO 5 ── 330 Ω ── (74AHCT125) ── DIN tira
```

No alimentes la tira desde el pin de 5 V del ESP32: la corriente de la tira lo quema.

## 1. Registrar el nodo en IoT Core

El **nombre del Thing debe ser el `almacen_id`** (por ejemplo `almacen-01`). La política `PoliticaNodoAlmacen` del stack solo deja que el nodo se conecte con ese clientId y escuche el topic de su propio almacén.

```bash
aws iot create-thing --thing-name almacen-01
```

```bash
aws iot create-keys-and-certificate --set-as-active --certificate-pem-outfile almacen-01.cert.pem --private-key-outfile almacen-01.private.key --query certificateArn --output text
```

Guarda el ARN que imprime y úsalo en los dos comandos siguientes. El nombre de la política lo da la salida `PoliticaIoTNodos` del stack.

```bash
aws iot attach-policy --policy-name localizador-objetos-dev-nodo-almacen --target ARN_DEL_CERTIFICADO
```

```bash
aws iot attach-thing-principal --thing-name almacen-01 --principal ARN_DEL_CERTIFICADO
```

El endpoint de IoT Core es el mismo que se pasa al stack como `EndpointIoT`:

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

Descarga también la CA raíz de Amazon: https://www.amazontrust.com/repository/AmazonRootCA1.pem

> `almacen-01.private.key` es secreta. No la subas al repositorio ni la mandes por chat; solo va en `config.h`, que está en `.gitignore`.

## 2. Configurar

1. Copia `include/config.example.h` como `include/config.h`.
2. Llena el Wi-Fi, `ALMACEN_ID`, `IOT_ENDPOINT`, `NUM_LEDS` y pega los tres certificados.

## 3. Compilar y grabar

Con [PlatformIO](https://platformio.org/) (extensión de VS Code o `pip install platformio`), desde esta carpeta:

```bash
pio run -t upload
```

```bash
pio device monitor
```

En el monitor debe aparecer `[mqtt] escuchando almacen/almacen-01/led`. El LED azul de la placa (GPIO 2) se queda encendido mientras hay conexión con IoT Core.

> En Windows, si la compilación falla con `CreateProcess: No such file or directory`, la ruta del proyecto es demasiado larga para el compilador. Mueve la carpeta a una ruta corta (por ejemplo `C:\fw\nodo_almacen`) o usa `subst`.

## 4. Probar sin la app

Desde la consola de AWS IoT (**MQTT test client**), publica en `almacen/almacen-01/led`:

```json
{"posicion_led": 3, "color_indicador": "#00FF00", "duracion_segundos": 10, "object_id": "prueba"}
```

El LED 3 (contando desde 0) debe encenderse en verde durante 10 segundos.

## Estructura

| Archivo | Qué hace |
|---|---|
| `src/main.cpp` | Wi-Fi, hora por NTP (TLS la necesita), MQTT con reconexión y la tira |
| `lib/orden_led/orden_led.h` | Lógica sin hardware: valida la orden y lleva los temporizadores de cada LED |
| `include/config.example.h` | Plantilla de configuración; la real (`config.h`) no se sube |
