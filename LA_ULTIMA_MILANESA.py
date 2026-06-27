import random
import tkinter as tk
from tkinter import messagebox
import os
import json

from PIL import Image, ImageDraw, ImageTk
from pygame import mixer

try:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
except:
    pass

# guarda el record del modo infinito en un json
ARCHIVO_RECORD = "record_infinito.json"

def leer_record():
    if os.path.exists(ARCHIVO_RECORD):
        try:
            with open(ARCHIVO_RECORD, "r") as f:
                return json.load(f).get("record", 1)
        except:
            return 1
    return 1

def guardar_record(ronda):
    try:
        with open(ARCHIVO_RECORD, "w") as f:
            json.dump({"record": ronda}, f)
    except:
        pass

ultima_dif = 2
ultimo_modo = "Historia"

# colores del menu
COLOR_ORO = "#D4AF37"
COLOR_AMBAR = "#B46E14"
COLOR_VERDE_BTN = "#14A03C"
ANCHO, ALTO = 620, 580

# velocidad del fondo animado en ms (100 = ~10fps, bastante fluido)
VEL_FONDO = 100

# carpetas de recursos
SND = "sonidos"
SPR = "sprites"
FIN = "finales"
FND = "fondo"

def ruta_snd(f): return os.path.join(SND, f)
def ruta_spr(f): return os.path.join(SPR, f)
def ruta_fin(f): return os.path.join(FIN, f)
def ruta_fnd(f): return os.path.join(FND, f)


# ---- clases del juego ----

class Personaje:
    def __init__(self, nombre, salud, arma, armadura=None, sprite_base="", sprite_roto="", esquiva=0):
        self.nombre = nombre
        self.hp = salud
        self.hp_max = salud
        self.arma = arma
        self.armadura = armadura
        self.sprite_base = sprite_base
        self.sprite_roto = sprite_roto
        self.armadura_rota = False
        self.esquiva = esquiva

    def obtener_salud(self):
        return self.hp

    def __add__(self, curacion):
        self.hp = min(self.hp + curacion, self.hp_max)
        return self

    def recibir_daño(self, dmg, arena):
        # chance de esquivar
        if random.randint(1, 100) <= self.esquiva:
            if arena.snd_esquivar:
                arena.snd_esquivar.play()
            return f"🤸‍♂️ ¡{self.nombre} tiró un esquive fisura en el piso!\n", False

        msg_arm = ""
        if self.armadura and not self.armadura_rota:
            dmg = self.armadura.absorber(dmg)
            msg_arm = "🛡️ ¡Mitigado por armadura!\n"
            if self.hp - dmg <= self.hp_max * 0.5:
                self.armadura_rota = True
                msg_arm += "💥 ¡LA ARMADURA SE HIZO PEDAZOS!\n"
                if arena.snd_romper_arm:
                    arena.snd_romper_arm.play()

        self.hp -= dmg
        if self.hp <= 0:
            self.hp = 0
            return f"{msg_arm}💀 {self.nombre} mordió el polvo.\n", True
        return f"{msg_arm}💥 {self.nombre} recibió {dmg:.1f} de daño.\n", False

    def atacar(self, objetivo, arena):
        golpe = self.arma.tirar_daño()
        reporte, murio = objetivo.recibir_daño(golpe, arena)
        return f"⚔️ {self.nombre} atacó con {self.arma.nombre}.\n{reporte}", murio


class Jugador(Personaje):
    def __init__(self, nombre, salud, arma, armadura=None, alfajores=2, sprite_base="", sprite_roto=""):
        super().__init__(nombre, salud, arma, armadura, sprite_base, sprite_roto, esquiva=0)
        self.alfajores = alfajores

    def obtener_cantidad_alfajores(self):
        return self.alfajores

    def usar_alfajor(self):
        if self.alfajores > 0:
            self.alfajores -= 1
            self + 50
            return True
        return False

    def ganar_alfajor(self):
        self.alfajores += 1


class Arma:
    def __init__(self, nombre, dmg_min, dmg_max):
        self.nombre = nombre
        self.dmg_min = dmg_min
        self.dmg_max = dmg_max

    def tirar_daño(self):
        return random.randint(self.dmg_min, self.dmg_max)


class Armadura:
    def __init__(self, nombre, res):
        self.nombre = nombre
        self.res = res

    def absorber(self, dmg):
        return max(0, dmg - self.res)


# ---- tipos de enanos ----

class EnanoManija(Personaje):
    def __init__(self, dif, *args):
        if dif == "facil":
            super().__init__("Enano Manija", 30, Arma("Vino en Cartón Cortado", 3, 6), None,
                             ruta_spr("enano_manija_facil.png"), ruta_spr("enano_manija_facil.png"), esquiva=35)
        elif dif == "medio":
            super().__init__("Enano Manija", 45, Arma("Tramontina Oxidado", 4, 7), Armadura("Remera a Rayas Estirada", 1),
                             ruta_spr("enano_manija_medio_armadura.png"), ruta_spr("enano_manija_medio_sin_armadura.png"), esquiva=35)
        else:
            super().__init__("Enano Manija", 55, Arma("Pico de Botella Roto", 7, 13), Armadura("Campera de Cuero Tachonada", 1),
                             ruta_spr("enano_manija_dificil_armadura.png"), ruta_spr("enano_manija_dificil_sin_armadura.png"), esquiva=35)


class EnanoComunacho(Personaje):
    def __init__(self, dif, *args):
        if dif == "facil":
            super().__init__("Enano Comunacho", 40, Arma("Tramontina Doblado", 4, 8), None,
                             ruta_spr("enano_machete.png"), ruta_spr("enano_machete.png"), esquiva=10)
        elif dif == "medio":
            super().__init__("Enano Comunacho", 55, Arma("Fierro de Obra", 5, 9), Armadura("Chapa de Aluminio", 1),
                             ruta_spr("enano_fierro_armadura.png"), ruta_spr("enano_comun_medio_sin_armadura.png"), esquiva=10)
        else:
            super().__init__("Enano Comunacho", 70, Arma("Espada Oxidada de Reja", 9, 15), Armadura("Escudo de Madera Maciza", 2),
                             ruta_spr("enano_comun_dificil_armadura.png"), ruta_spr("enano_comun_dificil_sin_armadura.png"), esquiva=10)


