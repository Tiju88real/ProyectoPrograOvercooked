import random
import pyxel

# =============================================================================
# CONSTANTES DEL JUEGO
# =============================================================================
ANCHO_PANTALLA = 192
ALTO_PANTALLA = 176
ALTO_TABLERO = 32
TAM_CASILLA = 16
COLS = 12
FILAS = 9
FPS = 30
ESCALA_PANTALLA = 4

DURACION_SERVICIO = 180 * FPS
RETRASO_PRIMER_PEDIDO = 3 * FPS
MAX_PEDIDOS_ACTIVOS = 3
MAX_FALLOS = 3
PEDIDOS_NIVEL_1 = 4

INGREDIENTES_CORTABLES = ("cebolla", "chorizo", "tomate", "patata")

RECETAS = {
    "gazpacho": {
        "nombre": "GAZPACHO",
        "aparato": "batidora",
        "req": [("tomate", "cortado"), ("cebolla", "cortado")],
        "puntos": 10,
        "penalizacion": 5,
        "tiempo": 48 * FPS,
    },
    "tortilla": {
        "nombre": "TORTILLA",
        "aparato": "sarten",
        "req": [("patata", "cortado"), ("cebolla", "cortado"), ("huevo", "entero")],
        "puntos": 12,
        "penalizacion": 6,
        "tiempo": 60 * FPS,
    },
    "huevos_rotos": {
        "nombre": "H.ROTOS",
        "aparato": "sarten",
        "req": [("patata", "cortado"), ("huevo", "entero"), ("chorizo", "cortado")],
        "puntos": 12,
        "penalizacion": 6,
        "tiempo": 60 * FPS,
    },
}

MAPA_COCINA = [
    "EchzETEMEEDE",
    "............",
    "............",
    "............",
    "PBPSSPPSSPPP",
    "............",
    "............",
    "............",
    "EtpEETEFEELE",
]


# =============================================================================
# MODELO DE INGREDIENTES, PLATOS Y PEDIDOS
# =============================================================================

class Ingrediente:
    """Representa una unidad de ingrediente con su estado."""

    def __init__(self, nombre):
        self._nombre = nombre
        self._estado = "entero"

    @property
    def nombre(self):
        return self._nombre

    @property
    def estado(self):
        return self._estado

    def cortar(self):
        if self._nombre in INGREDIENTES_CORTABLES and self._estado == "entero":
            self._estado = "cortado"

    def procesar(self, tipo_aparato):
        self._estado = "triturado" if tipo_aparato == "batidora" else "cocinado"

    def clave(self):
        return (self._nombre, self._estado)

    def color(self):
        colores = {
            "cebolla": 14,
            "huevo": 10,
            "chorizo": 8,
            "tomate": 8,
            "patata": 9,
        }
        return 4 if self._estado in ("triturado", "cocinado") else colores.get(self._nombre, 13)


class Plato:
    """Contenedor simple que transporta ingredientes o una receta lista."""

    def __init__(self):
        self._ingredientes = []
        self._preparacion = None

    @property
    def ingredientes(self):
        return self._ingredientes

    @property
    def preparacion(self):
        return self._preparacion

    @property
    def esta_vacio(self):
        return len(self._ingredientes) == 0 and self._preparacion is None

    def agregar_ingrediente(self, ingrediente):
        if self._preparacion is None:
            self._ingredientes.append(ingrediente)

    def establecer_preparacion(self, nombre_receta):
        self._ingredientes = []
        self._preparacion = nombre_receta

    def transferir_a(self, otro_plato):
        if otro_plato.preparacion is not None or self._preparacion is not None:
            return
        for ing in self._ingredientes:
            otro_plato.agregar_ingrediente(ing)
        self._ingredientes = []

    def vaciar(self):
        self._ingredientes = []
        self._preparacion = None

    def dibujar(self, x, y):
        pyxel.circ(x, y, 4, 7)
        pyxel.circb(x, y, 4, 13)
        if self._preparacion is not None:
            color = 8 if self._preparacion == "gazpacho" else 10
            pyxel.circ(x, y, 2, color)
        elif self._ingredientes:
            pyxel.circ(x, y, 2, self._ingredientes[-1].color())


