import random
import pyxel


class OvercookedSimple:

    def __init__(self):
        # Ventana de 160x120 píxeles
        pyxel.init(160, 120, title="Overcooked Pyxel", fps=30)
        self.reiniciar_juego()
        pyxel.run(self.update, self.draw)

    def reiniciar_juego(self):
        # Estado del jugador
        self.px = 76
        self.py = 60
        self.velocidad = 2
        self.en_mano = None  # Objeto que lleva el chef

        # Estado de las estaciones de trabajo
        self.sarten_item = None
        self.sarten_progreso = 0  # 0 a 90 frames (3 segundos)

        self.tabla_item = None
        self.tabla_progreso = 0  # 0 a 45 frames (1.5 segundos)

        # Mostrador de entrega (acumula ingredientes para platos combinados)
        self.entrega_items = []

        # Sistema de pedidos y puntuación
        self.recetas = [
            {"nombre": "ENSALADA", "req": ["lechuga_picada"], "puntos": 100},
            {"nombre": "HAMBURGUESA", "req": ["carne_cocida"], "puntos": 150},
            {
                "nombre": "BURGER FULL",
                "req": ["carne_cocida", "lechuga_picada"],
                "puntos": 300,
            },
        ]
        self.pedido_actual = random.choice(self.recetas)
        self.puntos = 0
        self.tiempo_restante = 90 * 30  # 90 segundos a 30 FPS
        self.game_over = False

        # Definición de estaciones (x, y, ancho, alto, tipo)
        self.estaciones = [
            # Caja de Carne (Arriba izquierda)
            {"x": 16, "y": 28, "w": 16, "h": 16, "tipo": "caja_carne"},
            # Caja de Lechuga (Abajo izquierda)
            {"x": 16, "y": 84, "w": 16, "h": 16, "tipo": "caja_lechuga"},
            # Sartén / Fogón (Arriba centro)
            {"x": 72, "y": 28, "w": 16, "h": 16, "tipo": "sarten"},
            # Tabla de cortar (Abajo centro)
            {"x": 72, "y": 84, "w": 16, "h": 16, "tipo": "tabla"},
            # Basura (Arriba derecha)
            {"x": 128, "y": 28, "w": 16, "h": 16, "tipo": "basura"},
            # Mostrador de Entrega (Abajo derecha)
            {"x": 128, "y": 84, "w": 16, "h": 16, "tipo": "entrega"},
        ]

    def update(self):
        if self.game_over:
            if pyxel.btnp(pyxel.KEY_R):
                self.reiniciar_juego()
            return

        # Actualizar temporizador
        self.tiempo_restante -= 1
        if self.tiempo_restante <= 0:
            self.tiempo_restante = 0
            self.game_over = True
            return

        # Movimiento del jugador
        dx, dy = 0, 0
        if pyxel.btn(pyxel.KEY_LEFT) or pyxel.btn(pyxel.KEY_A):
            dx = -self.velocidad
        if pyxel.btn(pyxel.KEY_RIGHT) or pyxel.btn(pyxel.KEY_D):
            dx = self.velocidad
        if pyxel.btn(pyxel.KEY_UP) or pyxel.btn(pyxel.KEY_W):
            dy = -self.velocidad
        if pyxel.btn(pyxel.KEY_DOWN) or pyxel.btn(pyxel.KEY_S):
            dy = self.velocidad

        # Mover y evitar colisiones con bordes y estaciones
        self.mover_con_colision(dx, dy)

        # Cocción automática en la sartén
        if self.sarten_item == "carne_cruda":
            self.sarten_progreso += 1
            if self.sarten_progreso >= 90:  # 3 segundos para cocinarse
                self.sarten_item = "carne_cocida"
        elif self.sarten_item == "carne_cocida":
            self.sarten_progreso += 1
            if self.sarten_progreso >= 210:  # Si se deja 4s más, se quema
                self.sarten_item = "quemado"

        # Detectar estación cercana para interactuar
        estacion = self.obtener_estacion_cercana()

        # Acción de picar (manteniendo pulsado ESPACIO o E frente a la tabla)
        if (
            estacion
            and estacion["tipo"] == "tabla"
            and self.tabla_item == "lechuga_entera"
        ):
            if pyxel.btn(pyxel.KEY_SPACE) or pyxel.btn(pyxel.KEY_E):
                self.tabla_progreso += 1
                if self.tabla_progreso >= 45:
                    self.tabla_item = "lechuga_picada"

        # Acción puntual (pulsar ESPACIO o E)
        if pyxel.btnp(pyxel.KEY_SPACE) or pyxel.btnp(pyxel.KEY_E):
            if estacion:
                self.interactuar(estacion)

    def mover_con_colision(self, dx, dy):
        # Límites de la cocina (dejando margen superior para la interfaz)
        nuevo_x = max(8, min(144, self.px + dx))
        if not self.colisiona_estaciones(nuevo_x, self.py):
            self.px = nuevo_x

        nuevo_y = max(22, min(106, self.py + dy))
        if not self.colisiona_estaciones(self.px, nuevo_y):
            self.py = nuevo_y

    def colisiona_estaciones(self, x, y):
        # El jugador mide 8x8
        for est in self.estaciones:
            if (
                x < est["x"] + est["w"]
                and x + 8 > est["x"]
                and y < est["y"] + est["h"]
                and y + 8 > est["y"]
            ):
                return True
        return False

    def obtener_estacion_cercana(self):
        # Centro del jugador
        cx, cy = self.px + 4, self.py + 4
        mejor_est = None
        menor_dist = 18  # Radio de alcance

        for est in self.estaciones:
            ex, ey = est["x"] + est["w"] / 2, est["y"] + est["h"] / 2
            dist = ((cx - ex) ** 2 + (cy - ey) ** 2) ** 0.5
            if dist < menor_dist:
                menor_dist = dist
                mejor_est = est
        return mejor_est

    def interactuar(self, est):
        tipo = est["tipo"]

        # 1. Cajas de ingredientes
        if tipo == "caja_carne" and self.en_mano is None:
            self.en_mano = "carne_cruda"
        elif tipo == "caja_lechuga" and self.en_mano is None:
            self.en_mano = "lechuga_entera"

        # 2. Sartén
        elif tipo == "sarten":
            if self.en_mano == "carne_cruda" and self.sarten_item is None:
                self.sarten_item = "carne_cruda"
                self.sarten_progreso = 0
                self.en_mano = None
            elif self.en_mano is None and self.sarten_item in [
                "carne_cocida",
                "quemado",
            ]:
                self.en_mano = self.sarten_item
                self.sarten_item = None
                self.sarten_progreso = 0

        # 3. Tabla de cortar
        elif tipo == "tabla":
            if self.en_mano == "lechuga_entera" and self.tabla_item is None:
                self.tabla_item = "lechuga_entera"
                self.tabla_progreso = 0
                self.en_mano = None
            elif self.en_mano is None and self.tabla_item == "lechuga_picada":
                self.en_mano = "lechuga_picada"
                self.tabla_item = None
                self.tabla_progreso = 0

        # 4. Basura
        elif tipo == "basura" and self.en_mano is not None:
            self.en_mano = None

        # 5. Mostrador de entrega
        elif tipo == "entrega" and self.en_mano is not None:
            if self.en_mano in self.pedido_actual["req"]:
                if self.en_mano not in self.entrega_items:
                    self.entrega_items.append(self.en_mano)
                    self.en_mano = None
                    # Comprobar si el pedido está completo
                    if sorted(self.entrega_items) == sorted(
                        self.pedido_actual["req"]
                    ):
                        self.puntos += self.pedido_actual["puntos"]
                        self.entrega_items = []
                        self.pedido_actual = random.choice(self.recetas)
            else:
                # Si entrega algo equivocado o quemado, pierde puntos y se limpia
                self.puntos = max(0, self.puntos - 50)
                self.en_mano = None

    def dibujar_item(self, item, x, y):
        if item == "carne_cruda":
            pyxel.circ(x, y, 3, 8)  # Rojo
        elif item == "carne_cocida":
            pyxel.circ(x, y, 3, 4)  # Marrón
        elif item == "quemado":
            pyxel.circ(x, y, 3, 0)  # Negro
        elif item == "lechuga_entera":
            pyxel.rect(x - 3, y - 3, 6, 6, 11)  # Verde claro
        elif item == "lechuga_picada":
            pyxel.rect(x - 2, y - 2, 2, 2, 3)  # Verde oscuro picado
            pyxel.rect(x + 1, y - 1, 2, 2, 3)
            pyxel.rect(x - 1, y + 1, 2, 2, 3)

    def draw(self):
        # Fondo de suelo de cocina (gris claro)
        pyxel.cls(13)

        # Barra superior de interfaz (UI)
        pyxel.rect(0, 0, 160, 18, 1)
        pyxel.text(4, 3, f"PEDIDO: {self.pedido_actual['nombre']}", 7)

        # Mostrar ingredientes que faltan para el pedido actual
        faltan = [
            i for i in self.pedido_actual["req"] if i not in self.entrega_items
        ]
        req_texto = "+".join([f[:5].upper() for f in faltan])
        pyxel.text(4, 10, f"FALTA: {req_texto}", 10)

        # Puntos y Tiempo
        segundos = self.tiempo_restante // 30
        pyxel.text(112, 3, f"PTS:{self.puntos}", 11)
        color_tiempo = 8 if segundos <= 15 else 7
        pyxel.text(112, 10, f"SEG:{segundos}", color_tiempo)

        # Dibujar estaciones
        est_cercana = self.obtener_estacion_cercana()
        for est in self.estaciones:
            x, y, w, h = est["x"], est["y"], est["w"], est["h"]
            tipo = est["tipo"]

            # Resaltar estación si el jugador está cerca
            borde = 7 if est == est_cercana else 5
            pyxel.rect(x, y, w, h, 6)
            pyxel.rectb(x, y, w, h, borde)

            if tipo == "caja_carne":
                pyxel.circ(x + 8, y + 8, 4, 8)
                pyxel.text(x + 2, y - 6, "CARNE", 1)
            elif tipo == "caja_lechuga":
                pyxel.rect(x + 4, y + 4, 8, 8, 11)
                pyxel.text(x - 2, y + 18, "LECHUGA", 1)
            elif tipo == "sarten":
                pyxel.circ(x + 8, y + 8, 5, 0)
                pyxel.text(x + 1, y - 6, "SARTEN", 1)
                if self.sarten_item:
                    self.dibujar_item(self.sarten_item, x + 8, y + 8)
                    # Barra de progreso de cocción
                    if self.sarten_item == "carne_cruda":
                        ancho_barra = int((self.sarten_progreso / 90) * 14)
                        pyxel.rect(x + 1, y + 14, ancho_barra, 2, 11)
                    elif self.sarten_item == "carne_cocida":
                        # Barra de aviso antes de quemarse
                        ancho_quema = int(
                            ((self.sarten_progreso - 90) / 120) * 14
                        )
                        pyxel.rect(x + 1, y + 14, ancho_quema, 2, 8)
            elif tipo == "tabla":
                pyxel.rect(x + 3, y + 3, 10, 10, 15)
                pyxel.text(x + 2, y + 18, "PICAR", 1)
                if self.tabla_item:
                    self.dibujar_item(self.tabla_item, x + 8, y + 8)
                    if self.tabla_item == "lechuga_entera":
                        ancho_barra = int((self.tabla_progreso / 45) * 14)
                        pyxel.rect(x + 1, y + 14, ancho_barra, 2, 10)
            elif tipo == "basura":
                pyxel.rect(x + 4, y + 4, 8, 8, 2)
                pyxel.text(x + 1, y - 6, "BASURA", 1)
            elif tipo == "entrega":
                pyxel.rect(x + 2, y + 2, 12, 12, 10)
                pyxel.text(x - 2, y + 18, "ENTREGA", 1)
                # Mostrar lo que ya está puesto en el mostrador
                for idx, item in enumerate(self.entrega_items):
                    self.dibujar_item(item, x + 5 + (idx * 6), y + 8)

        # Dibujar al jugador (Chef)
        pyxel.rect(self.px, self.py, 8, 8, 12)  # Cuerpo azul
        pyxel.rect(self.px + 1, self.py - 2, 6, 3, 7)  # Gorro blanco de chef

        # Dibujar el objeto que lleva en la mano
        if self.en_mano:
            self.dibujar_item(self.en_mano, self.px + 4, self.py - 5)

        # Pantalla de Fin de Juego
        if self.game_over:
            pyxel.rect(25, 42, 110, 36, 0)
            pyxel.rectb(25, 42, 110, 36, 7)
            pyxel.text(55, 48, "TIEMPO AGOTADO", 8)
            pyxel.text(46, 58, f"PUNTUACION: {self.puntos}", 10)
            pyxel.text(35, 68, "Pulsa R para reiniciar", 7)


OvercookedSimple()