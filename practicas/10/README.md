# Imagen de contenedor de la app · Práctica 10

Foráneos Team · Cómputo en la Nube · Localizador inteligente de objetos

Una sola imagen con la app completa del modo local: la API en FastAPI (`main.py`),
la app web ya compilada (`frontend/dist`, servida en `/`) y la base SQLite. Se
construye en dos etapas (Node solo para compilar la app web) sobre
`python:3.12-slim` y corre con un usuario sin privilegios (`app`, uid 10001).

## Construir y ejecutar

Desde la raíz del repositorio:

```bash
docker build -t localizador-objetos:1.0.0 .
docker run -d --name localizador -p 8000:8000 -v localizador-datos:/datos localizador-objetos:1.0.0
curl http://127.0.0.1:8000/api/salud
```

La app web queda en http://127.0.0.1:8000. El volumen `localizador-datos` guarda
la base para que no se pierda al borrar el contenedor.

La misma imagen con otra configuración, sin reconstruir:

```bash
docker run -d --name localizador-prueba -p 8080:9000 -e PORT=9000 -e LOCALIZADOR_BD=/datos/prueba.db -e LOG_LEVEL=WARNING localizador-objetos:1.0.0
```

En Git Bash (Windows) antepón `MSYS_NO_PATHCONV=1` a ese comando: si no, Git Bash
convierte `/datos/prueba.db` en una ruta de Windows y la app no arranca.

## Variables de entorno

| Variable | Valor por defecto | Para qué sirve |
|---|---|---|
| `PORT` | `8000` | Puerto en el que escucha uvicorn |
| `LOCALIZADOR_BD` | `/datos/localizador.db` | Ruta de la base SQLite |
| `CORS_ALLOW_ORIGIN` | `http://localhost:8000` | Orígenes permitidos, separados por comas |
| `LOG_LEVEL` | `INFO` | Nivel de los registros de la app (`DEBUG`, `INFO`, `WARNING`…) |
| `DURACION_LED_DEFECTO` | `30` (en el código) | Opcional. Segundos que se enciende el LED si no se indican |
| `DURACION_LED_MAXIMA` | `300` (en el código) | Opcional. Máximo de segundos que se acepta |
| `LIMITE_PAGINA_DEFECTO` | `50` (en el código) | Opcional. Elementos por página en los listados |
| `LIMITE_PAGINA_MAXIMO` | `200` (en el código) | Opcional. Máximo de elementos que se pueden pedir |

## Publicar en Amazon ECR

Repositorio privado `localizador-objetos` en us-east-1, con etiquetas inmutables,
escaneo al subir y la política de ciclo de vida de `politica_ciclo_vida.json`
(borra las imágenes sin etiqueta y las `prueba-*` un día después de subirlas).
`<cuenta>` es el número de 12 dígitos de la cuenta; sale de
`aws sts get-caller-identity`. Sin llaves de acceso: la sesión se inicia con `aws login`.

```bash
aws ecr create-repository --repository-name localizador-objetos --region us-east-1 \
  --image-tag-mutability IMMUTABLE --image-scanning-configuration scanOnPush=true \
  --tags Key=Project,Value=foraneos-proyecto Key=Team,Value=foraneos-team Key=Environment,Value=dev Key=Equipo,Value=ForaneosTeam
aws ecr put-lifecycle-policy --repository-name localizador-objetos --region us-east-1 \
  --lifecycle-policy-text file://practicas/10/politica_ciclo_vida.json

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <cuenta>.dkr.ecr.us-east-1.amazonaws.com
docker tag localizador-objetos:1.0.0 <cuenta>.dkr.ecr.us-east-1.amazonaws.com/localizador-objetos:1.0.0
docker push <cuenta>.dkr.ecr.us-east-1.amazonaws.com/localizador-objetos:1.0.0
aws ecr describe-images --repository-name localizador-objetos --region us-east-1
```

Las etiquetas son inmutables: una versión nueva se sube con otra etiqueta (`1.0.1`),
y las de prueba con el prefijo `prueba-` para que la política las borre.

En Windows con Docker Desktop, `docker login` puede fallar con
`error storing credentials … The stub received bad data`: el token de ECR mide más
de 2560 caracteres, el máximo del administrador de credenciales de Windows. En ese
caso se usa el ayudante `docker-credential-ecr-login` que trae Docker Desktop
(`"credHelpers": { "<cuenta>.dkr.ecr.us-east-1.amazonaws.com": "ecr-login" }` en la
configuración de Docker) con las credenciales temporales de la sesión en variables
de entorno: `eval $(aws configure export-credentials --format env)`.

Docker Desktop sube la imagen como un índice OCI (la etiqueta `1.0.0`) con dos
manifiestos sin etiqueta: la imagen `linux/amd64` y la atestación de procedencia.
La regla de imágenes sin etiqueta no los borra mientras exista el índice, y el
escaneo se consulta con el digest de la imagen `linux/amd64`, no con la etiqueta.
