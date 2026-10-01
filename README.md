# Localizador inteligente de objetos — backend serverless

Backend en AWS SAM para localizar físicamente objetos en un almacén. Cuando la app
cliente pide localizar un objeto, el backend lo busca en DynamoDB y publica una orden
MQTT en AWS IoT Core; el nodo ESP32 del almacén la recibe y enciende el LED WS2812B
correspondiente a esa posición.

```
App cliente ──HTTPS──▶ API Gateway ──▶ Lambda (Python 3.12) ──▶ DynamoDB
                                             │
                                             └──MQTT──▶ IoT Core ──▶ ESP32 ──▶ tira WS2812B
                                                   topic: almacen/{almacen_id}/led
```

> **¿Aún sin AWS?** Todo el sistema funciona en local con un solo comando:
>
> ```bash
> python -m uvicorn main:app --reload
> ```
>
> Después abre http://127.0.0.1:8000. El avance, lo que falta y la guía para configurar AWS
> después están en **[ESTADO_DEL_PROYECTO.md](ESTADO_DEL_PROYECTO.md)**.

Este README cubre el despliegue en AWS con SAM. Fuera de alcance por ahora: autenticación
con Cognito, firmware del ESP32 y el módulo de visión.

---

## 1. Requisitos

| Herramienta | Para qué | Comprobar |
|---|---|---|
| AWS SAM CLI | build, local, deploy | `sam --version` |
| AWS CLI v2 | credenciales y consultas | `aws --version` |
| Docker Desktop | emular Lambda y DynamoDB en local | `docker --version` |
| Python 3.12 | ejecutar tests fuera de Docker | `python --version` |

> En esta máquina Docker y Python están listos, pero **SAM CLI y AWS CLI no estaban
> instalados** cuando se generó el andamiaje. Instálalos antes del paso 3:
>
> ```bash
> winget install --id Amazon.AWSCLI -e
> ```
>
> ```bash
> winget install --id Amazon.SAM-CLI -e
> ```
>
> Cierra y reabre la terminal después, para que el PATH se actualice.

---

## 2. Estructura

```
.
├── template.yaml              # Infraestructura: API, 6 Lambdas, 2 tablas, IAM, capa
├── samconfig.toml             # Defaults de build/local/deploy
├── env.json.example           # Plantilla de variables para sam local (copiar a env.json)
├── requirements-dev.txt       # boto3 + pytest, solo para desarrollo
│
├── src/                       # Una carpeta por función (handlers finos)
│   ├── listar_objetos/
│   ├── obtener_objeto/
│   ├── crear_objeto/
│   ├── actualizar_objeto/
│   ├── localizar_objeto/
│   └── listar_categorias/
│
├── layers/common/localizador/   # Lambda Layer: toda la lógica compartida
│   ├── config.py              # Variables de entorno, validadas y cacheadas
│   ├── errores.py             # Errores de dominio → códigos HTTP
│   ├── respuestas.py          # CORS, JSON y el decorador @handler_api
│   ├── validacion.py          # Validación de toda entrada externa
│   ├── paginacion.py          # Cursores keyset opacos
│   ├── modelos.py             # Objeto, Ubicacion, OrdenLed
│   ├── repositorios.py        # Único módulo que habla con DynamoDB
│   └── iot.py                 # Único módulo que publica MQTT
│
├── events/                    # Eventos de prueba para sam local invoke
├── scripts/bootstrap_local.py # Crea y siembra las tablas en DynamoDB Local
└── tests/                     # Tests de validación y modelo
```

La lógica vive en la capa compartida y los handlers solo orquestan: cada `app.py`
ocupa unas 20 líneas. Así el dominio no depende de API Gateway ni de DynamoDB, y
mañana se puede cambiar el transporte sin tocar las reglas de negocio.

---

## 3. Desarrollo local

### 3.1 Levantar DynamoDB Local y sembrar datos

```bash
docker run -d --name dynamodb-local -p 8000:8000 amazon/dynamodb-local
```

```bash
python -m venv .venv
```

```bash
.venv/Scripts/pip install -r requirements-dev.txt
```

```bash
.venv/Scripts/python scripts/bootstrap_local.py
```

Crea `localizador-objetos-dev-Objetos` (con su GSI) y `localizador-objetos-dev-Categorias`,
y siembra tres objetos y tres categorías de ejemplo. Es idempotente; `--reset` borra y recrea.

### 3.2 Configurar variables locales

```bash
cp env.json.example env.json
```

`env.json` está en `.gitignore`. Cada clave de primer nivel debe ser el ID lógico de
una función del template: SAM rechaza cualquier otra clave, así que no le añadas
comentarios.

`DYNAMODB_ENDPOINT_URL` usa `host.docker.internal` porque, dentro del contenedor de
Lambda, `localhost` es el propio contenedor y no tu PC.

Trae `IOT_MODO_SIMULACION: "true"`, de modo que
`localizar` registra la orden MQTT en el log en vez de publicarla en AWS: puedes
desarrollar el flujo completo sin tocar IoT Core ni tener un ESP32 encendido.