class EnanoMorfi(Personaje):
    def __init__(self, dif, *args):
        if dif == "facil":
            super().__init__("Enano Morfi", 60, Arma("Maza de Goma", 5, 10), None,
                             ruta_spr("enano_tanque_facil.png"), ruta_spr("enano_tanque_facil.png"), esquiva=0)
        elif dif == "medio":
            super().__init__("Enano Morfi", 85, Arma("Cartel de Moscú", 6, 11), Armadura("Chaleco de Lana Grueso", 2),
                             ruta_spr("enano_tanque_medio_armadura.png"), ruta_spr("enano_tanque_medio_sin_armadura.png"), esquiva=0)
        else:
            super().__init__("Enano Morfi", 100, Arma("Garrafa de Gas de 10Kg", 11, 18), Armadura("Traje de Chatarrero Blindado", 3),
                             ruta_spr("enano_tanque_dificil_armadura.png"), ruta_spr("enano_tanque_dificil_sin_armadura.png"), esquiva=0)


class JefeFalopino(Personaje):
    def __init__(self):
        super().__init__(
            nombre="Jefe Falopino",
            salud=135,
            arma=Arma("Palo de Paravalancha de Boca", 13, 23),
            armadura=Armadura("Armadura Medieval de Platino", 5),
            sprite_base=ruta_spr("jefe_armadura.png"),
            sprite_roto=ruta_spr("jefe_sin_armadura.png"),
            esquiva=10
        )


# ---- helpers visuales ----

def hacer_panel(w, h, color=(10, 6, 2), alpha=130, radio=10, borde="#D4AF37", grosor=2, glow=False):
    rgb_borde = tuple(int(borde[i:i+2], 16) for i in (1, 3, 5))
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([0, 0, w-1, h-1], radius=radio,
                         fill=(*color, alpha), outline=(*rgb_borde, 210), width=grosor)
    if glow:
        d.rounded_rectangle([grosor+1, grosor+1, w-grosor-2, h-grosor-2],
                              radius=max(radio-2, 2), outline=(255, 220, 100, 50), width=1)
    return img


def cargar_frames(carpeta, prefijo, ancho, alto, hasta=61):
    """carga los frames del fondo animado de una carpeta dada"""
    frames = []
    ruta_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), carpeta)
    if not os.path.exists(ruta_base):
        print(f"no encuentro la carpeta: {ruta_base}")
        return frames
    for n in range(1, hasta + 1, 4):
        archivo = f"{prefijo}{n:05d}.png"
        ruta = os.path.join(ruta_base, archivo)
        try:
            img = Image.open(ruta).resize((ancho, alto), Image.Resampling.LANCZOS)
            frames.append(ImageTk.PhotoImage(img))
        except Exception as e:
            print(f"no se pudo cargar {archivo}: {e}")
    return frames


# ---- menu principal ----

