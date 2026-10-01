import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "layers" / "common"))

os.environ.setdefault("TABLA_OBJETOS", "tabla-objetos-test")
os.environ.setdefault("TABLA_CATEGORIAS", "tabla-categorias-test")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
