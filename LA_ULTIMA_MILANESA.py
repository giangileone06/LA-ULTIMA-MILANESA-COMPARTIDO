import random
import tkinter as tk
from tkinter import messagebox
import os
import sys
import json

from PIL import Image, ImageDraw, ImageTk
from pygame import mixer

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except Exception:
    pass

ARCH_RECORD = "record_infinito.json"

def obtener_record_maximo():
    if os.path.exists(ARCH_RECORD):
        try:
            with open(ARCH_RECORD, "r") as f:
                data = json.load(f)
                return data.get("record", 1)
        except:
            return 1
    return 1

def guardar_nuevo_record(ronda):
    try:
        with open(ARCH_RECORD, "w") as f:
            json.dump({"record": ronda}, f)
    except:
        pass

ULTIMA_DIFICULTAD = 2
ULTIMO_MODO = "Historia"

# =========================================================================
# BACKEND
# =========================================================================

class Personaje:
    def __init__(self, nombre, salud, arma, armadura=None, sprite_base="", sprite_roto="", chance_esquivar=0):
        self.nombre = nombre
        self._salud_actual = salud
        self.salud_maxima = salud
        self._arma_equipada = arma
        self._armadura_equipada = armadura
        self.sprite_base = sprite_base
        self.sprite_roto = sprite_roto
        self.armadura_rota = False
        self.chance_esquivar = chance_esquivar

    def obtener_salud(self):
        return self._salud_actual

    def __add__(self, cantidad_curacion):
        self._salud_actual += cantidad_curacion
        if self._salud_actual > self.salud_maxima:
            self._salud_actual = self.salud_maxima
        return self

    def recibir_daño(self, cantidad, juego_arena):
        if random.randint(1, 100) <= self.chance_esquivar:
            if juego_arena.sound_esquivar:
                juego_arena.sound_esquivar.play()
            return f"🤸‍♂️ ¡{self.nombre} tiró un esquive fisura en el piso!\n", False

        texto_armadura = ""
        if self._armadura_equipada is not None and not self.armadura_rota:
            amount = self._armadura_equipada.absorber_daño(cantidad)
            texto_armadura = "🛡️ ¡Mitigado por armadura!\n"
            if self._salud_actual - amount <= self.salud_maxima * 0.5:
                self.armadura_rota = True
                texto_armadura += "💥 ¡LA ARMADURA SE HIZO PEDAZOS!\n"
                if juego_arena.sound_romper_armadura:
                    juego_arena.sound_romper_armadura.play()
            cantidad = amount

        self._salud_actual -= cantidad
        if self._salud_actual <= 0:
            self._salud_actual = 0
            return f"{texto_armadura}💀 {self.nombre} mordió el polvo.\n", True
        else:
            return f"{texto_armadura}💥 {self.nombre} recibió {cantidad:.1f} de daño.\n", False

    def atacar(self, enemigo, juego_arena):
        golpe = self._arma_equipada.calcular_daño()
        reporte, muerto = enemigo.recibir_daño(golpe, juego_arena)
        return f"⚔️ {self.nombre} atacó con {self._arma_equipada._nombre}.\n{reporte}", muerto


class Jugador(Personaje):
    def __init__(self, nombre, salud, arma, armadura=None, alfajores_iniciales=2, s_base="", s_roto=""):
        super().__init__(nombre, salud, arma, armadura, s_base, s_roto, chance_esquivar=0)
        self._alfajores = alfajores_iniciales

    def obtener_cantidad_alfajores(self):
        return self._alfajores

    def usar_alfajor(self):
        if self._alfajores > 0:
            self._alfajores -= 1
            self + 50
            return True
        return False

    def ganar_alfajor(self):
        self._alfajores += 1


class Arma:
    def __init__(self, nombre, daño_minimo, daño_maximo):
        self._nombre = nombre
        self._daño_minimo = daño_minimo
        self._daño_maximo = daño_maximo

    def calcular_daño(self):
        return random.randint(self._daño_minimo, self._daño_maximo)


class Armadura:
    def __init__(self, nombre, resistencia):
        self._nombre = nombre
        self._resistencia = resistencia

    def absorber_daño(self, daño_entrante):
        return max(0, daño_entrante - self._resistencia)


# --- ENEMIGOS ---

class EnanoManija(Personaje):
    def __init__(self, dif_str, mod_vida, mod_daño):
        if dif_str == "facil":
            super().__init__("Enano Manija", 30, Arma("Vino en Cartón Cortado", 3, 6), None,
                             "enano_manija_facil.png", "enano_manija_facil.png", chance_esquivar=35)
        elif dif_str == "medio":
            super().__init__("Enano Manija", 45, Arma("Tramontina Oxidado", 4, 7), Armadura("Remera a Rayas Estirada", 1),
                             "enano_manija_medio_armadura.png", "enano_manija_medio_sin_armadura.png", chance_esquivar=35)
        else:
            super().__init__("Enano Manija", 55, Arma("Pico de Botella Roto", 7, 13), Armadura("Campera de Cuero Tachonada", 1),
                             "enano_manija_dificil_armadura.png", "enano_manija_dificil_sin_armadura.png", chance_esquivar=35)


class EnanoComunacho(Personaje):
    def __init__(self, dif_str, mod_vida, mod_daño):
        if dif_str == "facil":
            super().__init__("Enano Comunacho", 40, Arma("Tramontina Doblado", 4, 8), None,
                             "enano_machete.png", "enano_machete.png", chance_esquivar=10)
        elif dif_str == "medio":
            super().__init__("Enano Comunacho", 55, Arma("Fierro de Obra", 5, 9), Armadura("Chapa de Aluminio", 1),
                             "enano_fierro_armadura.png", "enano_comun_medio_sin_armadura.png", chance_esquivar=10)
        else:
            super().__init__("Enano Comunacho", 70, Arma("Espada Oxidada de Reja", 9, 15), Armadura("Escudo de Madera Maciza", 2),
                             "enano_comun_dificil_armadura.png", "enano_comun_dificil_sin_armadura.png", chance_esquivar=10)


class EnanoMorfi(Personaje):
    def __init__(self, dif_str, mod_vida, mod_daño):
        if dif_str == "facil":
            super().__init__("Enano Morfi", 60, Arma("Maza de Goma", 5, 10), None,
                             "enano_tanque_facil.png", "enano_tanque_facil.png", chance_esquivar=0)
        elif dif_str == "medio":
            super().__init__("Enano Morfi", 85, Arma("Cartel de Moscú", 6, 11), Armadura("Chaleco de Lana Grueso", 2),
                             "enano_tanque_medio_armadura.png", "enano_tanque_medio_sin_armadura.png", chance_esquivar=0)
        else:
            super().__init__("Enano Morfi", 100, Arma("Garrafa de Gas de 10Kg", 11, 18), Armadura("Traje de Chatarrero Blindado", 3),
                             "enano_tanque_dificil_armadura.png", "enano_tanque_dificil_sin_armadura.png", chance_esquivar=0)


