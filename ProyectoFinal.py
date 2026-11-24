

"""
OVERCOOKED con Pyxel
--------------------
Requisito:  pip install pyxel
Ejecutar:   python overcooked_pyxel.py

Controles:
    Flechas o WASD ... moverte / mirar hacia una estacion
    ESPACIO .......... coger / dejar / usar la estacion que tienes delante
    R ................ reiniciar (en la pantalla final)
    ESC .............. salir

Estaciones:
    Cajas (tomate / lechuga) ... sacan ingredientes
    Tabla de cortar ............ deja un ingrediente y pulsa ESPACIO 4 veces (manos vacias)
    Olla ....................... echa tomate picado; tras unos segundos hay sopa
    Pila de platos ............. coge un plato para montar el pedido
    Mesas ...................... dejar y coger cosas
    Papelera ................... tirar cosas (el plato se vacia)
    OUT (amarilla) ............. entrega el plato con el pedido
"""

import random
import pyxel
# ----------------------------------------------------------------------
# CONFIGURACION
# ----------------------------------------------------------------------
TILE = 16
COLS, ROWS = 12, 6
MAP_Y = 24                       # espacio para el HUD superior
ANCHO = COLS * TILE              # 192
ALTO = MAP_Y + ROWS * TILE + 24  # 144 (24 extra abajo para los pedidos)
FPS = 30

MAPA = [
    "############",
    "#T L C O P #",
    "#          S",
    "#          #",
    "#M M    X  #",
    "############",
]
POS_INICIAL = (2, 5)             # (fila, columna)

DURACION_PARTIDA = 120 * FPS     # 120 segundos
GOLPES_PICAR = 4
FRAMES_COCINAR = 6 * FPS
FRAMES_QUEMAR = 8 * FPS          # tras estar lista
MAX_PEDIDOS = 3
PACIENCIA = 50 * FPS

ESTACIONES = "TLPCOMXS"
CAJAS = {"T": "tomate", "L": "lechuga"}
CORTADOS = {"tomate": "tomate_cortado", "lechuga": "lechuga_cortada"}
APTOS_PARA_PLATO = {"tomate_cortado", "lechuga_cortada", "sopa"}

RECETAS = {
    "ENS. MIXTA": ["lechuga_cortada", "tomate_cortado"],
    "ENS. LECHUGA": ["lechuga_cortada"],
    "SOPA TOMATE": ["sopa"],
}

# Nota: la fuente de Pyxel solo tiene caracteres ASCII (sin tildes ni signos
# de apertura), por eso los textos que se dibujan no llevan acentos.
NOMBRES = {
    "tomate": "tomate",
    "lechuga": "lechuga",
    "tomate_cortado": "tomate picado",
    "lechuga_cortada": "lechuga picada",
    "sopa": "sopa",
    "quemado": "sopa quemada",
}

# Colores de la paleta por defecto de Pyxel
NEGRO, AZUL_OSC, MORADO, VERDE_OSC, MARRON, GRIS_OSC = 0, 1, 2, 3, 4, 5
AZUL_CLARO, BLANCO, ROJO, NARANJA, AMARILLO, VERDE = 6, 7, 8, 9, 10, 11
CIELO, GRIS, ROSA, PIEL = 12, 13, 14, 15


# ----------------------------------------------------------------------
# OBJETOS
# ----------------------------------------------------------------------
class Plato:
    def __init__(self):
        self.contenido = []


def nombre(obj):
    if obj is None:
        return "nada"
    if isinstance(obj, Plato):
        if not obj.contenido:
            return "plato vacio"
        return "plato: " + " + ".join(NOMBRES[i] for i in obj.contenido)
    return NOMBRES[obj]


def anadir_a_plato(plato, item):
    if isinstance(item, str) and item in APTOS_PARA_PLATO \
            and item not in plato.contenido:
        plato.contenido.append(item)
        return True
    return False