### 3.3 Compilar

```bash
sam build
```

### 3.4 Invocar una función suelta

```bash
sam local invoke FnLocalizarObjeto -e events/localizar_objeto.json --env-vars env.json
```

Hay un evento por función en `events/`, más `crear_objeto_invalido.json` para
comprobar que las respuestas 400 salen bien formadas:

| Función | Evento |
|---|---|
| `FnListarObjetos` | `events/listar_objetos.json` |
| `FnObtenerObjeto` | `events/obtener_objeto.json` |
| `FnCrearObjeto` | `events/crear_objeto.json` |
| `FnActualizarObjeto` | `events/actualizar_objeto.json` |
| `FnLocalizarObjeto` | `events/localizar_objeto.json` |
| `FnListarCategorias` | `events/listar_categorias.json` |

### 3.5 Levantar la API completa

```bash
sam local start-api --env-vars env.json
```

Queda en `http://127.0.0.1:3000`:

```bash
curl "http://127.0.0.1:3000/objetos?categoria=herramientas"
```

```bash
curl -X POST http://127.0.0.1:3000/objetos/obj-demo-001/localizar -H "Content-Type: application/json" -d "{\"duracion_segundos\":15}"
```

### 3.6 Tests

```bash
.venv/Scripts/python -m pytest tests -v
```

---

## 4. Despliegue

### 4.1 Obtener el endpoint de IoT Core

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS --query endpointAddress --output text
```

Devuelve algo como `a1b2c3d4e5f6g7-ats.iot.us-east-1.amazonaws.com`. Se pasa **sin**
`https://`. Si lo dejas vacío, el stack despliega con la localización en modo
simulación y no publica nada real.

### 4.2 Primer despliegue

```bash
sam build --use-container
```

```bash
sam deploy --guided
```

Responde:

| Pregunta | Valor sugerido |
|---|---|
| Stack Name | `localizador-objetos-dev` |
| AWS Region | tu región (la misma del endpoint IoT) |
| `Entorno` | `dev` |
| `EndpointIoT` | el host del paso 4.1 |
| `OrigenCorsPermitido` | `*` en dev; el dominio exacto en prod |
| Confirm changes before deploy | `Y` |
| Allow SAM CLI IAM role creation | `Y` |
| Save arguments to configuration file | `Y` |

Al terminar imprime `UrlApi`, que es la URL base para la app cliente.

### 4.3 Despliegues siguientes

```bash
sam build --use-container
```

```bash
sam deploy
```

Para iterar rápido sobre una Lambda sin rehacer el stack completo:

```bash
sam sync --watch
```

> `sam sync` salta el ciclo de CloudFormation. Es para desarrollo, **no lo uses en prod**.

### 4.4 Eliminar el stack

```bash
sam delete
```

En `Entorno=prod` las tablas tienen `DeletionPolicy: Retain` y sobreviven a propósito:
borrarlas hay que hacerlo a mano y de forma deliberada.

---

## 5. API

Base: `https://{api-id}.execute-api.{region}.amazonaws.com/{entorno}`

| # | Método | Ruta | Qué hace |
|---|---|---|---|
| 1 | GET | `/objetos?categoria={categoria}` | Lista objetos de una categoría (Query sobre el GSI). Sin `categoria`, hace Scan. |
| 2 | GET | `/objetos/{object_id}` | Detalle de un objeto. |
| 3 | POST | `/objetos` | Registra un objeto nuevo. |
| 4 | PUT | `/objetos/{object_id}` | Actualiza la ubicación (parcial). |
| 5 | POST | `/objetos/{object_id}/localizar` | Publica la orden MQTT que enciende el LED. |
| 6 | GET | `/categorias` | Lista el catálogo de categorías. |

### Crear un objeto

```json
{
  "nombre": "Taladro percutor",
  "categoria": "herramientas",
  "almacen_id": "almacen-01",
  "pasillo": "A",
  "anaquel": "3",
  "nivel": "2",
  "posicion_led": 42,
  "color_indicador": "#00FF00"
}
```

`object_id` es opcional: si no lo mandas se genera un UUID. `color_indicador` también
(por defecto `#00FF00`). Responde `201` con el objeto creado, o `409` si el `object_id`
ya existía.

### Actualizar la ubicación

Actualización parcial: manda solo lo que cambia.

```json
{ "pasillo": "B", "anaquel": "1", "nivel": "4", "posicion_led": 117 }
```

Responde `200` con el objeto ya actualizado, o `404` si no existe.

### Localizar (dispara el LED)

Cuerpo opcional: `{ "duracion_segundos": 15 }` (por defecto 30, máximo 300).

Responde `202 Accepted` — la orden se publicó, pero que el LED encienda depende de
que el nodo esté conectado; el backend no puede confirmarlo.

Payload publicado en `almacen/{almacen_id}/led` con QoS 1:

```json
{
  "posicion_led": 42,
  "color_indicador": "#00FF00",
  "duracion_segundos": 15,
  "object_id": "obj-demo-001",
  "emitido_en": "2026-09-13T12:00:00+00:00"
}
```