class JefeFalopino(Personaje):
    def __init__(self):
        super().__init__(
            nombre="Jefe Falopino",
            salud=135,
            arma=Arma("Palo de Paravalancha de Boca", 13, 23),
            armadura=Armadura("Armadura Medieval de Platino", 5),
            sprite_base="jefe_armadura.png",
            sprite_roto="jefe_sin_armadura.png",
            chance_esquivar=10
        )


# =========================================================================
# MENÚ INICIAL
# =========================================================================

_GOLD      = "#D4AF37"
_AMBER     = "#B46E14"
_PARCHMENT = "#F0D7A0"
_SAGE      = "#1E5020"
_BLOOD     = "#8C140A"
_STEEL     = "#1E3264"
_VIOLET    = "#3C0A50"
_GREEN_BTN = "#14A03C"
_W, _H     = 620, 580


def _make_panel(w, h, fill_rgb=(10, 6, 2), alpha=130, radius=10,
                border_hex=_GOLD, border_w=2, glow=False):
    br = tuple(int(border_hex[i:i+2], 16) for i in (1, 3, 5))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w-1, h-1], radius=radius,
                         fill=(*fill_rgb, alpha),
                         outline=(*br, 210), width=border_w)
    if glow:
        d.rounded_rectangle([border_w+1, border_w+1, w-border_w-2, h-border_w-2],
                              radius=max(radius-2, 2),
                              outline=(255, 220, 100, 50), width=1)
    return img


class VentanaConfiguracion:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gnomos vs Enanos — Menú")
        self.root.geometry(f"{_W}x{_H}")
        self.root.resizable(False, False)

        self.dificultad_elegida = 2
        self.modo_elegido       = "Historia"
        self.confirmado         = False

        self._refs       = []
        self._fila_ids   = [None, None, None]
        self._fila_imgs  = [None, None, None]
        self._modo_ids   = {}

        mixer.init()
        try:
            mixer.music.load("musica_menu.mp3")
            mixer.music.set_volume(0.5)
            mixer.music.play(-1)
        except:
            pass

        self.crear_interfaz()

    def crear_interfaz(self):
        self.canvas = tk.Canvas(self.root, width=_W, height=_H,
                                highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0)

        try:
            bg = Image.open("fondo_menu.png").resize((_W, _H), Image.Resampling.LANCZOS)
        except FileNotFoundError:
            bg = Image.new("RGB", (_W, _H), "#1a0a00")
        vig = Image.new("RGBA", (_W, _H), (0, 0, 0, 0))
        vd  = ImageDraw.Draw(vig)
        for i in range(110):
            a = int(155 * (i / 110) ** 1.8)
            vd.rectangle([i, i, _W-1-i, _H-1-i], outline=(0, 0, 0, a))
        comp = Image.alpha_composite(bg.convert("RGBA"), vig)
        self._bg_photo = ImageTk.PhotoImage(comp.convert("RGB"))
        self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)

        self._pegar_panel(_make_panel(500, 46,  fill_rgb=(8,4,0),    alpha=165,
                                      radius=8,  border_hex=_GOLD,   border_w=2, glow=True),  60, 17)
        self._pegar_panel(_make_panel(500, 160, fill_rgb=(8,5,0),    alpha=128,
                                      radius=10, border_hex=_AMBER,  border_w=2, glow=True),  60, 76)
        self._pegar_panel(_make_panel(540, 188, fill_rgb=(5,5,15),   alpha=110,
                                      radius=10, border_hex=_AMBER,  border_w=2, glow=True),  40, 268)
        self._pegar_panel(_make_panel(540, 52,  fill_rgb=(10,80,25), alpha=235,
                                      radius=10, border_hex="#32C850", border_w=2, glow=True), 40, 490)

        self._panel_dif_y = [115, 155, 195]
        self._redraw_dif_rows()

        self._modo_ids = {}
        for key, y in [("Historia", 310), ("Infinito", 386)]:
            ph = ImageTk.PhotoImage(Image.new("RGBA", (510, 62), (0,0,0,0)))
            self._refs.append(ph)
            self._modo_ids[key] = self.canvas.create_image(55, y, anchor="nw", image=ph)

        self.canvas.create_text(310, 40,
            text="⚔️ GNOMOS VS ENANITOS ⚔️",
            font=("Courier", 15, "bold"), fill=_GOLD, anchor="center")

        self.canvas.create_text(83, 94,
            text="🧠 SELECCIONÁ TU GNOMO",
            font=("Arial", 10, "bold"), fill="#ffffff", anchor="w")

        descs = [
            "🟢 ROBERTITO (Fácil): Sifón rendidor, Enanos sin escudo.",
            "🟡 ROBERTITO (Medio): Macana de palo de escoba, Balanceado criollo.",
            "🔴 ROBERTITO (Ultra): Tramontina doblegado, vas a puro pulmón.",
        ]
        for i, txt in enumerate(descs):
            self.canvas.create_text(82, self._panel_dif_y[i] + 12,
                text=txt, font=("Arial", 9), fill="#dddddd", anchor="w")

        self.canvas.create_text(63, 284,
            text="🕹️ MODOS DE COMBATE",
            font=("Arial", 10, "bold"), fill="#ffffff", anchor="w")

        self._modo_text_ids = {}
        self._modo_text_ids["Historia"] = [
            self.canvas.create_text(310, 339,
                text="📜 MODO HISTORIA",
                font=("Courier", 11, "bold"), fill="#ffffff", anchor="center"),
            self.canvas.create_text(310, 358,
                text="(5 Rondas de Lacayos + El Jefe Falopino)",
                font=("Courier", 9), fill="#cccccc", anchor="center"),
        ]
        self._modo_text_ids["Infinito"] = [
            self.canvas.create_text(310, 415,
                text="♾️ MODO INFINITO",
                font=("Courier", 11, "bold"), fill="#aaaaaa", anchor="center"),
            self.canvas.create_text(310, 434,
                text="(Hordas sin fin. Buscando romper el Récord del Barrio)",
                font=("Courier", 9), fill="#888888", anchor="center"),
        ]

        def _click_historia(e): self.seleccionar_modo("Historia")
        def _click_infinito(e): self.seleccionar_modo("Infinito")
        r_h = self.canvas.create_rectangle(55, 310, 565, 372, fill="", outline="", tags="clickarea")
        r_i = self.canvas.create_rectangle(55, 386, 565, 448, fill="", outline="", tags="clickarea")
        self.canvas.tag_bind(r_h, "<Button-1>", _click_historia)
        self.canvas.tag_bind(r_i, "<Button-1>", _click_infinito)
        for tid in self._modo_text_ids["Historia"]:
            self.canvas.tag_bind(tid, "<Button-1>", _click_historia)
        for tid in self._modo_text_ids["Infinito"]:
            self.canvas.tag_bind(tid, "<Button-1>", _click_infinito)

        self._redraw_modo_btns()

        self._btns_dif = []
        for i, lbl in enumerate(["Fácil", "Medio", "Ultra"]):
            y   = self._panel_dif_y[i] + 2
            btn = tk.Button(self.root, text=lbl,
                            font=("Arial", 9, "bold"), width=8,
                            bg="#222222", fg="#999999",
                            relief="flat", bd=0,
                            activebackground="#333333", activeforeground="white",
                            cursor="hand2")
            btn.place(x=494, y=y, width=62, height=26)
            self._btns_dif.append(btn)
        for i in range(3):
            self._btns_dif[i].config(command=lambda n=i+1: self.seleccionar_dificultad(n))
        self._apply_dif_style()

        tk.Button(self.root,
            text="🔥 IR A COPAR EL PASILLO 🔥",
            font=("Courier", 12, "bold"),
            bg=_GREEN_BTN, fg="white",
            activebackground="#0d7a2a", activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            command=self.iniciar_juego
        ).place(x=42, y=492, width=536, height=48)

    def _pegar_panel(self, panel_pil, x, y):
        ph = ImageTk.PhotoImage(panel_pil)
        self._refs.append(ph)
        self.canvas.create_image(x, y, anchor="nw", image=ph)

    def _redraw_dif_rows(self):
        colors  = {1: (30,80,30), 2: (130,90,10), 3: (100,15,10)}
        borders = {1: "#32C850", 2: _GOLD, 3: "#C83220"}
        for i in range(3):
            nivel  = i + 1
            active = (self.dificultad_elegida == nivel)
            if active:
                hl = _make_panel(488, 32, fill_rgb=colors[nivel], alpha=65,
                                  radius=5, border_hex=borders[nivel], border_w=1)
            else:
                hl = Image.new("RGBA", (488, 32), (0, 0, 0, 0))
            ph = ImageTk.PhotoImage(hl)
            self._refs.append(ph)
            self._fila_imgs[i] = ph
            if self._fila_ids[i]:
                self.canvas.delete(self._fila_ids[i])
            self._fila_ids[i] = self.canvas.create_image(
                66, self._panel_dif_y[i] - 2, anchor="nw", image=ph)

    def _redraw_modo_btns(self):
        modos = [
            ("Historia", 310, (20, 50, 100),  "#5080D0"),
            ("Infinito",  386, (60, 10,  80),  "#9040C0"),
        ]
        for (key, y, col, border) in modos:
            active = (self.modo_elegido == key)
            panel  = _make_panel(510, 62, fill_rgb=col,
                                  alpha=210 if active else 70,
                                  radius=8,
                                  border_hex=border if active else _AMBER,
                                  border_w=2 if active else 1,
                                  glow=active)
            ph = ImageTk.PhotoImage(panel)
            self._refs.append(ph)
            if key in self._modo_ids:
                self.canvas.delete(self._modo_ids[key])
            self._modo_ids[key] = self.canvas.create_image(55, y, anchor="nw", image=ph)

        if hasattr(self, "_modo_text_ids"):
            for key in ("Historia", "Infinito"):
                for tid in self._modo_text_ids[key]:
                    self.canvas.tag_raise(tid)
        self.canvas.tag_raise("clickarea")

    def _apply_dif_style(self):
        estilos = {1: ("#2ecc71","black"), 2: ("#f1c40f","black"), 3: ("#e74c3c","white")}
        for i, btn in enumerate(self._btns_dif):
            nivel = i + 1
            if nivel == self.dificultad_elegida:
                bg, fg = estilos[nivel]
                btn.config(bg=bg, fg=fg)
            else:
                btn.config(bg="#222222", fg="#666666")

    def _apply_modo_style(self):
        activo   = (255, 255, 200)
        inactivo = (100,  90,  60)
        for key, color in [("Historia", activo if self.modo_elegido == "Historia" else inactivo),
                            ("Infinito", activo if self.modo_elegido == "Infinito" else inactivo)]:
            hex_col = "#{:02x}{:02x}{:02x}".format(*color)
            for tid in self._modo_text_ids[key]:
                self.canvas.itemconfig(tid, fill=hex_col)

    def seleccionar_dificultad(self, d):
        self.dificultad_elegida = d
        self._redraw_dif_rows()
        self._apply_dif_style()

    def seleccionar_modo(self, modo):
        self.modo_elegido = modo
        self._redraw_modo_btns()
        self._apply_modo_style()

    def iniciar_juego(self):
        global ULTIMA_DIFICULTAD, ULTIMO_MODO
        ULTIMA_DIFICULTAD = self.dificultad_elegida
        ULTIMO_MODO       = self.modo_elegido
        self.confirmado   = True
        mixer.music.stop()
        self.root.destroy()


