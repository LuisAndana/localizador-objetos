"""Datos de demostración para el modo local. Son placeholders, no datos reales."""

import sqlite3

from localizador.modelos import ahora_iso

CATEGORIAS = [
    ("herramientas", "Herramientas", "Herramienta manual y eléctrica"),
    ("refacciones", "Refacciones", "Piezas de repuesto para maquinaria"),
    ("consumibles", "Consumibles", "Material de uso y desgaste"),
    ("electronica", "Electrónica", "Componentes y equipo de medición"),
]

# (object_id, nombre, categoria, almacen, pasillo, anaquel, nivel, posicion_led, color, cantidad)
OBJETOS = [
    ("obj-demo-001", "Taladro percutor", "herramientas", "almacen-01", "A", "3", "2", 42, "#00FF00", 2),
    ("obj-demo-002", "Llave de torque", "herramientas", "almacen-01", "A", "4", "1", 57, "#00AAFF", 3),
    ("obj-demo-003", "Juego de desarmadores", "herramientas", "almacen-01", "A", "1", "3", 12, "#FFD400", 5),
    ("obj-demo-004", "Rodamiento 6204", "refacciones", "almacen-02", "C", "1", "3", 8, "#FF8800", 24),
    ("obj-demo-005", "Banda de transmisión", "refacciones", "almacen-02", "C", "2", "1", 23, "#FF3B30", 6),
    ("obj-demo-006", "Filtro de aire", "refacciones", "almacen-02", "D", "1", "2", 61, "#AF52DE", 10),
    ("obj-demo-007", "Cinta aislante", "consumibles", "almacen-01", "B", "2", "1", 88, "#00FF00", 40),
    ("obj-demo-008", "Guantes de nitrilo", "consumibles", "almacen-01", "B", "3", "2", 95, "#00AAFF", 120),
    ("obj-demo-009", "Tornillos M6 (caja)", "consumibles", "almacen-01", "B", "5", "4", 117, "#FFD400", 15),
    ("obj-demo-010", "Multímetro digital", "electronica", "almacen-02", "E", "1", "2", 74, "#00FF00", 4),
    ("obj-demo-011", "Sensor de proximidad", "electronica", "almacen-02", "E", "2", "3", 83, "#FF3B30", 8),
    ("obj-demo-012", "Fuente de 12 V", "electronica", "almacen-02", "E", "3", "1", 99, "#00AAFF", 7),
]


def sembrar(con: sqlite3.Connection) -> None:
    con.executemany(
        "INSERT OR IGNORE INTO categorias (categoria_id, nombre, descripcion) VALUES (?, ?, ?)",
        CATEGORIAS,
    )
    marca = ahora_iso()
    con.executemany(
        """INSERT OR IGNORE INTO objetos
           (object_id, nombre, categoria, almacen_id, pasillo, anaquel, nivel,
            posicion_led, color_indicador, cantidad, ultima_actualizacion)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        [(*o, marca) for o in OBJETOS],
    )