class MenuInicio:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gnomos vs Enanos — Menú")
        self.root.geometry(f"{ANCHO}x{ALTO}")
        self.root.resizable(False, False)

        self.dificultad = 2
        self.modo = "Historia"
        self.confirmado = False

        self._refs = []
        self._ids_filas = [None, None, None]
        self._imgs_filas = [None, None, None]
        self._ids_modos = {}

        mixer.init()
        try:
            mixer.music.load(ruta_snd("musica_menu.mp3"))
            mixer.music.set_volume(0.5)
            mixer.music.play(-1)
        except:
            pass

        self.armar_pantalla()

    def armar_pantalla(self):
        self.canvas = tk.Canvas(self.root, width=ANCHO, height=ALTO, highlightthickness=0, bd=0)
        self.canvas.place(x=0, y=0)

        try:
            fondo = Image.open(ruta_fnd("fondo_menu.png")).resize((ANCHO, ALTO), Image.Resampling.LANCZOS)
        except:
            fondo = Image.new("RGB", (ANCHO, ALTO), "#1a0a00")

        # viñeta encima del fondo
        vig = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, 0))
        vd = ImageDraw.Draw(vig)
        for i in range(110):
            a = int(155 * (i / 110) ** 1.8)
            vd.rectangle([i, i, ANCHO-1-i, ALTO-1-i], outline=(0, 0, 0, a))
        resultado = Image.alpha_composite(fondo.convert("RGBA"), vig)
        self._bg_photo = ImageTk.PhotoImage(resultado.convert("RGB"))
        self.canvas.create_image(0, 0, anchor="nw", image=self._bg_photo)

        self._pegar(hacer_panel(500, 46, color=(8,4,0), alpha=165, radio=8, borde=COLOR_ORO, grosor=2, glow=True), 60, 17)
        self._pegar(hacer_panel(500, 160, color=(8,5,0), alpha=128, radio=10, borde=COLOR_AMBAR, grosor=2, glow=True), 60, 76)
        self._pegar(hacer_panel(540, 188, color=(5,5,15), alpha=110, radio=10, borde=COLOR_AMBAR, grosor=2, glow=True), 40, 268)
        self._pegar(hacer_panel(540, 52, color=(10,80,25), alpha=235, radio=10, borde="#32C850", grosor=2, glow=True), 40, 490)

        self._y_filas = [115, 155, 195]
        self._redibujar_filas_dif()

        for key, y in [("Historia", 310), ("Infinito", 386)]:
            ph = ImageTk.PhotoImage(Image.new("RGBA", (510, 62), (0,0,0,0)))
            self._refs.append(ph)
            self._ids_modos[key] = self.canvas.create_image(55, y, anchor="nw", image=ph)

        self.canvas.create_text(310, 40, text="⚔️ GNOMOS VS ENANITOS ⚔️",
            font=("Courier", 15, "bold"), fill=COLOR_ORO, anchor="center")
        self.canvas.create_text(83, 94, text="🧠 SELECCIONÁ TU GNOMO",
            font=("Arial", 10, "bold"), fill="#ffffff", anchor="w")

        textos_dif = [
            "🟢 ROBERTITO (Fácil): Sifón rendidor, Enanos sin escudo.",
            "🟡 ROBERTITO (Medio): Macana de palo de escoba, Balanceado criollo.",
            "🔴 ROBERTITO (Ultra): Tramontina doblegado, vas a puro pulmón.",
        ]
        for i, t in enumerate(textos_dif):
            self.canvas.create_text(82, self._y_filas[i] + 12, text=t,
                font=("Arial", 9), fill="#dddddd", anchor="w")

        self.canvas.create_text(63, 284, text="🕹️ MODOS DE COMBATE",
            font=("Arial", 10, "bold"), fill="#ffffff", anchor="w")

        self._txt_modos = {}
        self._txt_modos["Historia"] = [
            self.canvas.create_text(310, 339, text="📜 MODO HISTORIA",
                font=("Courier", 11, "bold"), fill="#ffffff", anchor="center"),
            self.canvas.create_text(310, 358, text="(5 Rondas de Lacayos + El Jefe Falopino)",
                font=("Courier", 9), fill="#cccccc", anchor="center"),
        ]
        self._txt_modos["Infinito"] = [
            self.canvas.create_text(310, 415, text="♾️ MODO INFINITO",
                font=("Courier", 11, "bold"), fill="#aaaaaa", anchor="center"),
            self.canvas.create_text(310, 434, text="(Hordas sin fin. Buscando romper el Récord del Barrio)",
                font=("Courier", 9), fill="#888888", anchor="center"),
        ]

        r_h = self.canvas.create_rectangle(55, 310, 565, 372, fill="", outline="", tags="clickable")
        r_i = self.canvas.create_rectangle(55, 386, 565, 448, fill="", outline="", tags="clickable")
        self.canvas.tag_bind(r_h, "<Button-1>", lambda e: self.elegir_modo("Historia"))
        self.canvas.tag_bind(r_i, "<Button-1>", lambda e: self.elegir_modo("Infinito"))
        for tid in self._txt_modos["Historia"]:
            self.canvas.tag_bind(tid, "<Button-1>", lambda e: self.elegir_modo("Historia"))
        for tid in self._txt_modos["Infinito"]:
            self.canvas.tag_bind(tid, "<Button-1>", lambda e: self.elegir_modo("Infinito"))

        self._redibujar_btns_modo()

        self._btns_dif = []
        for i, label in enumerate(["Fácil", "Medio", "Ultra"]):
            y = self._y_filas[i] + 2
            b = tk.Button(self.root, text=label, font=("Arial", 9, "bold"), width=8,
                          bg="#222222", fg="#999999", relief="flat", bd=0,
                          activebackground="#333333", activeforeground="white", cursor="hand2")
            b.place(x=494, y=y, width=62, height=26)
            self._btns_dif.append(b)
        for i in range(3):
            self._btns_dif[i].config(command=lambda n=i+1: self.elegir_dificultad(n))
        self._estilo_dif()

        tk.Button(self.root, text="🔥 IR A COPAR EL PASILLO 🔥",
            font=("Courier", 12, "bold"), bg=COLOR_VERDE_BTN, fg="white",
            activebackground="#0d7a2a", activeforeground="white",
            relief="flat", bd=0, cursor="hand2",
            command=self.arrancar
        ).place(x=42, y=492, width=536, height=48)

    def _pegar(self, panel_pil, x, y):
        ph = ImageTk.PhotoImage(panel_pil)
        self._refs.append(ph)
        self.canvas.create_image(x, y, anchor="nw", image=ph)

    def _redibujar_filas_dif(self):
        colores = {1: (30,80,30), 2: (130,90,10), 3: (100,15,10)}
        bordes = {1: "#32C850", 2: COLOR_ORO, 3: "#C83220"}
        for i in range(3):
            n = i + 1
            if self.dificultad == n:
                hl = hacer_panel(488, 32, color=colores[n], alpha=65, radio=5, borde=bordes[n], grosor=1)
            else:
                hl = Image.new("RGBA", (488, 32), (0,0,0,0))
            ph = ImageTk.PhotoImage(hl)
            self._refs.append(ph)
            self._imgs_filas[i] = ph
            if self._ids_filas[i]:
                self.canvas.delete(self._ids_filas[i])
            self._ids_filas[i] = self.canvas.create_image(66, self._y_filas[i] - 2, anchor="nw", image=ph)

    def _redibujar_btns_modo(self):
        configs = [
            ("Historia", 310, (20, 50, 100), "#5080D0"),
            ("Infinito", 386, (60, 10, 80), "#9040C0"),
        ]
        for key, y, col, borde in configs:
            activo = self.modo == key
            panel = hacer_panel(510, 62, color=col,
                                alpha=210 if activo else 70, radio=8,
                                borde=borde if activo else COLOR_AMBAR,
                                grosor=2 if activo else 1, glow=activo)
            ph = ImageTk.PhotoImage(panel)
            self._refs.append(ph)
            if key in self._ids_modos:
                self.canvas.delete(self._ids_modos[key])
            self._ids_modos[key] = self.canvas.create_image(55, y, anchor="nw", image=ph)

        if hasattr(self, "_txt_modos"):
            for key in ("Historia", "Infinito"):
                for tid in self._txt_modos[key]:
                    self.canvas.tag_raise(tid)
        self.canvas.tag_raise("clickable")

    def _estilo_dif(self):
        paleta = {1: ("#2ecc71","black"), 2: ("#f1c40f","black"), 3: ("#e74c3c","white")}
        for i, b in enumerate(self._btns_dif):
            n = i + 1
            if n == self.dificultad:
                bg, fg = paleta[n]
                b.config(bg=bg, fg=fg)
            else:
                b.config(bg="#222222", fg="#666666")

    def _estilo_modo(self):
        for key in ("Historia", "Infinito"):
            color = (255, 255, 200) if self.modo == key else (100, 90, 60)
            hex_col = "#{:02x}{:02x}{:02x}".format(*color)
            for tid in self._txt_modos[key]:
                self.canvas.itemconfig(tid, fill=hex_col)

    def elegir_dificultad(self, d):
        self.dificultad = d
        self._redibujar_filas_dif()
        self._estilo_dif()

    def elegir_modo(self, modo):
        self.modo = modo
        self._redibujar_btns_modo()
        self._estilo_modo()

    def arrancar(self):
        global ultima_dif, ultimo_modo
        ultima_dif = self.dificultad
        ultimo_modo = self.modo
        self.confirmado = True
        mixer.music.stop()
        self.root.destroy()