# =========================================================================
# ARENA DE ENCUENTROS
# =========================================================================

# Velocidad de la animación de fondo: ms entre cada frame.
# 100ms = ~10fps, se ve fluido sin ser mareante.
_MS_FONDO = 100


def _cargar_frames_carpeta(nombre_carpeta, prefijo_archivo, ancho, alto, ultimo=61):
    """
    Carga todos los frames de una carpeta con el patrón:
      <prefijo_archivo>00001.png, 00005.png, 00009.png ... 000XX.png
    (paso de 4)
    - fondo_normal: ultimo=61  → 16 frames (1..61)
    - fondo_final:  ultimo=65  → 17 frames (1..65)
    Devuelve una lista de ImageTk.PhotoImage listos para usar.
    """
    frames = []
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), nombre_carpeta)
    if not os.path.exists(base):
        print(f"⚠️  Carpeta no encontrada: {base}")
        return frames

    # Números: 1, 5, 9, 13, ... hasta `ultimo`  →  paso de 4
    numeros = range(1, ultimo + 1, 4)
    for n in numeros:
        nombre = f"{prefijo_archivo}{n:05d}.png"
        ruta   = os.path.join(base, nombre)
        try:
            img = Image.open(ruta).resize((ancho, alto), Image.Resampling.LANCZOS)
            frames.append(ImageTk.PhotoImage(img))
        except Exception as e:
            print(f"⚠️  No se pudo cargar {nombre}: {e}")
            # Si falta un frame, simplemente lo salteamos (no rompemos el bucle)
    return frames