class Pedido:
    """Comanda activa en el tablero superior."""

    def __init__(self, id_receta):
        datos = RECETAS[id_receta]
        self._id_receta = id_receta
        self._nombre = datos["nombre"]
        self._puntos = datos["puntos"]
        self._penalizacion = datos["penalizacion"]
        self._tiempo_total = datos["tiempo"]
        self._tiempo_restante = datos["tiempo"]

    @property
    def id_receta(self):
        return self._id_receta

    @property
    def puntos(self):
        return self._puntos

    @property
    def penalizacion(self):
        return self._penalizacion

    @property
    def expirado(self):
        return self._tiempo_restante <= 0

    def actualizar(self):
        self._tiempo_restante = max(0, self._tiempo_restante - 1)

    def dibujar(self, x, y):
        pyxel.rect(x, y, 42, 26, 7)
        pyxel.rectb(x, y, 42, 26, 4)
        pyxel.rect(x, y, 42, 8, 9)
        pyxel.text(x + 2, y + 1, self._nombre[:8], 0)

        reqs = RECETAS[self._id_receta]["req"]
        resumen = "".join(r[0][0].upper() for r in reqs)
        seg = self._tiempo_restante // FPS
        pyxel.text(x + 2, y + 11, f"{resumen} {seg}s", 0)

        ratio = self._tiempo_restante / self._tiempo_total
        ancho = int(38 * ratio)
        color = 11 if ratio > 0.5 else (10 if ratio > 0.25 else 8)
        pyxel.rect(x + 2, y + 21, ancho, 3, color)


# =============================================================================
# ENTIDADES: CHEFS Y ESTACIONES
# =============================================================================

class Entidad:
    def __init__(self, x, y, w, h):
        self._x = x
        self._y = y
        self._w = w
        self._h = h

    def colisiona(self, ox, oy, ow, oh):
        return (
            ox < self._x + self._w
            and ox + ow > self._x
            and oy < self._y + self._h
            and oy + oh > self._y
        )