# ---- arena de pelea ----

class Arena:
    def __init__(self, dificultad, modo):
        self.dificultad = dificultad
        self.modo = modo
        self.ronda = 1
        self.es_jefe = False
        self.dif_str = "medio"

        self._frames_fondo = []
        self._idx_fondo = 0
        self._after_fondo = None
        self._ref_fondo = None

        if dificultad == 1:
            self.dif_str = "facil"
            self.heroe = Jugador("Robertito", 140,
                Arma("Sifón con Escudo Quilmes", 16, 28),
                Armadura("Tapa de Olla Nivel 1", 3), 3,
                ruta_spr("nomo_facil_armadura.png"), ruta_spr("nomo_facil_sin_armadura.png"))
        elif dificultad == 2:
            self.dif_str = "medio"
            self.heroe = Jugador("Robertito", 110,
                Arma("Sifón Clásico", 14, 25),
                Armadura("Tapa de Olla de Aluminio", 3), 2,
                ruta_spr("nomo_medio_armadura.png"), ruta_spr("nomo_medio_sin_armadura.png"))
        else:
            self.dif_str = "dificil"
            self.heroe = Jugador("Robertito", 105,
                Arma("Machete Oxidado de Mano", 14, 28),
                None, 2,
                ruta_spr("nomo_dificil.png"), ruta_spr("nomo_dificil.png"))

        self.nuevo_enemigo()

        self.ventana = tk.Tk()
        self.ventana.title(f"Arena de Pelea - Ronda {self.ronda}")
        self.ventana.geometry("750x550")
        self.ventana.resizable(False, False)

        self.imgs = {}
        self.X_NOMO, self.Y_NOMO = 220, 249
        self.X_ENANO, self.Y_ENANO = 603, 149

        mixer.init()
        self.cargar_sonidos()
        self.poner_musica()
        self.construir_arena()
        self.refrescar()

    def nuevo_enemigo(self):
        if self.modo == "Historia" and self.ronda == 6:
            self.es_jefe = True
            self.enemigo = JefeFalopino()
        else:
            tipo = random.choice([EnanoManija, EnanoComunacho, EnanoMorfi])
            self.enemigo = tipo(self.dif_str, None, None)

    def cargar_sonidos(self):
        def s(f):
            try: return mixer.Sound(f)
            except: return None
        self.snd_ataque     = s(ruta_snd("hace_daño.mp3"))
        self.snd_recibe     = s(ruta_snd("recibe_daño.mp3"))
        self.snd_cura       = s(ruta_snd("curacion.mp3"))
        self.snd_nop        = s(ruta_snd("nop.mp3"))
        self.snd_romper_arm = s(ruta_snd("romper_armadura.mp3"))
        self.snd_esquivar   = s(ruta_snd("esquivar.mp3"))
        self.snd_muerte     = s(ruta_snd("muerte.mp3"))
        self.snd_ronda_ok   = s(ruta_snd("pasaste_ronda.mp3"))
        self.snd_item       = s(ruta_snd("obtener_item.mp3"))

    def poner_musica(self):
        try:
            if self.es_jefe:
                mixer.music.stop()
                mixer.music.load(ruta_snd("batalla_final.mp3"))
                mixer.music.set_volume(0.85)
                mixer.music.play(-1)
            else:
                if not mixer.music.get_busy():
                    mixer.music.load(ruta_snd("musica_batalla.mp3"))
                    mixer.music.set_volume(0.75)
                    mixer.music.play(-1)
        except:
            pass

    def cargar_img(self, ruta, key, w, h):
        try:
            img = Image.open(ruta).resize((w, h), Image.Resampling.LANCZOS)
            ph = ImageTk.PhotoImage(img)
            self.imgs[key] = ph
            return ph
        except Exception as e:
            print(f"no se pudo cargar {ruta}: {e}")
            return None

    def parar_fondo(self):
        if self._after_fondo:
            try: self.ventana.after_cancel(self._after_fondo)
            except: pass
            self._after_fondo = None

    def arrancar_fondo(self, frames):
        self.parar_fondo()
        self._frames_fondo = frames
        self._idx_fondo = 0
        if frames:
            self.tick_fondo()

    def tick_fondo(self):
        if not self._frames_fondo:
            return
        ph = self._frames_fondo[self._idx_fondo]
        if ph:
            try:
                self.canvas.itemconfig(self._id_fondo, image=ph)
                self._ref_fondo = ph
            except tk.TclError:
                return
        self._idx_fondo = (self._idx_fondo + 1) % len(self._frames_fondo)
        self._after_fondo = self.ventana.after(VEL_FONDO, self.tick_fondo)

    def construir_arena(self):
        self.canvas = tk.Canvas(self.ventana, width=750, height=360, highlightthickness=0)
        self.canvas.place(x=0, y=0)

        self._id_fondo = self.canvas.create_image(375, 180, anchor="center")

        if self.es_jefe:
            frames = cargar_frames("fondo_final", "fondo_final", 750, 360, hasta=65)
            if frames:
                self.arrancar_fondo(frames)
            else:
                img = self.cargar_img("fondo_final.png", f"fondo_{self.ronda}", 750, 360)
                if img:
                    self.canvas.itemconfig(self._id_fondo, image=img)
                else:
                    self.canvas.configure(bg="#2c3e50")
        else:
            frames = cargar_frames("fondo_normal", "fondo_normal", 750, 360, hasta=61)
            if frames:
                self.arrancar_fondo(frames)
            else:
                img = self.cargar_img(ruta_spr("fondo.png"), f"fondo_{self.ronda}", 750, 360)
                if img:
                    self.canvas.itemconfig(self._id_fondo, image=img)
                else:
                    self.canvas.configure(bg="#eae6d8")

        # card del enemigo
        self.card_enano = tk.Canvas(self.ventana, width=260, height=75,
                                    bg="#fbf9f0", bd=2, relief="solid", highlightthickness=0)
        self.card_enano.place(x=40, y=30)
        self.lbl_nom_enano = tk.Label(self.card_enano, text=self.enemigo.nombre.upper(),
                                      font=("Courier", 11, "bold"), bg="#fbf9f0")
        self.lbl_nom_enano.place(x=10, y=8)
        self.lbl_hp_enano = tk.Label(self.card_enano, text="", font=("Courier", 9, "bold"), bg="#fbf9f0")
        self.lbl_hp_enano.place(x=10, y=30)

        # card del heroe
        self.card_nomo = tk.Canvas(self.ventana, width=260, height=90,
                                   bg="#fbf9f0", bd=2, relief="solid", highlightthickness=0)
        self.card_nomo.place(x=450, y=240)
        self.lbl_nom_nomo = tk.Label(self.card_nomo, text=self.heroe.nombre.upper(),
                                     font=("Courier", 11, "bold"), bg="#fbf9f0")
        self.lbl_nom_nomo.place(x=10, y=8)
        self.lbl_hp_nomo = tk.Label(self.card_nomo, text="", font=("Courier", 9, "bold"), bg="#fbf9f0")
        self.lbl_hp_nomo.place(x=10, y=30)
        self.lbl_alfas = tk.Label(self.card_nomo, text="", font=("Courier", 8, "italic"),
                                  bg="#fbf9f0", fg="#7f8c8d")
        self.lbl_alfas.place(x=10, y=65)

        # sprites
        self.img_nomo = self.cargar_img(self.heroe.sprite_base, f"n_b_{self.ronda}", 224, 224)
        self.img_nomo_roto = self.cargar_img(self.heroe.sprite_roto, f"n_r_{self.ronda}", 224, 224)

        if self.img_nomo and not self.heroe.armadura_rota:
            self.id_nomo = self.canvas.create_image(self.X_NOMO, self.Y_NOMO, image=self.img_nomo)
        elif self.img_nomo_roto:
            self.id_nomo = self.canvas.create_image(self.X_NOMO, self.Y_NOMO, image=self.img_nomo_roto)
        else:
            self.id_nomo = self.canvas.create_rectangle(
                self.X_NOMO-40, self.Y_NOMO-40, self.X_NOMO+40, self.Y_NOMO+40, fill="#e67e22")

        self.img_enano = self.cargar_img(self.enemigo.sprite_base, f"e_b_{self.ronda}", 205, 205)
        self.img_enano_roto = self.cargar_img(self.enemigo.sprite_roto, f"e_r_{self.ronda}", 205, 205)

        if self.img_enano:
            self.id_enano = self.canvas.create_image(self.X_ENANO, self.Y_ENANO, image=self.img_enano)
        else:
            self.id_enano = self.canvas.create_rectangle(
                self.X_ENANO-40, self.Y_ENANO-40, self.X_ENANO+40, self.Y_ENANO+40, fill="#bdc3c7")

        self.img_guayma = self.cargar_img(ruta_spr("guaymallen.png"), "guaymallen", 50, 50)

        # dialogo
        self.frame_log = tk.Frame(self.ventana, bg="#253446", bd=4, relief="ridge")
        self.frame_log.place(x=10, y=380, width=440, height=150)
        self.txt_log = tk.Text(self.frame_log, bg="#253446", fg="white",
                               font=("Courier", 11, "bold"), bd=0, wrap="word", padx=12, pady=12)
        self.txt_log.pack(fill="both", expand=True)

        # botones
        self.frame_btns = tk.Frame(self.ventana, bg="white", bd=4, relief="ridge")
        self.frame_btns.place(x=460, y=380, width=280, height=150)
        self.btn_lucha = tk.Button(self.frame_btns, text="⚔️ LUCHA",
                                   font=("Courier", 14, "bold"), bg="white", fg="black",
                                   bd=0, command=self.atacar)
        self.btn_lucha.place(x=10, y=15, width=250, height=50)
        self.btn_mochila = tk.Button(self.frame_btns, text="🎒 MOCHILA",
                                     font=("Courier", 14, "bold"), bg="white", fg="black",
                                     bd=0, command=self.usar_item)
        self.btn_mochila.place(x=10, y=75, width=250, height=50)

        if self.es_jefe:
            msg = "🔥 ¡EL BARRIO ESTÁ TOTALMENTE PRENDIDO FUEGO! 🔥\nEL JEFE FALOPINO sale a reventarte.\n¿Qué hará tu Gnomo?"
        else:
            msg = f"¡RONDA {self.ronda}! Un {self.enemigo.nombre} te corta el pasillo.\n¿Qué hace tu Gnomo?"
        self.log(msg)

    def log(self, texto):
        self.txt_log.config(state="normal")
        self.txt_log.delete("1.0", tk.END)
        self.txt_log.insert(tk.END, texto)
        self.txt_log.config(state="disabled")

    def refrescar(self):
        self.lbl_nom_enano.config(text=self.enemigo.nombre.upper())
        self.lbl_hp_nomo.config(text=f"PS: {self.heroe.obtener_salud():.1f} / {self.heroe.hp_max}")
        self.lbl_hp_enano.config(text=f"PS: {self.enemigo.obtener_salud():.1f} / {self.enemigo.hp_max}")
        self.lbl_alfas.config(text=f"Guaymalléns: {self.heroe.obtener_cantidad_alfajores()} 🍪")

        self.card_enano.delete("barra")
        self.card_nomo.delete("barra")

        pct_e = max(0.0, self.enemigo.obtener_salud() / self.enemigo.hp_max)
        c_e = "#2ecc71" if pct_e > 0.2 else "#e74c3c"
        self.card_enano.create_rectangle(10, 52, 250, 64, fill="#bdc3c7", outline="black", tags="barra")
        self.card_enano.create_rectangle(10, 52, 10 + int(240*pct_e), 64, fill=c_e, outline="", tags="barra")

        pct_n = max(0.0, self.heroe.obtener_salud() / self.heroe.hp_max)
        c_n = "#2ecc71" if pct_n > 0.2 else "#e74c3c"
        self.card_nomo.create_rectangle(10, 50, 250, 62, fill="#bdc3c7", outline="black", tags="barra")
        self.card_nomo.create_rectangle(10, 50, 10 + int(240*pct_n), 62, fill=c_n, outline="", tags="barra")

        if self.heroe.armadura_rota and self.img_nomo_roto:
            self.canvas.itemconfig(self.id_nomo, image=self.img_nomo_roto)
        if self.enemigo.armadura_rota and self.img_enano_roto:
            self.canvas.itemconfig(self.id_enano, image=self.img_enano_roto)

    # animaciones de movimiento
    def mover_nomo_adelante(self, x):
        if x < 460:
            x += 20
            self.canvas.coords(self.id_nomo, x, self.Y_NOMO)
            self.ventana.after(15, lambda: self.mover_nomo_adelante(x))
        else:
            if self.snd_ataque: self.snd_ataque.play()
            self.terminar_ataque()

    def mover_nomo_atras(self, x):
        if x > self.X_NOMO:
            x -= 20
            self.canvas.coords(self.id_nomo, x, self.Y_NOMO)
            self.ventana.after(15, lambda: self.mover_nomo_atras(x))
        else:
            self.canvas.coords(self.id_nomo, self.X_NOMO, self.Y_NOMO)

    def mover_enano_adelante(self, x):
        if x > 360:
            x -= 20
            self.canvas.coords(self.id_enano, x, self.Y_ENANO)
            self.ventana.after(15, lambda: self.mover_enano_adelante(x))
        else:
            if self.snd_recibe: self.snd_recibe.play()
            self.terminar_turno_enemigo()
            self.ventana.after(100, lambda: self.mover_enano_atras(x))

    def mover_enano_atras(self, x):
        if x < self.X_ENANO:
            x += 20
            self.canvas.coords(self.id_enano, x, self.Y_ENANO)
            self.ventana.after(15, lambda: self.mover_enano_atras(x))
        else:
            self.canvas.coords(self.id_enano, self.X_ENANO, self.Y_ENANO)

    # acciones del jugador
    def atacar(self):
        self.btn_lucha.config(state="disabled")
        self.btn_mochila.config(state="disabled")
        self.mover_nomo_adelante(self.X_NOMO)

    def terminar_ataque(self):
        reporte, murio = self.heroe.atacar(self.enemigo, self)
        self.log(reporte)
        self.refrescar()
        self.mover_nomo_atras(460)
        if murio:
            if self.snd_muerte: self.snd_muerte.play()
            self.ventana.after(1500, self.victoria_ronda)
        else:
            self.ventana.after(1800, self.turno_enemigo)

    def usar_item(self):
        self.btn_lucha.config(state="disabled")
        self.btn_mochila.config(state="disabled")
        if self.heroe.obtener_cantidad_alfajores() > 0:
            if self.snd_cura: self.snd_cura.play()
            if self.img_guayma:
                id_item = self.canvas.create_image(self.X_NOMO+60, self.Y_NOMO-30, image=self.img_guayma)
            else:
                id_item = self.canvas.create_text(self.X_NOMO+60, self.Y_NOMO-30, text="🍪", font=("Arial", 16))
            self.ventana.after(600, lambda: self.terminar_curacion(id_item))
        else:
            if self.snd_nop: self.snd_nop.play()
            self.log("❌ ¡No te quedan más Guaymallén!\nPerdiste el turno buscando migajas, alto MIGAJERO.")
            self.ventana.after(2200, self.turno_enemigo)

    def terminar_curacion(self, id_item):
        self.heroe.usar_alfajor()
        self.canvas.delete(id_item)
        self.log(f"🍪 ¡{self.heroe.nombre.upper()} se clavó un Guaymallén bajonero!\nRecuperó 50 PS del backend.")
        self.refrescar()
        self.ventana.after(1500, self.turno_enemigo)

    def turno_enemigo(self):
        if self.enemigo.obtener_salud() > 0:
            self.mover_enano_adelante(self.X_ENANO)

    def terminar_turno_enemigo(self):
        reporte, murio = self.enemigo.atacar(self.heroe, self)
        self.log(reporte)
        self.refrescar()
        if murio:
            self.ventana.after(1500, self.game_over)
        else:
            self.ventana.after(1800, lambda: [
                self.log(f"¿Qué debería hacer\n{self.heroe.nombre.upper()}?"),
                self.btn_lucha.config(state="normal"),
                self.btn_mochila.config(state="normal")
            ])

    def limpiar_arena(self):
        self.parar_fondo()
        self.canvas.destroy()
        self.card_enano.destroy()
        self.card_nomo.destroy()
        self.frame_log.destroy()
        self.frame_btns.destroy()

    def victoria_ronda(self):
        self.heroe.ganar_alfajor()

        if self.modo == "Historia" and self.es_jefe:
            self.parar_fondo()
            mixer.music.stop()
            self.ventana.destroy()
            PantallaFin(gano=True, rondas=self.ronda, modo=self.modo)
            return

        if self.snd_ronda_ok: self.snd_ronda_ok.play()

        self.ronda += 1
        msg = f"🏆 ¡Mataste al enano! Sumás +1 Guaymallén 🍪.\n⚠️ Recordá que tu escudo NO se cura solo, seguís con la armadura gastada..."

        if self.modo == "Historia" and self.ronda == 6:
            msg = ("🏆 ¡Limpiaste las 5 hordas de lacayos!\n\n"
                   "🛡 ¡TE ENCONTRÁS UN ESCUDO EN EL PISO!\n"
                   "Robertito se lo pone encima y queda blindado\n"
                   "para aguantar los paravalanchas del JEFE FALOPINO...")
            self.heroe.armadura_rota = False
            if self.dificultad == 1:
                self.heroe.armadura = Armadura("Tapa de Olla Nivel 1", 3)
            elif self.dificultad == 2:
                self.heroe.armadura = Armadura("Tapa de Olla de Aluminio", 3)
            else:
                self.heroe.armadura = Armadura("Portón de Reja Blindado", 4)
                self.heroe.sprite_base = ruta_spr("nomo_dificil_armadura.png")
                self.heroe.sprite_roto = ruta_spr("nomo_dificil.png")

        if self.snd_item: self.snd_item.play()
        messagebox.showinfo("PRÓXIMA ONDA", msg)

        self.limpiar_arena()
        self.nuevo_enemigo()
        self.poner_musica()
        self.construir_arena()
        self.refrescar()

    def game_over(self):
        self.parar_fondo()
        mixer.music.stop()
        self.ventana.destroy()
        PantallaFin(gano=False, rondas=self.ronda, modo=self.modo)