class ArenaPokemon:
    def __init__(self, dificultad, modo):
        self.dificultad = dificultad
        self.modo       = modo
        self.ronda_actual    = 1
        self.fase_jefe_final = False

        self.mod_vida = 1.0
        self.mod_daño = 1.0
        self.dif_str  = "medio"

        # ── Estado del fondo animado ──────────────────────────────────────
        self._frames_fondo    = []   # lista de PhotoImage del fondo actual
        self._frame_fondo_idx = 0
        self._after_fondo_id  = None
        self._fondo_ref       = None  # ancla del frame visible

        # ── Héroe según dificultad ────────────────────────────────────────
        if dificultad == 1:
            self.dif_str = "facil"
            self.heroe = Jugador(
                "Robertito", 140,
                Arma("Sifón con Escudo Quilmes", 16, 28),
                Armadura("Tapa de Olla Nivel 1", 3), 3,
                "nomo_facil_armadura.png", "nomo_facil_sin_armadura.png")
        elif dificultad == 2:
            self.dif_str = "medio"
            self.heroe = Jugador(
                "Robertito", 110,
                Arma("Sifón Clásico", 14, 25),
                Armadura("Tapa de Olla de Aluminio", 3), 2,
                "nomo_medio_armadura.png", "nomo_medio_sin_armadura.png")
        else:
            self.dif_str = "dificil"
            self.heroe = Jugador(
                "Robertito", 105,
                Arma("Machete Oxidado de Mano", 14, 28),
                None, 2,
                "nomo_dificil.png", "nomo_dificil.png")

        self.generar_nuevo_enemigo()

        self.ventana = tk.Tk()
        self.ventana.title(f"Arena de Pelea - Ronda {self.ronda_actual}")
        self.ventana.geometry("750x550")
        self.ventana.resizable(False, False)

        self.anclas = {}
        self.X_ORIGEN_HEROE,  self.Y_HEROE   = 220, 249
        self.X_ORIGEN_ENEMIGO, self.Y_ENEMIGO = 603, 149

        mixer.init()
        self.cargar_sistema_audio()
        self.reproducir_musica_ambiente()

        self.crear_arena_grafica()
        self.actualizar_pantalla()

    # ── Generación de enemigo ─────────────────────────────────────────────

    def generar_nuevo_enemigo(self):
        if self.modo == "Historia" and self.ronda_actual == 6:
            self.fase_jefe_final = True
            self.enemigo = JefeFalopino()
        else:
            tipo_enano = random.choice([EnanoManija, EnanoComunacho, EnanoMorfi])
            self.enemigo = tipo_enano(self.dif_str, self.mod_vida, self.mod_daño)

    # ── Audio ─────────────────────────────────────────────────────────────

    def cargar_sistema_audio(self):
        def _s(nombre):
            try:    return mixer.Sound(nombre)
            except: return None
        self.sound_hace_daño      = _s("hace_daño.mp3")
        self.sound_recibe_daño    = _s("recibe_daño.mp3")
        self.sound_curacion       = _s("curacion.mp3")
        self.sound_nop            = _s("nop.mp3")
        self.sound_romper_armadura= _s("romper_armadura.mp3")
        self.sound_esquivar       = _s("esquivar.mp3")
        self.sound_muerte         = _s("muerte.mp3")
        self.sound_pasar_ronda    = _s("pasaste_ronda.mp3")
        self.sound_obtener_item   = _s("obtener_item.mp3")

    def reproducir_musica_ambiente(self):
        try:
            if self.fase_jefe_final:
                mixer.music.stop()
                mixer.music.load("batalla_final.mp3")
                mixer.music.set_volume(0.85)
                mixer.music.play(-1)
            else:
                if not mixer.music.get_busy():
                    mixer.music.load("musica_batalla.mp3")
                    mixer.music.set_volume(0.75)
                    mixer.music.play(-1)
        except:
            pass

    # ── Carga de imágenes ─────────────────────────────────────────────────

    def cargar_y_anclar(self, ruta, clave, ancho, alto):
        try:
            img = Image.open(ruta).resize((ancho, alto), Image.Resampling.LANCZOS)
            ph  = ImageTk.PhotoImage(img)
            self.anclas[clave] = ph
            return ph
        except Exception as e:
            print(f"⚠️  No se pudo cargar {ruta}: {e}")
            return None

    # ── Fondo animado ─────────────────────────────────────────────────────

    def _detener_fondo(self):
        """Cancela el loop de animación del fondo si está corriendo."""
        if self._after_fondo_id is not None:
            try:
                self.ventana.after_cancel(self._after_fondo_id)
            except Exception:
                pass
            self._after_fondo_id = None

    def _iniciar_fondo_animado(self, frames):
        """Arranca (o reinicia) la animación con la lista de frames dada."""
        self._detener_fondo()
        self._frames_fondo    = frames
        self._frame_fondo_idx = 0
        if self._frames_fondo:
            self._tick_fondo()

    def _tick_fondo(self):
        """Un tick del loop: muestra el frame actual y programa el siguiente."""
        if not self._frames_fondo:
            return
        ph = self._frames_fondo[self._frame_fondo_idx]
        if ph is not None:
            try:
                self.canvas_escenario.itemconfig(self._img_fondo_id, image=ph)
                self._fondo_ref = ph   # ancla → el GC no destruye el PhotoImage
            except tk.TclError:
                return   # el canvas ya fue destruido → salimos limpio
        self._frame_fondo_idx = (self._frame_fondo_idx + 1) % len(self._frames_fondo)
        self._after_fondo_id  = self.ventana.after(_MS_FONDO, self._tick_fondo)

    # ── Construcción de la arena ──────────────────────────────────────────

    def crear_arena_grafica(self):
        self.canvas_escenario = tk.Canvas(self.ventana, width=750, height=360,
                                          highlightthickness=0)
        self.canvas_escenario.place(x=0, y=0)

        # Creamos el ítem de fondo vacío (siempre en la posición -1, abajo de todo)
        self._img_fondo_id = self.canvas_escenario.create_image(375, 180, anchor="center")

        if self.fase_jefe_final:
            # ── Fondo final animado ───────────────────────────────────────
            frames = _cargar_frames_carpeta(
                "fondo_final",          # nombre de la carpeta
                "fondo_final",          # prefijo de los archivos
                750, 360, ultimo=65)    # 17 frames: 1, 5, 9, ... 65
            if frames:
                self._iniciar_fondo_animado(frames)
            else:
                # Fallback: imagen estática si no hay carpeta
                img_estatica = self.cargar_y_anclar(
                    "fondo_final.png", f"fondo_rd_{self.ronda_actual}", 750, 360)
                if img_estatica:
                    self.canvas_escenario.itemconfig(
                        self._img_fondo_id, image=img_estatica)
                else:
                    self.canvas_escenario.configure(bg="#2c3e50")
        else:
            # ── Fondo normal animado ──────────────────────────────────────
            frames = _cargar_frames_carpeta(
                "fondo_normal",         # nombre de la carpeta
                "fondo_normal",         # prefijo de los archivos
                750, 360)
            if frames:
                self._iniciar_fondo_animado(frames)
            else:
                # Fallback: imagen estática
                img_estatica = self.cargar_y_anclar(
                    "fondo.png", f"fondo_rd_{self.ronda_actual}", 750, 360)
                if img_estatica:
                    self.canvas_escenario.itemconfig(
                        self._img_fondo_id, image=img_estatica)
                else:
                    self.canvas_escenario.configure(bg="#eae6d8")

        # ── Cards de estado ───────────────────────────────────────────────
        self.card_enano = tk.Canvas(self.ventana, width=260, height=75,
                                    bg="#fbf9f0", bd=2, relief="solid", highlightthickness=0)
        self.card_enano.place(x=40, y=30)
        self.lbl_name_enano = tk.Label(self.card_enano,
            text=self.enemigo.nombre.upper(), font=("Courier", 11, "bold"), bg="#fbf9f0")
        self.lbl_name_enano.place(x=10, y=8)
        self.lbl_hp_enano = tk.Label(self.card_enano,
            text="", font=("Courier", 9, "bold"), bg="#fbf9f0")
        self.lbl_hp_enano.place(x=10, y=30)

        self.card_nomo = tk.Canvas(self.ventana, width=260, height=90,
                                   bg="#fbf9f0", bd=2, relief="solid", highlightthickness=0)
        self.card_nomo.place(x=450, y=240)
        self.lbl_name_nomo = tk.Label(self.card_nomo,
            text=self.heroe.nombre.upper(), font=("Courier", 11, "bold"), bg="#fbf9f0")
        self.lbl_name_nomo.place(x=10, y=8)
        self.lbl_hp_nomo = tk.Label(self.card_nomo,
            text="", font=("Courier", 9, "bold"), bg="#fbf9f0")
        self.lbl_hp_nomo.place(x=10, y=30)
        self.lbl_alfajores_count = tk.Label(self.card_nomo,
            text="", font=("Courier", 8, "italic"), bg="#fbf9f0", fg="#7f8c8d")
        self.lbl_alfajores_count.place(x=10, y=65)

        # ── Sprites ───────────────────────────────────────────────────────
        self.img_nomo_obj = self.cargar_y_anclar(
            self.heroe.sprite_base, f"g_b_{self.ronda_actual}", 224, 224)
        self.img_nomo_broken_obj = self.cargar_y_anclar(
            self.heroe.sprite_roto, f"g_r_{self.ronda_actual}", 224, 224)

        if self.img_nomo_obj and not self.heroe.armadura_rota:
            self.sprite_nomo_id = self.canvas_escenario.create_image(
                self.X_ORIGEN_HEROE, self.Y_HEROE, image=self.img_nomo_obj)
        elif self.img_nomo_broken_obj:
            self.sprite_nomo_id = self.canvas_escenario.create_image(
                self.X_ORIGEN_HEROE, self.Y_HEROE, image=self.img_nomo_broken_obj)
        else:
            self.sprite_nomo_id = self.canvas_escenario.create_rectangle(
                self.X_ORIGEN_HEROE-40, self.Y_HEROE-40,
                self.X_ORIGEN_HEROE+40, self.Y_HEROE+40, fill="#e67e22")

        self.img_enano_obj = self.cargar_y_anclar(
            self.enemigo.sprite_base, f"e_b_{self.ronda_actual}", 205, 205)
        self.img_enano_broken_obj = self.cargar_y_anclar(
            self.enemigo.sprite_roto, f"e_r_{self.ronda_actual}", 205, 205)

        if self.img_enano_obj:
            self.sprite_enano_id = self.canvas_escenario.create_image(
                self.X_ORIGEN_ENEMIGO, self.Y_ENEMIGO, image=self.img_enano_obj)
        else:
            self.sprite_enano_id = self.canvas_escenario.create_rectangle(
                self.X_ORIGEN_ENEMIGO-40, self.Y_ENEMIGO-40,
                self.X_ORIGEN_ENEMIGO+40, self.Y_ENEMIGO+40, fill="#bdc3c7")

        self.img_guayma = self.cargar_y_anclar("guaymallen.png", "guaymallen", 50, 50)

        # ── Panel de diálogo y botones ────────────────────────────────────
        self.frame_historial = tk.Frame(self.ventana, bg="#253446", bd=4, relief="ridge")
        self.frame_historial.place(x=10, y=380, width=440, height=150)
        self.txt_dialogo = tk.Text(self.frame_historial, bg="#253446", fg="white",
                                   font=("Courier", 11, "bold"), bd=0, wrap="word",
                                   padx=12, pady=12)
        self.txt_dialogo.pack(fill="both", expand=True)

        self.frame_comandos = tk.Frame(self.ventana, bg="white", bd=4, relief="ridge")
        self.frame_comandos.place(x=460, y=380, width=280, height=150)
        self.btn_lucha = tk.Button(self.frame_comandos, text="⚔️ LUCHA",
                                   font=("Courier", 14, "bold"), bg="white", fg="black",
                                   bd=0, command=self.ejecutar_ataque_jugador)
        self.btn_lucha.place(x=10, y=15, width=250, height=50)
        self.btn_mochila = tk.Button(self.frame_comandos, text="🎒 MOCHILA",
                                     font=("Courier", 14, "bold"), bg="white", fg="black",
                                     bd=0, command=self.ejecutar_curacion_jugador)
        self.btn_mochila.place(x=10, y=75, width=250, height=50)

        if self.fase_jefe_final:
            msg = ("🔥 ¡EL BARRIO ESTÁ TOTALMENTE PRENDIDO FUEGO! 🔥\n"
                   "EL JEFE FALOPINO sale a reventarte.\n¿Qué hará tu Gnomo?")
        else:
            msg = (f"¡RONDA {self.ronda_actual}! Un {self.enemigo.nombre} te corta el pasillo.\n"
                   f"¿Qué hace tu Gnomo?")
        self.escribir_dialogo(msg)

    # ── Pantalla ──────────────────────────────────────────────────────────

    def escribir_dialogo(self, texto):
        self.txt_dialogo.config(state="normal")
        self.txt_dialogo.delete("1.0", tk.END)
        self.txt_dialogo.insert(tk.END, texto)
        self.txt_dialogo.config(state="disabled")

    def actualizar_pantalla(self):
        self.lbl_name_enano.config(text=self.enemigo.nombre.upper())
        self.lbl_hp_nomo.config(text=f"PS: {self.heroe.obtener_salud():.1f} / {self.heroe.salud_maxima}")
        self.lbl_hp_enano.config(text=f"PS: {self.enemigo.obtener_salud():.1f} / {self.enemigo.salud_maxima}")
        self.lbl_alfajores_count.config(text=f"Guaymalléns: {self.heroe.obtener_cantidad_alfajores()} 🍪")

        self.card_enano.delete("bar")
        self.card_nomo.delete("bar")

        pct_e = max(0.0, self.enemigo.obtener_salud() / self.enemigo.salud_maxima)
        col_e = "#2ecc71" if pct_e > 0.2 else "#e74c3c"
        self.card_enano.create_rectangle(10, 52, 250, 64, fill="#bdc3c7", outline="black", tags="bar")
        self.card_enano.create_rectangle(10, 52, 10 + int(240*pct_e), 64, fill=col_e, outline="", tags="bar")

        pct_n = max(0.0, self.heroe.obtener_salud() / self.heroe.salud_maxima)
        col_n = "#2ecc71" if pct_n > 0.2 else "#e74c3c"
        self.card_nomo.create_rectangle(10, 50, 250, 62, fill="#bdc3c7", outline="black", tags="bar")
        self.card_nomo.create_rectangle(10, 50, 10 + int(240*pct_n), 62, fill=col_n, outline="", tags="bar")

        if self.heroe.armadura_rota and self.img_nomo_broken_obj:
            self.canvas_escenario.itemconfig(self.sprite_nomo_id, image=self.img_nomo_broken_obj)
        if self.enemigo.armadura_rota and self.img_enano_broken_obj:
            self.canvas_escenario.itemconfig(self.sprite_enano_id, image=self.img_enano_broken_obj)

    # ── Animaciones de combate ────────────────────────────────────────────

    def animar_avance_heroe(self, x):
        if x < 460:
            x += 20
            self.canvas_escenario.coords(self.sprite_nomo_id, x, self.Y_HEROE)
            self.ventana.after(15, lambda: self.animar_avance_heroe(x))
        else:
            if self.sound_hace_daño: self.sound_hace_daño.play()
            self.concluir_ataque_jugador()

    def animar_regreso_heroe(self, x):
        if x > self.X_ORIGEN_HEROE:
            x -= 20
            self.canvas_escenario.coords(self.sprite_nomo_id, x, self.Y_HEROE)
            self.ventana.after(15, lambda: self.animar_regreso_heroe(x))
        else:
            self.canvas_escenario.coords(self.sprite_nomo_id, self.X_ORIGEN_HEROE, self.Y_HEROE)

    def animar_avance_enano(self, x):
        if x > 360:
            x -= 20
            self.canvas_escenario.coords(self.sprite_enano_id, x, self.Y_ENEMIGO)
            self.ventana.after(15, lambda: self.animar_avance_enano(x))
        else:
            if self.sound_recibe_daño: self.sound_recibe_daño.play()
            self.concluir_turno_enemigo()
            self.ventana.after(100, lambda: self.animar_regreso_enano(x))

    def animar_regreso_enano(self, x):
        if x < self.X_ORIGEN_ENEMIGO:
            x += 20
            self.canvas_escenario.coords(self.sprite_enano_id, x, self.Y_ENEMIGO)
            self.ventana.after(15, lambda: self.animar_regreso_enano(x))
        else:
            self.canvas_escenario.coords(self.sprite_enano_id, self.X_ORIGEN_ENEMIGO, self.Y_ENEMIGO)

    # ── Acciones del jugador ──────────────────────────────────────────────

    def ejecutar_ataque_jugador(self):
        self.btn_lucha.config(state="disabled")
        self.btn_mochila.config(state="disabled")
        self.animar_avance_heroe(self.X_ORIGEN_HEROE)

    def concluir_ataque_jugador(self):
        reporte, enemigo_muerto = self.heroe.atacar(self.enemigo, self)
        self.escribir_dialogo(reporte)
        self.actualizar_pantalla()
        self.animar_regreso_heroe(460)
        if enemigo_muerto:
            if self.sound_muerte: self.sound_muerte.play()
            self.ventana.after(1500, self.gestionar_victoria_ronda)
        else:
            self.ventana.after(1800, self.turnkey_enemigo_automatico)

    def ejecutar_curacion_jugador(self):
        self.btn_lucha.config(state="disabled")
        self.btn_mochila.config(state="disabled")
        if self.heroe.obtener_cantidad_alfajores() > 0:
            if self.sound_curacion: self.sound_curacion.play()
            if self.img_guayma:
                item_id = self.canvas_escenario.create_image(
                    self.X_ORIGEN_HEROE+60, self.Y_HEROE-30, image=self.img_guayma)
            else:
                item_id = self.canvas_escenario.create_text(
                    self.X_ORIGEN_HEROE+60, self.Y_HEROE-30, text="🍪", font=("Arial", 16))
            self.ventana.after(600, lambda: self.concluir_curacion_jugador(item_id))
        else:
            if self.sound_nop: self.sound_nop.play()
            self.escribir_dialogo("❌ ¡No te quedan más Guaymallén!\nPerdiste el turno buscando migajas, alto MIGAJERO.")
            self.ventana.after(2200, self.turnkey_enemigo_automatico)

    def concluir_curacion_jugador(self, item_id):
        self.heroe.usar_alfajor()
        self.canvas_escenario.delete(item_id)
        self.escribir_dialogo(f"🍪 ¡{self.heroe.nombre.upper()} se clavó un Guaymallén bajonero!\nRecuperó 50 PS del backend.")
        self.actualizar_pantalla()
        self.ventana.after(1500, self.turnkey_enemigo_automatico)

    def turnkey_enemigo_automatico(self):
        if self.enemigo.obtener_salud() > 0:
            self.animar_avance_enano(self.X_ORIGEN_ENEMIGO)

    def concluir_turno_enemigo(self):
        reporte, heroe_muerto = self.enemigo.atacar(self.heroe, self)
        self.escribir_dialogo(reporte)
        self.actualizar_pantalla()
        if heroe_muerto:
            self.ventana.after(1500, self.gestionar_game_over)
        else:
            self.ventana.after(1800, lambda: [
                self.escribir_dialogo(f"¿Qué debería hacer\n{self.heroe.nombre.upper()}?"),
                self.btn_lucha.config(state="normal"),
                self.btn_mochila.config(state="normal")
            ])

    # ── Gestión de rondas ─────────────────────────────────────────────────

    def _destruir_arena(self):
        """Para el fondo y destruye todos los widgets de la arena actual."""
        self._detener_fondo()
        self.canvas_escenario.destroy()
        self.card_enano.destroy()
        self.card_nomo.destroy()
        self.frame_historial.destroy()
        self.frame_comandos.destroy()

    def gestionar_victoria_ronda(self):
        self.heroe.ganar_alfajor()

        if self.modo == "Historia" and self.fase_jefe_final:
            self._detener_fondo()
            mixer.music.stop()
            self.ventana.destroy()
            PantallaFinal(victoria=True, hordas=self.ronda_actual, modo=self.modo)
            return

        if self.sound_pasar_ronda: self.sound_pasar_ronda.play()

        self.ronda_actual += 1
        msg = (f"🏆 ¡Mataste al enano! Sumás +1 Guaymallén 🍪.\n"
               f"⚠️ Recordá que tu escudo NO se cura solo, seguís con la armadura gastada...")

        if self.modo == "Historia" and self.ronda_actual == 6:
            msg = ("🏆 ¡Limpiaste las 5 hordas de lacayos!\n\n"
                   "🛡 ¡TE ENCONTRÁS UN ESCUDO EN EL PISO!\n"
                   "Robertito se lo pone encima y queda blindado\n"
                   "para aguantar los paravalanchas del JEFE FALOPINO...")
            self.heroe.armadura_rota = False
            if self.dificultad == 1:
                self.heroe._armadura_equipada = Armadura("Tapa de Olla Nivel 1", 3)
            elif self.dificultad == 2:
                self.heroe._armadura_equipada = Armadura("Tapa de Olla de Aluminio", 3)
            else:
                self.heroe._armadura_equipada = Armadura("Portón de Reja Blindado", 4)
                self.heroe.sprite_base = "nomo_dificil_armadura.png"
                self.heroe.sprite_roto = "nomo_dificil.png"

        if self.sound_obtener_item: self.sound_obtener_item.play()
        messagebox.showinfo("PRÓXIMA ONDA", msg)

        self._destruir_arena()
        self.generar_nuevo_enemigo()
        self.reproducir_musica_ambiente()
        self.crear_arena_grafica()
        self.actualizar_pantalla()

    def gestionar_game_over(self):
        self._detener_fondo()
        mixer.music.stop()
        self.ventana.destroy()
        PantallaFinal(victoria=False, hordas=self.ronda_actual, modo=self.modo)