class Chef(Entidad):
    def __init__(self, x, y, color_camisa, controles):
        super().__init__(x, y, 12, 12)
        self._color_camisa = color_camisa
        self._controles = controles
        self._velocidad = 2
        self._dir_x = 0
        self._dir_y = 1
        self._plato = None

    @property
    def plato(self):
        return self._plato

    @plato.setter
    def plato(self, nuevo_plato):
        self._plato = nuevo_plato

    def actualizar(self, cocina):
        dx, dy = 0, 0
        if pyxel.btn(self._controles["izq"]):
            dx = -self._velocidad
            self._dir_x, self._dir_y = -1, 0
        if pyxel.btn(self._controles["der"]):
            dx = self._velocidad
            self._dir_x, self._dir_y = 1, 0
        if pyxel.btn(self._controles["arr"]):
            dy = -self._velocidad
            self._dir_x, self._dir_y = 0, -1
        if pyxel.btn(self._controles["aba"]):
            dy = self._velocidad
            self._dir_x, self._dir_y = 0, 1

        self._mover(dx, dy, cocina)

        if pyxel.btnp(self._controles["accion"]):
            estacion = self.obtener_estacion_objetivo(cocina)
            if estacion is not None:
                estacion.interactuar(self)

    def _mover(self, dx, dy, cocina):
        nx = max(0, min(ANCHO_PANTALLA - self._w, self._x + dx))
        if not cocina.colisiona_solido(nx, self._y, self._w, self._h):
            self._x = nx

        ny = max(ALTO_TABLERO, min(ALTO_PANTALLA - self._h, self._y + dy))
        if not cocina.colisiona_solido(self._x, ny, self._w, self._h):
            self._y = ny

    def obtener_estacion_objetivo(self, cocina):
        """Busca primero justo delante del chef y, si no hay nada, la estación adyacente más cercana."""
        cx = self._x + self._w // 2
        cy = self._y + self._h // 2

        # 1. Comprobar delante según hacia dónde mira
        for dist in (8, 12, 16):
            tx = cx + self._dir_x * dist
            ty = cy + self._dir_y * dist
            est = cocina.obtener_estacion(tx // TAM_CASILLA, (ty - ALTO_TABLERO) // TAM_CASILLA)
            if est is not None and not isinstance(est, Pared):
                return est

        # 2. Comprobar las 4 direcciones adyacentes por si el jugador no giró exactamente
        mejor_est = None
        menor_dist = 18
        for ox, oy in ((0, -12), (0, 12), (-12, 0), (12, 0)):
            tx, ty = cx + ox, cy + oy
            est = cocina.obtener_estacion(tx // TAM_CASILLA, (ty - ALTO_TABLERO) // TAM_CASILLA)
            if est is not None and not isinstance(est, Pared):
                ex = est._x + TAM_CASILLA // 2
                ey = est._y + TAM_CASILLA // 2
                d = ((cx - ex) ** 2 + (cy - ey) ** 2) ** 0.5
                if d < menor_dist:
                    menor_dist = d
                    mejor_est = est
        return mejor_est

    def dibujar(self):
        pyxel.rect(self._x + 1, self._y + 10, 10, 3, 5)
        pyxel.rect(self._x + 1, self._y + 4, 10, 7, self._color_camisa)
        pyxel.rect(self._x + 3, self._y + 6, 6, 5, 7)
        pyxel.rect(self._x + 2, self._y, 8, 5, 15)
        pyxel.rect(self._x + 2, self._y - 4, 8, 4, 7)
        pyxel.rectb(self._x + 2, self._y - 4, 8, 4, 13)

        ox = self._x + 5 + self._dir_x * 2
        oy = self._y + 2 + self._dir_y
        pyxel.pset(ox, oy, 0)
        pyxel.pset(ox + 2, oy, 0)

        if self._plato is not None:
            px = self._x + 6 + self._dir_x * 7
            py = self._y + 6 + self._dir_y * 7
            self._plato.dibujar(px, py)


class Estacion(Entidad):
    def __init__(self, col, fila, color_fondo=4, color_borde=9):
        super().__init__(
            col * TAM_CASILLA,
            ALTO_TABLERO + fila * TAM_CASILLA,
            TAM_CASILLA,
            TAM_CASILLA,
        )
        self._color_fondo = color_fondo
        self._color_borde = color_borde

    def interactuar(self, chef):
        pass

    def dibujar(self, resaltada=False):
        pyxel.rect(self._x, self._y, self._w, self._h, self._color_fondo)
        pyxel.rect(self._x + 1, self._y + 1, self._w - 2, self._h - 4, self._color_borde)
        pyxel.rectb(self._x, self._y, self._w, self._h, 7 if resaltada else 0)


class Pared(Estacion):
    def __init__(self, col, fila):
        super().__init__(col, fila, color_fondo=5, color_borde=13)


class Superficie(Estacion):
    def __init__(self, col, fila, color_fondo=4, color_borde=9):
        super().__init__(col, fila, color_fondo, color_borde)
        self._plato = None

    def interactuar(self, chef):
        if chef.plato is None and self._plato is not None:
            chef.plato = self._plato
            self._plato = None
        elif chef.plato is not None and self._plato is None:
            self._plato = chef.plato
            chef.plato = None
        elif chef.plato is not None and self._plato is not None and not chef.plato.esta_vacio:
            chef.plato.transferir_a(self._plato)

    def dibujar(self, resaltada=False):
        super().dibujar(resaltada)
        if self._plato is not None:
            self._plato.dibujar(self._x + 8, self._y + 7)


class SuperficiePaso(Superficie):
    def __init__(self, col, fila):
        super().__init__(col, fila, color_fondo=9, color_borde=15)


class Cajon(Estacion):
    def __init__(self, col, fila, nombre_ingrediente, letra):
        super().__init__(col, fila, color_fondo=4, color_borde=9)
        self._nombre_ingrediente = nombre_ingrediente
        self._letra = letra

    def interactuar(self, chef):
        if chef.plato is not None:
            chef.plato.agregar_ingrediente(Ingrediente(self._nombre_ingrediente))

    def dibujar(self, resaltada=False):
        super().dibujar(resaltada)
        pyxel.text(self._x + 6, self._y + 5, self._letra, 7)


class TablaCortar(Estacion):
    def __init__(self, col, fila):
        super().__init__(col, fila, color_fondo=4, color_borde=9)
        self._ingredientes = []

    def interactuar(self, chef):
        if chef.plato is None:
            return
        if not chef.plato.esta_vacio and not self._ingredientes and chef.plato.preparacion is None:
            for ing in chef.plato.ingredientes:
                ing.cortar()
                self._ingredientes.append(ing)
            chef.plato.vaciar()
        elif chef.plato.esta_vacio and self._ingredientes:
            for ing in self._ingredientes:
                chef.plato.agregar_ingrediente(ing)
            self._ingredientes = []

    def dibujar(self, resaltada=False):
        super().dibujar(resaltada)
        pyxel.rect(self._x + 3, self._y + 3, 10, 8, 7)
        if self._ingredientes:
            pyxel.circ(self._x + 8, self._y + 7, 2, self._ingredientes[-1].color())


class Aparato(Estacion):
    def __init__(self, col, fila, tipo_aparato, color_aparato):
        super().__init__(col, fila, color_fondo=4, color_borde=9)
        self._tipo_aparato = tipo_aparato
        self._color_aparato = color_aparato
        self._contenido_ingredientes = []
        self._preparacion_lista = None

    def interactuar(self, chef):
        if chef.plato is None:
            return
        esta_vacio = not self._contenido_ingredientes and self._preparacion_lista is None

        if not chef.plato.esta_vacio and esta_vacio and chef.plato.preparacion is None:
            self._procesar(chef.plato.ingredientes)
            chef.plato.vaciar()
        elif chef.plato.esta_vacio and not esta_vacio:
            if self._preparacion_lista is not None:
                chef.plato.establecer_preparacion(self._preparacion_lista)
                self._preparacion_lista = None
            else:
                for ing in self._contenido_ingredientes:
                    chef.plato.agregar_ingrediente(ing)
                self._contenido_ingredientes = []

    def _procesar(self, ingredientes):
        claves = sorted(ing.clave() for ing in ingredientes)
        for id_receta, datos in RECETAS.items():
            if datos["aparato"] == self._tipo_aparato and sorted(datos["req"]) == claves:
                self._preparacion_lista = id_receta
                return
        for ing in ingredientes:
            ing.procesar(self._tipo_aparato)
            self._contenido_ingredientes.append(ing)

    def dibujar(self, resaltada=False):
        super().dibujar(resaltada)
        pyxel.circ(self._x + 8, self._y + 7, 4, self._color_aparato)
        if self._preparacion_lista is not None:
            pyxel.circ(self._x + 8, self._y + 7, 2, 11)
        elif self._contenido_ingredientes:
            pyxel.circ(self._x + 8, self._y + 7, 2, 4)


class Batidora(Aparato):
    def __init__(self, col, fila):
        super().__init__(col, fila, "batidora", color_aparato=12)


class Sarten(Aparato):
    def __init__(self, col, fila):
        super().__init__(col, fila, "sarten", color_aparato=0)


class PilaPlatos(Estacion):
    def __init__(self, col, fila):
        super().__init__(col, fila, color_fondo=4, color_borde=9)

    def interactuar(self, chef):
        if chef.plato is None:
            chef.plato = Plato()

    def dibujar(self, resaltada=False):
        super().dibujar(resaltada)
        pyxel.circ(self._x + 8, self._y + 7, 4, 7)
        pyxel.circb(self._x + 8, self._y + 7, 2, 13)


class Basura(Estacion):
    def __init__(self, col, fila):
        super().__init__(col, fila, color_fondo=5, color_borde=2)

    def interactuar(self, chef):
        if chef.plato is not None and not chef.plato.esta_vacio:
            chef.plato.vaciar()

    def dibujar(self, resaltada=False):
        super().dibujar(resaltada)
        pyxel.rect(self._x + 4, self._y + 3, 8, 8, 0)


class MostradorEntrega(Estacion):
    def __init__(self, col, fila, gestor_pedidos):
        super().__init__(col, fila, color_fondo=9, color_borde=10)
        self._gestor = gestor_pedidos

    def interactuar(self, chef):
        if chef.plato is not None and not chef.plato.esta_vacio:
            self._gestor.entregar_plato(chef.plato)
            chef.plato = None

    def dibujar(self, resaltada=False):
        super().dibujar(resaltada)
        pyxel.text(self._x + 6, self._y + 5, "E", 0)


# =============================================================================
# GESTIÓN DE COCINA, PEDIDOS Y BUCLE PRINCIPAL
# =============================================================================

class Cocina:
    def __init__(self, gestor_pedidos):
        self._estaciones = {}
        self._cargar_mapa(gestor_pedidos)

    def _cargar_mapa(self, gestor_pedidos):
        for fila, linea in enumerate(MAPA_COCINA):
            for col, simb in enumerate(linea):
                est = self._crear_estacion(simb, col, fila, gestor_pedidos)
                if est is not None:
                    self._estaciones[(col, fila)] = est

    def _crear_estacion(self, simb, col, fila, gestor_pedidos):
        mapa_cajones = {
            "c": ("cebolla", "C"),
            "h": ("huevo", "H"),
            "z": ("chorizo", "Z"),
            "t": ("tomate", "T"),
            "p": ("patata", "P"),
        }
        if simb in mapa_cajones:
            nombre, letra = mapa_cajones[simb]
            return Cajon(col, fila, nombre, letra)
        if simb == "E":
            return Superficie(col, fila)
        if simb == "S":
            return SuperficiePaso(col, fila)
        if simb == "P":
            return Pared(col, fila)
        if simb == "B":
            return Basura(col, fila)
        if simb == "T":
            return TablaCortar(col, fila)
        if simb == "M":
            return Batidora(col, fila)
        if simb == "F":
            return Sarten(col, fila)
        if simb == "L":
            return PilaPlatos(col, fila)
        if simb == "D":
            return MostradorEntrega(col, fila, gestor_pedidos)
        return None

    def obtener_estacion(self, col, fila):
        return self._estaciones.get((col, fila))

    def colisiona_solido(self, x, y, w, h):
        return any(est.colisiona(x, y, w, h) for est in self._estaciones.values())

    def dibujar(self, estaciones_resaltadas):
        for fila in range(FILAS):
            for col in range(COLS):
                color = 15 if (fila + col) % 2 == 0 else 7
                pyxel.rect(
                    col * TAM_CASILLA,
                    ALTO_TABLERO + fila * TAM_CASILLA,
                    TAM_CASILLA,
                    TAM_CASILLA,
                    color,
                )
        for est in self._estaciones.values():
            est.dibujar(resaltada=(est in estaciones_resaltadas))


class GestorPedidos:
    def __init__(self):
        self._puntos = 0
        self._fallos = 0
        self._nivel = 1
        self._pedidos_activos = []
        self._programar_nivel()

    @property
    def nivel(self):
        return self._nivel

    @property
    def game_over(self):
        return self._fallos >= MAX_FALLOS

    def _programar_nivel(self):
        total = PEDIDOS_NIVEL_1 + (self._nivel - 1)
        self._pedidos_activos = []
        intervalo = (DURACION_SERVICIO - RETRASO_PRIMER_PEDIDO) // max(1, total)
        self._tiempos_llegada = [
            RETRASO_PRIMER_PEDIDO + i * intervalo for i in range(total)
        ]

    def siguiente_nivel(self):
        self._nivel += 1
        self._programar_nivel()

    def actualizar(self, tiempo_transcurrido):
        while (
            self._tiempos_llegada
            and tiempo_transcurrido >= self._tiempos_llegada[0]
            and len(self._pedidos_activos) < MAX_PEDIDOS_ACTIVOS
        ):
            self._tiempos_llegada.pop(0)
            id_receta = random.choice(list(RECETAS.keys()))
            self._pedidos_activos.append(Pedido(id_receta))

        activos = []
        for pedido in self._pedidos_activos:
            pedido.actualizar()
            if pedido.expirado:
                self._fallos += 1
                self._puntos = max(0, self._puntos - pedido.penalizacion)
            else:
                activos.append(pedido)
        self._pedidos_activos = activos

    def entregar_plato(self, plato):
        for idx, pedido in enumerate(self._pedidos_activos):
            if plato.preparacion == pedido.id_receta:
                self._puntos += pedido.puntos
                self._pedidos_activos.pop(idx)
                return
        self._fallos += 1

    def dibujar_tablero(self, tiempo_restante):
        pyxel.rect(0, 0, ANCHO_PANTALLA, ALTO_TABLERO, 4)
        pyxel.line(0, ALTO_TABLERO - 1, ANCHO_PANTALLA, ALTO_TABLERO - 1, 0)

        for idx, pedido in enumerate(self._pedidos_activos):
            pedido.dibujar(3 + idx * 44, 3)

        seg = tiempo_restante // FPS
        mins, segs = divmod(seg, 60)
        pyxel.rect(136, 3, 53, 25, 0)
        pyxel.rectb(136, 3, 53, 25, 9)
        pyxel.text(140, 5, f"{mins:02d}:{segs:02d} N{self._nivel}", 10)
        pyxel.text(140, 13, f"PTS:{self._puntos}", 11)
        pyxel.text(140, 20, f"FAL:{self._fallos}/{MAX_FALLOS}", 8)


class JuegoServiceRush:
    def __init__(self):
        pyxel.init(
            ANCHO_PANTALLA,
            ALTO_PANTALLA,
            title="Service Rush",
            fps=FPS,
            display_scale=ESCALA_PANTALLA,
        )
        self._reiniciar_partida()
        pyxel.run(self.update, self.draw)

    def _reiniciar_partida(self):
        self._gestor = GestorPedidos()
        self._iniciar_servicio()

    def _iniciar_servicio(self):
        self._cocina = Cocina(self._gestor)
        controles_c1 = {
            "arr": pyxel.KEY_W,
            "aba": pyxel.KEY_S,
            "izq": pyxel.KEY_A,
            "der": pyxel.KEY_D,
            "accion": pyxel.KEY_E,
        }
        controles_c2 = {
            "arr": pyxel.KEY_UP,
            "aba": pyxel.KEY_DOWN,
            "izq": pyxel.KEY_LEFT,
            "der": pyxel.KEY_RIGHT,
            "accion": pyxel.KEY_SPACE,
        }
        self._chefs = [
            Chef(90, ALTO_TABLERO + 2 * TAM_CASILLA + 2, 12, controles_c1),
            Chef(90, ALTO_TABLERO + 6 * TAM_CASILLA + 2, 8, controles_c2),
        ]
        self._tiempo_restante = DURACION_SERVICIO
        self._fin_servicio = False

    def update(self):
        if self._gestor.game_over:
            if pyxel.btnp(pyxel.KEY_R):
                self._reiniciar_partida()
            return

        if self._fin_servicio:
            if pyxel.btnp(pyxel.KEY_RETURN) or pyxel.btnp(pyxel.KEY_SPACE):
                self._gestor.siguiente_nivel()
                self._iniciar_servicio()
            return

        self._tiempo_restante -= 1
        if self._tiempo_restante <= 0:
            self._tiempo_restante = 0
            self._fin_servicio = True
            return

        tiempo_transcurrido = DURACION_SERVICIO - self._tiempo_restante
        self._gestor.actualizar(tiempo_transcurrido)

        for chef in self._chefs:
            chef.actualizar(self._cocina)

    def draw(self):
        pyxel.cls(0)
        self._gestor.dibujar_tablero(self._tiempo_restante)
        resaltadas = {chef.obtener_estacion_objetivo(self._cocina) for chef in self._chefs}
        self._cocina.dibujar(resaltadas)

        for chef in self._chefs:
            chef.dibujar()

        if self._gestor.game_over:
            self._dibujar_mensaje("GAME OVER", "Pulsa R para reiniciar", 8)
        elif self._fin_servicio:
            self._dibujar_mensaje(
                f"NIVEL {self._gestor.nivel} COMPLETADO",
                "Pulsa ENTER para seguir",
                11,
            )

    def _dibujar_mensaje(self, titulo, subtitulo, color_titulo):
        pyxel.rect(36, 72, 120, 36, 0)
        pyxel.rectb(36, 72, 120, 36, 7)
        pyxel.text(56, 80, titulo, color_titulo)
        pyxel.text(46, 94, subtitulo, 7)


if __name__ == "__main__":
    JuegoServiceRush()