# ----------------------------------------------------------------------
# DIBUJO DE OBJETOS
# ----------------------------------------------------------------------
def dibujar_ingrediente(item, cx, cy):
    if item == "tomate":
        pyxel.circ(cx, cy, 3, ROJO)
        pyxel.pset(cx - 1, cy - 1, ROSA)
        pyxel.rect(cx, cy - 4, 1, 2, VERDE_OSC)
    elif item == "tomate_cortado":
        pyxel.rect(cx - 4, cy - 2, 3, 5, ROJO)
        pyxel.rect(cx, cy - 2, 3, 5, ROSA)
        pyxel.rect(cx + 3, cy - 2, 2, 5, ROJO)
    elif item == "lechuga":
        pyxel.circ(cx, cy, 3, VERDE)
        pyxel.circb(cx, cy, 3, VERDE_OSC)
    elif item == "lechuga_cortada":
        pyxel.rect(cx - 4, cy - 2, 8, 2, VERDE)
        pyxel.rect(cx - 3, cy, 7, 2, VERDE_OSC)
        pyxel.rect(cx - 4, cy + 2, 6, 1, VERDE)
    elif item == "sopa":
        pyxel.circ(cx, cy, 3, NARANJA)
        pyxel.pset(cx - 1, cy - 1, AMARILLO)
    elif item == "quemado":
        pyxel.circ(cx, cy, 3, NEGRO)
        pyxel.circb(cx, cy, 3, GRIS)


def dibujar_objeto(obj, cx, cy):
    """Dibuja lo que lleva el jugador / hay sobre una estacion."""
    if obj is None:
        return
    if isinstance(obj, Plato):
        pyxel.circ(cx, cy, 5, BLANCO)
        pyxel.circb(cx, cy, 5, GRIS)
        n = len(obj.contenido)
        for k, item in enumerate(obj.contenido):
            dx = 0 if n == 1 else (-3 if k == 0 else 3)
            dibujar_ingrediente(item, cx + dx, cy)
    else:
        dibujar_ingrediente(obj, cx, cy)


def barra(x, y, ancho, frac, col=None):
    frac = max(0.0, min(1.0, frac))
    if col is None:
        col = VERDE if frac > 0.5 else (AMARILLO if frac > 0.25 else ROJO)
    pyxel.rect(x, y, ancho, 2, NEGRO)
    pyxel.rect(x, y, int(ancho * frac), 2, col)