# =========================================================================
# PANTALLA FINAL
# =========================================================================

class PantallaFinal:
    def __init__(self, victoria, hordas, modo="Historia"):
        self.root = tk.Tk()
        self.root.title("Fin del Juego")
        self.root.geometry("750x640")
        self.root.resizable(False, False)
        self.root.configure(bg="#0b0f19")

        self.victoria     = victoria
        self.hordas       = hordas
        self.modo         = modo
        self.anclas_final = {}

        mixer.init()
        try:
            mixer.music.load("victoria.mp3" if victoria else "derrota.mp3")
            mixer.music.play(-1)
        except:
            pass

        self.crear_interfaz()
        self.root.mainloop()

    def ir_al_menu(self):
        mixer.music.stop()
        self.root.destroy()
        menu = VentanaConfiguracion()
        menu.root.mainloop()
        if menu.confirmado:
            game = ArenaPokemon(dificultad=menu.dificultad_elegida, modo=menu.modo_elegido)
            game.ventana.mainloop()

    def iniciar_restart_real(self):
        mixer.music.stop()
        self.root.destroy()
        game = ArenaPokemon(dificultad=ULTIMA_DIFICULTAD, modo=ULTIMO_MODO)
        game.ventana.mainloop()

    def cargar_img_f(self, ruta, clave, w, h):
        try:
            img = Image.open(ruta).resize((w, h), Image.Resampling.LANCZOS)
            self.anclas_final[clave] = ImageTk.PhotoImage(img)
            return self.anclas_final[clave]
        except:
            return None

    def crear_interfaz(self):
        canvas_render = tk.Canvas(self.root, width=750, height=350,
                                  highlightthickness=0, bg="#000000")
        canvas_render.place(x=0, y=0)

        if self.victoria:
            img_f = self.cargar_img_f("imagen_victoria.png", "v_bg", 750, 350)
            if img_f: canvas_render.create_image(375, 175, image=img_f)
            text_p = (
                "¡Felicidades, ganaste! Tomá tu porción de píxeles con forma de milanesa, campeón del mundo. "
                "Lograste erradicar a la plaga de los enanos, rescataste el Sagrado Manjar entre dos panes y tu gnomo "
                "se consagró como el rey indiscutido del pasillo 3 de la villa medieval. Sos un héroe. Una leyenda viviente.\n\n"
                "But bajemos a la realidad un toque: estuviste tres horas seguidas mirando enanos en 16 bits cagarse a piñas "
                "por un bife de nalga engualichado. El olor a chivo que emana de tu pieza está alterando el ecosistema local "
                "y tu vieja ya está buscando el agua bendita porque piensa que te poseyó un duende.\n\n"
                "Gracias por jugar el juego, posta. Ahora hacenos un favor a todos: apagá la compu, abrí la ventana, salí a la vereda "
                "y TOCÁ PASTO, gordo compu. Urgente."
            )
            col_txt = "#2ecc71"
        else:
            if self.modo == "Infinito":
                img_f = self.cargar_img_f("imagen_fin_infinito.png", "inf_bg", 750, 350)
                if img_f: canvas_render.create_image(375, 175, image=img_f)
                rec_anterior = obtener_record_maximo()
                if self.hordas > rec_anterior:
                    guardar_nuevo_record(self.hordas)
                    msg_rec = (f"✨ ¡NUEVO RÉCORD DEL PASILLO! ✨\n"
                               f"Llegaste hasta la Ronda {self.hordas}.\n"
                               f"Superaste tu récord viejo de {rec_anterior} rondas.")
                else:
                    msg_rec = (f"Llegaste hasta la Ronda {self.hordas}.\n"
                               f"Tu récord máximo actual es de Ronda {rec_anterior}.")
                text_p = (f"💀 FIN DEL MODO INFINITO 💀\n\n{msg_rec}\n\n"
                          f"¿Vas a dejar que la mafia se quede con los récords del barrio o vas a intentar de vuelta?")
                col_txt = "#9b59b6"
            else:
                img_f = self.cargar_img_f("imagen_derrota.png", "d_bg", 750, 350)
                if img_f: canvas_render.create_image(375, 175, image=img_f)
                text_p = (
                    "JAJAJA NOOO, ¡ALTO MANCO!\n\n"
                    "Qué deprimente lo tuyo, hermano. Mirá que la IA del juego la programamos en media hora arriba de un bondi, "
                    "pero las decisiones de tu cerebro fueron peores que el servicio de Edenor en pleno enero. Hasta un caniche con "
                    "parkinson y miopía avanzada te metía un combo más digno con el Tramontina doblado.\n\n"
                    "El Lore de tu Fracaso: Gracias a tu increíble falta de pulgar, el enano gordo ruso se comió la milanesa de un solo "
                    "bocado en tu cara, eructó en clave morse y usó tu gorrito de gnomo para destapar la canaleta. El barrio cayó en una "
                    "edad oscura de desnutrición y cumbia rancia. Todo por tu culpa.\n\n"
                    "¿Qué vas a hacer ahora? ¿Vas a llorar en Twitter o vas a intentar de vuelta, boludo? Dale, metele \"Reintentar\" "
                    "a ver si esta vez coordinás dos neuronas libres."
                )
                col_txt = "#e74c3c"

        txt_box = tk.Text(self.root, bg="#111625", fg=col_txt,
                          font=("Courier", 10, "bold"), bd=2, relief="solid",
                          wrap="word", padx=12, pady=8)
        txt_box.place(x=20, y=365, width=710, height=180)
        txt_box.insert(tk.END, text_p)
        txt_box.config(state="disabled")

        self.img_b_casa = self.cargar_img_f("boton_casa.png",    "btn_c", 55,  55)
        self.img_b_rest = self.cargar_img_f("boton_restart.png", "btn_r", 140, 45)

        if self.img_b_casa:
            tk.Button(self.root, image=self.img_b_casa, bg="#0b0f19", bd=0,
                      activebackground="#0b0f19", command=self.ir_al_menu).place(x=250, y=565)
        else:
            tk.Button(self.root, text="CASA", font=("Arial", 11, "bold"),
                      command=self.ir_al_menu).place(x=250, y=565, width=80, height=40)

        if self.img_b_rest:
            tk.Button(self.root, image=self.img_b_rest, bg="#0b0f19", bd=0,
                      activebackground="#0b0f19", command=self.iniciar_restart_real).place(x=380, y=570)
        else:
            tk.Button(self.root, text="REINTENTAR", font=("Arial", 11, "bold"),
                      command=self.iniciar_restart_real).place(x=380, y=565, width=120, height=40)


