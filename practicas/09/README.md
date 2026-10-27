# Función `recalcular-metricas-busquedas` · Práctica 9

Foráneos Team · Cómputo en la Nube · Localizador inteligente de objetos

Recalcula el resumen de métricas cada vez que se confirma una búsqueda, para que
la consulta del indicador de tiempo lea **un solo registro** en lugar de recorrer
toda la tabla de búsquedas.

## Configuración

| Parámetro | Valor |
|---|---|
| Región | us-east-1 |
| Runtime | Python 3.12, arm64 |
| Memoria | 128 MB (usa ≈ 92 MB) |
| Tiempo de espera | 10 s |
| Variable de entorno | `TABLA_RESUMEN = localizador-objetos-p09-resumen` |
| Rol de ejecución | Propio: `AWSLambdaBasicExecutionRole` + política insertada `MetricasP09` (`politica_metricas.json`) |
| Disparador 1 | DynamoDB Streams de `localizador-objetos-p09-busquedas` (imágenes nuevas y antiguas, lote de 10, posición LATEST) |
| Disparador 2 | URL de función con autenticación `AWS_IAM` |

## Cómo funciona

- **Stream:** por cada cambio en la tabla de búsquedas, si la búsqueda acaba de
  recibir `confirmada_en`, suma 1 al total y su `duracion_ms` a la suma
  (`UpdateItem` con `ADD`, atómico). `total` es palabra reservada de DynamoDB,
  por eso se usa el alias `#total`.
- **URL (GET):** devuelve `{"total_busquedas": n, "promedio_ms": m}`.
  Cualquier otro método responde 405: la interfaz no modifica datos.

## Archivos

| Archivo | Contenido |
|---|---|
| `lambda_function.py` | Código de la función |
| `politica_metricas.json` | Permisos mínimos del rol (stream de búsquedas y tabla de resumen) |
| `eventos_prueba.json` | Eventos de prueba de la consola |

## Probar la URL (CloudShell, sin llaves de acceso)

```bash
URL="https://<id>.lambda-url.us-east-1.on.aws/"
eval $(aws configure export-credentials --format env)
curl -s --aws-sigv4 "aws:amz:us-east-1:lambda" \
     --user "$AWS_ACCESS_KEY_ID:$AWS_SECRET_ACCESS_KEY" \
     -H "x-amz-security-token: $AWS_SESSION_TOKEN" "$URL"
```

Sin firma la URL responde `403 Forbidden`.

No hay credenciales en este código: la función usa su rol de ejecución.