# ---- pantalla de fin ----

class PantallaFin:
    def __init__(self, gano, rondas, modo="Historia"):
        self.root = tk.Tk()
        self.root.title("Fin del Juego")
        self.root.geometry("750x640")
        self.root.resizable(False, False)
        self.root.configure(bg="#0b0f19")

        self.gano = gano
        self.rondas = rondas
        self.modo = modo
        self.imgs = {}

        mixer.init()
        try:
            mixer.music.load(ruta_snd("victoria.mp3") if gano else ruta_snd("derrota.mp3"))
            mixer.music.play(-1)
        except:
            pass

        self.armar()
        self.root.mainloop()

    def ir_al_menu(self):
        mixer.music.stop()
        self.root.destroy()
        menu = MenuInicio()
        menu.root.mainloop()
        if menu.confirmado:
            juego = Arena(menu.dificultad, menu.modo)
            juego.ventana.mainloop()

    def reintentar(self):
        mixer.music.stop()
        self.root.destroy()
        juego = Arena(ultima_dif, ultimo_modo)
        juego.ventana.mainloop()

    def cargar_img(self, ruta, key, w, h):
        try:
            img = Image.open(ruta).resize((w, h), Image.Resampling.LANCZOS)
            self.imgs[key] = ImageTk.PhotoImage(img)
            return self.imgs[key]
        except:
            return None

    def armar(self):
        canvas = tk.Canvas(self.root, width=750, height=350, highlightthickness=0, bg="#000000")
        canvas.place(x=0, y=0)

        if self.gano:
            img = self.cargar_img(ruta_fin("imagen_victoria.png"), "bg", 750, 350)
            if img: canvas.create_image(375, 175, image=img)
            texto = (
                "¡Felicidades, ganaste! Tomá tu porción de píxeles con forma de milanesa, campeón del mundo. "
                "Lograste erradicar a la plaga de los enanos, rescataste el Sagrado Manjar entre dos panes y tu gnomo "
                "se consagró como el rey indiscutido del pasillo 3 de la villa medieval. Sos un héroe. Una leyenda viviente.\n\n"
                "But bajemos a la realidad un toque: estuviste tres horas seguidas mirando enanos en 16 bits cagarse a piñas "
                "por un bife de nalga engualichado. El olor a chivo que emana de tu pieza está alterando el ecosistema local "
                "y tu vieja ya está buscando el agua bendita porque piensa que te poseyó un duende.\n\n"
                "Gracias por jugar el juego, posta. Ahora hacenos un favor a todos: apagá la compu, abrí la ventana, salí a la vereda "
                "y TOCÁ PASTO, gordo compu. Urgente."
            )
            color = "#2ecc71"
        else:
            if self.modo == "Infinito":
                img = self.cargar_img(ruta_fin("imagen_fin_infinito.png"), "bg", 750, 350)
                if img: canvas.create_image(375, 175, image=img)
                rec = leer_record()
                if self.rondas > rec:
                    guardar_record(self.rondas)
                    msg_rec = f"✨ ¡NUEVO RÉCORD DEL PASILLO! ✨\nLlegaste hasta la Ronda {self.rondas}.\nSuperaste tu récord viejo de {rec} rondas."
                else:
                    msg_rec = f"Llegaste hasta la Ronda {self.rondas}.\nTu récord máximo actual es de Ronda {rec}."
                texto = f"💀 FIN DEL MODO INFINITO 💀\n\n{msg_rec}\n\n¿Vas a dejar que la mafia se quede con los récords del barrio o vas a intentar de vuelta?"
                color = "#9b59b6"
            else:
                img = self.cargar_img(ruta_fin("imagen_derrota.png"), "bg", 750, 350)
                if img: canvas.create_image(375, 175, image=img)
                texto = (
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
                color = "#e74c3c"

        caja = tk.Text(self.root, bg="#111625", fg=color, font=("Courier", 10, "bold"),
                       bd=2, relief="solid", wrap="word", padx=12, pady=8)
        caja.place(x=20, y=365, width=710, height=180)
        caja.insert(tk.END, texto)
        caja.config(state="disabled")

        self.img_casa = self.cargar_img(ruta_spr("boton_casa.png"), "btn_casa", 55, 55)
        self.img_retry = self.cargar_img(ruta_spr("boton_restart.png"), "btn_retry", 140, 45)

        if self.img_casa:
            tk.Button(self.root, image=self.img_casa, bg="#0b0f19", bd=0,
                      activebackground="#0b0f19", command=self.ir_al_menu).place(x=250, y=565)
        else:
            tk.Button(self.root, text="CASA", font=("Arial", 11, "bold"),
                      command=self.ir_al_menu).place(x=250, y=565, width=80, height=40)

        if self.img_retry:
            tk.Button(self.root, image=self.img_retry, bg="#0b0f19", bd=0,
                      activebackground="#0b0f19", command=self.reintentar).place(x=380, y=570)
        else:
            tk.Button(self.root, text="REINTENTAR", font=("Arial", 11, "bold"),
                      command=self.reintentar).place(x=380, y=565, width=120, height=40)


# ---- pantalla de intro ----

class Intro:
    CARPETA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "intro")
    MS_FRAME = 77

    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        self.idx = 0
        self.frames = []
        self._refs = []
        self._blink = None
        self._after = None
        self.listo = False
        self.en_transicion = False

        self.canvas = tk.Canvas(root, width=ANCHO, height=ALTO,
                                highlightthickness=0, bd=0, bg="black")
        self.canvas.place(x=0, y=0)
        root.update()

        self._txt_carga = self.canvas.create_text(ANCHO//2, ALTO//2, text="Cargando intro...",
            font=("Courier", 14, "bold"), fill="#888888", anchor="center")
        root.update()

        for n in range(1, 66):
            ruta = os.path.join(self.CARPETA, f"fotograma{n:05d}.png")
            if not os.path.exists(ruta):
                ruta = os.path.join(self.CARPETA, f"fotograma{n:05d}.jpg")
            try:
                img = Image.open(ruta).resize((ANCHO, ALTO), Image.Resampling.LANCZOS)
                self.frames.append(ImageTk.PhotoImage(img))
            except:
                self.frames.append(None)

        self.canvas.delete(self._txt_carga)

        primer = next((f for f in self.frames if f), None)
        self._id_img = self.canvas.create_image(0, 0, anchor="nw", image=primer or "")
        if primer:
            self._refs = [primer]

        self._id_press = self.canvas.create_text(ANCHO//2, ALTO-50,
            text="▶   TOCÁ CUALQUIER TECLA PARA CONTINUAR   ◀",
            font=("Courier", 11, "bold"), fill="#ffffff", anchor="center", state="hidden")

        self.root.bind("<KeyPress>", self._input)
        self.canvas.bind("<Button-1>", self._input)
        self.root.after(50, self._arrancar_musica)

    def _arrancar_musica(self):
        try:
            mixer.init()
            mixer.music.load(ruta_snd("sonido_intro.mp3"))
            mixer.music.set_volume(0.8)
            mixer.music.play(0)
        except:
            pass
        self._reproducir()

    def _reproducir(self):
        if self.idx >= len(self.frames):
            self.listo = True
            self._parpadear()
            return
        ph = self.frames[self.idx]
        if ph:
            self.canvas.itemconfig(self._id_img, image=ph)
            self._refs = [ph]
        self.idx += 1
        self._after = self.root.after(self.MS_FRAME, self._reproducir)

    def _parpadear(self, on=True):
        try:
            self.canvas.itemconfig(self._id_press, state="normal",
                                   fill="#ffffff" if on else "#777777")
        except tk.TclError:
            return
        self._blink = self.root.after(500, lambda: self._parpadear(not on))

    def _input(self, event=None):
        if self.en_transicion:
            return
        if not self.listo:
            if self._after:
                self.root.after_cancel(self._after)
                self._after = None
            ph = next((f for f in reversed(self.frames) if f), None)
            if ph:
                self.canvas.itemconfig(self._id_img, image=ph)
                self._refs = [ph]
            self.listo = True
            self._parpadear()
            return
        self.en_transicion = True
        if self._blink:
            self.root.after_cancel(self._blink)
            self._blink = None
        self.root.unbind("<KeyPress>")
        self.canvas.unbind("<Button-1>")
        self._fade(0)

    def _fade(self, step=0):
        alphas = [0, 30, 60, 90, 120, 150, 180, 210, 230, 245, 255]
        if step <= 10:
            a = alphas[min(step, len(alphas)-1)]
            overlay = Image.new("RGBA", (ANCHO, ALTO), (0, 0, 0, a))
            ph = ImageTk.PhotoImage(overlay)
            self._refs.append(ph)
            if not hasattr(self, '_id_overlay'):
                self._id_overlay = self.canvas.create_image(0, 0, anchor="nw", image=ph)
            else:
                self.canvas.itemconfig(self._id_overlay, image=ph)
            self.root.after(25, lambda: self._fade(step + 1))
        else:
            try: mixer.music.stop()
            except: pass
            self.root.configure(bg="black")
            try: self.canvas.destroy()
            except tk.TclError: pass
            self.root.update()
            self.frames.clear()
            self.callback()


# ---- main ----

def main():
    root = tk.Tk()
    root.title("Gnomos vs Enanos")
    root.geometry(f"{ANCHO}x{ALTO}")
    root.resizable(False, False)
    root.configure(bg="black")

    termino = [False]

    def fin_intro():
        termino[0] = True
        root.destroy()

    Intro(root, fin_intro)
    root.mainloop()

    if not termino[0]:
        return

    menu = MenuInicio()
    menu.root.mainloop()

    if menu.confirmado:
        juego = Arena(menu.dificultad, menu.modo)
        juego.ventana.mainloop()


if __name__ == "__main__":
    main()