# =========================================================================
# PANTALLA DE INTRO
# =========================================================================

class PantallaIntro:
    TOTAL_FRAMES  = 45
    FPS           = 10
    MS_POR_FRAME  = 77
    CARPETA_INTRO = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intro")

    def __init__(self, root, al_terminar):
        self.root        = root
        self.al_terminar = al_terminar
        self._frame_idx  = 0
        self._frames     = []
        self._refs       = []
        self._blink_id   = None
        self._after_id   = None
        self._listo      = False
        self._transicion_en_curso = False

        self.canvas = tk.Canvas(root, width=_W, height=_H,
                                highlightthickness=0, bd=0, bg="black")
        self.canvas.place(x=0, y=0)
        root.update()

        self._loading_id = self.canvas.create_text(
            _W // 2, _H // 2, text="Cargando intro...",
            font=("Courier", 14, "bold"), fill="#888888", anchor="center")
        root.update()

        for n in range(1, 66):
            ruta = os.path.join(self.CARPETA_INTRO, f"fotograma{n:05d}.png")
            if not os.path.exists(ruta):
                ruta = os.path.join(self.CARPETA_INTRO, f"fotograma{n:05d}.jpg")
            try:
                img = Image.open(ruta).resize((_W, _H), Image.Resampling.LANCZOS)
                self._frames.append(ImageTk.PhotoImage(img))
            except Exception:
                self._frames.append(None)

        self.canvas.delete(self._loading_id)

        primer_frame = next((f for f in self._frames if f), None)
        self._img_id = self.canvas.create_image(0, 0, anchor="nw",
                                                 image=primer_frame or "")
        if primer_frame:
            self._refs = [primer_frame]

        self._press_id = self.canvas.create_text(
            _W // 2, _H - 50,
            text="▶   TOCÁ CUALQUIER TECLA PARA CONTINUAR   ◀",
            font=("Courier", 11, "bold"), fill="#ffffff",
            anchor="center", state="hidden")

        self.root.bind("<KeyPress>",   self._on_input)
        self.canvas.bind("<Button-1>", self._on_input)
        self.root.after(50, self._iniciar_con_musica)

    def _iniciar_con_musica(self):
        try:
            mixer.init()
            mixer.music.load("sonido_intro.mp3")
            mixer.music.set_volume(0.8)
            mixer.music.play(0)
        except Exception:
            pass
        self._reproducir()

    def _reproducir(self):
        if self._frame_idx >= len(self._frames):
            self._listo = True
            self._parpadear()
            return
        ph = self._frames[self._frame_idx]
        if ph:
            self.canvas.itemconfig(self._img_id, image=ph)
            self._refs = [ph]
        self._frame_idx += 1
        self._after_id = self.root.after(self.MS_POR_FRAME, self._reproducir)

    def _parpadear(self, on=True):
        try:
            self.canvas.itemconfig(self._press_id, state="normal",
                                   fill="#ffffff" if on else "#777777")
        except tk.TclError:
            return
        self._blink_id = self.root.after(500, lambda: self._parpadear(not on))

    def _on_input(self, event=None):
        if self._transicion_en_curso:
            return
        if not self._listo:
            if self._after_id:
                self.root.after_cancel(self._after_id)
                self._after_id = None
            ph = next((f for f in reversed(self._frames) if f), None)
            if ph:
                self.canvas.itemconfig(self._img_id, image=ph)
                self._refs = [ph]
            self._listo = True
            self._parpadear()
            return
        self._transicion_en_curso = True
        if self._blink_id:
            self.root.after_cancel(self._blink_id)
            self._blink_id = None
        self.root.unbind("<KeyPress>")
        self.canvas.unbind("<Button-1>")
        self._fade_salida(step=0)

    def _fade_salida(self, step=0):
        alpha_steps = [0, 30, 60, 90, 120, 150, 180, 210, 230, 245, 255]
        if step <= 10:
            a = alpha_steps[min(step, len(alpha_steps)-1)]
            overlay = Image.new("RGBA", (_W, _H), (0, 0, 0, a))
            ph = ImageTk.PhotoImage(overlay)
            self._refs.append(ph)
            if not hasattr(self, '_overlay_id'):
                self._overlay_id = self.canvas.create_image(0, 0, anchor="nw", image=ph)
            else:
                self.canvas.itemconfig(self._overlay_id, image=ph)
            self.root.after(25, lambda: self._fade_salida(step + 1))
        else:
            try:
                mixer.music.stop()
            except Exception:
                pass
            self.root.configure(bg="black")
            try:
                self.canvas.destroy()
            except tk.TclError:
                pass
            self.root.update()
            self._frames.clear()
            self.al_terminar()


# =========================================================================
# MAIN
# =========================================================================

def main():
    intro_root = tk.Tk()
    intro_root.title("Gnomos vs Enanos")
    intro_root.geometry(f"{_W}x{_H}")
    intro_root.resizable(False, False)
    intro_root.configure(bg="black")

    intro_terminada = [False]

    def al_terminar_intro():
        intro_terminada[0] = True
        intro_root.destroy()

    PantallaIntro(intro_root, al_terminar=al_terminar_intro)
    intro_root.mainloop()

    if not intro_terminada[0]:
        return

    menu = VentanaConfiguracion()
    menu.root.mainloop()

    if menu.confirmado:
        game = ArenaPokemon(dificultad=menu.dificultad_elegida, modo=menu.modo_elegido)
        game.ventana.mainloop()


if __name__ == "__main__":
    main()