# ----------------------------------------------------------------------
# JUEGO
# ----------------------------------------------------------------------
class Juego:
    def __init__(self):
        pyxel.init(ANCHO, ALTO, title="Overcooked UC3M", fps=FPS)
        self.estado = "menu"          # menu / juego / fin
        self.reiniciar()
        pyxel.run(self.update, self.draw)

    # ---------------- estado ----------------
    def reiniciar(self):
        self.estaciones = {}
        for f, fila in enumerate(MAPA):
            for c, ch in enumerate(fila):
                if ch in ESTACIONES:
                    self.estaciones[(f, c)] = {
                        "tipo": ch, "item": None, "progreso": 0}
        self.pos = POS_INICIAL
        self.mira = (-1, 0)           # (dfila, dcolumna)
        self.mano = None
        self.pedidos = []
        self.puntos = 0
        self.entregados = 0
        self.tiempo = DURACION_PARTIDA
        self.espera_pedido = 0
        self.msg = ""
        self.msg_t = 0

    def decir(self, texto):
        self.msg = texto
        self.msg_t = 2 * FPS

    # ---------------- logica ----------------
    def update(self):
        if self.estado == "menu":
            if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_RETURN):
                self.reiniciar()
                self.estado = "juego"
        elif self.estado == "juego":
            self.update_juego()
        elif self.estado == "fin":
            if pyxel.btnp(pyxel.KEY_R):
                self.reiniciar()
                self.estado = "juego"

    def update_juego(self):
        # Entrada
        if pyxel.btnp(pyxel.KEY_UP, 6, 3) or pyxel.btnp(pyxel.KEY_W, 6, 3):
            self.mover(-1, 0)
        elif pyxel.btnp(pyxel.KEY_DOWN, 6, 3) or pyxel.btnp(pyxel.KEY_S, 6, 3):
            self.mover(1, 0)
        elif pyxel.btnp(pyxel.KEY_LEFT, 6, 3) or pyxel.btnp(pyxel.KEY_A, 6, 3):
            self.mover(0, -1)
        elif pyxel.btnp(pyxel.KEY_RIGHT, 6, 3) or pyxel.btnp(pyxel.KEY_D, 6, 3):
            self.mover(0, 1)

        if pyxel.btnp(pyxel.KEY_SPACE):
            f, c = self.pos[0] + self.mira[0], self.pos[1] + self.mira[1]
            est = self.estaciones.get((f, c))
            if est is not None:
                self.interactuar(est)

        # Tiempo
        self.tiempo -= 1
        if self.msg_t > 0:
            self.msg_t -= 1
        self.actualizar_ollas()
        self.actualizar_pedidos()
        if self.tiempo <= 0:
            self.estado = "fin"

    def mover(self, df, dc):
        self.mira = (df, dc)
        f, c = self.pos[0] + df, self.pos[1] + dc
        if MAPA[f][c] == " ":
            self.pos = (f, c)

    def actualizar_ollas(self):
        for est in self.estaciones.values():
            if est["tipo"] != "O":
                continue
            if est["item"] == "tomate_cortado":
                est["progreso"] += 1
                if est["progreso"] >= FRAMES_COCINAR:
                    est["item"] = "sopa"
                    est["progreso"] = 0
                    self.decir("La sopa esta lista!")
            elif est["item"] == "sopa":
                est["progreso"] += 1
                if est["progreso"] >= FRAMES_QUEMAR:
                    est["item"] = "quemado"
                    est["progreso"] = 0
                    self.decir("Se ha quemado la sopa!")

    def actualizar_pedidos(self):
        for p in self.pedidos[:]:
            p["paciencia"] -= 1
            if p["paciencia"] <= 0:
                self.pedidos.remove(p)
                self.puntos -= 5
                self.decir("Pedido perdido (-5)")
        self.espera_pedido -= 1
        if len(self.pedidos) < MAX_PEDIDOS and (
                self.espera_pedido <= 0 or not self.pedidos):
            nombre_p = random.choice(list(RECETAS.keys()))
            self.pedidos.append({"nombre": nombre_p, "paciencia": PACIENCIA})
            self.espera_pedido = random.randint(10, 16) * FPS

    def entregar(self):
        plato = self.mano
        for p in self.pedidos:
            if sorted(RECETAS[p["nombre"]]) == sorted(plato.contenido):
                bonus = p["paciencia"] // (5 * FPS)
                self.puntos += 20 + bonus
                self.entregados += 1
                self.pedidos.remove(p)
                self.mano = None
                self.decir("Entregado! +%d puntos" % (20 + bonus))
                return
        self.decir("Nadie ha pedido eso")

    # ---------------- interaccion ----------------
    def interactuar(self, est):
        tipo = est["tipo"]
        mano = self.mano

        if tipo in CAJAS:                                   # cajas
            if mano is None:
                self.mano = CAJAS[tipo]
                self.decir("Coges " + NOMBRES[self.mano])
            else:
                self.decir("Tienes las manos ocupadas")

        elif tipo == "P":                                   # platos
            if mano is None:
                self.mano = Plato()
                self.decir("Coges un plato")
            else:
                self.decir("Tienes las manos ocupadas")

        elif tipo == "X":                                   # basura
            if mano is None:
                self.decir("No tienes nada que tirar")
            elif isinstance(mano, Plato):
                mano.contenido = []
                self.decir("Vacias el plato")
            else:
                self.mano = None
                self.decir("Lo tiras a la basura")

        elif tipo == "S":                                   # ventanilla
            if isinstance(mano, Plato) and mano.contenido:
                self.entregar()
            else:
                self.decir("Necesitas un plato con comida")

        elif tipo == "C":                                   # tabla
            self.usar_tabla(est)

        elif tipo == "O":                                   # olla
            self.usar_olla(est)

        elif tipo == "M":                                   # mesa
            self.usar_mesa(est)

    def usar_tabla(self, est):
        item, mano = est["item"], self.mano
        if item is None:
            if isinstance(mano, str) and mano in CORTADOS:
                est["item"], est["progreso"] = mano, 0
                self.mano = None
                self.decir("Pulsa ESPACIO para picar")
            else:
                self.decir("Pon tomate o lechuga crudos")
        elif item in CORTADOS:                              # crudo
            if mano is None:
                est["progreso"] += 1
                if est["progreso"] >= GOLPES_PICAR:
                    est["item"] = CORTADOS[item]
                    self.decir("Ya esta picado!")
                else:
                    self.decir("Picando %d/%d" % (est["progreso"], GOLPES_PICAR))
            else:
                self.decir("Necesitas las manos libres")
        else:                                               # ya picado
            if mano is None:
                self.mano, est["item"] = item, None
                self.decir("Coges " + NOMBRES[item])
            elif isinstance(mano, Plato) and anadir_a_plato(mano, item):
                est["item"] = None
                self.decir("Lo anades al plato")
            else:
                self.decir("Tienes las manos ocupadas")

    def usar_olla(self, est):
        item, mano = est["item"], self.mano
        if item is None:
            if mano == "tomate_cortado":
                est["item"], est["progreso"] = "tomate_cortado", 0
                self.mano = None
                self.decir("Cocinando sopa...")
            else:
                self.decir("Solo tomate picado")
        elif item == "tomate_cortado":
            self.decir("Aun se esta cocinando")
        elif item == "sopa":
            if isinstance(mano, Plato) and anadir_a_plato(mano, "sopa"):
                est["item"], est["progreso"] = None, 0
                self.decir("Sirves la sopa")
            else:
                self.decir("Necesitas un plato sin sopa")
        elif item == "quemado":
            if mano is None:
                self.mano = "quemado"
                est["item"], est["progreso"] = None, 0
                self.decir("Tirala a la basura!")
            else:
                self.decir("Tienes las manos ocupadas")

    def usar_mesa(self, est):
        item, mano = est["item"], self.mano
        if item is None:
            if mano is not None:
                est["item"], self.mano = mano, None
                self.decir("Lo dejas en la mesa")
            else:
                self.decir("La mesa esta vacia")
        elif mano is None:
            self.mano, est["item"] = item, None
            self.decir("Lo coges de la mesa")
        elif isinstance(mano, Plato) and anadir_a_plato(mano, item):
            est["item"] = None
            self.decir("Lo anades al plato")
        elif isinstance(item, Plato) and anadir_a_plato(item, mano):
            self.mano = None
            self.decir("Lo anades al plato de la mesa")
        else:
            self.decir("No se puede combinar")

    # ---------------- dibujo ----------------
    def draw(self):
        pyxel.cls(NEGRO)
        if self.estado == "menu":
            self.draw_menu()
            return
        self.draw_mapa()
        self.draw_jugador()
        self.draw_hud()
        self.draw_pedidos()
        if self.estado == "fin":
            self.draw_fin()

    def draw_mapa(self):
        for f, fila in enumerate(MAPA):
            for c, ch in enumerate(fila):
                x, y = c * TILE, MAP_Y + f * TILE
                if ch == "#":
                    pyxel.rect(x, y, TILE, TILE, GRIS_OSC)
                    pyxel.rectb(x, y, TILE, TILE, AZUL_OSC)
                elif ch == " ":
                    pyxel.rect(x, y, TILE, TILE,
                               AZUL_OSC if (f + c) % 2 == 0 else MORADO)
                else:
                    self.draw_estacion(self.estaciones[(f, c)], x, y)

    def draw_estacion(self, est, x, y):
        tipo, item = est["tipo"], est["item"]
        cx, cy = x + TILE // 2, y + TILE // 2
        if tipo in CAJAS:
            pyxel.rect(x, y, TILE, TILE, MARRON)
            pyxel.rectb(x, y, TILE, TILE, NARANJA)
            dibujar_ingrediente(CAJAS[tipo], cx, cy)
        elif tipo == "P":
            pyxel.rect(x, y, TILE, TILE, PIEL)
            for dy in (3, 0):
                pyxel.circ(cx, cy + dy, 5, BLANCO)
                pyxel.circb(cx, cy + dy, 5, GRIS)
        elif tipo == "C":
            pyxel.rect(x, y, TILE, TILE, PIEL)
            pyxel.rect(x + 2, y + 2, 12, 12, NARANJA)
            pyxel.rectb(x + 2, y + 2, 12, 12, MARRON)
            dibujar_objeto(item, cx, cy)
            if item in CORTADOS:
                barra(x + 1, y + 13, 14, est["progreso"] / GOLPES_PICAR, AZUL_CLARO)
        elif tipo == "O":
            pyxel.rect(x, y, TILE, TILE, GRIS)
            pyxel.circ(cx, cy, 7, AZUL_OSC)
            pyxel.circb(cx, cy, 7, GRIS_OSC)
            if item is not None:
                col = {"tomate_cortado": ROJO, "sopa": NARANJA,
                       "quemado": NEGRO}[item]
                pyxel.circ(cx, cy, 5, col)
            if item == "tomate_cortado":
                barra(x + 1, y + 13, 14, est["progreso"] / FRAMES_COCINAR, AZUL_CLARO)
            elif item == "sopa":
                # barra de "peligro": se vacia hasta que se quema
                barra(x + 1, y + 13, 14, 1 - est["progreso"] / FRAMES_QUEMAR)
        elif tipo == "M":
            pyxel.rect(x, y, TILE, TILE, PIEL)
            pyxel.rectb(x, y, TILE, TILE, MARRON)
            dibujar_objeto(item, cx, cy)
        elif tipo == "X":
            pyxel.rect(x, y, TILE, TILE, GRIS)
            pyxel.rect(x + 4, y + 4, 8, 10, GRIS_OSC)
            pyxel.rect(x + 3, y + 2, 10, 2, BLANCO)
        elif tipo == "S":
            pyxel.rect(x, y, TILE, TILE, AMARILLO)
            pyxel.rectb(x, y, TILE, TILE, NARANJA)
            pyxel.text(x + 2, y + 5, "OUT", NEGRO)

    def draw_jugador(self):
        f, c = self.pos
        x, y = c * TILE, MAP_Y + f * TILE
        cx = x + TILE // 2
        pyxel.rect(x + 4, y + 7, 8, 8, BLANCO)             # cuerpo
        pyxel.circ(cx, y + 6, 4, PIEL)                      # cabeza
        pyxel.rect(x + 4, y, 8, 3, BLANCO)                  # gorro
        pyxel.rect(x + 5, y + 2, 6, 2, BLANCO)
        df, dc = self.mira                                   # ojos
        ox, oy = dc * 2, df * 1
        pyxel.pset(cx - 1 + ox, y + 6 + oy, NEGRO)
        pyxel.pset(cx + 1 + ox, y + 6 + oy, NEGRO)
        # Lo que lleva, delante del cocinero
        dibujar_objeto(self.mano, cx + dc * 8, y + 8 + df * 8)

    def draw_hud(self):
        pyxel.rect(0, 0, ANCHO, MAP_Y, NEGRO)
        seg = max(0, (self.tiempo + FPS - 1) // FPS)
        pyxel.text(4, 3, "TIEMPO %3d   PUNTOS %d" % (seg, self.puntos), BLANCO)
        if self.msg_t > 0:
            pyxel.text(4, 14, self.msg, AMARILLO)
        else:
            pyxel.text(4, 14, "Mano: " + nombre(self.mano), PIEL)

    def draw_pedidos(self):
        y0 = MAP_Y + ROWS * TILE
        pyxel.rect(0, y0, ANCHO, 24, AZUL_OSC)
        for i, p in enumerate(self.pedidos):
            x = 3 + i * 64
            pyxel.text(x, y0 + 2, p["nombre"], BLANCO)
            for k, ing in enumerate(RECETAS[p["nombre"]]):
                dibujar_ingrediente(ing, x + 5 + k * 11, y0 + 14)
            barra(x, y0 + 20, 58, p["paciencia"] / PACIENCIA)

    def draw_menu(self):
        pyxel.rect(0, 0, ANCHO, ALTO, AZUL_OSC)
        pyxel.text(70, 6, "OVERCOOKED", AMARILLO)
        lineas = [
            "Flechas/WASD: moverte y mirar",
            "ESPACIO: coger / dejar / usar",
            "",
            "Cajas: sacan tomate y lechuga",
            "Tabla: ESPACIO x4 para picar",
            "Olla: tomate picado = sopa (no la quemes!)",
            "Plato: monta el pedido y llevalo a OUT",
            "Papelera: tira lo que no sirva",
            "",
            "Tienes 120 segundos. Suerte, chef!",
        ]
        for i, linea in enumerate(lineas):
            pyxel.text(8, 22 + i * 9, linea, BLANCO)
        if (pyxel.frame_count // 15) % 2 == 0:
            pyxel.text(40, ALTO - 14, "Pulsa ESPACIO para empezar", AMARILLO)

    def draw_fin(self):
        pyxel.rect(26, 34, 140, 66, NEGRO)
        pyxel.rectb(26, 34, 140, 66, AMARILLO)
        pyxel.text(66, 40, "FIN DEL SERVICIO", AMARILLO)
        pyxel.text(36, 54, "Pedidos entregados: %d" % self.entregados, BLANCO)
        pyxel.text(36, 64, "Puntuacion final:   %d" % self.puntos, BLANCO)
        if self.puntos >= 120:
            rango = "Chef con estrella Michelin!"
        elif self.puntos >= 60:
            rango = "Buen cocinero"
        else:
            rango = "Aprendiz de cocina"
        pyxel.text(36, 76, rango, VERDE)
        pyxel.text(36, 88, "R: reiniciar   ESC: salir", GRIS)


if __name__ == "__main__":
    Juego()