Cada nodo ESP32 se suscribe únicamente al topic de su propio almacén.

### Paginación

`/objetos` y `/categorias` aceptan `limite` (1–200, por defecto 50) y `cursor`. La
respuesta trae `siguiente_cursor`; si es `null`, no hay más páginas.

```json
{ "elementos": [ ], "total_en_pagina": 20, "siguiente_cursor": "eyJvYmp..." }
```

Es paginación keyset, no `offset`: el coste no crece con el tamaño de la tabla.

### Errores

Formato uniforme:

```json
{ "error": "peticion_invalida", "mensaje": "'posicion_led' debe estar entre 0 y 65535." }
```

| Código | Cuándo |
|---|---|
| `400` | Cuerpo mal formado, campo inválido o cursor manipulado. |
| `404` | El `object_id` no existe. |
| `409` | Ya existe un objeto con ese `object_id`. |
| `500` | Error interno. El detalle va a CloudWatch, nunca al cliente. |
| `503` | DynamoDB o IoT Core saturados. Reintentable. |

---

## 6. Modelo de datos

**`{stack}-Objetos`** — PK `object_id` (S)

`nombre`, `categoria`, `almacen_id`, `pasillo`, `anaquel`, `nivel`,
`posicion_led` (N), `color_indicador`, `ultima_actualizacion` (ISO-8601 UTC).

GSI **`categoria-index`**: PK `categoria`, SK `nombre`, proyección `ALL`.
Permite listar por categoría con un Query de coste proporcional a los resultados,
en vez de un Scan de la tabla entera, y devuelve los objetos ya ordenados por nombre.

**`{stack}-Categorias`** — PK `categoria_id` (S), con `nombre` y `descripcion`.

Ambas en `PAY_PER_REQUEST` (no se paga capacidad ociosa) y con cifrado en reposo.
En `prod` además llevan Point-in-Time Recovery.

> Las tablas se llaman `{nombre-del-stack}-Objetos` y no `Objetos` a secas, para poder
> tener `dev` y `prod` en la misma cuenta sin colisionar. El código nunca ve esos
> nombres: los recibe por variable de entorno.

---

## 7. Decisiones de seguridad

**IAM mínimo, función por función.** Cada Lambda declara solo las acciones que ejecuta,
sobre el ARN exacto:

| Función | Permisos |
|---|---|
| `FnListarObjetos` | `dynamodb:Query` sobre el GSI + `Scan` sobre la tabla |
| `FnObtenerObjeto` | `dynamodb:GetItem` |
| `FnCrearObjeto` | `dynamodb:PutItem` (sin `GetItem`: la unicidad la resuelve una `ConditionExpression`) |
| `FnActualizarObjeto` | `dynamodb:UpdateItem` |
| `FnLocalizarObjeto` | `dynamodb:GetItem` + `iot:Publish` acotado a `topic/almacen/*/led` |
| `FnListarCategorias` | `dynamodb:Scan` sobre `Categorias` |

Ninguna función puede leer la tabla que no le toca, ni publicar en un topic fuera del
patrón del proyecto.

**Inyección de topic MQTT.** `almacen_id` se interpola en el nombre del topic. Un valor
con `/`, `#` o `+` permitiría publicar en topics ajenos o hacer un broadcast a todos
los almacenes. Se valida contra `^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$` al crear el objeto
**y otra vez** justo antes de publicar, en `iot.py`.

**Escrituras seguras.** `crear` usa `attribute_not_exists(object_id)` y `actualizar`
usa `attribute_exists(object_id)`: nada de leer-y-luego-escribir, que deja una ventana
de carrera. `actualizar` además solo acepta campos de una lista blanca, así que un
cliente no puede inyectar atributos arbitrarios en el item.

**Errores que no filtran.** Solo los errores de dominio llevan su mensaje al cliente.
Cualquier otra excepción se registra completa en CloudWatch y sale como `500` genérico,
sin trazas ni nombres de recursos.

**CORS.** Configurado en la API y además en cada respuesta. Las `GatewayResponses`
`DEFAULT_4XX`/`DEFAULT_5XX` añaden las cabeceras a los errores que genera la propia
API Gateway; sin eso, el navegador vería un error de red opaco en vez del código real.

**Throttling.** El stage limita a 25 req/s con ráfagas de 50. Evita que un cliente en
bucle sature DynamoDB o bombardee de órdenes a los nodos ESP32.

**Sin secretos en el repositorio.** Todo va por variables de entorno o parámetros de
CloudFormation. `env.json`, `.env`, `*.pem` y `*.key` están en `.gitignore`.

---

## 8. Pendiente (siguientes sesiones)

- **Autenticación con Cognito.** Mientras no exista, la API es pública: no la
  despliegues con datos reales, y mantén `OrigenCorsPermitido` acotado.
- **Firmware del ESP32**: suscripción a `almacen/{id}/led`, certificado por dispositivo
  y política IoT que lo limite a su propio topic.
- **Módulo de visión** (Rekognition / SageMaker).
- **CI/CD**: `sam validate --lint` + `pytest` en cada push.
