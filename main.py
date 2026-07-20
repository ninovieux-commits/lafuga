"""
La Fuga – Version Kivy complète
Compatible Pydroid 3 / Build APK via buildozer
"""
from kivy.app import App
from kivy.uix.widget import Widget
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.image import Image
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.slider import Slider
from kivy.uix.textinput import TextInput
from kivy.graphics import Color, Rectangle, Ellipse, Line, Mesh, RoundedRectangle
from kivy.core.window import Window
from kivy.core.text import Label as CoreLabel
from kivy.core.audio import SoundLoader
from kivy.clock import Clock
from kivy.animation import Animation
from kivy.properties import NumericProperty
import os
import datetime
import re
import json
import threading
import urllib.request
import urllib.error

# ── Constantes ───────────────────────────────────────────────────────────────

COLS, ROWS = 7, 8
EXT_ROWS   = 10
RALLY      = frozenset({2, 3, 4})

# ── Échelle adaptative ───────────────────────────────────────────────────────
# Référence : Samsung Galaxy A06 = 720 px de large. Tout est calibré pour cet
# écran. Sur un écran plus petit/grand, on multiplie les tailles par un facteur
# proportionnel pour que l'affichage soit identique (juste mis à l'échelle).
REF_WIDTH = 720.0

# Coefficient global de confort pour TOUTES les polices de l'app.
# 1.0 = taille de référence calibrée A06. Augmenter pour grossir partout.
FONT_BOOST = 1.70

# Durée (en secondes) de l'animation de glissement des pièces.
# 0 = instantané (pas d'animation). Réglable dans les réglages.
SLIDE_SPEED = 0.18

def _scale_factor():
    """Facteur d'échelle basé sur la largeur réelle de l'écran vs la référence A06."""
    try:
        w = float(Window.width)
        if w <= 0:
            return 1.0
        return w / REF_WIDTH
    except Exception:
        return 1.0

def S(value):
    """Met une taille (en px de référence A06) à l'échelle de l'écran courant."""
    return value * _scale_factor()

def SF(size_str):
    """Met une taille de police à l'échelle de l'écran, en PIXELS PURS.

    On n'utilise PAS l'unité 'sp' de Kivy car elle dépend de la densité (DPI)
    de l'écran : un même '15sp' apparaît plus gros sur un écran dense. Pour que
    le texte occupe TOUJOURS la même proportion de l'écran (comme les boutons),
    on convertit la taille de référence A06 en pixels et on la met à l'échelle
    par le facteur largeur_écran / 720.

    FONT_BOOST : coefficient global pour ajuster la taille de TOUTES les polices
    d'un coup (réglage de confort de lecture).
    """
    try:
        if isinstance(size_str, str):
            num = float(size_str.replace("sp", "").replace("dp", "").strip())
        else:
            num = float(size_str)
        # Taille en pixels purs (pas de 'sp'), proportionnelle à la largeur.
        return num * _scale_factor() * FONT_BOOST
    except Exception:
        return size_str

# ── Client en ligne ──────────────────────────────────────────────────────────
# URL du serveur. On stocke ça dans config.txt pour pouvoir la changer sans
# recompiler. Par défaut on pointe sur localhost (utile pour tester en local).
SERVER_URL_DEFAULT = "http://127.0.0.1:5000"

# Liens de don pour le bouton "Soutenir les devs".
# À COMPLÉTER quand les comptes seront créés (laisser "" = bouton "bientôt").
# Exemple PayPal : "https://paypal.me/tonpseudo"
SUPPORT_LINKS = {
    "paypal":    "https://paypal.me/NinoVieuxFuga",
    "kofi":      "",   # ex: https://ko-fi.com/...
    "bmac":      "",   # ex: https://buymeacoffee.com/...
    "liberapay": "",   # ex: https://liberapay.com/...
}


class OnlineClient:
    """Client HTTP pour parler au serveur La Fuga.
    Stocke le token de session et le pseudo en mémoire.
    Les appels réseau se font en arrière-plan (thread) pour ne pas bloquer
    l'interface. Le résultat est renvoyé via un callback appelé sur le thread
    principal Kivy (via Clock.schedule_once)."""

    def __init__(self):
        self.server_url = SERVER_URL_DEFAULT
        self.token = None
        self.pseudo = None
        self.melo = 1500

    def is_logged_in(self):
        return self.token is not None and self.pseudo is not None

    def logout(self):
        self.token = None
        self.pseudo = None
        self.melo = 1500
        # Couper la connexion temps réel pour ne pas rester identifié au serveur
        try:
            if getattr(self, "sio", None) is not None and self.sio.connected:
                self.sio.disconnect()
        except Exception:
            pass

    def _post(self, path, payload, callback):
        """POST JSON en arrière-plan. callback(response_dict, error_str) sur main thread."""
        def worker():
            url = self.server_url.rstrip("/") + path
            data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url, data=data,
                headers={"Content-Type": "application/json"},
                method="POST")
            try:
                with urllib.request.urlopen(req, timeout=10) as resp:
                    body = resp.read().decode("utf-8")
                    result = json.loads(body) if body else {}
                    Clock.schedule_once(
                        lambda dt, r=result: callback(r, None), 0)
            except urllib.error.HTTPError as e:
                # Erreur HTTP : essayer de parser le JSON quand même
                try:
                    body = e.read().decode("utf-8")
                    result = json.loads(body) if body else {}
                    Clock.schedule_once(
                        lambda dt, r=result: callback(r, None), 0)
                except Exception:
                    Clock.schedule_once(
                        lambda dt, msg="Erreur serveur (%d)" % e.code:
                            callback(None, msg), 0)
            except urllib.error.URLError as e:
                Clock.schedule_once(
                    lambda dt, msg="Pas de connexion au serveur":
                        callback(None, msg), 0)
            except Exception as e:
                Clock.schedule_once(
                    lambda dt, msg="Erreur : %s" % str(e):
                        callback(None, msg), 0)
        t = threading.Thread(target=worker, daemon=True)
        t.start()

    def register(self, pseudo, password, email, callback):
        """callback(success: bool, msg: str)"""
        def on_response(result, err):
            if err:
                callback(False, err); return
            if result and result.get("ok"):
                self.token = result.get("token")
                self.pseudo = result.get("pseudo")
                self.melo = result.get("melo", 1500)
                save_online_session(self.token, self.pseudo, self.melo)
                callback(True, "Compte créé !")
            else:
                callback(False, (result or {}).get("error", "Erreur inconnue"))
        self._post("/register",
                   {"pseudo": pseudo, "password": password, "email": email or ""},
                   on_response)

    def login(self, pseudo, password, callback):
        """callback(success: bool, msg: str)"""
        def on_response(result, err):
            if err:
                callback(False, err); return
            if result and result.get("ok"):
                self.token = result.get("token")
                self.pseudo = result.get("pseudo")
                self.melo = result.get("melo", 1500)
                save_online_session(self.token, self.pseudo, self.melo)
                callback(True, "Connecté !")
            else:
                callback(False, (result or {}).get("error", "Erreur inconnue"))
        self._post("/login",
                   {"pseudo": pseudo, "password": password},
                   on_response)

    def auto_login_with_token(self, token, callback):
        """Tente une reconnexion avec un token sauvegardé."""
        def on_response(result, err):
            if err or not result or not result.get("ok"):
                callback(False); return
            self.token = token
            self.pseudo = result.get("pseudo")
            self.melo = result.get("melo", 1500)
            callback(True)
        self._post("/ping", {"token": token}, on_response)

    # ── Socket.IO (temps réel : matchmaking + parties) ──────────────────────
    def _ensure_sio(self):
        """Crée le client Socket.IO si pas déjà fait. Retourne l'instance ou None."""
        if getattr(self, "_sio", None) is not None:
            return self._sio
        try:
            import socketio as _sio_lib
        except Exception:
            self._sio = None
            return None
        self._sio = _sio_lib.Client(reconnection=True,
                                    reconnection_attempts=0,  # infini
                                    logger=False, engineio_logger=False)
        # Handlers : on relaie les événements serveur vers des callbacks
        # enregistrés (sur le thread Kivy via Clock).
        self._sio_handlers = {}

        def _relay(event):
            def handler(data=None):
                cb = self._sio_handlers.get(event)
                if cb:
                    Clock.schedule_once(lambda dt, d=data: cb(d or {}), 0)
            return handler

        for ev in ("auth_ok", "auth_erreur", "recherche_en_cours",
                   "partie_trouvee", "recherche_timeout",
                   "coup_adverse", "partie_terminee", "adversaire_deconnecte",
                   "chat_recu", "nulle_proposee", "melo_maj",
                   "adversaire_revenu", "reprise_partie", "etat_partie",
                   "adversaire_pret", "match_continue", "match_over",
                   "match_abandonne",
                   "defi_recu", "defi_envoye", "defi_echec", "defi_refuse",
                   "defi_annule"):
            self._sio.on(ev, _relay(ev))

        # CRUCIAL : Socket.IO se reconnecte tout seul après une coupure réseau
        # (fréquent sur mobile). À CHAQUE (re)connexion, on doit ré-envoyer 'auth'
        # pour que le serveur réassocie ce nouveau socket à notre compte et à
        # notre partie en cours, sinon l'adversaire nous voit "déconnecté" et nos
        # coups se perdent.
        @self._sio.event
        def connect():
            try:
                if self.token:
                    self._sio.emit("auth", {"token": self.token})
            except Exception:
                pass
        return self._sio

    def on_event(self, event, callback):
        """Enregistre un callback pour un événement serveur (appelé sur le
        thread Kivy). callback(data_dict)."""
        self._ensure_sio()
        if getattr(self, "_sio_handlers", None) is not None:
            self._sio_handlers[event] = callback

    def sio_connect(self, on_ready=None):
        """Se connecte au serveur en Socket.IO (en thread) puis s'authentifie
        avec le token. on_ready(success: bool, msg: str) sur le thread Kivy."""
        sio = self._ensure_sio()
        if sio is None:
            if on_ready:
                on_ready(False, "Module réseau indisponible")
            return

        def worker():
            try:
                if not sio.connected:
                    # On laisse python-socketio négocier automatiquement le
                    # transport (polling puis montée en websocket). Forcer un seul
                    # transport échouait sur certains environnements.
                    sio.connect(self.server_url, wait_timeout=15)
                # S'authentifier
                sio.emit("auth", {"token": self.token})
                if on_ready:
                    Clock.schedule_once(lambda dt: on_ready(True, ""), 0)
            except Exception as e:
                # Journaliser l'erreur complète pour diagnostic
                try:
                    import traceback, os
                    p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                     "sio_error.txt")
                    with open(p, "w", encoding="utf-8") as f:
                        f.write("URL : %s\n\n" % self.server_url)
                        traceback.print_exc(file=f)
                except Exception:
                    pass
                if on_ready:
                    Clock.schedule_once(
                        lambda dt, m=str(e): on_ready(False, m), 0)
        threading.Thread(target=worker, daemon=True).start()

    def sio_emit(self, event, data=None):
        """Envoie un événement au serveur (thread-safe via thread)."""
        sio = getattr(self, "_sio", None)
        if sio is None:
            return
        def worker():
            try:
                sio.emit(event, data or {})
            except Exception:
                pass
        threading.Thread(target=worker, daemon=True).start()

    def sio_connected(self):
        sio = getattr(self, "_sio", None)
        return bool(sio is not None and sio.connected)

    def chercher_partie(self, objectif, cadence):
        # Random Fuga : on transmet l'état de l'interrupteur. Le serveur n'apparie
        # un joueur random qu'avec un autre joueur random (matchmaking standard
        # inchangé) et génère un code commun.
        self.sio_emit("chercher_partie", {"objectif": objectif,
                                          "cadence": cadence,
                                          "random": RANDOM_MODE})

    def annuler_recherche(self):
        self.sio_emit("annuler_recherche", {})

    # ── Recherche de joueurs & favoris (HTTP) ───────────────────────────────
    def search_user(self, pseudo, callback):
        """Cherche un joueur par pseudo. callback(result_dict_or_None, error)."""
        if not self.is_logged_in():
            callback(None, "Non connecté"); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result, None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/search_user", {"token": self.token, "pseudo": pseudo}, on_resp)

    def add_favorite(self, pseudo, callback=None):
        if not self.is_logged_in():
            if callback: callback(False, "Non connecté")
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/add_favorite", {"token": self.token, "pseudo": pseudo}, on_resp)

    def remove_favorite(self, pseudo, callback=None):
        if not self.is_logged_in():
            if callback: callback(False, "Non connecté")
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/remove_favorite", {"token": self.token, "pseudo": pseudo}, on_resp)

    def list_favorites(self, callback):
        """callback(favorites_list_or_None, error)."""
        if not self.is_logged_in():
            callback(None, "Non connecté"); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result.get("favorites", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/list_favorites", {"token": self.token}, on_resp)

    # ── Défi rapide (temps réel) ────────────────────────────────────────────
    def defier(self, pseudo_cible, objectif, cadence):
        # Random Fuga : le défi porte l'état de l'interrupteur du défieur.
        self.sio_emit("defier", {"pseudo_cible": pseudo_cible,
                                 "objectif": objectif, "cadence": cadence,
                                 "random": RANDOM_MODE})

    def annuler_defi(self, defi_id):
        self.sio_emit("annuler_defi", {"defi_id": defi_id})

    def repondre_defi(self, defi_id, accepte):
        self.sio_emit("repondre_defi", {"defi_id": defi_id, "accepte": accepte})

    # ── Correspondance (HTTP, asynchrone) ───────────────────────────────────
    def corr_list(self, callback):
        """Liste les parties de correspondance actives. callback(games, err)."""
        if not self.is_logged_in():
            callback(None, "Non connecté"); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result.get("games", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/corr_list", {"token": self.token}, on_resp)

    def corr_defier(self, pseudo, objectif, callback):
        """Défie un pote par correspondance. callback(result_dict, err)."""
        if not self.is_logged_in():
            callback(None, "Non connecté"); return
        def on_resp(result, err):
            if err: callback(None, err); return
            callback(result, None)
        self._post("/corr_defier",
                   {"token": self.token, "pseudo": pseudo, "objectif": objectif,
                    "random": RANDOM_MODE},
                   on_resp)

    def corr_repondre(self, game_id, accepte, callback=None):
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/corr_repondre",
                   {"token": self.token, "game_id": game_id, "accepte": accepte},
                   on_resp)

    def corr_jouer(self, game_id, notation, methode=None, callback=None):
        payload = {"token": self.token, "game_id": game_id, "notation": notation}
        if methode:
            payload["methode"] = methode
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/corr_jouer", payload, on_resp)

    def corr_abandon(self, game_id, callback=None):
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/corr_abandon",
                   {"token": self.token, "game_id": game_id}, on_resp)

    def corr_close(self, game_id, callback=None):
        """Masque (ferme) une partie de correspondance terminée sur le slot."""
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")), err)
        self._post("/corr_close",
                   {"token": self.token, "game_id": game_id}, on_resp)

    def corr_proposer_nulle(self, game_id, callback=None):
        """Propose une nulle en correspondance (l'adversaire verra un popup)."""
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/corr_proposer_nulle",
                   {"token": self.token, "game_id": game_id}, on_resp)

    def corr_repondre_nulle(self, game_id, accepte, callback=None):
        """Répond à une proposition de nulle en correspondance.
        callback(result_dict, err), result['nulle'] indique si la partie est nulle."""
        def on_resp(result, err):
            if callback:
                callback(result, err)
        self._post("/corr_repondre_nulle",
                   {"token": self.token, "game_id": game_id, "accepte": accepte},
                   on_resp)

    def corr_chat_send(self, game_id, texte, callback=None):
        """Envoie un message dans le chat d'une partie de correspondance."""
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")), err)
        self._post("/corr_chat_send",
                   {"token": self.token, "game_id": game_id, "texte": texte},
                   on_resp)

    def corr_chat_list(self, game_id, callback):
        """Récupère les messages du chat de correspondance. callback(msgs, err)."""
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"):
                callback(result.get("messages", []), None)
            else:
                callback(None, (result or {}).get("error", "Erreur"))
        self._post("/corr_chat_list",
                   {"token": self.token, "game_id": game_id}, on_resp)

    # ── Sauvegarde des parties liées au compte (HTTP) ───────────────────────
    def save_game_to_account(self, game_data, callback=None):
        """Envoie une partie au serveur pour la lier au compte. game_data doit
        contenir game_uid, nmc_text, joueur1, joueur2, resultat, methode,
        cadence, objectif. Silencieux par défaut (callback optionnel)."""
        if not self.is_logged_in():
            if callback: callback(False, "Non connecté")
            return
        payload = dict(game_data)
        payload["token"] = self.token
        def on_response(result, err):
            if callback:
                if err: callback(False, err)
                else: callback(bool(result and result.get("ok")), "")
        self._post("/save_game", payload, on_response)

    def list_account_games(self, callback):
        """Récupère la liste des parties du compte.
        callback(games_list_or_None, error_str)."""
        if not self.is_logged_in():
            callback(None, "Non connecté"); return
        def on_response(result, err):
            if err:
                callback(None, err); return
            if result and result.get("ok"):
                callback(result.get("games", []), None)
            else:
                callback(None, (result or {}).get("error", "Erreur"))
        self._post("/list_games", {"token": self.token}, on_response)

    def get_account_game(self, game_uid, callback):
        """Récupère le contenu .nmc complet d'une partie du compte.
        callback(nmc_text_or_None, error_str)."""
        if not self.is_logged_in():
            callback(None, "Non connecté"); return
        def on_response(result, err):
            if err:
                callback(None, err); return
            if result and result.get("ok"):
                callback(result.get("nmc_text"), None)
            else:
                callback(None, (result or {}).get("error", "Erreur"))
        self._post("/get_game", {"token": self.token, "game_uid": game_uid},
                   on_response)


# Instance globale (utilisée par les écrans)
ONLINE = OnlineClient()


def save_online_session(token, pseudo, melo):
    """Sauvegarde la session dans config.txt pour reconnexion auto."""
    try:
        cfg = load_config()
        cfg["online_token"] = token or ""
        cfg["online_pseudo"] = pseudo or ""
        cfg["online_melo"] = str(melo or 1500)
        save_config(cfg)
    except Exception:
        pass


def clear_online_session():
    """Supprime VRAIMENT les infos de connexion du config.txt. On réécrit le
    fichier en omettant les clés online (save_config ne peut pas supprimer une
    clé car il fusionne avec l'existant, d'où l'écriture directe ici)."""
    try:
        cfg = load_config()
        for k in ("online_token", "online_pseudo", "online_melo"):
            cfg.pop(k, None)
        with open(_config_path(), "w", encoding="utf-8") as f:
            for k, v in cfg.items():
                f.write(f"{k}={v}\n")
    except Exception:
        pass


# ── Système de thèmes ────────────────────────────────────────────────────────
# Chaque thème définit : clair (camp Blanc), foncé (camp Noir), leurs versions
# "dim" (bandeau inactif), le gris du plateau, le gris du menu, et la grille.
# Les pièces restent toujours blanc crème / noir.

THEMES = {
    "original": {
        "clair":     (1.0, 0.55, 0.0, 1),     # orange
        "fonce":     (0.0, 0.50, 1.0, 1),     # bleu
        "clair_dim": (0.45, 0.22, 0.0, 1),
        "fonce_dim": (0.0, 0.22, 0.45, 1),
        "board":     (0.55, 0.55, 0.55, 1),
        "menu":      (0.78, 0.78, 0.78, 1),
        "grid":      (0.44, 0.44, 0.44, 1),
    },
    "foret": {
        "clair":     (0.45, 0.78, 0.30, 1),   # vert clair
        "fonce":     (0.13, 0.40, 0.13, 1),   # vert foncé
        "clair_dim": (0.22, 0.38, 0.15, 1),
        "fonce_dim": (0.06, 0.20, 0.06, 1),
        "board":     (0.42, 0.50, 0.40, 1),   # vert-gris
        "menu":      (0.62, 0.70, 0.60, 1),
        "grid":      (0.32, 0.40, 0.30, 1),
    },
    "ocean": {
        "clair":     (0.35, 0.75, 0.95, 1),   # bleu clair
        "fonce":     (0.05, 0.25, 0.55, 1),   # bleu foncé
        "clair_dim": (0.17, 0.37, 0.47, 1),
        "fonce_dim": (0.02, 0.12, 0.27, 1),
        "board":     (0.40, 0.48, 0.55, 1),   # bleu-gris
        "menu":      (0.60, 0.68, 0.75, 1),
        "grid":      (0.30, 0.38, 0.45, 1),
    },
    "volcan": {
        "clair":     (1.0, 0.65, 0.25, 1),    # orange clair
        "fonce":     (0.65, 0.20, 0.0, 1),    # orange-rouge foncé
        "clair_dim": (0.48, 0.30, 0.12, 1),
        "fonce_dim": (0.32, 0.10, 0.0, 1),
        "board":     (0.52, 0.46, 0.42, 1),   # gris-orangé
        "menu":      (0.74, 0.66, 0.60, 1),
        "grid":      (0.42, 0.36, 0.32, 1),
    },
    "hemo": {
        "clair":     (0.95, 0.35, 0.35, 1),   # rouge clair
        "fonce":     (0.50, 0.05, 0.08, 1),   # rouge foncé
        "clair_dim": (0.47, 0.17, 0.17, 1),
        "fonce_dim": (0.25, 0.02, 0.04, 1),
        "board":     (0.52, 0.44, 0.44, 1),   # gris-rougeâtre
        "menu":      (0.74, 0.62, 0.62, 1),
        "grid":      (0.42, 0.34, 0.34, 1),
    },
    "spatial": {
        "clair":     (0.70, 0.45, 0.95, 1),   # violet clair
        "fonce":     (0.30, 0.10, 0.50, 1),   # violet foncé
        "clair_dim": (0.35, 0.22, 0.47, 1),
        "fonce_dim": (0.15, 0.05, 0.25, 1),
        "board":     (0.48, 0.44, 0.54, 1),   # gris-violacé
        "menu":      (0.68, 0.62, 0.74, 1),
        "grid":      (0.38, 0.34, 0.44, 1),
    },
    "imperial": {
        "clair":     (0.85, 0.70, 0.30, 1),   # doré
        "fonce":     (0.75, 0.75, 0.80, 1),   # argenté
        "clair_dim": (0.42, 0.35, 0.15, 1),
        "fonce_dim": (0.37, 0.37, 0.40, 1),
        "board":     (0.45, 0.16, 0.24, 1),   # pourpre (rouge foncé bordeaux)
        "menu":      (0.58, 0.24, 0.32, 1),
        "grid":      (0.34, 0.10, 0.17, 1),
    },
    "royal": {
        "clair":     (0.85, 0.70, 0.30, 1),   # doré
        "fonce":     (0.75, 0.75, 0.80, 1),   # argenté
        "clair_dim": (0.42, 0.35, 0.15, 1),
        "fonce_dim": (0.37, 0.37, 0.40, 1),
        "board":     (0.20, 0.28, 0.55, 1),   # bleu roi
        "menu":      (0.35, 0.42, 0.68, 1),
        "grid":      (0.14, 0.20, 0.42, 1),
    },
    "terre": {
        "clair":     (0.80, 0.62, 0.42, 1),   # beige/terre clair
        "fonce":     (0.40, 0.26, 0.13, 1),   # marron foncé
        "clair_dim": (0.40, 0.31, 0.21, 1),
        "fonce_dim": (0.20, 0.13, 0.06, 1),
        "board":     (0.52, 0.44, 0.36, 1),   # brun-gris
        "menu":      (0.68, 0.58, 0.48, 1),
        "grid":      (0.40, 0.32, 0.24, 1),
    },
    "bonbon": {
        "clair":     (1.0, 0.72, 0.85, 1),    # rose clair
        "fonce":     (0.85, 0.22, 0.55, 1),   # rose vif/fuchsia
        "clair_dim": (0.50, 0.36, 0.43, 1),
        "fonce_dim": (0.42, 0.11, 0.27, 1),
        "board":     (0.60, 0.48, 0.55, 1),   # gris-rosé
        "menu":      (0.82, 0.68, 0.75, 1),
        "grid":      (0.48, 0.36, 0.43, 1),
    },
    "arcenciel": {
        # Festif multicolore : décor bleu ciel pastel, pièces et boutons
        # multicolores (gérés à part). clair/fonce = repli des accents.
        "clair":     (0.95, 0.55, 0.30, 1),
        "fonce":     (0.30, 0.50, 0.85, 1),
        "clair_dim": (0.60, 0.45, 0.40, 1),
        "fonce_dim": (0.30, 0.40, 0.55, 1),
        "board":     (0.72, 0.85, 0.95, 1),   # plateau bleu ciel pastel
        "menu":      (0.78, 0.90, 0.98, 1),   # fond menu bleu ciel pastel
        "grid":      (0.55, 0.70, 0.85, 1),   # quadrillage bleu ciel plus soutenu
    },
    "etoile": {
        "clair":     (1.0, 0.85, 0.20, 1),    # jaune vif
        "fonce":     (0.75, 0.60, 0.08, 1),   # jaune-or foncé
        "clair_dim": (0.45, 0.40, 0.12, 1),
        "fonce_dim": (0.30, 0.24, 0.04, 1),
        "board":     (0.06, 0.06, 0.10, 1),   # fond noir bleuté (ciel nocturne)
        "menu":      (0.10, 0.10, 0.16, 1),
        "grid":      (0.25, 0.23, 0.10, 1),   # quadrillage doré sombre
    },
    "medieval": {
        # Thème à images personnalisées : pièces + fonds en pierre (themebataille/).
        "clair":     (1.0, 0.55, 0.0, 1),
        "fonce":     (0.0, 0.50, 1.0, 1),
        "clair_dim": (0.45, 0.22, 0.0, 1),
        "fonce_dim": (0.0, 0.22, 0.45, 1),
        "board":     (0.42, 0.42, 0.44, 1),   # gris pierre (repli si image absente)
        "menu":      (0.42, 0.42, 0.44, 1),
        "grid":      (0.30, 0.30, 0.32, 1),
    },
    "fleur": {
        # Thème à images personnalisées (themefleurs/) : pièces + fonds.
        # Décor en tons roses/rouges pastel ; lignes du plateau en noir.
        "clair":     (0.95, 0.40, 0.45, 1),   # rouge (bouton)
        "fonce":     (0.95, 0.70, 0.82, 1),   # rose pastel (bouton)
        "clair_dim": (0.62, 0.32, 0.35, 1),
        "fonce_dim": (0.65, 0.52, 0.58, 1),
        "board":     (0.98, 0.88, 0.90, 1),   # rose très clair (repli si image absente)
        "menu":      (0.99, 0.92, 0.94, 1),   # rose pâle
        "grid":      (0.0, 0.0, 0.0, 1),      # lignes du plateau en noir
    },
    "insectes": {
        # Thème à images personnalisées (themeinsectes/) : pièces + fonds.
        # Soldat et Garde partagent la même image (carree...) ; une croix
        # dessinée derrière les distingue (+ Soldat / × Garde).
        # Décor en tons verts (le plateau image est vert).
        "clair":     (0.45, 0.70, 0.30, 1),   # vert clair (bouton)
        "fonce":     (0.20, 0.45, 0.18, 1),   # vert foncé (bouton)
        "clair_dim": (0.30, 0.46, 0.20, 1),
        "fonce_dim": (0.14, 0.30, 0.12, 1),
        "board":     (0.85, 0.92, 0.80, 1),   # vert très clair (repli si image absente)
        "menu":      (0.90, 0.95, 0.86, 1),   # vert pâle
        "grid":      (0.0, 0.0, 0.0, 1),      # lignes du plateau en noir
    },
}

THEME_ORDER = ["original", "foret", "ocean", "volcan", "hemo",
               "spatial", "imperial", "royal", "terre", "bonbon",
               "arcenciel", "etoile", "medieval", "fleur", "insectes"]
THEME_LABELS = {
    "original": "Original", "foret": "Forêt", "ocean": "Océan",
    "volcan": "Volcan", "hemo": "Hémo", "spatial": "Spatial",
    "imperial": "Impérial", "royal": "Royal",
    "terre": "Terre", "bonbon": "Bonbon",
    "arcenciel": "Arc-en-ciel", "etoile": "Étoile", "medieval": "Médiéval",
    "fleur": "Fleur", "insectes": "Insectes",
}

CURRENT_THEME = "original"

# Mode Random Fuga (variante Fischer-random) : interrupteur global. Quand il est
# allumé, chaque nouvelle partie démarre sur une position aléatoire parmi 3500.
# Sauvegardé dans config.txt (clé "random_mode").
RANDOM_MODE = False

# Couleurs dynamiques (mises à jour par apply_theme)
COL_BG_MENU    = THEMES["original"]["menu"]
COL_BG_BOARD   = THEMES["original"]["board"]
COL_GRID       = THEMES["original"]["grid"]
COL_ORANGE     = THEMES["original"]["clair"]
COL_BLUE       = THEMES["original"]["fonce"]
COL_ORANGE_DIM = THEMES["original"]["clair_dim"]
COL_BLUE_DIM   = THEMES["original"]["fonce_dim"]
COL_WHITE_PC   = (0.96, 0.94, 0.86, 1)
COL_BLACK_PC   = (0.07, 0.07, 0.13, 1)
COL_SEL_MAIN   = (1.0, 1.0, 0.0, 1)
COL_SEL_GROUP  = (1.0, 0.4, 1.0, 1)
COL_IMMOBILE   = (1.0, 0.2, 0.2, 1)
COL_BTN_GREY   = (0.35, 0.35, 0.35, 1)


def apply_theme(name):
    """Met à jour les couleurs globales selon le thème choisi."""
    global CURRENT_THEME, COL_BG_MENU, COL_BG_BOARD, COL_GRID
    global COL_ORANGE, COL_BLUE, COL_ORANGE_DIM, COL_BLUE_DIM
    if name not in THEMES:
        name = "original"
    CURRENT_THEME = name
    t = THEMES[name]
    COL_BG_MENU    = t["menu"]
    COL_BG_BOARD   = t["board"]
    COL_GRID       = t["grid"]
    COL_ORANGE     = t["clair"]
    COL_BLUE       = t["fonce"]
    COL_ORANGE_DIM = t["clair_dim"]
    COL_BLUE_DIM   = t["fonce_dim"]


SCRIPT_FONT = "Comic Sans MS"   # fallback Kivy si absent


# ── Notation .nmc ────────────────────────────────────────────────────────────

NOTES = ["Do", "Ré", "Mi", "Fa", "Sol", "La", "Si"]

def cell_to_notation(c, r):
    """(col, row) → 'Fa5' (row 0 = 1, row 7 = 8). Renvoie None pour case ralliement."""
    if not (0 <= c < COLS and 0 <= r < ROWS): return None
    return f"{NOTES[c]}{r + 1}"

def notation_to_cell(notation):
    """'Fa5' → (col, row). Renvoie None si invalide."""
    if not notation: return None
    # Trouver la note (1 à 3 caractères, ex: Do, Ré, Mi, Fa, Sol, La, Si)
    for i, note in enumerate(NOTES):
        if notation.startswith(note):
            rest = notation[len(note):]
            try:
                num = int(rest)
                if 1 <= num <= 8:
                    return (i, num - 1)
            except ValueError:
                pass
            return None
    return None

def parse_cells_concat(s):
    """Découpe une chaîne 'Do1Mi3Sol5' en liste [(col,row), ...]."""
    cells = []
    i = 0
    while i < len(s):
        # Trouver la note qui matche
        matched = False
        for note in NOTES:
            if s[i:i+len(note)] == note:
                # Lire le chiffre qui suit
                j = i + len(note)
                k = j
                while k < len(s) and s[k].isdigit():
                    k += 1
                if k > j:
                    cell = notation_to_cell(s[i:k])
                    if cell is None: return None
                    cells.append(cell)
                    i = k
                    matched = True
                    break
        if not matched: return None
    return cells


# ── Stockage des parties .nmc ────────────────────────────────────────────────

def get_parties_dir():
    """Renvoie le chemin du dossier où stocker les parties (.nmc)."""
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, "parties")
    if not os.path.exists(path):
        try:
            os.makedirs(path)
        except Exception:
            pass
    return path


def _config_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "config.txt")

def load_config():
    """Charge la config. Renvoie un dict avec toutes les clés trouvées."""
    cfg = {"theme": "original", "volume": 1.0}
    try:
        with open(_config_path(), "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if "=" in line:
                    k, v = line.split("=", 1)
                    k = k.strip(); v = v.strip()
                    if k == "theme":
                        cfg["theme"] = v
                    elif k == "volume":
                        try: cfg["volume"] = max(0.0, min(1.0, float(v)))
                        except ValueError: pass
                    else:
                        cfg[k] = v
    except Exception:
        pass
    return cfg

def save_config(*args, **kw):
    """Sauvegarde la config. Deux modes d'appel :
       - save_config(dict)            : remplace toutes les clés du dict fourni
       - save_config(theme=..., volume=..., ...) : met à jour les clés données
    """
    cfg = load_config()
    if args and isinstance(args[0], dict):
        cfg.update(args[0])
    else:
        if kw.get("theme") is not None:  cfg["theme"]  = kw["theme"]
        if kw.get("volume") is not None: cfg["volume"] = kw["volume"]
        # Autres clés génériques fournies en kwargs
        for k, v in kw.items():
            if k in ("theme", "volume"): continue
            if v is None: continue
            cfg[k] = v
    try:
        with open(_config_path(), "w", encoding="utf-8") as f:
            for k, v in cfg.items():
                f.write(f"{k}={v}\n")
    except Exception:
        pass

# ── Random Fuga (variante Fischer-random) ────────────────────────────────────
# Une position est codée [symbole][Position]-[Disposition], ex. ".03-09" ou
# "/18-54".  symbole : "." = rotation 180° (colonnes inversées do↔si ré↔la
# mi↔sol fa↔fa) ; "/" = réflexion horizontale (colonnes gardées, Héritiers face
# à face).  Position 1..25 = (Héritier × Chevalier) sur [ré,mi,fa,sol,la].
# Disposition 1..70 = la D-ième combinaison de 4 Gardes parmi 8 carrées (lues en
# U : do2, do1, [ré/mi/fa/sol/la sauf Héritier], si1, si2).  Total = 2×25×70.
import itertools as _itertools

# Les 70 combinaisons de 4 Gardes parmi 8 carrées, précalculées une seule fois
# (évite de reconstruire la liste à chaque tirage).
_RF_COMBOS = list(_itertools.combinations(range(8), 4))

def rf_parse_code(code):
    """Analyse un code Random Fuga. Renvoie (sym, P, D) ou None si invalide."""
    try:
        code = (code or "").strip()
        sym = code[0]
        if sym not in (".", "/"):
            return None
        ps, ds = code[1:].split("-")
        P = int(ps); D = int(ds)
        if not (1 <= P <= 25 and 1 <= D <= 70):
            return None
        return (sym, P, D)
    except Exception:
        return None

def rf_random_code():
    """Tire un code aléatoire parmi les 2×25×70 = 3500 positions."""
    import random as _r
    return "%s%02d-%02d" % (_r.choice([".", "/"]), _r.randint(1, 25),
                            _r.randint(1, 70))

def rf_build_board(code):
    """Construit le plateau (board[col][row], 7×8) à partir d'un code Random
    Fuga. Renvoie le board, ou None si le code est invalide. Mêmes pièces que la
    position standard (1 Héritier, 1 Chevalier, 5 Nurses, 4 Gardes, 4 Soldats par
    camp), simplement réarrangées."""
    parsed = rf_parse_code(code)
    if not parsed:
        return None
    sym, P, D = parsed
    board = [[None for _ in range(ROWS)] for _ in range(COLS)]
    iH = (P - 1) // 5       # colonne Héritier : ré..la = 1..5
    iC = (P - 1) % 5        # colonne Chevalier : ré..la = 1..5
    col_H = 1 + iH
    col_C = 1 + iC
    # Camp BLANC (lignes 0,1,2)
    board[col_H][0] = {"type": "Héritier",  "camp": "Blanc"}
    board[col_C][2] = {"type": "Chevalier", "camp": "Blanc"}
    for c in range(1, 6):
        board[c][1] = {"type": "Nurse", "camp": "Blanc"}
    # 8 emplacements de carrées, ordre en U
    milieu = [c for c in range(1, 6) if c != col_H]   # 4 colonnes, gauche→droite
    slots = [(0, 1), (0, 0)] + [(c, 0) for c in milieu] + [(6, 0), (6, 1)]
    garde_idx = _RF_COMBOS[D - 1]
    for i, (c, r) in enumerate(slots):
        board[c][r] = {"type": "Garde" if i in garde_idx else "Soldat",
                       "camp": "Blanc"}
    # Camp NOIR : appliquer la symétrie aux pièces blanches
    for c in range(COLS):
        for r in range(3):
            p = board[c][r]
            if not p:
                continue
            if sym == "/":
                nc, nr = c, 7 - r          # réflexion : colonne gardée
            else:
                nc, nr = 6 - c, 7 - r      # rotation 180° : colonne inversée
            board[nc][nr] = {"type": p["type"], "camp": "Noir"}
    return board


def format_nmc_moves(history):
    """Formate la liste des coups en chaîne nmc : '1.Do1-Do2/Do8-Do7  2....'."""
    parts = []
    i = 0
    turn_num = 1
    while i < len(history):
        blanc = history[i][0] if i < len(history) else ""
        noir  = history[i+1][0] if i + 1 < len(history) else ""
        s = f"{turn_num}.{blanc}"
        if noir:
            s += f"/{noir}"
        parts.append(s)
        i += 2
        turn_num += 1
    return "  ".join(parts)

def make_nmc_content(meta, history):
    """Génère le contenu d'un fichier .nmc avec en-tête style PGN.
    meta = dict avec date, player1, player2, objectif, cadence,
           result_symbol ('1-0' / '0-1' / '½-½'), method, points."""
    header = (
        f"[Date \"{meta['date']}\"]\n"
        f"[Joueur1 \"{meta['player1']}\"]\n"
        f"[Joueur2 \"{meta['player2']}\"]\n"
        f"[Blanc \"{meta.get('blanc', meta['player1'])}\"]\n"
        f"[Objectif \"{meta['objectif']}\"]\n"
        f"[Cadence \"{meta['cadence']}\"]\n"
        f"[Resultat \"{meta['result']}\"]\n"
        f"[Methode \"{meta['method']}\"]\n"
        f"[Points \"{meta['points']}\"]\n"
    )
    # Random Fuga : si la partie est partie d'une position aléatoire, on stocke
    # son code pour pouvoir reconstruire la position de départ à la relecture.
    if meta.get("random"):
        header += f"[Random \"{meta['random']}\"]\n"
    header += "\n"
    return header + format_nmc_moves(history)

def list_local_parties():
    """Renvoie la liste des fichiers .nmc dans le dossier parties, triés du plus récent."""
    path = get_parties_dir()
    try:
        files = [f for f in os.listdir(path) if f.endswith(".nmc")]
        files.sort(reverse=True)
        return [os.path.join(path, f) for f in files]
    except Exception:
        return []


def erase_local_parties():
    """Efface tous les fichiers .nmc locaux. Appelé à la connexion : le jeu
    est pensé pour être connecté, l'historique vient alors du compte."""
    path = get_parties_dir()
    try:
        for f in os.listdir(path):
            if f.endswith(".nmc"):
                try:
                    os.remove(os.path.join(path, f))
                except Exception:
                    pass
    except Exception:
        pass

def parse_nmc_file(filepath):
    """Lit un fichier .nmc et renvoie (meta, moves_text). Renvoie (None, None) si invalide."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception:
        return None, None
    return parse_nmc_content(content)

def parse_nmc_content(content):
    """Parse le contenu d'un fichier nmc : en-tête + coups. Renvoie (meta, moves_text)."""
    meta = {}
    lines = content.split("\n")
    move_lines = []
    in_header = True
    for line in lines:
        line = line.rstrip()
        if in_header and line.startswith("[") and line.endswith("]"):
            m = re.match(r'\[(\w+)\s+"(.*)"\]', line)
            if m:
                meta[m.group(1).lower()] = m.group(2)
        elif line.strip() == "":
            if in_header:
                in_header = False
        else:
            in_header = False
            move_lines.append(line)
    moves_text = " ".join(move_lines).strip()
    return meta, moves_text


# ── Gestionnaire de sons ─────────────────────────────────────────────────────

# Notes en minuscules pour les noms de fichiers (do, re, mi, fa, sol, la, si)
SOUND_NOTE_FILES = ["do", "re", "mi", "fa", "sol", "la", "si"]

# Instruments disponibles (chacun a un sous-dossier sons/<instrument>/)
INSTRUMENT_ORDER = ["piano", "orgue", "guitare", "cloche"]
INSTRUMENT_LABELS = {"piano": "Piano",
                     "orgue": "Orgue", "guitare": "Guitare", "cloche": "Cloche"}

# Octave (fichier) selon la ligne du plateau (row 0 = ligne 1 ... row 7 = ligne 8)
# Lignes 1,8 ET 4,5 (centrales) -> octave 5 (aigu) / Lignes 2,7 -> 4 / Lignes 3,6 -> 3
# (les octaves graves rendaient mal : les lignes centrales passent en aigu)
def _row_to_octave(row):
    line = row + 1   # ligne 1 à 8
    return {1: 5, 8: 5, 2: 4, 7: 4, 3: 3, 6: 3, 4: 5, 5: 5}.get(line, 3)


class SoundManager:
    """Charge et joue les sons du jeu (notes + arpèges), avec choix de
    l'instrument (piano / orgue / guitare / cloche). Chaque instrument a ses
    fichiers .wav dans un sous-dossier sons/<instrument>/."""
    def __init__(self):
        self.enabled = True
        self.volume = 1.0      # 0.0 = muet, 1.0 = max
        self.instrument = "piano"
        self.sounds = {}      # nom -> objet Sound (instrument courant)
        self._loaded_instruments = set()
        self._all_sounds = {}  # instrument -> {nom: Sound}
        self._loaded = False
        self._gliss_events = []

    def set_volume(self, v):
        """Règle le volume (0.0 à 1.0). 0 = muet."""
        self.volume = max(0.0, min(1.0, v))
        for s in self.sounds.values():
            try:
                s.volume = self.volume
            except Exception:
                pass

    def set_instrument(self, name):
        """Change l'instrument courant et (re)charge ses sons si besoin."""
        if name not in INSTRUMENT_ORDER:
            return
        self.instrument = name
        self._load_instrument(name)
        self.sounds = self._all_sounds.get(name, {})

    def _sons_dir(self):
        base = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base, "sons")

    def _instrument_dir(self, instrument):
        """Dossier d'un instrument : sons/<instrument>/. Repli sur sons/ pour
        le piano (compatibilité avec l'ancienne organisation à plat)."""
        d = os.path.join(self._sons_dir(), instrument)
        if os.path.isdir(d):
            return d
        # Repli : anciens fichiers piano directement dans sons/
        if instrument == "piano":
            return self._sons_dir()
        return d

    def _load_instrument(self, instrument):
        """Charge les .wav d'un instrument donné (une seule fois)."""
        if instrument in self._loaded_instruments:
            return
        d = self._instrument_dir(instrument)
        store = {}
        if os.path.isdir(d):
            for note in SOUND_NOTE_FILES:
                for octv in (2, 3, 4, 5):
                    name = f"{note}{octv}"
                    path = os.path.join(d, f"{name}.wav")
                    if os.path.exists(path):
                        try:
                            s = SoundLoader.load(path)
                            if s:
                                s.volume = self.volume
                                store[name] = s
                        except Exception:
                            pass
            for name in ("ejection", "mat", "fugue"):
                path = os.path.join(d, f"{name}.wav")
                if os.path.exists(path):
                    try:
                        s = SoundLoader.load(path)
                        if s:
                            s.volume = self.volume
                            store[name] = s
                    except Exception:
                        pass
        self._all_sounds[instrument] = store
        self._loaded_instruments.add(instrument)

    def load(self):
        """Charge l'instrument courant (et marque le système comme prêt)."""
        if self._loaded:
            return
        d = self._sons_dir()
        if not os.path.isdir(d):
            self.enabled = False
            return
        self._load_instrument(self.instrument)
        self.sounds = self._all_sounds.get(self.instrument, {})
        self._loaded = True

    def _volume_factor(self, name):
        """Facteur d'atténuation par note. Les graves restent à 1.0 (référence)
        et les aigus sont nettement plus bas, ce qui équilibre l'ensemble."""
        if name and name[-1].isdigit():
            octv = int(name[-1])
            if octv == 5: return 0.40   # très aigus : très atténués
            if octv == 4: return 0.55
            if octv == 3: return 0.80
            return 1.0                    # octave 2 (graves) : volume max
        return 1.0

    def _play(self, name):
        if not self.enabled or self.volume <= 0: return
        s = self.sounds.get(name)
        if s:
            try:
                v = self.volume * self._volume_factor(name)
                s.volume = max(0.0, min(1.0, v))
                s.stop()
                s.play()
            except Exception:
                self._reload(name)

    def _play_fresh(self, name):
        """Joue un son rapidement (pour glissandos / notes rapides)."""
        if not self.enabled or self.volume <= 0: return
        s = self.sounds.get(name)
        if s:
            try:
                v = self.volume * self._volume_factor(name)
                s.volume = max(0.0, min(1.0, v))
                s.stop()
                s.play()
            except Exception:
                self._reload(name)

    def _reload(self, name):
        """Recharge un son qui a planté."""
        try:
            d = self._sons_dir()
            path = os.path.join(d, f"{name}.wav")
            if os.path.exists(path):
                s = SoundLoader.load(path)
                if s:
                    s.volume = self.volume
                    self.sounds[name] = s
                    s.play()
        except Exception:
            pass

    def note_name_for_cell(self, col, row):
        """Renvoie le nom de fichier de note pour une case (col, row)."""
        note = SOUND_NOTE_FILES[col]
        octv = _row_to_octave(row)
        return f"{note}{octv}"

    def play_note_cell(self, col, row):
        """Joue la note correspondant à une case."""
        self._play(self.note_name_for_cell(col, row))

    def play_glissando(self, target_col, target_row, count, direction, initial_delay=0.0):
        """Joue un glissando qui ARRIVE sur la note de la case cible.
        Utilise un thread séparé pour un timing précis."""
        if not self.enabled: return
        if count < 1: count = 1

        target_octave = _row_to_octave(target_row)
        def to_index(col, octv):
            return (octv - 2) * 7 + col
        def from_index(idx):
            idx = max(0, min(27, idx))
            octv = 2 + idx // 7
            col = idx % 7
            return col, octv

        target_idx = to_index(target_col, target_octave)
        notes_idx = []
        for k in range(count - 1, -1, -1):
            idx = target_idx - direction * k
            notes_idx.append(idx)

        notes = []
        for idx in notes_idx:
            col, octv = from_index(idx)
            notes.append(f"{SOUND_NOTE_FILES[col]}{octv}")

        self.play_sequence(notes, interval=0.10, initial_delay=initial_delay)

    def play_sequence(self, notes, interval=0.10, initial_delay=0.0):
        """Joue une suite de notes avec un timing précis via thread séparé."""
        if not self.enabled or not notes: return
        import threading, time
        def run():
            if initial_delay > 0:
                time.sleep(initial_delay)
            for nm in notes:
                self._play_fresh(nm)
                time.sleep(interval)
        t = threading.Thread(target=run, daemon=True)
        t.start()

    def play_delayed(self, name, delay):
        """Joue une note unique après un délai précis (via thread)."""
        if not self.enabled or not name: return
        import threading, time
        def run():
            time.sleep(delay)
            self._play_fresh(name)
        t = threading.Thread(target=run, daemon=True)
        t.start()

    def play_special(self, kind, delay=0.0):
        """Joue un arpège spécial (ejection / mat / fugue) après un délai (thread précis)."""
        if not self.enabled: return
        if delay > 0:
            import threading, time
            def run():
                time.sleep(delay)
                self._play(kind)
            t = threading.Thread(target=run, daemon=True)
            t.start()
        else:
            self._play(kind)


# Instance globale du gestionnaire de sons
SOUNDS = SoundManager()


def _accent(camp):   return COL_ORANGE   if camp == "Blanc" else COL_BLUE
def _piece_bg(camp): return COL_WHITE_PC if camp == "Blanc" else COL_BLACK_PC


# Palette de couleurs vives pour le thème "arcenciel" (festif multicolore).
RAINBOW_PALETTE = [
    (0.95, 0.26, 0.21, 1),  # rouge
    (0.95, 0.55, 0.15, 1),  # orange
    (0.98, 0.85, 0.20, 1),  # jaune
    (0.40, 0.80, 0.30, 1),  # vert
    (0.20, 0.70, 0.70, 1),  # turquoise
    (0.25, 0.55, 0.95, 1),  # bleu
    (0.55, 0.40, 0.90, 1),  # violet
    (0.95, 0.45, 0.75, 1),  # rose
]


def _rainbow_color(frac, camp):
    """Couleur d'accent multicolore pour le thème 'arcenciel'. La couleur est
    fixe selon `frac` (dérivé de la position de la pièce). Le fond blanc/noir et
    les contours ne changent pas : les camps restent distinguables."""
    idx = int(round(frac * (len(RAINBOW_PALETTE) - 1)))
    return RAINBOW_PALETTE[max(0, min(len(RAINBOW_PALETTE) - 1, idx))]


# ── Images de pièces personnalisées (thèmes "medieval" et "fleur") ───────────
_PIECE_IMG_CACHE = {}   # clé "dossier/fichier" -> CoreImage (ou False si absent)
_BG_IMG_CACHE = {}      # clé "dossier/fichier" -> texture (ou False si absent)

# Mapping thème -> dossier d'images personnalisées
_THEME_IMG_DIR = {"medieval": "themebataille", "fleur": "themefleurs",
                  "insectes": "themeinsectes"}

def _theme_image_dir(theme=None):
    """Renvoie le nom du dossier d'images du thème (ou None si le thème n'a pas
    d'images personnalisées)."""
    if theme is None:
        theme = CURRENT_THEME
    return _THEME_IMG_DIR.get(theme)

def _theme_bg_texture(fname, theme=None):
    """Renvoie la texture d'un fond (fond.png / plateau.png) du thème à images,
    ou None si absent. Mise en cache (clé incluant le dossier)."""
    folder = _theme_image_dir(theme)
    if not folder:
        return None
    key = f"{folder}/{fname}"
    if key in _BG_IMG_CACHE:
        cached = _BG_IMG_CACHE[key]
        return cached if cached else None
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, folder, fname)
    if not os.path.exists(path):
        _BG_IMG_CACHE[key] = False
        return None
    try:
        from kivy.core.image import Image as CoreImage
        tex = CoreImage(path).texture
        _BG_IMG_CACHE[key] = tex
        return tex
    except Exception:
        _BG_IMG_CACHE[key] = False
        return None


def _fit_width_rect(tex, screen_w, screen_h):
    """Calcule (pos, size) pour afficher une texture en occupant TOUTE la largeur
    de l'écran, la hauteur suivant le ratio de l'image (pas de déformation), le
    tout centré verticalement. Marche sur tous les écrans."""
    if not tex:
        return (0, 0), (0, 0)
    tw, th = tex.width, tex.height
    if tw <= 0:
        return (0, 0), (screen_w, screen_h)
    disp_w = screen_w
    disp_h = screen_w * (th / tw)     # hauteur proportionnelle à la largeur
    x = 0
    y = (screen_h - disp_h) / 2.0     # centré verticalement
    return (x, y), (disp_w, disp_h)


def _fit_height_rect(tex, screen_w, screen_h):
    """Calcule (pos, size) pour afficher une texture en occupant TOUTE la hauteur
    de l'écran, la largeur suivant le ratio (pas de déformation), centré
    horizontalement. Utile pour un fond qui serait coupé en haut/bas."""
    if not tex:
        return (0, 0), (0, 0)
    tw, th = tex.width, tex.height
    if th <= 0:
        return (0, 0), (screen_w, screen_h)
    disp_h = screen_h
    disp_w = screen_h * (tw / th)     # largeur proportionnelle à la hauteur
    x = (screen_w - disp_w) / 2.0     # centré horizontalement
    y = 0
    return (x, y), (disp_w, disp_h)


def _fit_menu_bg(tex, screen_w, screen_h):
    """Choisit l'ajustement du fond menu selon le thème : insectes cale sur la
    hauteur (sinon l'image était coupée), les autres calent sur la largeur."""
    if CURRENT_THEME == "insectes":
        return _fit_height_rect(tex, screen_w, screen_h)
    return _fit_width_rect(tex, screen_w, screen_h)


def _piece_image_for(piece, theme=None):
    """Renvoie la texture de l'image personnalisée pour une pièce (thèmes à
    images), ou None si absente. Fichiers : <type><camp>.png
    ex. heritierblanc.png, gardenoir.png."""
    folder = _theme_image_dir(theme)
    if not folder:
        return None
    type_map = {"Héritier": "heritier", "Nurse": "nurse", "Soldat": "soldat",
                "Garde": "garde", "Chevalier": "chevalier"}
    camp_map = {"Blanc": "blanc", "Noir": "noir"}
    # Thème insectes : Soldat et Garde partagent la même image "carree".
    if theme == "insectes" and piece["type"] in ("Soldat", "Garde"):
        t = "carree"
    else:
        t = type_map.get(piece["type"])
    c = camp_map.get(piece["camp"])
    if not t or not c:
        return None
    fname = f"{t}{c}.png"
    key = f"{folder}/{fname}"
    if key in _PIECE_IMG_CACHE:
        cached = _PIECE_IMG_CACHE[key]
        return cached.texture if cached else None
    base = os.path.dirname(os.path.abspath(__file__))
    path = os.path.join(base, folder, fname)
    if not os.path.exists(path):
        _PIECE_IMG_CACHE[key] = False
        return None
    try:
        from kivy.core.image import Image as CoreImage
        img = CoreImage(path)
        _PIECE_IMG_CACHE[key] = img
        return img.texture
    except Exception:
        _PIECE_IMG_CACHE[key] = False
        return None


# ── Dessin d'une pièce ───────────────────────────────────────────────────────

def draw_piece(canvas, x, y, sz, piece, outline=None, outline_w=2,
               push_highlight_dirs=None, flipped=True, rainbow_frac=None,
               preview_theme=None, force_normal=False):
    """Dessine une pièce. push_highlight_dirs : liste de (dc, dr) en coordonnées
    de jeu, dont les points correspondants doivent être grossis (et inversés en
    couleur : noir sur pièce blanche, blanc sur pièce noire).
    flipped : True si le plateau est dans l'orientation Blanc-en-bas (par défaut).
    rainbow_frac : si le thème 'arcenciel' est actif, fraction 0→1 (position) pour
    la teinte de l'accent ; None sinon (accent normal du thème).
    preview_theme : pour un aperçu, force l'affichage des images de CE thème
    (ex. 'medieval', 'fleur'), sans dépendre du thème global courant.
    force_normal : force le dessin classique (jamais d'image), même si le thème
    courant est à images (pour les aperçus des AUTRES thèmes)."""
    pd    = sz * 0.04
    px    = x + pd
    py    = y + pd
    inner = sz - 2 * pd
    cx    = x + sz / 2
    cy    = y + sz / 2

    # Thèmes à images (medieval, fleur) : afficher l'image perso (si présente)
    img_theme = preview_theme if preview_theme else CURRENT_THEME
    is_img_theme = _theme_image_dir(img_theme) is not None
    if is_img_theme and not force_normal:
        tex = _piece_image_for(piece, theme=img_theme)
        if tex is not None:
            dx_factor = 1 if flipped else -1
            dy_factor = 1 if flipped else -1
            with canvas:
                # Contour de sélection/groupe/immobilisé autour de l'image
                if outline is not None:
                    Color(*outline)
                    Line(rectangle=(px, py, inner, inner), width=outline_w)
                # Thème insectes : Soldat et Garde ont la même image. On dessine
                # PAR-DESSUS une croix pour les distinguer et montrer le sens de
                # poussée : Soldat = croix '+' (orthogonal), Garde = croix '×'
                # (diagonal), comme dans le reste du jeu.
                if img_theme == "insectes" and piece["type"] in ("Soldat", "Garde"):
                    # Couleur sable (clair) pour les Blancs, terre (foncé) pour
                    # les Noirs.
                    cross_col = ((0.86, 0.72, 0.45, 1) if piece["camp"] == "Blanc"
                                 else (0.30, 0.18, 0.08, 1))
                    arm = inner * 0.46           # longueur des branches
                    cw = max(S(3), inner * 0.10)  # épaisseur (un peu épaisse)
                    Color(*cross_col)
                    if piece["type"] == "Soldat":
                        # Soldat : croix droite + (pousse en orthogonal)
                        Line(points=[cx - arm, cy, cx + arm, cy], width=cw,
                             cap="round")
                        Line(points=[cx, cy - arm, cx, cy + arm], width=cw,
                             cap="round")
                    else:
                        # Garde : croix diagonale × (pousse en diagonale)
                        d = arm * 0.72
                        Line(points=[cx - d, cy - d, cx + d, cy + d], width=cw,
                             cap="round")
                        Line(points=[cx - d, cy + d, cx + d, cy - d], width=cw,
                             cap="round")
                Color(1, 1, 1, 1)
                # Image agrandie de 10 % (centrée) pour mieux ressortir
                img_sz = inner * 1.10
                img_off = (img_sz - inner) / 2.0
                Rectangle(texture=tex,
                          pos=(px - img_off, py - img_off),
                          size=(img_sz, img_sz))
                # Gros points de poussée par-dessus l'image (après une poussée)
                if push_highlight_dirs:
                    big_color = ((0, 0, 0, 1) if piece["camp"] == "Blanc"
                                 else (1, 1, 1, 1))
                    pr = inner * 0.12
                    off = inner * 0.32
                    for (gdc, gdr) in push_highlight_dirs:
                        ex = cx + (gdc * dx_factor) * off
                        ey = cy + (gdr * dy_factor) * off
                        Color(*big_color)
                        Ellipse(pos=(ex - pr, ey - pr), size=(pr * 2, pr * 2))
            return   # image affichée : on ne dessine pas la pièce normale

    bg    = _piece_bg(piece["camp"])
    if CURRENT_THEME == "arcenciel" and rainbow_frac is not None:
        acc = _rainbow_color(rainbow_frac, piece["camp"])
    else:
        acc   = _accent(piece["camp"])
    if outline is None:
        outline = (0.87, 0.87, 0.87, 1) if piece["camp"] == "Blanc" else (0.2, 0.2, 0.33, 1)
    sw  = max(2, inner * 0.10)
    t   = piece["type"]

    # Sens écran selon flipped. Le joueur Noir voit le plateau tourné à 180°
    # (colonnes ET rangées inversées), donc les deux axes s'inversent.
    dx_factor = 1 if flipped else -1
    dy_factor = 1 if flipped else -1

    # Préparer un set de directions visuelles (dx_écran, dy_écran) à grossir
    big_dirs = set()
    if push_highlight_dirs:
        for (gdc, gdr) in push_highlight_dirs:
            big_dirs.add((gdc * dx_factor, gdr * dy_factor))

    # Couleur inversée pour les points grossis
    big_color = (0, 0, 0, 1) if piece["camp"] == "Blanc" else (1, 1, 1, 1)

    with canvas:
        if t in ("Soldat", "Garde"):
            Color(*bg);      Rectangle(pos=(px, py), size=(inner, inner))
            Color(*outline); Line(rectangle=(px, py, inner, inner), width=outline_w)
            Color(*acc)
            inset = inner * 0.18
            if t == "Soldat":
                # Croix +
                Line(points=[px + inset, cy, px + inner - inset, cy],
                     width=sw, cap="round")
                Line(points=[cx, py + inset, cx, py + inner - inset],
                     width=sw, cap="round")
                # Points en X : positions diagonales (±off, ±off)
                pr = inner * 0.06
                off = inner * 0.30
                point_specs = [(-off, -off, -1, -1), ( off, -off,  1, -1),
                               (-off,  off, -1,  1), ( off,  off,  1,  1)]
                for dx, dy, gdc, gdy_e in point_specs:
                    is_big = (gdc, gdy_e) in big_dirs
                    point_r = pr * 2.0 if is_big else pr
                    if is_big:
                        Color(*big_color)
                    else:
                        Color(*acc)
                    Ellipse(pos=(cx + dx - point_r, cy + dy - point_r),
                            size=(point_r * 2, point_r * 2))
            else:
                # Croix X
                Line(points=[px + inset, py + inset, px + inner - inset, py + inner - inset],
                     width=sw, cap="round")
                Line(points=[px + inset, py + inner - inset, px + inner - inset, py + inset],
                     width=sw, cap="round")
                # Points en + : positions (0, ±off) et (±off, 0)
                pr = inner * 0.06
                off = inner * 0.36
                point_specs = [(0, -off, 0, -1), (0, off, 0, 1),
                               (-off, 0, -1, 0), (off, 0, 1, 0)]
                for dx, dy, gdc, gdy_e in point_specs:
                    is_big = (gdc, gdy_e) in big_dirs
                    point_r = pr * 2.0 if is_big else pr
                    if is_big:
                        Color(*big_color)
                    else:
                        Color(*acc)
                    Ellipse(pos=(cx + dx - point_r, cy + dy - point_r),
                            size=(point_r * 2, point_r * 2))

        elif t in ("Nurse", "Héritier"):
            Color(*bg);      Ellipse(pos=(px, py), size=(inner, inner))
            Color(*outline); Line(circle=(cx, cy, inner / 2), width=outline_w)
            if t == "Héritier":
                d  = inner * 0.20
                r2 = inner * 0.14
                Color(*acc);             Ellipse(pos=(px + d, py + d), size=(inner - 2*d, inner - 2*d))
                # "Trou" : on peint le centre avec la couleur du plateau → illusion de transparence
                Color(*COL_BG_BOARD);    Ellipse(pos=(cx - r2, cy - r2), size=(r2*2, r2*2))

        elif t == "Chevalier":
            h_off = inner * 0.20
            pts = [cx, py + inner,
                   px + inner, cy + h_off,
                   px + inner, cy - h_off,
                   cx, py,
                   px, cy - h_off,
                   px, cy + h_off]
            mesh_verts = [cx, cy, 0, 0]
            for i in range(0, len(pts), 2):
                mesh_verts.extend([pts[i], pts[i+1], 0, 0])
            indices = []
            for i in range(1, 6):
                indices.extend([0, i, i + 1])
            indices.extend([0, 6, 1])
            Color(*acc)
            Mesh(vertices=mesh_verts, indices=indices, mode="triangles")
            Color(*outline)
            Line(points=pts + [pts[0], pts[1]], width=outline_w)


# ── Logo de La Fuga (rosace 8 segments) ──────────────────────────────────────

import math

def draw_logo(canvas, cx, cy, radius, colored=True, line_width=2.5):
    """Dessine la rosace du logo La Fuga.
    8 segments rectangulaires alternant orange/bleu (col 0,2,4,6 et 1,3,5,7),
    avec petits triangles noir/blanc dans les coins, et trou central.
    Si colored=False, ne dessine que les contours sur fond plateau."""
    inner_r = radius * 0.42
    outer_r = radius
    # 8 directions cardinales et diagonales
    # Cas simple : on dessine 8 secteurs trapézoïdaux puis on masque par cercle intérieur
    # Pour la version "contours seulement", on dessine les traits délimitant les segments
    seg_half_angle = math.pi / 8   # 22.5° de demi-largeur par segment
    if colored:
        # 8 segments : orange (haut, bas, gauche, droite) et bleu (diagonales)
        colors_seg = [COL_ORANGE, COL_BLUE] * 4
        for i in range(8):
            ang = -math.pi / 2 + i * (math.pi / 4)   # part du haut, sens horaire
            a1 = ang - seg_half_angle
            a2 = ang + seg_half_angle
            verts = [
                cx + inner_r * math.cos(a1), cy + inner_r * math.sin(a1),
                cx + outer_r * math.cos(a1), cy + outer_r * math.sin(a1),
                cx + outer_r * math.cos(a2), cy + outer_r * math.sin(a2),
                cx + inner_r * math.cos(a2), cy + inner_r * math.sin(a2),
            ]
            with canvas:
                Color(*colors_seg[i])
                Mesh(vertices=[verts[0], verts[1], 0, 0,
                               verts[2], verts[3], 0, 0,
                               verts[4], verts[5], 0, 0,
                               verts[6], verts[7], 0, 0],
                     indices=[0, 1, 2, 0, 2, 3],
                     mode="triangles")
        # Petits triangles noir/blanc dans les coins entre segments
        for i in range(8):
            ang_gap = -math.pi / 2 + i * (math.pi / 4) + math.pi / 8
            # Triangle noir d'un côté, blanc de l'autre, alternance
            tri_color = (0, 0, 0, 1) if i % 2 == 0 else (1, 1, 1, 1)
            a1 = ang_gap - math.pi / 24
            a2 = ang_gap + math.pi / 24
            with canvas:
                Color(*tri_color)
                Mesh(vertices=[cx + outer_r * math.cos(a1), cy + outer_r * math.sin(a1), 0, 0,
                               cx + outer_r * math.cos(a2), cy + outer_r * math.sin(a2), 0, 0,
                               cx + (inner_r + (outer_r - inner_r) * 0.55) * math.cos(ang_gap),
                               cy + (inner_r + (outer_r - inner_r) * 0.55) * math.sin(ang_gap), 0, 0],
                     indices=[0, 1, 2], mode="triangles")
        # Contours
        with canvas:
            Color(0, 0, 0, 1)
            Line(circle=(cx, cy, outer_r), width=line_width)
            Line(circle=(cx, cy, inner_r), width=line_width)
            for i in range(8):
                ang = -math.pi / 2 + i * (math.pi / 4) - seg_half_angle
                Line(points=[cx + inner_r * math.cos(ang), cy + inner_r * math.sin(ang),
                             cx + outer_r * math.cos(ang), cy + outer_r * math.sin(ang)],
                     width=line_width)
                ang2 = -math.pi / 2 + i * (math.pi / 4) + seg_half_angle
                Line(points=[cx + inner_r * math.cos(ang2), cy + inner_r * math.sin(ang2),
                             cx + outer_r * math.cos(ang2), cy + outer_r * math.sin(ang2)],
                     width=line_width)
    else:
        # Contours seulement, en gris foncé
        with canvas:
            Color(*COL_GRID)
            Line(circle=(cx, cy, outer_r), width=line_width)
            Line(circle=(cx, cy, inner_r), width=line_width)
            for i in range(8):
                ang = -math.pi / 2 + i * (math.pi / 4) - seg_half_angle
                Line(points=[cx + inner_r * math.cos(ang), cy + inner_r * math.sin(ang),
                             cx + outer_r * math.cos(ang), cy + outer_r * math.sin(ang)],
                     width=line_width)
                ang2 = -math.pi / 2 + i * (math.pi / 4) + seg_half_angle
                Line(points=[cx + inner_r * math.cos(ang2), cy + inner_r * math.sin(ang2),
                             cx + outer_r * math.cos(ang2), cy + outer_r * math.sin(ang2)],
                     width=line_width)


class CapturesWidget(Widget):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.pieces = []
        self.bind(size=self._redraw, pos=self._redraw)

    def update_pieces(self, pieces):
        self.pieces = pieces
        self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        if not self.pieces or self.width < 10 or self.height < 10:
            return
        n = len(self.pieces)
        # Calcule la taille de pièce qui permet de toutes les afficher
        # Avec un chevauchement de 30% (sp = 0.7 * sz)
        # Largeur totale = sz + (n - 1) * sp = sz * (1 + 0.7 * (n - 1))
        max_h = self.height - 2
        max_w_each = self.width / (1 + 0.7 * (n - 1)) if n > 1 else self.width
        sz = min(max_h, max_w_each, 36)
        sp = sz * 0.7   # chevauchement marqué pour gagner de la place
        # Affichage de GAUCHE à droite (plus naturel à lire)
        for i, p in enumerate(self.pieces):
            x = self.x + i * sp
            y = self.y + (self.height - sz) / 2
            draw_piece(self.canvas, x, y, sz, p, outline_w=1)


class RoundButton(Button):
    _rainbow_counter = 0   # compteur global pour assigner une couleur fixe

    def __init__(self, bg_color=COL_BTN_GREY, radius=None, **kw):
        # Police de base demandée (sert de plafond pour l'auto-ajustement)
        self._base_font = kw.get("font_size", None)
        super().__init__(**kw)
        self.background_normal = ""
        self.background_color  = (0, 0, 0, 0)
        self._bg_color = bg_color
        # Mémorise SI la couleur est une couleur de thème (par identité), pour
        # pouvoir la relire après un changement de thème (sinon le bouton
        # garderait l'ancienne teinte, le tuple global ayant été réassigné).
        self._theme_key = RoundButton._detect_theme_key(bg_color)
        # Couleur arc-en-ciel FIXE de ce bouton (assignée une fois, à la création)
        self._rainbow_idx = RoundButton._rainbow_counter % len(RAINBOW_PALETTE)
        RoundButton._rainbow_counter += 1
        # radius calculé à l'exécution (pas à la définition de classe)
        self._radius   = radius if radius is not None else S(18)
        # IMPORTANT : on ne fixe PAS text_size -> le texte reste sur UNE seule
        # ligne et est centré automatiquement par le Button. L'auto-fit réduit
        # la police pour qu'il rentre en largeur.
        self.halign = "center"
        self.valign = "middle"
        self.shorten = False
        self.bind(pos=self._redraw, size=self._redraw)
        self.bind(size=self._autofit_font, text=self._autofit_font)

    @staticmethod
    def _detect_theme_key(color):
        """Renvoie la 'clé de thème' d'une couleur si c'en est une (comparaison
        par identité), sinon None. Permet de relire la bonne teinte après un
        changement de thème."""
        if color is COL_ORANGE:     return "orange"
        if color is COL_BLUE:       return "blue"
        if color is COL_ORANGE_DIM: return "orange_dim"
        if color is COL_BLUE_DIM:   return "blue_dim"
        return None

    def refresh_theme_color(self):
        """Réapplique la couleur de thème courante (si le bouton en utilise une)
        puis redessine. Appelé au changement de thème."""
        key = getattr(self, "_theme_key", None)
        if key == "orange":       self._bg_color = COL_ORANGE
        elif key == "blue":       self._bg_color = COL_BLUE
        elif key == "orange_dim": self._bg_color = COL_ORANGE_DIM
        elif key == "blue_dim":   self._bg_color = COL_BLUE_DIM
        self._redraw()

    def set_bg(self, color):
        self._bg_color = color
        self._theme_key = RoundButton._detect_theme_key(color)
        self._redraw()

    def set_selected(self, selected):
        """Marque le bouton comme sélectionné. Sur TOUS les thèmes (y compris
        l'arc-en-ciel où la couleur de fond est imposée par la palette), un
        contour blanc épais rend la sélection visible."""
        self._selected = bool(selected)
        self._redraw()

    def _autofit_font(self, *a):
        """Réduit la police si le texte dépasse la largeur ou la hauteur du
        bouton. Garantit qu'aucun texte ne déborde, sur n'importe quel écran."""
        if not self.text or self.width <= 1:
            return
        from kivy.core.text import Label as CoreLabel
        avail_w = self.width * 0.90
        avail_h = self.height * 0.85
        if avail_w <= 0 or avail_h <= 0:
            return
        try:
            base = float(str(self._base_font).replace("sp", "").replace("dp", "")) \
                   if self._base_font else 16.0
        except Exception:
            base = 16.0
        size = base
        for _ in range(24):
            cl = CoreLabel(text=self.text, font_size=size)
            cl.refresh()
            tw = cl.texture.size[0] if cl.texture else 0
            th = cl.texture.size[1] if cl.texture else 0
            if (tw <= avail_w and th <= avail_h) or size <= 6:
                break
            size -= 1
        # Pixels purs (cohérent avec SF) : pas d'unité 'sp'
        self.font_size = size

    def _redraw(self, *a):
        self.canvas.before.clear()
        # Thème arc-en-ciel : chaque bouton a une couleur vive FIXE de la palette.
        if CURRENT_THEME == "arcenciel":
            base = RAINBOW_PALETTE[self._rainbow_idx]
            a_orig = self._bg_color[3] if len(self._bg_color) > 3 else 1.0
            col = (base[0], base[1], base[2], a_orig)
        else:
            col = self._bg_color
        with self.canvas.before:
            Color(*col)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self._radius])
            # Contour de sélection (visible sur tous les thèmes, arc-en-ciel inclus)
            if getattr(self, "_selected", False):
                from kivy.graphics import Line
                Color(1, 1, 1, 1)
                Line(rounded_rectangle=(self.x + S(2), self.y + S(2),
                                        self.width - S(4), self.height - S(4),
                                        self._radius), width=S(2.5))
        # On ne touche pas à text_size : le texte reste sur une ligne, centré.


class StarButton(RoundButton):
    """Bouton rond affichant une ÉTOILE dessinée (pas un caractère, pour éviter
    les soucis de police). L'étoile est proportionnelle à la taille du bouton.
    star_color : couleur de l'étoile. filled : pleine ou contour."""
    def __init__(self, star_color=(1, 0.85, 0.3, 1), filled=True, **kw):
        kw["text"] = ""
        super().__init__(**kw)
        self._star_color = star_color
        self._star_filled = filled
        self.bind(pos=self._redraw_star, size=self._redraw_star)

    def set_filled(self, filled):
        self._star_filled = filled
        self._redraw_star()

    def _redraw_star(self, *a):
        import math
        self.canvas.after.clear()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        R = min(self.width, self.height) * 0.32   # rayon externe (proportionnel)
        r = R * 0.42                               # rayon interne
        pts = []
        for i in range(10):
            ang = math.pi / 2 + i * math.pi / 5   # 5 branches
            rad = R if i % 2 == 0 else r
            pts.append(cx + rad * math.cos(ang))
            pts.append(cy + rad * math.sin(ang))
        with self.canvas.after:
            Color(*self._star_color)
            if self._star_filled:
                # Triangulation en éventail depuis le centre
                verts = []
                indices = []
                verts += [cx, cy, 0, 0]
                for k in range(10):
                    verts += [pts[2 * k], pts[2 * k + 1], 0, 0]
                for k in range(10):
                    indices += [0, 1 + k, 1 + (k + 1) % 10]
                Mesh(vertices=verts, indices=indices, mode="triangles")
            else:
                Line(points=pts + pts[:2], width=1.4)


class UndoButton(RoundButton):
    """Bouton rond affichant une FLÈCHE GAUCHE droite dessinée (←), pour éviter
    les soucis de police. Proportionnelle à la taille du bouton."""
    def __init__(self, arrow_color=(1, 1, 1, 1), **kw):
        kw["text"] = ""
        super().__init__(**kw)
        self._arrow_color = arrow_color
        self.bind(pos=self._redraw_arrow, size=self._redraw_arrow)

    def _redraw_arrow(self, *a):
        self.canvas.after.clear()
        cx = self.x + self.width / 2
        cy = self.y + self.height / 2
        L = min(self.width, self.height) * 0.30      # demi-longueur de la flèche
        w = max(1.8, L * 0.22)                        # épaisseur du trait
        head = L * 0.7                                # taille de la pointe
        x_left = cx - L
        x_right = cx + L
        with self.canvas.after:
            Color(*self._arrow_color)
            # Tige horizontale
            Line(points=[x_left, cy, x_right, cy], width=w, cap="round")
            # Pointe (deux segments) à gauche
            Line(points=[x_left, cy, x_left + head, cy + head], width=w,
                 cap="round", joint="round")
            Line(points=[x_left, cy, x_left + head, cy - head], width=w,
                 cap="round", joint="round")


# ── Écran de connexion / inscription en ligne ───────────────────────────────

class LoginScreen(Screen):
    """Écran d'authentification : login ou inscription au serveur en ligne."""
    def __init__(self, **kw):
        super().__init__(**kw)
        self.mode = "login"   # "login" ou "register"
        self._build()

    def _build(self):
        root = FloatLayout()
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        # Bouton retour
        back = RoundButton(text="< Menu", font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(0.28, 0.05),
                           pos_hint={"x": 0.04, "top": 0.975})
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        root.add_widget(back)

        # Titre
        self.title_lbl = Label(text="Connexion", font_size=SF("28sp"), bold=True,
                               italic=True, color=(0.05, 0.05, 0.05, 1),
                               size_hint=(1, 0.08),
                               pos_hint={"center_x": 0.5, "top": 0.90})
        root.add_widget(self.title_lbl)

        # Bouton toggle login/inscription
        self.toggle_btn = RoundButton(text="Pas encore inscrit ?",
                                      font_size=SF("13sp"), bold=True,
                                      bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                                      size_hint=(0.5, 0.045),
                                      pos_hint={"center_x": 0.5, "top": 0.80})
        self.toggle_btn.bind(on_release=self._toggle_mode)
        root.add_widget(self.toggle_btn)

        # Champ pseudo
        self.pseudo_input = TextInput(text="", multiline=False,
                                      size_hint=(0.7, 0.06),
                                      hint_text="Pseudo",
                                      font_size=SF("16sp"),
                                      pos_hint={"center_x": 0.5, "top": 0.70})
        root.add_widget(self.pseudo_input)

        # Champ mot de passe
        self.password_input = TextInput(text="", multiline=False, password=True,
                                        size_hint=(0.7, 0.06),
                                        hint_text="Mot de passe",
                                        font_size=SF("16sp"),
                                        pos_hint={"center_x": 0.5, "top": 0.61})
        root.add_widget(self.password_input)

        # Champ email (visible seulement en mode register, optionnel)
        self.email_input = TextInput(text="", multiline=False,
                                     size_hint=(0.7, 0.06),
                                     hint_text="Email (optionnel)",
                                     font_size=SF("16sp"),
                                     pos_hint={"center_x": 0.5, "top": 0.52})
        root.add_widget(self.email_input)
        self.email_input.opacity = 0
        self.email_input.disabled = True

        # Bouton valider
        self.submit_btn = RoundButton(text="Se connecter", font_size=SF("17sp"),
                                      bold=True, bg_color=COL_ORANGE,
                                      color=(1, 1, 1, 1),
                                      size_hint=(0.6, 0.07),
                                      pos_hint={"center_x": 0.5, "top": 0.40})
        self.submit_btn.bind(on_release=self._submit)
        root.add_widget(self.submit_btn)

        # Label statut (erreur / succès)
        self.status_lbl = Label(text="", font_size=SF("14sp"), italic=True,
                                color=(0.7, 0.1, 0.1, 1),
                                halign="center", valign="middle",
                                size_hint=(0.9, 0.06),
                                pos_hint={"center_x": 0.5, "top": 0.30})
        self.status_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        root.add_widget(self.status_lbl)

        self.add_widget(root)
        self._update_mode_ui()

    def _toggle_mode(self, *a):
        self.mode = "register" if self.mode == "login" else "login"
        self._update_mode_ui()

    def _update_mode_ui(self):
        if self.mode == "login":
            self.title_lbl.text = "Connexion"
            self.toggle_btn.text = "Pas encore inscrit ?"
            self.submit_btn.text = "Se connecter"
            self.email_input.opacity = 0
            self.email_input.disabled = True
        else:
            self.title_lbl.text = "Inscription"
            self.toggle_btn.text = "J'ai déjà un compte"
            self.submit_btn.text = "Créer le compte"
            self.email_input.opacity = 1
            self.email_input.disabled = False
        self.status_lbl.text = ""

    def _submit(self, *a):
        pseudo = self.pseudo_input.text.strip()
        password = self.password_input.text
        email = self.email_input.text.strip()
        if not pseudo or not password:
            self.status_lbl.color = (0.7, 0.1, 0.1, 1)
            self.status_lbl.text = "Pseudo et mot de passe requis"
            return
        self.submit_btn.disabled = True
        self.status_lbl.color = (0.2, 0.2, 0.5, 1)
        self.status_lbl.text = "Connexion au serveur..."
        def on_done(success, msg):
            self.submit_btn.disabled = False
            if success:
                self.status_lbl.color = (0.1, 0.6, 0.1, 1)
                self.status_lbl.text = msg
                # Le jeu est pensé pour être connecté : les parties locales
                # jouées hors compte sont effacées définitivement. L'historique
                # affichera désormais les parties du compte (tous appareils).
                try:
                    erase_local_parties()
                except Exception:
                    pass
                Clock.schedule_once(lambda dt: self._goto_menu(), 0.8)
            else:
                self.status_lbl.color = (0.7, 0.1, 0.1, 1)
                self.status_lbl.text = msg
        if self.mode == "login":
            ONLINE.login(pseudo, password, on_done)
        else:
            ONLINE.register(pseudo, password, email, on_done)

    def _goto_menu(self):
        self.manager.current = "menu"
        # Notifier le menu pour rafraîchir l'état de connexion
        menu = self.manager.get_screen("menu")
        if hasattr(menu, "_refresh_online_ui"):
            menu._refresh_online_ui()


# ── Écran menu ───────────────────────────────────────────────────────────────

class MenuTourOverlay(FloatLayout):
    """Calque-guide affiché PAR-DESSUS le vrai menu : surbrillance de l'élément
    décrit (anneau rouge), bulle de texte en bas, boutons Précédent / Continuer.
    Fait défiler le menu automatiquement vers chaque élément."""

    def __init__(self, menu, tuto_screen, **kw):
        super().__init__(**kw)
        self.menu = menu
        self.tuto = tuto_screen
        self.idx = 0
        self.stops = self._build_stops()

        # Barre du bas : texte + Précédent / Continuer
        bar = BoxLayout(orientation="vertical", size_hint=(1, 0.26),
                        pos_hint={"x": 0, "y": 0})
        with bar.canvas.before:
            Color(0.09, 0.09, 0.13, 0.97)
            self._bar_bg = Rectangle()
        bar.bind(pos=lambda *a: setattr(self._bar_bg, "pos", bar.pos),
                 size=lambda *a: setattr(self._bar_bg, "size", bar.size))
        self.text_lbl = Label(text="", font_size=SF("15sp"), color=(1, 1, 1, 1),
                              halign="center", valign="middle", size_hint=(1, 0.6))
        self.text_lbl.bind(size=lambda w, s: setattr(
            w, "text_size", (s[0] - S(32), s[1])))
        nav = BoxLayout(size_hint=(1, 0.4), spacing=S(12), padding=(S(16), S(8)))
        self.prev_b = RoundButton(text="< Précédent", font_size=SF("14sp"),
                                  bold=True, bg_color=COL_BTN_GREY,
                                  color=(1, 1, 1, 1))
        self.prev_b.bind(on_release=lambda *a: self._prev())
        self.next_b = RoundButton(text="Continuer >", font_size=SF("14sp"),
                                  bold=True, bg_color=COL_BLUE, color=(1, 1, 1, 1))
        self.next_b.bind(on_release=lambda *a: self._next())
        nav.add_widget(self.prev_b)
        nav.add_widget(self.next_b)
        bar.add_widget(self.text_lbl)
        bar.add_widget(nav)
        self.add_widget(bar)
        self._bar = bar
        # Suivre le défilement du menu pour que l'anneau rouge reste sur la touche.
        try:
            self.menu._menu_scroll.bind(scroll_y=self._on_scroll)
        except Exception:
            pass
        Clock.schedule_once(lambda dt: self._show_stop(), 0.06)

    def _build_stops(self):
        return [
            {"targets": ["obj", "cad"], "scroll": "obj",
             "text": ("Avant une partie, choisis un OBJECTIF (Partie = une seule ; "
                      "3/5/7 = premier à ce nombre de points ; Flash = 2 parties, "
                      "une par couleur, puis 2 de plus si égalité) et une CADENCE "
                      "(minutes par joueur, ou Zen sans pendule). En 3/5/7, si "
                      "l'adversaire atteint le score alors que tu as joué une "
                      "partie de MOINS que lui en Blanc, tu joues une ULTIME partie "
                      "en Blanc pour égaliser les couleurs.")},
            {"targets": ["local", "online"], "scroll": "local",
             "text": ("Puis lance : « Jouer en local » (à deux sur le même "
                      "appareil) ou « Jouer en ligne ». En ligne, le matchmaking "
                      "te trouve un adversaire de ton niveau ; c'est le SEUL mode "
                      "qui fait bouger ton MÉLO, ton classement (~1500 au départ), "
                      "qui monte quand tu gagnes et baisse quand tu perds.")},
            {"targets": ["ai"], "scroll": "ai",
             "text": ("« deep grey » est l'intelligence artificielle du jeu : "
                      "affronte-la pour t'entraîner quand tu veux.")},
            {"targets": ["search", "fav"], "scroll": "search",
             "text": ("Cherche un joueur par son nom pour le défier directement ; "
                      "l'étoile gère tes favoris.")},
            {"targets": ["corr"], "scroll": "corr",
             "text": ("Fais glisser l'écran vers le BAS pour la CORRESPONDANCE : "
                      "des parties sans limite de temps, contre des joueurs "
                      "enregistrés. Pour en lancer une, clique sur un plateau "
                      "vide, puis choisis ton adversaire parmi tes favoris.")},
            {"targets": ["compte"], "scroll": "obj",
             "text": ("« Compte » : crée ton compte ici. Il est OBLIGATOIRE pour "
                      "jouer en ligne et en correspondance.")},
            {"targets": ["random"], "scroll": "obj",
             "text": ("« Random » active la variante Random Fuga : la position de "
                      "départ est tirée au hasard parmi 1750 positions x 2 types "
                      "de symétrie, soit 3500 débuts possibles. Il se réinitialise "
                      "à chaque lancement.")},
            {"targets": ["plus"], "scroll": "plus",
             "text": ("« Plus » donne accès à ce tuto, à l'historique de tes "
                      "parties, à l'analyse, aux réglages, et à SOUTENIR LES "
                      "DÉVELOPPEURS (un petit don pour aider le jeu).")},
            {"targets": [], "scroll": "obj",
             "text": ("Et voilà, tu sais tout ! Le reste (thèmes, réglages, "
                      "historique, analyse), tu le découvriras toi-même. "
                      "Bonne fugue !")},
        ]

    def on_touch_down(self, touch):
        # La barre du bas capte ses propres taps (Précédent/Continuer) ; partout
        # ailleurs on laisse passer vers le menu, pour qu'il DÉFILE normalement.
        # Les anneaux rouges suivent le défilement (voir _on_scroll).
        return super().on_touch_down(touch)

    def _widgets(self, names):
        m = {"obj": getattr(self.menu, "_obj_row", None),
             "cad": getattr(self.menu, "_cad_row", None),
             "local": getattr(self.menu, "_btn_local", None),
             "online": getattr(self.menu, "_btn_online", None),
             "search": getattr(self.menu, "search_input", None),
             "fav": getattr(self.menu, "_btn_fav", None),
             "ai": getattr(self.menu, "_btn_ai", None),
             "plus": getattr(self.menu, "_btn_plus", None),
             "corr": getattr(self.menu, "_corr_header", None),
             "compte": getattr(self.menu, "account_btn", None),
             "random": getattr(self.menu, "random_btn", None)}
        return [m[n] for n in names if m.get(n) is not None]

    def _scroll_to_element(self, w):
        """Fait défiler le menu pour amener w dans la zone visible, AU-DESSUS de
        la barre de texte du bas."""
        sv = getattr(self.menu, "_menu_scroll", None)
        if sv is None:
            return
        try:
            col = sv.children[0]        # le conteneur vertical du menu
        except Exception:
            return
        view_h = sv.height
        scrollable = col.height - view_h
        if scrollable <= 1:
            return                      # tout tient à l'écran, pas de défilement
        _, wy = w.to_window(w.center_x, w.center_y)
        _, cy = col.to_window(col.x, col.y)
        y_in_content = wy - cy          # position de w depuis le bas du contenu
        # On place w à ~62% de la hauteur visible (bien au-dessus de la barre).
        target = view_h * 0.62
        sy = (y_in_content - target) / scrollable
        try:
            sv.scroll_y = max(0.0, min(1.0, sy))
        except Exception:
            pass

    def _on_scroll(self, *a):
        # Le menu a défilé : on redessine l'anneau à la nouvelle position.
        try:
            self._draw_ring(self.stops[self.idx]["targets"])
        except Exception:
            pass

    def _show_stop(self):
        stop = self.stops[self.idx]
        self.text_lbl.text = stop["text"]
        last = (self.idx == len(self.stops) - 1)
        self.next_b.text = "Bonne fugue !" if last else "Continuer >"
        self.prev_b.opacity = 1
        sc = stop.get("scroll")
        if sc:
            w = self._widgets([sc])
            if w:
                self._scroll_to_element(w[0])
        # On redessine l'anneau une fois la mise en page stabilisée (le défilement
        # peut prendre une image ou deux).
        self.canvas.after.clear()
        Clock.schedule_once(lambda dt: self._draw_ring(stop["targets"]), 0.05)
        Clock.schedule_once(lambda dt: self._draw_ring(stop["targets"]), 0.18)

    def _draw_ring(self, names):
        self.canvas.after.clear()
        ws = self._widgets(names)
        if not ws:
            return
        xs, ys, xe, ye = [], [], [], []
        for w in ws:
            wx, wy = w.to_window(w.x, w.y)
            xs.append(wx)
            ys.append(wy)
            xe.append(wx + w.width)
            ye.append(wy + w.height)
        pad = S(8)
        x0, y0 = min(xs) - pad, min(ys) - pad
        x1, y1 = max(xe) + pad, max(ye) + pad
        with self.canvas.after:
            Color(0.90, 0.22, 0.22, 1)
            Line(rounded_rectangle=(x0, y0, x1 - x0, y1 - y0, S(10)), width=3)

    def _next(self):
        if self.idx < len(self.stops) - 1:
            self.idx += 1
            self._show_stop()
        else:
            try:
                save_config(tuto_seen="1")
            except Exception:
                pass
            self._close()

    def _prev(self):
        if self.idx > 0:
            self.idx -= 1
            self._show_stop()
        else:
            self._close()
            try:
                self.tuto._return_from_menu_tour()
            except Exception:
                pass

    def _close(self):
        try:
            self.menu._menu_scroll.unbind(scroll_y=self._on_scroll)
        except Exception:
            pass
        self.canvas.after.clear()
        if self.parent:
            self.parent.remove_widget(self)


class MenuScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.target  = 5
        self.cadence = 15
        self._build()

    def _build(self):
        root = FloatLayout()
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
            # Thème médiéval : fond image, largeur calée sur l'écran
            self._bg_stone_col = Color(1, 1, 1, 1)
            tex = _theme_bg_texture("fond.png") if _theme_image_dir(CURRENT_THEME) else None
            if tex:
                pos, size = _fit_menu_bg(tex, Window.width, Window.height)
            else:
                pos, size = (0, 0), (0, 0)
                self._bg_stone_col.a = 0
            self._bg_stone = Rectangle(texture=tex, pos=pos, size=size)
            # Thème fleur : filigrane blanchâtre par-dessus le fond pour que les
            # écritures du menu restent bien lisibles.
            self._bg_veil_col = Color(1, 1, 1, 0)
            self._bg_veil = Rectangle(pos=(0, 0), size=Window.size)
            if CURRENT_THEME == "fleur" and tex:
                self._bg_veil_col.rgba = (1, 1, 1, 0.45)
        self._menu_canvas_before = root.canvas.before
        def _sync_bg(*a):
            self._bg.size = Window.size
            self._bg_veil.size = Window.size
            t = self._bg_stone.texture
            if t:
                p, s = _fit_menu_bg(t, Window.width, Window.height)
                self._bg_stone.pos = p
                self._bg_stone.size = s
        Window.bind(size=lambda *a: _sync_bg())

        # ── Menu défilant ──
        # Tout est proportionnel à la hauteur d'écran (H). Le contenu interne a
        # une hauteur totale = facteur × H ; s'il dépasse l'écran, on défile.
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True,
                            bar_width=S(4))
        self._menu_scroll = scroll   # référence pour réinitialiser au resume
        # Conteneur vertical : sa hauteur s'ajuste à la somme de ses enfants.
        col = BoxLayout(orientation="vertical", size_hint=(1, None),
                        spacing=S(6), padding=(0, 0))
        col.bind(minimum_height=col.setter("height"))

        H = Window.height  # référence pour les hauteurs proportionnelles

        def add_spacer(frac):
            col.add_widget(Widget(size_hint=(1, None), height=Window.height * frac))

        # Petit espace en haut (sous la zone du bouton Compte)
        add_spacer(0.06)

        # ── Titre "La Fuga" ──
        titre_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  "titre.png")
        if os.path.exists(titre_path):
            title = Image(source=titre_path, size_hint=(1, None),
                          height=Window.height * 0.16,
                          allow_stretch=True, keep_ratio=True)
        else:
            title = Label(text="La Fuga", font_size=SF("48sp"),
                          color=(0, 0, 0, 1), italic=True,
                          size_hint=(1, None), height=Window.height * 0.10)
        col.add_widget(title)

        # ── Logo ──
        self._logo_widget = Image(source=self._theme_logo_path(),
                                  size_hint=(1, None), height=Window.height * 0.13,
                                  allow_stretch=True, keep_ratio=True)
        col.add_widget(self._logo_widget)

        add_spacer(0.02)

        # ── Objectif ──
        col.add_widget(Label(text="Objectif", font_size=SF("17sp"),
                             color=(0.15, 0.15, 0.15, 1), bold=True,
                             size_hint=(1, None), height=Window.height * 0.04))
        obj_row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                            height=Window.height * 0.05, spacing=S(6),
                            padding=(S(14), 0))
        self.pts_btns = {}
        for v in ["partie", 3, 5, 7, "flash"]:
            if v == "partie":   label = "Partie"
            elif v == "flash":  label = "Flash"
            else:               label = str(v)
            b = RoundButton(text=label, font_size=SF("12sp"), bold=True,
                            color=(1, 1, 1, 1), size_hint=(1, 1))
            b.bind(on_release=lambda btn, val=v: self._set_pts(val))
            self.pts_btns[v] = b
            obj_row.add_widget(b)
        self._obj_row = obj_row
        col.add_widget(obj_row)

        add_spacer(0.015)

        # ── Cadence ──
        col.add_widget(Label(text="Cadence (min / joueur)", font_size=SF("17sp"),
                             color=(0.15, 0.15, 0.15, 1), bold=True,
                             size_hint=(1, None), height=Window.height * 0.04))
        cad_row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                            height=Window.height * 0.05, spacing=S(6),
                            padding=(S(14), 0))
        self.cad_btns = {}
        for v in [5, 15, 30, "zen"]:
            label = f"{v} min" if v != "zen" else "Zen"
            b = RoundButton(text=label, font_size=SF("13sp"), bold=True,
                            color=(1, 1, 1, 1), size_hint=(1, 1))
            b.bind(on_release=lambda btn, val=v: self._set_cad(val))
            self.cad_btns[v] = b
            cad_row.add_widget(b)
        self._cad_row = cad_row
        col.add_widget(cad_row)

        add_spacer(0.02)

        # ── Boutons principaux ──
        def main_btn(text, bg, cb):
            b = RoundButton(text=text, font_size=SF("16sp"), bold=True,
                            bg_color=bg, color=(1, 1, 1, 1),
                            size_hint=(0.7, None), height=Window.height * 0.06,
                            pos_hint={"center_x": 0.5})
            b.bind(on_release=cb)
            wrap = AnchorLayout(size_hint=(1, None), height=Window.height * 0.06)
            wrap.add_widget(b)
            col.add_widget(wrap)
            return b

        self._btn_local = main_btn("Jouer en local", COL_ORANGE, self._start_local)
        add_spacer(0.012)

        # ── Ligne "Jouer en ligne" + recherche + favoris ──
        # Bouton "Jouer en ligne" (matchmaking)
        self._btn_online = main_btn("Jouer en ligne", COL_BLUE, self._on_play_online)
        add_spacer(0.012)

        # Barre de recherche de joueurs + bouton favoris
        search_row = BoxLayout(orientation="horizontal", size_hint=(0.7, None),
                               height=Window.height * 0.05, spacing=S(6),
                               pos_hint={"center_x": 0.5})
        self.search_input = TextInput(
            hint_text="Rechercher un joueur…",
            multiline=False, size_hint=(1, 1),
            font_size=SF("14sp"),
            background_color=COL_BTN_GREY,        # fond gris
            foreground_color=(1, 1, 1, 1),        # texte blanc
            hint_text_color=(0.8, 0.8, 0.8, 1),   # placeholder gris clair
            cursor_color=(1, 1, 1, 1),
            padding=(S(12), S(10)))
        self.search_input.bind(on_text_validate=self._on_search_player)
        fav_btn = StarButton(star_color=(1, 0.85, 0.3, 1), filled=True,
                             bg_color=COL_BTN_GREY,
                             size_hint=(None, 1), radius=S(12))
        fav_btn.bind(height=lambda b, h: setattr(b, "width", h))
        fav_btn.bind(on_release=self._on_favorites)
        self._btn_fav = fav_btn
        search_wrap = BoxLayout(size_hint=(1, None), height=Window.height * 0.05)
        search_row.add_widget(self.search_input)
        search_row.add_widget(fav_btn)
        sw = AnchorLayout(size_hint=(1, None), height=Window.height * 0.05)
        sw.add_widget(search_row)
        col.add_widget(sw)
        add_spacer(0.012)

        self._btn_ai = main_btn("Jouer contre deep grey", COL_BTN_GREY, self._start_vs_ai)
        add_spacer(0.012)
        self._btn_plus = main_btn("Plus", COL_BTN_GREY, self._open_plus_popup)

        add_spacer(0.02)

        # ── Parties par correspondance : 4 emplacements (2×2) ──
        # Chaque case a la FORME du plateau (ratio 7 colonnes : 8 rangées).
        corr_header = BoxLayout(orientation="horizontal", size_hint=(1, None),
                                height=Window.height * 0.04, spacing=S(8))
        corr_header.add_widget(Label(text="Parties par correspondance",
                                     font_size=SF("15sp"),
                                     color=(0.15, 0.15, 0.15, 1), bold=True,
                                     halign="left", valign="middle"))
        corr_refresh = RoundButton(text="Actualiser", bg_color=COL_BLUE,
                                   color=(1, 1, 1, 1), font_size=SF("12sp"),
                                   bold=True, size_hint=(None, 1), width=S(100),
                                   radius=S(12))
        corr_refresh.bind(on_release=lambda *a: self._refresh_corr_games())
        corr_header.add_widget(corr_refresh)
        self._corr_header = corr_header
        col.add_widget(corr_header)
        self.corr_slots = []
        grid = GridLayout(cols=2, size_hint=(None, None), spacing=S(10))

        def _sync_corr_grid(*a):
            # Largeur de la grille = 80% de l'écran ; 6 cases en 3 rangées de 2.
            gw_w = Window.width * 0.8
            spacing = S(10)
            slot_w = (gw_w - spacing) / 2          # largeur d'une case
            slot_h = slot_w * 8.0 / 7.0            # hauteur = ratio plateau 7:8
            grid.cols = 2
            grid.width = gw_w
            grid.height = slot_h * 3 + spacing * 2   # 3 rangées
            for s in self.corr_slots:
                s.size_hint = (None, None)
                s.width = slot_w
                s.height = slot_h

        for i in range(6):
            slot = self._make_corr_slot(i)
            self.corr_slots.append(slot)
            grid.add_widget(slot)
        _sync_corr_grid()
        Window.bind(size=lambda *a: _sync_corr_grid())

        gw = AnchorLayout(size_hint=(1, None))
        # La hauteur du wrapper suit celle de la grille
        grid.bind(height=lambda inst, h: setattr(gw, "height", h + S(10)))
        gw.height = grid.height + S(10)
        gw.add_widget(grid)
        col.add_widget(gw)

        add_spacer(0.03)

        scroll.add_widget(col)
        root.add_widget(scroll)

        # ── Éléments fixes par-dessus (ne défilent pas) ──
        # Pseudo + mélo en haut à gauche
        self.online_info_lbl = Label(text="", font_size=SF("13sp"), bold=True,
                                     color=(0.1, 0.1, 0.1, 1),
                                     halign="left", valign="middle",
                                     size_hint=(0.45, 0.06),
                                     pos_hint={"x": 0.03, "top": 0.995})
        self.online_info_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        root.add_widget(self.online_info_lbl)

        # Bouton "Compte" en haut à droite (un peu plus haut pour tenir le
        # pseudo + le Mélo sur deux lignes une fois connecté).
        self.account_btn = RoundButton(text="Compte", font_size=SF("12sp"), bold=True,
                                       bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                                       size_hint=(0.2, 0.05),
                                       pos_hint={"right": 0.97, "top": 0.985})
        self.account_btn.bind(on_release=self._on_account_press)
        root.add_widget(self.account_btn)

        # Interrupteur "Random" en haut à gauche (variante Random Fuga). Allumé =
        # chaque partie démarre sur une position aléatoire. Couleur claire du
        # thème quand actif.
        self.random_btn = RoundButton(text="Random", font_size=SF("12sp"),
                                      bold=True, bg_color=COL_BTN_GREY,
                                      color=(1, 1, 1, 1), size_hint=(0.2, 0.05),
                                      pos_hint={"x": 0.03, "top": 0.985})
        self.random_btn.bind(on_release=self._on_random_toggle)
        root.add_widget(self.random_btn)
        self._refresh_random_btn()

        self.add_widget(root)
        self._refresh()

    def start_menu_tour(self, tuto_screen):
        """Lance la visite guidée du menu (calque-guide par-dessus le vrai menu)."""
        try:
            self._refresh()
        except Exception:
            pass
        # Remettre le menu tout en haut, puis afficher le calque.
        try:
            self._menu_scroll.scroll_y = 1
        except Exception:
            pass
        ov = MenuTourOverlay(self, tuto_screen)
        self.add_widget(ov)

    def _make_corr_slot(self, index):
        """Crée un emplacement de correspondance : mini-plateau dessiné (canvas)
        + un overlay (FloatLayout) pour le texte (noms, score) et les boutons
        (accepter/refuser/etc.) affichés PAR-DESSUS le plateau."""
        slot = ClickableRow(on_press_cb=lambda idx=index: self._on_corr_slot(idx),
                            orientation="vertical", size_hint=(1, 1))
        slot._game_data = None   # dict serveur (statut, adversaire, score, moves_text...) ou None
        slot._index = index
        # Overlay pour le texte et les boutons (transparent, par-dessus)
        overlay = FloatLayout(size_hint=(1, 1))
        slot.add_widget(overlay)
        slot._overlay = overlay

        def _redraw_slot(*a):
            slot.canvas.before.clear()
            gd = slot._game_data
            statut = gd.get("statut") if gd else None
            my_turn = bool(gd and gd.get("my_turn"))
            COLS_, ROWS_ = 7, 8
            pad = min(slot.width, slot.height) * 0.08
            avail_w = slot.width - 2 * pad
            avail_h = slot.height - 2 * pad
            cell = min(avail_w / COLS_, avail_h / ROWS_)
            bw = cell * COLS_
            bh = cell * ROWS_
            bx = slot.x + (slot.width - bw) / 2
            by = slot.y + (slot.height - bh) / 2
            with slot.canvas.before:
                # Fond de la case : surligné orange si c'est à NOUS de jouer
                Color(*(COL_ORANGE if my_turn else COL_BTN_GREY))
                RoundedRectangle(pos=slot.pos, size=slot.size, radius=[S(10)])
                # Fond du plateau
                Color(*COL_BG_MENU)
                RoundedRectangle(pos=(bx, by), size=(bw, bh), radius=[S(4)])
                # Quadrillage
                Color(0.1, 0.1, 0.1, 0.5)
                for c in range(COLS_ + 1):
                    x = bx + c * cell
                    Line(points=[x, by, x, by + bh], width=1)
                for r in range(ROWS_ + 1):
                    y = by + r * cell
                    Line(points=[bx, y, bx + bw, y], width=1)
            # Pièces : reconstruites depuis moves_text (partie en cours), ou
            # position de départ (défi pas encore accepté). Rien si case vide.
            board = None
            if gd and statut in ("en_cours", "defi"):
                board = self._corr_board_from_moves(gd.get("moves_text", ""),
                                                    random_code=gd.get("random_code"))
            if board:
                for c in range(COLS_):
                    for r in range(ROWS_):
                        p = board[c][r] if c < len(board) and r < len(board[c]) else None
                        if not p:
                            continue
                        px = bx + c * cell
                        py = by + r * cell
                        draw_piece(slot.canvas.before, px, py, cell, p,
                                   outline=None, outline_w=1, flipped=True)
            # Reconstruire l'overlay (texte + boutons)
            self._build_corr_overlay(slot)
        slot.bind(pos=_redraw_slot, size=_redraw_slot)
        slot._redraw_slot = _redraw_slot
        return slot

    def _build_corr_overlay(self, slot):
        """(Re)construit le texte et les boutons affichés par-dessus le plateau
        d'une case de correspondance, selon son état."""
        overlay = slot._overlay
        overlay.clear_widgets()
        gd = slot._game_data
        if not gd:
            return   # case vide : rien par-dessus
        statut = gd.get("statut")
        adv = gd.get("adversaire", "?")
        mon_score = gd.get("mon_score", 0)
        score_adv = gd.get("score_adverse", 0)
        mode_txt = "Random" if gd.get("random_code") else "Standard"

        # Bandeau du haut : adversaire + mode (random/standard) + score
        top_lbl = Label(text="[b]%s[/b]\n%s · %d - %d"
                             % (adv, mode_txt, mon_score, score_adv),
                        markup=True, font_size=SF("12sp"),
                        color=(1, 1, 1, 1), halign="center", valign="top",
                        size_hint=(0.9, 0.22), pos_hint={"center_x": 0.5, "top": 0.99})
        top_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        # Fond semi-transparent derrière le texte pour la lisibilité
        with top_lbl.canvas.before:
            Color(0, 0, 0, 0.45)
            top_lbl._bg = RoundedRectangle(radius=[S(6)])
        def _sync_bg(w, *a):
            w._bg.pos = w.pos; w._bg.size = w.size
        top_lbl.bind(pos=_sync_bg, size=_sync_bg)
        overlay.add_widget(top_lbl)

        if statut == "defi":
            is_defieur = gd.get("is_defieur", False)
            if is_defieur:
                # J'ai lancé le défi : "en attente" + Annuler
                wait = Label(text="En attente…", font_size=SF("11sp"),
                             color=(1, 1, 1, 1), halign="center",
                             size_hint=(0.9, 0.15),
                             pos_hint={"center_x": 0.5, "center_y": 0.5})
                wait.bind(size=lambda w, s: setattr(w, "text_size", s))
                overlay.add_widget(wait)
                annul = RoundButton(text="Annuler", bg_color=(0.55, 0.1, 0.1, 1),
                                    color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                                    size_hint=(0.6, 0.16),
                                    pos_hint={"center_x": 0.5, "y": 0.06})
                annul.bind(on_release=lambda *a, g=gd: self._corr_cancel_defi(g))
                overlay.add_widget(annul)
            else:
                # On me défie : "X vous défie !" + Mélo du défieur + Accepter/Refuser
                defi_melo = gd.get("adversaire_melo", 1500)
                rnd_txt = "\nRandom Fuga" if gd.get("random_code") else ""
                msg = Label(text="vous défie !\nMélo %d%s" % (defi_melo, rnd_txt),
                            font_size=SF("10sp"), bold=True,
                            color=(1, 1, 1, 1), halign="center",
                            size_hint=(0.9, 0.16),
                            pos_hint={"center_x": 0.5, "center_y": 0.54})
                msg.bind(size=lambda w, s: setattr(w, "text_size", s))
                overlay.add_widget(msg)
                acc = RoundButton(text="Accepter", bg_color=COL_BLUE,
                                  color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                                  size_hint=(0.8, 0.15),
                                  pos_hint={"center_x": 0.5, "y": 0.24})
                acc.bind(on_release=lambda *a, g=gd: self._corr_accept(g))
                overlay.add_widget(acc)
                ref = RoundButton(text="Refuser", bg_color=(0.55, 0.1, 0.1, 1),
                                  color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                                  size_hint=(0.8, 0.15),
                                  pos_hint={"center_x": 0.5, "y": 0.06})
                ref.bind(on_release=lambda *a, g=gd: self._corr_refuse(g))
                overlay.add_widget(ref)
        elif statut == "en_cours":
            # Statut clair du tour, visible directement dans l'aperçu (sans avoir
            # à ouvrir la partie), comme "En attente…" pour les défis.
            if gd.get("my_turn"):
                txt = "À vous de jouer"
                col = (1, 1, 1, 1)
            else:
                txt = "À votre adversaire\nde jouer"
                col = (0.9, 0.9, 0.9, 1)
            turn_lbl = Label(text=txt, font_size=SF("11sp"), bold=True,
                             color=col, halign="center", valign="middle",
                             size_hint=(0.92, 0.2),
                             pos_hint={"center_x": 0.5, "y": 0.04})
            turn_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            # Petit fond sombre pour la lisibilité par-dessus le plateau
            with turn_lbl.canvas.before:
                Color(0, 0, 0, 0.45)
                turn_lbl._bg = RoundedRectangle(radius=[S(6)])
            def _sync_turn_bg(w, *a):
                w._bg.pos = w.pos; w._bg.size = w.size
            turn_lbl.bind(pos=_sync_turn_bg, size=_sync_turn_bg)
            overlay.add_widget(turn_lbl)

        elif statut == "termine":
            # Résultat de la partie + boutons Revanche / Fermer
            gagne = gd.get("gagne")
            if gagne is True:
                res_txt = "Gagné !"; res_col = (0.5, 0.9, 0.5, 1)
            elif gagne is False:
                res_txt = "Perdu"; res_col = (0.95, 0.5, 0.5, 1)
            else:
                res_txt = "Nulle"; res_col = (0.9, 0.9, 0.6, 1)
            res_lbl = Label(text=res_txt, font_size=SF("14sp"), bold=True,
                            color=res_col, halign="center", valign="middle",
                            size_hint=(0.9, 0.18),
                            pos_hint={"center_x": 0.5, "center_y": 0.5})
            res_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            with res_lbl.canvas.before:
                Color(0, 0, 0, 0.5)
                res_lbl._bg = RoundedRectangle(radius=[S(6)])
            res_lbl.bind(pos=lambda w, *a: setattr(w._bg, "pos", w.pos),
                         size=lambda w, *a: setattr(w._bg, "size", w.size))
            overlay.add_widget(res_lbl)
            rev = RoundButton(text="Revanche", bg_color=COL_BLUE,
                              color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                              size_hint=(0.8, 0.15),
                              pos_hint={"center_x": 0.5, "y": 0.22})
            rev.bind(on_release=lambda *a, g=gd: self._corr_revanche(g))
            overlay.add_widget(rev)
            ferm = RoundButton(text="Fermer", bg_color=COL_BTN_GREY,
                               color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                               size_hint=(0.8, 0.15),
                               pos_hint={"center_x": 0.5, "y": 0.05})
            ferm.bind(on_release=lambda *a, g=gd: self._corr_fermer(g))
            overlay.add_widget(ferm)

    def _corr_board_from_moves(self, moves_text, random_code=None):
        """Reconstruit le plateau d'une partie de correspondance en rejouant les
        notations sur l'écran de jeu réel (instance dédiée au calcul), puis
        renvoie une COPIE du board. Fallback : position de départ. random_code :
        si la partie est en Random Fuga, la position de départ est celle du code
        (et non la standard).

        IMPORTANT (anti 'comptes collés') : on sauvegarde l'état de l'écran de
        jeu AVANT de rejouer, et on le restaure TOUJOURS (try/finally), pour ne
        jamais laisser un état résiduel mélanger les parties."""
        # Position de départ (toujours disponible comme fallback), DOIT
        # correspondre exactement à _setup_pieces (placement actuel du jeu).
        def _start_board():
            b = [[None] * ROWS for _ in range(COLS)]
            layout = ["Soldat", "Garde", "Soldat", "Chevalier", "Garde", "Soldat", "Garde"]
            for c, t in enumerate(layout):
                b[c][0] = {"type": t, "camp": "Blanc"}
                b[c][7] = {"type": t, "camp": "Noir"}
            for c in [1, 2, 4, 5]:
                b[c][1] = {"type": "Nurse", "camp": "Blanc"}
                b[c][6] = {"type": "Nurse", "camp": "Noir"}
            b[3][1] = {"type": "Héritier", "camp": "Blanc"}
            b[3][6] = {"type": "Héritier", "camp": "Noir"}
            # Pièces supplémentaires (mêmes que _setup_pieces)
            b[0][1] = {"type": "Garde",  "camp": "Blanc"}
            b[6][1] = {"type": "Soldat", "camp": "Blanc"}
            b[0][6] = {"type": "Garde",  "camp": "Noir"}
            b[6][6] = {"type": "Soldat", "camp": "Noir"}
            # Colonne fa : Héritier (fa1), Nurse (fa2), Chevalier (fa3) + miroir
            b[3][0] = {"type": "Héritier",  "camp": "Blanc"}
            b[3][1] = {"type": "Nurse",     "camp": "Blanc"}
            b[3][2] = {"type": "Chevalier", "camp": "Blanc"}
            b[3][7] = {"type": "Héritier",  "camp": "Noir"}
            b[3][6] = {"type": "Nurse",     "camp": "Noir"}
            b[3][5] = {"type": "Chevalier", "camp": "Noir"}
            return b
        # Position de départ EFFECTIVE : random si code fourni, sinon standard.
        def _base_board():
            if random_code:
                rb = rf_build_board(random_code)
                if rb is not None:
                    return rb
            return _start_board()
        if not (moves_text or "").strip():
            return _base_board()
        # Rejouer les coups sur l'écran de jeu réel (sans affecter l'UI).
        g = None
        saved = None
        try:
            g = self.manager.get_screen("game")
        except Exception:
            return _base_board()
        # GARDE CRITIQUE (anti-corruption) : on n'emprunte l'écran de jeu QUE si
        # on est actuellement sur le menu. Si une partie est en cours ailleurs
        # (en direct, contre l'IA, ou une correspondance ouverte), l'écran de jeu
        # est affiché/actif : échanger temporairement son plateau pour
        # reconstruire un aperçu corromprait la partie. Les aperçus ne sont de
        # toute façon visibles que depuis le menu, donc hors menu on renvoie la
        # position de départ.
        try:
            if self.manager is None or self.manager.current != "menu":
                return _base_board()
        except Exception:
            return _base_board()
        # Sauvegarder l'état courant de l'écran de jeu
        try:
            saved = {
                "board": [[dict(p) if p else None for p in col] for col in g.board]
                         if getattr(g, "board", None) else None,
                "turn": getattr(g, "turn", "Blanc"),
                "blanc_fugued": getattr(g, "blanc_fugued", False),
                "fugued_heirs": [dict(h) for h in getattr(g, "fugued_heirs", [])],
                "captured": {k: list(v) for k, v in
                             getattr(g, "captured", {"Blanc": [], "Noir": []}).items()},
            }
        except Exception:
            saved = None
        result = None
        try:
            # Repartir d'une position de départ propre, puis rejouer le NMC
            g.board = _base_board()
            g.turn = "Blanc"; g.blanc_fugued = False; g.fugued_heirs = []
            g.captured = {"Blanc": [], "Noir": []}
            for nota in moves_text.split("\n"):
                nota = nota.strip()
                if nota:
                    try: g._apply_notation(nota)
                    except Exception: pass
            result = [[dict(p) if p else None for p in col] for col in g.board]
        except Exception:
            result = None
        finally:
            # TOUJOURS restaurer l'état précédent de l'écran de jeu (même en cas
            # d'erreur), sinon un état résiduel pourrait "coller" entre parties.
            if saved is not None:
                try:
                    if saved["board"] is not None:
                        g.board = saved["board"]
                    g.turn = saved["turn"]
                    g.blanc_fugued = saved["blanc_fugued"]
                    g.fugued_heirs = saved["fugued_heirs"]
                    g.captured = saved["captured"]
                except Exception:
                    pass
        return result if result is not None else _base_board()

    def set_corr_game(self, index, game_data):
        """Associe une partie par correspondance à l'emplacement donné.
        game_data : dict serveur (statut, adversaire, mon_score, score_adverse,
        moves_text, my_turn, is_defieur...). None pour vider."""
        if not hasattr(self, "corr_slots") or index >= len(self.corr_slots):
            return
        slot = self.corr_slots[index]
        slot._game_data = game_data
        if hasattr(slot, "_redraw_slot"):
            slot._redraw_slot()

    def _refresh_corr_games(self):
        """Charge les parties de correspondance depuis le serveur et remplit les
        6 slots. Les parties au-delà de 6 (rare) sont ignorées ; les slots non
        utilisés sont vidés."""
        if not ONLINE.is_logged_in():
            for i in range(len(getattr(self, "corr_slots", []))):
                self.set_corr_game(i, None)
            return

        def on_games(games, err):
            n = len(getattr(self, "corr_slots", []))
            if err or not games:
                games = games or []
            for i in range(n):
                self.set_corr_game(i, games[i] if i < len(games) else None)
        ONLINE.corr_list(on_games)

    # ── Callbacks online ────────────────────────────────────────────────────
    def _on_play_online(self, *a):
        """Matchmaking : se connecter au serveur, s'abonner aux événements, puis
        lancer la recherche d'un adversaire (même objectif + cadence)."""
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        # Ici, on ne s'abonne QU'aux événements du matchmaking (gérés par le
        # menu). Les événements de JEU (coup adverse, fin, etc.) sont enregistrés
        # plus tard par _on_partie_trouvee, vers le GameScreen (qui gère le
        # plateau), sinon on référencerait des méthodes absentes du menu.
        ONLINE.on_event("partie_trouvee", self._on_partie_trouvee)
        ONLINE.on_event("recherche_timeout", self._on_recherche_timeout)

        # Popup "Recherche d'un adversaire…" avec bouton Annuler
        content = BoxLayout(orientation="vertical", spacing=S(14), padding=S(20))
        lbl = Label(text="Recherche d'un adversaire…\n\nObjectif : %s\nCadence : %s"
                         % (self._fmt_objectif(), self._fmt_cadence()),
                    color=(1, 1, 1, 1), halign="center", valign="middle",
                    font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        btn_cancel = RoundButton(text="Annuler", bg_color=COL_BTN_GREY,
                                 color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                                 size_hint=(1, 0.35))
        content.add_widget(btn_cancel)
        self._search_popup = Popup(title="", content=content,
                                   size_hint=(0.82, 0.42), separator_height=0,
                                   auto_dismiss=False)
        self._search_lbl = lbl

        def _cancel(*_a):
            ONLINE.annuler_recherche()
            try: self._search_popup.dismiss()
            except Exception: pass
        btn_cancel.bind(on_release=_cancel)
        self._search_popup.open()

        # Se connecter au serveur, puis lancer la recherche
        def _ready(success, msg):
            if not success:
                self._search_lbl.text = "Connexion impossible :\n%s" % msg
                return
            ONLINE.chercher_partie(self.target, self.cadence)
        ONLINE.sio_connect(on_ready=_ready)

    def _on_recherche_timeout(self, data):
        """Le serveur signale une longue attente (on reste en file)."""
        if hasattr(self, "_search_lbl"):
            self._search_lbl.text = ("Toujours en recherche…\n\n"
                                     "Essayez une autre cadence si l'attente\n"
                                     "se prolonge.")


    def _on_partie_trouvee(self, data):
        """Un adversaire a été trouvé : fermer le popup, basculer sur l'écran de
        jeu et y démarrer la partie en ligne. Les événements de JEU (coup adverse,
        fin, déconnexion, nulle) sont réenregistrés pour pointer vers le
        GameScreen, qui est celui qui manipule le plateau."""
        try:
            if hasattr(self, "_search_popup"):
                self._search_popup.dismiss()
        except Exception:
            pass
        # Fermer aussi les popups de défi (côté défieur et côté cible)
        for attr in ("_defi_popup", "_defi_recu_popup"):
            try:
                p = getattr(self, attr, None)
                if p is not None:
                    p.dismiss()
                    setattr(self, attr, None)
            except Exception:
                pass
        game_id   = data.get("game_id")
        couleur   = data.get("couleur", "Blanc")     # MA couleur
        adversaire = data.get("adversaire", "Adversaire")
        opp_melo  = data.get("adversaire_melo", 1500)
        objectif  = data.get("objectif", self.target)
        cadence   = data.get("cadence", self.cadence)
        score_moi = data.get("score_moi", 0)
        score_adv = data.get("score_adversaire", 0)
        last_chance = data.get("last_chance", False)
        random_code = data.get("random_code")   # None si partie standard
        # Récupérer l'écran de jeu (c'est lui qui gère le plateau)
        game = self.manager.get_screen("game")
        # Si on enchaîne une partie suivante d'un match : fermer le popup
        # "Partie suivante" et arrêter son compte à rebours.
        if getattr(game, "_next_popup", None) is not None:
            try: game._next_popup.dismiss()
            except Exception: pass
            game._next_popup = None
        if hasattr(game, "_cancel_next_timer"):
            game._cancel_next_timer()
        # Réenregistrer les handlers de JEU vers le GameScreen
        ONLINE.on_event("coup_adverse", game._on_coup_adverse)
        ONLINE.on_event("partie_terminee", game._on_partie_terminee_remote)
        ONLINE.on_event("adversaire_deconnecte", game._on_adversaire_deconnecte)
        ONLINE.on_event("adversaire_revenu", game._on_adversaire_revenu)
        ONLINE.on_event("nulle_proposee", game._on_nulle_proposee_remote)
        ONLINE.on_event("melo_maj", game._on_melo_maj)
        ONLINE.on_event("chat_recu", game._on_chat_recu)
        ONLINE.on_event("adversaire_pret", game._on_adversaire_pret)
        ONLINE.on_event("match_abandonne", game._on_match_abandonne)
        ONLINE.on_event("match_continue", game._on_match_continue)
        ONLINE.on_event("match_over", game._on_match_over)
        # Démarrer la partie sur l'écran de jeu, puis basculer dessus
        game.start_match_online(game_id, couleur, adversaire, opp_melo,
                                objectif, cadence, score_moi=score_moi,
                                score_adv=score_adv, last_chance=last_chance,
                                random_code=random_code)
        self.manager.current = "game"

    def _online_unavailable_popup(self):
        """Affiche un message indiquant que le mode en ligne n'est pas disponible."""
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
        lbl = Label(text="Le mode en ligne n'est pas\nencore disponible.",
                    color=(1, 1, 1, 1), halign="center", valign="middle",
                    font_size=SF("16sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        btn = RoundButton(text="OK", bg_color=COL_BLUE, color=(1, 1, 1, 1),
                          font_size=SF("15sp"), bold=True, size_hint=(1, 0.4))
        content.add_widget(btn)
        p = Popup(title="", content=content, size_hint=(0.8, 0.4),
                  separator_height=0)
        btn.bind(on_release=lambda *a: p.dismiss())
        p.open()

    def _fmt_objectif(self):
        if self.target == "partie": return "Partie unique"
        if self.target == "flash":  return "Flash"
        return str(self.target)

    def _fmt_cadence(self):
        return "Zen" if self.cadence == "zen" else "%s min" % self.cadence

    def _on_search_player(self, *a):
        """Recherche un joueur par pseudo exact, puis affiche sa fiche (avec le
        bouton Défier). Nécessite d'être connecté à un compte."""
        query = self.search_input.text.strip()
        if not query:
            return
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        # S'assurer d'être connecté au serveur temps réel (pour pouvoir défier)
        ONLINE.sio_connect(on_ready=lambda ok, msg: None)

        def on_result(res, err):
            if err:
                self._popup_simple("Recherche", "Erreur : %s" % err)
                return
            if not res or not res.get("found"):
                self._popup_simple("Recherche",
                                   "Aucun joueur nommé « %s »." % query)
                return
            if res.get("is_self"):
                self._popup_simple("Recherche", "C'est vous !")
                return
            self._show_player_card(res)
        ONLINE.search_user(query, on_result)

    def _popup_simple(self, title, message):
        Popup(title=title,
              content=Label(text=message, color=(1, 1, 1, 1), halign="center"),
              size_hint=(0.8, 0.3)).open()

    def _show_player_card(self, res):
        """Affiche une fiche joueur trouvé : pseudo, mélo, en ligne, + boutons
        Défier et Enregistrer/Retirer favori."""
        pseudo = res.get("pseudo", "?")
        melo = res.get("melo", 1500)
        online = res.get("online", False)
        is_fav = res.get("is_favorite", False)
        statut = "En ligne" if online else "Hors ligne"
        statut_col = (0.2, 0.7, 0.2, 1) if online else (0.6, 0.6, 0.6, 1)

        content = BoxLayout(orientation="vertical", spacing=S(10), padding=S(16))
        content.add_widget(Label(text="[b]%s[/b]" % pseudo, markup=True,
                                 font_size=SF("20sp"), color=(1, 1, 1, 1),
                                 size_hint=(1, None), height=S(34)))
        content.add_widget(Label(text="Mélo : %d" % melo, font_size=SF("14sp"),
                                 color=(0.9, 0.9, 0.9, 1),
                                 size_hint=(1, None), height=S(24)))
        content.add_widget(Label(text=statut, font_size=SF("13sp"), bold=True,
                                 color=statut_col,
                                 size_hint=(1, None), height=S(22)))

        row = BoxLayout(size_hint=(1, None), height=S(48), spacing=S(8))
        defier_btn = RoundButton(text="Défier", bg_color=COL_BLUE,
                                 color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True)
        fav_btn = RoundButton(
            text="Retirer" if is_fav else "Enregistrer",
            bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
            font_size=SF("14sp"), bold=True)
        row.add_widget(defier_btn)
        row.add_widget(fav_btn)
        content.add_widget(row)
        close_btn = RoundButton(text="Fermer", bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("13sp"),
                                size_hint=(1, None), height=S(40))
        content.add_widget(close_btn)
        pop = Popup(title="", content=content, size_hint=(0.85, 0.5),
                    separator_height=0)
        close_btn.bind(on_release=lambda *a: pop.dismiss())

        # Défier : envoie un défi temps réel (objectif/cadence courants du menu).
        # Le serveur prévient la cible (defi_recu) ou renvoie defi_echec si elle
        # est hors-ligne. Si accepté, la partie démarre via partie_trouvee
        # (exactement comme un matchmaking).
        def _defier(*a):
            pop.dismiss()
            self._envoyer_defi(pseudo)
        defier_btn.bind(on_release=_defier)

        # Enregistrer / Retirer favori
        def _toggle_fav(*a):
            if is_fav:
                ONLINE.remove_favorite(pseudo,
                    lambda ok, e: self._popup_simple(
                        "Favoris", "%s retiré des favoris." % pseudo if ok
                        else "Erreur : %s" % e))
            else:
                ONLINE.add_favorite(pseudo,
                    lambda ok, e: self._popup_simple(
                        "Favoris", "%s ajouté aux favoris !" % pseudo if ok
                        else "Erreur : %s" % e))
            pop.dismiss()
        fav_btn.bind(on_release=_toggle_fav)
        pop.open()

    # ── Défi par recherche (comme le matchmaking, mais en choisissant la cible) ──
    def _bind_defi_handlers(self):
        """Abonne le menu aux événements de défi du serveur."""
        ONLINE.on_event("defi_envoye", self._on_defi_envoye)
        ONLINE.on_event("defi_echec", self._on_defi_echec)
        ONLINE.on_event("defi_refuse", self._on_defi_refuse)
        ONLINE.on_event("defi_recu", self._on_defi_recu)
        ONLINE.on_event("defi_annule", self._on_defi_annule)
        # Si le défi est accepté, la partie démarre via partie_trouvee
        ONLINE.on_event("partie_trouvee", self._on_partie_trouvee)
        ONLINE.on_event("recherche_timeout", self._on_recherche_timeout)

    def _envoyer_defi(self, pseudo_cible):
        """Envoie un défi à un joueur (objectif + cadence courants du menu)."""
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        self._bind_defi_handlers()
        self._defi_cible = pseudo_cible
        # Popup d'attente "Défi envoyé à X…" avec bouton Annuler
        content = BoxLayout(orientation="vertical", spacing=S(14), padding=S(20))
        lbl = Label(text="Défi envoyé à %s…\n\nObjectif : %s\nCadence : %s\n\n"
                         "En attente de sa réponse." %
                         (pseudo_cible, self._fmt_objectif(), self._fmt_cadence()),
                    color=(1, 1, 1, 1), halign="center", valign="middle",
                    font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        btn_cancel = RoundButton(text="Annuler", bg_color=COL_BTN_GREY,
                                 color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                                 size_hint=(1, 0.35))
        content.add_widget(btn_cancel)
        self._defi_popup = Popup(title="", content=content, size_hint=(0.82, 0.5),
                                 separator_height=0, auto_dismiss=False)
        self._defi_lbl = lbl

        def _cancel(*_a):
            did = getattr(self, "_defi_id", None)
            if did:
                try: ONLINE.annuler_defi(did)
                except Exception: pass
            try: self._defi_popup.dismiss()
            except Exception: pass
            self._defi_id = None
        btn_cancel.bind(on_release=_cancel)

        # Envoyer le défi quand on est bien connecté au serveur
        def _ready(ok, msg):
            if not ok:
                self._defi_lbl.text = "Connexion impossible :\n%s" % msg
                return
            try:
                ONLINE.defier(pseudo_cible, self.target, self.cadence)
            except Exception:
                self._defi_lbl.text = "Impossible d'envoyer le défi."
        ONLINE.sio_connect(on_ready=_ready)
        self._defi_popup.open()

    def _on_defi_envoye(self, data):
        """Le serveur confirme que le défi est bien parti (cible en ligne)."""
        self._defi_id = (data or {}).get("defi_id")
        # le popup d'attente est déjà affiché ; rien de plus à faire

    def _on_defi_echec(self, data):
        """La cible n'est pas disponible (hors-ligne) ou défi impossible."""
        raison = (data or {}).get("raison", "")
        try:
            if hasattr(self, "_defi_popup"):
                self._defi_popup.dismiss()
        except Exception:
            pass
        if raison == "soi_meme":
            msg = "Vous ne pouvez pas vous défier vous-même."
        else:
            msg = "Désolé, cet adversaire n'est pas disponible."
        self._popup_simple("Défi", msg)
        self._defi_id = None

    def _on_defi_refuse(self, data):
        """La cible a refusé le défi."""
        cible = (data or {}).get("cible", self._defi_cible if hasattr(self, "_defi_cible") else "L'adversaire")
        try:
            if hasattr(self, "_defi_popup"):
                self._defi_popup.dismiss()
        except Exception:
            pass
        self._popup_simple("Défi refusé", "%s a refusé votre défi." % cible)
        self._defi_id = None

    def _on_defi_annule(self, data):
        """Le défieur a annulé son défi (vu côté cible) : fermer le popup reçu."""
        try:
            if hasattr(self, "_defi_recu_popup"):
                self._defi_recu_popup.dismiss()
        except Exception:
            pass

    def _on_defi_recu(self, data):
        """On reçoit un défi d'un autre joueur : popup Accepter / Refuser."""
        defi_id = (data or {}).get("defi_id")
        defieur = (data or {}).get("defieur", "Un joueur")
        defieur_melo = (data or {}).get("defieur_melo", 1500)
        objectif = (data or {}).get("objectif", "partie")
        cadence = (data or {}).get("cadence", 15)
        # S'abonner aux événements de jeu/annulation (pour démarrer la partie)
        self._bind_defi_handlers()

        obj_txt = {"partie": "1 partie", "flash": "Flash",
                   2: "2 points", 3: "3 points", 5: "5 points"}.get(objectif, str(objectif))
        cad_txt = ("Zen (illimité)" if cadence == "zen" else "%s min" % cadence)
        rnd = bool((data or {}).get("random", False))
        extra = "\nMode : Random Fuga" if rnd else ""

        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
        lbl = Label(text="[b]%s[/b] (Mélo %d)\nvous défie !\n\nObjectif : %s\nCadence : %s%s"
                         % (defieur, defieur_melo, obj_txt, cad_txt, extra),
                    markup=True, color=(1, 1, 1, 1), halign="center",
                    valign="middle", font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        row = BoxLayout(orientation="horizontal", spacing=S(10), size_hint=(1, 0.4))
        acc = RoundButton(text="Accepter", bg_color=COL_BLUE, color=(1, 1, 1, 1),
                          font_size=SF("14sp"), bold=True)
        ref = RoundButton(text="Refuser", bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                          font_size=SF("14sp"), bold=True)
        row.add_widget(acc); row.add_widget(ref)
        content.add_widget(row)
        self._defi_recu_popup = Popup(title="", content=content,
                                      size_hint=(0.82, 0.5), separator_height=0,
                                      auto_dismiss=False)

        def _accept(*a):
            try: self._defi_recu_popup.dismiss()
            except Exception: pass
            try:
                ONLINE.repondre_defi(defi_id, True)
            except Exception:
                pass
            # La partie démarrera via partie_trouvee (envoyé par le serveur)
        def _refuse(*a):
            try: self._defi_recu_popup.dismiss()
            except Exception: pass
            try:
                ONLINE.repondre_defi(defi_id, False)
            except Exception:
                pass
        acc.bind(on_release=_accept)
        ref.bind(on_release=_refuse)
        self._defi_recu_popup.open()

    def _on_favorites(self, *a):
        """Ouvre la liste des favoris (pseudo + Mélo + état en ligne + Défier)."""
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        ONLINE.sio_connect(on_ready=lambda ok, msg: None)
        self._bind_defi_handlers()

        content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(10))
        title = Label(text="Mes favoris", font_size=SF("18sp"), bold=True,
                      color=(1, 1, 1, 1), size_hint=(1, None), height=S(40))
        content.add_widget(title)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._fav_box = BoxLayout(orientation="vertical", size_hint=(1, None),
                                  spacing=S(6), padding=(S(2), S(2)))
        self._fav_box.bind(minimum_height=self._fav_box.setter("height"))
        scroll.add_widget(self._fav_box)
        content.add_widget(scroll)
        close_btn = RoundButton(text="Fermer", bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                                size_hint=(1, None), height=S(46))
        content.add_widget(close_btn)
        self._fav_popup = Popup(title="", content=content, size_hint=(0.9, 0.8),
                                separator_height=0)
        close_btn.bind(on_release=lambda *a: self._fav_popup.dismiss())

        # Message de chargement
        loading = Label(text="Chargement…", color=(0.8, 0.8, 0.8, 1),
                        size_hint=(1, None), height=S(40))
        self._fav_box.add_widget(loading)

        def on_favs(favs, err):
            self._fav_box.clear_widgets()
            if err:
                self._fav_box.add_widget(Label(text="Erreur : %s" % err,
                    color=(1, 0.5, 0.5, 1), size_hint=(1, None), height=S(40)))
                return
            if not favs:
                self._fav_box.add_widget(Label(
                    text="Aucun favori pour le moment.\nCherchez un joueur pour "
                         "l'ajouter en favori.",
                    color=(0.8, 0.8, 0.8, 1), halign="center",
                    size_hint=(1, None), height=S(60)))
                return
            for fav in favs:
                self._fav_box.add_widget(self._make_fav_row(fav, self._fav_popup))
        ONLINE.list_favorites(on_favs)
        self._fav_popup.open()

    def _make_fav_row(self, fav, parent_popup):
        """Une ligne de favori : pseudo + mélo + état + bouton Défier (compacte,
        tout sur une seule ligne pour tenir dans la case)."""
        pseudo = fav.get("pseudo", "?")
        melo = fav.get("melo", 1500)
        online = fav.get("online", False)
        row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                        height=S(50), spacing=S(8), padding=(S(10), S(4)))
        with row.canvas.before:
            Color(*COL_BTN_GREY)
            row._r = RoundedRectangle(pos=row.pos, size=row.size, radius=[S(10)])
        row.bind(pos=lambda b, *a: setattr(b._r, "pos", b.pos),
                 size=lambda b, *a: setattr(b._r, "size", b.size))
        # Une seule ligne : "Pseudo · Mélo 1500 · en ligne". Le pseudo est tronqué
        # automatiquement (shorten) s'il est trop long, plutôt que de passer à la
        # ligne. Vert si en ligne, blanc sinon.
        etat = "  ·  en ligne" if online else ""
        nom_col = (0.55, 0.9, 0.55, 1) if online else (1, 1, 1, 1)
        info = Label(text="%s  ·  Mélo %d%s" % (pseudo, melo, etat),
                     font_size=SF("13sp"), bold=True, color=nom_col,
                     halign="left", valign="middle",
                     shorten=True, shorten_from="right",
                     size_hint=(1, 1))
        info.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(info)
        defier = RoundButton(text="Défier", bg_color=COL_BLUE, color=(1, 1, 1, 1),
                             font_size=SF("12sp"), bold=True,
                             size_hint=(None, 0.8), width=S(80),
                             pos_hint={"center_y": 0.5})
        def _defier(*a):
            parent_popup.dismiss()
            self._envoyer_defi(pseudo)
        defier.bind(on_release=_defier)
        row.add_widget(defier)
        return row

    def _on_corr_slot(self, index):
        """Clic sur une case de correspondance :
        - vide → choisir un favori à défier
        - partie 'en_cours' → ouvrir la partie pour jouer
        - 'defi' / 'termine' → géré par les boutons de l'overlay (accepter,
          refuser, annuler, revanche, fermer) ; le clic sur le corps ne fait rien.
        """
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        slot = self.corr_slots[index] if index < len(self.corr_slots) else None
        gd = slot._game_data if slot else None
        if gd is None:
            self._open_corr_defi_volet()
            return
        statut = gd.get("statut")
        if statut == "en_cours":
            self._open_corr_game(gd)
        # 'defi' / 'termine' : ne rien faire ici (les boutons s'en chargent)

    def _open_corr_defi_volet(self):
        """Volet pour défier un favori par correspondance (pas de cadence ni
        d'objectif : une partie unique, sans pendule)."""
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(10))
        title = Label(text="Défier un favori\n(par correspondance)",
                      font_size=SF("16sp"), bold=True, color=(1, 1, 1, 1),
                      halign="center", size_hint=(1, None), height=S(54))
        title.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(title)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        box = BoxLayout(orientation="vertical", size_hint=(1, None),
                        spacing=S(6), padding=(S(2), S(2)))
        box.bind(minimum_height=box.setter("height"))
        scroll.add_widget(box)
        content.add_widget(scroll)
        close_btn = RoundButton(text="Fermer", bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                                size_hint=(1, None), height=S(46))
        content.add_widget(close_btn)
        popup = Popup(title="", content=content, size_hint=(0.9, 0.8),
                      separator_height=0)
        close_btn.bind(on_release=lambda *a: popup.dismiss())

        box.add_widget(Label(text="Chargement…", color=(0.8, 0.8, 0.8, 1),
                             size_hint=(1, None), height=S(40)))

        def on_favs(favs, err):
            box.clear_widgets()
            if err:
                box.add_widget(Label(text="Erreur : %s" % err,
                    color=(1, 0.5, 0.5, 1), size_hint=(1, None), height=S(40)))
                return
            if not favs:
                box.add_widget(Label(
                    text="Aucun favori.\nAjoutez des favoris via la recherche.",
                    color=(0.8, 0.8, 0.8, 1), halign="center",
                    size_hint=(1, None), height=S(60)))
                return
            for fav in favs:
                box.add_widget(self._make_corr_defi_row(fav, popup))
        ONLINE.list_favorites(on_favs)
        popup.open()

    def _make_corr_defi_row(self, fav, parent_popup):
        """Ligne d'un favori dans le volet de défi par correspondance."""
        pseudo = fav.get("pseudo", "?")
        melo = fav.get("melo", 1500)
        online = fav.get("online", False)
        row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                        height=S(50), spacing=S(8), padding=(S(10), S(4)))
        with row.canvas.before:
            Color(*COL_BTN_GREY)
            row._r = RoundedRectangle(pos=row.pos, size=row.size, radius=[S(10)])
        row.bind(pos=lambda b, *a: setattr(b._r, "pos", b.pos),
                 size=lambda b, *a: setattr(b._r, "size", b.size))
        etat = "  ·  en ligne" if online else ""
        nom_col = (0.55, 0.9, 0.55, 1) if online else (1, 1, 1, 1)
        info = Label(text="%s  ·  Mélo %d%s" % (pseudo, melo, etat),
                     font_size=SF("13sp"), bold=True, color=nom_col,
                     halign="left", valign="middle",
                     shorten=True, shorten_from="right", size_hint=(1, 1))
        info.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(info)
        btn = RoundButton(text="Défier", bg_color=COL_BLUE, color=(1, 1, 1, 1),
                          font_size=SF("12sp"), bold=True,
                          size_hint=(None, 0.8), width=S(80),
                          pos_hint={"center_y": 0.5})

        def _defi(*a):
            parent_popup.dismiss()
            def on_done(result, err):
                if err or not (result and result.get("ok")):
                    msg = (result or {}).get("message") or err or "Échec du défi."
                    self._popup_simple("Correspondance", msg)
                else:
                    self._popup_simple("Correspondance",
                                       "Défi envoyé à %s !" % pseudo)
                self._refresh_corr_games()
            ONLINE.corr_defier(pseudo, "partie", on_done)
        btn.bind(on_release=_defi)
        row.add_widget(btn)
        return row

    def _corr_accept(self, gd):
        """Accepter un défi de correspondance reçu, puis ouvrir la partie."""
        gid = gd.get("id")
        def on_done(ok, err):
            if not ok:
                self._popup_simple("Correspondance", "Échec : %s" % (err or ""))
                self._refresh_corr_games()
                return
            # Recharger la liste puis ouvrir la partie fraîchement acceptée
            def on_games(games, err2):
                n = len(getattr(self, "corr_slots", []))
                for i in range(n):
                    self.set_corr_game(i, games[i] if games and i < len(games) else None)
                found = None
                for g in (games or []):
                    if g.get("id") == gid:
                        found = g; break
                if found and found.get("statut") == "en_cours":
                    self._open_corr_game(found)
            ONLINE.corr_list(on_games)
        ONLINE.corr_repondre(gid, True, on_done)

    def _corr_refuse(self, gd):
        """Refuser un défi de correspondance reçu."""
        def on_done(ok, err):
            self._refresh_corr_games()
        ONLINE.corr_repondre(gd.get("id"), False, on_done)

    def _corr_cancel_defi(self, gd):
        """Annuler un défi de correspondance que J'AI envoyé (avant acceptation).
        On réutilise l'abandon (qui supprime/clôt la partie au statut 'defi')."""
        def on_done(ok, err):
            self._refresh_corr_games()
        ONLINE.corr_abandon(gd.get("id"), on_done)

    def _corr_revanche(self, gd):
        """Renvoyer un défi de correspondance à l'adversaire (après une partie
        terminée), puis fermer le slot terminé."""
        adv = gd.get("adversaire", "")
        gid = gd.get("id")
        def after_close(ok, err):
            def on_done(result, err2):
                if err2 or not (result and result.get("ok")):
                    msg = (result or {}).get("message") or err2 or "Échec du défi."
                    self._popup_simple("Correspondance", msg)
                else:
                    self._popup_simple("Correspondance", "Revanche envoyée à %s !" % adv)
                self._refresh_corr_games()
            ONLINE.corr_defier(adv, "partie", on_done)
        # Fermer d'abord la partie terminée (libère le slot), puis défier
        ONLINE.corr_close(gid, after_close)

    def _corr_fermer(self, gd):
        """Fermer (masquer) une partie de correspondance terminée sur le slot."""
        def on_done(ok, err):
            self._refresh_corr_games()
        ONLINE.corr_close(gd.get("id"), on_done)

    def _open_corr_game(self, gd):
        """Ouvre une partie de correspondance : on délègue au GameScreen qui fait
        un RESET COMPLET et reconstruit l'état uniquement à partir des coups NMC
        fournis par le serveur (aucun état résiduel, anti 'comptes collés')."""
        game = self.manager.get_screen("game")
        game.start_corr_game(gd)
        self.manager.current = "game"

    def _require_login(self):
        """Invite à se connecter pour utiliser les fonctions en ligne."""
        Popup(title="Connexion requise",
              content=Label(text="Connectez-vous (bouton Compte)\n"
                                 "pour jouer en ligne.", color=(1, 1, 1, 1)),
              size_hint=(0.8, 0.3)).open()

    def _open_plus_popup(self, *a):
        """Ouvre une popup avec les options Règles / Parties / Analyse / Réglages."""
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
        popup = Popup(title="", content=content,
                      size_hint=(0.8, 0.7),
                      separator_height=0, auto_dismiss=True)

        def make_btn(label, action, bg=COL_BTN_GREY):
            b = RoundButton(text=label, font_size=SF("17sp"), bold=True,
                            bg_color=bg, color=(1, 1, 1, 1),
                            size_hint=(1, 0.18))
            b.bind(on_release=lambda *_: (popup.dismiss(), action()))
            return b

        content.add_widget(make_btn("Tuto",
            lambda: setattr(self.manager, "current", "tuto"), bg=COL_ORANGE))
        content.add_widget(make_btn("Historique",
            lambda: setattr(self.manager, "current", "parties_menu")))
        content.add_widget(make_btn("Analyse",
            lambda: self._start_analysis()))
        content.add_widget(make_btn("Réglages",
            lambda: open_settings_popup(None)))
        content.add_widget(make_btn("Soutenir les devs",
            lambda: self._open_support_popup(), bg=COL_ORANGE))
        popup.open()

    def _open_support_popup(self):
        """Popup listant les plateformes de don (le joueur choisit la sienne).
        Chaque bouton ouvre le lien correspondant dans le navigateur."""
        # ↓↓↓ Liens à compléter quand les comptes seront créés ↓↓↓
        liens = [
            ("PayPal",            SUPPORT_LINKS.get("paypal", "")),
        ]
        content = BoxLayout(orientation="vertical", spacing=S(10), padding=S(16))
        intro = Label(
            text="Merci de soutenir le développement de La Fuga !\n"
                 "Votre aide compte beaucoup.",
            font_size=SF("14sp"), color=(1, 1, 1, 1),
            halign="center", valign="middle", size_hint=(1, None), height=S(60))
        intro.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(intro)

        popup = Popup(title="Soutenir les devs", content=content,
                      size_hint=(0.82, 0.6))

        def make_link_btn(label, url):
            b = RoundButton(text=label, font_size=SF("16sp"), bold=True,
                            bg_color=COL_BLUE, color=(1, 1, 1, 1),
                            size_hint=(1, None), height=S(50))
            def _open(*a):
                if not url:
                    self._popup_simple("Bientôt",
                                       "Ce lien sera bientôt disponible.")
                    return
                try:
                    import webbrowser
                    webbrowser.open(url)
                except Exception:
                    self._popup_simple("Lien", url)
            b.bind(on_release=_open)
            return b

        for label, url in liens:
            content.add_widget(make_link_btn(label, url))
        popup.open()

    def _start_analysis(self, *a):
        g = self.manager.get_screen("game")
        g.start_analysis()
        self.manager.current = "game"

    def _set_pts(self, v): self.target  = v; self._refresh()
    def _set_cad(self, v): self.cadence = v; self._refresh()

    def _refresh(self):
        for v, b in self.pts_btns.items():
            sel = (v == self.target)
            b.set_bg(COL_ORANGE if sel else COL_BTN_GREY)
            b.set_selected(sel)
        for v, b in self.cad_btns.items():
            sel = (v == self.cadence)
            b.set_bg(COL_BLUE if sel else COL_BTN_GREY)
            b.set_selected(sel)

    def apply_theme_colors(self):
        """Met à jour les couleurs du menu après changement de thème."""
        if hasattr(self, "_bg_col"):
            self._bg_col.rgba = COL_BG_MENU
        # Fond image (thème médiéval), largeur calée sur l'écran
        if hasattr(self, "_bg_stone") and hasattr(self, "_bg_stone_col"):
            tex = _theme_bg_texture("fond.png") if _theme_image_dir(CURRENT_THEME) else None
            if tex:
                pos, size = _fit_menu_bg(tex, Window.width, Window.height)
                self._bg_stone.texture = tex
                self._bg_stone.pos = pos
                self._bg_stone.size = size
                self._bg_stone_col.a = 1
            else:
                self._bg_stone_col.a = 0
        # Filigrane blanchâtre (thème fleur uniquement)
        if hasattr(self, "_bg_veil_col"):
            if CURRENT_THEME == "fleur" and _theme_bg_texture("fond.png"):
                self._bg_veil_col.rgba = (1, 1, 1, 0.45)
                self._bg_veil.size = Window.size
            else:
                self._bg_veil_col.rgba = (1, 1, 1, 0)
            self._btn_local.set_bg(COL_ORANGE)
        if hasattr(self, "_btn_online"):
            self._btn_online.set_bg(COL_BLUE)
        if hasattr(self, "_logo_widget"):
            self._logo_widget.source = self._theme_logo_path()
            self._logo_widget.reload()
        # Redessiner les cases de correspondance avec les nouvelles couleurs
        if hasattr(self, "corr_slots"):
            for slot in self.corr_slots:
                if hasattr(slot, "_redraw_slot"):
                    slot._redraw_slot()
        self._refresh()

    def _theme_logo_path(self):
        """Chemin du logo correspondant au thème courant (fallback logo.png)."""
        base = os.path.dirname(os.path.abspath(__file__))
        # Le thème "medieval" utilise le logo nommé logo_bataille.png
        # Mapping thème -> nom de logo (certains diffèrent du nom du thème)
        logo_special = {"medieval": "bataille", "fleur": "fleurs",
                        "insectes": "foret"}
        logo_name = logo_special.get(CURRENT_THEME, CURRENT_THEME)
        themed = os.path.join(base, "logos", f"logo_{logo_name}.png")
        if os.path.exists(themed):
            return themed
        fallback = os.path.join(base, "logo.png")
        return fallback if os.path.exists(fallback) else themed

    def on_pre_enter(self, *a):
        """Appelée chaque fois qu'on entre dans le menu."""
        self._refresh_online_ui()
        self._refresh_random_btn()
        # Si connecté : se brancher au serveur temps réel et s'abonner aux défis,
        # pour pouvoir RECEVOIR un défi à tout moment (sans action préalable).
        if ONLINE.is_logged_in():
            try:
                ONLINE.sio_connect(on_ready=lambda ok, msg: None)
                self._bind_defi_handlers()
            except Exception:
                pass
            # Rafraîchir les parties de correspondance (états à jour : nouveau
            # défi reçu, à qui de jouer, partie terminée…).
            try:
                self._refresh_corr_games()
            except Exception:
                pass

    def apply_theme_colors(self):
        """Appelée au changement de thème (par refresh_all_screens). Redessine les
        aperçus de correspondance, qui dessinent leur fond avec les couleurs du
        thème (sinon ils garderaient l'ancienne teinte jusqu'au prochain passage
        par le menu)."""
        for slot in getattr(self, "corr_slots", []):
            if hasattr(slot, "_redraw_slot"):
                try:
                    slot._redraw_slot()
                except Exception:
                    pass

    def _on_random_toggle(self, *a):
        """Interrupteur global Random Fuga : bascule ON/OFF, sauvegarde l'état."""
        global RANDOM_MODE
        RANDOM_MODE = not RANDOM_MODE
        # (Plus mémorisé : le mode Random se réinitialise à chaque lancement.)
        self._refresh_random_btn()

    def _refresh_random_btn(self):
        """Met à jour l'apparence de l'interrupteur Random : fond couleur claire
        du thème quand allumé, gris quand éteint. (RoundButton n'a pas de
        propriété bg_color : on passe par set_bg pour redessiner le fond.)"""
        if not hasattr(self, "random_btn"):
            return
        if RANDOM_MODE:
            self.random_btn.text = "Random"
            self.random_btn.set_bg(COL_ORANGE)             # couleur claire du thème
            self.random_btn.color = (0.1, 0.1, 0.1, 1)     # texte foncé (contraste)
        else:
            self.random_btn.text = "Random"
            self.random_btn.set_bg(COL_BTN_GREY)
            self.random_btn.color = (1, 1, 1, 1)

    def _refresh_online_ui(self):
        """Met à jour le bouton compte : 'Compte' si déconnecté, sinon le pseudo
        et le Mélo du joueur connecté."""
        if not hasattr(self, "account_btn"): return
        if ONLINE.is_logged_in():
            self.account_btn.text = "%s (%d)" % (ONLINE.pseudo or "?", ONLINE.melo)
        else:
            self.account_btn.text = "Compte"
        self.account_btn.bg_color = COL_BTN_GREY
        self.account_btn.color = (1, 1, 1, 1)

    def _on_account_press(self, *a):
        """Si connecté : popup infos compte + déconnexion. Sinon : écran login."""
        if ONLINE.is_logged_in():
            self._show_account_popup()
        else:
            self.manager.current = "login"

    def _show_account_popup(self):
        """Popup d'infos du compte connecté, avec bouton de déconnexion."""
        content = BoxLayout(orientation="vertical", spacing=S(14), padding=S(18))
        info = Label(text="Connecté en tant que :\n[b]%s[/b]\n\nMélo : %d"
                          % (ONLINE.pseudo or "?", ONLINE.melo),
                     markup=True, color=(1, 1, 1, 1), halign="center",
                     valign="middle", font_size=SF("16sp"))
        info.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(info)
        btn = RoundButton(text="Se déconnecter", font_size=SF("15sp"), bold=True,
                          bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                          size_hint=(1, None), height=S(48))
        content.add_widget(btn)
        popup = Popup(title="Mon compte", content=content,
                      size_hint=(0.82, 0.5))

        def do_logout(*_):
            ONLINE.logout()
            clear_online_session()
            popup.dismiss()
            self._refresh_online_ui()
        btn.bind(on_release=do_logout)
        popup.open()

    def _start_local(self, *a):
        g = self.manager.get_screen("game")
        g.start_match(self.target, self.cadence)
        self.manager.current = "game"

    def _start_vs_ai(self, *a):
        """Ouvre une popup pour choisir la couleur."""
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
        lbl = Label(text="Choisissez votre couleur",
                    font_size=SF("17sp"), bold=True,
                    color=(1, 1, 1, 1),
                    size_hint=(1, 0.22), halign="center", valign="middle")
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        popup = Popup(title="", content=content,
                      size_hint=(0.8, 0.55),
                      separator_height=0, auto_dismiss=True)

        def launch(player_color):
            popup.dismiss()
            g = self.manager.get_screen("game")
            g.start_match_vs_ai(self.target, self.cadence, player_color=player_color)
            self.manager.current = "game"

        b_blanc = RoundButton(text="Jouer avec les Blancs", font_size=SF("16sp"),
                              bold=True, bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                              size_hint=(1, 0.26))
        b_blanc.bind(on_release=lambda *_: launch("Blanc"))

        b_noir = RoundButton(text="Jouer avec les Noirs", font_size=SF("16sp"),
                             bold=True, bg_color=COL_BLUE, color=(1, 1, 1, 1),
                             size_hint=(1, 0.26))
        b_noir.bind(on_release=lambda *_: launch("Noir"))

        b_alea = RoundButton(text="Aléatoire", font_size=SF("16sp"),
                             bold=True, bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                             size_hint=(1, 0.26))
        b_alea.bind(on_release=lambda *_: launch("random"))

        content.add_widget(b_blanc)
        content.add_widget(b_noir)
        content.add_widget(b_alea)
        popup.open()


# ── Écran Règles ─────────────────────────────────────────────────────────────


# ── Tutoriel interactif ──────────────────────────────────────────────────────
# Le tuto réutilise le VRAI plateau du jeu (BoardWidget) : rendu, thèmes, zones
# de ralliement, animations, tout est identique à une partie. La TutoScreen sert
# d'"hôte" au BoardWidget (elle fournit board, flipped, sel, handle_cell, etc.).
# Chaque étape = une fiche : position + flèche(s) + cadre(s) + texte. Les étapes
# interactives (à venir) n'autoriseront que le coup prévu.

_TUTO_NOTES = ["do", "ré", "mi", "fa", "sol", "la", "si"]


def _tuto_start_position():
    """Position de départ standard (identique à _setup_pieces), en liste de
    tuples (colonne, ligne 1..8, type, camp)."""
    line1 = ["Soldat", "Garde", "Soldat", "Héritier", "Garde", "Soldat", "Garde"]
    line2 = ["Garde", "Nurse", "Nurse", "Nurse", "Nurse", "Nurse", "Soldat"]
    pieces = []
    for i, c in enumerate(_TUTO_NOTES):
        pieces.append((c, 1, line1[i], "Blanc"))
        pieces.append((c, 2, line2[i], "Blanc"))
        pieces.append((c, 8, line1[i], "Noir"))
        pieces.append((c, 7, line2[i], "Noir"))
    pieces.append(("fa", 3, "Chevalier", "Blanc"))
    pieces.append(("fa", 6, "Chevalier", "Noir"))
    return pieces


def _build_tuto_steps():
    """Liste ordonnée des étapes du tuto. (On ajoutera les suivantes au fur et à
    mesure.)"""
    return [
        {   # Étape 1, Le but du jeu (illustration ; flèche vers le ralliement)
            "title": "Le but du jeu",
            "pieces": _tuto_start_position(),
            "framed": [("fa", 1)],
            "arrows": [(("fa", 1), ("fa", "out"))],   # "out" = ralliement (hors plateau)
            "text": ("Bienvenue. À La Fuga, le but du jeu est d'emmener "
                     "l'Héritier (pièce encadrée) jusqu'à sa zone de ralliement, "
                     "à l'autre bout du plateau. Bien sûr, vous devrez aussi "
                     "empêcher votre adversaire d'y parvenir. Il peut y parvenir "
                     "par lui-même ou en étant poussé."),
        },
        {   # Étape 2, Le déplacement (interactive : bouger d'une case)
            "title": "Le déplacement",
            "pieces": [("fa", 4, "Héritier", "Blanc")],
            "interactive": True,
            "move": ("fa", 4),
            "dests": [("mi", 3), ("fa", 3), ("sol", 3),
                      ("mi", 4), ("sol", 4),
                      ("mi", 5), ("fa", 5), ("sol", 5)],
            "arrows": [(("fa", 4), ("mi", 3)), (("fa", 4), ("fa", 3)),
                       (("fa", 4), ("sol", 3)), (("fa", 4), ("mi", 4)),
                       (("fa", 4), ("sol", 4)), (("fa", 4), ("mi", 5)),
                       (("fa", 4), ("fa", 5)), (("fa", 4), ("sol", 5))],
            "text_select": "Clique sur l'Héritier pour le sélectionner.",
            "text_move": ("Toutes les pièces peuvent se déplacer d'une case dans "
                          "n'importe quelle direction. Déplace l'Héritier sur "
                          "une case voisine."),
            "text_validate": ("Pour valider ton coup, clique à nouveau sur la "
                              "pièce, sur sa nouvelle case."),
            "text_done": "Parfait ! Clique sur « Suivant » pour continuer.",
        },
        {   # Étape 3, La règle de contact (illustration, non interactive)
            "title": "La règle de contact",
            "pieces": [
                # Rondes qui PEUVENT bouger (une ronde touche une ronde :
                # ici une alliée et une adverse)
                ("mi", 6, "Nurse", "Blanc"), ("mi", 7, "Nurse", "Noir"),
                # Carrées qui PEUVENT bouger (une carrée touche une carrée :
                # ici une alliée et une adverse)
                ("do", 2, "Soldat", "Blanc"), ("ré", 2, "Garde", "Noir"),
                # BLOQUÉES : formes différentes côte à côte (ronde + carrée :
                # aucune ne « débloque » l'autre)
                ("sol", 4, "Nurse", "Blanc"), ("sol", 5, "Soldat", "Blanc"),
            ],
            "framed_ok": [("mi", 6), ("mi", 7), ("do", 2), ("ré", 2)],
            "framed": [("sol", 4), ("sol", 5)],
            "text": ("Pour se déplacer, une pièce RONDE doit toucher une autre "
                     "ronde (alliée ou adverse), et une pièce CARRÉE doit toucher "
                     "une autre carrée. En vert : les pièces qui peuvent bouger. "
                     "En rouge : les pièces bloquées (aucune pièce de leur forme "
                     "à côté)."),
        },
        {   # Étape 4, Le multisaut (interactive : sauts droits ET diagonaux)
            "title": "Le multisaut",
            "pieces": [
                ("do", 1, "Nurse", "Blanc"),   # la sauteuse
                ("ré", 2, "Nurse", "Blanc"),   # saut 1 (diagonale, alliée)
                ("fa", 3, "Nurse", "Noir"),    # saut 2 (orthogonal, adverse)
                ("fa", 4, "Nurse", "Blanc"),   # saut 3 (diagonale, alliée)
                ("mi", 6, "Nurse", "Noir"),    # saut 4 (orthogonal, adverse)
            ],
            "interactive": True,
            "move": ("do", 1),
            "sequence": [
                {"dest": ("mi", 3),
                 "text": "Saut en DIAGONALE par-dessus ré2, jusqu'en mi3."},
                {"dest": ("sol", 3),
                 "text": "Saut tout DROIT par-dessus fa3, jusqu'en sol3."},
                {"dest": ("mi", 5),
                 "text": "De nouveau en DIAGONALE par-dessus fa4, jusqu'en mi5."},
                {"dest": ("mi", 7),
                 "text": "Et tout DROIT par-dessus mi6, jusqu'en mi7."},
            ],
            "text_select": ("Une pièce ronde saute par-dessus une autre ronde "
                            "(alliée ou adverse), en ligne DROITE ou en DIAGONALE, "
                            "et peut enchaîner les sauts ! Clique sur la Nurse."),
            "text_validate": ("Clique à nouveau sur la Nurse pour valider ton "
                              "multisaut."),
            "text_done": ("Bravo ! Sauts droits et diagonaux : tu maîtrises le "
                          "multisaut."),
        },
        {   # Étape 5, Fugue par saut (droits + diagonaux, se termine hors plateau)
            "title": "Fuguer en sautant",
            "pieces": [
                ("mi", 3, "Héritier", "Blanc"),  # l'Héritier
                ("fa", 4, "Nurse", "Noir"),      # saut 1 (diagonale, adverse)
                ("sol", 6, "Nurse", "Blanc"),    # saut 2 (orthogonal, alliée)
                ("fa", 8, "Nurse", "Noir"),      # saut 3 (diagonale) -> fugue
            ],
            "interactive": True,
            "move": ("mi", 3),
            "sequence": [
                {"dest": ("sol", 5),
                 "text": "Saut en DIAGONALE par-dessus fa4, jusqu'en sol5."},
                {"dest": ("sol", 7),
                 "text": "Saut tout DROIT par-dessus sol6, jusqu'en sol7."},
                {"dest": ("mi", "out"),
                 "text": "Dernier saut, en DIAGONALE par-dessus fa8 : l'Héritier "
                         "SORT du plateau et rejoint son ralliement !"},
            ],
            "text_select": ("L'Héritier peut lui aussi enchaîner les sauts, "
                            "droits ou diagonaux, et même FUGUER en sautant. "
                            "Clique sur l'Héritier."),
            "text_done": ("Fugue réussie ! L'Héritier a atteint son ralliement : "
                          "VICTOIRE !"),
        },
        {   # Étape 6, Les groupes + la manœuvre (interactive, 2 groupes)
            "title": "Les unités",
            "pieces": [
                # Unité 1 (vert), fa3 n'est relié que par la diagonale
                ("do", 2, "Soldat", "Blanc"),
                ("ré", 2, "Garde", "Blanc"),
                ("mi", 2, "Soldat", "Blanc"),
                ("fa", 3, "Garde", "Blanc"),
                # Unité 2 (bleu)
                ("sol", 6, "Garde", "Blanc"),
                ("la", 6, "Soldat", "Blanc"),
            ],
            "framed_ok": [("do", 2), ("ré", 2), ("mi", 2), ("fa", 3)],
            "framed_blue": [("sol", 6), ("la", 6)],
            "links": [
                {"pairs": [(("do", 2), ("ré", 2)), (("ré", 2), ("mi", 2)),
                           (("mi", 2), ("fa", 3))],
                 "color": (0.18, 0.72, 0.30)},
                {"pairs": [(("sol", 6), ("la", 6))], "color": (0.92, 0.55, 0.12)},
            ],
            "interactive": True,
            "maneuver": True,
            "leader": ("do", 2),
            "group_add": [("ré", 2), ("fa", 3)],
            "move_to": ("do", 3),
            "done_frame": ("fa", 4),
            "text_select": ("Les pièces carrées d'un même camp qui se touchent, "
                            "même en diagonale, forment une UNITÉ. Plusieurs "
                            "pièces de la même unité peuvent se déplacer en même "
                            "temps, dans la même direction. Déplaçons plusieurs "
                            "pièces de l'unité en vert ; clique sur do2, qui sera "
                            "la meneuse."),
            "text_group": ("Ajoute ré2 puis fa3 à la sélection (on laisse mi2 de "
                           "côté : tu n'es pas obligé de tout prendre)."),
            "text_move": ("L'unité se déplace selon la meneuse. Clique en do3 "
                          "pour monter les pièces choisies d'une case."),
            "text_validate": "Clique sur la meneuse pour valider ton coup.",
            "text_done": ("En montant, la pièce en fa s'est retrouvée seule "
                          "(encadrée) ! Une manœuvre peut donc IMMOBILISER une "
                          "pièce : fa n'a plus aucune carrée à côté."),
        },
        {   # Étape 7, La poussée : le Garde (pousse une ligne + élimine)
            "title": "La poussée : le Garde",
            "pieces": [
                ("mi", 3, "Garde", "Blanc"),    # le Garde (pousseur)
                ("mi", 2, "Soldat", "Blanc"),   # allié : contact pour pouvoir bouger
                ("sol", 4, "Soldat", "Noir"),   # ligne adverse
                ("la", 4, "Garde", "Noir"),
                ("si", 4, "Soldat", "Noir"),
            ],
            "interactive": True,
            "push": True,
            "leader": ("mi", 3),
            "move_to": ("fa", 4),
            "push_to": ("sol", 4),
            "text_select": ("Le GARDE (croix ×) se déplace en diagonale et POUSSE "
                            "en ligne droite. Clique sur le Garde."),
            "text_move": "Déplace le Garde en diagonale, jusqu'en fa4.",
            "text_push": ("Maintenant POUSSE : clique en sol4. Toute la ligne est "
                          "repoussée d'une case, et la pièce du bord tombe du "
                          "plateau (éliminée) !"),
            "text_validate": "Clique sur le Garde pour valider ton coup.",
            "text_done": ("Bravo ! Le Garde a poussé la ligne et éliminé une "
                          "pièce. C'est le SEUL moyen d'éliminer une pièce : la "
                          "pousser hors du plateau. Et tu peux même éliminer tes "
                          "PROPRES pièces !"),
        },
        {   # Étape 9, La poussée : le Soldat (+ s'immobilise)
            "title": "La poussée : le Soldat",
            "pieces": [
                ("do", 3, "Soldat", "Blanc"),   # le Soldat (pousseur)
                ("do", 2, "Soldat", "Blanc"),   # allié : contact au départ
                ("ré", 5, "Nurse", "Noir"),     # pièce à pousser (en diagonale)
            ],
            "interactive": True,
            "push": True,
            "leader": ("do", 3),
            "move_to": ("do", 4),
            "push_to": ("ré", 5),
            "done_frame": ("do", 4),
            "text_select": ("Le SOLDAT (croix +) se déplace en ligne droite et "
                            "POUSSE en diagonale. Clique sur le Soldat."),
            "text_move": "Déplace le Soldat tout droit, en do4.",
            "text_push": ("POUSSE en diagonale : clique en ré5 pour repousser la "
                          "pièce."),
            "text_validate": "Clique sur le Soldat pour valider ton coup.",
            "text_done": ("Attention : en se déplaçant, le Soldat s'est éloigné de "
                          "son allié et n'a plus de carrée à côté, il est "
                          "maintenant BLOQUÉ (encadré) jusqu'à ce qu'une carrée le "
                          "rejoigne."),
        },
        {   # Étape 10, Poussée : plusieurs directions au choix
            "title": "Pousser plusieurs directions",
            "pieces": [
                ("mi", 3, "Garde", "Blanc"),    # le Garde
                ("mi", 2, "Soldat", "Blanc"),   # allié : contact
                ("fa", 5, "Nurse", "Noir"),     # à pousser vers le haut
                ("sol", 4, "Soldat", "Noir"),   # à pousser vers la droite
                ("fa", 3, "Soldat", "Noir"),    # poussable vers le bas... mais on la LAISSE
            ],
            "interactive": True,
            "push": True,
            "leader": ("mi", 3),
            "move_to": ("fa", 4),
            "pushes": [
                {"push_to": ("fa", 5),
                 "text": "Pousse une 1re direction : clique en fa5 (vers le haut)."},
                {"push_to": ("sol", 4),
                 "text": "Tu peux pousser une AUTRE direction ! Clique en sol4 "
                         "(vers la droite)."},
            ],
            "text_select": ("Après s'être déplacée, une carrée peut pousser dans "
                            "PLUSIEURS directions, autant que tu veux. Clique sur "
                            "le Garde."),
            "text_move": "Déplace le Garde en diagonale, en fa4.",
            "text_validate": "Clique sur le Garde pour valider ton coup.",
            "text_done": ("Bravo ! Tu as poussé en haut et à droite. Remarque : "
                          "fa3 (en bas) pouvait aussi être poussée, mais on l'a "
                          "laissée, c'est toi qui choisis quelles directions "
                          "pousser."),
        },
        {   # Étape 11, Fuguer en poussant (pousser SON Héritier au ralliement)
            "title": "Fuguer en poussant",
            "pieces": [
                ("mi", 6, "Garde", "Blanc"),     # le Garde (pousseur)
                ("mi", 5, "Soldat", "Blanc"),    # allié : contact
                ("fa", 8, "Héritier", "Blanc"),  # TON Héritier, au bord
            ],
            "interactive": True,
            "push": True,
            "leader": ("mi", 6),
            "move_to": ("fa", 7),
            "push_to": ("fa", 8),
            "win": True,
            "text_select": ("On peut aussi POUSSER son propre Héritier ! Clique "
                            "sur le Garde."),
            "text_move": "Déplace le Garde en diagonale, en fa7 (sous l'Héritier).",
            "text_push": ("POUSSE vers le haut : clique en fa8. L'Héritier est "
                          "poussé dans son ralliement !"),
            "text_done": ("Fugue ! Tu as poussé ton Héritier dans son ralliement : "
                          "VICTOIRE !"),
        },
        {   # Étape 11, Mater en poussant (pousser l'Héritier ADVERSE hors plateau)
            "title": "Mater en poussant",
            "pieces": [
                ("sol", 6, "Garde", "Blanc"),    # le Garde (pousseur)
                ("sol", 5, "Soldat", "Blanc"),   # allié : contact
                ("la", 8, "Héritier", "Noir"),   # Héritier ADVERSE, au bord
            ],
            "interactive": True,
            "push": True,
            "leader": ("sol", 6),
            "move_to": ("la", 7),
            "push_to": ("la", 8),
            "win": True,
            "text_select": ("Enfin, pousser l'Héritier ADVERSE hors du plateau le "
                            "met MAT. Clique sur le Garde."),
            "text_move": "Déplace le Garde en diagonale, en la7 (sous l'Héritier adverse).",
            "text_push": ("POUSSE vers le haut : clique en la8. L'Héritier adverse "
                          "est éjecté du plateau !"),
            "text_done": ("Mat ! Tu as poussé l'Héritier adverse hors du plateau : "
                          "VICTOIRE !"),
        },
        {   # Étape 12, Le Chevalier (illustration : inébranlable + indépendant)
            "title": "Le Chevalier",
            "pieces": [
                ("fa", 3, "Chevalier", "Blanc"),
                ("fa", 6, "Chevalier", "Noir"),
            ],
            "framed_blue": [("fa", 3), ("fa", 6)],
            "text": ("Le CHEVALIER (l'hexagone) est une pièce à part, avec deux "
                     "pouvoirs. INÉBRANLABLE : il ne peut jamais être poussé, une "
                     "poussée s'arrête net sur lui. INDÉPENDANT : il peut se "
                     "déplacer même s'il ne touche aucune pièce de sa forme (il "
                     "n'a pas besoin de voisine pour bouger)."),
        },
        {   # Étape 14, Le Chevalier bloque les lignes (illustration)
            "title": "Le Chevalier bloque",
            "pieces": [
                ("mi", 2, "Garde", "Noir"),       # adversaire (la menace)
                ("fa", 4, "Chevalier", "Blanc"),  # le mur
                ("fa", 5, "Héritier", "Blanc"),   # protégé
                ("fa", 6, "Nurse", "Blanc"),      # protégé
            ],
            "framed_blue": [("fa", 4)],
            "arrows": [(("mi", 2), ("fa", 3))],
            "text": ("Puisqu'il ne peut être poussé, le Chevalier sert de MUR : il "
                     "bloque les poussées. Ici, même si le Garde adverse s'avance "
                     "en fa3 pour pousser vers le haut, le Chevalier (fa4) arrête "
                     "tout : l'Héritier (fa5) est protégé."),
        },
        {   # Transition : bannière "motifs de fin de partie"
            "title": "Fins de partie",
            "banner": "MOTIFS DE\nFIN DE PARTIE",
            "pieces": [],
            "text": ("Voici toutes les façons dont une partie peut se terminer, "
                     "et combien de points chacune rapporte."),
        },
        {   # Fin : la fugue (+2)
            "title": "Fin : la fugue",
            "pieces": [
                ("ré", 8, "Héritier", "Blanc"),
                ("mi", 8, "Nurse", "Blanc"),
                ("sol", 5, "Chevalier", "Noir"),
                ("la", 6, "Chevalier", "Blanc"),
                ("la", 4, "Nurse", "Noir"),
                ("do", 3, "Garde", "Blanc"),
                ("fa", 2, "Héritier", "Noir"),
            ],
            "arrows": [(("ré", 8), ("mi", "out"))],
            "text": ("FUGUE (+2 points). Ton Héritier atteint son ralliement (la "
                     "flèche) : tu gagnes la partie ! C'est la victoire la plus "
                     "valorisée. Une Nurse à son contact lui permet de bouger."),
        },
        {   # Fin : la double fugue (0)
            "title": "Fin : la double fugue",
            "pieces": [
                ("fa", 8, "Héritier", "Blanc"),
                ("mi", 8, "Nurse", "Blanc"),
                ("fa", 1, "Héritier", "Noir"),
                ("mi", 1, "Nurse", "Noir"),
                ("sol", 4, "Chevalier", "Blanc"),
                ("do", 4, "Chevalier", "Noir"),
            ],
            "arrows": [(("fa", 8), ("fa", "out")), (("fa", 1), ("fa", 0))],
            "text": ("DOUBLE FUGUE (0 point). Quand les Blancs fuguent, les Noirs "
                     "ont droit à un DERNIER coup pour égaliser. Si les deux "
                     "Héritiers rejoignent leur ralliement, la partie est nulle. "
                     "Ici, c'est aux Blancs de jouer, et les deux Héritiers peuvent "
                     "fuguer (flèches)."),
        },
        {   # Fin : le mat (+1)
            "title": "Fin : le mat",
            "pieces": [
                ("si", 6, "Garde", "Blanc"),
                ("si", 5, "Soldat", "Blanc"),
                ("la", 8, "Héritier", "Noir"),
                ("mi", 4, "Chevalier", "Blanc"),
                ("do", 7, "Chevalier", "Noir"),
                ("do", 5, "Nurse", "Noir"),
                ("fa", 6, "Nurse", "Blanc"),
            ],
            "arrows": [(("si", 6), ("la", 7)), (("la", 8), ("la", "out"))],
            "text": ("MAT (+1 point). Le Garde (si6) se déplace en la7, puis pousse "
                     "l'Héritier adverse (la8) hors du plateau : il est éjecté, tu "
                     "gagnes."),
        },
        {   # Fin : la guillotine (adversaire +1)
            "title": "Fin : la guillotine",
            "pieces": [
                ("la", 8, "Héritier", "Blanc"),
                ("si", 6, "Garde", "Blanc"),
                ("si", 5, "Soldat", "Blanc"),
                ("fa", 1, "Héritier", "Noir"),
                ("sol", 1, "Nurse", "Noir"),
                ("mi", 4, "Chevalier", "Blanc"),
                ("do", 5, "Chevalier", "Noir"),
            ],
            "arrows": [(("si", 6), ("la", 7)), (("la", 8), ("la", "out")),
                       (("fa", 1), ("fa", 0))],
            "text": ("GUILLOTINE. L'adversaire va fuguer (son Héritier fa1, mobile "
                     "grâce à sa Nurse, atteint son ralliement en bas : +2 pour "
                     "lui). Pour limiter la casse, ton Garde (si6 vers la7) pousse "
                     "TON PROPRE Héritier (la8) hors du plateau : c'est un mat sur "
                     "toi-même, l'adversaire ne prend que +1 au lieu de +2."),
        },
        {   # Fin : la papatte (+1)
            "title": "Fin : la papatte",
            "pieces": [
                ("do", 8, "Chevalier", "Noir"),
                ("si", 8, "Héritier", "Noir"),
                ("do", 7, "Garde", "Blanc"),
                ("ré", 7, "Soldat", "Blanc"),
                ("ré", 8, "Garde", "Blanc"),
                ("fa", 3, "Héritier", "Blanc"),
                ("mi", 5, "Nurse", "Blanc"),
                ("sol", 5, "Chevalier", "Blanc"),
            ],
            "framed": [("do", 8), ("si", 8)],
            "text": ("PAPATTE (+1 point). C'est à l'adversaire de jouer, mais il "
                     "n'a AUCUN coup légal : son Chevalier (do8) est coincé, et son "
                     "Héritier (si8) est isolé (aucune ronde à côté). Il perd. Très "
                     "rare !"),
        },
        {   # Fin : la trêve (0)
            "title": "Fin : la trêve",
            "pieces": [
                ("do", 4, "Nurse", "Blanc"), ("do", 5, "Héritier", "Blanc"),
                ("si", 4, "Nurse", "Noir"), ("si", 5, "Héritier", "Noir"),
                ("fa", 1, "Soldat", "Blanc"), ("fa", 8, "Garde", "Noir"),
                ("mi", 6, "Chevalier", "Blanc"), ("la", 5, "Chevalier", "Noir"),
            ],
            "framed": [("fa", 1), ("fa", 8)],
            "text": ("TRÊVE (0 point). Quand plus AUCUN joueur n'a de carrée qui "
                     "peut bouger (peu importe à qui c'est de jouer), la partie est "
                     "nulle : sans carrée mobile, plus aucune poussée n'est "
                     "possible. Ici, les deux carrées (encadrées) sont isolées."),
        },
        {   # Fin : nulle par accord + répétition (0)
            "title": "Fin : nulle par accord",
            "pieces": [
                ("mi", 5, "Héritier", "Blanc"), ("fa", 4, "Nurse", "Blanc"),
                ("ré", 6, "Héritier", "Noir"), ("sol", 5, "Nurse", "Noir"),
                ("do", 3, "Garde", "Blanc"), ("la", 6, "Soldat", "Noir"),
                ("fa", 7, "Chevalier", "Noir"), ("si", 5, "Chevalier", "Blanc"),
            ],
            "mock_ui": [
                {"text": "½", "fx": 0.5, "fy": 0.09, "fw": 0.11, "fh": 0.055,
                 "bg": (0.20, 0.45, 0.75), "circle": True},
            ],
            "text": ("NULLE PAR ACCORD (0 point). Pendant une partie, tu peux "
                     "proposer la nulle avec le bouton « ½ » (entouré) ; si "
                     "l'adversaire accepte, la partie est nulle. RÉPÉTITION : si la "
                     "même position revient 4 fois, la nulle est automatique."),
        },
        {   # Fin : abandon / temps / déconnexion (+2)
            "title": "Fin : abandon, temps, déco",
            "pieces": [
                ("mi", 4, "Héritier", "Blanc"), ("fa", 5, "Nurse", "Blanc"),
                ("sol", 4, "Héritier", "Noir"), ("ré", 5, "Nurse", "Noir"),
                ("la", 3, "Garde", "Blanc"), ("do", 6, "Soldat", "Noir"),
                ("fa", 3, "Chevalier", "Blanc"), ("si", 5, "Chevalier", "Noir"),
            ],
            "mock_ui": [
                {"text": "0:00", "fx": 0.19, "fy": 0.93, "fw": 0.17, "fh": 0.06,
                 "bg": (0.55, 0.12, 0.12), "circle": True},
                {"text": "Joueur 1 deconnecte", "fx": 0.63, "fy": 0.93, "fw": 0.50,
                 "fh": 0.06, "bg": (0.20, 0.22, 0.28), "circle": True},
                {"text": "X", "fx": 0.30, "fy": 0.07, "fw": 0.11, "fh": 0.055,
                 "bg": (0.60, 0.20, 0.20), "circle": True},
            ],
            "text": ("ABANDON / TEMPS / DÉCONNEXION (+2 points chacun). Trois façons "
                     "de gagner sans jouer : si l'adversaire ABANDONNE (le bouton "
                     "« X »), si son TEMPS tombe à 0:00 (la pendule), ou s'il se "
                     "DÉCONNECTE. Dans les trois cas, tu gagnes +2 "
                     "points."),
        },
    ]


class TutoScreen(Screen):
    """Écran du tutoriel : héberge le VRAI plateau du jeu. Plateau en haut,
    encadré de texte au milieu, barre Précédent / pause / Suivant + progression."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.steps = _build_tuto_steps()
        self.idx = 0
        self._step_done = False
        self._phase = "select"     # phases d'une étape interactive
        self._moved_to = None      # case (interne) où la pièce a été déplacée
        self._seq_idx = 0          # index du saut courant dans une séquence
        self._grp_idx = 0          # index du membre courant à ajouter (manœuvre)
        self._push_idx = 0         # index de la poussée courante (multi-directions)
        self._tour_idx = 0         # index de l'étape de la visite du menu
        # ── Interface attendue par BoardWidget (self sert d'hôte "gs") ──
        self.board = None          # grille 7×8 (remplie à chaque étape)
        self.flipped = True        # camp du joueur (Blanc) en bas
        self.sel = None
        self.group_sel = set()
        self.fugued_heirs = []
        self._cs = self._ox = self._oy = 0
        self.tuto_annotations = None
        self._build()

    # ── Prédicats requis par BoardWidget (copie du jeu) ──
    def is_round(self, p):
        return p is not None and p["type"] in ("Nurse", "Héritier")

    def is_square(self, p):
        return p is not None and p["type"] in ("Soldat", "Garde")

    def has_round_nbr(self, c, r):
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == dr == 0:
                    continue
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if self.is_round(self.board[nc][nr]):
                        return True
        return False

    def has_square_nbr(self, c, r):
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == dr == 0:
                    continue
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if self.is_square(self.board[nc][nr]):
                        return True
        return False

    def handle_cell(self, col, row):
        """Reproduit le vrai mécanisme du jeu, en 3 phases :
          select   : cliquer la pièce pour la sélectionner
          move     : la déplacer (case voisine, OU séquence de sauts guidés)
          validate : re-cliquer la pièce pour valider le coup
        Seul le coup prévu est possible ; le texte change à chaque phase. Cas
        spécial : une fugue (atterrissage hors plateau) gagne directement."""
        step = self.steps[self.idx]
        if not step.get("interactive") or self._step_done:
            return
        if step.get("maneuver"):
            self._handle_maneuver(col, row)
            return
        if step.get("push"):
            self._handle_push(col, row)
            return
        mp = step.get("_move_internal")
        ph = self._phase
        seq = step.get("_sequence_internal")
        if ph == "select":
            if (col, row) == mp:
                self.sel = (col, row)
                self._phase = "move"
                self._seq_idx = 0
                self._apply_phase()
                self.board_w._redraw()
        elif ph == "move":
            if seq is not None:
                # Séquence guidée (multisaut) : seule la case prévue est valide
                target = seq[self._seq_idx]["dest"]
                if (col, row) == target:
                    self._do_tuto_move(mp, target)
                elif (col, row) == mp and self._seq_idx == 0:
                    self._deselect()
            else:
                dests = step.get("_dests_internal", [])
                if (col, row) in dests:
                    self._do_tuto_move(mp, (col, row))
                elif (col, row) == mp:
                    self._deselect()
        elif ph == "validate":
            if (col, row) == self._moved_to:
                self.sel = None
                self._phase = "done"
                self._step_done = True
                self._apply_phase()
                self.board_w._redraw()
                self._refresh_nav()

    def _deselect(self):
        self.sel = None
        self._phase = "select"
        self._apply_phase()
        self.board_w._redraw()

    def _do_tuto_move(self, src, dst):
        """Joue un coup/saut (animation du vrai plateau) et enchaîne la phase
        suivante : saut suivant d'une séquence, validation, ou victoire si c'est
        une fugue (atterrissage hors plateau)."""
        step = self.steps[self.idx]
        c0, r0 = src
        c1, r1 = dst
        piece = self.board[c0][r0]
        if not piece:
            return
        seq = step.get("_sequence_internal")
        is_fugue = (r1 >= ROWS or r1 <= -1)   # hors plateau -> fugue

        self.board[c0][r0] = None
        if is_fugue:
            # La pièce quitte le plateau : dessinée dans le ralliement.
            self.sel = None
            self._moved_to = None
            self.fugued_heirs = [{"col": c1, "row": r1, "camp": piece["camp"]}]
            self._phase = "done"
            self._step_done = True
        else:
            self.board[c1][r1] = piece
            self.sel = (c1, r1)              # la sélection suit la pièce
            self._moved_to = (c1, r1)
            step["_move_internal"] = (c1, r1)
            if seq is not None:
                self._seq_idx += 1
                self._phase = "move" if self._seq_idx < len(seq) else "validate"
            else:
                self._phase = "validate"
        self.tuto_annotations = None          # nettoyer pendant le glissement

        def _done():
            try:
                self.board_w._redraw()
            except Exception:
                pass
            self._apply_phase()
            self.board_w._redraw()
            if self._step_done:
                self._refresh_nav()

        try:
            self.board_w.animate_slide([(piece, (c0, r0), (c1, r1))],
                                       on_done=_done)
        except Exception:
            _done()

    # ── Manœuvre de groupe (pièces carrées) ──
    def _handle_maneuver(self, col, row):
        """Manœuvre en 4 temps, comme le vrai jeu :
          select : cliquer la MENEUSE (surbrillance distincte)
          group  : ajouter des pièces carrées du groupe (guidé)
          mmove  : cliquer une case voisine -> tout le groupe se décale
          validate : re-cliquer la meneuse pour valider."""
        step = self.steps[self.idx]
        leader = step["_leader_internal"]
        group = step.get("_group_internal", [])
        move_to = step["_moveto_internal"]
        ph = self._phase
        if ph == "select":
            if (col, row) == leader:
                self.sel = (col, row)      # meneuse -> COL_SEL_MAIN (natif)
                self._grp_idx = 0
                self._phase = "group" if group else "mmove"
                self._apply_phase()
                self.board_w._redraw()
        elif ph == "group":
            if self._grp_idx < len(group) and (col, row) == group[self._grp_idx]:
                self.group_sel.add((col, row))   # membre -> COL_SEL_GROUP (natif)
                self._grp_idx += 1
                self._phase = "group" if self._grp_idx < len(group) else "mmove"
                self._apply_phase()
                self.board_w._redraw()
        elif ph == "mmove":
            if (col, row) == move_to:
                self._do_maneuver_move(leader, move_to)
        elif ph == "validate":
            if (col, row) == self._moved_to:
                self.sel = None
                self.group_sel = set()
                self._phase = "done"
                self._step_done = True
                self._apply_phase()
                self.board_w._redraw()
                self._refresh_nav()

    def _do_maneuver_move(self, leader, move_to):
        """Décale en bloc la meneuse + les membres sélectionnés de (dc,dr), avec
        l'animation du vrai plateau. Les pièces non choisies restent en place."""
        dc = move_to[0] - leader[0]
        dr = move_to[1] - leader[1]
        sel_cells = [leader] + sorted(self.group_sel)
        pieces = {(c, r): self.board[c][r] for (c, r) in sel_cells}
        slides = [(dict(pieces[(c, r)]), (c, r), (c + dc, r + dr))
                  for (c, r) in sel_cells]
        for (c, r) in sel_cells:
            self.board[c][r] = None
        for (c, r), p in pieces.items():
            self.board[c + dc][r + dr] = p
        self.sel = (leader[0] + dc, leader[1] + dr)
        self.group_sel = {(c + dc, r + dr) for (c, r) in self.group_sel}
        self._moved_to = self.sel        # nouvelle position de la meneuse
        self._phase = "validate"
        self.tuto_annotations = None

        def _done():
            try:
                self.board_w._redraw()
            except Exception:
                pass
            self._apply_phase()
            self.board_w._redraw()

        try:
            self.board_w.animate_slide(slides, on_done=_done)
        except Exception:
            _done()

    # ── Poussée (pièces carrées) ──
    def _handle_push(self, col, row):
        """Poussée en 4 temps, comme le vrai jeu :
          select   : cliquer la carrée
          move     : la déplacer d'une case (orthogonal pour le Soldat, diagonale
                     pour le Garde)
          push     : cliquer une case dans la direction de poussée (× pour le
                     Soldat, + pour le Garde) où il y a une pièce -> toute la
                     ligne est poussée
          validate : re-cliquer la carrée pour valider (sauf fugue/mat = victoire)."""
        step = self.steps[self.idx]
        leader = step["_leader_internal"]     # position courante de la carrée
        move_to = step["_moveto_internal"]
        push_to = step["_pushto_internal"]
        ph = self._phase
        if ph == "select":
            if (col, row) == leader:
                self.sel = (col, row)
                self._phase = "move"
                self._apply_phase()
                self.board_w._redraw()
        elif ph == "move":
            if (col, row) == move_to:
                self._do_push_move(leader, move_to)
        elif ph == "push":
            pushes = step.get("_pushes_internal")
            if pushes is not None:
                target = pushes[self._push_idx]["push_to"]
                if (col, row) == target:
                    self._do_tuto_push(move_to, target, is_seq=True)
            elif (col, row) == push_to:
                self._do_tuto_push(move_to, push_to)
        elif ph == "validate":
            if (col, row) == self._moved_to:
                self.sel = None
                self._phase = "done"
                self._step_done = True
                self._apply_phase()
                self.board_w._redraw()
                self._refresh_nav()

    def _do_push_move(self, src, dst):
        """Déplacement de la carrée (avant la poussée)."""
        c0, r0 = src
        c1, r1 = dst
        piece = self.board[c0][r0]
        if not piece:
            return
        self.board[c1][r1] = piece
        self.board[c0][r0] = None
        self.sel = (c1, r1)
        self.steps[self.idx]["_leader_internal"] = (c1, r1)
        self._phase = "push"
        self.tuto_annotations = None

        def _done():
            try:
                self.board_w._redraw()
            except Exception:
                pass
            self._apply_phase()          # flèche de poussée + texte
            self.board_w._redraw()

        try:
            self.board_w.animate_slide([(piece, (c0, r0), (c1, r1))],
                                       on_done=_done)
        except Exception:
            _done()

    def _do_tuto_push(self, pusher, push_to, is_seq=False):
        """Applique la poussée depuis la carrée (en `pusher`) dans la direction de
        `push_to` : décale toute la ligne d'une case ; une pièce sortie du plateau
        est éliminée ; un Héritier sorti = mat (ou fugue s'il rejoint son
        ralliement). Reproduit _dg_apply_pushes. is_seq : poussée multi-directions
        (on enchaîne, puis on valide)."""
        pc, pr = pusher
        dc = push_to[0] - pc
        dr = push_to[1] - pr
        # Construire la ligne de pièces consécutives (un Chevalier bloque)
        line = []
        cc, rr = pc + dc, pr + dr
        while 0 <= cc < COLS and 0 <= rr < ROWS:
            p = self.board[cc][rr]
            if p is None:
                break
            if p["type"] == "Chevalier":
                line = []
                break
            line.append((cc, rr, p))
            cc += dc
            rr += dr
        slides = []
        fugue = False
        mate = False
        fugue_heir = None
        for (cc, rr, p) in reversed(line):
            nc, nr = cc + dc, rr + dr
            self.board[cc][rr] = None
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                self.board[nc][nr] = p
                slides.append((dict(p), (cc, rr), (nc, nr)))
            else:
                # Sortie du plateau
                slides.append((dict(p), (cc, rr), (nc, nr)))
                if p["type"] == "Héritier" and nc in RALLY and (
                        (p["camp"] == "Blanc" and nr >= ROWS) or
                        (p["camp"] == "Noir" and nr < 0)):
                    fugue = True
                    fugue_heir = {"col": nc, "row": nr, "camp": p["camp"]}
                elif p["type"] == "Héritier":
                    mate = True
        self._moved_to = pusher
        is_win = fugue or mate
        if is_win:
            self._phase = "done"
            self._step_done = True
        elif is_seq:
            # Poussée multi-directions : passer à la poussée suivante, ou valider
            self._push_idx += 1
            pushes = self.steps[self.idx].get("_pushes_internal", [])
            self._phase = "push" if self._push_idx < len(pushes) else "validate"
        else:
            self._phase = "validate"
        self.tuto_annotations = None

        def _done():
            if fugue and fugue_heir:
                self.fugued_heirs = [fugue_heir]
            try:
                self.board_w._redraw()
            except Exception:
                pass
            self._apply_phase()
            self.board_w._redraw()
            if self._step_done:
                self._refresh_nav()

        try:
            self.board_w.animate_slide(slides, on_done=_done)
        except Exception:
            _done()

    def _apply_phase(self):
        """Met à jour le texte et les annotations selon la phase courante."""
        step = self.steps[self.idx]
        if not step.get("interactive"):
            self.text_box.text = step.get("text", "")
            self.tuto_annotations = {
                "framed": [self._conv_cell(c, r) for (c, r) in step.get("framed", [])],
                "framed_ok": [self._conv_cell(c, r)
                              for (c, r) in step.get("framed_ok", [])],
                "framed_blue": [self._conv_cell(c, r)
                                for (c, r) in step.get("framed_blue", [])],
                "links": [{"pairs": [(self._conv_cell(*a), self._conv_cell(*b))
                                     for (a, b) in lk.get("pairs", [])],
                           "color": lk.get("color", (0.4, 0.4, 0.4))}
                          for lk in step.get("links", [])],
                "arrows": [(self._conv_cell(*p0), self._conv_cell(*p1))
                           for (p0, p1) in step.get("arrows", [])],
            }
            return
        # Manœuvre : phases select -> group -> mmove -> validate -> done
        if step.get("maneuver"):
            leader = step["_leader_internal"]
            ph = self._phase
            if ph == "select":
                self.text_box.text = step.get("text_select", "")
                ann = {"framed_sel": [leader], "arrows": []}
                # Illustration des groupes (montrée au moment de la sélection)
                if step.get("framed_ok"):
                    ann["framed_ok"] = [self._conv_cell(c, r)
                                        for (c, r) in step["framed_ok"]]
                if step.get("framed_blue"):
                    ann["framed_blue"] = [self._conv_cell(c, r)
                                          for (c, r) in step["framed_blue"]]
                if step.get("links"):
                    ann["links"] = [
                        {"pairs": [(self._conv_cell(*a), self._conv_cell(*b))
                                   for (a, b) in lk.get("pairs", [])],
                         "color": lk.get("color", (0.4, 0.4, 0.4))}
                        for lk in step["links"]]
                self.tuto_annotations = ann
            elif ph == "group":
                self.text_box.text = step.get("text_group", "")
                nxt = step["_group_internal"][self._grp_idx]
                self.tuto_annotations = {"framed_sel": [nxt], "arrows": []}
            elif ph == "mmove":
                self.text_box.text = step.get("text_move", "")
                self.tuto_annotations = {
                    "framed": [],
                    "arrows": [(leader, step["_moveto_internal"])],
                }
            elif ph == "validate":
                self.text_box.text = step.get("text_validate", "")
                self.tuto_annotations = {"framed_sel": [self._moved_to], "arrows": []}
            else:  # done
                self.text_box.text = step.get("text_done", "")
                dframe = step.get("_doneframe_internal")
                self.tuto_annotations = ({"framed": [dframe], "arrows": []}
                                         if dframe else None)
            return
        # Poussée : phases select -> move -> push -> validate -> done
        if step.get("push"):
            leader = step["_leader_internal"]
            ph = self._phase
            if ph == "select":
                self.text_box.text = step.get("text_select", "")
                self.tuto_annotations = {"framed_sel": [leader], "arrows": []}
            elif ph == "move":
                self.text_box.text = step.get("text_move", "")
                self.tuto_annotations = {
                    "framed": [],
                    "arrows": [(leader, step["_moveto_internal"])],
                }
            elif ph == "push":
                pushes = step.get("_pushes_internal")
                if pushes is not None:
                    cur = pushes[self._push_idx]
                    self.text_box.text = cur.get("text", step.get("text_push", ""))
                    self.tuto_annotations = {
                        "framed": [],
                        "arrows": [(step["_moveto_internal"], cur["push_to"])],
                    }
                else:
                    self.text_box.text = step.get("text_push", "")
                    self.tuto_annotations = {
                        "framed": [],
                        "arrows": [(step["_moveto_internal"], step["_pushto_internal"])],
                    }
            elif ph == "validate":
                self.text_box.text = step.get("text_validate", "")
                self.tuto_annotations = {"framed_sel": [self._moved_to], "arrows": []}
            else:  # done
                self.text_box.text = step.get("text_done", "")
                dframe = step.get("_doneframe_internal")
                self.tuto_annotations = ({"framed": [dframe], "arrows": []}
                                         if dframe else None)
            return
        ph = self._phase
        mp = step["_move_internal"]
        seq = step.get("_sequence_internal")
        if ph == "select":
            self.text_box.text = step.get("text_select", "")
            self.tuto_annotations = {"framed_sel": [mp], "arrows": []}
        elif ph == "move":
            if seq is not None:
                # Multisaut : flèche du saut courant (de la pièce vers l'arrivée)
                cur = seq[self._seq_idx]
                self.text_box.text = cur.get("text", step.get("text_move", ""))
                self.tuto_annotations = {"framed": [], "arrows": [(mp, cur["dest"])]}
            else:
                self.text_box.text = step.get("text_move", "")
                self.tuto_annotations = {
                    "framed": [],
                    "arrows": [(self._conv_cell(*p0), self._conv_cell(*p1))
                               for (p0, p1) in step.get("arrows", [])],
                }
        elif ph == "validate":
            self.text_box.text = step.get("text_validate", "")
            self.tuto_annotations = {"framed_sel": [self._moved_to], "arrows": []}
        else:  # done
            self.text_box.text = step.get("text_done", "")
            self.tuto_annotations = None

    # ── Construction de l'écran ──
    def _build(self):
        # Racine en FloatLayout (comme l'écran de jeu) : la pile est dans un
        # BoxLayout interne, et le plateau est un OVERLAY par-dessus. Ainsi le
        # BoxLayout ne repositionne jamais le plateau (plus de "téléport").
        root = FloatLayout()
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        stack = BoxLayout(orientation="vertical", size_hint=(1, 1))
        root.add_widget(stack)

        # Barre du haut : pause (gauche) + progression (droite)
        top = BoxLayout(size_hint=(1, 0.06), padding=(S(10), S(4)), spacing=S(8))
        self.pause_btn = RoundButton(text="Pause", font_size=SF("13sp"), bold=True,
                                     bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                                     size_hint=(None, 1), width=S(95))
        self.pause_btn.bind(on_release=lambda *a: self._open_pause())
        self.progress_lbl = Label(text="", font_size=SF("15sp"), bold=True,
                                  color=(0.15, 0.15, 0.15, 1),
                                  halign="right", valign="middle")
        self.progress_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        top.add_widget(self.pause_btn)
        top.add_widget(Widget())
        top.add_widget(self.progress_lbl)
        stack.add_widget(top)

        # Emplacement réservé au plateau (grand, plein largeur)
        self._board_slot = Widget(size_hint=(1, 0.66))
        stack.add_widget(self._board_slot)

        # Encadré de texte EN BAS (fond arrondi crème)
        box_wrap = BoxLayout(size_hint=(1, 0.17), padding=(S(16), S(6)))
        with box_wrap.canvas.before:
            Color(1.0, 0.97, 0.90, 1)
            self._box_rect = RoundedRectangle(radius=[S(12)])
            Color(0.85, 0.78, 0.65, 1)
            self._box_line = Line(width=1.4)
        box_wrap.bind(pos=self._sync_box, size=self._sync_box)
        self.text_box = Label(text="", font_size=SF("15sp"),
                              color=(0.12, 0.12, 0.12, 1),
                              halign="center", valign="middle")
        self.text_box.bind(size=lambda w, s: setattr(w, "text_size", s))
        box_wrap.add_widget(self.text_box)
        stack.add_widget(box_wrap)

        # Barre du bas : Précédent / Suivant
        bottom = BoxLayout(size_hint=(1, 0.11), padding=(S(16), S(6)), spacing=S(14))
        self.prev_btn = RoundButton(text="< Précédent", font_size=SF("15sp"),
                                    bold=True, bg_color=COL_BTN_GREY,
                                    color=(1, 1, 1, 1))
        self.prev_btn.bind(on_release=lambda *a: self._prev())
        self.next_btn = RoundButton(text="Suivant >", font_size=SF("15sp"),
                                    bold=True, bg_color=COL_BLUE,
                                    color=(1, 1, 1, 1))
        self.next_btn.bind(on_release=lambda *a: self._next())
        bottom.add_widget(self.prev_btn)
        bottom.add_widget(self.next_btn)
        stack.add_widget(bottom)

        self.add_widget(root)

        # Le VRAI plateau du jeu, en OVERLAY dans le FloatLayout, calé sur
        # l'emplacement réservé, en PLEIN LARGEUR (comme en partie : les zones de
        # ralliement débordent en haut/bas).
        self.board_w = BoardWidget(self, size_hint=(None, None))
        root.add_widget(self.board_w)
        self._board_slot.bind(pos=self._sync_board, size=self._sync_board)
        Clock.schedule_once(lambda dt: self._sync_board(), 0)

        # Bannière de transition (grand texte centré), masquée par défaut.
        self.banner_lbl = Label(text="", font_size=SF("30sp"), bold=True,
                                color=(0.13, 0.45, 0.85, 1), halign="center",
                                valign="middle", opacity=0,
                                size_hint=(None, None))
        self.banner_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        root.add_widget(self.banner_lbl)
        self._board_slot.bind(pos=self._sync_banner, size=self._sync_banner)

    def _sync_banner(self, *a):
        slot = self._board_slot
        self.banner_lbl.size = slot.size
        self.banner_lbl.pos = slot.pos

    def _sync_box(self, w, *a):
        self._box_rect.pos = (w.x + S(8), w.y + S(6))
        self._box_rect.size = (w.width - S(16), w.height - S(12))
        self._box_line.rectangle = (w.x + S(8), w.y + S(6),
                                    w.width - S(16), w.height - S(12))

    def _sync_board(self, *a):
        slot = self._board_slot
        if slot.width <= 0 or slot.height <= 0:
            return
        # Plein largeur, comme en partie : le plateau prend toute la largeur de
        # son emplacement ; les zones de ralliement (haut/bas) débordent
        # volontairement (comme sur l'écran de jeu).
        self.board_w.size = slot.size
        self.board_w.pos = slot.pos
        self.board_w._redraw()

    # ── Navigation ──
    def on_pre_enter(self, *a):
        # Normalement, entrer dans le tuto le recommence au début. Exception :
        # quand on revient du menu (Précédent au 1er temps de la visite), on
        # reprend à la dernière étape au lieu de tout recommencer.
        if getattr(self, "_returning_from_menu", False):
            self._returning_from_menu = False
        else:
            self.idx = 0
        self._show()

    def _grid_from_pieces(self, pieces):
        g = [[None] * ROWS for _ in range(COLS)]
        for (c, r, typ, camp) in pieces:
            ci = _TUTO_NOTES.index(c)
            g[ci][r - 1] = {"type": typ, "camp": camp}
        return g

    def _conv_cell(self, c, r):
        """(colonne, ligne 1..8 ou 'out') -> (colonne interne, ligne interne).
        'out' = ralliement du joueur (Blanc, en bas) = rangée 8 (hors plateau)."""
        ci = _TUTO_NOTES.index(c)
        ri = 8 if r == "out" else (r - 1)
        return (ci, ri)

    def _show(self):
        step = self.steps[self.idx]
        self.board = self._grid_from_pieces(step["pieces"])
        self.sel = None
        self.group_sel = set()
        self.fugued_heirs = []
        # Héritiers ayant fugué (illustration) : (colonne, camp) -> dessinés dans
        # le ralliement (haut pour Blanc, bas pour Noir).
        for (c, camp) in step.get("fugued", []):
            self.fugued_heirs.append({
                "col": _TUTO_NOTES.index(c),
                "row": ROWS if camp == "Blanc" else -1,
                "camp": camp,
            })
        self._step_done = False
        # Bannière de transition : grand texte centré, plateau masqué.
        if step.get("banner"):
            self.banner_lbl.text = step["banner"]
            self.banner_lbl.opacity = 1
            self.board_w.opacity = 0
        else:
            self.banner_lbl.opacity = 0
            self.board_w.opacity = 1
        self.mock_ui = step.get("mock_ui")   # faux éléments d'UI (illustration)
        self._phase = "select"
        self._moved_to = None
        self._seq_idx = 0
        self._grp_idx = 0
        self._push_idx = 0
        # Coordonnées internes du coup autorisé (étapes interactives)
        if step.get("interactive"):
            if step.get("maneuver"):
                step["_leader_internal"] = self._conv_cell(*step["leader"])
                step["_group_internal"] = [self._conv_cell(*g)
                                           for g in step.get("group_add", [])]
                step["_moveto_internal"] = self._conv_cell(*step["move_to"])
                step["_doneframe_internal"] = (
                    self._conv_cell(*step["done_frame"])
                    if step.get("done_frame") else None)
            elif step.get("push"):
                step["_leader_internal"] = self._conv_cell(*step["leader"])
                step["_moveto_internal"] = self._conv_cell(*step["move_to"])
                step["_pushto_internal"] = (self._conv_cell(*step["push_to"])
                                            if step.get("push_to") else None)
                if step.get("pushes"):
                    step["_pushes_internal"] = [
                        {"push_to": self._conv_cell(*p["push_to"]),
                         "text": p.get("text", "")}
                        for p in step["pushes"]]
                else:
                    step["_pushes_internal"] = None
                step["_doneframe_internal"] = (
                    self._conv_cell(*step["done_frame"])
                    if step.get("done_frame") else None)
            else:
                step["_move_internal"] = self._conv_cell(*step["move"])
                step["_dests_internal"] = [self._conv_cell(*d)
                                           for d in step.get("dests", [])]
                if step.get("sequence"):
                    step["_sequence_internal"] = [
                        {"dest": self._conv_cell(*s["dest"]), "text": s.get("text", "")}
                        for s in step["sequence"]
                    ]
                else:
                    step["_sequence_internal"] = None
        if step.get("menu_tour"):
            self._tour_idx = 0
            self._apply_menu_tour()  # visite du menu (mock UI + surbrillances)
        else:
            self._apply_phase()      # texte + annotations selon la phase
        self._refresh_nav()
        self._sync_board()

    def _apply_menu_tour(self):
        """Visite guidée du menu : dessine le faux menu et met en évidence
        l'élément décrit à l'étape courante (self._tour_idx)."""
        step = self.steps[self.idx]
        tour = step.get("tour", [])
        if not tour:
            return
        i = max(0, min(self._tour_idx, len(tour) - 1))
        stop = tour[i]
        circ = set(stop.get("circle", []))
        self.mock_ui = [dict(el, circle=(el.get("id") in circ))
                        for el in step.get("menu", [])]
        self.text_box.text = stop.get("text", "")
        try:
            self.board_w._redraw()
        except Exception:
            pass
        self._refresh_nav()

    def _refresh_nav(self):
        """Met à jour Précédent / Suivant + progression. Sur une étape
        interactive, Suivant reste bloqué tant que le bon coup n'est pas joué."""
        step = self.steps[self.idx]
        first = (self.idx == 0)
        last = (self.idx == len(self.steps) - 1)
        self.progress_lbl.text = "%d / %d" % (self.idx + 1, len(self.steps))
        self.prev_btn.disabled = first
        self.prev_btn.opacity = 0.35 if first else 1
        locked = bool(step.get("interactive")) and not self._step_done
        self.next_btn.disabled = locked
        self.next_btn.opacity = 0.35 if locked else 1
        # Au dernier temps, Suivant lance la visite du VRAI menu.
        self.next_btn.text = "Le menu >" if last else "Suivant >"

    def _prev(self):
        if self.idx > 0:
            self.idx -= 1
            self._show()

    def _next(self):
        if self.idx < len(self.steps) - 1:
            self.idx += 1
            self._show()
        else:
            self._launch_menu_tour()

    def _launch_menu_tour(self):
        """Passe au VRAI menu et affiche le calque-guide (visite du menu)."""
        try:
            menu = self.manager.get_screen("menu")
        except Exception:
            self._finish()
            return
        self.manager.current = "menu"
        # Petit délai pour laisser le menu s'afficher/se dimensionner avant de
        # dérouler la visite.
        Clock.schedule_once(lambda dt: menu.start_menu_tour(self), 0.2)

    def _return_from_menu_tour(self):
        """Retour au tuto depuis le calque (Précédent au 1er temps du menu)."""
        self.idx = len(self.steps) - 1
        self._returning_from_menu = True   # évite la remise à zéro dans on_pre_enter
        self.manager.current = "tuto"
        self._show()

    def _finish(self):
        try:
            save_config(tuto_seen="1")
        except Exception:
            pass
        self.manager.current = "menu"

    def _open_pause(self):
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
        popup = Popup(title="Pause", content=content, size_hint=(0.8, 0.42))

        def mk(label, fn, bg=COL_BTN_GREY):
            b = RoundButton(text=label, font_size=SF("16sp"), bold=True,
                            bg_color=bg, color=(1, 1, 1, 1), size_hint=(1, 0.5))
            b.bind(on_release=lambda *a: (popup.dismiss(), fn()))
            return b

        def _close():
            try:
                save_config(tuto_seen="1")
            except Exception:
                pass
            self.manager.current = "menu"

        content.add_widget(mk("Réglages", lambda: open_settings_popup(None)))
        content.add_widget(mk("Fermer le tuto", _close, bg=COL_ORANGE))
        popup.open()


# ── Plateau ──────────────────────────────────────────────────────────────────

class BoardWidget(Widget):
    NOTES = ["do", "ré", "mi", "fa", "sol", "la", "si"]

    # Propriété animée : avance de 0 à 1 pendant le glissement.
    _anim_t = NumericProperty(0.0)

    def __init__(self, game_screen, **kw):
        super().__init__(**kw)
        self.gs = game_screen
        # Données de l'animation en cours (None = aucune)
        self._anim = None
        # Couche de canvas dédiée aux pièces qui glissent (par-dessus le fond).
        # On la redessine seule pendant l'animation, sans tout reconstruire :
        # c'est beaucoup plus fluide.
        from kivy.graphics import Canvas
        self._anim_canvas = Canvas()
        self.bind(pos=self._redraw, size=self._redraw)
        # Quand la propriété animée change, on ne met à jour QUE la couche animée
        self.bind(_anim_t=lambda *a: self._redraw_anim_layer())

    def animate_slide(self, slides, on_done=None):
        """Anime le glissement de pièces. `slides` = liste de
        (piece_dict, (c0,r0), (c1,r1)). À la fin, appelle on_done().
        Si SLIDE_SPEED <= 0 : pas d'animation, on_done() direct + redraw.

        GARANTIE : on_done() est TOUJOURS appelé exactement une fois, même si
        l'animation échoue (téléphone lent, contexte graphique perdu...). Les
        règles du jeu (fugue, mat...) ne doivent jamais dépendre du succès
        d'une animation purement visuelle."""
        self._cancel_anim()

        # Drapeau anti double-appel partagé par tous les chemins de sortie
        done_holder = {"called": False}
        def _safe_done():
            if done_holder["called"]:
                return
            done_holder["called"] = True
            if on_done:
                try:
                    on_done()
                except Exception:
                    pass

        if SLIDE_SPEED <= 0.02 or not slides:
            _safe_done()
            self._redraw()
            return

        self._anim = {"slides": slides, "on_done": on_done}
        self._anim_t = 0.0
        self._redraw()

        def _finish(*a):
            self._anim = None
            _safe_done()
            self._redraw()

        try:
            anim = Animation(_anim_t=1.0, duration=max(0.05, SLIDE_SPEED),
                             transition="out_quad")
            anim.bind(on_complete=_finish)
            anim.start(self)
            # Filet de sécurité : si l'animation ne se termine jamais (frame
            # perdue, app en pause...), forcer la finalisation un peu après sa
            # durée prévue. _safe_done garantit qu'on n'exécute pas deux fois.
            try:
                Clock.schedule_once(lambda *a: _finish(),
                                    max(0.05, SLIDE_SPEED) + 0.5)
            except Exception:
                pass
        except Exception:
            # Impossible de lancer l'animation : appliquer directement.
            self._anim = None
            _safe_done()
            self._redraw()

    def _cancel_anim(self):
        """Arrête toute animation en cours et nettoie l'état."""
        try:
            Animation.cancel_all(self, "_anim_t")
        except Exception:
            pass
        self._anim = None

    def _geom(self):
        # Plateau en PLEINE LARGEUR : la taille de case est calée sur la largeur.
        # Les 8 rangées de jeu + 2 zones de ralliement (haut/bas) font 10*cs de
        # haut. Si ça dépasse la hauteur allouée au widget, les zones de
        # ralliement débordent (volontairement) dans les cadres infos.
        cs = self.width / COLS
        bw = cs * COLS
        bh = cs * EXT_ROWS
        ox = self.x + (self.width - bw) / 2
        oy = self.y + (self.height - bh) / 2
        return cs, ox, oy

    def _row_to_y(self, row, cs, oy):
        if self.gs.flipped:
            if row <= -1: return oy + (row + 1) * cs   # extrapole sous le plateau
            if row >= 8:  return oy + (row + 1) * cs    # extrapole au-dessus
            return oy + cs + row * cs
        else:
            if row <= -1: return oy + 9 * cs - (row + 1) * cs
            if row >= 8:  return oy - (row - 8) * cs
            return oy + cs + (ROWS - 1 - row) * cs

    def _col_to_x(self, col, cs, ox):
        """Colonne interne -> x écran. Pour le joueur Noir (flipped=False) le
        plateau est tourné à 180° (comme aux échecs) : les colonnes sont donc
        inversées (la colonne interne 0 'do' apparaît à DROITE)."""
        screen_col = col if self.gs.flipped else (COLS - 1 - col)
        return ox + screen_col * cs

    def _pixel_to_cell(self, px, py):
        cs, ox, oy = self._geom()
        if cs <= 0: return None
        screen_col = int((px - ox) // cs)
        if not (0 <= screen_col < COLS): return None
        # Inverser pour retrouver la colonne INTERNE (rotation 180° côté Noir)
        col = screen_col if self.gs.flipped else (COLS - 1 - screen_col)
        rel_y = py - oy
        if rel_y < 0 or rel_y >= EXT_ROWS * cs: return None
        if rel_y < cs:
            if col not in RALLY: return None
            return (col, -1 if self.gs.flipped else 8)
        elif rel_y < 9 * cs:
            rv = int((rel_y - cs) // cs)
            return (col, rv) if self.gs.flipped else (col, ROWS - 1 - rv)
        else:
            if col not in RALLY: return None
            return (col, 8 if self.gs.flipped else -1)

    def _redraw(self, *a):
        self.canvas.clear()
        if not self.gs.board: return
        cs, ox, oy = self._geom()
        self.gs._cs, self.gs._ox, self.gs._oy = cs, ox, oy

        top_color = COL_ORANGE if self.gs.flipped else COL_BLUE
        bot_color = COL_BLUE   if self.gs.flipped else COL_ORANGE

        rally_list = sorted(RALLY)
        rx_start = rally_list[0] * cs + ox
        rx_end   = (rally_list[-1] + 1) * cs + ox
        rad      = cs * 0.22

        with self.canvas:
            # Zone bas : arrondie en bas (extérieur), droite en haut (côté plateau)
            Color(*bot_color)
            RoundedRectangle(pos=(rx_start, oy),
                             size=(rx_end - rx_start, cs),
                             radius=[(0, 0), (0, 0), (rad, rad), (rad, rad)])
            # Zone haut : arrondie en haut (extérieur), droite en bas (côté plateau)
            Color(*top_color)
            RoundedRectangle(pos=(rx_start, oy + 9 * cs),
                             size=(rx_end - rx_start, cs),
                             radius=[(rad, rad), (rad, rad), (0, 0), (0, 0)])
            # Contour foncé (couleur du fond) autour des zones de ralliement,
            # pour que leur débordement éventuel dans les cadres infos paraisse
            # volontaire et net.
            Color(0.10, 0.10, 0.10, 1)
            Line(rounded_rectangle=(rx_start, oy, rx_end - rx_start, cs,
                                    0, 0, rad, rad), width=S(2))
            Line(rounded_rectangle=(rx_start, oy + 9 * cs, rx_end - rx_start, cs,
                                    rad, rad, 0, 0), width=S(2))

            # Plateau
            medieval_tex = (_theme_bg_texture("plateau.png")
                            if _theme_image_dir(CURRENT_THEME) else None)
            if medieval_tex is not None:
                # Fond image sur toute la surface du plateau. Le bas réel du
                # plateau est à oy + cs (la rangée oy est réservée au cadre info).
                Color(1, 1, 1, 1)
                Rectangle(texture=medieval_tex,
                          pos=(ox, oy + cs), size=(cs * COLS, cs * ROWS))
                # Juste les lignes de grille par-dessus
                for c in range(COLS):
                    for r in range(ROWS):
                        x = self._col_to_x(c, cs, ox)
                        y = self._row_to_y(r, cs, oy)
                        Color(*COL_GRID)
                        Line(rectangle=(x, y, cs, cs), width=S(1))
            else:
                for c in range(COLS):
                    for r in range(ROWS):
                        x = self._col_to_x(c, cs, ox)
                        y = self._row_to_y(r, cs, oy)
                        Color(*COL_BG_BOARD)
                        Rectangle(pos=(x, y), size=(cs, cs))
                        Color(*COL_GRID)
                        Line(rectangle=(x, y, cs, cs), width=S(1))

            # Logo central (contour seulement, sous les pièces)
            cx_m = ox + 3 * cs + cs / 2
            cy_m = oy + cs + 4 * cs
            r_m  = cs * 0.42       # un peu plus gros que l'ancien cercle
            draw_logo(self.canvas, cx_m, cy_m, r_m, colored=False, line_width=1.6)

        # ─ Annotations (chiffres et notes), AVANT les pièces pour qu'elles passent dessus ─
        self._draw_annotations(cs, ox, oy)

        # ─ Mise en évidence du dernier coup : contours autour des cases ─
        hl = getattr(self.gs, "_last_move_highlight", None)
        if hl is not None:
            highlight_cells = set(hl.get("from_cells", [])) | set(hl.get("to_cells", []))
            # Couleur : noir si la pièce qui a bougé est blanche, blanc sinon
            # On détermine la couleur en regardant l'une des cases d'arrivée
            hl_color = (1, 1, 1, 1)   # blanc par défaut
            for (hc, hr) in hl.get("to_cells", []):
                if 0 <= hc < COLS and 0 <= hr < ROWS:
                    pp = self.gs.board[hc][hr]
                    if pp is not None:
                        if pp["camp"] == "Blanc":
                            hl_color = (0, 0, 0, 1)   # noir pour coups blancs
                        else:
                            hl_color = (1, 1, 1, 1)   # blanc pour coups noirs
                        break
            with self.canvas:
                Color(*hl_color)
                for (hc, hr) in highlight_cells:
                    if 0 <= hc < COLS and 0 <= hr < ROWS:
                        x = self._col_to_x(hc, cs, ox)
                        y = self._row_to_y(hr, cs, oy)
                        # Cadre VERS L'EXTÉRIEUR : on agrandit le rectangle de ~2px
                        # pour qu'il englobe la case sans empiéter sur la pièce.
                        Line(rectangle=(x - 1, y - 1, cs + 2, cs + 2), width=S(2.4))

        # Cases dont la pièce est en cours d'animation : on ne les dessine PAS
        # à leur place normale (elles sont dessinées en position interpolée).
        anim_skip = set()
        if self._anim is not None:
            for (piece, c0r0, c1r1) in self._anim["slides"]:
                anim_skip.add(tuple(c1r1))   # case d'arrivée (board déjà à jour)

        for c in range(COLS):
            for r in range(ROWS):
                if (c, r) in anim_skip:
                    continue
                p = self.gs.board[c][r]
                if not p: continue
                x = self._col_to_x(c, cs, ox)
                y = self._row_to_y(r, cs, oy)
                is_imm_round  = self.gs.is_round(p)  and not self.gs.has_round_nbr(c, r)
                is_imm_square = self.gs.is_square(p) and not self.gs.has_square_nbr(c, r)
                is_imm = is_imm_round or is_imm_square
                outline = None; ow = 2
                if self.gs.sel == (c, r):
                    outline = COL_SEL_MAIN; ow = 4
                elif (c, r) in self.gs.group_sel:
                    outline = COL_SEL_GROUP; ow = 4
                elif is_imm:
                    outline = COL_IMMOBILE; ow = 3
                # Récupérer les directions de poussée à mettre en évidence
                push_dirs_for_cell = None
                if hl is not None:
                    push_dirs_for_cell = hl.get("push_dirs", {}).get((c, r))
                # Couleur multicolore fixe selon la position (colonne+rangée)
                rfrac = ((c * 3 + r * 5) % len(RAINBOW_PALETTE)) / (len(RAINBOW_PALETTE) - 1)
                draw_piece(self.canvas, x, y, cs, p,
                           outline=outline, outline_w=ow,
                           push_highlight_dirs=push_dirs_for_cell,
                           flipped=self.gs.flipped, rainbow_frac=rfrac)

        # Héritiers ayant fugué : dessinés en permanence dans leur ralliement.
        for h in getattr(self.gs, "fugued_heirs", []):
            hc, hr = h["col"], h["row"]
            x = self._col_to_x(hc, cs, ox)
            y = self._row_to_y(hr, cs, oy)
            draw_piece(self.canvas, x, y, cs,
                       {"type": "Héritier", "camp": h["camp"]},
                       outline=None, outline_w=2, flipped=self.gs.flipped)

        # Annotations du TUTORIEL (cadre de l'Héritier + flèche du coup). Dessinées
        # par-dessus le plateau. Sans effet hors tuto (l'écran de jeu n'a pas
        # d'attribut tuto_annotations).
        ann = getattr(self.gs, "tuto_annotations", None)
        if ann:
            with self.canvas:
                for (c, r) in ann.get("framed_ok", []):
                    x = self._col_to_x(c, cs, ox)
                    y = self._row_to_y(r, cs, oy)
                    Color(0.18, 0.72, 0.30, 1)
                    Line(rectangle=(x + cs * 0.03, y + cs * 0.03,
                                    cs * 0.94, cs * 0.94),
                         width=max(2.5, cs * 0.055))
                for (c, r) in ann.get("framed_blue", []):
                    x = self._col_to_x(c, cs, ox)
                    y = self._row_to_y(r, cs, oy)
                    Color(0.92, 0.55, 0.12, 1)       # orange = 2e groupe / Chevalier
                    Line(rectangle=(x + cs * 0.03, y + cs * 0.03,
                                    cs * 0.94, cs * 0.94),
                         width=max(2.5, cs * 0.055))
                for (c, r) in ann.get("framed_sel", []):
                    x = self._col_to_x(c, cs, ox)
                    y = self._row_to_y(r, cs, oy)
                    Color(0.13, 0.45, 0.85, 1)       # bleu = "clique ici"
                    Line(rectangle=(x + cs * 0.03, y + cs * 0.03,
                                    cs * 0.94, cs * 0.94),
                         width=max(2.5, cs * 0.055))
                # Traits de liaison (montre les liens d'un groupe, dont diagonaux)
                for lk in ann.get("links", []):
                    Color(*lk.get("color", (0.4, 0.4, 0.4)), 1)
                    for (a, b) in lk.get("pairs", []):
                        xa = self._col_to_x(a[0], cs, ox) + cs / 2
                        ya = self._row_to_y(a[1], cs, oy) + cs / 2
                        xb = self._col_to_x(b[0], cs, ox) + cs / 2
                        yb = self._row_to_y(b[1], cs, oy) + cs / 2
                        Line(points=[xa, ya, xb, yb],
                             width=max(2.5, cs * 0.05), cap="round")
                for (c, r) in ann.get("framed", []):
                    x = self._col_to_x(c, cs, ox)
                    y = self._row_to_y(r, cs, oy)
                    Color(0.90, 0.22, 0.22, 1)
                    Line(rectangle=(x + cs * 0.03, y + cs * 0.03,
                                    cs * 0.94, cs * 0.94),
                         width=max(2.5, cs * 0.05))
                aw = max(3, cs * 0.06)
                for (p0, p1) in ann.get("arrows", []):
                    x0 = self._col_to_x(p0[0], cs, ox) + cs / 2
                    y0 = self._row_to_y(p0[1], cs, oy) + cs / 2
                    x1 = self._col_to_x(p1[0], cs, ox) + cs / 2
                    y1 = self._row_to_y(p1[1], cs, oy) + cs / 2
                    Color(0.16, 0.42, 0.72, 1)
                    Line(points=[x0, y0, x1, y1], width=aw, cap="round")
                    ang = math.atan2(y1 - y0, x1 - x0)
                    ah = cs * 0.34
                    for da in (math.radians(148), math.radians(-148)):
                        Line(points=[x1, y1,
                                     x1 + ah * math.cos(ang + da),
                                     y1 + ah * math.sin(ang + da)],
                             width=aw, cap="round")


        # Faux éléments d'interface (illustration : bouton nulle/abandon, timer,
        # label déconnecté). Sans effet en jeu (l'écran de jeu n'a pas de mock_ui).
        mock = getattr(self.gs, "mock_ui", None)
        if mock:
            from kivy.core.text import Label as _CoreLabel
            W, H = self.width, self.height
            for el in mock:
                w = el.get("fw", 0.25) * W
                h = el.get("fh", 0.07) * H
                cx = self.x + el.get("fx", 0.5) * W
                cy = self.y + el.get("fy", 0.5) * H
                rx, ry = cx - w / 2, cy - h / 2
                bg = el.get("bg", (0.20, 0.22, 0.28))
                with self.canvas:
                    Color(*bg, 1)
                    RoundedRectangle(pos=(rx, ry), size=(w, h), radius=[h * 0.28])
                    Color(1, 1, 1, 0.9)
                    Line(rounded_rectangle=(rx, ry, w, h, h * 0.28), width=1.4)
                cl = _CoreLabel(text=el.get("text", ""),
                                font_size=max(11, h * 0.48), bold=True)
                cl.refresh()
                tex = cl.texture
                tw, th = tex.size
                with self.canvas:
                    Color(*el.get("fg", (1, 1, 1)), 1)
                    Rectangle(texture=tex, pos=(cx - tw / 2, cy - th / 2),
                              size=(tw, th))
                if el.get("circle"):
                    mw, mh = w * 1.22, h * 1.7
                    with self.canvas:
                        Color(0.90, 0.22, 0.22, 1)
                        Line(ellipse=(cx - mw / 2, cy - mh / 2, mw, mh), width=2.6)

        # Couche animée : on l'ajoute au canvas (dessinée par-dessus le fond).
        # Elle est mise à jour seule pendant l'animation via _redraw_anim_layer.
        if self._anim_canvas not in self.canvas.children:
            self.canvas.add(self._anim_canvas)
        self._redraw_anim_layer()

    def _redraw_anim_layer(self):
        """Redessine UNIQUEMENT la couche des pièces qui glissent.
        Appelé à chaque frame d'animation : ne reconstruit pas tout le plateau,
        d'où une bien meilleure fluidité.
        Un masque (stencil) limite le dessin à la zone des 8 rangées de jeu :
        une pièce éjectée vers le haut/bas disparaît donc 'derrière le bord du
        plateau', comme celles éjectées sur les côtés gauche/droite."""
        self._anim_canvas.clear()
        if self._anim is None:
            return
        from kivy.graphics import (StencilPush, StencilUse, StencilUnUse,
                                    StencilPop, Rectangle as _Rect)
        cs, ox, oy = self._geom()
        te = self._anim_t
        # Zone de JEU uniquement (8 rangées, sans les ralliements). Toute pièce
        # qui glisse au-delà (éjection vers un bord, y compris poussée dans un
        # ralliement si ce n'est pas un Héritier) disparaît 'derrière le bord'.
        # Les Héritiers qui fuguent sont dessinés à part (hors de ce clip).
        clip_x = self.x
        clip_w = self.width
        clip_y = oy + cs          # bas de la 1re rangée de jeu
        clip_h = ROWS * cs        # hauteur des 8 rangées de jeu
        # On sépare les pièces animées : les Héritiers qui glissent dans une
        # zone de ralliement (fugue) restent visibles (dessinés HORS du clip) ;
        # toutes les autres sont clippées à la zone de jeu.
        clipped = []
        unclipped = []
        for (piece, (c0, r0), (c1, r1)) in self._anim["slides"]:
            is_heir_to_rally = (piece.get("type") == "Héritier"
                                and (r1 >= 8 or r1 <= -1))
            if is_heir_to_rally:
                unclipped.append((piece, (c0, r0), (c1, r1)))
            else:
                clipped.append((piece, (c0, r0), (c1, r1)))

        def _draw_one(piece, c0, r0, c1, r1):
            x0 = self._col_to_x(c0, cs, ox); y0 = self._row_to_y(r0, cs, oy)
            x1 = self._col_to_x(c1, cs, ox); y1 = self._row_to_y(r1, cs, oy)
            xa = x0 + (x1 - x0) * te
            ya = y0 + (y1 - y0) * te
            draw_piece(self._anim_canvas, xa, ya, cs, piece,
                       outline=None, outline_w=2, flipped=self.gs.flipped)

        # Pièces clippées (jeu + éjections coupées au bord)
        if clipped:
            with self._anim_canvas:
                StencilPush()
                _Rect(pos=(clip_x, clip_y), size=(clip_w, clip_h))
                StencilUse()
            for (piece, (c0, r0), (c1, r1)) in clipped:
                _draw_one(piece, c0, r0, c1, r1)
            with self._anim_canvas:
                StencilUnUse()
                _Rect(pos=(clip_x, clip_y), size=(clip_w, clip_h))
                StencilPop()

        # Héritiers en fugue : dessinés sans clip, restent visibles
        for (piece, (c0, r0), (c1, r1)) in unclipped:
            _draw_one(piece, c0, r0, c1, r1)

    def _draw_text(self, text, x, y, font_size, color, anchor="center"):
        """Dessine du texte dans le canvas à (x,y).
        anchor: 'center', 'bottom-left', 'top-center', etc."""
        cl = CoreLabel(text=text, font_size=font_size, bold=True, color=color)
        cl.refresh()
        tex = cl.texture
        tw, th = tex.size
        # Calcul du coin bas-gauche selon l'ancre
        if anchor == "center":
            dx, dy = x - tw / 2, y - th / 2
        elif anchor == "bottom-left":
            dx, dy = x, y
        elif anchor == "top-center":
            dx, dy = x - tw / 2, y - th
        else:
            dx, dy = x, y
        with self.canvas:
            Color(*color)
            Rectangle(texture=tex, pos=(dx, dy), size=(tw, th))

    def _draw_annotations(self, cs, ox, oy):
        """Dessine les chiffres 1-8 et les notes do-si. Cohérent avec la rotation
        180° côté Noir : chaque note NOTES[c] est dessinée à la position écran de
        sa colonne interne (_col_to_x), et les chiffres dans la colonne qui se
        trouve visuellement à gauche."""
        fs_num  = max(10, cs * 0.20)
        fs_note = max(11, cs * 0.26)

        # Colonne dont la position écran est la plus à GAUCHE.
        # flipped=True  : colonne interne 0 à gauche. flipped=False : colonne 6.
        col_left = 0 if self.gs.flipped else (COLS - 1)

        # Chiffres 1 à 8 dans l'angle bas-gauche de la colonne de gauche
        for r in range(ROWS):
            num = r + 1   # 1 = côté Blanc, 8 = côté Noir
            x_cell = self._col_to_x(col_left, cs, ox)
            y_cell = self._row_to_y(r, cs, oy)
            self._draw_text(str(num),
                            x_cell + cs * 0.08,
                            y_cell + cs * 0.04,
                            font_size=fs_num,
                            color=(0, 0, 0, 1),
                            anchor="bottom-left")

        # Notes do-si sous le plateau, chacune sous SA colonne
        y_note = oy + cs * 0.80
        for c in range(COLS):
            note = self.NOTES[c]
            x_cell_center = self._col_to_x(c, cs, ox) + cs / 2
            self._draw_text(note,
                            x_cell_center,
                            y_note,
                            font_size=fs_note,
                            color=(1, 1, 1, 1),
                            anchor="center")

    def on_touch_down(self, touch):
        if not self.collide_point(*touch.pos): return False
        cell = self._pixel_to_cell(touch.x, touch.y)
        if cell: self.gs.handle_cell(*cell)
        return True


# ── Popups pause / abandon ───────────────────────────────────────────────────

def open_pause_popup(game):
    """Pause visuelle mais le chrono du joueur au trait continue (anti-triche)."""
    content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(16))
    title_lbl = Label(text="Pause", font_size=SF("20sp"), bold=True,
                      color=(1, 1, 1, 1), size_hint=(1, 0.14),
                      halign="center", valign="middle")
    title_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(title_lbl)
    info_lbl = Label(
        text="Le chrono du joueur au trait continue à s'écouler.",
        font_size=SF("13sp"), italic=True, color=(0.8, 0.8, 0.8, 1),
        size_hint=(1, 0.20), halign="center", valign="middle")
    info_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(info_lbl)
    btn_resume = RoundButton(text="Reprendre", bg_color=COL_ORANGE,
                             color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                             size_hint=(1, 0.18))
    btn_settings = RoundButton(text="Réglages", bg_color=COL_BTN_GREY,
                               color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                               size_hint=(1, 0.18))
    # En correspondance : pas de "match" (partie unique), donc le bouton ne
    # propose pas d'annuler/abandonner mais simplement de revenir au menu (la
    # partie reste en cours sur le serveur, on y reviendra plus tard).
    # EN LIGNE (matchmaking/défi) : pas de bouton "Annuler le match" ici, on
    # abandonne la PARTIE via le bouton [×], et on met fin au MATCH entre deux
    # parties via "Quitter le match". Inutile de dupliquer dans la pause.
    _is_corr_pause = getattr(game, "corr_mode", False)
    _is_online_pause = getattr(game, "online_mode", False)
    btn_quit = None
    if not _is_online_pause:
        btn_quit = RoundButton(text=("Revenir au menu" if _is_corr_pause
                                     else "Annuler le match"),
                               bg_color=COL_BLUE,
                               color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                               size_hint=(1, 0.18))
    content.add_widget(btn_resume)
    content.add_widget(btn_settings)
    if btn_quit is not None:
        content.add_widget(btn_quit)
    # Popup un peu plus court s'il n'y a que deux boutons
    p = Popup(title="", content=content,
              size_hint=(0.82, 0.44 if _is_online_pause else 0.52),
              separator_height=0, auto_dismiss=False)

    def _refresh_pause_theme(*a):
        """Réapplique les couleurs de thème aux boutons du popup pause
        (utile après un changement de thème via le sous-menu Réglages)."""
        btn_resume.set_bg(COL_ORANGE)
        btn_settings.set_bg(COL_BTN_GREY)
        if btn_quit is not None:
            btn_quit.set_bg(COL_BLUE)
    # Mémoriser pour pouvoir rafraîchir depuis les Réglages
    game._pause_theme_refresh = _refresh_pause_theme

    def _on_quit(*a):
        if getattr(game, "corr_mode", False):
            # Correspondance : revenir au menu SANS abandonner.
            p.dismiss()
            game._back_to_menu()
        else:
            _confirm_cancel_match(game, p)

    btn_resume.bind(on_release=lambda *a: p.dismiss())
    btn_settings.bind(on_release=lambda *a: open_settings_popup(game))
    if btn_quit is not None:
        btn_quit.bind(on_release=_on_quit)
    p.open()


def _confirm_cancel_match(game, pause_popup):
    """Demande confirmation avant d'annuler le match en cours.
    En ligne / correspondance : annuler = ABANDON (déshonneur). Le joueur perd,
    l'adversaire gagne (et prend les points mélo de cette partie en ligne)."""
    is_online = getattr(game, "online_mode", False)
    is_corr = getattr(game, "corr_mode", False)
    content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(16))
    t = Label(text="Annuler le match ?", font_size=SF("18sp"), bold=True,
              color=(1, 1, 1, 1), size_hint=(1, 0.3),
              halign="center", valign="middle")
    t.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(t)
    if is_online:
        msg = ("Abandonner compte comme une DÉFAITE.\n"
               "Votre adversaire gagne les points.")
    elif is_corr:
        msg = ("Abandonner compte comme une défaite\n"
               "dans cette partie de correspondance.")
    else:
        msg = "La partie en cours sera perdue."
    info = Label(text=msg, font_size=SF("13sp"), color=(0.85, 0.85, 0.85, 1),
                 size_hint=(1, 0.25), halign="center", valign="middle")
    info.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(info)
    row = BoxLayout(orientation="horizontal", size_hint=(1, 0.32), spacing=S(8))
    b_no  = RoundButton(text="Continuer", bg_color=COL_BTN_GREY,
                        color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                        size_hint=(0.5, 1))
    b_yes = RoundButton(text="Abandonner" if (is_online or is_corr) else "Annuler le match",
                        bg_color=COL_BLUE, color=(1, 1, 1, 1),
                        font_size=SF("15sp"), bold=True, size_hint=(0.5, 1))
    row.add_widget(b_no)
    row.add_widget(b_yes)
    content.add_widget(row)
    cp = Popup(title="", content=content, size_hint=(0.82, 0.42),
               separator_height=0, auto_dismiss=False)
    b_no.bind(on_release=lambda *a: cp.dismiss())

    def _do_cancel(*a):
        cp.dismiss()
        pause_popup.dismiss()
        # En ligne / correspondance : déclencher l'abandon (le joueur local perd)
        if is_online and not getattr(game, "_game_over", False):
            game._end_game_by_color(loser_color=game.online_my_color,
                                    method="abandon")
            return  # _end_game_by_color gère la suite (popup + retour)
        if is_corr:
            try:
                ONLINE.corr_abandon(game.corr_game_id)
            except Exception:
                pass
        game._back_to_menu()
    b_yes.bind(on_release=_do_cancel)
    cp.open()


def open_abandon_popup(game, which):
    """which = 'top' ou 'bot', indique quel joueur clique pour abandonner."""
    # On regarde quel joueur est affiché sur cette barre
    if which == "top":
        camp = "Noir"  if game.flipped else "Blanc"
    else:
        camp = "Blanc" if game.flipped else "Noir"
    abandoning = game._player_of(camp)

    content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(16))
    t = Label(text="Abandonner ?", font_size=SF("18sp"), bold=True,
              color=(1, 1, 1, 1), size_hint=(1, 0.18),
              halign="center", valign="middle")
    t.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(t)
    info = Label(
        text=f"{abandoning} confirme abandonner. L'adversaire marquera 2 points.",
        font_size=SF("13sp"), color=(0.85, 0.85, 0.85, 1),
        size_hint=(1, 0.26), halign="center", valign="middle")
    info.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(info)
    btn_no  = RoundButton(text="Annuler", bg_color=COL_BTN_GREY,
                          color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                          size_hint=(1, 0.22))
    btn_yes = RoundButton(text="Oui, abandonner", bg_color=(0.7, 0.15, 0.15, 1),
                          color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                          size_hint=(1, 0.22))
    content.add_widget(btn_no)
    content.add_widget(btn_yes)
    p = Popup(title="", content=content, size_hint=(0.82, 0.48),
              separator_height=0, auto_dismiss=False)
    btn_no.bind(on_release=lambda *a: p.dismiss())
    btn_yes.bind(on_release=lambda *a: (p.dismiss(),
                                         game._end_game_by_color(loser_color=camp,
                                                                 method="abandon")))
    p.open()


# ── Intelligence artificielle "deep grey" ────────────────────────────────────
#
# Moteur indépendant travaillant sur des copies de plateau (listes de listes).
# Un "board" est board[col][row] = None ou {"type":..., "camp":...}.
# deep grey raisonne à 2 coups de profondeur avec un système de scores pondérés.

def _dg_clone(board):
    # Les pièces (dicts {"type","camp"}) ne sont jamais modifiées en place dans
    # le moteur : on déplace les références, on ne mute pas leur contenu. On peut
    # donc partager les références de pièces et ne copier que la structure des
    # colonnes. Beaucoup plus rapide que dict(p) pour chaque pièce, et strictement
    # équivalent en résultat (vérifié : aucun p["type"]=... dans le code).
    return [col[:] for col in board]

def _dg_on_board(c, r):
    return 0 <= c < COLS and 0 <= r < ROWS

def _dg_is_round(p):
    return p is not None and p["type"] in ("Nurse", "Héritier")

def _dg_is_square(p):
    return p is not None and p["type"] in ("Soldat", "Garde")

def _dg_has_allied_knight_nbr(board, c, r):
    """True si la pièce en (c,r) est adjacente à un Chevalier du même camp."""
    p = board[c][r]
    if not p:
        return False
    camp = p["camp"]
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == dr == 0: continue
            nc, nr = c + dc, r + dr
            if _dg_on_board(nc, nr):
                q = board[nc][nr]
                if q and q["type"] == "Chevalier" and q["camp"] == camp:
                    return True
    return False

def _dg_has_round_nbr(board, c, r):
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == dr == 0: continue
            nc, nr = c + dc, r + dr
            if _dg_on_board(nc, nr) and _dg_is_round(board[nc][nr]):
                return True
    return False

def _dg_has_square_nbr(board, c, r):
    for dc in (-1, 0, 1):
        for dr in (-1, 0, 1):
            if dc == dr == 0: continue
            nc, nr = c + dc, r + dr
            if _dg_on_board(nc, nr) and _dg_is_square(board[nc][nr]):
                return True
    return False

def _dg_group_of(board, c, r):
    p = board[c][r]
    if not _dg_is_square(p): return set()
    camp = p["camp"]
    seen = {(c, r)}; stack = [(c, r)]
    while stack:
        x, y = stack.pop()
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                if dx == dy == 0: continue
                nx, ny = x + dx, y + dy
                if (nx, ny) in seen: continue
                if not _dg_on_board(nx, ny): continue
                q = board[nx][ny]
                if _dg_is_square(q) and q["camp"] == camp:
                    seen.add((nx, ny)); stack.append((nx, ny))
    return seen

def _dg_rally_row(camp):
    return 8 if camp == "Blanc" else -1

def _dg_is_fugue_dest(c, r, piece):
    if piece["type"] != "Héritier": return False
    if c not in RALLY: return False
    return r == _dg_rally_row(piece["camp"])

def _dg_push_activated(ptype, dc, dr):
    if ptype == "Soldat": return abs(dc) + abs(dr) == 1
    if ptype == "Garde":  return abs(dc) == abs(dr) == 1
    return False

def dg_generate_moves(board, camp):
    """Génère tous les coups légaux pour `camp`.
    Chaque coup = dict {board: nouveau_board, kind: ..., fugue: bool, mat_on: camp|None,
                        ejected: int, moved_cells: [...]}.
    On ne simule PAS les sous-choix de poussée multiples : on pousse toutes les
    directions activées (comportement simple, suffisant pour l'IA)."""
    moves = []
    opp = "Noir" if camp == "Blanc" else "Blanc"

    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if not p or p["camp"] != camp:
                continue

            # ── Pièces rondes (Nurse, Héritier) ──
            if _dg_is_round(p):
                if not _dg_has_round_nbr(board, c, r):
                    continue   # isolée → immobile
                # Déplacements simples (8 directions, 1 case)
                for dc in (-1, 0, 1):
                    for dr in (-1, 0, 1):
                        if dc == dr == 0: continue
                        nc, nr = c + dc, r + dr
                        # Fugue ?
                        if p["type"] == "Héritier" and _dg_is_fugue_dest(nc, nr, p):
                            nb = _dg_clone(board)
                            nb[c][r] = None
                            moves.append({"board": nb, "kind": "fugue",
                                          "fugue": True, "mat_on": None,
                                          "ejected": 0, "moved_cells": [(nc, nr)],
                                          "from": (c, r)})
                            continue
                        if not _dg_on_board(nc, nr): continue
                        if board[nc][nr] is not None: continue
                        nb = _dg_clone(board)
                        nb[nc][nr] = nb[c][r]; nb[c][r] = None
                        moves.append({"board": nb, "kind": "move",
                                      "fugue": False, "mat_on": None,
                                      "ejected": 0, "moved_cells": [(nc, nr)],
                                      "from": (c, r)})
                # Sauts simples ET multisauts : exploration récursive en
                # maintenant un board simulé. Règle : on ne peut pas re-sauter
                # IMMÉDIATEMENT par-dessus la même nurse qu'au saut précédent
                # (mais on peut la re-sauter plus tard).
                start = (c, r)
                start_piece = board[c][r]
                sim_board = _dg_clone(board)
                sim_board[c][r] = None
                # to_explore : (pos, visited_cases, last_jumped_cell_or_None)
                to_explore = [(c, r, frozenset({(c, r)}), None)]
                jump_destinations = set()
                while to_explore:
                    cur_c, cur_r, visited, last_jumped = to_explore.pop()
                    for jdc in (-1, 0, 1):
                        for jdr in (-1, 0, 1):
                            if jdc == 0 and jdr == 0: continue
                            mc, mr = cur_c + jdc, cur_r + jdr       # case sautée
                            nc, nr = cur_c + 2*jdc, cur_r + 2*jdr   # case d'arrivée

                            # Règle anti-aller-retour : on ne peut pas re-sauter
                            # immédiatement par-dessus la nurse qu'on vient de sauter
                            if last_jumped is not None and (mc, mr) == last_jumped:
                                continue

                            # Cas fugue par saut (Héritier seulement)
                            if start_piece["type"] == "Héritier" and \
                               _dg_is_fugue_dest(nc, nr, start_piece):
                                if _dg_on_board(mc, mr) and \
                                   _dg_is_round(sim_board[mc][mr]):
                                    nb = _dg_clone(board)
                                    nb[c][r] = None
                                    moves.append({"board": nb, "kind": "fugue",
                                                  "fugue": True, "mat_on": None,
                                                  "ejected": 0,
                                                  "moved_cells": [(nc, nr)],
                                                  "from": (c, r)})
                                continue

                            if not _dg_on_board(mc, mr): continue
                            if not _dg_on_board(nc, nr): continue
                            jumped = sim_board[mc][mr]
                            if jumped is None: continue
                            if not _dg_is_round(jumped): continue
                            if sim_board[nc][nr] is not None: continue
                            if (nc, nr) in visited: continue

                            if (nc, nr) not in jump_destinations:
                                jump_destinations.add((nc, nr))
                                nb = _dg_clone(board)
                                nb[nc][nr] = nb[c][r]; nb[c][r] = None
                                moves.append({"board": nb, "kind": "jump",
                                              "fugue": False, "mat_on": None,
                                              "ejected": 0,
                                              "moved_cells": [(nc, nr)],
                                              "from": (c, r)})
                            # On note la nurse qui vient d'être sautée
                            to_explore.append((nc, nr, visited | {(nc, nr)}, (mc, mr)))

            # ── Pièces carrées (Soldat, Garde) ──
            elif _dg_is_square(p):
                if not _dg_has_square_nbr(board, c, r):
                    continue   # isolée → immobile
                # Déplacement simple + poussée éventuelle
                for dc in (-1, 0, 1):
                    for dr in (-1, 0, 1):
                        if dc == dr == 0: continue
                        nc, nr = c + dc, r + dr
                        if not _dg_on_board(nc, nr): continue
                        if board[nc][nr] is not None: continue
                        nb = _dg_clone(board)
                        nb[nc][nr] = nb[c][r]; nb[c][r] = None
                        # Poussée activée ?
                        if _dg_push_activated(p["type"], dc, dr):
                            # Identifier les directions où il y a effectivement
                            # une pièce à pousser (case adjacente non vide).
                            if p["type"] == "Soldat":
                                all_push_dirs = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
                            else:
                                all_push_dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
                            available_dirs = []
                            for pdc, pdr in all_push_dirs:
                                ac, ar = nc + pdc, nr + pdr
                                if _dg_on_board(ac, ar) and nb[ac][ar] is not None:
                                    available_dirs.append((pdc, pdr))
                            # Toujours générer le déplacement sans pousser
                            moves.append({"board": _dg_clone(nb), "kind": "square",
                                          "fugue": False, "fugue_by": None,
                                          "mat_on": None,
                                          "ej_ally": 0, "ej_opp": 0,
                                          "ejected": 0, "total_pushed": 0,
                                          "push_dirs_used": [],
                                          "moved_cells": [(nc, nr)], "from": (c, r)})
                            # Puis générer toutes les combinaisons non vides
                            n_dirs = len(available_dirs)
                            for mask in range(1, 1 << n_dirs):
                                chosen = [available_dirs[i] for i in range(n_dirs)
                                          if mask & (1 << i)]
                                nb_var = _dg_clone(nb)
                                ej_ally, ej_opp, mat_on, fugue_by, total_pushed = (
                                    _dg_apply_pushes(nb_var, nc, nr, p["type"], camp,
                                                     dirs_to_use=chosen))
                                moves.append({"board": nb_var, "kind": "square",
                                              "fugue": False, "fugue_by": fugue_by,
                                              "mat_on": mat_on,
                                              "ej_ally": ej_ally, "ej_opp": ej_opp,
                                              "ejected": ej_ally + ej_opp,
                                              "total_pushed": total_pushed,
                                              "push_dirs_used": chosen,
                                              "moved_cells": [(nc, nr)], "from": (c, r)})
                        else:
                            # Poussée non activée : juste le déplacement
                            moves.append({"board": nb, "kind": "square",
                                          "fugue": False, "fugue_by": None,
                                          "mat_on": None,
                                          "ej_ally": 0, "ej_opp": 0,
                                          "ejected": 0, "total_pushed": 0,
                                          "push_dirs_used": [],
                                          "moved_cells": [(nc, nr)], "from": (c, r)})
                # Manœuvres de groupe (déplacer tout le groupe d'1 case)
                grp = _dg_group_of(board, c, r)
                if len(grp) >= 2:
                    for dc in (-1, 0, 1):
                        for dr in (-1, 0, 1):
                            if dc == dr == 0: continue
                            ok = True
                            for (gc, gr) in grp:
                                tc, tr = gc + dc, gr + dr
                                if not _dg_on_board(tc, tr): ok = False; break
                                tgt = board[tc][tr]
                                if tgt is not None and (tc, tr) not in grp:
                                    ok = False; break
                            if not ok: continue
                            nb = _dg_clone(board)
                            pieces = {(gc, gr): nb[gc][gr] for (gc, gr) in grp}
                            for (gc, gr) in grp:
                                nb[gc][gr] = None
                            for (gc, gr), pp in pieces.items():
                                nb[gc + dc][gr + dr] = pp
                            # Maître = (c, r) (la case d'origine du scan).
                            # moved_cells doit avoir le maître en premier pour
                            # que la notation/highlight parse correctement.
                            moved = [(c + dc, r + dr)]
                            for (gc, gr) in grp:
                                if (gc, gr) == (c, r): continue
                                moved.append((gc + dc, gr + dr))
                            from_cells_ordered = [(c, r)]
                            for (gc, gr) in grp:
                                if (gc, gr) == (c, r): continue
                                from_cells_ordered.append((gc, gr))
                            moves.append({"board": nb, "kind": "maneuver",
                                          "fugue": False, "mat_on": None,
                                          "ejected": 0, "moved_cells": moved,
                                          "from_cells": from_cells_ordered,
                                          "from": (c, r)})

            # ── Chevalier ──
            # Le Chevalier se déplace d'1 case dans les 8 directions, vers une
            # case vide, sans condition de voisinage et sans pousser. Il est
            # immortel (il ne peut pas être éjecté), mais il PEUT bloquer.
            elif p["type"] == "Chevalier":
                for dc in (-1, 0, 1):
                    for dr in (-1, 0, 1):
                        if dc == dr == 0: continue
                        nc, nr = c + dc, r + dr
                        if not _dg_on_board(nc, nr): continue
                        if board[nc][nr] is not None: continue
                        nb = _dg_clone(board)
                        nb[nc][nr] = nb[c][r]; nb[c][r] = None
                        moves.append({"board": nb, "kind": "knight",
                                      "fugue": False, "fugue_by": None,
                                      "mat_on": None, "ejected": 0,
                                      "moved_cells": [(nc, nr)], "from": (c, r)})
    return moves


def _dg_apply_pushes(board, c, r, ptype, camp, dirs_to_use=None):
    """Applique les poussées (lignes entières) depuis (c,r) après le déplacement.
    Si dirs_to_use est fourni : ne pousse que dans ce sous-ensemble de directions.
    Sinon : pousse dans toutes les directions de poussée activées.
    Retourne (ej_ally, ej_opp, mat_on, fugue_by, total_pushed)."""
    opp = "Noir" if camp == "Blanc" else "Blanc"
    if ptype == "Soldat":
        all_dirs = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
    else:
        all_dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    dirs = dirs_to_use if dirs_to_use is not None else all_dirs
    ej_ally = 0
    ej_opp = 0
    mat_on = None
    fugue_by = None
    total_pushed = 0
    for dc, dr in dirs:
        # Construire la ligne de pièces consécutives depuis (c+dc, r+dr)
        line = []
        cc, rr = c + dc, r + dr
        while _dg_on_board(cc, rr):
            p = board[cc][rr]
            if p is None: break
            if p["type"] == "Chevalier":
                line = None
                break
            line.append((cc, rr, p))
            cc += dc; rr += dr
        if not line:
            continue
        for cc, rr, p in reversed(line):
            nc2, nr2 = cc + dc, rr + dr
            board[cc][rr] = None
            if _dg_on_board(nc2, nr2):
                board[nc2][nr2] = p
                total_pushed += 1
            else:
                if p["type"] == "Héritier" and nc2 in RALLY and (
                    (p["camp"] == "Blanc" and nr2 == 8) or
                    (p["camp"] == "Noir"  and nr2 == -1)):
                    fugue_by = p["camp"]
                elif p["type"] == "Héritier":
                    mat_on = p["camp"]
                    if p["camp"] == camp: ej_ally += 1
                    else:                  ej_opp += 1
                else:
                    if p["camp"] == camp: ej_ally += 1
                    else:                  ej_opp += 1
                total_pushed += 1
    return ej_ally, ej_opp, mat_on, fugue_by, total_pushed


def dg_count_isolated(board, camp):
    """Compte les pièces de `camp` actuellement isolées (immobilisées)."""
    n = 0
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if not p or p["camp"] != camp: continue
            if _dg_is_round(p) and not _dg_has_round_nbr(board, c, r):
                n += 1
            elif _dg_is_square(p) and not _dg_has_square_nbr(board, c, r):
                n += 1
    return n


def dg_round_clusters(board, camp):
    """Compte le nombre de groupes connectés de pièces rondes (Nurse/Héritier)
    pour `camp`. Plus le nombre est petit, plus les rondes sont en un seul bloc.
    Renvoie aussi le nombre total de rondes."""
    visited = set()
    clusters = 0
    total = 0
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if not p or p["camp"] != camp or not _dg_is_round(p): continue
            total += 1
            if (c, r) in visited: continue
            clusters += 1
            stack = [(c, r)]
            visited.add((c, r))
            while stack:
                x, y = stack.pop()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == dy == 0: continue
                        nx, ny = x + dx, y + dy
                        if (nx, ny) in visited: continue
                        if not _dg_on_board(nx, ny): continue
                        q = board[nx][ny]
                        if q and q["camp"] == camp and _dg_is_round(q):
                            visited.add((nx, ny))
                            stack.append((nx, ny))
    return clusters, total

def dg_advance_score(board, camp):
    """Score d'avancement : plus les pièces rondes de `camp` sont proches du
    ralliement adverse, mieux c'est. L'Héritier compte ×1,5 (objectif principal)."""
    rally = _dg_rally_row(camp)
    score = 0.0
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if not p or p["camp"] != camp: continue
            if _dg_is_round(p):
                dist = abs(r - rally)
                # Poids spécial Héritier : avancée vers la victoire = priorité
                weight = 1.5 if p["type"] == "Héritier" else 1.0
                score += (8 - dist) * weight
                # Bonus centrage : si la pièce ronde est encore de son côté
                own_side_row = 0 if camp == "Blanc" else 7
                on_own_side = abs(r - own_side_row) < abs(r - (7 - own_side_row))
                if on_own_side:
                    centrality = 3 - abs(c - 3)
                    score += centrality * 0.6 * weight
    return score

def dg_square_advance_score(board, camp):
    """Petit score pour rapprocher les carrées du centre (préparer poussées)."""
    score = 0.0
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if not p or p["camp"] != camp: continue
            if _dg_is_square(p):
                # bonus si la carrée a des voisines (groupe), favorise cohésion
                if _dg_has_square_nbr(board, c, r):
                    score += 1.0
    return score


def _dg_board_key(board):
    """Clé compacte d'une position (pour le cache d'évaluation et le livre
    d'ouvertures). Encode type+camp de chaque case, ou '.' si vide."""
    parts = []
    for c in range(COLS):
        col = board[c]
        for r in range(ROWS):
            p = col[r]
            if p is None:
                parts.append(".")
            else:
                parts.append(p["type"][0] + p["camp"][0])
    return "".join(parts)


def _dg_position_key(board, camp):
    """Clé d'une position incluant le camp au trait (anti-répétition)."""
    return _dg_board_key(board) + "|" + camp


def _dg_own_pieces_key(board, camp):
    """Clé ne codant que la configuration des pièces du camp donné. Sert à
    détecter les répétitions de placement de NOS pièces (anti allers-retours)."""
    parts = []
    for c in range(COLS):
        col = board[c]
        for r in range(ROWS):
            p = col[r]
            if p is not None and p["camp"] == camp:
                parts.append(p["type"][0] + str(c) + str(r))
    return "|".join(parts)


# ── Apprentissage des VALEURS (poids) de deep grey ───────────────────────────
# Chaque catégorie de la table a un multiplicateur (défaut 1.0). L'IA l'affine
# elle-même après chaque partie, dans des limites strictes :
#   • borné à [0.60, 1.40] (jamais plus de ±40% de la valeur de base)
#   • bouge d'au plus 0.03 (±3%) par partie (changements progressifs)
# Stocké dans dg_weights.json. Un défaut absent vaut 1.0.
_DGW_CATS = ("heir_adv", "heir_edge", "heir_immo", "heir_contact",
             "nurse_adv", "nurse_edge", "nurse_mat", "nurse_immo",
             "nurse_groups", "square_mat", "square_immo", "square_push")
_DGW_MIN, _DGW_MAX = 0.60, 1.40
_DGW_STEP = 0.03
_DG_WEIGHTS = None
_DG_WEIGHTS_LOADED = False


def _dg_weights_path():
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "dg_weights.json")


def _dg_weights():
    """Renvoie le dict des multiplicateurs (chargé une fois). Toute catégorie
    absente vaut 1.0."""
    global _DG_WEIGHTS, _DG_WEIGHTS_LOADED
    if not _DG_WEIGHTS_LOADED:
        _DG_WEIGHTS = {}
        try:
            path = _dg_weights_path()
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    _DG_WEIGHTS = data
        except Exception:
            _DG_WEIGHTS = {}
        _DG_WEIGHTS_LOADED = True
    # Compléter les catégories manquantes à 1.0 (sans réécrire le fichier)
    return {cat: float(_DG_WEIGHTS.get(cat, 1.0)) for cat in _DGW_CATS}


def dg_learn_weights(winner_color, loser_color, final_board):
    """Auto-ajustement des poids après une partie (option 1, garde-fous stricts).
    Idée prudente : on regarde, sur la position FINALE, quelles catégories ont
    aidé le GAGNANT (score positif de son point de vue) et on augmente très
    légèrement leur poids ; celles qui ont desservi le gagnant baissent un peu.
    Chaque poids bouge d'au plus _DGW_STEP (3%) et reste dans [0.60, 1.40]."""
    global _DG_WEIGHTS, _DG_WEIGHTS_LOADED
    if winner_color not in ("Blanc", "Noir"):
        return
    # S'assurer que le cache est chargé
    cur = _dg_weights()
    # Contribution de chaque catégorie au score, du point de vue du gagnant.
    contribs = _dg_category_contributions(final_board, winner_color)
    total = sum(abs(v) for v in contribs.values()) or 1.0
    changed = False
    new_weights = dict(_DG_WEIGHTS) if isinstance(_DG_WEIGHTS, dict) else {}
    for cat in _DGW_CATS:
        contrib = contribs.get(cat, 0.0)
        # direction : si la catégorie a aidé le gagnant (contrib>0), on la
        # renforce ; sinon on la réduit. Amplitude proportionnelle au poids
        # relatif de la catégorie, plafonnée à _DGW_STEP.
        delta = _DGW_STEP * (contrib / total)
        if delta > _DGW_STEP: delta = _DGW_STEP
        if delta < -_DGW_STEP: delta = -_DGW_STEP
        old = cur[cat]
        new = old + delta
        if new < _DGW_MIN: new = _DGW_MIN
        if new > _DGW_MAX: new = _DGW_MAX
        if abs(new - old) > 1e-6:
            new_weights[cat] = round(new, 4)
            changed = True
        else:
            new_weights[cat] = round(old, 4)
    if changed:
        _DG_WEIGHTS = new_weights
        _DG_WEIGHTS_LOADED = True
        try:
            path = _dg_weights_path()
            tmp = path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(new_weights, f, ensure_ascii=False)
            os.replace(tmp, path)
        except Exception:
            pass


def _dg_category_contributions(board, camp):
    """Renvoie, par catégorie, la contribution NETTE au score positionnel du
    point de vue de `camp` sur cette position. Sert à l'apprentissage : une
    catégorie avec une grosse contribution positive a 'aidé' camp."""
    opp = "Noir" if camp == "Blanc" else "Blanc"
    rally = _dg_rally_row(camp)
    contribs = {cat: 0.0 for cat in _DGW_CATS}
    occ = {}
    my_nurses = []; opp_nurses = []
    my_heir = None; opp_heir = None
    my_squares = []; opp_squares = []
    best_close = {camp: None, opp: None}
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if p is None: continue
            occ[(c, r)] = p
            cp = p["camp"]; typ = p["type"]
            if typ == "Chevalier": continue
            closeness = 8 - abs(r - rally)
            if p["type"] in ("Nurse", "Héritier"):
                bc = best_close[cp]
                if bc is None or closeness > bc: best_close[cp] = closeness
            if typ == "Héritier":
                if cp == camp: my_heir = (c, r)
                else: opp_heir = (c, r)
            elif typ == "Nurse":
                (my_nurses if cp == camp else opp_nurses).append((c, r))
            elif typ in ("Soldat", "Garde"):
                (my_squares if cp == camp else opp_squares).append((c, r))

    def immobile(c, r, p):
        typ = p["type"]
        if typ == "Soldat": dirs = ((-1,-1),(1,-1),(-1,1),(1,1))
        elif typ == "Garde": dirs = ((0,-1),(0,1),(-1,0),(1,0))
        else: dirs = ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1))
        for dc, dr in dirs:
            nc, nr = c+dc, r+dr
            if 0 <= nc < COLS and 0 <= nr < ROWS and (nc, nr) not in occ:
                return False
        return True

    for heir, cp in ((my_heir, camp), (opp_heir, opp)):
        if heir is None: continue
        c, r = heir; p = occ[(c, r)]; sign = 1.0 if cp == camp else -1.0
        contribs["heir_adv"] += (8 - abs(r - rally)) * 15
        if c == 0 or c == COLS-1: contribs["heir_edge"] += -sign * 30
        if immobile(c, r, p): contribs["heir_immo"] += -sign * 40
    for lst, cp in ((my_nurses, camp), (opp_nurses, opp)):
        sign = 1.0 if cp == camp else -1.0
        for (c, r) in lst:
            p = occ[(c, r)]
            contribs["nurse_adv"] += (8 - abs(r - rally)) * 10
            if c == 0 or c == COLS-1: contribs["nurse_edge"] += -sign * 20
            contribs["nurse_mat"] += sign * 40
            if immobile(c, r, p): contribs["nurse_immo"] += -sign * 30
    for lst, cp in ((my_squares, camp), (opp_squares, opp)):
        sign = 1.0 if cp == camp else -1.0
        cp_fwd = 1 if cp == "Blanc" else -1
        for (c, r) in lst:
            p = occ[(c, r)]
            contribs["square_mat"] += sign * 50
            if immobile(c, r, p): contribs["square_immo"] += -sign * 20
            pushdirs = ((-1, cp_fwd),(1, cp_fwd)) if p["type"]=="Soldat" else ((0, cp_fwd),)
            can_push = False
            for dc, dr in pushdirs:
                tc, tr = c+dc, r+dr
                if not (0<=tc<COLS and 0<=tr<ROWS): continue
                if (tc, tr) not in occ: continue
                bc2, br2 = tc+dc, tr+dr
                if not (0<=bc2<COLS and 0<=br2<ROWS): can_push=True; break
                if (bc2, br2) not in occ: can_push=True; break
            if can_push: contribs["square_push"] += sign * 10
    return contribs


def dg_positional_strategy(board, camp):
    """Valeurs de position de deep grey, calibrees sur la table du concepteur
    (unite x10). Tout est SYMETRIQUE. Optimisee : UN SEUL balayage du plateau,
    puis calculs sur les listes collectees (immobilite, groupes de nurses,
    contact heritier, carree devant les rondes).

    Les poids de base (ci-dessous, _DGW_BASE) peuvent etre modules par des
    multiplicateurs appris (dg_weights.json), bornes a +-40% de la base, et
    bougeant d'au plus 3% par partie. W(cat) renvoie le poids effectif.
    """
    W = _dg_weights()       # multiplicateurs appris (cat -> float), defaut 1.0
    opp = "Noir" if camp == "Blanc" else "Blanc"
    rally = _dg_rally_row(camp)
    fwd = 1 if camp == "Blanc" else -1
    score = 0.0

    # Collecte en un seul passage
    occ = {}                       # (c,r) -> piece (cases occupees)
    my_nurses = []; opp_nurses = []
    my_heir = None; opp_heir = None
    my_squares = []; opp_squares = []
    for c in range(COLS):
        col = board[c]
        for r in range(ROWS):
            p = col[r]
            if p is None: continue
            occ[(c, r)] = p
            cp = p["camp"]; typ = p["type"]
            if typ == "Chevalier":
                continue
            if typ == "Héritier":
                if cp == camp: my_heir = (c, r)
                else: opp_heir = (c, r)
            elif typ == "Nurse":
                (my_nurses if cp == camp else opp_nurses).append((c, r))
            elif typ in ("Soldat", "Garde"):
                (my_squares if cp == camp else opp_squares).append((c, r))

    def immobile(c, r, typ):
        if typ == "Soldat":
            dirs = ((-1,-1),(1,-1),(-1,1),(1,1))
        elif typ == "Garde":
            dirs = ((0,-1),(0,1),(-1,0),(1,0))
        else:
            dirs = ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1))
        for dc, dr in dirs:
            nc = c + dc; nr = r + dr
            if 0 <= nc < COLS and 0 <= nr < ROWS and board[nc][nr] is None:
                return False
        return True

    # Heritier (les deux camps), avancement vers TON camp compté pareil quel
    # que soit le camp de la pièce (objectif : tout amener vers le camp adverse).
    for heir, cp in ((my_heir, camp), (opp_heir, opp)):
        if heir is None: continue
        c, r = heir; p = occ[(c, r)]
        sign = 1.0 if cp == camp else -1.0
        closeness = 8 - abs(r - rally)
        # Avancement : TOUJOURS positif (toute pièce proche de la cible = bon).
        score += closeness * 15 * W["heir_adv"]
        # Bord, immobilité : restent symétriques (mauvais pour le camp de la pièce).
        if c == 0 or c == COLS-1:
            score -= sign * 30 * W["heir_edge"]
        if immobile(c, r, "Héritier"):
            score -= sign * 40 * W["heir_immo"]

    # Nurses (les deux camps)
    for lst, cp in ((my_nurses, camp), (opp_nurses, opp)):
        sign = 1.0 if cp == camp else -1.0
        for (c, r) in lst:
            p = occ[(c, r)]
            closeness = 8 - abs(r - rally)
            # Avancement : TOUJOURS positif (toute nurse proche de la cible = bon).
            score += closeness * 10 * W["nurse_adv"]
            if c == 0 or c == COLS-1:
                score -= sign * 20 * W["nurse_edge"]
            score += sign * 40 * W["nurse_mat"]
            if immobile(c, r, "Nurse"):
                score -= sign * 30 * W["nurse_immo"]

    # Carrees (les deux camps)
    for lst, cp in ((my_squares, camp), (opp_squares, opp)):
        sign = 1.0 if cp == camp else -1.0
        cp_fwd = 1 if cp == "Blanc" else -1
        for (c, r) in lst:
            p = occ[(c, r)]
            score += sign * 50 * W["square_mat"]
            if immobile(c, r, p["type"]):
                score -= sign * 20 * W["square_immo"]
            # en position de pousser vers l'avant ?
            if p["type"] == "Soldat":
                pushdirs = ((-1, cp_fwd), (1, cp_fwd))
            else:
                pushdirs = ((0, cp_fwd),)
            can_push = False
            for dc, dr in pushdirs:
                tc, tr = c+dc, r+dr
                if not (0 <= tc < COLS and 0 <= tr < ROWS): continue
                if (tc, tr) not in occ: continue
                bc2, br2 = tc+dc, tr+dr
                if not (0 <= bc2 < COLS and 0 <= br2 < ROWS):
                    can_push = True; break
                if (bc2, br2) not in occ:
                    can_push = True; break
            if can_push:
                score += sign * 10 * W["square_push"]

    # Groupes de nurses (adjacence 8 dir), sur les listes collectees
    def n_groups(nurse_cells):
        cells = set(nurse_cells)
        seen = set(); groups = 0
        for cell in cells:
            if cell in seen: continue
            groups += 1; stack = [cell]; seen.add(cell)
            while stack:
                x, y = stack.pop()
                for dx in (-1,0,1):
                    for dy in (-1,0,1):
                        if dx == dy == 0: continue
                        nb = (x+dx, y+dy)
                        if nb in cells and nb not in seen:
                            seen.add(nb); stack.append(nb)
        return groups
    mg = n_groups(my_nurses); og = n_groups(opp_nurses)
    if mg > 1: score -= (mg-1) * 10 * W["nurse_groups"]
    if og > 1: score += (og-1) * 10 * W["nurse_groups"]

    # Heritier en contact avec une nurse de son camp ?
    def heir_touches(heir, nurse_cells):
        if heir is None: return True
        hc, hr = heir; ncells = set(nurse_cells)
        for dx in (-1,0,1):
            for dy in (-1,0,1):
                if dx == dy == 0: continue
                if (hc+dx, hr+dy) in ncells:
                    return True
        return False
    if not heir_touches(my_heir, my_nurses):
        score -= 30 * W["heir_contact"]
    if not heir_touches(opp_heir, opp_nurses):
        score += 30 * W["heir_contact"]

    return score


def _dg_nurse_groups(board, camp):
    """Nombre de groupes connectés de NURSES du camp (adjacence 8 directions)."""
    visited = set()
    groups = 0
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if not p or p["camp"] != camp or p["type"] != "Nurse":
                continue
            if (c, r) in visited:
                continue
            groups += 1
            stack = [(c, r)]
            visited.add((c, r))
            while stack:
                x, y = stack.pop()
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        if dx == dy == 0: continue
                        nx, ny = x + dx, y + dy
                        if (nx, ny) in visited or not _dg_on_board(nx, ny):
                            continue
                        q = board[nx][ny]
                        if q and q["camp"] == camp and q["type"] == "Nurse":
                            visited.add((nx, ny))
                            stack.append((nx, ny))
    return groups


def _dg_heir_touches_nurse(board, camp):
    """True si l'Héritier du camp est adjacent (8 dir) à au moins une de ses
    nurses. (Si l'Héritier n'est pas sur le plateau, on considère True pour ne
    pas pénaliser à tort.)"""
    heir = None
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if p and p["camp"] == camp and p["type"] == "Héritier":
                heir = (c, r); break
        if heir: break
    if heir is None:
        return True
    hc, hr = heir
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == dy == 0: continue
            nx, ny = hc + dx, hr + dy
            if not _dg_on_board(nx, ny): continue
            q = board[nx][ny]
            if q and q["camp"] == camp and q["type"] == "Nurse":
                return True
    return False


def _dg_square_ahead_of_rounds(board, c, r, camp):
    """True si la carrée en (c,r) est DEVANT ou AU MÊME NIVEAU que la ronde la
    plus avancée de son camp (donc mal placée pour pousser vers l'avant).
    'Avancé' = plus proche de la zone-cible du camp."""
    rally = _dg_rally_row(camp)
    # Rangée de la ronde la plus avancée du camp (proximité max de la cible)
    best_round_close = None
    for cc in range(COLS):
        for rr in range(ROWS):
            p = board[cc][rr]
            if p and p["camp"] == camp and _dg_is_round(p):
                close = 8 - abs(rr - rally)
                if best_round_close is None or close > best_round_close:
                    best_round_close = close
    if best_round_close is None:
        return False
    sq_close = 8 - abs(r - rally)
    return sq_close >= best_round_close


def _dg_is_immobile(board, c, r):
    """True si la pièce en (c,r) ne peut bouger sur aucune case adjacente
    accessible (toutes ses destinations naturelles sont occupées ou hors
    plateau). Vérif légère (ne simule pas les poussées)."""
    p = board[c][r]
    if not p:
        return False
    typ = p["type"]
    if typ == "Soldat":
        dirs = ((-1, -1), (1, -1), (-1, 1), (1, 1))
    elif typ == "Garde":
        dirs = ((0, -1), (0, 1), (-1, 0), (1, 0))
    else:
        # rondes (Nurse, Héritier) : bougent dans les 8 directions
        dirs = ((-1,-1),(0,-1),(1,-1),(-1,0),(1,0),(-1,1),(0,1),(1,1))
    for dc, dr in dirs:
        nc, nr = c + dc, r + dr
        if _dg_on_board(nc, nr) and board[nc][nr] is None:
            return False   # au moins une case libre = mobile
    return True


def _dg_square_can_push_forward(board, c, r, camp):
    """True si la carrée en (c,r) est en position de pousser une pièce vers la
    zone-cible de son camp (poussée utile, vers l'avant). Vérif légère."""
    p = board[c][r]
    if not p:
        return False
    fwd = 1 if camp == "Blanc" else -1
    if p["type"] == "Soldat":
        dirs = ((-1, fwd), (1, fwd))     # diagonales avant
    elif p["type"] == "Garde":
        dirs = ((0, fwd),)               # orthogonale avant
    else:
        return False
    for dc, dr in dirs:
        tc, tr = c + dc, r + dr
        if not _dg_on_board(tc, tr):
            continue
        target = board[tc][tr]
        if target is None:
            continue
        # Pièce à pousser devant : place derrière (ou bord = éjection) ?
        bc, br = tc + dc, tr + dr
        if not _dg_on_board(bc, br):
            return True
        if board[bc][br] is None:
            return True
    return False


_DG_EVAL_CACHE = {}   # cache d'évaluation par (clé_board, camp) -> score
_DG_EVAL_CACHE_MAX = 50000   # plafond pour éviter une croissance infinie

def dg_evaluate(board, camp):
    """Évalue une position du point de vue de `camp` (deep grey).
    Score élevé = bon pour deep grey.

    Deux niveaux :
    1) SÉCURITÉ (fin de partie), domine tout :
         pouvoir fuguer +10000 / pouvoir mater +5000
         laisser fuguer -10000 / laisser mater -5000
    2) VALEURS DE POSITION (table calibrée par le concepteur), calculée dans
       dg_positional_strategy : avancement des rondes, bords, immobilisations,
       matériel, carrées en position de pousser. Tout est symétrique.
    Mise en cache : une même position n'est évaluée qu'une fois."""
    cache_key = (_dg_board_key(board), camp)
    cached = _DG_EVAL_CACHE.get(cache_key)
    if cached is not None:
        return cached

    opp = "Noir" if camp == "Blanc" else "Blanc"
    score = 0.0

    # ── 1. SÉCURITÉ : menaces adverses (fin de partie, domine tout) ──
    opp_can_fugue = False
    mat_threat = False
    for mv in dg_generate_moves(board, opp):
        if mv["fugue"] or mv.get("fugue_by") == opp:
            opp_can_fugue = True
        if mv["mat_on"] == camp:
            mat_threat = True
        if opp_can_fugue:
            break   # rien de pire, inutile de continuer
    if opp_can_fugue:
        score -= 10000          # se faire fuguer = le pire
    elif mat_threat:
        score -= 5000           # se faire mater = juste au-dessus

    # ── 1bis. SÉCURITÉ : nos opportunités gagnantes au coup suivant ──
    # (détection coûteuse, faite seulement si la position semble propice)
    rally_camp = 8 if camp == "Blanc" else -1
    propice = False
    for c in range(COLS):
        for r in range(ROWS):
            p = board[c][r]
            if p is None or p["type"] != "Héritier": continue
            if p["camp"] == camp and abs(r - rally_camp) <= 2:
                propice = True
            if p["camp"] == opp and (c == 0 or c == COLS-1 or r == 0 or r == ROWS-1):
                propice = True
    if propice:
        own_can_fugue = False
        own_can_mat = False
        for mv in dg_generate_moves(board, camp):
            if mv["fugue"] or mv.get("fugue_by") == camp:
                own_can_fugue = True
                break
            if mv["mat_on"] == opp:
                own_can_mat = True
        if own_can_fugue:
            score += 10000
        elif own_can_mat:
            score += 5000

    # ── 2. VALEURS DE POSITION (table calibrée) ──
    score += dg_positional_strategy(board, camp)

    if len(_DG_EVAL_CACHE) < _DG_EVAL_CACHE_MAX:
        _DG_EVAL_CACHE[cache_key] = score
    return score


def dg_move_bonus(mv, board_before, camp):
    """Bonus immédiat lié au COUP joué. Volontairement minimal : la stratégie
    est portée par l'évaluation de POSITION (dg_evaluate). On gère ici les
    ACTIONS décisives (fin de partie) selon la hiérarchie voulue :
        fuguer (+200000) > mater (+100000) > ... > se faire mater (-100000)
        > se faire fuguer (-200000)
    La fugue est une action ; le mat aussi peut résulter directement d'un coup
    (y compris un AUTO-mat : pousser son propre Héritier hors plateau, ce qui
    est un coup légal). On veille à ce que, contrainte à perdre, deep grey
    préfère se faire mater plutôt que se faire fuguer."""
    opp = "Noir" if camp == "Blanc" else "Blanc"

    # Fugue réalisée par deep grey = victoire : au-dessus de TOUT.
    if mv.get("fugue") or mv.get("fugue_by") == camp:
        return 200000.0
    # Fugue offerte à l'adversaire par ce coup = défaite : sous TOUT.
    if mv.get("fugue_by") == opp:
        return -200000.0
    # Mat : ce coup éjecte un Héritier hors plateau (hors ralliement).
    mat_on = mv.get("mat_on")
    if mat_on == opp:
        return 100000.0    # on mate l'adversaire : excellent
    if mat_on == camp:
        return -100000.0   # on se mate soi-même : mauvais, mais > se faire fuguer
    return 0.0


# ── Apprentissage des ouvertures de deep grey ────────────────────────────────
# Principe : on mémorise, pour une position donnée (clé board + camp au trait),
# les coups qui ont mené à une VICTOIRE, avec un compteur. L'IA, tant qu'elle
# "connaît" la position courante, joue le coup le plus souvent gagnant (sous
# réserve d'un garde-fou de sécurité géré dans _ai_play_inner). Ce livre
# s'enrichit à chaque partie perdue par l'IA (et via le self-play hors-ligne).

import json as _json

_DG_OPENINGS = None        # dict chargé en mémoire : { "cle": { "coup": count } }
_DG_OPENINGS_LOADED = False

def _dg_openings_path():
    """Chemin du fichier d'ouvertures (à côté de main.py)."""
    base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, "dg_openings.json")

def dg_load_openings():
    """Charge le livre d'ouvertures en mémoire (une seule fois)."""
    global _DG_OPENINGS, _DG_OPENINGS_LOADED
    if _DG_OPENINGS_LOADED:
        return _DG_OPENINGS
    _DG_OPENINGS = {}
    try:
        p = _dg_openings_path()
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                _DG_OPENINGS = _json.load(f)
    except Exception:
        _DG_OPENINGS = {}
    _DG_OPENINGS_LOADED = True
    return _DG_OPENINGS

def dg_save_openings():
    """Écrit le livre d'ouvertures sur disque."""
    if _DG_OPENINGS is None:
        return
    try:
        with open(_dg_openings_path(), "w", encoding="utf-8") as f:
            _json.dump(_DG_OPENINGS, f, ensure_ascii=False)
    except Exception:
        pass

def _dg_opening_key(board, camp):
    """Clé d'une position pour le livre : board + camp au trait."""
    return _dg_board_key(board) + "|" + camp

def dg_record_winning_line(history, winner_color, initial_board=None,
                           first_player_color="Blanc"):
    """Enregistre dans le livre les coups joués par le GAGNANT.
    history = liste de (notation, snapshot APRÈS coup). Le board AVANT le coup i
    est le board du snapshot i-1 (ou initial_board pour le 1er coup). Le camp qui
    joue alterne en partant de first_player_color. On ne retient que les coups
    du gagnant. Sauvegarde immédiate (anti-perte de données)."""
    if not history or winner_color not in ("Blanc", "Noir"):
        return
    book = dg_load_openings()
    changed = False
    prev_board = initial_board
    cur_color = first_player_color
    for idx, (notation, snap) in enumerate(history):
        board_before = prev_board
        # Si c'est le gagnant qui a joué ce coup, on l'enregistre
        if board_before is not None and cur_color == winner_color:
            coup = (notation or "").strip().rstrip("#*")
            if coup:
                key = _dg_opening_key(board_before, winner_color)
                entry = book.setdefault(key, {})
                entry[coup] = entry.get(coup, 0) + 1
                changed = True
        # Préparer l'itération suivante : board après ce coup, camp suivant
        prev_board = snap.get("board") if snap else None
        cur_color = "Noir" if cur_color == "Blanc" else "Blanc"
    if changed:
        dg_save_openings()

def dg_lookup_opening(board, camp, min_count=1):
    """Renvoie le coup (notation) le plus souvent gagnant pour cette position,
    ou None si la position est inconnue. min_count = nombre minimal de victoires
    pour faire confiance à un coup (fiabilité)."""
    book = dg_load_openings()
    key = _dg_opening_key(board, camp)
    entry = book.get(key)
    if not entry:
        return None
    # coup le plus fréquemment gagnant
    best_coup, best_n = None, 0
    for coup, n in entry.items():
        if n > best_n:
            best_coup, best_n = coup, n
    if best_coup is not None and best_n >= min_count:
        return best_coup
    return None


def dg_choose_move_deep(board, camp, seen_positions=None, top_k=5):
    """Version profonde de dg_choose_move : top_k candidats à profondeur 2,
    puis ré-évalués à profondeur 3 pour plus de finesse."""
    opp = "Noir" if camp == "Blanc" else "Blanc"
    my_moves = dg_generate_moves(board, camp)
    if not my_moves:
        return None

    # Déduplication
    seen_boards = {}
    deduped = []
    for mv in my_moves:
        key = _dg_board_key(mv["board"])
        if key not in seen_boards:
            seen_boards[key] = True
            deduped.append(mv)
    my_moves = deduped

    # Filtrer les coups interdits
    valid_moves = []
    for mv in my_moves:
        if mv.get("fugue_by") == opp:
            continue
        if mv.get("ej_ally", 0) > 0:
            wins_now = mv["fugue"] or mv.get("fugue_by") == camp or mv["mat_on"] == opp
            if not wins_now:
                continue
        # Coup gagnant immédiat
        if mv["fugue"] or mv.get("fugue_by") == camp or mv["mat_on"] == opp:
            return mv
        valid_moves.append(mv)

    if not valid_moves:
        # Fallback : prendre le moins pire
        return dg_choose_move(board, camp, depth=2, seen_positions=seen_positions)

    # Évaluer chaque coup à profondeur 2 (rapide), garder le top_k
    scored = []
    for mv in valid_moves:
        nb = mv["board"]
        move_bonus = dg_move_bonus(mv, board, camp)
        # Pénalité répétition : config de NOS pièces, à partir de la 3e fois, croissante
        rep_pen = 0.0
        if seen_positions:
            key_own = _dg_own_pieces_key(nb, camp)
            cnt = seen_positions.get(key_own, 0)
            if cnt + 1 >= 3:
                n_extra = (cnt + 1) - 2
                rep_pen = -150 * (n_extra ** 2)
        # Score à profondeur 1 (juste l'évaluation directe)
        sc = dg_evaluate(nb, camp) + move_bonus + rep_pen
        scored.append((sc, mv))
    scored.sort(key=lambda x: -x[0])
    top_candidates = [mv for _, mv in scored[:top_k]]

    # Coups CRITIQUES à approfondir EN PLUS du top_k :
    # tout coup qui implique l'Héritier proche des 2 dernières lignes de défense
    # adverses (= proche de notre ralliement). On veut absolument évaluer ces
    # coups à fond, qu'ils soient à nous (chance de gagner) ou simulés à l'adversaire.
    # Notre ralliement (notre objectif) est :
    #   Blanc → ligne 8 (donc lignes 6-7 = 2 dernières lignes adverses)
    #   Noir  → ligne -1 (donc lignes 0-1 = 2 dernières lignes adverses)
    if camp == "Blanc":
        critical_rows = {5, 6, 7}   # row 7 (départ adverse) + 2 lignes devant
    else:
        critical_rows = {0, 1, 2}
    in_top = set(id(mv) for mv in top_candidates)
    critical_extra = []
    for mv in valid_moves:
        if id(mv) in in_top: continue
        # Coup qui amène notre Héritier sur une ligne critique
        from_c, from_r = mv["from"]
        piece_moved = board[from_c][from_r]
        if piece_moved and piece_moved["type"] == "Héritier" \
                       and piece_moved["camp"] == camp:
            # destination dans les rangées critiques ?
            dest = mv["moved_cells"][0] if mv["moved_cells"] else None
            if dest and dest[1] in critical_rows:
                critical_extra.append(mv)
                continue
        # Coup qui repousse l'Héritier adverse loin de SES lignes critiques
        # (= empêche l'adversaire de gagner)
        if mv["kind"] == "square" and mv.get("total_pushed", 0) > 0:
            # Vérifier si le coup déplace l'Héritier adverse vers son recul
            nb_after = mv["board"]
            for c in range(COLS):
                for r in range(ROWS):
                    p_before = board[c][r]
                    p_after = nb_after[c][r]
                    if p_before is None: continue
                    if p_before["type"] != "Héritier": continue
                    if p_before["camp"] != opp: continue
                    # L'Héritier adverse était-il dans NOS lignes critiques (=ses lignes d'avancée) ?
                    opp_critical_rows = {0,1,2} if camp == "Blanc" else {5,6,7}
                    if r in opp_critical_rows:
                        # Si il a changé de place (p_after est None ici, il est ailleurs)
                        if p_after != p_before:
                            critical_extra.append(mv)
                            break
                if mv in critical_extra: break
    # Combiner top + critiques (sans dépasser top_k + 4)
    extended_top = top_candidates + critical_extra[:4]

    # Ré-évaluation profonde : pour chaque candidate, évaluer à profondeur 3
    best_move = None
    best_score = None
    for mv in extended_top:
        nb = mv["board"]
        move_bonus = dg_move_bonus(mv, board, camp)
        rep_pen = 0.0
        if seen_positions:
            key_after = _dg_position_key(nb, opp)
            cnt = seen_positions.get(key_after, 0)
            if cnt >= 1: rep_pen = -120 * (cnt ** 2)
        # Pire réponse adverse à profondeur 2 (donc 3 niveaux au total)
        opp_moves = dg_generate_moves(nb, opp)
        if not opp_moves:
            sc = dg_evaluate(nb, camp) + move_bonus + rep_pen
        else:
            # Déduper et trier
            opp_deduped = {}
            for omv in opp_moves:
                k = _dg_board_key(omv["board"])
                if k not in opp_deduped:
                    opp_deduped[k] = omv
            opp_filtered = list(opp_deduped.values())
            opp_filtered.sort(key=lambda o: (
                0 if (o["fugue"] or o.get("fugue_by") == opp) else
                1 if o["mat_on"] == camp else
                2 if o["ejected"] > 0 else 3))
            worst = None
            for omv in opp_filtered:
                if omv["fugue"] or omv.get("fugue_by") == opp:
                    s = -100000
                elif omv["mat_on"] == camp:
                    s = -50000
                else:
                    # Réponse de nous à profondeur 1 (notre meilleur coup simple)
                    next_my_moves = dg_generate_moves(omv["board"], camp)
                    if not next_my_moves:
                        s = dg_evaluate(omv["board"], camp)
                    else:
                        # Meilleur score sur les top 3 candidates
                        next_scores = []
                        for nmv in next_my_moves[:8]:
                            if nmv.get("ej_ally", 0) > 0 and not (
                                nmv["fugue"] or nmv.get("fugue_by") == camp
                                or nmv["mat_on"] == opp):
                                continue
                            if nmv.get("fugue_by") == opp: continue
                            ns = dg_evaluate(nmv["board"], camp) + dg_move_bonus(nmv, omv["board"], camp)
                            next_scores.append(ns)
                        s = max(next_scores) if next_scores else dg_evaluate(omv["board"], camp)
                if worst is None or s < worst:
                    worst = s
            sc = worst + move_bonus + rep_pen
        if best_score is None or sc > best_score:
            best_score = sc
            best_move = mv

    return best_move


def _dg_score_move(mv, board, camp, opp, depth, seen_positions):
    """Score d'un coup `mv` à la profondeur donnée (logique partagée).
    Renvoie un très grand/petit nombre pour les coups décisifs."""
    # Coups décisifs immédiats
    if mv["fugue"] or mv.get("fugue_by") == camp:
        return 200000.0
    if mv["mat_on"] == opp:
        return 100000.0
    if mv.get("fugue_by") == opp:
        return -200000.0
    nb = mv["board"]
    move_bonus = dg_move_bonus(mv, board, camp)
    rep_penalty = 0.0
    if seen_positions:
        key_own = _dg_own_pieces_key(nb, camp)
        count = seen_positions.get(key_own, 0)
        if count + 1 >= 3:
            n_extra = (count + 1) - 2
            rep_penalty = -150 * (n_extra ** 2)
    if depth <= 1:
        return dg_evaluate(nb, camp) + move_bonus + rep_penalty
    # depth >= 2 : pire réponse adverse
    opp_moves = dg_generate_moves(nb, opp)
    if not opp_moves:
        return dg_evaluate(nb, camp) + move_bonus + rep_penalty
    worst = None
    for omv in opp_moves:
        if omv["fugue"] or omv.get("fugue_by") == opp:
            s = -100000
        elif omv["mat_on"] == camp:
            s = -50000
        else:
            nb2 = omv["board"]
            if depth >= 3:
                my2 = dg_generate_moves(nb2, camp)
                if not my2:
                    s = dg_evaluate(nb2, camp)
                else:
                    best2 = None
                    for m2 in my2:
                        if m2.get("fugue_by") == opp:
                            continue
                        if m2.get("ej_ally", 0) > 0 and not (
                            m2["fugue"] or m2.get("fugue_by") == camp
                            or m2["mat_on"] == opp):
                            continue
                        if m2["fugue"] or m2.get("fugue_by") == camp:
                            s2 = 100000
                        elif m2["mat_on"] == opp:
                            s2 = 50000
                        else:
                            s2 = dg_evaluate(m2["board"], camp) + dg_move_bonus(m2, nb2, camp)
                        if best2 is None or s2 > best2:
                            best2 = s2
                    s = best2 if best2 is not None else dg_evaluate(nb2, camp)
            else:
                s = dg_evaluate(nb2, camp)
        if worst is None or s < worst:
            worst = s
    return worst + move_bonus + rep_penalty


def dg_choose_move_topn(board, camp, seen_positions=None, move_number=None,
                        top_n=5):
    """Mode PROFOND optimisé (recherche en deux temps, sûr) :
    1) évalue TOUS les coups à profondeur 2 (rapide),
    2) garde les `top_n` meilleurs (toutes catégories confondues),
    3) ré-évalue CES coups-là à profondeur 3 (cher mais sur peu de coups),
    4) renvoie le meilleur.
    Donne la force d'une profondeur 3 sans en payer le coût sur tous les coups.
    Ne peut pas rater le meilleur coup s'il est dans le top_n de la profondeur 2."""
    opp = "Noir" if camp == "Blanc" else "Blanc"
    my_moves = dg_generate_moves(board, camp)
    if not my_moves:
        return None
    # Déduplication par position résultante
    seen_boards = {}
    deduped = []
    for mv in my_moves:
        key = _dg_board_key(mv["board"])
        if key not in seen_boards:
            seen_boards[key] = True
            deduped.append(mv)
    my_moves = deduped

    # Coup gagnant immédiat : on le joue directement
    for mv in my_moves:
        if mv["fugue"] or mv.get("fugue_by") == camp or mv["mat_on"] == opp:
            return mv

    # Filtrer les coups interdits (donner la fugue, auto-éjection non gagnante)
    candidates = []
    for mv in my_moves:
        if mv.get("fugue_by") == opp:
            continue
        if mv.get("ej_ally", 0) > 0:
            wins_now = mv["fugue"] or mv.get("fugue_by") == camp or mv["mat_on"] == opp
            if not wins_now:
                continue
        candidates.append(mv)
    if not candidates:
        # repli : laisser dg_choose_move gérer (rare)
        return dg_choose_move(board, camp, depth=2,
                              seen_positions=seen_positions,
                              move_number=move_number)

    # PASSE 1 : profondeur 2 sur tous les candidats
    scored = []
    for mv in candidates:
        sc2 = _dg_score_move(mv, board, camp, opp, 2, seen_positions)
        scored.append((sc2, mv))
    scored.sort(key=lambda x: x[0], reverse=True)

    # Phase d'ouverture : varier parmi les 3 meilleurs (à profondeur 2)
    if move_number is not None and move_number <= 5:
        import random
        top3 = [mv for _, mv in scored[:3]]
        return random.choice(top3)

    # PASSE 2 : profondeur 3 sur les top_n meilleurs
    best_move, best_score = None, None
    for sc2, mv in scored[:top_n]:
        sc3 = _dg_score_move(mv, board, camp, opp, 3, seen_positions)
        if best_score is None or sc3 > best_score:
            best_score = sc3
            best_move = mv
    return best_move


def dg_choose_move(board, camp, depth=2, seen_positions=None, move_number=None):
    """Choisit le meilleur coup pour deep grey (camp) en profondeur `depth`.
    Utilise un élagage alpha-beta pour aller plus vite.
    Si move_number est fourni et <= 5 (5 premiers coups), choisit au hasard
    parmi les 3 meilleurs coups, pour varier les ouvertures."""
    opp = "Noir" if camp == "Blanc" else "Blanc"
    my_moves = dg_generate_moves(board, camp)
    if not my_moves:
        return None

    # Déduplication : si deux variantes produisent le même board, garder une seule
    seen_boards = {}
    deduped = []
    for mv in my_moves:
        key = _dg_board_key(mv["board"])
        if key not in seen_boards:
            seen_boards[key] = True
            deduped.append(mv)
    my_moves = deduped

    # Trier les coups : prioriser ceux à fort potentiel (fugues, mats, éjections)
    # pour permettre des élagages tôt.
    def move_priority(mv):
        if mv["fugue"]: return 0
        if mv.get("fugue_by") == camp: return 0
        if mv.get("fugue_by") == opp: return 100  # ne JAMAIS jouer = dernier
        if mv["mat_on"] == opp: return 1
        if mv["ejected"] > 0: return 2
        return 3
    my_moves.sort(key=move_priority)

    best_move = None
    best_score = None
    alpha = float("-inf")
    # Pour varier les ouvertures : pendant les 5 premiers coups, on collecte
    # tous les coups avec leur score (sans élagage) pour en tirer un top 3.
    opening_phase = (move_number is not None and move_number <= 5)
    scored_moves = []

    for mv in my_moves:
        # Coup catastrophique : donner la fugue à l'adversaire
        if mv.get("fugue_by") == opp:
            continue
        # Règle d'or : interdit d'éjecter une de nos propres pièces,
        # sauf si le coup est une fugue ou un mat dans le même coup
        if mv.get("ej_ally", 0) > 0:
            wins_now = mv["fugue"] or mv.get("fugue_by") == camp or mv["mat_on"] == opp
            if not wins_now:
                continue
        # Coup gagnant immédiat = on prend direct
        if mv["fugue"]:
            return mv
        if mv.get("fugue_by") == camp:
            return mv
        if mv["mat_on"] == opp:
            return mv

        nb = mv["board"]
        move_bonus = dg_move_bonus(mv, board, camp)

        # Pénalité de répétition : éviter de ramener NOS propres pièces dans une
        # configuration déjà vue. On ne pénalise qu'à partir de la 3e occurrence,
        # et la pénalité grandit à chaque répétition (pour ne jamais tourner en rond).
        rep_penalty = 0.0
        if seen_positions:
            key_own = _dg_own_pieces_key(nb, camp)
            count = seen_positions.get(key_own, 0)
            # count = nombre de fois où cette config de nos pièces a déjà été vue.
            # Jouer ce coup créerait la (count+1)-ème occurrence.
            if count + 1 >= 3:
                # 3e occurrence -> -150, 4e -> -600, 5e -> -1350, etc.
                n_extra = (count + 1) - 2          # 1 à la 3e, 2 à la 4e...
                rep_penalty = -150 * (n_extra ** 2)

        if depth <= 1:
            sc = dg_evaluate(nb, camp) + move_bonus + rep_penalty
        else:
            # On évalue la pire réponse adverse, avec élagage : si on trouve une
            # réponse plus mauvaise que notre meilleure jusqu'ici, on abandonne ce coup.
            opp_moves = dg_generate_moves(nb, opp)
            if not opp_moves:
                sc = dg_evaluate(nb, camp) + move_bonus + rep_penalty
            else:
                # Tri rapide : les coups dangereux pour nous en premier
                def opp_priority(omv):
                    if omv["fugue"] or omv.get("fugue_by") == opp: return 0
                    if omv["mat_on"] == camp: return 1
                    if omv["ejected"] > 0: return 2
                    return 3
                opp_moves.sort(key=opp_priority)

                worst = None
                for omv in opp_moves:
                    if omv["fugue"] or omv.get("fugue_by") == opp:
                        s = -100000
                    elif omv["mat_on"] == camp:
                        s = -50000
                    else:
                        nb2 = omv["board"]
                        if depth >= 3:
                            # Un niveau de plus : notre MEILLEURE contre-réponse
                            # (mode profond). On regarde nos coups depuis nb2 et
                            # on prend le meilleur score d'évaluation directe.
                            my2 = dg_generate_moves(nb2, camp)
                            if not my2:
                                s = dg_evaluate(nb2, camp)
                            else:
                                best2 = None
                                for m2 in my2:
                                    if m2.get("fugue_by") == opp:
                                        continue
                                    if m2.get("ej_ally", 0) > 0 and not (
                                        m2["fugue"] or m2.get("fugue_by") == camp
                                        or m2["mat_on"] == opp):
                                        continue
                                    if m2["fugue"] or m2.get("fugue_by") == camp:
                                        s2 = 100000
                                    elif m2["mat_on"] == opp:
                                        s2 = 50000
                                    else:
                                        s2 = (dg_evaluate(m2["board"], camp)
                                              + dg_move_bonus(m2, nb2, camp))
                                    if best2 is None or s2 > best2:
                                        best2 = s2
                                s = best2 if best2 is not None else dg_evaluate(nb2, camp)
                        else:
                            s = dg_evaluate(nb2, camp)
                    if worst is None or s < worst:
                        worst = s
                        # Élagage désactivé en phase d'ouverture (pour avoir
                        # des scores complets et un vrai top 3)
                        if not opening_phase and worst + move_bonus + rep_penalty <= alpha:
                            break
                sc = worst + move_bonus + rep_penalty

        if opening_phase:
            scored_moves.append((sc, mv))
        if best_score is None or sc > best_score:
            best_score = sc
            best_move = mv
            alpha = max(alpha, sc)

    # Phase d'ouverture : choisir au hasard parmi les 3 meilleurs coups
    # (pour varier les débuts de partie). On garde les coups gagnants immédiats
    # déjà renvoyés plus haut, donc ici ce sont des coups "normaux".
    if opening_phase and scored_moves:
        scored_moves.sort(key=lambda x: x[0], reverse=True)
        top = scored_moves[:3]
        import random
        return random.choice(top)[1]

    if best_move is None:
        # Aucun coup non-catastrophique : prendre le moins pire
        for mv in my_moves:
            sc = dg_evaluate(mv["board"], camp) - 100000
            if mv.get("ej_ally", 0) > 0:
                sc -= 5000 * mv["ej_ally"]
            if best_score is None or sc > best_score:
                best_score = sc
                best_move = mv

    return best_move


# ── Écran de jeu ─────────────────────────────────────────────────────────────

class GameScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.target   = 5
        self.cadence  = 15
        self.scores   = {"Joueur 1": 0, "Joueur 2": 0}
        self.flipped  = True
        self.flash_round = 0
        self.flash_phase = 1
        self.last_chance = False
        self.first_player_blanc = "Joueur 1"
        self.replay_mode = False     # True quand on visionne une partie sauvegardée
        self.analysis_mode = False   # True en mode analyse
        self._analysis_from_replay = False   # True si l'analyse vient d'un replay
        self.vs_ai = False           # True si on joue contre deep grey
        self.ai_camp = None          # camp joué par deep grey ("Blanc"/"Noir")
        self.ai_player = "deep grey" # nom affiché pour l'IA
        # ── Mode en ligne ──
        self.online_mode = False     # True si partie en ligne
        self.online_game_id = None   # identifiant de partie côté serveur
        self.online_my_color = None  # "Blanc"/"Noir" : couleur du joueur local
        self.online_opponent = None  # pseudo de l'adversaire
        self.online_opp_melo = None  # mélo de l'adversaire
        # ── Mode correspondance ──
        self.corr_mode = False
        self.corr_game_id = None
        self.corr_my_color = None
        self.corr_opponent = None
        self.corr_my_turn = False
        self._corr_pending_method = None

        self.turn         = "Blanc"
        self.board        = None
        self.sel          = None
        self.group_sel    = set()
        self.moved        = False
        self.push_on      = False
        self.jumping      = False
        self.captured     = {"Blanc": [], "Noir": []}
        self.blanc_fugued = False
        # Héritiers ayant fugué, à dessiner en permanence dans leur ralliement :
        # liste de dict {"camp","col","row","type":"Héritier"}
        self.fugued_heirs = []
        # Propositions de nulle par accord mutuel (mode local)
        self._draw_offers = {"Blanc": False, "Noir": False}
        self.time_left    = {"Blanc": 0, "Noir": 0}
        self._timer_evt   = None
        self._paused      = False
        self._cs = self._ox = self._oy = 0

        # Historique de la partie courante
        # Liste d'entrées : (notation_str, snapshot_state)
        # snapshot_state = dict avec board, captured, turn, blanc_fugued
        self.history = []
        self.viewing_idx = None   # None = en train de jouer ; int = en mode lecture (index dans history)
        # Variables temporaires pour construire la notation du coup en cours
        self._move_start = None      # case de départ (col, row) ou None
        self._move_jumping_start = None  # même que move_start mais conservé en cas de multisaut
        self._move_is_push = False
        self._move_is_maneuver = False
        self._move_maneuver_pieces = []  # [(col,row), ...] avec maître en [0]
        self._move_push_targets = []     # cases où le joueur a poussé volontairement
        self._move_pushable_dirs = []    # toutes les directions de poussée disponibles
        self._move_is_fugue = False

        self.played_blanc = {"Joueur 1": 0, "Joueur 2": 0}
        self._build()

    def _build(self):
        # Racine en FloatLayout : on empile les bandes dans un BoxLayout interne
        # (stack), mais le PLATEAU est ajouté par-dessus tout (dessiné en dernier)
        # pour que ses zones de ralliement débordent toujours AU-DESSUS des cadres
        # infos, des deux côtés (haut ET bas).
        root = FloatLayout()
        with root.canvas.before:
            Color(0.10, 0.10, 0.10, 1)
            self._root_bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._root_bg, "size", Window.size))

        stack = BoxLayout(orientation="vertical", size_hint=(1, 1),
                          pos_hint={"x": 0, "y": 0})

        # ── Bandeau coloré du haut : boutons (hauteur proportionnelle) ──
        self.top_bar = BoxLayout(size_hint=(1, 0.07),
                                 padding=(S(12), S(6)), spacing=S(6))
        with self.top_bar.canvas.before:
            self._top_col  = Color(*COL_BLUE_DIM)
            self._top_rect = Rectangle(pos=self.top_bar.pos, size=self.top_bar.size)
        self.top_bar.bind(pos=lambda *a: setattr(self._top_rect, "pos", self.top_bar.pos),
                          size=lambda *a: setattr(self._top_rect, "size", self.top_bar.size))

        # Les boutons ronds : taille basée sur la hauteur du bandeau (carrés).
        # On les dimensionne via un width fixe proportionnel mais leur hauteur
        # suit le bandeau (size_hint_y=1, largeur = hauteur pour rester ronds).
        self.pause_btn = RoundButton(text="| |", font_size=SF("22sp"), bold=True,
                                     bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                     size_hint=(None, 1), width=S(58),
                                     radius=S(20))
        self.pause_btn.bind(on_release=self._pause_release_handler)
        self.pause_btn.bind(height=lambda b, h: setattr(b, "width", h))
        self.flip_btn = RoundButton(text="< >", font_size=SF("18sp"), bold=True,
                                    bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                    size_hint=(None, 1), width=S(58),
                                    radius=S(20))
        self.flip_btn.bind(on_release=self._toggle_flip)
        self.flip_btn.bind(height=lambda b, h: setattr(b, "width", h))
        # Bouton "Analyser" visible uniquement en mode replay
        self.analyse_btn = RoundButton(text="Analyser", font_size=SF("14sp"), bold=True,
                                       bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                                       size_hint=(None, 1), width=S(100),
                                       radius=S(14))
        self.analyse_btn.bind(on_release=lambda *a: self.start_analysis_from_replay())
        self.analyse_btn.opacity = 0
        self.analyse_btn.disabled = True
        # Bouton "Deep Grey" : lancer une partie vs l'IA depuis la position
        # affichée (visible en analyse et en replay).
        self.dg_btn = RoundButton(text="Deep Grey", font_size=SF("14sp"), bold=True,
                                   bg_color=(0.30, 0.30, 0.34, 1), color=(1, 1, 1, 1),
                                   size_hint=(None, 1), width=S(110),
                                   radius=S(14))
        self.dg_btn.bind(on_release=lambda *a: self._open_dg_from_position())
        self.dg_btn.opacity = 0
        self.dg_btn.disabled = True
        # Bouton "Mode IA" (Rapide / Profond) visible uniquement en vs_ai
        self.ai_mode_btn = RoundButton(text="Rapide", font_size=SF("15sp"), bold=True,
                                       bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                       size_hint=(None, 1), width=S(108),
                                       radius=S(14))
        self.ai_mode_btn.bind(on_release=self._toggle_ai_mode)
        self.ai_mode_btn.opacity = 0
        self.ai_mode_btn.disabled = True
        # Bouton "Chat" visible uniquement en partie en ligne
        self.chat_btn = RoundButton(text="Chat", font_size=SF("14sp"), bold=True,
                                    bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                    size_hint=(None, 1), width=S(88),
                                    radius=S(14))
        self.chat_btn.bind(on_release=lambda *a: self._open_chat())
        self.chat_btn.opacity = 0
        self.chat_btn.disabled = True
        self.top_bar.add_widget(self.flip_btn)
        self.top_bar.add_widget(BoxLayout(size_hint=(1, 1)))
        self.top_bar.add_widget(self.chat_btn)
        self.top_bar.add_widget(self.ai_mode_btn)
        self.top_bar.add_widget(self.analyse_btn)
        self.top_bar.add_widget(self.dg_btn)
        self.top_bar.add_widget(self.pause_btn)
        stack.add_widget(self.top_bar)

        # ── Cadre info HAUT (côté noir, miroir) ──
        # Ligne haut : nom (gauche) + horloge (centre-droite) + score (droite)
        # Ligne bas (près du plateau) : captures (gauche) + abandon (droite)
        self.top_info = BoxLayout(orientation="vertical",
                                  size_hint=(1, 0.10),
                                  padding=(S(12), S(4)), spacing=S(2))
        with self.top_info.canvas.before:
            self._top_info_col = Color(*COL_BG_MENU)
            self._top_info_rect = RoundedRectangle(pos=self.top_info.pos,
                                                   size=self.top_info.size,
                                                   radius=[S(14)])
        self.top_info.bind(
            pos=lambda *a: setattr(self._top_info_rect, "pos", self.top_info.pos),
            size=lambda *a: setattr(self._top_info_rect, "size", self.top_info.size))

        # Ligne 1 : nom + horloge + score
        top_row1 = BoxLayout(size_hint=(1, 0.5), spacing=S(6))
        self.top_name = Label(text="Joueur 2", font_size=SF("16sp"), bold=True,
                              color=(0.05, 0.05, 0.05, 1),
                              size_hint=(0.42, 1),
                              halign="left", valign="middle", shorten=True)
        self.top_name.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        self.top_timer = Label(text="00:00", font_size=SF("19sp"), bold=True,
                               color=(0.05, 0.05, 0.05, 1),
                               size_hint=(0.36, 1),
                               halign="right", valign="middle", shorten=False)
        self.top_timer.bind(size=lambda lbl, sz: setattr(lbl, "text_size", (sz[0], None)))
        self.top_score = Label(text="0 / 5", font_size=SF("16sp"), bold=True,
                               color=(0.05, 0.05, 0.05, 1),
                               size_hint=(0.22, 1),
                               halign="right", valign="middle", shorten=False)
        self.top_score.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        top_row1.add_widget(self.top_name)
        top_row1.add_widget(self.top_timer)
        top_row1.add_widget(self.top_score)
        self.top_info.add_widget(top_row1)

        # Ligne 2 (près du plateau) : captures + abandon
        top_row2 = BoxLayout(size_hint=(1, 0.5), spacing=S(6))
        self.top_caps = CapturesWidget(size_hint=(1, 1))
        self.top_undo = UndoButton(arrow_color=(1, 1, 1, 1),
                                   bg_color=COL_BTN_GREY,
                                   size_hint=(None, 0.85), width=S(38),
                                   pos_hint={"center_y": 0.5},
                                   radius=S(16))
        self.top_undo.bind(height=lambda b, h: setattr(b, "width", h))
        self.top_undo.bind(on_release=lambda *a: self._cancel_current_move("top"))
        self.top_draw = RoundButton(text="½", font_size=SF("16sp"), bold=True,
                                    bg_color=COL_BTN_GREY,
                                    color=(1, 1, 1, 1),
                                    size_hint=(None, 0.85), width=S(38),
                                    pos_hint={"center_y": 0.5},
                                    radius=S(16))
        self.top_draw.bind(height=lambda b, h: setattr(b, "width", h))
        self.top_draw.bind(on_release=lambda *a: self._toggle_draw_offer("top"))
        self.top_abandon = RoundButton(text="X", font_size=SF("15sp"), bold=True,
                                       bg_color=(0.55, 0.1, 0.1, 1),
                                       color=(1, 1, 1, 1),
                                       size_hint=(None, 0.85), width=S(38),
                                       pos_hint={"center_y": 0.5},
                                       radius=S(16))
        self.top_abandon.bind(height=lambda b, h: setattr(b, "width", h))
        self.top_abandon.bind(on_release=lambda *a: open_abandon_popup(self, "top"))
        top_row2.add_widget(self.top_caps)
        top_row2.add_widget(self.top_undo)
        top_row2.add_widget(self.top_draw)
        top_row2.add_widget(self.top_abandon)
        self.top_info.add_widget(top_row2)
        stack.add_widget(self.top_info)

        # ── Emplacement du plateau (placeholder qui réserve la place) ──
        # Le vrai plateau (board_w) est ajouté à root APRÈS, par-dessus tout.
        self._board_slot = Widget(size_hint=(1, 0.66))
        stack.add_widget(self._board_slot)

        # ── Cadre info BAS (côté blanc) : miroir du haut ──
        # Ligne haut (près du plateau) : captures + abandon
        # Ligne bas : nom + horloge + score
        self.bot_info = BoxLayout(orientation="vertical",
                                  size_hint=(1, 0.10),
                                  padding=(S(12), S(4)), spacing=S(2))
        with self.bot_info.canvas.before:
            self._bot_info_col = Color(*COL_BG_MENU)
            self._bot_info_rect = RoundedRectangle(pos=self.bot_info.pos,
                                                   size=self.bot_info.size,
                                                   radius=[S(14)])
        self.bot_info.bind(
            pos=lambda *a: setattr(self._bot_info_rect, "pos", self.bot_info.pos),
            size=lambda *a: setattr(self._bot_info_rect, "size", self.bot_info.size))

        # Ligne 1 (près du plateau) : captures + abandon
        bot_row1 = BoxLayout(size_hint=(1, 0.5), spacing=S(6))
        self.bot_caps = CapturesWidget(size_hint=(1, 1))
        self.bot_undo = UndoButton(arrow_color=(1, 1, 1, 1),
                                   bg_color=COL_BTN_GREY,
                                   size_hint=(None, 0.85), width=S(38),
                                   pos_hint={"center_y": 0.5},
                                   radius=S(16))
        self.bot_undo.bind(height=lambda b, h: setattr(b, "width", h))
        self.bot_undo.bind(on_release=lambda *a: self._cancel_current_move("bot"))
        self.bot_draw = RoundButton(text="½", font_size=SF("16sp"), bold=True,
                                    bg_color=COL_BTN_GREY,
                                    color=(1, 1, 1, 1),
                                    size_hint=(None, 0.85), width=S(38),
                                    pos_hint={"center_y": 0.5},
                                    radius=S(16))
        self.bot_draw.bind(height=lambda b, h: setattr(b, "width", h))
        self.bot_draw.bind(on_release=lambda *a: self._toggle_draw_offer("bot"))
        self.bot_abandon = RoundButton(text="X", font_size=SF("15sp"), bold=True,
                                       bg_color=(0.55, 0.1, 0.1, 1),
                                       color=(1, 1, 1, 1),
                                       size_hint=(None, 0.85), width=S(38),
                                       pos_hint={"center_y": 0.5},
                                       radius=S(16))
        self.bot_abandon.bind(height=lambda b, h: setattr(b, "width", h))
        self.bot_abandon.bind(on_release=lambda *a: open_abandon_popup(self, "bot"))
        bot_row1.add_widget(self.bot_caps)
        bot_row1.add_widget(self.bot_undo)
        bot_row1.add_widget(self.bot_draw)
        bot_row1.add_widget(self.bot_abandon)
        self.bot_info.add_widget(bot_row1)

        # Ligne 2 : nom + horloge + score
        bot_row2 = BoxLayout(size_hint=(1, 0.5), spacing=S(6))
        self.bot_name = Label(text="Joueur 1", font_size=SF("16sp"), bold=True,
                              color=(0.05, 0.05, 0.05, 1),
                              size_hint=(0.42, 1),
                              halign="left", valign="middle", shorten=True)
        self.bot_name.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        self.bot_timer = Label(text="00:00", font_size=SF("19sp"), bold=True,
                               color=(0.05, 0.05, 0.05, 1),
                               size_hint=(0.36, 1),
                               halign="right", valign="middle", shorten=False)
        self.bot_timer.bind(size=lambda lbl, sz: setattr(lbl, "text_size", (sz[0], None)))
        self.bot_score = Label(text="0 / 5", font_size=SF("16sp"), bold=True,
                               color=(0.05, 0.05, 0.05, 1),
                               size_hint=(0.22, 1),
                               halign="right", valign="middle", shorten=False)
        self.bot_score.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        bot_row2.add_widget(self.bot_name)
        bot_row2.add_widget(self.bot_timer)
        bot_row2.add_widget(self.bot_score)
        self.bot_info.add_widget(bot_row2)
        stack.add_widget(self.bot_info)

        # ── Bandeau coloré du bas : navigation (hauteur proportionnelle) ──
        self.bot_bar = BoxLayout(size_hint=(1, 0.07),
                                 padding=(S(12), S(6)), spacing=S(4))
        with self.bot_bar.canvas.before:
            self._bot_col  = Color(*COL_ORANGE_DIM)
            self._bot_rect = Rectangle(pos=self.bot_bar.pos, size=self.bot_bar.size)
        self.bot_bar.bind(pos=lambda *a: setattr(self._bot_rect, "pos", self.bot_bar.pos),
                          size=lambda *a: setattr(self._bot_rect, "size", self.bot_bar.size))

        # ── Bandeau bas : flèche gauche, historique défilant, flèche droite ──
        self.prev_btn = RoundButton(text="<", font_size=SF("22sp"), bold=True,
                                    bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                    size_hint=(None, 1), width=S(44),
                                    radius=S(20))
        self.prev_btn.bind(on_release=lambda *a: self._nav_prev())
        self.prev_btn.bind(height=lambda b, h: setattr(b, "width", h))

        # ScrollView horizontal pour les coups
        self.history_scroll = ScrollView(size_hint=(1, 1),
                                          do_scroll_x=True, do_scroll_y=False,
                                          bar_width=0)
        self.history_box = BoxLayout(orientation="horizontal",
                                      size_hint=(None, 1), spacing=S(4),
                                      padding=(S(8), S(4)))
        self.history_box.bind(minimum_width=self.history_box.setter("width"))
        self.history_scroll.add_widget(self.history_box)

        self.next_btn = RoundButton(text=">", font_size=SF("22sp"), bold=True,
                                    bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                    size_hint=(None, 1), width=S(44),
                                    radius=S(20))
        self.next_btn.bind(on_release=lambda *a: self._nav_next())
        self.next_btn.bind(height=lambda b, h: setattr(b, "width", h))

        self.bot_bar.add_widget(self.prev_btn)
        self.bot_bar.add_widget(self.history_scroll)
        self.bot_bar.add_widget(self.next_btn)
        stack.add_widget(self.bot_bar)

        # On ajoute d'abord la pile (bandes), puis le plateau PAR-DESSUS.
        root.add_widget(stack)

        # ── Plateau (pleine largeur), dessiné PAR-DESSUS les cadres ──
        # Il suit la position/taille du placeholder réservé dans la pile.
        self.board_w = BoardWidget(self, size_hint=(None, None))
        root.add_widget(self.board_w)
        def _sync_board(*a):
            self.board_w.pos = self._board_slot.pos
            self.board_w.size = self._board_slot.size
        self._board_slot.bind(pos=_sync_board, size=_sync_board)
        # Synchronisation initiale (après que la pile ait été dimensionnée)
        Clock.schedule_once(lambda dt: _sync_board(), 0)

        self.add_widget(root)

    def start_match(self, target, cadence):
        self.replay_mode = False
        self.analysis_mode = False
        self.vs_ai = False
        self.online_mode = False
        self.corr_mode = False
        self.online_game_id = None
        self.ai_camp = None
        self.target   = target
        self.cadence  = cadence
        self.scores   = {"Joueur 1": 0, "Joueur 2": 0}
        self.played_blanc = {"Joueur 1": 0, "Joueur 2": 0}
        self.flash_round = 1 if target == "flash" else 0
        self.flash_phase = 1
        self.last_chance = False
        # Random Fuga : si l'interrupteur global est allumé, tirer une position
        # aléatoire pour cette partie (chaque partie d'un match en a une nouvelle).
        self._pending_random_code = rf_random_code() if RANDOM_MODE else None
        self._new_game(first_blanc_player="Joueur 1")
        self._update_action_buttons()

    def start_match_vs_ai(self, target, cadence, player_color="random"):
        """Lance une partie contre deep grey.
        player_color : 'Blanc', 'Noir' ou 'random'."""
        import random
        self.replay_mode = False
        self.analysis_mode = False
        self.vs_ai = True
        self.online_mode = False
        self.corr_mode = False
        self.online_game_id = None
        self.ai_deep_mode = False   # mode rapide par défaut, togglable en jeu
        # Mode partie simple + zen (pas de timer)
        self.target   = "partie"
        self.cadence  = "zen"
        self.scores   = {"Joueur 1": 0, "deep grey": 0}
        self.played_blanc = {"Joueur 1": 0, "deep grey": 0}
        self.flash_round = 0
        self.flash_phase = 1
        self.last_chance = False
        # Déterminer qui joue Blanc selon le choix
        if player_color == "Blanc":
            first_blanc = "Joueur 1"
        elif player_color == "Noir":
            first_blanc = "deep grey"
        else:
            first_blanc = random.choice(["Joueur 1", "deep grey"])
        # deep grey joue le camp opposé au joueur
        self.ai_camp = "Blanc" if first_blanc == "deep grey" else "Noir"
        # Orientation : joueur humain en bas. On la fixe AVANT _new_game pour
        # que le premier rendu utilise déjà la bonne orientation (sinon, rare
        # bug d'affichage où le joueur se retrouve du mauvais côté).
        self.flipped = (self.ai_camp == "Noir")
        # Random Fuga : position aléatoire si l'interrupteur est allumé.
        self._pending_random_code = rf_random_code() if RANDOM_MODE else None
        self._new_game(first_blanc_player=first_blanc)
        self._update_action_buttons()
        # Si c'est à deep grey de commencer, il joue
        self._maybe_ai_turn()

    def _on_melo_maj(self, data):
        """Reçoit le nouveau Mélo après une partie classée et met à jour
        l'affichage + la session sauvegardée."""
        nouveau = (data or {}).get("mon_melo")
        delta = (data or {}).get("delta", 0)
        if nouveau is None:
            return
        ONLINE.melo = nouveau
        try:
            save_online_session(ONLINE.token, ONLINE.pseudo, ONLINE.melo)
        except Exception:
            pass
        self._last_melo_delta = delta
        self._last_melo_value = nouveau
        # Rafraîchir l'affichage du Mélo dans le menu (bouton compte)
        try:
            menu = self.manager.get_screen("menu")
            if hasattr(menu, "_refresh_online_ui"):
                menu._refresh_online_ui()
        except Exception:
            pass

    def _on_match_continue(self, data):
        """Le serveur indique que le match continue : afficher le popup 'Partie
        suivante' (avec compte à rebours). Le résultat de la partie qui vient de
        finir a été mémorisé dans _pending_finish."""
        if not getattr(self, "online_mode", False):
            return
        pf = getattr(self, "_pending_finish", None)
        if pf:
            title, body, _wp = pf
        else:
            title, body = "Partie terminée", ""
        # Mettre à jour le score affiché à partir du payload serveur
        sb = (data or {}).get("score_blanc")
        sn = (data or {}).get("score_noir")
        if sb is not None and sn is not None:
            try:
                bn = self._online_blanc_name; nn = self._online_noir_name
                self.scores[bn] = sb; self.scores[nn] = sn
                body = "%s : %d    %s : %d" % (bn, sb, nn, sn)
            except Exception:
                pass
        self._popup_continue_online(title, body)

    def _on_match_over(self, data):
        """Le serveur indique que le match est terminé : afficher le popup final
        avec le vainqueur du match."""
        if not getattr(self, "online_mode", False):
            return
        pf = getattr(self, "_pending_finish", None)
        title = pf[0] if pf else "Match terminé"
        body = pf[1] if pf else ""
        winner_player = pf[2] if pf else None
        sb = (data or {}).get("score_blanc")
        sn = (data or {}).get("score_noir")
        if sb is not None and sn is not None:
            try:
                bn = self._online_blanc_name; nn = self._online_noir_name
                self.scores[bn] = sb; self.scores[nn] = sn
                if sb > sn: winner_player = bn
                elif sn > sb: winner_player = nn
                else: winner_player = None
                body = "Score final\n%s : %d    %s : %d" % (bn, sb, nn, sn)
            except Exception:
                pass
        self._popup_finish(title, body, winner_player=winner_player)

    def _on_adversaire_pret(self, data):
        """L'adversaire a cliqué 'Partie suivante' : on l'indique dans le popup."""
        if not getattr(self, "online_mode", False):
            return
        if getattr(self, "_next_status_lbl", None) is not None:
            try:
                if not getattr(self, "_next_ready_sent", False):
                    self._next_status_lbl.text = ("L'adversaire est prêt !\n"
                        "Clique sur « Partie suivante ».")
                    self._next_status_lbl.color = (0.45, 0.85, 0.45, 1)
            except Exception:
                pass

    def _on_match_abandonne(self, data):
        """Le match est terminé car un joueur n'a pas rejoint la partie suivante
        à temps (ou a quitté). Pas de coût de Mélo (aucune partie en cours)."""
        if not getattr(self, "online_mode", False):
            return
        self._cancel_next_timer()
        if getattr(self, "_next_popup", None) is not None:
            try: self._next_popup.dismiss()
            except Exception: pass
            self._next_popup = None
        gagnant = (data or {}).get("gagnant")  # pseudo du gagnant du match
        my_name = ONLINE.pseudo or "Moi"
        if gagnant == my_name:
            titre = "Match gagné"
            corps = ("Votre adversaire n'a pas rejoint la partie suivante.\n"
                     "Vous remportez le match.\n\n(Aucun point Mélo : pas de "
                     "partie en cours.)")
        else:
            titre = "Match terminé"
            corps = ("Vous n'avez pas rejoint la partie suivante à temps.\n"
                     "Le match est perdu.\n\n(Aucun point Mélo : pas de partie "
                     "en cours.)")
        # Popup simple d'information puis retour menu
        c = BoxLayout(orientation="vertical", spacing=S(12), padding=S(16))
        lbl = Label(text=corps, color=(1, 1, 1, 1), halign="center",
                    valign="middle", font_size=SF("14sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        c.add_widget(lbl)
        ok = RoundButton(text="OK", bg_color=COL_BLUE, color=(1, 1, 1, 1),
                         font_size=SF("15sp"), bold=True, size_hint=(1, 0.35))
        c.add_widget(ok)
        p = Popup(title=titre, content=c, size_hint=(0.85, 0.45),
                  separator_height=0, auto_dismiss=False)
        ok.bind(on_release=lambda *a: (p.dismiss(), self._leave_online_to_menu()))
        p.open()

    def _on_coup_adverse(self, data):
        """Réception d'un coup de l'adversaire (notation NMC). On le rejoue
        AUTOMATIQUEMENT sur le plateau, sans que le joueur ait à agir. Le
        garde-fou _applying_remote empêche que ce coup soit renvoyé au serveur."""
        if not getattr(self, "online_mode", False):
            return
        notation = (data or {}).get("notation", "")
        if not notation:
            return
        self._applying_remote = True
        try:
            ok = self._apply_notation(notation)
        except Exception:
            ok = False
        finally:
            self._applying_remote = False
        if ok:
            # Sortir d'un éventuel mode "lecture" pour rester sur la position live
            self.viewing_idx = None
            # Mettre à jour l'aperçu du dernier coup (sinon il resterait sur NOTRE
            # dernier coup au lieu de celui que l'adversaire vient de jouer). On
            # récupère l'état AVANT ce coup depuis l'historique (avant-dernier
            # snapshot), comme le fait la navigation dans l'historique.
            try:
                board_before = None
                if len(self.history) >= 2:
                    board_before = self.history[-2][1].get("board")
                push_targets = self._reconstruct_push_targets(notation, board_before)
                self._last_move_highlight = self._build_highlight_from_notation(
                    notation, board_before, explicit_push_targets=push_targets)
            except Exception:
                pass
            self._refresh_ui()
            self._update_history_ui()
            # Jouer le son du coup adverse (comme pour nos propres coups)
            try:
                self._play_move_sound(notation)
            except Exception:
                pass
            # Vérifier fin de partie de MON point de vue (Trêve / Papatte)
            if self._check_knight_stalemate():
                return
            if self._check_papatte():
                return

    def _on_partie_terminee_remote(self, data):
        """L'adversaire a terminé la partie (mat, fugue, abandon, ou il a constaté
        la fin). On affiche le résultat de notre côté SANS renvoyer fin_partie au
        serveur (sinon il compterait les points en double) : on pose donc le
        garde-fou _applying_remote pendant la finalisation."""
        if not getattr(self, "online_mode", False):
            return
        methode = (data or {}).get("methode", "")
        loser_color = (data or {}).get("loser_color")
        self._applying_remote = True
        try:
            if methode == "nulle":
                self._end_game_by_color(loser_color=None, method="nulle_accord")
            elif loser_color in ("Blanc", "Noir"):
                self._end_game_by_color(loser_color=loser_color,
                                        method=methode or "abandon")
        finally:
            self._applying_remote = False

    def _on_adversaire_deconnecte(self, data):
        """L'adversaire s'est déconnecté : on l'indique dans la barre avec un
        COMPTE À REBOURS (non bloquant). S'il ne revient pas avant la fin du
        délai, le serveur déclarera sa défaite par abandon."""
        if not getattr(self, "online_mode", False):
            return
        self._dc_opp_name = self.online_opponent or "Adversaire"
        # Délai fourni par le serveur (secondes), défaut 30 s
        try:
            self._dc_remaining = int((data or {}).get("delai", 30))
        except (ValueError, TypeError):
            self._dc_remaining = 30
        # Annuler un éventuel compte à rebours précédent
        if getattr(self, "_dc_event", None):
            try: self._dc_event.cancel()
            except Exception: pass
            self._dc_event = None
        self._dc_tick(0)   # affiche tout de suite
        # Programmer le décompte chaque seconde
        self._dc_event = Clock.schedule_interval(self._dc_tick, 1)

    def _dc_tick(self, dt):
        """Met à jour l'affichage du compte à rebours de déconnexion."""
        if not getattr(self, "online_mode", False) or not getattr(self, "_dc_opp_name", None):
            if getattr(self, "_dc_event", None):
                try: self._dc_event.cancel()
                except Exception: pass
                self._dc_event = None
            return
        if hasattr(self, "top_name"):
            try:
                if self._dc_remaining > 0:
                    self.top_name.text = "%s (déco %ds)" % (self._dc_opp_name,
                                                            self._dc_remaining)
                else:
                    self.top_name.text = "%s (abandon…)" % self._dc_opp_name
                self.top_name.color = (0.9, 0.4, 0.4, 1)
            except Exception:
                pass
        if dt:  # ne décrémente pas au tout premier appel (dt=0)
            self._dc_remaining -= 1
        if self._dc_remaining < 0:
            if getattr(self, "_dc_event", None):
                try: self._dc_event.cancel()
                except Exception: pass
                self._dc_event = None

    def _on_adversaire_revenu(self, data):
        """L'adversaire est revenu : on arrête le compte à rebours et on rétablit
        l'affichage normal."""
        if not getattr(self, "online_mode", False):
            return
        if getattr(self, "_dc_event", None):
            try: self._dc_event.cancel()
            except Exception: pass
            self._dc_event = None
        self._dc_opp_name = None
        self._refresh_ui()

    def _on_nulle_proposee_remote(self, data):
        """L'adversaire propose la nulle : popup Accepter / Refuser."""
        if not getattr(self, "online_mode", False):
            return
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
        lbl = Label(text="%s propose la nulle." % (self.online_opponent or "L'adversaire"),
                    color=(1, 1, 1, 1), halign="center", valign="middle",
                    font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        row = BoxLayout(orientation="horizontal", spacing=S(10), size_hint=(1, 0.4))
        acc = RoundButton(text="Accepter", bg_color=COL_BLUE, color=(1, 1, 1, 1),
                          font_size=SF("14sp"), bold=True)
        ref = RoundButton(text="Refuser", bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                          font_size=SF("14sp"), bold=True)
        row.add_widget(acc); row.add_widget(ref)
        content.add_widget(row)
        p = Popup(title="", content=content, size_hint=(0.82, 0.4),
                  separator_height=0, auto_dismiss=False)

        def _accept(*a):
            p.dismiss()
            # _end_game_by_color enverra lui-même 'fin_partie' au serveur (une
            # seule fois). Ne pas l'envoyer ici en plus, sinon double comptage.
            self._end_game_by_color(loser_color=None, method="nulle_accord")
        acc.bind(on_release=_accept)
        ref.bind(on_release=lambda *a: p.dismiss())
        p.open()

    def start_match_online(self, game_id, my_color, opponent, opp_melo,
                           objectif, cadence, score_moi=0, score_adv=0,
                           last_chance=False, random_code=None):
        """Démarre une partie EN LIGNE (matchmaking). Chemin totalement séparé du
        local : on réutilise le même moteur de jeu, mais les coups voyagent en
        NMC via le serveur. Le joueur Noir voit le plateau reversé (comme le
        bouton flip en local). random_code : code Random Fuga commun envoyé par le
        serveur (None = partie standard)."""
        self.replay_mode = False
        self.analysis_mode = False
        self.vs_ai = False
        self.corr_mode = False
        self.online_mode = True
        self.ai_camp = None
        # Identité de la partie en ligne
        self.online_game_id = game_id
        self.online_my_color = my_color           # "Blanc" ou "Noir"
        self.online_opponent = opponent
        self.online_opp_melo = opp_melo
        self._applying_remote = False             # garde-fou anti-renvoi
        # Réinitialiser l'état "adversaire déconnecté" (compte à rebours)
        if getattr(self, "_dc_event", None):
            try: self._dc_event.cancel()
            except Exception: pass
        self._dc_event = None
        self._dc_opp_name = None
        self._dc_remaining = 0
        # Score / objectif (réutilise la logique locale d'affichage)
        my_name = ONLINE.pseudo or "Moi"
        if my_color == "Blanc":
            blanc_name, noir_name = my_name, opponent
            first_blanc = blanc_name
        else:
            blanc_name, noir_name = opponent, my_name
            first_blanc = blanc_name
        self._online_blanc_name = blanc_name
        self._online_noir_name = noir_name
        self.target = objectif
        self.cadence = cadence
        # Score du match fourni par le serveur (0-0 pour une nouvelle partie ;
        # score en cours pour une partie suivante d'un match). On le replace dans
        # le repère blanc/noir.
        if my_color == "Blanc":
            sc_blanc, sc_noir = score_moi, score_adv
        else:
            sc_blanc, sc_noir = score_adv, score_moi
        self.scores = {blanc_name: sc_blanc, noir_name: sc_noir}
        self.played_blanc = {blanc_name: 0, noir_name: 0}
        self.flash_round = 1 if objectif == "flash" else 0
        self.flash_phase = 1
        self.last_chance = bool(last_chance)
        # Orientation : MON camp en bas (comme en local). La convention du jeu
        # est flipped=True => Blanc en bas. Donc : si je suis Blanc, flipped=True ;
        # si je suis Noir, flipped=False (le plateau est tourné pour que MES
        # pièces noires soient en bas).
        self.flipped = (my_color == "Blanc")
        # Réinitialiser les variables du flux "partie suivante" (match)
        self._next_popup = None
        self._next_ready_sent = False
        self._pending_finish = None
        self._mat_pending = None
        self._cancel_next_timer()
        # Random Fuga en ligne : le serveur a envoyé un code commun aux DEUX
        # joueurs → on le pose pour que _new_game construise la même position des
        # deux côtés. None = partie standard (comportement en ligne inchangé).
        self._pending_random_code = random_code
        self._new_game(first_blanc_player=first_blanc)
        self._update_action_buttons()

    def start_corr_game(self, gd):
        """Ouvre une partie de CORRESPONDANCE. Chemin TOTALEMENT séparé du reste.
        RESET COMPLET puis reconstruction UNIQUEMENT à partir des coups NMC
        fournis par le serveur (anti 'comptes collés' : aucun état résiduel n'est
        réutilisé). Le chat est rechargé frais depuis le serveur."""
        gd = gd or {}
        # 1) Modes : correspondance pure (surtout PAS online_mode, PAS d'IA)
        self.replay_mode = False
        self.analysis_mode = False
        self.vs_ai = False
        self.online_mode = False
        self.ai_camp = None
        self._applying_remote = False
        self.corr_mode = True
        # 2) Identité de la partie, la source de vérité est le SERVEUR
        self.corr_game_id = gd.get("id")
        self.corr_my_color = gd.get("ma_couleur", "Blanc")
        self.corr_opponent = gd.get("adversaire", "Adversaire")
        self.corr_my_turn = bool(gd.get("my_turn"))
        self._corr_pending_method = None
        # 3) Noms des joueurs (moi toujours en bas)
        my_name = ONLINE.pseudo or "Moi"
        if self.corr_my_color == "Blanc":
            blanc_name, noir_name = my_name, self.corr_opponent
        else:
            blanc_name, noir_name = self.corr_opponent, my_name
        self._corr_blanc_name = blanc_name
        self._corr_noir_name = noir_name
        # 4) Score head-to-head (renvoyé par le serveur) replacé en repère B/N
        mon_score = gd.get("mon_score", 0)
        score_adv = gd.get("score_adverse", 0)
        if self.corr_my_color == "Blanc":
            sc_blanc, sc_noir = mon_score, score_adv
        else:
            sc_blanc, sc_noir = score_adv, mon_score
        # 5) Pas de cadence ni d'objectif : partie unique, sans pendule
        self.target = "partie"
        self.cadence = "zen"
        self.scores = {blanc_name: sc_blanc, noir_name: sc_noir}
        self.played_blanc = {blanc_name: 0, noir_name: 0}
        self.flash_round = 0
        self.flash_phase = 1
        self.last_chance = False
        # 6) Orientation : mon camp en bas (flipped=True => Blanc en bas)
        self.flipped = (self.corr_my_color == "Blanc")
        # 7) Nettoyer les variables des autres modes (par sécurité)
        self._next_popup = None
        self._next_ready_sent = False
        self._pending_finish = None
        self._mat_pending = None
        self._cancel_next_timer()
        # Random Fuga en correspondance : le serveur a stocké un code commun.
        # On le pose pour que _new_game construise la bonne position de départ ;
        # les coups NMC sont ensuite rejoués par-dessus. '' / None = standard.
        self._pending_random_code = gd.get("random_code") or None
        # 8) RESET COMPLET : position de départ, historique et chat vidés
        self._new_game(first_blanc_player=blanc_name)
        # 9) RECONSTRUCTION depuis le NMC du serveur. _apply_notation N'ÉMET RIEN
        #    (il ne renvoie aucun coup) : on rebâtit le plateau ET l'historique.
        moves_text = gd.get("moves_text", "") or ""
        for nota in moves_text.split("\n"):
            nota = nota.strip()
            if nota:
                try:
                    self._apply_notation(nota)
                except Exception:
                    pass
        # 10) Forcer le tour exact indiqué par le serveur (sécurité anti-désync)
        srv_turn = gd.get("turn")
        if srv_turn in ("Blanc", "Noir"):
            self.turn = srv_turn
        self.viewing_idx = None
        # 10b) Mettre en évidence le DERNIER coup joué (cadre sur les cases +
        #      points de poussée), comme en ligne. On reconstruit à partir de
        #      l'historique rejoué et de l'état AVANT le dernier coup.
        self._last_move_highlight = None
        if self.history:
            try:
                last_nota = self.history[-1][0]
                if len(self.history) >= 2:
                    board_before = self.history[-2][1].get("board")
                else:
                    board_before = (self._initial_state or {}).get("board")
                push_targets = self._reconstruct_push_targets(last_nota, board_before)
                self._last_move_highlight = self._build_highlight_from_notation(
                    last_nota, board_before, explicit_push_targets=push_targets)
            except Exception:
                self._last_move_highlight = None
        # 11) Chat : on NE pré-charge PAS les messages ici (sinon ils seraient
        #     marqués "lus" avant même que tu ouvres la boîte de chat). On affiche
        #     seulement le BADGE de messages non lus renvoyé par le serveur. Les
        #     messages eux-mêmes seront chargés frais à l'ouverture du chat
        #     (_open_chat en corr les recharge et les marque lus côté serveur).
        self._chat_messages = []
        self._chat_open = False
        self._chat_unread = int(gd.get("chat_non_lus", 0) or 0)
        if hasattr(self, "chat_btn"):
            self.chat_btn.text = ("Chat (%d)" % self._chat_unread
                                  if self._chat_unread > 0 else "Chat")
        # 12) Rafraîchir l'affichage
        self._refresh_ui()
        self._update_history_ui()
        self._update_action_buttons()
        # 13) Si l'adversaire m'a proposé une nulle, l'afficher MAINTENANT (popup
        #     accepter/refuser). Rien n'est visible depuis l'aperçu : seulement ici.
        if gd.get("nulle_a_repondre"):
            # Léger délai pour laisser l'écran de jeu s'afficher d'abord.
            Clock.schedule_once(
                lambda dt, g=gd: self._corr_nulle_popup(g), 0.35)

    def _corr_nulle_popup(self, gd):
        """Popup proposé au joueur qui REÇOIT une nulle en correspondance, à
        l'ouverture de la partie : accepter (=> partie nulle) ou refuser (=> on
        continue de jouer)."""
        if not getattr(self, "corr_mode", False):
            return
        proposeur = gd.get("nulle_proposeur") or self.corr_opponent or "L'adversaire"
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(16))
        lbl = Label(text="%s propose une partie nulle." % proposeur,
                    font_size=SF("15sp"), color=(1, 1, 1, 1),
                    halign="center", valign="middle", size_hint=(1, 0.5))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        row = BoxLayout(orientation="horizontal", spacing=S(10),
                        size_hint=(1, 0.5))
        acc = RoundButton(text="Accepter", bg_color=(0.20, 0.60, 0.25, 1),
                          color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True)
        ref = RoundButton(text="Refuser", bg_color=COL_BTN_GREY,
                          color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True)
        row.add_widget(acc)
        row.add_widget(ref)
        content.add_widget(row)
        popup = Popup(title="Proposition de nulle", content=content,
                      size_hint=(0.82, 0.4), auto_dismiss=False)

        def _accept(*a):
            popup.dismiss()
            def _done(result, err):
                if err or not (result and result.get("ok")):
                    self._popup_simple("Nulle", err or "Échec.")
                    return
                # La partie est désormais nulle côté serveur.
                self._game_over = True
                self._popup_finish("Partie nulle",
                                   "Vous avez accepté la nulle.", None)
            try:
                ONLINE.corr_repondre_nulle(self.corr_game_id, True, _done)
            except Exception:
                pass

        def _refuse(*a):
            popup.dismiss()
            def _done(result, err):
                pass  # proposition effacée côté serveur ; on continue
            try:
                ONLINE.corr_repondre_nulle(self.corr_game_id, False, _done)
            except Exception:
                pass

        acc.bind(on_release=_accept)
        ref.bind(on_release=_refuse)
        popup.open()
    def _open_dg_from_position(self, *a):
        """Popup : choisir son camp pour jouer contre deep grey depuis la
        position actuellement affichée (analyse ou replay)."""
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(16))
        lbl = Label(text="Jouer contre Deep Grey depuis cette position.\n"
                         "Choisissez votre camp :",
                    font_size=SF("15sp"), color=(0.1, 0.1, 0.1, 1),
                    halign="center", valign="middle", size_hint=(1, None),
                    height=S(60))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        popup = Popup(title="Deep Grey", content=content, size_hint=(0.8, 0.42))
        row = BoxLayout(orientation="horizontal", spacing=S(12),
                        size_hint=(1, None), height=S(56))
        b_blanc = RoundButton(text="Blancs", font_size=SF("16sp"), bold=True,
                              bg_color=(0.92, 0.92, 0.92, 1), color=(0, 0, 0, 1))
        b_noir = RoundButton(text="Noirs", font_size=SF("16sp"), bold=True,
                             bg_color=(0.12, 0.12, 0.12, 1), color=(1, 1, 1, 1))
        b_blanc.bind(on_release=lambda *_: (popup.dismiss(),
                     self.start_vs_ai_from_position("Blanc")))
        b_noir.bind(on_release=lambda *_: (popup.dismiss(),
                    self.start_vs_ai_from_position("Noir")))
        row.add_widget(b_blanc)
        row.add_widget(b_noir)
        content.add_widget(row)
        popup.open()

    def start_vs_ai_from_position(self, player_color):
        """Lance une partie vs deep grey à partir de la position actuellement
        affichée. Le camp au trait est conservé : si le joueur choisit la
        couleur qui n'est PAS au trait, deep grey joue en premier."""
        # 1. Capturer la position actuellement affichée (board + camp au trait)
        cur_board = [[dict(p) if p else None for p in col] for col in self.board]
        cur_turn = self.turn
        cur_blanc_fugued = getattr(self, "blanc_fugued", False)
        cur_noir_fugued = getattr(self, "noir_fugued", False)

        # 2. Configurer une partie vs IA (sans timer, partie simple)
        self.replay_mode = False
        self.analysis_mode = False
        self._analysis_from_replay = False
        self.vs_ai = True
        self.online_mode = False
        self.corr_mode = False
        self.ai_deep_mode = False
        self.target = "partie"
        self.cadence = "zen"
        self.scores = {"Joueur 1": 0, "deep grey": 0}
        self.played_blanc = {"Joueur 1": 0, "deep grey": 0}
        self.flash_round = 0
        self.flash_phase = 1
        self.last_chance = False

        # 3. deep grey joue le camp opposé à celui choisi par le joueur
        self.ai_camp = "Noir" if player_color == "Blanc" else "Blanc"

        # 4. Repartir d'une nouvelle partie puis INJECTER la position capturée.
        #    first_blanc_player doit désigner QUI a les Blancs : si le joueur a
        #    choisi Blanc, c'est lui ("Joueur 1") ; sinon c'est deep grey.
        first_blanc = "Joueur 1" if player_color == "Blanc" else "deep grey"
        self._new_game(first_blanc_player=first_blanc)
        self.board = cur_board
        self.turn = cur_turn          # camp au trait conservé
        self.blanc_fugued = cur_blanc_fugued
        self.noir_fugued = cur_noir_fugued
        self.history = []             # nouvel historique à partir d'ici
        self.viewing_idx = None
        self._initial_state = self._snapshot()
        self._reset_move_tracking()

        # 5. Orientation : joueur humain toujours en bas
        self.flipped = (player_color == "Noir")

        self._refresh_ui()
        self._update_history_ui()
        self._update_action_buttons()

        # 6. Si c'est au tour de deep grey (le camp au trait est le sien), il joue
        self._maybe_ai_turn()

    def _build_moves_text_for_resume(self):
        """Concatène toutes les notations jouées (pour la reprise après
        reconnexion). Une notation par ligne."""
        notations = []
        for entry in self.history:
            nota = entry[0] if isinstance(entry, (list, tuple)) else None
            if nota:
                notations.append(nota)
        return "\n".join(notations)

    def _on_etat_partie(self, data):
        """Reçu par le joueur qui vient de se reconnecter : reconstruit le
        plateau en rejouant toutes les notations, et restaure les horloges."""
        if not self.online_mode:
            return
        moves_text = (data or {}).get("moves_text", "") or ""
        # Repartir d'une position initiale propre puis rejouer les coups
        self._applying_remote = True
        try:
            # Réinitialiser le plateau de départ
            blanc_player = getattr(self, "_online_blanc_player", "Blanc")
            self._new_game(first_blanc_player=blanc_player)
            for nota in moves_text.split("\n"):
                nota = nota.strip()
                if nota:
                    try:
                        self._apply_notation(nota)
                    except Exception:
                        pass
        finally:
            self._applying_remote = False
        # Restaurer les horloges
        cb = (data or {}).get("clock_blanc")
        cn = (data or {}).get("clock_noir")
        if cb is not None: self.time_left["Blanc"] = cb
        if cn is not None: self.time_left["Noir"] = cn
        self._refresh_ui()
        self.board_w._redraw()

    def _add_chat_message(self, auteur, texte):
        """Ajoute un message à l'historique du chat et rafraîchit l'affichage."""
        if not hasattr(self, "_chat_messages"):
            self._chat_messages = []
        self._chat_messages.append((auteur, texte))
        # Marquer un message non lu si le chat n'est pas ouvert
        if not getattr(self, "_chat_open", False):
            self._chat_unread = getattr(self, "_chat_unread", 0) + 1
            if hasattr(self, "chat_btn"):
                self.chat_btn.text = "Chat (%d)" % self._chat_unread
        # Rafraîchir la fenêtre de chat si elle est ouverte
        if getattr(self, "_chat_open", False) and hasattr(self, "_chat_log_box"):
            self._refresh_chat_log()

    def _refresh_chat_log(self):
        """Reconstruit la liste des messages dans la fenêtre de chat."""
        if not hasattr(self, "_chat_log_box"):
            return
        self._chat_log_box.clear_widgets()
        for auteur, texte in getattr(self, "_chat_messages", []):
            is_me = (auteur == (ONLINE.pseudo or "Moi"))
            # Couleurs LISIBLES sur fond sombre : mes messages en bleu clair,
            # ceux de l'adversaire en blanc cassé. (Avant : gris foncé illisible.)
            txt_color = (0.45, 0.7, 1.0, 1) if is_me else (0.95, 0.95, 0.95, 1)
            lbl = Label(text="[b]%s[/b] : %s" % (auteur, texte),
                        markup=True, font_size=SF("13sp"),
                        color=txt_color,
                        size_hint_y=None, halign="left", valign="top")
            lbl.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
            lbl.bind(texture_size=lambda w, ts: setattr(w, "height", ts[1] + S(4)))
            self._chat_log_box.add_widget(lbl)

    def _on_chat_recu(self, data):
        """Réception d'un message de chat de l'adversaire."""
        if not getattr(self, "online_mode", False):
            return
        auteur = (data or {}).get("auteur", self.online_opponent or "Adversaire")
        texte = (data or {}).get("texte", "")
        if texte:
            self._add_chat_message(auteur, texte)

    def _open_chat(self):
        """Ouvre la boîte de chat de la partie (en ligne OU correspondance). Elle
        occupe la MOITIÉ SUPÉRIEURE de l'écran : ainsi, quand le clavier Android
        s'ouvre en bas, la saisie et les messages restent visibles au-dessus."""
        if not (getattr(self, "online_mode", False)
                or getattr(self, "corr_mode", False)):
            return
        # Marquer les messages comme lus
        self._chat_open = True
        self._chat_unread = 0
        if hasattr(self, "chat_btn"):
            self.chat_btn.text = "Chat"
        # En correspondance : recharger le chat FRAIS depuis le serveur à
        # l'ouverture (les messages de l'adversaire n'arrivent qu'au rechargement).
        if getattr(self, "corr_mode", False) and self.corr_game_id:
            def _reload(msgs, err):
                if err or msgs is None:
                    return
                self._chat_messages = [(m.get("auteur", "?"), m.get("texte", ""))
                                       for m in msgs]
                if getattr(self, "_chat_open", False):
                    self._refresh_chat_log()
            try:
                ONLINE.corr_chat_list(self.corr_game_id, _reload)
            except Exception:
                pass
        try:
            from kivy.core.window import Window as _W
            self._prev_softinput = getattr(_W, "softinput_mode", "")
            _W.softinput_mode = "pan"
        except Exception:
            self._prev_softinput = ""

        content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(10))
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, do_scroll_y=True)
        self._chat_log_box = BoxLayout(orientation="vertical", size_hint=(1, None),
                                       spacing=S(4), padding=(S(4), S(4)))
        self._chat_log_box.bind(minimum_height=self._chat_log_box.setter("height"))
        scroll.add_widget(self._chat_log_box)
        content.add_widget(scroll)
        self._refresh_chat_log()

        row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                        height=S(48), spacing=S(6))
        chat_input = TextInput(hint_text="Votre message…", multiline=False,
                               size_hint=(1, 1), font_size=SF("14sp"))
        send_btn = RoundButton(text="Envoyer", bg_color=COL_BLUE,
                               color=(1, 1, 1, 1), font_size=SF("13sp"), bold=True,
                               size_hint=(None, 1), width=S(90), radius=S(12))

        def _send(*a):
            txt = chat_input.text.strip()
            if not txt:
                return
            txt = txt[:300]
            if getattr(self, "corr_mode", False):
                # Correspondance : envoi HTTP (le serveur conserve le message).
                try:
                    ONLINE.corr_chat_send(self.corr_game_id, txt)
                except Exception:
                    pass
            else:
                try:
                    ONLINE.sio_emit("chat", {
                        "game_id": self.online_game_id, "texte": txt})
                except Exception:
                    pass
            # Afficher tout de suite mon message
            self._add_chat_message(ONLINE.pseudo or "Moi", txt)
            chat_input.text = ""
        send_btn.bind(on_release=_send)
        chat_input.bind(on_text_validate=_send)
        row.add_widget(chat_input)
        row.add_widget(send_btn)
        content.add_widget(row)

        close_btn = RoundButton(text="Fermer", bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                                size_hint=(1, None), height=S(44))
        content.add_widget(close_btn)

        # Boîte sur la MOITIÉ HAUTE de l'écran (ancrée en haut)
        popup = Popup(title="Chat, %s" % (self.online_opponent or ""),
                      content=content, size_hint=(0.96, 0.5),
                      pos_hint={"top": 0.99})

        def _restore(*a):
            self._chat_open = False
            self._chat_log_box = None
            try:
                from kivy.core.window import Window as _W
                _W.softinput_mode = getattr(self, "_prev_softinput", "")
            except Exception:
                pass
        close_btn.bind(on_release=lambda *a: (popup.dismiss()))
        popup.bind(on_dismiss=lambda *a: _restore())
        popup.open()

    def start_analysis(self):
        """Lance le mode analyse : partie depuis la position initiale, sans timer, sans fin."""
        self.replay_mode = False
        self.analysis_mode = True
        self._analysis_from_replay = False
        self.vs_ai = False
        self.online_mode = False
        self.corr_mode = False
        self.ai_camp = None
        self.target = "partie"   # peu importe, on n'utilise pas le score
        self.cadence = "zen"     # pas de timer
        self.scores = {"Joueur 1": 0, "Joueur 2": 0}
        self.played_blanc = {"Joueur 1": 0, "Joueur 2": 0}
        self.flash_round = 0
        self.flash_phase = 1
        self.last_chance = False
        self._new_game(first_blanc_player="Joueur 1")
        self._update_action_buttons()

    def start_analysis_from_replay(self):
        """Bascule le replay actuel en mode analyse à partir de la position courante.
        L'état complet du replay est sauvegardé pour pouvoir y revenir."""
        # Sauvegarder l'historique complet et la position courante pour pouvoir restaurer
        self._saved_replay_history = list(self.history)
        self._saved_replay_viewing_idx = self.viewing_idx
        self._saved_replay_initial = self._initial_state

        # Couper l'historique au point actuel pour pouvoir continuer à jouer
        if self.viewing_idx is not None and self.viewing_idx >= 0:
            self.history = self.history[:self.viewing_idx + 1]
        elif self.viewing_idx == -1:
            self.history = []
        # Sinon on garde tout l'historique
        self.replay_mode = False
        self.analysis_mode = True
        self.viewing_idx = None   # On sort du mode lecture
        self._paused = False      # important : on n'est plus en pause
        self._analysis_from_replay = True   # pour savoir où retourner
        self._reset_move_tracking()
        self._refresh_ui()
        self._update_history_ui()
        self._update_action_buttons()

    def _exit_analysis_to_replay(self):
        """Sort du mode analyse pour revenir au replay d'origine."""
        # Restaurer l'historique complet et la position courante
        self.history = list(self._saved_replay_history)
        self.viewing_idx = self._saved_replay_viewing_idx
        self._initial_state = self._saved_replay_initial
        self.analysis_mode = False
        self._analysis_from_replay = False
        self.replay_mode = True
        self._paused = False
        # Restaurer le snapshot de la position où on était quand on a cliqué "Analyser"
        if self.viewing_idx is None and self.history:
            self._restore_snapshot(self.history[-1][1])
        elif self.viewing_idx is not None and self.viewing_idx >= 0 and self.viewing_idx < len(self.history):
            self._restore_snapshot(self.history[self.viewing_idx][1])
        elif self.viewing_idx == -1:
            self._restore_snapshot(self._initial_state)
        self._reset_move_tracking()
        self._refresh_ui()
        self._update_history_ui()
        self._update_action_buttons()

    def _new_game(self, first_blanc_player):
        if self._timer_evt: self._timer_evt.cancel()
        self._game_over = False
        self._ai_pos_counts = {}
        self._ai_consecutive_maneuvers = 0   # anti allers-retours de groupe
        # Réinitialiser le delta de mélo (sinon le popup de fin réafficherait le
        # delta d'une partie précédente, ex : -16 d'une défaite sur une nulle).
        self._last_melo_delta = None
        self._last_melo_value = None
        # Réinitialiser le chat (effacé à chaque nouvelle partie)
        self._chat_messages = []
        self._chat_unread = 0
        self._chat_open = False
        if hasattr(self, "chat_btn"):
            self.chat_btn.text = "Chat"
        self.first_player_blanc = first_blanc_player
        self.played_blanc[first_blanc_player] += 1
        self.turn         = "Blanc"
        self.sel          = None
        self.group_sel    = set()
        self.moved        = False
        self.push_on      = False
        self.jumping      = False
        self.board        = [[None] * ROWS for _ in range(COLS)]
        self.captured     = {"Blanc": [], "Noir": []}
        self.blanc_fugued = False
        self.fugued_heirs = []
        # Réinit historique
        self.history = []
        self.viewing_idx = None
        # Compteur de positions (pour la règle de répétition 4x)
        self._position_counts = {}
        # Compteur des configurations des PIÈCES DE L'IA (pour la pénalité
        # anti-répétition de deep grey, indépendant de la nulle par répétition)
        self._ai_pos_counts = {}
        # Mise en évidence du dernier coup joué
        self._last_move_highlight = None   # dict {from_cells, to_cells, push_dirs}
        self._reset_move_tracking()
        if self.cadence == "zen":
            self.time_left = {"Blanc": None, "Noir": None}
        else:
            self.time_left = {k: self.cadence * 60 for k in ("Blanc", "Noir")}
        # Position de départ : standard, ou Random Fuga si un code est en attente
        # (posé par start_match / start_match_vs_ai quand l'interrupteur est ON).
        code = getattr(self, "_pending_random_code", None)
        rboard = rf_build_board(code) if code else None
        if rboard is not None:
            self.board = rboard
            self.current_random_code = code
        else:
            self._setup_pieces()
            self.current_random_code = None
        self._pending_random_code = None
        # Sauvegarde l'état initial (snapshot 0) pour pouvoir revenir au début
        self._initial_state = self._snapshot()
        self._refresh_ui()
        self._update_history_ui()
        self._paused = False
        if self.cadence != "zen":
            self._timer_evt = Clock.schedule_interval(self._tick, 1)
        else:
            self._timer_evt = None

    def _reset_move_tracking(self):
        self._move_start = None
        self._move_jumping_start = None
        self._move_is_push = False
        self._move_is_maneuver = False
        self._move_maneuver_pieces = []
        self._move_push_targets = []
        self._move_pushable_dirs = []
        self._move_is_fugue = False
        self._move_had_ejection = False
        self._last_jumped_nurse = None   # case de la nurse sautée au saut précédent
        # Mise en évidence du dernier coup (renseignée à _record_move)
        # Ne pas reset ici : c'est mis à jour à chaque coup, pas à chaque tracking reset

    def _cancel_current_move(self, which=None):
        """Annule le coup EN COURS de construction (tant qu'il n'est pas validé)
        et restaure le plateau à l'état du début du tour. Fonctionne dans tous
        les modes. N'a aucun effet si aucun coup n'est en cours, en lecture,
        ou si ce n'est pas le tour du camp correspondant au bouton.
        which : "top" ou "bot", chaque bouton n'annule que SON camp."""
        if self.replay_mode:
            return
        if self._is_viewing():
            return
        # Rien à annuler si on n'a pas commencé de coup
        if not self.moved and self.sel is None and not self.group_sel:
            return
        # Déterminer le camp associé au bouton qui a été pressé
        if which is not None:
            if which == "top":
                btn_camp = "Noir" if self.flipped else "Blanc"
            else:  # "bot"
                btn_camp = "Blanc" if self.flipped else "Noir"
            # Ce bouton n'annule que si c'est au tour de SON camp
            if self.turn != btn_camp:
                return
        # En ligne / vs IA : on n'annule que pendant SON tour
        if self.vs_ai and self.turn == self.ai_camp:
            return
        if self.online_mode and self.turn != self.online_my_color:
            return
        # Annuler toute animation en cours
        self.board_w._cancel_anim()
        # Restaurer le plateau à l'état du début du tour (dernier snapshot
        # validé, ou l'état initial si on est au tout premier coup).
        if self.history:
            snap = self.history[-1][1]
        elif getattr(self, "_initial_state", None):
            snap = self._initial_state
        else:
            snap = None
        if snap is not None:
            self._restore_snapshot(snap)
        # Réinitialiser la sélection et le tracking du coup
        self.sel = None
        self.group_sel = set()
        self.moved = False
        self.push_on = False
        self.jumping = False
        self._reset_move_tracking()
        self._refresh_ui()

    def _setup_pieces(self):
        layout = ["Soldat", "Garde", "Soldat", "Chevalier", "Garde", "Soldat", "Garde"]
        for c, t in enumerate(layout):
            self.board[c][0] = {"type": t, "camp": "Blanc"}
        for c in [1, 2, 4, 5]:
            self.board[c][1] = {"type": "Nurse", "camp": "Blanc"}
        self.board[3][1] = {"type": "Héritier", "camp": "Blanc"}
        # Pièces supplémentaires (test), Blancs
        self.board[0][1] = {"type": "Garde",  "camp": "Blanc"}   # + en do2
        self.board[6][1] = {"type": "Soldat", "camp": "Blanc"}   # × en si2
        self.board[3][2] = {"type": "Nurse",  "camp": "Blanc"}   # Nurse en fa3
        # VARIANTE : colonne fa = Héritier (fa1), Nurse (fa2), Chevalier (fa3).
        self.board[3][0] = {"type": "Héritier",  "camp": "Blanc"}  # Héritier en fa1 (fond)
        self.board[3][1] = {"type": "Nurse",     "camp": "Blanc"}  # Nurse en fa2
        self.board[3][2] = {"type": "Chevalier", "camp": "Blanc"}  # Chevalier en fa3
        for c in [1, 2, 4, 5]:
            self.board[c][6] = {"type": "Nurse", "camp": "Noir"}
        self.board[3][6] = {"type": "Héritier", "camp": "Noir"}
        for c, t in enumerate(layout):
            self.board[c][7] = {"type": t, "camp": "Noir"}
        # Pièces supplémentaires (test), Noirs (miroir)
        self.board[0][6] = {"type": "Garde",  "camp": "Noir"}    # + en do7
        self.board[6][6] = {"type": "Soldat", "camp": "Noir"}    # × en si7
        self.board[3][5] = {"type": "Nurse",  "camp": "Noir"}    # Nurse en fa6
        # VARIANTE : miroir, Héritier (fa8), Nurse (fa7), Chevalier (fa6).
        self.board[3][7] = {"type": "Héritier",  "camp": "Noir"}  # Héritier en fa8 (fond)
        self.board[3][6] = {"type": "Nurse",     "camp": "Noir"}  # Nurse en fa7
        self.board[3][5] = {"type": "Chevalier", "camp": "Noir"}  # Chevalier en fa6

    # ── Gestion de l'historique des coups ────────────────────────────────────

    def _snapshot(self):
        """Capture l'état complet du plateau pour pouvoir y revenir."""
        return {
            "board": [[dict(p) if p else None for p in col] for col in self.board],
            "captured": {k: list(v) for k, v in self.captured.items()},
            "turn": self.turn,
            "blanc_fugued": self.blanc_fugued,
            "fugued_heirs": [dict(h) for h in self.fugued_heirs],
        }

    def _restore_snapshot(self, snap):
        """Restaure un état précédemment capturé."""
        self.board = [[dict(p) if p else None for p in col] for col in snap["board"]]
        self.captured = {k: list(v) for k, v in snap["captured"].items()}
        self.turn = snap["turn"]
        self.blanc_fugued = snap["blanc_fugued"]
        self.fugued_heirs = [dict(h) for h in snap.get("fugued_heirs", [])]
        self.sel = None
        self.group_sel = set()
        self.moved = False
        self.push_on = False
        self.jumping = False

    def _position_key(self):
        """Clé de la position courante pour la détection de répétition.
        Encode l'état du board + qui doit jouer."""
        parts = []
        for c in range(COLS):
            for r in range(ROWS):
                p = self.board[c][r]
                if p is None:
                    parts.append(".")
                else:
                    parts.append(f"{p['type'][0]}{p['camp'][0]}")
        parts.append(f"|{self.turn}|{self.blanc_fugued}")
        return "".join(parts)

    def _build_highlight_from_notation(self, notation, board_before=None,
                                       explicit_push_targets=None):
        """Analyse une notation et construit le dict de mise en évidence.
        explicit_push_targets : si fourni, liste des cases (c,r) qui ont été
        explicitement choisies comme cibles de poussée (le joueur a cliqué)."""
        if not notation: return None
        n = notation.strip().rstrip("#")
        result = {"from_cells": [], "to_cells": [], "push_dirs": {}}

        # Fugue depuis case nommable : "Mi7*"
        if "*" in n and "-" not in n:
            start_str = n.replace("*", "").strip()
            start = notation_to_cell(start_str)
            if start is not None:
                result["from_cells"].append(start)
            return result

        # Manœuvre : (pieces)-dest
        if n.startswith("("):
            m = re.match(r'^\((.*)\)-(.+)$', n)
            if m:
                pieces_str = m.group(1)
                dest_str = m.group(2)
                cells = parse_cells_concat(pieces_str)
                dest = notation_to_cell(dest_str)
                if cells and dest is not None:
                    master = cells[0]
                    dc = dest[0] - master[0]
                    dr = dest[1] - master[1]
                    for cell in cells:
                        result["from_cells"].append(cell)
                        result["to_cells"].append((cell[0] + dc, cell[1] + dr))
            return result

        # Déplacement / saut / poussée
        core = n
        if ">" in core:
            move_part, _ = core.split(">", 1)
        else:
            move_part = core
        if move_part.endswith("*"):
            move_part = move_part[:-1]
        if "-" in move_part:
            start_str, end_str = move_part.split("-", 1)
        else:
            start_str, end_str = move_part, ""

        start = notation_to_cell(start_str)
        end = notation_to_cell(end_str) if end_str else None

        if start is not None:
            result["from_cells"].append(start)
        if end is not None:
            result["to_cells"].append(end)

        # Directions de poussée effectives.
        # On filtre toujours par type de pièce : Soldat → diagonales, Garde → orthogonales
        # (sécurité contre les notations bizarres ou les mauvais targets)
        if ">" in n and end is not None:
            # Type de la pièce qui pousse (lue dans board_before en start,
            # ou dans le board actuel en end si board_before non dispo)
            piece_before = None
            if start is not None and board_before is not None:
                if 0 <= start[0] < COLS and 0 <= start[1] < ROWS:
                    piece_before = board_before[start[0]][start[1]]
            if piece_before is None and end is not None:
                if 0 <= end[0] < COLS and 0 <= end[1] < ROWS:
                    piece_before = self.board[end[0]][end[1]]
            if piece_before is not None and \
               piece_before["type"] in ("Soldat", "Garde"):
                if piece_before["type"] == "Soldat":
                    valid_dirs = {(-1, -1), (1, -1), (-1, 1), (1, 1)}
                else:
                    valid_dirs = {(0, -1), (0, 1), (-1, 0), (1, 0)}
                active = []
                if explicit_push_targets:
                    for (tc, tr) in explicit_push_targets:
                        dc = tc - end[0]
                        dr = tr - end[1]
                        if dc != 0: dc = 1 if dc > 0 else -1
                        if dr != 0: dr = 1 if dr > 0 else -1
                        if (dc, dr) in valid_dirs and (dc, dr) not in active:
                            active.append((dc, dr))
                else:
                    # Fallback : scan du board_before
                    if board_before is not None:
                        for dc, dr in valid_dirs:
                            bc, br = end[0] + dc, end[1] + dr
                            if 0 <= bc < COLS and 0 <= br < ROWS:
                                if board_before[bc][br] is not None:
                                    active.append((dc, dr))
                if active:
                    result["push_dirs"][end] = active

        return result

    def _record_move(self, notation, had_ejection=False, push_targets=None):
        """Enregistre le coup qui vient d'être joué : sa notation + l'état résultant.
        push_targets : cases explicitement poussées (passé depuis _end_turn)."""
        # Un coup a été joué : on annule les propositions de nulle en attente
        self._reset_draw_offers()
        # En correspondance : envoyer le coup au serveur (HTTP), UNE SEULE FOIS.
        # Si ce coup termine la partie (mat/fugue/papatte/Trêve), on l'envoie AVEC
        # la méthode (corr_jouer enregistre le coup ET clôt la partie atomiquement,
        # en une requête), jamais en double. _corr_pending_method est posé par
        # _end_turn AVANT cet appel quand une fin est détectée.
        if (getattr(self, "corr_mode", False) and notation
                and not getattr(self, "_applying_remote", False)):
            meth = getattr(self, "_corr_pending_method", None)
            try:
                ONLINE.corr_jouer(self.corr_game_id, notation, methode=meth)
                self.corr_my_turn = False
            except Exception:
                pass
            self._corr_pending_method = None
        # Sauvegarder le board AVANT pour la mise en évidence
        board_before = None
        if self.history:
            board_before = self.history[-1][1].get("board")
        elif hasattr(self, "_initial_state") and self._initial_state:
            board_before = self._initial_state.get("board")
        # Si push_targets n'est pas fourni explicitement, on essaye de le récupérer
        # depuis l'état actuel (cas où _record_move est appelé hors _end_turn)
        if push_targets is None:
            push_targets = list(getattr(self, "_move_push_targets", []) or [])
        # Pour les coups IA / replay où on a aucun target en mémoire mais où la
        # notation contient explicitement les cases poussées, on les extrait
        if not push_targets:
            push_targets = self._reconstruct_push_targets(notation, board_before)
        # Mise en évidence du dernier coup
        self._last_move_highlight = self._build_highlight_from_notation(
            notation, board_before, explicit_push_targets=push_targets)
        # On enregistre TOUJOURS le snapshot APRES le coup
        snapshot = self._snapshot()
        self.history.append((notation, snapshot))
        self._update_history_ui()
        # Jouer le son correspondant au coup
        self._play_move_sound(notation, had_ejection=had_ejection)
        # ── Mode en ligne : envoyer MON coup à l'adversaire ──
        # (pas si c'est un coup reçu de l'adversaire qu'on est en train d'appliquer)
        if (self.online_mode and not getattr(self, "_applying_remote", False)
                and self.online_game_id):
            try:
                ONLINE.sio_emit("jouer_coup", {
                    "game_id": self.online_game_id,
                    "notation": notation,
                    "clock_blanc": self.time_left.get("Blanc"),
                    "clock_noir": self.time_left.get("Noir"),
                })
            except Exception:
                pass
        # Détecter la répétition de position (4 fois = match nul)
        if not self.replay_mode and not self.analysis_mode:
            key = self._position_key()
            self._position_counts[key] = self._position_counts.get(key, 0) + 1
            if self._position_counts[key] >= 4:
                self._end_game_repetition()
            # Compteur séparé : configuration des pièces de l'IA (pour sa
            # pénalité anti-répétition). On compte après CHAQUE coup.
            if self.vs_ai and self.ai_camp:
                try:
                    ai_key = _dg_own_pieces_key(self.board, self.ai_camp)
                    self._ai_pos_counts[ai_key] = self._ai_pos_counts.get(ai_key, 0) + 1
                except Exception:
                    pass

    def _end_game_repetition(self):
        """Termine la partie en match nul par répétition."""
        if self._timer_evt:
            self._timer_evt.cancel()
            self._timer_evt = None
        title = "Match nul par répétition"
        players = self._players()
        pA, pB = players[0], players[1]
        body  = (f"La même position s'est répétée 4 fois.\n\n"
                 f"{pA} : {self.scores[pA]}    "
                 f"{pB} : {self.scores[pB]}")
        self._save_game(winner_player=None, method="repetition", pts=0)
        self._decide_next(title, body, winner_player=None)

    def _play_move_sound(self, notation, had_ejection=False):
        """Analyse la notation et joue le(s) son(s) approprié(s)."""
        if not notation: return
        notation = notation.strip()

        # Détecter et retirer les suffixes de fin de partie
        is_mat = notation.endswith("#")
        n = notation
        if is_mat:
            n = n[:-1]

        # ── Manœuvre : (pieces)-dest, glissando de 4 notes vers les graves ──
        if n.startswith("("):
            m = re.match(r'^\((.*)\)-(.+)$', n)
            if m:
                pieces_str = m.group(1)
                dest_str = m.group(2)
                dest = notation_to_cell(dest_str)
                # Pièce maître (1ère case du groupe noté)
                cells = parse_cells_concat(pieces_str)
                if cells:
                    master = cells[0]
                    SOUNDS.play_note_cell(master[0], master[1])
                if dest is not None:
                    SOUNDS.play_glissando(dest[0], dest[1], 4, direction=-1,
                                          initial_delay=0.25)
            return

        # ── Fugue : "Start*" (case d'arrivée non nommable) ──
        if "*" in n and "-" not in n:
            start_str = n.replace("*", "").strip()
            start = notation_to_cell(start_str)
            # Son de la case de départ (faute de case d'arrivée) puis arpège fugue
            if start is not None:
                SOUNDS.play_note_cell(start[0], start[1])
            SOUNDS.play_special("fugue", delay=0.16)
            return

        # ── Déplacement / saut / poussée ──
        push_part = ""
        ends_fugue = False
        core = n
        if ">" in core:
            move_part, push_part = core.split(">", 1)
        else:
            move_part = core
        if move_part.endswith("*"):
            ends_fugue = True
            move_part = move_part[:-1]

        if "-" in move_part:
            start_str, end_str = move_part.split("-", 1)
        else:
            start_str, end_str = move_part, ""

        end = notation_to_cell(end_str) if end_str else None
        start = notation_to_cell(start_str)

        # Son de la case de départ : joué immédiatement
        if start is not None:
            SOUNDS.play_note_cell(start[0], start[1])

        # Son de la case d'arrivée (ou glissando si poussée) : 250 ms plus tard
        if end is not None:
            if ">" in n:
                # Glissando ascendant arrivant sur la note de fin
                SOUNDS.play_glissando(end[0], end[1], 4, direction=+1,
                                      initial_delay=0.25)
            else:
                # Déplacement simple ou multisaut : note d'arrivée
                end_name = SOUNDS.note_name_for_cell(end[0], end[1])
                if end_name:
                    SOUNDS.play_delayed(end_name, 0.25)

        # Si fugue sur case nommable : arpège fugue après le son du coup
        if ends_fugue:
            SOUNDS.play_special("fugue", delay=0.41)

    def _nav_animate(self, old_board):
        """Anime la transition entre old_board (avant navigation) et le board
        courant (déjà restauré). Utilisé par les flèches de navigation."""
        if old_board is None:
            self.board_w._redraw()
            return
        slides = self._build_slides_from_diff(old_board, self.board)
        if slides:
            self.board_w.animate_slide(slides, on_done=self.board_w._redraw)
        else:
            self.board_w._redraw()

    def _nav_prev(self):
        """Recule d'un coup dans l'historique."""
        if not self.history: return
        self.board_w._cancel_anim()
        old_board = [[dict(p) if p else None for p in col] for col in self.board] if self.board else None
        if self.viewing_idx is None:
            self.viewing_idx = len(self.history) - 1
        if self.viewing_idx == 0:
            self._restore_snapshot(self._initial_state)
            self.viewing_idx = -1
            self._last_move_highlight = None
        elif self.viewing_idx > 0:
            self.viewing_idx -= 1
            self._restore_snapshot(self.history[self.viewing_idx][1])
            self._update_highlight_for_idx(self.viewing_idx)
            self._play_nav_sound(self.viewing_idx)
        self._refresh_ui_no_board()
        self._update_history_ui()
        self._nav_animate(old_board)

    def _nav_next(self):
        """Avance d'un coup dans l'historique. Si on atteint le dernier coup,
        on repasse au présent (déblocage des actions)."""
        if self.viewing_idx is None: return
        if not self.history:   # historique vide : rien à faire (évite IndexError)
            self.viewing_idx = None
            return
        self.board_w._cancel_anim()
        old_board = [[dict(p) if p else None for p in col] for col in self.board] if self.board else None
        if self.viewing_idx + 1 < len(self.history):
            self.viewing_idx += 1
            self._restore_snapshot(self.history[self.viewing_idx][1])
            self._update_highlight_for_idx(self.viewing_idx)
            self._play_nav_sound(self.viewing_idx)
            # Si on vient d'atteindre le dernier coup, repasser en mode présent
            if self.viewing_idx >= len(self.history) - 1:
                self.viewing_idx = None
        else:
            self.viewing_idx = None
            self._restore_snapshot(self.history[-1][1])
            self._update_highlight_for_idx(len(self.history) - 1)
        self._refresh_ui_no_board()
        self._update_history_ui()
        self._nav_animate(old_board)
        # Si on est de retour au présent et que c'est à l'IA de jouer, déclencher
        self._maybe_ai_turn()

    def _nav_to(self, idx):
        """Saute à un coup précis."""
        if not self.history: return
        self.board_w._cancel_anim()
        old_board = [[dict(p) if p else None for p in col] for col in self.board] if self.board else None
        if idx >= len(self.history) - 1:
            self.viewing_idx = None
            self._restore_snapshot(self.history[-1][1])
            self._update_highlight_for_idx(len(self.history) - 1)
            self._play_nav_sound(len(self.history) - 1)
        else:
            self.viewing_idx = idx
            self._restore_snapshot(self.history[idx][1])
            self._update_highlight_for_idx(idx)
            self._play_nav_sound(idx)
        self._refresh_ui_no_board()
        self._update_history_ui()
        self._nav_animate(old_board)
        # Si on est de retour au présent et que c'est à l'IA de jouer, déclencher
        self._maybe_ai_turn()

    def _update_highlight_for_idx(self, idx):
        """Met à jour la mise en évidence du dernier coup pour l'index donné."""
        if idx is None or idx < 0 or idx >= len(self.history):
            self._last_move_highlight = None
            return
        notation = self.history[idx][0]
        # Board AVANT ce coup : snapshot du coup précédent ou état initial
        if idx == 0:
            board_before = self._initial_state.get("board") if self._initial_state else None
        else:
            board_before = self.history[idx - 1][1].get("board")
        # Reconstruire push_targets à partir de la notation
        push_targets = self._reconstruct_push_targets(notation, board_before)
        self._last_move_highlight = self._build_highlight_from_notation(
            notation, board_before, explicit_push_targets=push_targets)

    def _reconstruct_push_targets(self, notation, board_before):
        """Reconstruit les cases poussées à partir d'une notation, pour la
        navigation dans l'historique où on n'a pas le tracking en direct."""
        if not notation: return []
        n = notation.strip().rstrip("#")
        if ">" not in n: return []
        # Récupérer la case d'arrivée du déplacement principal
        move_part, after_push = n.split(">", 1)
        if move_part.endswith("*"): move_part = move_part[:-1]
        if "-" not in move_part: return []
        _, end_str = move_part.split("-", 1)
        end = notation_to_cell(end_str)
        if end is None: return []
        # Si après ">" il y a des cases listées : ce sont les cibles explicites
        after_push = after_push.strip()
        if after_push:
            cells = parse_cells_concat(after_push)
            return cells
        # Sinon (notation "Ré1-Do2>" sans précisions) : toutes les directions
        # où il y avait une pièce adjacente dans board_before
        if board_before is None: return []
        # Type de la pièce qui a poussé : lue dans board_before en start
        if "-" in move_part:
            start_str = move_part.split("-", 1)[0]
            start = notation_to_cell(start_str)
        else:
            start = None
        if start is None: return []
        if 0 <= start[0] < COLS and 0 <= start[1] < ROWS:
            piece_before = board_before[start[0]][start[1]]
        else:
            piece_before = None
        if piece_before is None or piece_before["type"] not in ("Soldat", "Garde"):
            return []
        if piece_before["type"] == "Soldat":
            candidate_dirs = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        else:
            candidate_dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        targets = []
        for dc, dr in candidate_dirs:
            tc, tr = end[0] + dc, end[1] + dr
            if 0 <= tc < COLS and 0 <= tr < ROWS:
                if board_before[tc][tr] is not None:
                    targets.append((tc, tr))
        return targets

    def _play_nav_sound(self, idx):
        """Joue le son du coup d'index idx (lors de la navigation)."""
        if idx is None or idx < 0 or idx >= len(self.history):
            return
        notation = self.history[idx][0]
        self._play_move_sound(notation)

    def _is_viewing(self):
        """Vrai si l'on est en mode lecture (pas au présent)."""
        return self.viewing_idx is not None

    def _update_history_ui(self):
        """Reconstruit le bandeau scrollable de l'historique."""
        if not hasattr(self, "history_box"): return
        Clock.schedule_once(lambda dt: self._do_update_history_ui(), 0)

    def _do_update_history_ui(self):
        """Reconstruction effective du bandeau d'historique."""
        if not hasattr(self, "history_box"): return
        try:
            self.history_box.clear_widgets()
            # En mode Random Fuga : afficher le code de la position en tête du
            # bandeau (couleur claire du thème), pour identifier/vérifier le tirage.
            rcode = getattr(self, "current_random_code", None)
            if rcode:
                code_btn = Button(text=rcode, font_size=SF("13sp"), bold=True,
                                  size_hint=(None, 1), padding=(8, 0),
                                  background_normal="", background_color=(0, 0, 0, 0),
                                  color=COL_ORANGE)
                _cl = CoreLabel(text=rcode, font_size=SF("13sp"), bold=True)
                _cl.refresh()
                code_btn.width = _cl.texture.width + S(16)
                self.history_box.add_widget(code_btn)
            i = 0
            turn_num = 1
            active_idx = (len(self.history) - 1) if self.viewing_idx is None else self.viewing_idx
            while i < len(self.history):
                blanc_move = self.history[i][0] if i < len(self.history) else ""
                noir_move = self.history[i+1][0] if i + 1 < len(self.history) else ""
                i_blanc = i
                i_noir = i + 1 if i + 1 < len(self.history) else None
                label_text = f"{turn_num}.{blanc_move}"
                if noir_move:
                    label_text += f"/{noir_move}"
                b = Button(text=label_text, font_size=SF("13sp"), bold=True,
                           size_hint=(None, 1), padding=(8, 0),
                           background_normal="", background_color=(0, 0, 0, 0),
                           color=(1, 1, 1, 1))
                if i_blanc == active_idx or i_noir == active_idx:
                    b.color = (0, 0, 0, 1)   # noir : lisible sur tous les thèmes
                    b.bold = True
                # Largeur calculée IMMÉDIATEMENT (mesure synchrone du texte) au
                # lieu d'attendre l'événement asynchrone texture_size, qui faussait
                # le calcul du scroll et laissait le bandeau apparaître "vide".
                _lbl = CoreLabel(text=label_text, font_size=SF("13sp"), bold=True)
                _lbl.refresh()
                b.width = _lbl.texture.width + S(16)
                self.history_box.add_widget(b)
                b.bind(on_release=lambda btn, t=(i_noir if i_noir is not None
                                                 else i_blanc): self._nav_to(t))
                i += 2
                turn_num += 1
            # Scroll auto vers le dernier coup (à droite) si on est au présent.
            # La largeur du box est désormais correcte tout de suite, donc on peut
            # scroller de façon fiable.
            if self.viewing_idx is None and hasattr(self, "history_scroll"):
                def _scroll_end(dt):
                    try:
                        if self.history_box.width > self.history_scroll.width:
                            self.history_scroll.scroll_x = 1
                        else:
                            self.history_scroll.scroll_x = 0
                    except Exception:
                        pass
                Clock.schedule_once(_scroll_end, 0)
        except Exception:
            # En cas de souci de rendu, on ne casse pas le jeu
            pass

    def _back_to_menu(self, *a):
        if self._timer_evt:
            self._timer_evt.cancel()
            self._timer_evt = None
        # Si on est en analyse venant d'un replay, retour au replay (pas au menu)
        if self.analysis_mode and self._analysis_from_replay:
            self._exit_analysis_to_replay()
            return
        self.manager.current = "menu"

    def _toggle_flip(self, *a):
        self.flipped = not self.flipped
        self._refresh_ui()
        # Les côtés ont changé : réajuster la visibilité des boutons par camp
        self._update_side_buttons()

    def _update_action_buttons(self):
        """Adapte le bouton pause + boutons abandon selon le mode."""
        if not hasattr(self, "pause_btn"): return
        if self.replay_mode:
            # En replay : pause devient "Retour" → revient à l'historique
            self.pause_btn.text = "<<"
            self.pause_btn.unbind(on_release=self._pause_release_handler)
            self.pause_btn.unbind(on_release=self._back_to_history)
            self.pause_btn.unbind(on_release=self._back_to_menu)
            self.pause_btn.bind(on_release=self._back_to_history)
            if hasattr(self, "top_abandon"):
                self.top_abandon.disabled = True
                self.top_abandon.opacity = 0
            if hasattr(self, "bot_abandon"):
                self.bot_abandon.disabled = True
                self.bot_abandon.opacity = 0
            # Afficher le bouton Analyser
            if hasattr(self, "analyse_btn"):
                self.analyse_btn.opacity = 1
                self.analyse_btn.disabled = False
            # Afficher le bouton Deep Grey (jouer vs IA depuis la position)
            if hasattr(self, "dg_btn"):
                self.dg_btn.opacity = 1
                self.dg_btn.disabled = False
        elif self.analysis_mode:
            # En analyse : pause devient retour au menu (puisqu'aucune sauvegarde)
            self.pause_btn.text = "<<"
            self.pause_btn.unbind(on_release=self._pause_release_handler)
            self.pause_btn.unbind(on_release=self._back_to_history)
            self.pause_btn.unbind(on_release=self._back_to_menu)
            self.pause_btn.bind(on_release=self._back_to_menu)
            if hasattr(self, "top_abandon"):
                self.top_abandon.disabled = True
                self.top_abandon.opacity = 0
            if hasattr(self, "bot_abandon"):
                self.bot_abandon.disabled = True
                self.bot_abandon.opacity = 0
            if hasattr(self, "analyse_btn"):
                self.analyse_btn.opacity = 0
                self.analyse_btn.disabled = True
            # Deep Grey visible en analyse
            if hasattr(self, "dg_btn"):
                self.dg_btn.opacity = 1
                self.dg_btn.disabled = False
        else:
            # En jeu normal : pause = pause
            self.pause_btn.text = "| |"
            self.pause_btn.unbind(on_release=self._back_to_history)
            self.pause_btn.unbind(on_release=self._back_to_menu)
            self.pause_btn.unbind(on_release=self._pause_release_handler)
            self.pause_btn.bind(on_release=self._pause_release_handler)
            # En ligne (et en correspondance) : le joueur est TOUJOURS en bas et
            # ne doit voir QUE ses propres boutons (abandon / proposer nulle).
            # On masque donc les boutons du camp du haut (l'adversaire).
            online_like = (getattr(self, "online_mode", False)
                           or getattr(self, "corr_mode", False))
            if hasattr(self, "top_abandon"):
                self.top_abandon.disabled = online_like
                self.top_abandon.opacity = 0 if online_like else 1
            if hasattr(self, "top_draw"):
                self.top_draw.disabled = online_like
                self.top_draw.opacity = 0 if online_like else 1
            if hasattr(self, "bot_abandon"):
                self.bot_abandon.disabled = False
                self.bot_abandon.opacity = 1
            if hasattr(self, "bot_draw"):
                self.bot_draw.disabled = False
                self.bot_draw.opacity = 1
            if hasattr(self, "analyse_btn"):
                self.analyse_btn.opacity = 0
                self.analyse_btn.disabled = True
            # Deep Grey masqué en jeu normal
            if hasattr(self, "dg_btn"):
                self.dg_btn.opacity = 0
                self.dg_btn.disabled = True

        # Bouton mode IA visible UNIQUEMENT en partie vs deep grey
        if hasattr(self, "ai_mode_btn"):
            if getattr(self, "vs_ai", False) and not self.replay_mode and not self.analysis_mode:
                self.ai_mode_btn.opacity = 1
                self.ai_mode_btn.disabled = False
                self._refresh_ai_mode_btn()
            else:
                self.ai_mode_btn.opacity = 0
                self.ai_mode_btn.disabled = True

        # Bouton Chat visible en partie en ligne ET en correspondance
        if hasattr(self, "chat_btn"):
            show_chat = ((getattr(self, "online_mode", False)
                          or getattr(self, "corr_mode", False))
                         and not self.replay_mode and not self.analysis_mode)
            if show_chat:
                self.chat_btn.opacity = 1
                self.chat_btn.disabled = False
            else:
                self.chat_btn.opacity = 0
                self.chat_btn.disabled = True

        # Visibilité fine des boutons ↶ (annuler), ½ (nulle), X (abandon)
        # selon le mode et le côté.
        self._update_side_buttons()

    def _set_btn_visible(self, btn_attr, visible):
        """Affiche ou masque un bouton par son nom d'attribut."""
        if hasattr(self, btn_attr):
            b = getattr(self, btn_attr)
            b.opacity = 1 if visible else 0
            b.disabled = not visible

    def _update_side_buttons(self):
        """Gère quels boutons ↶ / ½ / X apparaissent de chaque côté :
        - local : tout des deux côtés
        - vs deep grey : pas de ½ ; ↶ et X seulement du côté du joueur humain
        - en ligne : pas de ½ adverse ; ↶ et X seulement de SON côté
        En replay/analyse, les abandons sont déjà gérés plus haut ; on masque
        ici ↶ et ½ partout."""
        if self.replay_mode or self.analysis_mode:
            for attr in ("top_undo", "bot_undo", "top_draw", "bot_draw"):
                self._set_btn_visible(attr, False)
            return

        # Quel côté est "en bas" = le joueur local. flipped=True => Blanc en bas.
        bot_camp = "Blanc" if self.flipped else "Noir"
        top_camp = "Noir" if self.flipped else "Blanc"

        if self.vs_ai:
            # Le joueur humain est le camp opposé à l'IA
            human_camp = "Blanc" if self.ai_camp == "Noir" else "Noir"
            human_is_bot = (human_camp == bot_camp)
            # ↶ et X : seulement côté humain. ½ : nulle part.
            self._set_btn_visible("bot_undo", human_is_bot)
            self._set_btn_visible("bot_abandon", human_is_bot)
            self._set_btn_visible("top_undo", not human_is_bot)
            self._set_btn_visible("top_abandon", not human_is_bot)
            self._set_btn_visible("bot_draw", False)
            self._set_btn_visible("top_draw", False)
        elif self.online_mode:
            # Le joueur local est toujours en bas (orientation forcée).
            self._set_btn_visible("bot_undo", True)
            self._set_btn_visible("bot_abandon", True)
            self._set_btn_visible("bot_draw", True)
            self._set_btn_visible("top_undo", False)
            self._set_btn_visible("top_abandon", False)
            self._set_btn_visible("top_draw", False)
        elif getattr(self, "corr_mode", False):
            # Correspondance : joueur local en bas. Abandon + annuler le coup ;
            # pas de ½ (temps illimité, on abandonne si ça gonfle).
            self._set_btn_visible("bot_undo", True)
            self._set_btn_visible("bot_abandon", True)
            self._set_btn_visible("bot_draw", False)
            self._set_btn_visible("top_undo", False)
            self._set_btn_visible("top_abandon", False)
            self._set_btn_visible("top_draw", False)
        else:
            # Local : tout des deux côtés
            for attr in ("top_undo", "bot_undo", "top_draw", "bot_draw",
                         "top_abandon", "bot_abandon"):
                self._set_btn_visible(attr, True)

    def _refresh_ai_mode_btn(self):
        """Met à jour le texte du bouton de mode IA selon l'état."""
        if not hasattr(self, "ai_mode_btn"): return
        deep = getattr(self, "ai_deep_mode", False)
        # Même couleur sombre pour les deux états, comme pause / flip
        self.ai_mode_btn.bg_color = (0.15, 0.15, 0.15, 1)
        self.ai_mode_btn.text = "Profond" if deep else "Rapide"

    def _toggle_ai_mode(self, *a):
        """Bascule entre mode rapide et mode profond pour deep grey."""
        self.ai_deep_mode = not getattr(self, "ai_deep_mode", False)
        self._refresh_ai_mode_btn()

    def _pause_release_handler(self, *a):
        open_pause_popup(self)

    def _back_to_history(self, *a):
        """Retour à l'écran d'historique depuis le mode replay (vers l'écran
        d'où la partie a été ouverte : local ou en ligne)."""
        if self._timer_evt:
            self._timer_evt.cancel()
            self._timer_evt = None
        self.replay_mode = False
        target = getattr(self, "_replay_origin", "history_local")
        self.manager.current = target if target in ("history_local", "history_online") \
            else "history_local"

    def _pause_game(self):       self._paused = True
    def _resume_after_pause(self): self._paused = False

    def _tick(self, dt):
        # Le chrono continue même en pause (anti-triche)
        self.time_left[self.turn] -= 1
        if self.time_left[self.turn] <= 0:
            losing_color = self.turn
            # En ligne : je ne déclare la perte au temps que si c'est MON horloge.
            # Si c'est celle de l'adversaire, j'attends qu'il le signale (sa machine
            # fait foi pour son temps).
            if self.online_mode and losing_color != self.online_my_color:
                self.time_left[losing_color] = 0
                self._refresh_ui()
                return  # on continue d'attendre le signal de l'adversaire
            self._end_game_by_color(loser_color=losing_color, method="temps")
            return False
        self._refresh_ui()

    @staticmethod
    def _fmt(s):
        if s is None: return "∞"
        s = max(0, s)
        return f"{s // 60:02d}:{s % 60:02d}"

    def _players(self):
        """Renvoie les deux noms de joueurs courants."""
        return list(self.scores.keys())

    def _player_of(self, color):
        if color == "Blanc": return self.first_player_blanc
        return self._other_player(self.first_player_blanc)

    def _other_player(self, p):
        players = self._players()
        for name in players:
            if name != p:
                return name
        return "Joueur 2"

    def target_max(self):
        if self.target == "flash": return "F"
        if self.target == "partie": return "1"
        return self.target

    def _refresh_ui(self):
        self._refresh_ui_no_board()
        self.board_w._redraw()

    def _refresh_ui_no_board(self):
        """Met à jour tous les bandeaux/infos SANS redessiner le plateau.
        Utile pendant une animation pour ne pas écraser la couche animée."""
        top_camp = "Noir"  if self.flipped else "Blanc"
        bot_camp = "Blanc" if self.flipped else "Noir"

        def vif(c):   return COL_ORANGE     if c == "Blanc" else COL_BLUE
        def terne(c): return COL_ORANGE_DIM if c == "Blanc" else COL_BLUE_DIM

        self._top_col.rgba = vif(top_camp) if self.turn == top_camp else terne(top_camp)
        self._bot_col.rgba = vif(bot_camp) if self.turn == bot_camp else terne(bot_camp)

        self.top_timer.text = self._fmt(self.time_left[top_camp])
        self.bot_timer.text = self._fmt(self.time_left[bot_camp])

        ptop = self._player_of(top_camp)
        pbot = self._player_of(bot_camp)
        # Si l'adversaire est en cours de déconnexion, ne pas écraser le statut
        # "(déco Xs)" affiché dans sa barre par le compte à rebours.
        _dc_active = getattr(self, "_dc_opp_name", None) is not None
        # En partie en ligne : afficher le Mélo à côté du nom de chaque joueur.
        if getattr(self, "online_mode", False):
            my_melo = ONLINE.melo
            opp_melo = getattr(self, "online_opp_melo", None) or 1500
            my_color = getattr(self, "online_my_color", None)
            top_is_me = (my_color == top_camp)
            top_melo = my_melo if top_is_me else opp_melo
            bot_melo = opp_melo if top_is_me else my_melo
            if not _dc_active:
                self.top_name.text = "%s  (%d)" % (ptop, top_melo)
            self.bot_name.text = "%s  (%d)" % (pbot, bot_melo)
        else:
            if not _dc_active:
                self.top_name.text = ptop
            self.bot_name.text = pbot
        # En correspondance, le score head-to-head est cumulatif et SANS objectif
        # fixe → on affiche "X / ..." plutôt que "X / 1".
        denom = "..." if getattr(self, "corr_mode", False) else self.target_max()
        self.top_score.text = f"{self.scores[ptop]} / {denom}"
        self.bot_score.text = f"{self.scores[pbot]} / {denom}"

        opp_top = "Blanc" if top_camp == "Noir" else "Noir"
        opp_bot = "Blanc" if bot_camp == "Noir" else "Noir"
        self.top_caps.update_pieces(self.captured[opp_top])
        self.bot_caps.update_pieces(self.captured[opp_bot])

    def apply_theme_colors(self):
        """Met à jour les couleurs du jeu après un changement de thème."""
        # Fonds des cartes info
        if hasattr(self, "_top_info_col"):
            self._top_info_col.rgba = COL_BG_MENU
        if hasattr(self, "_bot_info_col"):
            self._bot_info_col.rgba = COL_BG_MENU
        # Bandeaux + plateau (relisent les couleurs globales)
        if self.board is not None:
            self._refresh_ui()

    def is_round(self, p):
        return p is not None and p["type"] in ("Nurse", "Héritier")

    def is_square(self, p):
        return p is not None and p["type"] in ("Soldat", "Garde")

    def _has_allied_knight_nbr(self, c, r):
        """True si une pièce de MON camp en (c,r) est adjacente à un Chevalier
        du MÊME camp. Le Chevalier remobilise les pièces alliées (rondes et
        carrées) qui le touchent."""
        p = self.board[c][r]
        if not p:
            return False
        camp = p["camp"]
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == dr == 0: continue
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    q = self.board[nc][nr]
                    if q and q.get("type") == "Chevalier" and q["camp"] == camp:
                        return True
        return False

    def has_round_nbr(self, c, r):
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == dr == 0: continue
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if self.is_round(self.board[nc][nr]):
                        return True
        return False

    def has_square_nbr(self, c, r):
        """Une pièce carrée (Soldat/Garde) doit toucher une autre carrée pour
        bouger. Le Chevalier ne compte pas comme carrée."""
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == dr == 0: continue
                nc, nr = c + dc, r + dr
                if 0 <= nc < COLS and 0 <= nr < ROWS:
                    if self.is_square(self.board[nc][nr]):
                        return True
        return False

    def push_activated(self, ptype, dc, dr):
        if ptype == "Soldat": return abs(dc) + abs(dr) == 1
        if ptype == "Garde":  return abs(dc) == abs(dr) == 1
        return False

    def push_valid(self, ptype, dc, dr):
        if ptype == "Soldat": return abs(dc) == abs(dr) == 1
        if ptype == "Garde":  return abs(dc) + abs(dr) == 1
        return False

    def _compute_pushable_dirs(self, c, r, ptype):
        """Renvoie la liste des cases adjacentes occupées dans les directions de poussée."""
        if ptype == "Soldat":
            dirs = [(-1, -1), (1, -1), (-1, 1), (1, 1)]   # diagonales
        elif ptype == "Garde":
            dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]     # orthogonales
        else:
            return []
        result = []
        for dc, dr in dirs:
            nc, nr = c + dc, r + dr
            if self._on_board(nc, nr) and self.board[nc][nr]:
                result.append((nc, nr))
        return result

    def _on_board(self, c, r):
        return 0 <= c < COLS and 0 <= r < ROWS

    def _is_rally_dest(self, c, r, piece):
        if c not in RALLY: return False
        if piece["type"] != "Héritier": return False
        if piece["camp"] == "Blanc" and r == 8:  return True
        if piece["camp"] == "Noir"  and r == -1: return True
        return False

    def _valid_dest(self, c, r, piece):
        return self._on_board(c, r) or self._is_rally_dest(c, r, piece)

    def _is_empty(self, c, r):
        if self._on_board(c, r): return self.board[c][r] is None
        return True

    def _group_of(self, c, r):
        p = self.board[c][r]
        if not self.is_square(p): return set()
        camp = p["camp"]
        seen = {(c, r)}; stack = [(c, r)]
        while stack:
            x, y = stack.pop()
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    if dx == dy == 0: continue
                    nx, ny = x + dx, y + dy
                    if (nx, ny) in seen: continue
                    if not self._on_board(nx, ny): continue
                    q = self.board[nx][ny]
                    if self.is_square(q) and q["camp"] == camp:
                        seen.add((nx, ny)); stack.append((nx, ny))
        return seen

    def handle_cell(self, col, row):
        if self._paused: return
        # En mode replay pur : pas de jeu possible
        if self.replay_mode and self._is_viewing(): return
        if self.replay_mode: return   # même au présent en replay, on ne joue pas
        # Contre l'IA : on bloque les clics quand c'est au tour de deep grey
        if self.vs_ai and self.turn == self.ai_camp and not self._is_viewing():
            return
        # En ligne : on ne peut jouer que pendant SON tour (les coups adverses
        # arrivent via le réseau).
        if self.online_mode and self.turn != self.online_my_color \
                and not self._is_viewing():
            return
        # En correspondance : on ne peut jouer que si c'est notre tour
        if getattr(self, "corr_mode", False) and not self._is_viewing():
            if self.turn != self.corr_my_color or not self.corr_my_turn:
                return
        # En mode analyse : si on est sur un coup passé et qu'on joue, on coupe la suite
        if self.analysis_mode and self._is_viewing():
            # On clippe l'historique à la position courante
            idx = self.viewing_idx
            if idx == -1:
                self.history = []
            else:
                self.history = self.history[:idx + 1]
            self.viewing_idx = None
            self._update_history_ui()
        # En jeu normal : pas de jeu possible si on visualise un coup passé
        if not self.analysis_mode and self._is_viewing(): return
        if self.sel: self._with_sel(col, row)
        else:        self._no_sel(col, row)

    def _no_sel(self, col, row):
        if not self._on_board(col, row): return
        p = self.board[col][row]
        if p and p["camp"] == self.turn:
            if self.is_round(p) and not self.has_round_nbr(col, row): return
            if self.is_square(p) and not self.has_square_nbr(col, row): return
            self.sel       = (col, row)
            self.group_sel = set()
            self.moved     = False
            self.push_on   = False
            self.jumping   = False
            # ── Tracking pour la notation ──
            self._move_start = (col, row)
            self._move_jumping_start = (col, row)
            self._move_is_push = False
            self._move_is_maneuver = False
            self._move_maneuver_pieces = []
            self._move_push_targets = []
            self._move_pushable_dirs = []
            self._move_is_fugue = False
            self.board_w._redraw()

    def _with_sel(self, col, row):
        oc, or_ = self.sel
        piece   = self.board[oc][or_]
        dc, dr  = col - oc, row - or_

        if col == oc and row == or_:
            if self.moved: self._end_turn()
            else:
                self.sel = None; self.group_sel = set()
                self.board_w._redraw()
            return

        if self.is_square(piece) and not self.moved:
            target = self.board[col][row] if self._on_board(col, row) else None
            if target and self.is_square(target) and target["camp"] == self.turn:
                if (col, row) in self.group_sel:
                    self.group_sel.discard((col, row))
                else:
                    if (col, row) in self._group_of(oc, or_):
                        self.group_sel.add((col, row))
                self.board_w._redraw()
                return

        if self.moved and self.push_on:
            if (self.push_valid(piece["type"], dc, dr) and
                    self._on_board(col, row) and self.board[col][row]):
                # Tracking : noter qu'on est en poussée, et enregistrer cette cible
                self._move_is_push = True
                self._move_push_targets.append((col, row))
                self._last_push_slides = []
                self.do_push(col, row, dc, dr)
                # Animer le glissement des pièces poussées
                if self.board:
                    slides = getattr(self, "_last_push_slides", [])
                    if slides:
                        self.board_w.animate_slide(slides, on_done=self.board_w._redraw)
                    else:
                        self.board_w._redraw()
            return

        if self.is_square(piece) and self.group_sel and not self.moved:
            if abs(dc) <= 1 and abs(dr) <= 1 and (dc != 0 or dr != 0):
                if self._try_maneuver(dc, dr):
                    self.moved   = True
                    self.push_on = False
                    self.jumping = False
                    slides = getattr(self, "_last_maneuver_slides", [])
                    if slides:
                        self.board_w.animate_slide(slides, on_done=self._refresh_ui)
                    else:
                        self._refresh_ui()
            return

        if self.is_round(piece) and not self.group_sel and (not self.moved or self.jumping):
            if abs(dc) in (0, 2) and abs(dr) in (0, 2) and abs(dc) + abs(dr) > 0:
                mc, mr = oc + dc // 2, or_ + dr // 2
                if (self._on_board(mc, mr) and
                        self.is_round(self.board[mc][mr]) and
                        self._valid_dest(col, row, piece) and
                        self._is_empty(col, row)):
                    # Règle anti-aller-retour : on ne peut pas re-sauter
                    # IMMÉDIATEMENT par-dessus la même nurse qu'au saut précédent
                    if self._last_jumped_nurse is not None and \
                       (mc, mr) == self._last_jumped_nurse:
                        return
                    self.board[oc][or_] = None
                    if self._on_board(col, row):
                        self.board[col][row] = piece
                        self.sel     = (col, row)
                        self.moved   = True
                        self.jumping = True
                        self.push_on = False
                        self._last_jumped_nurse = (mc, mr)
                        # Animation : le pion bondit de sa case à la case d'arrivée
                        self.board_w.animate_slide(
                            [(piece, (oc, or_), (col, row))],
                            on_done=self._refresh_ui)
                    else:
                        self.moved = True
                        # Animer le bond de l'Héritier jusqu'au ralliement, puis fuguer
                        fugue_fn = (lambda: self._fugue_blanc((col, row))) if piece["camp"] == "Blanc" \
                                   else (lambda: self._fugue_noir((col, row)))
                        self.board_w.animate_slide(
                            [(piece, (oc, or_), (col, row))],
                            on_done=fugue_fn)
                    return

        if abs(dc) <= 1 and abs(dr) <= 1 and not self.moved and not self.group_sel:
            if not self._valid_dest(col, row, piece): return
            if not self._is_empty(col, row): return
            if self.is_round(piece) and not self.has_round_nbr(oc, or_): return
            self.board[oc][or_] = None
            if self._on_board(col, row):
                self.board[col][row] = piece
                self.sel     = (col, row)
                self.moved   = True
                self.jumping = False
                self.push_on = self.push_activated(piece["type"], dc, dr)
                # Si la poussée s'active : précalculer toutes les directions de poussée possibles
                if self.push_on:
                    self._move_pushable_dirs = self._compute_pushable_dirs(col, row, piece["type"])
                # Animation de glissement (cas 1 : déplacement simple)
                self.board_w.animate_slide(
                    [(piece, (oc, or_), (col, row))],
                    on_done=self._refresh_ui)
            else:
                self.moved = True
                # Animer l'Héritier qui glisse jusqu'à sa case de ralliement
                # (col,row), il y reste visible, PUIS déclencher la fugue.
                fugue_fn = (lambda: self._fugue_blanc((col, row))) if piece["camp"] == "Blanc" \
                           else (lambda: self._fugue_noir((col, row)))
                self.board_w.animate_slide(
                    [(piece, (oc, or_), (col, row))],
                    on_done=fugue_fn)
            return

        if not self.moved:
            self.sel = None; self.group_sel = set()
            self.board_w._redraw()

    def _try_maneuver(self, dc, dr):
        all_sel = {self.sel} | self.group_sel
        for (c, r) in all_sel:
            nc, nr = c + dc, r + dr
            if not self._on_board(nc, nr): return False
            occ = self.board[nc][nr]
            if occ is None: continue
            if (nc, nr) in all_sel: continue
            return False
        # Tracking : noter qu'on est en manœuvre, et les pièces (maître en premier)
        oc, or_ = self.sel
        self._move_is_maneuver = True
        # Maître = self.sel ; autres = group_sel
        # IMPORTANT : on note les positions INITIALES (avant le déplacement)
        master = (oc, or_)
        others = sorted(self.group_sel)  # ordre déterministe
        self._move_maneuver_pieces = [master] + others
        # Le _move_start représente la pièce maître initiale (utile pour la notation)
        self._move_start = master

        pieces = {(c, r): self.board[c][r] for (c, r) in all_sel}
        # Collecte des glissements pour animation (toutes les pièces du groupe)
        maneuver_slides = [(dict(pieces[(c, r)]), (c, r), (c + dc, r + dr))
                           for (c, r) in all_sel]
        for (c, r) in all_sel:
            self.board[c][r] = None
        for (c, r), p in pieces.items():
            self.board[c + dc][r + dr] = p
        self.sel = (oc + dc, or_ + dr)
        self.group_sel = {(c + dc, r + dr) for (c, r) in self.group_sel}
        self._last_maneuver_slides = maneuver_slides
        return True

    def do_push(self, c, r, dc, dr):
        line, cc, rr = [], c, r
        while 0 <= cc < COLS and 0 <= rr < ROWS:
            p = self.board[cc][rr]
            if p is None: break
            if p["type"] == "Chevalier": return
            line.append((cc, rr, p))
            cc += dc; rr += dr
        # Collecte des glissements pour l'animation : chaque pièce de la ligne
        # glisse d'une case dans la direction (dc, dr). Les pièces éjectées
        # (poussées hors du plateau) glissent aussi vers l'extérieur.
        push_slides = []
        for cc, rr, p in line:
            nc, nr = cc + dc, rr + dr
            # On anime vers (nc,nr) même si hors plateau (effet d'éjection).
            push_slides.append((dict(p), (cc, rr), (nc, nr)))
        # Mémoriser tôt (avant d'éventuels return de fugue/mat)
        self._last_push_slides = push_slides
        for cc, rr, p in reversed(line):
            nc, nr = cc + dc, rr + dr
            self.board[cc][rr] = None
            if 0 <= nc < COLS and 0 <= nr < ROWS:
                self.board[nc][nr] = p
            else:
                # Fugue par poussée : l'Héritier est poussé dans SON ralliement
                # (côté adverse marqué à sa couleur).
                # Blanc fugue en row 8 (côté Noir), Noir fugue en row -1 (côté Blanc).
                if (p["type"] == "Héritier" and nc in RALLY and
                        ((p["camp"] == "Blanc" and nr == 8) or
                         (p["camp"] == "Noir"  and nr == -1))):
                    if p["camp"] == "Blanc": self._fugue_blanc((nc, nr))
                    else: self._fugue_noir((nc, nr))
                    return
                self.captured[p["camp"]].append(p)
                if p["type"] == "Héritier":
                    loser = p["camp"]
                    # EN LIGNE *ET* EN CORRESPONDANCE : ne pas terminer tout de
                    # suite, sinon le coup de poussée (qui éjecte l'Héritier) ne
                    # serait jamais transmis à l'adversaire. On marque le mat ;
                    # _end_turn enverra d'abord le coup (avec la méthode en corr),
                    # PUIS terminera la partie.
                    if (getattr(self, "online_mode", False)
                            or getattr(self, "corr_mode", False)) \
                            and not getattr(self, "_applying_remote", False):
                        self._mat_pending = loser
                        self._move_had_ejection = True
                    else:
                        self._end_game_by_color(loser_color=loser, method="mat")
                        return
                else:
                    # Pièce normale éjectée → on note qu'il y a eu éjection
                    # (le son sera joué après le son de déplacement, dans _record_move)
                    self._move_had_ejection = True

    def _build_move_notation(self, end_cell):
        """Construit la notation nmc du coup qui vient d'être joué."""
        start = self._move_start
        if start is None: return ""
        start_str = cell_to_notation(*start)

        # Cas fugue : la case d'arrivée n'est pas sur le plateau → utiliser *
        if end_cell is None or not (0 <= end_cell[0] < COLS and 0 <= end_cell[1] < ROWS):
            return f"{start_str}*"

        end_str = cell_to_notation(*end_cell)

        # Manœuvre : (maître) ou (maître+autres) -dest
        if self._move_is_maneuver:
            pieces_str = "".join(cell_to_notation(*c) for c in self._move_maneuver_pieces)
            return f"({pieces_str})-{end_str}"

        # Poussée : start-end> ou start-end>targets
        if self._move_is_push:
            base = f"{start_str}-{end_str}>"
            # Si toutes les directions disponibles ont été poussées → on n'écrit rien après >
            # Sinon on écrit les cases où on a poussé
            pushed = set(self._move_push_targets)
            all_dirs = set(self._move_pushable_dirs)
            if pushed == all_dirs and all_dirs:
                return base   # toutes poussées → rien après >
            # Sinon on écrit les cases poussées concaténées
            targets_str = "".join(cell_to_notation(*c) for c in self._move_push_targets
                                  if cell_to_notation(*c) is not None)
            return base + targets_str

        # Déplacement simple ou multisaut
        return f"{start_str}-{end_str}"

    def _maybe_ai_turn(self):
        """Si on joue contre l'IA et que c'est son tour, déclenche son coup."""
        if not self.vs_ai: return
        if self.replay_mode or self.analysis_mode: return
        if self._is_viewing(): return
        if self.turn != self.ai_camp: return
        # Lancer le calcul de l'IA après un court délai (pour laisser l'UI se rafraîchir)
        Clock.schedule_once(lambda dt: self._ai_play(), 0.4)

    def _ai_play(self):
        """deep grey calcule et joue son coup."""
        try:
            self._ai_play_inner()
        except Exception:
            import traceback, os
            try:
                base = os.path.dirname(os.path.abspath(__file__))
                with open(os.path.join(base, "fuga_error.txt"), "a") as f:
                    f.write("\n[ai_play] " + traceback.format_exc())
            except Exception:
                pass

    def _ai_play_inner(self):
        """Logique effective du coup de l'IA (voir _ai_play pour le wrap erreur)."""
        if not self.vs_ai or self.turn != self.ai_camp:
            return
        if self.replay_mode or self.analysis_mode or self._is_viewing():
            return
        board_copy = [[dict(p) if p else None for p in col] for col in self.board]
        ai_move_num = len(self.history) + 1
        # Vider le cache d'évaluation avant chaque réflexion (positions fraîches)
        _DG_EVAL_CACHE.clear()

        # ── B. Livre d'ouvertures ──
        # Si la position courante est connue dans le livre, on tente de jouer le
        # coup mémorisé (le plus souvent gagnant), SOUS garde-fou de sécurité :
        # on refuse un coup du livre qui donnerait la fugue à l'adversaire ou
        # éjecterait nos propres pièces sans gagner.
        move = None
        try:
            booked = dg_lookup_opening(board_copy, self.ai_camp, min_count=1)
            if booked:
                opp = "Noir" if self.ai_camp == "Blanc" else "Blanc"
                for mv in dg_generate_moves(board_copy, self.ai_camp):
                    if self._ai_notation(mv).strip().rstrip("#*") == booked:
                        # Garde-fou : ne pas jouer un coup catastrophique
                        danger = (mv.get("fugue_by") == opp
                                  or (mv.get("ej_ally", 0) > 0
                                      and not mv["fugue"]
                                      and mv.get("fugue_by") != self.ai_camp
                                      and mv["mat_on"] != opp))
                        if not danger:
                            move = mv
                        break
        except Exception:
            move = None

        if move is None:
            if getattr(self, "ai_deep_mode", False):
                # Mode profond : recherche en deux temps (top 5 à prof. 2 puis
                # prof. 3 sur ces 5), force d'une profondeur 3, bien plus rapide.
                move = dg_choose_move_topn(board_copy, self.ai_camp,
                                           seen_positions=self._ai_pos_counts,
                                           move_number=ai_move_num, top_n=5)
            else:
                move = dg_choose_move(board_copy, self.ai_camp, depth=2,
                                      seen_positions=self._ai_pos_counts,
                                      move_number=ai_move_num)
        if move is None:
            return

        # ── Anti allers-retours de groupe ──
        # Interdire une 3e manœuvre de groupe consécutive : si le coup choisi est
        # une manœuvre et que l'IA en a déjà fait 2 d'affilée, on choisit le
        # meilleur coup NON-manœuvre à la place.
        try:
            if (move.get("kind") == "maneuver"
                    and getattr(self, "_ai_consecutive_maneuvers", 0) >= 2):
                alt = None
                # Réévaluer les coups en excluant les manœuvres
                candidates = [m for m in dg_generate_moves(board_copy, self.ai_camp)
                              if m.get("kind") != "maneuver"]
                if candidates:
                    best_sc = None
                    for m in candidates:
                        sc = (dg_evaluate(m["board"], self.ai_camp)
                              + dg_move_bonus(m, board_copy, self.ai_camp))
                        if best_sc is None or sc > best_sc:
                            best_sc, alt = sc, m
                if alt is not None:
                    move = alt
        except Exception:
            pass

        # Mettre à jour le compteur de manœuvres consécutives
        if move.get("kind") == "maneuver":
            self._ai_consecutive_maneuvers = getattr(
                self, "_ai_consecutive_maneuvers", 0) + 1
        else:
            self._ai_consecutive_maneuvers = 0

        # Calculer les cases poussées AVANT d'appliquer le coup
        # (compute_push_targets compare self.board actuel et move["board"])
        ai_push_targets = self._ai_compute_push_targets(move)
        # Sauver l'ancien board pour calculer l'animation (différence avant/après)
        old_board = [[dict(p) if p else None for p in col] for col in self.board]
        # Appliquer le coup au plateau réel
        self.board = [[dict(p) if p else None for p in col] for col in move["board"]]
        self._ai_old_board = old_board

        # Enregistrer les pièces capturées par l'IA (l'IA applique directement
        # son board calculé sans passer par do_push, donc on détecte les
        # disparitions en comparant l'ancien et le nouveau plateau). On compte
        # les pièces présentes avant et absentes après, par camp, hors pièces
        # simplement déplacées (même set de pièces), on compare les totaux.
        try:
            def _count_by(board):
                d = {"Blanc": [], "Noir": []}
                for c in range(COLS):
                    for r in range(ROWS):
                        pc = board[c][r]
                        if pc:
                            d[pc["camp"]].append(pc["type"])
                return d
            before = _count_by(old_board)
            after = _count_by(self.board)
            for camp in ("Blanc", "Noir"):
                # Types disparus pour ce camp
                from collections import Counter
                diff = Counter(before[camp]) - Counter(after[camp])
                for ptype, n in diff.items():
                    # Ne pas compter le Chevalier (immortel) ni l'Héritier
                    # (géré par fugue/mat séparément)
                    if ptype in ("Chevalier",):
                        continue
                    for _ in range(n):
                        self.captured[camp].append({"type": ptype, "camp": camp})
        except Exception:
            pass

        # Construire la notation du coup (avec les push_targets pour notation précise)
        notation = self._ai_notation(move, push_targets=ai_push_targets)
        had_ejection = move["ejected"] > 0

        # Gérer fugue / mat / fin de partie
        if move["fugue"]:
            # Déterminer la case de ralliement où l'Héritier fugue
            frm = move.get("from")
            moved = move.get("moved_cells", [])
            dest = moved[0] if moved else frm
            rally_row = 8 if self.ai_camp == "Blanc" else -1
            rally_col = dest[0] if dest else (frm[0] if frm else 3)
            rally_cell = (rally_col, rally_row)
            # Animer le glissement de l'Héritier jusqu'au ralliement puis fuguer.
            # IMPORTANT (règle immuable) : la fugue DOIT se finaliser quoi qu'il
            # arrive, même si l'animation échoue (téléphone lent, contexte
            # graphique perdu...). On protège donc l'appel par un drapeau anti
            # double-exécution + un filet de sécurité via Clock.
            heir_piece = {"type": "Héritier", "camp": self.ai_camp}
            self._ai_fugue_done = False
            def _do_ai_fugue(*a):
                if getattr(self, "_ai_fugue_done", False):
                    return                      # déjà fait : ne pas refaire
                self._ai_fugue_done = True
                if self.ai_camp == "Blanc":
                    self._ai_finish_fugue_blanc(notation, rally_cell)
                else:
                    self._ai_finish_fugue_noir(notation, rally_cell)
            if frm is not None:
                try:
                    self.board_w.animate_slide(
                        [(heir_piece, frm, rally_cell)], on_done=_do_ai_fugue)
                except Exception:
                    _do_ai_fugue()
                # Filet de sécurité : si l'animation n'a pas rappelé le callback
                # (interruption, lenteur), on force la finalisation peu après.
                try:
                    Clock.schedule_once(_do_ai_fugue, 1.0)
                except Exception:
                    _do_ai_fugue()
            else:
                _do_ai_fugue()
            return
        if move["mat_on"] is not None:
            loser = move["mat_on"]
            self.turn = self.ai_camp
            self._record_move(notation, had_ejection=had_ejection,
                              push_targets=ai_push_targets)
            # Règle immuable : le mat DOIT terminer la partie, même si
            # l'animation échoue. Drapeau anti double-appel + filet Clock.
            self._ai_mat_done = False
            def _do_ai_mat(*a):
                if getattr(self, "_ai_mat_done", False):
                    return
                self._ai_mat_done = True
                self._end_game_by_color(loser_color=loser, method="mat")
            slides = self._ai_build_slides(move)
            if slides:
                try:
                    self.board_w.animate_slide(slides, on_done=_do_ai_mat)
                except Exception:
                    _do_ai_mat()
                try:
                    Clock.schedule_once(_do_ai_mat, 1.0)
                except Exception:
                    _do_ai_mat()
            else:
                _do_ai_mat()
            return

        # Cas du rattrapage : si Blanc humain a fugué et l'IA joue Noir,
        # ce coup est le coup de rattrapage.
        if self.blanc_fugued and self.turn == "Noir":
            self.turn = "Blanc"
            self._record_move(notation, had_ejection=had_ejection,
                              push_targets=ai_push_targets)
            self._end_game_by_color(loser_color="Noir", method="fugue")
            return

        # Coup normal : changer le tour puis enregistrer
        self.turn = "Noir" if self.turn == "Blanc" else "Blanc"
        self.sel = None; self.group_sel = set()
        self.moved = False; self.push_on = False; self.jumping = False
        self._record_move(notation, had_ejection=had_ejection,
                          push_targets=ai_push_targets)
        # Animation du coup de deep grey (cas simple : 1 pièce, pas de poussée)
        slides = self._ai_build_slides(move)
        def _after_ai():
            self._refresh_ui()
            if self._check_knight_stalemate():
                return
            # Papatte : si le joueur humain (au trait) n'a aucun coup légal
            if self._check_papatte():
                return
            # Reconstruire le bandeau APRÈS l'animation (état stable).
            self._do_update_history_ui()
        if slides:
            self.board_w.animate_slide(slides, on_done=_after_ai)
        else:
            _after_ai()

    def _build_slides_from_diff(self, old, new):
        """Calcule les glissements (piece, from, to) entre deux états de
        plateau, en appariant départs et arrivées (même type+camp, plus proche).
        Réutilisé pour l'IA, la navigation et (à venir) le mode en ligne."""
        try:
            departed = []
            arrived  = []
            for c in range(COLS):
                for r in range(ROWS):
                    o = old[c][r] if old else None
                    n = new[c][r] if new else None
                    o_id = (o.get("type"), o.get("camp")) if o else None
                    n_id = (n.get("type"), n.get("camp")) if n else None
                    if o is not None and o_id != n_id:
                        departed.append((c, r, o))
                    if n is not None and o_id != n_id:
                        arrived.append((c, r, n))
            if not departed or not arrived:
                return []
            slides = []
            used = set()
            for (ac, ar, ap) in arrived:
                best = None; best_d = None
                for i, (dc_, dr_, dp) in enumerate(departed):
                    if i in used: continue
                    if dp.get("type") == ap.get("type") and dp.get("camp") == ap.get("camp"):
                        dist = abs(dc_ - ac) + abs(dr_ - ar)
                        if best_d is None or dist < best_d:
                            best_d = dist; best = i
                if best is not None:
                    used.add(best)
                    dc_, dr_, dp = departed[best]
                    slides.append((dict(ap), (dc_, dr_), (ac, ar)))
            # Départs NON appariés = pièces éjectées (poussées hors du plateau).
            # On les fait glisser d'une case vers le bord le plus proche pour
            # qu'elles disparaissent 'derrière le bord' (effet d'éjection).
            # On déduit la direction depuis l'arrivée appariée la plus proche
            # (le pousseur), si possible ; sinon vers le bord le plus proche.
            for i, (dc_, dr_, dp) in enumerate(departed):
                if i in used:
                    continue
                # Chercher une pièce arrivée juste à côté (le pousseur potentiel)
                push_dir = None
                for (ac, ar, ap) in arrived:
                    if (ac, ar) == (dc_, dr_):
                        continue
                    ddx = dc_ - ac
                    ddy = dr_ - ar
                    if abs(ddx) <= 1 and abs(ddy) <= 1 and (ddx or ddy):
                        # le pousseur arrive vers la pièce éjectée → même direction
                        sx = (1 if ddx > 0 else (-1 if ddx < 0 else 0))
                        sy = (1 if ddy > 0 else (-1 if ddy < 0 else 0))
                        push_dir = (sx, sy)
                        break
                if push_dir is None:
                    # Bord le plus proche : on choisit la sortie la plus courte
                    left, right = dc_, (COLS - 1 - dc_)
                    bottom, top = dr_, (ROWS - 1 - dr_)
                    m = min(left, right, bottom, top)
                    if m == left:    push_dir = (-1, 0)
                    elif m == right: push_dir = (1, 0)
                    elif m == bottom:push_dir = (0, -1)
                    else:            push_dir = (0, 1)
                to = (dc_ + push_dir[0], dr_ + push_dir[1])
                slides.append((dict(dp), (dc_, dr_), to))
            return slides
        except Exception:
            return []

    def _ai_build_slides(self, move):
        """Glissements pour animer le coup de l'IA (différence avant/après)."""
        old = getattr(self, "_ai_old_board", None)
        if old is None:
            return []
        return self._build_slides_from_diff(old, self.board)

    def _ai_finish_fugue_blanc(self, notation, rally_cell=None):
        self.blanc_fugued = True
        if rally_cell is not None:
            self.fugued_heirs.append({"camp": "Blanc", "type": "Héritier",
                                      "col": rally_cell[0], "row": rally_cell[1]})
        self.turn = "Noir"
        self._record_move(notation)
        self._refresh_ui()
        # Après la fugue blanche, c'est au tour de Noir (rattrapage)
        self._maybe_ai_turn()

    def _ai_finish_fugue_noir(self, notation, rally_cell=None):
        if rally_cell is not None:
            self.fugued_heirs.append({"camp": "Noir", "type": "Héritier",
                                      "col": rally_cell[0], "row": rally_cell[1]})
        self.turn = "Blanc"
        self._record_move(notation)
        if self.blanc_fugued:
            self._end_game_by_color(loser_color=None, method="nulle")
        else:
            self._end_game_by_color(loser_color="Blanc", method="fugue")

    def _ai_notation(self, move, push_targets=None):
        """Construit la notation nmc d'un coup de l'IA.
        push_targets : si fourni, liste des cases (c,r) effectivement poussées."""
        frm = move["from"]
        start_str = cell_to_notation(*frm)
        kind = move["kind"]
        if move["fugue"]:
            return f"{start_str}*"
        if kind == "maneuver":
            # Notation : (Cell1Cell2Cell3)-DestMaitre où Cell1=maître
            from_cells = move.get("from_cells", [move["from"]])
            # Mettre 'from' (maître) en premier
            ordered = [move["from"]] + [c for c in from_cells if c != move["from"]]
            cells_str = "".join(cell_to_notation(c[0], c[1]) for c in ordered)
            # Destination du maître = move["moved_cells"][0] dans la convention IA
            # (le maître est en première position du groupe original donc en index 0)
            dest = move["moved_cells"][0]
            return f"({cells_str})-{cell_to_notation(*dest)}"
        # move, jump, square
        dest = move["moved_cells"][0]
        dest_str = cell_to_notation(*dest)
        base = f"{start_str}-{dest_str}"
        # Si poussée : ajouter > et la liste explicite des cases poussées
        if kind == "square" and push_targets:
            base += ">"
            # Lister les cases poussées (cases adjacentes à end dans les
            # directions de poussée où il y a eu déplacement)
            cells_str = "".join(cell_to_notation(c[0], c[1]) for c in push_targets
                                if 0 <= c[0] < COLS and 0 <= c[1] < ROWS
                                and cell_to_notation(c[0], c[1]) is not None)
            base += cells_str
        return base

    def _ai_compute_push_targets(self, move):
        """Détermine quelles cases ont été effectivement poussées par un coup
        carré IA. Utilise push_dirs_used si disponible, sinon fallback diff."""
        if move["kind"] != "square":
            return []
        # Méthode privilégiée : directions explicites stockées dans le move
        dirs_used = move.get("push_dirs_used")
        if dirs_used is not None:
            end_c, end_r = move["moved_cells"][0]
            targets = []
            for dc, dr in dirs_used:
                tc, tr = end_c + dc, end_r + dr
                if 0 <= tc < COLS and 0 <= tr < ROWS:
                    targets.append((tc, tr))
            return targets
        # Fallback : comparer board avant/après (méthode imprécise)
        board_before = self.board
        board_after = move["board"]
        end_c, end_r = move["moved_cells"][0]
        piece = board_before[move["from"][0]][move["from"][1]]
        if piece is None or piece["type"] not in ("Soldat", "Garde"):
            return []
        if piece["type"] == "Soldat":
            dirs = [(-1, -1), (1, -1), (-1, 1), (1, 1)]
        else:
            dirs = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        targets = []
        for dc, dr in dirs:
            tc, tr = end_c + dc, end_r + dr
            if not (0 <= tc < COLS and 0 <= tr < ROWS): continue
            before = board_before[tc][tr]
            if before is None: continue
            bc, br = tc + dc, tr + dr
            after = board_after[tc][tr]
            if after is None or after != before:
                if 0 <= bc < COLS and 0 <= br < ROWS:
                    if board_after[bc][br] == before:
                        targets.append((tc, tr))
                else:
                    targets.append((tc, tr))
        return targets

    def _ai_move_pushed(self, move):
        """Détermine si le coup carré a réellement poussé (pour la notation >)."""
        return move["ejected"] > 0 or move.get("total_pushed", 0) > 0

    def _end_turn(self):
        # Si une animation de glissement tourne encore, la terminer net
        # pour éviter tout conflit d'état avant de changer de tour.
        if hasattr(self, "board_w"):
            self.board_w._cancel_anim()
        # Calculer la notation du coup à partir de l'état actuel
        notation = None
        had_ejection = getattr(self, "_move_had_ejection", False)
        # Capturer les push_targets AVANT le reset_move_tracking
        captured_push_targets = list(getattr(self, "_move_push_targets", []) or [])
        if self._move_start is not None:
            end_cell = self.sel  # case d'arrivée
            notation = self._build_move_notation(end_cell)
            self._reset_move_tracking()

        if self.blanc_fugued and self.turn == "Noir":
            # Enregistrer le coup AVANT la fin de partie (avec le tour adverse comme suivant)
            if notation is not None:
                self.turn = "Blanc"   # le tour "suivant" hypothétique
                # En corr : ce coup CLÔT la partie (fugue) → l'envoyer AVEC la
                # méthode en une seule requête (anti double-envoi / anti-race).
                if getattr(self, "corr_mode", False):
                    self._corr_pending_method = "fugue"
                self._record_move(notation, had_ejection=had_ejection,
                                  push_targets=captured_push_targets)
            self._end_game_by_color(loser_color="Noir", method="fugue")
            return
        # Changer le tour AVANT d'enregistrer pour que le snapshot ait le bon turn
        self.turn      = "Noir" if self.turn == "Blanc" else "Blanc"
        self.sel       = None
        self.group_sel = set()
        self.moved     = False
        self.push_on   = False
        self.jumping   = False
        # EN CORRESPONDANCE : détecter MAINTENANT (avant l'envoi) si ce coup
        # termine la partie, pour l'envoyer AVEC la méthode en une seule requête
        # (corr_jouer enregistre le coup ET clôt la partie atomiquement). Cela
        # évite tout double-envoi et toute condition de course entre deux requêtes.
        if (getattr(self, "corr_mode", False) and notation is not None
                and not getattr(self, "_applying_remote", False)):
            if getattr(self, "_mat_pending", None) is not None:
                self._corr_pending_method = "mat"
            elif not self._player_has_any_move(self.turn):
                self._corr_pending_method = "papatte"
            elif not self._any_square_can_move():
                self._corr_pending_method = "nulle"   # Trêve
        if notation is not None:
            self._record_move(notation, had_ejection=had_ejection,
                              push_targets=captured_push_targets)
        # (L'envoi du coup en ligne est fait par _record_move ci-dessus, une seule
        # fois, surtout pas en double, sinon l'adversaire l'applique deux fois.)
        self._refresh_ui()
        # EN LIGNE : si un mat par poussée a été détecté pendant ce coup, on
        # termine MAINTENANT (après que le coup a été transmis à l'adversaire, qui
        # voit donc l'Héritier être poussé hors du plateau avant la fin).
        if getattr(self, "_mat_pending", None) is not None:
            loser = self._mat_pending
            self._mat_pending = None
            self._end_game_by_color(loser_color=loser, method="mat")
            return
        # Nulle par blocage (Trêve) : si plus aucune pièce carrée ne peut bouger
        if self._check_knight_stalemate():
            return
        # Papatte : si le joueur qui doit jouer maintenant n'a aucun coup légal
        if self._check_papatte():
            return
        # Si on joue contre l'IA et que c'est son tour, elle joue
        self._maybe_ai_turn()

    def _check_knight_stalemate(self):
        """Nulle par blocage : si PLUS AUCUNE pièce carrée (Soldat/Garde) ne peut
        bouger sur tout le plateau (toutes mortes, immobilisées, ou un mélange,
        dans les deux camps), la partie est nulle. En effet, sans carrée mobile,
        plus aucune poussée n'est possible et les rondes ne peuvent plus
        progresser vers la zone de ralliement : aucun camp ne peut gagner.
        Renvoie True si la nulle a été déclarée."""
        try:
            if self.replay_mode or self.analysis_mode:
                return False
            if self._any_square_can_move():
                return False
            # Aucune carrée ne peut bouger nulle part → nulle
            self._end_game_by_color(loser_color=None, method="nulle_pat")
            return True
        except Exception:
            return False

    def _any_square_can_move(self):
        """True s'il existe AU MOINS une pièce carrée (n'importe quel camp) qui
        n'est PAS immobilisée. On utilise exactement la même condition que le
        contour rouge affiché sur le plateau : une carrée est immobilisée si elle
        n'a aucune carrée adjacente (has_square_nbr est False). Donc tant qu'une
        carrée a un voisin carré (alliée ou adverse), elle peut bouger."""
        for c in range(COLS):
            for r in range(ROWS):
                p = self.board[c][r]
                if not self.is_square(p):
                    continue
                # Même test que le contour rouge : carrée NON immobilisée
                if self.has_square_nbr(c, r):
                    return True
        return False

    def _player_has_any_move(self, camp):
        """True si le joueur `camp` possède AU MOINS un coup légal. Sert à
        détecter la Papatte : si c'est à un joueur de jouer et qu'il n'a aucun
        coup possible (aucune pièce, Chevalier compris, ne peut bouger), il perd.
        - Ronde : doit toucher une autre ronde ET avoir une case d'arrivée libre
          (ou une case de fugue pour l'Héritier).
        - Carrée : doit toucher une autre carrée ET avoir une case libre autour.
        - Chevalier : peut bouger s'il a au moins une case vide adjacente."""
        for c in range(COLS):
            for r in range(ROWS):
                p = self.board[c][r]
                if not p or p["camp"] != camp:
                    continue
                typ = p["type"]
                if typ == "Chevalier":
                    # Le Chevalier bouge dans les 8 directions vers une case vide
                    for dc in (-1, 0, 1):
                        for dr in (-1, 0, 1):
                            if dc == dr == 0:
                                continue
                            nc, nr = c + dc, r + dr
                            if self._on_board(nc, nr) and self.board[nc][nr] is None:
                                return True
                elif self.is_round(p):
                    if not self.has_round_nbr(c, r):
                        continue  # ronde isolée : immobilisée
                    # Au moins une case d'arrivée valide (libre ou fugue)
                    for dc in (-1, 0, 1):
                        for dr in (-1, 0, 1):
                            if dc == dr == 0:
                                continue
                            nc, nr = c + dc, r + dr
                            if self._on_board(nc, nr) and self.board[nc][nr] is None:
                                return True
                            if self._is_rally_dest(nc, nr, p):
                                return True
                elif self.is_square(p):
                    if not self.has_square_nbr(c, r):
                        continue  # carrée isolée : immobilisée
                    # Au moins une case libre autour (déplacement 8 dirs)
                    for dc in (-1, 0, 1):
                        for dr in (-1, 0, 1):
                            if dc == dr == 0:
                                continue
                            nc, nr = c + dc, r + dr
                            if self._on_board(nc, nr) and self.board[nc][nr] is None:
                                return True
        return False

    def _check_papatte(self):
        """Papatte : si c'est au tour d'un joueur et qu'il n'a AUCUN coup légal,
        il perd et l'adversaire gagne 1 point (comme un mat). À vérifier au
        DÉBUT du tour du joueur concerné. Renvoie True si déclenchée."""
        try:
            if self.replay_mode or self.analysis_mode:
                return False
            if getattr(self, "_game_over", False):
                return False
            if self._player_has_any_move(self.turn):
                return False
            # Le joueur au trait ne peut rien jouer : il est papatte → il perd
            self._end_game_by_color(loser_color=self.turn, method="papatte")
            return True
        except Exception:
            return False

    def _is_knight_move(self, notation):
        """Vrai si la notation correspond à un déplacement de Chevalier.
        On identifie la pièce via la case de départ dans le snapshot précédent."""
        try:
            if not notation:
                return False
            n = notation.strip().rstrip("#").rstrip("*")
            # Manœuvre (groupe de carrés) → jamais un chevalier seul
            if n.startswith("("):
                return False
            if "-" not in n:
                return False
            start_str = n.split("-", 1)[0]
            start = notation_to_cell(start_str)
            if start is None:
                return False
            # Chercher la pièce de départ dans le snapshot AVANT ce coup.
            # On retrouve l'index du coup pour lire le board précédent.
            idx = None
            for i, (nota, _s) in enumerate(self.history):
                if nota is notation or nota == notation:
                    idx = i
                    break
            if idx is None:
                return False
            if idx == 0:
                prev_board = self._initial_state.get("board") if self._initial_state else None
            else:
                prev_board = self.history[idx - 1][1].get("board")
            if prev_board is None:
                return False
            p = prev_board[start[0]][start[1]]
            return p is not None and p.get("type") == "Chevalier"
        except Exception:
            return False

    def _fugue_blanc(self, rally_cell=None):
        # Calculer notation puis changer le tour AVANT d'enregistrer
        notation = None
        captured_push_targets = list(getattr(self, "_move_push_targets", []) or [])
        if self._move_start is not None:
            notation = self._build_move_notation(None)   # None = fugue
            self._reset_move_tracking()
        self.blanc_fugued = True
        # Mémoriser l'Héritier fugué pour l'afficher en permanence dans le ralliement
        if rally_cell is not None:
            self.fugued_heirs.append({"camp": "Blanc", "type": "Héritier",
                                      "col": rally_cell[0], "row": rally_cell[1]})
        self.sel       = None
        self.group_sel = set()
        self.moved     = False
        self.push_on   = False
        self.jumping   = False
        self.turn      = "Noir"
        if notation is not None:
            self._record_move(notation, push_targets=captured_push_targets)
        self._refresh_ui()
        self._maybe_ai_turn()

    def _fugue_noir(self, rally_cell=None):
        # Calculer notation puis changer le tour AVANT d'enregistrer
        notation = None
        captured_push_targets = list(getattr(self, "_move_push_targets", []) or [])
        if self._move_start is not None:
            notation = self._build_move_notation(None)
            self._reset_move_tracking()
        # Mémoriser l'Héritier fugué
        if rally_cell is not None:
            self.fugued_heirs.append({"camp": "Noir", "type": "Héritier",
                                      "col": rally_cell[0], "row": rally_cell[1]})
        # Le tour bascule à Blanc pour le snapshot (fin de partie)
        self.turn = "Blanc"
        if notation is not None:
            self._record_move(notation, push_targets=captured_push_targets)
        if self.blanc_fugued:
            self._end_game_by_color(loser_color=None, method="nulle")
        else:
            self._end_game_by_color(loser_color="Blanc", method="fugue")

    def _toggle_draw_offer(self, which):
        """Proposition de nulle.
        - En LOCAL : chaque joueur a son bouton ½ ; si les deux sont actifs,
          nulle par accord mutuel.
        - EN LIGNE : le bouton envoie une proposition à l'adversaire (popup
          chez lui). On n'utilise que le bouton du joueur local.
        En replay/analyse : sans effet."""
        if self.replay_mode or self.analysis_mode:
            return
        # ── Mode correspondance ──
        if getattr(self, "corr_mode", False):
            if not self.corr_game_id:
                return
            if hasattr(self, "bot_draw"):
                self.bot_draw.set_bg(COL_ORANGE)
            def _done(ok, err):
                if ok:
                    self._popup_simple(
                        "Nulle proposée",
                        "Proposition de nulle envoyée.\nVotre adversaire la verra "
                        "en ouvrant la partie.")
                else:
                    self._popup_simple("Nulle", err or "Échec de la proposition.")
            try:
                ONLINE.corr_proposer_nulle(self.corr_game_id, _done)
            except Exception:
                pass
            return
        # ── Mode en ligne ──
        if self.online_mode:
            # On ne propose que pour soi-même (le bouton de son côté)
            ONLINE.sio_emit("proposer_nulle", {"game_id": self.online_game_id})
            # Éclairer brièvement le bouton du joueur local pour feedback
            btn = self.bot_draw if not self.flipped else self.bot_draw
            if hasattr(self, "bot_draw"):
                self.bot_draw.set_bg(COL_ORANGE)
            Popup(title="Nulle proposée",
                  content=Label(text="Proposition de nulle envoyée\nà votre adversaire.",
                                color=(1, 1, 1, 1), halign="center"),
                  size_hint=(0.75, 0.3)).open()
            return
        # ── Mode local ──
        # Quel camp correspond à ce bouton (selon l'orientation du plateau) ?
        if which == "top":
            camp = "Noir" if self.flipped else "Blanc"
            btn = self.top_draw
        else:
            camp = "Blanc" if self.flipped else "Noir"
            btn = self.bot_draw
        # Bascule l'état de la proposition de ce camp
        self._draw_offers[camp] = not self._draw_offers.get(camp, False)
        # Met à jour la couleur du bouton (éclairé = orange, sinon gris)
        btn.set_bg(COL_ORANGE if self._draw_offers[camp] else COL_BTN_GREY)
        # Si les deux camps ont proposé → nulle par accord mutuel
        if self._draw_offers.get("Blanc") and self._draw_offers.get("Noir"):
            self._draw_offers = {"Blanc": False, "Noir": False}
            self._end_game_by_color(loser_color=None, method="nulle_accord")

    def _reset_draw_offers(self):
        """Réinitialise les propositions de nulle (à chaque coup joué)."""
        self._draw_offers = {"Blanc": False, "Noir": False}
        if hasattr(self, "top_draw"):
            self.top_draw.set_bg(COL_BTN_GREY)
        if hasattr(self, "bot_draw"):
            self.bot_draw.set_bg(COL_BTN_GREY)

    def _end_game_by_color(self, loser_color, method):
        # En mode analyse : pas de fin de partie, on continue
        if self.analysis_mode:
            # On bascule juste de tour (sauf si fugue blanc qui doit donner un coup à noir)
            return
        # Éviter une double fin (ex : signal réseau + détection locale)
        if getattr(self, "_game_over", False):
            return
        self._game_over = True
        # En ligne : prévenir le serveur de la fin de partie, SAUF si cette fin
        # découle d'un coup qu'on vient de recevoir (l'adversaire le sait déjà).
        if self.online_mode and not getattr(self, "_applying_remote", False):
            try:
                ONLINE.sio_emit("fin_partie", {
                    "game_id": self.online_game_id,
                    "methode": method,
                    "loser_color": loser_color,  # None = nulle
                })
            except Exception:
                pass
        # En correspondance : la fin est gérée AUTREMENT selon le cas.
        #  - abandon : route dédiée (le joueur PERD, l'adversaire gagne).
        #  - mat / fugue / papatte / Trêve : le coup final a DÉJÀ été envoyé AVEC
        #    sa méthode par _record_move (corr_jouer enregistre le coup ET clôt la
        #    partie en une seule requête). Il ne faut donc RIEN renvoyer ici, sinon
        #    on compterait les points en double / on dupliquerait le coup.
        if (getattr(self, "corr_mode", False)
                and not getattr(self, "_applying_remote", False)):
            if method == "abandon":
                try:
                    ONLINE.corr_abandon(self.corr_game_id)
                except Exception:
                    pass
        if self._timer_evt:
            self._timer_evt.cancel()
            self._timer_evt = None

        # Ajouter le suffixe de fin (# = mat, * = temps/abandon) au DERNIER coup
        # de l'historique, pour qu'il apparaisse aussi dans le bandeau (pas
        # seulement dans le fichier .nmc). La fugue se termine déjà par *.
        if method not in ("nulle", "nulle_accord", "nulle_pat") and self.history:
            last_notation, last_snap = self.history[-1]
            if method == "mat" and not last_notation.endswith("#"):
                self.history[-1] = (last_notation + "#", last_snap)
            elif method in ("temps", "abandon") and not last_notation.endswith("*") \
                    and not last_notation.endswith("#"):
                self.history[-1] = (last_notation + "*", last_snap)
            self._update_history_ui()

        if method in ("nulle", "nulle_accord", "nulle_pat"):
            winner_player = None
            title = "Partie nulle"
            if method == "nulle_accord":
                body = "Nulle par accord mutuel.\nAucun point accordé."
            elif method == "nulle_pat":
                body = ("Trêve : plus aucune pièce carrée ne peut bouger.\n"
                        "Aucun point accordé.")
            else:
                body = "Les deux Héritiers ont fugué.\nAucun point accordé."
            pts = 0
            # Pour la sauvegarde .nmc, on uniformise la méthode à "nulle"
            method = "nulle"
        else:
            winner_color  = "Blanc" if loser_color == "Noir" else "Noir"
            winner_player = self._player_of(winner_color)
            # Mat = 1 pt ; papatte (le joueur ne peut plus jouer) = 1 pt ;
            # fugue, temps écoulé, abandon = 2 pts
            pts = 1 if method in ("mat", "papatte") else 2
            # En ligne, c'est le SERVEUR qui tient le score du match (et le
            # renvoie via match_continue/match_over). On n'incrémente donc PAS
            # localement, pour éviter tout double comptage.
            if not getattr(self, "online_mode", False):
                self.scores[winner_player] += pts
            verbe = {"fugue":  "fugue",
                     "mat":    "mat",
                     "temps":  "temps écoulé",
                     "abandon": "abandon",
                     "papatte": "papatte (adversaire bloqué)"}[method]
            title = f"{winner_player} gagne la partie"
            players = self._players()
            pA, pB = players[0], players[1]
            body  = (f"Victoire par {verbe} (+{pts} pt{'s' if pts > 1 else ''})\n\n"
                     f"{pA} : {self.scores[pA]}    "
                     f"{pB} : {self.scores[pB]}")

        # ── Apprentissage des ouvertures ──
        # Si on joue contre l'IA et que l'IA a PERDU, on enregistre les coups
        # du gagnant (l'humain) dans le livre d'ouvertures : l'IA apprend.
        try:
            wc = locals().get("winner_color")
            if (getattr(self, "vs_ai", False) and winner_player is not None
                    and wc in ("Blanc", "Noir")):
                ai_won = (winner_player == getattr(self, "ai_player", "deep grey"))
                if not ai_won:
                    init_board = None
                    if getattr(self, "_initial_state", None):
                        init_board = self._initial_state.get("board")
                    dg_record_winning_line(self.history, wc,
                                           initial_board=init_board,
                                           first_player_color="Blanc")
        except Exception:
            pass

        # ── Apprentissage des VALEURS (poids) ──
        # Après chaque partie vs IA, l'IA affine légèrement ses poids selon le
        # résultat (auto-ajustement borné : ±3%/partie, ±40% max). Elle apprend
        # de la position finale, qu'elle ait gagné ou perdu.
        try:
            wc = locals().get("winner_color")
            if (getattr(self, "vs_ai", False) and wc in ("Blanc", "Noir")):
                loser_c = "Noir" if wc == "Blanc" else "Blanc"
                dg_learn_weights(wc, loser_c, self.board)
        except Exception:
            pass

        # Sauvegarder la partie en .nmc
        self._save_game(winner_player, method, pts)

        self._decide_next(title, body, winner_player)

    def _save_game(self, winner_player, method, pts):
        """Sauvegarde la partie en cours dans un fichier .nmc."""
        if self.replay_mode: return   # Pas de sauvegarde en mode lecture
        try:
            # Préparer la chaîne de coups avec suffixe de fin (# = mat 1pt, * = fugue/temps/abandon 2pts)
            history = list(self.history)
            if method != "nulle" and history:
                # Ajouter un suffixe au dernier coup pour indiquer le mode de fin
                # # = mat (1pt), * = fugue/temps/abandon (2pts)
                # Mais pour fugue, le coup se termine déjà par * (Mi7*)
                # Donc on n'ajoute le suffixe que si pas déjà présent
                last_notation, last_snap = history[-1]
                if method == "mat":
                    if not last_notation.endswith("#"):
                        history[-1] = (last_notation + "#", last_snap)
                elif method == "fugue":
                    # Le coup se termine déjà par *, rien à faire
                    pass
                elif method in ("temps", "abandon"):
                    if not last_notation.endswith("*"):
                        history[-1] = (last_notation + "*", last_snap)

            # Result : 1-0 si le 1er joueur gagne, 0-1 si le 2e, ½-½ si nulle.
            # player1/player2 = ordre des joueurs (point de vue pour l'affichage
            # gagné/perdu dans l'historique). On stocke EN PLUS qui a les Blancs
            # ("blanc") pour que le replay oriente correctement le plateau et les
            # noms, sans confondre avec le point de vue.
            players = self._players()
            pA, pB = players[0], players[1]
            if winner_player is None:
                result = "½-½"
            elif winner_player == pA:
                result = "1-0"
            else:
                result = "0-1"

            meta = {
                "date": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                "player1": pA,
                "player2": pB,
                "blanc": self.first_player_blanc,
                "objectif": str(self.target),
                "cadence": str(self.cadence),
                "result": result,
                "method": method,
                "points": str(pts),
                # Random Fuga : code de la position de départ (None si standard)
                "random": getattr(self, "current_random_code", None),
            }
            content = make_nmc_content(meta, history)
            # CLASSEMENT : une partie EN LIGNE va uniquement dans l'historique en
            # ligne (serveur) ; une partie LOCALE (2 joueurs ou vs IA) va
            # uniquement dans l'historique local (fichier .nmc).
            if self.online_mode and ONLINE.is_logged_in():
                game_uid = self._make_game_uid(meta, content)
                ONLINE.save_game_to_account({
                    "game_uid": game_uid,
                    "nmc_text": content,
                    "joueur1": meta["player1"],
                    "joueur2": meta["player2"],
                    "resultat": result,
                    "methode": method,
                    "cadence": str(self.cadence),
                    "objectif": str(self.target),
                })
            else:
                # Partie locale / vs IA : fichier .nmc local
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{timestamp}.nmc"
                filepath = os.path.join(get_parties_dir(), filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
        except Exception as e:
            # En cas d'erreur, on n'interrompt pas le jeu
            print(f"Erreur sauvegarde partie: {e}")

    def _make_game_uid(self, meta, content):
        """Génère un identifiant unique de partie. En ligne, on réutilise le
        game_id du serveur (pour que les 2 joueurs aient le MÊME uid et que ce
        soit bien la même partie des deux côtés). Sinon, basé sur date+contenu."""
        if self.online_mode and self.online_game_id:
            return "online_%s" % self.online_game_id
        import hashlib as _hl
        h = _hl.sha1((meta["date"] + content[:200]).encode("utf-8")).hexdigest()[:16]
        return "local_%s" % h

    # ── Chargement d'une partie en mode lecture ──────────────────────────────

    def load_replay(self, meta, moves_text):
        """Charge une partie en mode lecture pure (pas de jeu possible).
        meta : dict des en-têtes ; moves_text : chaîne des coups concaténés.
        Renvoie True si la lecture est possible, False si le nmc est invalide."""
        if not moves_text:
            moves_text = ""
        try:
            moves = self._parse_moves_text(moves_text)
        except Exception:
            return False
        if moves is None:
            return False

        # Activer le mode replay : pas de timer, pas d'abandon, pas de sauvegarde
        self.replay_mode = True
        # Mémoriser l'écran d'origine (pour y revenir au lieu de toujours local)
        try:
            cur = self.manager.current if self.manager else "history_local"
            if cur in ("history_local", "history_online"):
                self._replay_origin = cur
        except Exception:
            pass

        # Réinitialiser comme une nouvelle partie
        if self._timer_evt:
            self._timer_evt.cancel()
            self._timer_evt = None
        try:
            self.target = int(meta.get("objectif", 5))
        except (ValueError, TypeError):
            self.target = meta.get("objectif", 5)
        cadence_str = meta.get("cadence", "15")
        if cadence_str == "zen":
            self.cadence = "zen"
        else:
            try:
                self.cadence = int(cadence_str)
            except ValueError:
                self.cadence = 15
        # Utiliser les noms de joueurs stockés dans le .nmc
        player1 = meta.get("joueur1", "Joueur 1")
        player2 = meta.get("joueur2", "Joueur 2")
        self.scores = {player1: 0, player2: 0}
        self.played_blanc = {player1: 0, player2: 0}
        self.flash_round = 0
        self.flash_phase = 1
        self.last_chance = False
        # Qui a les Blancs : champ "blanc" si présent, sinon repli sur player1
        # (anciennes parties sauvegardées avant l'ajout de ce champ).
        blanc_player = meta.get("blanc", player1)
        if blanc_player not in (player1, player2):
            blanc_player = player1
        self.first_player_blanc = blanc_player
        self.played_blanc[blanc_player] += 1
        self.turn = "Blanc"
        self.sel = None
        self.group_sel = set()
        self.moved = False
        self.push_on = False
        self.jumping = False
        self.board = [[None] * ROWS for _ in range(COLS)]
        self.captured = {"Blanc": [], "Noir": []}
        self.blanc_fugued = False
        self.fugued_heirs = []
        self.history = []
        self.viewing_idx = None
        self._reset_move_tracking()
        if self.cadence == "zen":
            self.time_left = {"Blanc": None, "Noir": None}
        else:
            cad = self.cadence if isinstance(self.cadence, int) else 15
            self.time_left = {k: cad * 60 for k in ("Blanc", "Noir")}
        # Random Fuga : si la partie est partie d'une position aléatoire (en-tête
        # [Random "..."]), reconstruire CETTE position au lieu de la standard,
        # sinon les coups seraient rejoués sur un mauvais plateau.
        rcode = meta.get("random")
        rboard = rf_build_board(rcode) if rcode else None
        if rboard is not None:
            self.board = rboard
            self.current_random_code = rcode
        else:
            self._setup_pieces()
            self.current_random_code = None
        self._initial_state = self._snapshot()
        self._paused = True   # bloque tout, mais on est en mode lecture de toute façon

        # Rejouer chaque coup pour reconstituer les snapshots
        for notation in moves:
            ok = self._apply_notation(notation)
            if not ok:
                # Partie invalide → on annule tout
                self.history = []
                return False

        # On bascule en mode lecture
        if self.history:
            self.viewing_idx = 0
            self._restore_snapshot(self.history[0][1])
        else:
            # Partie sans coup : on reste sur l'état initial mais en mode lecture
            self.viewing_idx = -1   # avant le premier coup
        self._refresh_ui()
        self._update_history_ui()
        self._update_action_buttons()
        return True

    def _parse_moves_text(self, text):
        """Parse '1.X/Y  2.X/Y ...' en liste de notations [X, Y, X, Y, ...]."""
        moves = []
        # Découper par les numéros de tour : on cherche tous les motifs "N.contenu"
        # Le contenu va jusqu'au prochain " N." ou la fin
        tokens = re.split(r'\s+', text.strip())
        for token in tokens:
            if not token: continue
            # Retirer le préfixe "N." si présent
            m = re.match(r'^(\d+)\.(.*)$', token)
            if m:
                rest = m.group(2)
            else:
                rest = token
            # Séparer par "/"
            if "/" in rest:
                blanc, noir = rest.split("/", 1)
            else:
                blanc, noir = rest, ""
            if blanc:
                moves.append(blanc)
            if noir:
                moves.append(noir)
        return moves

    def _apply_notation(self, notation):
        """Applique une notation de coup au plateau courant. Renvoie True si OK.
        Cette méthode RECONSTRUIT l'état après le coup et enregistre le snapshot."""
        # Retirer suffixe de fin de partie # ou final *
        suffix = ""
        notation = notation.strip()
        if not notation: return False
        ends_with_hash = notation.endswith("#")
        ends_with_fugue = notation.endswith("*")
        # Cas spécial : la notation peut se finir par "X#" (mat) ou "X*" (fugue/temps/abandon)
        # On parse normalement, le suffixe est juste indicatif
        clean = notation
        if ends_with_hash:
            clean = clean[:-1]
        # Le * peut être fugue (case d'arrivée non nommable) OU suffixe de fin
        # Distinguer : si le coup contient "-" et finit par "*", c'est fugue sur case nommable + suffixe
        # Si le coup finit par "*" sans "-X*", c'est une fugue sur case non nommable

        # Manœuvre : commence par "("
        if clean.startswith("("):
            return self._apply_maneuver(clean)
        # Sinon : déplacement / saut / poussée / fugue
        return self._apply_simple_or_push(clean)

    def _apply_simple_or_push(self, s):
        """Applique 'Do1-Do2', 'Do1-Do2>', 'Do1-Do2>Re7Do6', 'Mi7*'."""
        # Cas fugue (case d'arrivée non nommable) : "Start*"
        if "*" in s and "-" not in s:
            start_str = s.replace("*", "").strip()
            start = notation_to_cell(start_str)
            if start is None: return False
            # Joue le coup : la pièce sort par sa zone de ralliement
            piece = self.board[start[0]][start[1]]
            if piece is None: return False
            self.board[start[0]][start[1]] = None
            # Enregistrer l'Héritier fugué pour l'afficher dans le ralliement
            if piece.get("type") == "Héritier":
                rally_row = 8 if piece["camp"] == "Blanc" else -1
                self.fugued_heirs.append({"camp": piece["camp"], "type": "Héritier",
                                          "col": start[0], "row": rally_row})
            # Bascule de tour
            self._end_replay_turn(start_str + "*", was_fugue=True)
            return True

        # Sépare la partie déplacement de la partie poussée
        push_part = ""
        if ">" in s:
            move_part, push_part = s.split(">", 1)
        else:
            move_part = s

        # move_part = "Start-End" ou "Start-End*" (fugue avec case nommable, rare)
        if "-" not in move_part: return False
        start_str, end_str = move_part.split("-", 1)
        # end_str peut contenir * en fin pour fugue
        ends_fugue = end_str.endswith("*")
        if ends_fugue:
            end_str = end_str[:-1]

        start = notation_to_cell(start_str)
        end = notation_to_cell(end_str)
        if start is None: return False

        piece = self.board[start[0]][start[1]]
        if piece is None: return False

        # Effectuer le déplacement
        self.board[start[0]][start[1]] = None
        if end is not None:
            self.board[end[0]][end[1]] = piece

        # Appliquer les poussées
        notation_full = s
        if ">" in s and end is not None:
            # Si push_part vide → toutes les directions sont poussées
            # Sinon push_part = "Re7Do6" → cases à pousser
            ptype = piece["type"]
            if push_part.strip() == "":
                # Pousser toutes les directions possibles
                push_dirs = self._compute_pushable_dirs(end[0], end[1], ptype)
                for (pc, pr) in push_dirs:
                    dc = pc - end[0]
                    dr = pr - end[1]
                    self.do_push(pc, pr, dc, dr)
            else:
                cells = parse_cells_concat(push_part)
                if cells is None: return False
                for (pc, pr) in cells:
                    dc = pc - end[0]
                    dr = pr - end[1]
                    self.do_push(pc, pr, dc, dr)

        self._end_replay_turn(notation_full, was_fugue=ends_fugue)
        return True

    def _apply_maneuver(self, s):
        """Applique '(Do1)-Re2' ou '(Do8Mi8)-Do7'."""
        m = re.match(r'^\((.*)\)-(.+)$', s)
        if not m: return False
        pieces_str = m.group(1)
        dest_str = m.group(2)
        # Le dest peut finir par # (mat sur destination, rare)
        if dest_str.endswith("#"):
            dest_str = dest_str[:-1]
        cells = parse_cells_concat(pieces_str)
        if cells is None or not cells: return False
        dest = notation_to_cell(dest_str)
        if dest is None: return False
        master = cells[0]
        # Si une seule case : c'est le groupe entier → on doit récupérer tout le groupe
        if len(cells) == 1:
            group = self._group_of(master[0], master[1])
            if not group: return False
            cells = [master] + sorted(group - {master})
        # Calculer le delta
        dc = dest[0] - master[0]
        dr = dest[1] - master[1]
        # Déplacer toutes les pièces
        pieces_data = {(c, r): self.board[c][r] for (c, r) in cells}
        for (c, r) in cells:
            self.board[c][r] = None
        for (c, r), p in pieces_data.items():
            if p is None: return False
            nc, nr = c + dc, r + dr
            if not (0 <= nc < COLS and 0 <= nr < ROWS): return False
            self.board[nc][nr] = p
        self._end_replay_turn(s, was_fugue=False)
        return True

    def _end_replay_turn(self, notation, was_fugue):
        """Bascule de tour et enregistre le coup dans l'historique pendant un replay."""
        # Mettre à jour blanc_fugued si fugue
        if was_fugue and self.turn == "Blanc":
            self.blanc_fugued = True
        # Bascule de tour
        self.turn = "Noir" if self.turn == "Blanc" else "Blanc"
        # Enregistrer snapshot
        snapshot = self._snapshot()
        self.history.append((notation, snapshot))

    def _decide_next(self, title, body, winner_player):
        players = self._players()
        pA, pB = players[0], players[1]

        # Correspondance UNIQUEMENT : toujours une partie unique (jamais de
        # "partie suivante"). Les parties en direct (matchmaking/défi) respectent
        # l'objectif choisi et peuvent donc enchaîner plusieurs points, exactement
        # comme en local.
        if getattr(self, "corr_mode", False):
            self._popup_finish(title, body, winner_player=winner_player)
            return

        # EN LIGNE : c'est le SERVEUR qui est l'arbitre du match (il connaît le
        # score, gère l'alternance des couleurs et la règle de la dernière
        # chance). Le client n'enchaîne donc RIEN tout seul : il mémorise le
        # résultat de cette partie et attend l'événement du serveur
        # (match_continue → popup "Partie suivante", ou match_over → popup final).
        if getattr(self, "online_mode", False):
            self._pending_finish = (title, body, winner_player)
            return

        # Mode "Partie" : on s'arrête après une seule partie
        if self.target == "partie":
            self._popup_finish(title, body, winner_player=winner_player)
            return

        if self.target == "flash":
            if self.flash_round < 2:
                self.flash_round += 1
                self._popup_continue(title, body,
                                     next_first_blanc=self._other_player(self.first_player_blanc))
                return
            sA, sB = self.scores[pA], self.scores[pB]
            if sA != sB:
                self._popup_finish(title, body, winner_player=(pA if sA > sB else pB))
                return
            if self.flash_phase < 2:
                self.flash_phase += 1
                self.flash_round  = 1
                next_first = self._other_player(self._first_blanc_of_round1())
                self._popup_continue(title + "  (égalité)", body, next_first_blanc=next_first)
                return
            self._popup_finish(title, body, winner_player=None)
            return

        cible = self.target
        sA, sB = self.scores[pA], self.scores[pB]
        leader  = pA if sA > sB else (pB if sB > sA else None)
        reached = (leader is not None and self.scores[leader] >= cible)

        if not reached:
            self._popup_continue(title, body,
                                 next_first_blanc=self._other_player(self.first_player_blanc))
            return

        if self.last_chance:
            if sA == sB:
                self._popup_finish("Match nul !",
                                   f"{pA} : {sA}   {pB} : {sB}",
                                   winner_player=None)
            else:
                self._popup_finish(title, body, winner_player=leader)
            return

        loser = self._other_player(leader)
        b_lead = self.played_blanc[leader]
        b_lose = self.played_blanc[loser]
        if b_lead > b_lose:
            self.last_chance = True
            self._popup_continue(title + f"  •  Ultime partie pour {loser}",
                                 body, next_first_blanc=loser)
            return

        self._popup_finish(title, body, winner_player=leader)

    def _first_blanc_of_round1(self):
        players = self._players()
        pA, pB = players[0], players[1]
        return pA if self.played_blanc[pA] >= self.played_blanc[pB] else pB

    def _popup_continue(self, title, body, next_first_blanc):
        # EN LIGNE : le bouton "Partie suivante" ne relance pas localement. Il
        # signale au serveur qu'on est prêt (pret_partie_suivante). Quand LES DEUX
        # sont prêts, le serveur renvoie 'partie_trouvee' (couleurs alternées) qui
        # démarre la partie suivante via _on_partie_trouvee. Un compte à rebours
        # d'1 min s'affiche : si l'adversaire ne clique pas à temps, il abandonne
        # le match (géré par le serveur).
        if getattr(self, "online_mode", False):
            self._popup_continue_online(title, body)
            return
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(Label(text=body, font_size=SF("14sp"), color=(1, 1, 1, 1)))
        info = Label(text=f"Prochaine partie : {next_first_blanc} joue Blanc",
                     font_size=SF("12sp"), italic=True,
                     color=(0.8, 0.8, 0.8, 1),
                     size_hint=(1, None), height=S(24))
        content.add_widget(info)
        btn = RoundButton(text="Partie suivante", bg_color=COL_ORANGE,
                          color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                          size_hint=(1, None), height=S(50))
        content.add_widget(btn)
        popup = Popup(title=title, content=content,
                      size_hint=(0.85, 0.55), auto_dismiss=False)
        btn.bind(on_release=lambda *a: (popup.dismiss(),
                                        self._start_next_game(next_first_blanc)))
        popup.open()

    def _popup_continue_online(self, title, body):
        """Popup 'Partie suivante' en ligne : on signale au serveur qu'on est
        prêt, puis on attend que l'adversaire le soit aussi. Compte à rebours d'1
        minute pour l'adversaire (sinon il perd le match, sans coût de Mélo)."""
        content = BoxLayout(orientation="vertical", spacing=S(10), padding=S(12))
        content.add_widget(Label(text=body, font_size=SF("14sp"),
                                 color=(1, 1, 1, 1)))
        self._next_status_lbl = Label(
            text="Clique sur « Partie suivante » pour continuer le match.",
            font_size=SF("12sp"), italic=True, color=(0.85, 0.85, 0.85, 1),
            size_hint=(1, None), height=S(40), halign="center")
        self._next_status_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(self._next_status_lbl)
        btn = RoundButton(text="Partie suivante", bg_color=COL_ORANGE,
                          color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                          size_hint=(1, None), height=S(50))
        content.add_widget(btn)
        quit_btn = RoundButton(text="Quitter le match", bg_color=COL_BTN_GREY,
                               color=(1, 1, 1, 1), font_size=SF("12sp"),
                               size_hint=(1, None), height=S(40))
        content.add_widget(quit_btn)
        popup = Popup(title=title, content=content, size_hint=(0.85, 0.6),
                      auto_dismiss=False)
        self._next_popup = popup
        self._next_ready_sent = False

        def _ready(*a):
            if self._next_ready_sent:
                return
            self._next_ready_sent = True
            btn.text = "En attente de l'adversaire…"
            btn.disabled = True
            try:
                ONLINE.sio_emit("pret_partie_suivante",
                                {"game_id": self.online_game_id})
            except Exception:
                pass
            # Démarrer un compte à rebours d'1 min (affichage informatif côté
            # joueur prêt : c'est l'adversaire qui risque l'abandon).
            self._next_remaining = 60
            self._next_status_lbl.text = ("En attente de l'adversaire…  (%ds)"
                                          % self._next_remaining)
            if getattr(self, "_next_timer", None):
                try: self._next_timer.cancel()
                except Exception: pass
            self._next_timer = Clock.schedule_interval(self._next_tick, 1)
        btn.bind(on_release=_ready)

        def _quit(*a):
            self._cancel_next_timer()
            try: popup.dismiss()
            except Exception: pass
            # Quitter le match = abandon du match côté serveur
            try:
                ONLINE.sio_emit("abandonner_match",
                                {"game_id": self.online_game_id})
            except Exception:
                pass
            self._leave_online_to_menu()
        quit_btn.bind(on_release=_quit)
        popup.open()

    def _next_tick(self, dt):
        """Compte à rebours d'1 min pour la partie suivante (informatif)."""
        self._next_remaining -= 1
        if getattr(self, "_next_status_lbl", None):
            try:
                if self._next_remaining > 0:
                    self._next_status_lbl.text = ("En attente de l'adversaire…  (%ds)"
                                                  % self._next_remaining)
                else:
                    self._next_status_lbl.text = "Temps écoulé…"
            except Exception:
                pass
        if self._next_remaining <= 0:
            self._cancel_next_timer()

    def _cancel_next_timer(self):
        if getattr(self, "_next_timer", None):
            try: self._next_timer.cancel()
            except Exception: pass
            self._next_timer = None

    def _leave_online_to_menu(self):
        """Quitte proprement une partie/un match en ligne et revient au menu."""
        self._cancel_next_timer()
        self.online_mode = False
        self.online_game_id = None
        try:
            self.manager.current = "menu"
        except Exception:
            pass

    def _start_next_game(self, next_first_blanc):
        """Démarre la partie suivante d'un match, en recalculant le camp de l'IA."""
        # Random Fuga : nouvelle position aléatoire pour chaque partie du match
        # (local / contre l'IA ; le online suit son propre chemin en phase 2).
        if RANDOM_MODE and not getattr(self, "online_mode", False) \
                and not getattr(self, "corr_mode", False):
            self._pending_random_code = rf_random_code()
        self._new_game(first_blanc_player=next_first_blanc)
        if self.vs_ai:
            # deep grey joue le camp opposé au joueur humain
            self.ai_camp = "Blanc" if next_first_blanc == "deep grey" else "Noir"
            self._maybe_ai_turn()

    def _popup_finish(self, title, body, winner_player):
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(Label(text=body, font_size=SF("14sp"), color=(1, 1, 1, 1)))
        if winner_player:
            big = Label(text=f"Victoire de {winner_player} !",
                        font_size=SF("18sp"), bold=True,
                        color=COL_ORANGE,
                        size_hint=(1, None), height=S(40))
        else:
            big = Label(text="Match nul",
                        font_size=SF("18sp"), bold=True,
                        color=(0.2, 0.2, 0.2, 1),
                        size_hint=(1, None), height=S(40))
        content.add_widget(big)
        # En ligne (partie classée) : afficher le changement de mélo
        if self.online_mode:
            delta = getattr(self, "_last_melo_delta", None)
            melo_val = getattr(self, "_last_melo_value", None)
            if delta is not None and melo_val is not None:
                sign = "+" if delta >= 0 else ""
                dcol = (0.20, 0.70, 0.20, 1) if delta > 0 else (
                    (0.85, 0.25, 0.25, 1) if delta < 0 else (0.5, 0.5, 0.5, 1))
                melo_lbl = Label(text="Mélo : %d  (%s%d)" % (melo_val, sign, delta),
                                 font_size=SF("15sp"), bold=True, color=dcol,
                                 size_hint=(1, None), height=S(34))
                content.add_widget(melo_lbl)
            else:
                # Le mélo peut arriver juste après : message d'attente neutre
                wait_lbl = Label(text="Mise à jour du mélo…",
                                 font_size=SF("13sp"), italic=True,
                                 color=(0.6, 0.6, 0.6, 1),
                                 size_hint=(1, None), height=S(28))
                content.add_widget(wait_lbl)
        btn = RoundButton(text="Retour au menu", bg_color=COL_BLUE,
                          color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                          size_hint=(1, None), height=S(50))
        content.add_widget(btn)
        popup = Popup(title=title, content=content,
                      size_hint=(0.85, 0.55), auto_dismiss=True)
        btn.bind(on_release=lambda *a: (popup.dismiss(), self._back_to_menu()))
        popup.open()


# ── Écran "Menu Parties" ─────────────────────────────────────────────────────

class PartiesMenuScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _open_online_history(self, *a):
        """Ouvre l'historique en ligne (les parties du compte). Si l'utilisateur
        n'est pas connecté, on l'invite à se connecter."""
        if not ONLINE.is_logged_in():
            content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
            lbl = Label(text="Connectez-vous à un compte\npour voir vos parties en ligne.",
                        color=(1, 1, 1, 1), halign="center", valign="middle",
                        font_size=SF("15sp"))
            lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            content.add_widget(lbl)
            btn = RoundButton(text="OK", bg_color=COL_BLUE, color=(1, 1, 1, 1),
                              font_size=SF("15sp"), bold=True, size_hint=(1, 0.4))
            content.add_widget(btn)
            p = Popup(title="", content=content, size_hint=(0.8, 0.4),
                      separator_height=0)
            btn.bind(on_release=lambda *a: p.dismiss())
            p.open()
            return
        self.manager.current = "history_online"

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        header = BoxLayout(size_hint=(1, 0.08), padding=(S(8), S(6)))
        back = RoundButton(text="< Menu", font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        title = Label(text="Historique", font_size=SF("32sp"), italic=True,
                      color=(0, 0, 0, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(110)))
        root.add_widget(header)

        body = FloatLayout()

        b_online = RoundButton(text="Historique en ligne", font_size=SF("17sp"), bold=True,
                               bg_color=COL_BLUE, color=(1, 1, 1, 1),
                               size_hint=(0.8, 0.1),
                               pos_hint={"center_x": 0.5, "top": 0.85})
        b_online.bind(on_release=lambda *a: self._open_online_history())
        body.add_widget(b_online)
        self._b_online = b_online

        b_local = RoundButton(text="Historique en local", font_size=SF("17sp"), bold=True,
                              bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                              size_hint=(0.8, 0.1),
                              pos_hint={"center_x": 0.5, "top": 0.70})
        b_local.bind(on_release=lambda *a: setattr(self.manager, "current", "history_local"))
        body.add_widget(b_local)
        self._b_local = b_local

        b_reader = RoundButton(text="Lecteur nmc", font_size=SF("17sp"), bold=True,
                               bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                               size_hint=(0.8, 0.1),
                               pos_hint={"center_x": 0.5, "top": 0.55})
        b_reader.bind(on_release=lambda *a: setattr(self.manager, "current", "reader"))
        body.add_widget(b_reader)

        root.add_widget(body)
        self.add_widget(root)

    def apply_theme_colors(self):
        if hasattr(self, "_bg_col"):
            self._bg_col.rgba = COL_BG_MENU
        if hasattr(self, "_b_online"):
            self._b_online.set_bg(COL_BLUE)
        if hasattr(self, "_b_local"):
            self._b_local.set_bg(COL_ORANGE)


# ── Écran "Historique en ligne" (placeholder) ───────────────────────────────

class OnlineHistoryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def on_enter(self):
        self._refresh_list()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        header = BoxLayout(size_hint=(1, 0.08), padding=(S(8), S(6)))
        back = RoundButton(text="< Historique", font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "parties_menu"))
        title = Label(text="En ligne", font_size=SF("28sp"), italic=True,
                      color=(0, 0, 0, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(110)))
        root.add_widget(header)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=6)
        self.list_box = GridLayout(cols=1, spacing=S(8),
                                   padding=(S(12), S(8), S(12), S(12)),
                                   size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def _refresh_list(self):
        self.list_box.clear_widgets()
        if not ONLINE.is_logged_in():
            msg = Label(text="Connectez-vous pour voir vos parties en ligne.",
                        font_size=SF("15sp"), color=(0.3, 0.3, 0.3, 1), italic=True,
                        size_hint=(1, None), height=S(80), halign="center")
            msg.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
            self.list_box.add_widget(msg)
            return
        loading = Label(text="Chargement des parties en ligne…",
                        font_size=SF("14sp"), color=(0.3, 0.3, 0.3, 1),
                        italic=True, size_hint=(1, None), height=S(80),
                        halign="center")
        self.list_box.add_widget(loading)

        def on_games(games, err):
            self.list_box.clear_widgets()
            if err:
                self.list_box.add_widget(Label(
                    text="Impossible de charger l'historique\n(%s)" % err,
                    font_size=SF("14sp"), color=(0.6, 0.2, 0.2, 1), italic=True,
                    size_hint=(1, None), height=S(80), halign="center"))
                return
            if not games:
                self.list_box.add_widget(Label(
                    text="Aucune partie en ligne.\nJouez une partie en ligne pour la voir ici !",
                    font_size=SF("15sp"), color=(0.3, 0.3, 0.3, 1), italic=True,
                    size_hint=(1, None), height=S(80), halign="center"))
                return
            for g in games:
                self._add_account_entry(g)
        ONLINE.list_account_games(on_games)


# ── Écran "Historique local" ─────────────────────────────────────────────────

class ClickableRow(BoxLayout):
    """Un BoxLayout qui réagit au tap (comme un bouton, mais peut contenir
    d'autres widgets, contrairement à un Button Kivy)."""
    def __init__(self, on_press_cb=None, **kw):
        super().__init__(**kw)
        self._on_press_cb = on_press_cb

    def on_touch_down(self, touch):
        if self.collide_point(*touch.pos):
            # Laisser les enfants gérer d'abord (ex : si un bouton est dedans)
            for child in self.children:
                if child.dispatch("on_touch_down", touch):
                    return True
            if self._on_press_cb:
                self._on_press_cb()
            return True
        return super().on_touch_down(touch)


class HistoryScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def on_enter(self):
        """Recharger la liste à chaque entrée."""
        self._refresh_list()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        header = BoxLayout(size_hint=(1, 0.08), padding=(S(8), S(6)))
        back = RoundButton(text="< Historique", font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "parties_menu"))
        title = Label(text="En local", font_size=SF("28sp"), italic=True,
                      color=(0, 0, 0, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(110)))
        root.add_widget(header)

        # Liste scrollable
        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=6)
        self.list_box = GridLayout(cols=1, spacing=S(8), padding=(S(12), S(8), S(12), S(12)),
                                    size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def _refresh_list(self):
        self.list_box.clear_widgets()
        # Historique LOCAL : toujours les parties locales (.nmc), qu'on soit
        # connecté ou non. Les parties en ligne vont dans l'historique en ligne.
        files = list_local_parties()
        if not files:
            empty = Label(text="Aucune partie locale.\nJouez en local ou contre l'IA pour la voir ici !",
                          font_size=SF("15sp"), color=(0.3, 0.3, 0.3, 1), italic=True,
                          size_hint=(1, None), height=S(80), halign="center")
            empty.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
            self.list_box.add_widget(empty)
            return
        for filepath in files:
            self._add_entry(filepath)

    def _add_account_entry(self, g):
        """Ajoute une ligne d'historique pour une partie DU COMPTE (métadonnées
        venant du serveur). Le contenu .nmc complet est récupéré au tap."""
        method = g.get("methode", "?")
        result = g.get("resultat", "?")
        date   = ""  # le serveur stocke played_at (epoch) ; on formate
        try:
            import datetime as _dt
            ts = g.get("played_at")
            if ts:
                date = _dt.datetime.fromtimestamp(int(ts)).strftime("%Y-%m-%d %H:%M")
        except Exception:
            pass
        cadence = g.get("cadence", "?")
        verbe = {"fugue": "fugue", "mat": "mat", "temps": "temps",
                 "abandon": "abandon", "nulle": "nulle",
                 "papatte": "papatte"}.get(method, method)
        if cadence == "corr":
            cad_str = "Corresp"
        elif cadence == "zen":
            cad_str = "Zen"
        elif cadence in ("?", None, ""):
            cad_str = "?"
        else:
            cad_str = f"{cadence}min"
        player1 = g.get("joueur1", "Joueur 1")
        player2 = g.get("joueur2", "Joueur 2")
        game_uid = g.get("game_uid", "")

        if result == "1-0":
            sym_col = (0.30, 0.85, 0.30, 1); sym = "#"
        elif result == "0-1":
            sym_col = (1.0, 0.33, 0.33, 1); sym = "#"
        else:
            sym_col = (0.75, 0.75, 0.75, 1); sym = "½"

        wrap = BoxLayout(orientation="horizontal", size_hint=(1, None),
                         height=S(90), spacing=S(8))
        row = ClickableRow(on_press_cb=lambda u=game_uid: self._open_account_party(u),
                           orientation="horizontal", size_hint=(1, 1),
                           padding=(S(12), S(6)), spacing=S(10))
        with row.canvas.before:
            Color(*COL_BTN_GREY)
            row._rect = RoundedRectangle(pos=row.pos, size=row.size, radius=[S(10)])
        row.bind(pos=lambda b, *a: setattr(b._rect, "pos", b.pos),
                 size=lambda b, *a: setattr(b._rect, "size", b.size))
        sym_lbl = Label(text=sym, font_size=SF("26sp"), bold=True, color=sym_col,
                        size_hint=(None, 1), width=S(40), halign="center",
                        valign="middle")
        sym_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(sym_lbl)
        txt_box = BoxLayout(orientation="vertical", size_hint=(1, 1))
        names_lbl = Label(text=f"{player1}  vs  {player2}", font_size=SF("14sp"),
                          bold=True, color=(1, 1, 1, 1), size_hint=(1, 0.4),
                          halign="left", valign="middle", shorten=True)
        names_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        date_lbl = Label(text=date, font_size=SF("11sp"), color=(0.85, 0.85, 0.85, 1),
                         size_hint=(1, 0.3), halign="left", valign="middle")
        date_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        info_lbl = Label(text=f"{cad_str}  •  {verbe}", font_size=SF("11sp"),
                         italic=True, color=(0.85, 0.85, 0.85, 1),
                         size_hint=(1, 0.3), halign="left", valign="middle")
        info_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        txt_box.add_widget(names_lbl)
        txt_box.add_widget(date_lbl)
        txt_box.add_widget(info_lbl)
        row.add_widget(txt_box)
        wrap.add_widget(row)
        self.list_box.add_widget(wrap)

    def _open_account_party(self, game_uid):
        """Récupère le .nmc d'une partie du compte puis l'ouvre en lecture."""
        def on_nmc(nmc_text, err):
            if err or not nmc_text:
                Popup(title="Erreur",
                      content=Label(text="Impossible de charger la partie.",
                                    color=(1, 1, 1, 1)),
                      size_hint=(0.7, 0.3)).open()
                return
            meta, moves = parse_nmc_content(nmc_text)
            if not meta:
                return
            g = self.manager.get_screen("game")
            if g.load_replay(meta, moves):
                self.manager.current = "game"
        ONLINE.get_account_game(game_uid, on_nmc)

    def _add_entry(self, filepath):
        meta, moves = parse_nmc_file(filepath)
        if not meta: return
        method = meta.get("methode", "?")
        result = meta.get("resultat", "?")
        points = meta.get("points", "0")
        date   = meta.get("date", "")
        cadence = meta.get("cadence", "?")
        objectif = meta.get("objectif", "?")

        # Symbole de résultat (point de vue Joueur 1) : * = fugue/abandon (2pts), # = mat, ½ = nulle
        if result == "1-0":
            sym = "*" if points == "2" else "#"
        elif result == "0-1":
            sym = "*" if points == "2" else "#"
        else:
            sym = "½"

        cad_str = f"{cadence}min" if cadence != "zen" else "Zen"
        verbe = {"fugue": "fugue", "mat": "mat",
                 "temps": "temps", "abandon": "abandon",
                 "nulle": "nulle"}.get(method, method)

        # Conteneur horizontal : zone cliquable + bouton Copier
        wrap = BoxLayout(orientation="horizontal", size_hint=(1, None),
                         height=S(90), padding=(0, 0, 0, 0), spacing=S(8))

        player1 = meta.get("joueur1", "Joueur 1")
        player2 = meta.get("joueur2", "Joueur 2")

        # Conteneur cliquable : un BoxLayout avec fond gris (un Button Kivy ne
        # peut PAS contenir d'autres widgets correctement, d'où les bugs).
        # On utilise un BoxLayout custom qui réagit au tap.
        if result == "1-0":
            sym_col = (0.30, 0.85, 0.30, 1)
        elif result == "0-1":
            sym_col = (1.0, 0.33, 0.33, 1)
        else:
            sym_col = (0.75, 0.75, 0.75, 1)

        row = ClickableRow(on_press_cb=lambda fp=filepath: self._open_party(fp),
                           orientation="horizontal", size_hint=(1, 1),
                           padding=(S(12), S(6)), spacing=S(10))
        with row.canvas.before:
            Color(*COL_BTN_GREY)
            row._rect = RoundedRectangle(pos=row.pos, size=row.size, radius=[S(10)])
        row.bind(pos=lambda b, *a: setattr(b._rect, "pos", b.pos),
                 size=lambda b, *a: setattr(b._rect, "size", b.size))

        sym_lbl = Label(text=sym, font_size=SF("26sp"), bold=True,
                        color=sym_col, size_hint=(None, 1), width=S(40),
                        halign="center", valign="middle")
        sym_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(sym_lbl)

        # Bloc texte vertical : noms / date / cadence•méthode
        txt_box = BoxLayout(orientation="vertical", size_hint=(1, 1))
        names_lbl = Label(text=f"{player1}  vs  {player2}",
                          font_size=SF("14sp"), bold=True, color=(1, 1, 1, 1),
                          size_hint=(1, 0.4), halign="left", valign="middle",
                          shorten=True)
        names_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        date_lbl = Label(text=date, font_size=SF("11sp"), color=(0.85, 0.85, 0.85, 1),
                         size_hint=(1, 0.3), halign="left", valign="middle")
        date_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        info_lbl = Label(text=f"{cad_str}  •  {verbe}", font_size=SF("11sp"),
                         italic=True, color=(0.85, 0.85, 0.85, 1),
                         size_hint=(1, 0.3), halign="left", valign="middle")
        info_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        txt_box.add_widget(names_lbl)
        txt_box.add_widget(date_lbl)
        txt_box.add_widget(info_lbl)
        row.add_widget(txt_box)

        wrap.add_widget(row)

        # Bouton Copier à droite
        b_copy = RoundButton(text="Copier", font_size=SF("11sp"), bold=True,
                             bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                             size_hint=(None, 1), width=S(76), radius=S(8))
        b_copy.bind(on_release=lambda *a, fp=filepath: self._copy_nmc(fp))
        wrap.add_widget(b_copy)

        self.list_box.add_widget(wrap)

    def _open_party(self, filepath):
        """Ouvre la partie en mode visualisation dans le GameScreen."""
        game = self.manager.get_screen("game")
        meta, moves_text = parse_nmc_file(filepath)
        if not meta:
            self._show_error()
            return
        if game.load_replay(meta, moves_text):
            self.manager.current = "game"
        else:
            self._show_error()

    def _copy_nmc(self, filepath):
        """Affiche le contenu du fichier dans une popup avec sélection facile."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            return
        from kivy.uix.textinput import TextInput
        content_box = BoxLayout(orientation="vertical", spacing=8, padding=10)
        content_box.add_widget(Label(text="Sélectionnez tout le texte ci-dessous,\npuis copiez-le.",
                                     font_size=SF("13sp"), color=(1, 1, 1, 1),
                                     size_hint=(1, None), height=S(40), halign="center"))
        ti = TextInput(text=content, multiline=True, readonly=False,
                       font_size=SF("13sp"), size_hint=(1, 1))
        content_box.add_widget(ti)
        close_btn = RoundButton(text="Fermer", bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                                size_hint=(1, None), height=S(44))
        content_box.add_widget(close_btn)
        p = Popup(title="Contenu .nmc", content=content_box,
                  size_hint=(0.95, 0.85), auto_dismiss=True)
        close_btn.bind(on_release=lambda *a: p.dismiss())
        p.open()

    def _share_nmc(self, filepath):
        """Tente d'utiliser le partage natif Android via plyer. Sinon affiche un popup."""
        try:
            from plyer import share
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            share.share(title="Partie La Fuga", text=content)
        except Exception:
            # Fallback : ouvre la popup de copie
            self._copy_nmc(filepath)

    def _show_error(self):
        p = Popup(title="Erreur",
                  content=Label(text="désolé, le fichier nmc est invalide,\nla lecture ne peut pas s effectuer",
                                color=(1, 1, 1, 1), font_size=SF("13sp")),
                  size_hint=(0.85, 0.3))
        p.open()


# OnlineHistoryScreen réutilise la présentation/ouverture des parties du compte
# définies dans HistoryScreen (assigné ici car HistoryScreen est défini après).
OnlineHistoryScreen._add_account_entry = HistoryScreen._add_account_entry
OnlineHistoryScreen._open_account_party = HistoryScreen._open_account_party


# ── Écran "Lecteur nmc" ──────────────────────────────────────────────────────

class ReaderScreen(Screen):
    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        header = BoxLayout(size_hint=(1, 0.08), padding=(S(8), S(6)))
        back = RoundButton(text="< Historique", font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "parties_menu"))
        title = Label(text="Lecteur nmc", font_size=SF("26sp"), italic=True,
                      color=(0, 0, 0, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(110)))
        root.add_widget(header)

        # Zone de saisie
        from kivy.uix.textinput import TextInput
        instruct = Label(text="Collez le contenu d'un fichier .nmc ci-dessous :",
                         font_size=SF("13sp"), color=(0.1, 0.1, 0.1, 1),
                         size_hint=(1, None), height=S(30), halign="center")
        instruct.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        root.add_widget(instruct)

        self.text_input = TextInput(multiline=True, font_size=SF("13sp"),
                                     hint_text="[Date \"...\"]\n[Joueur1 \"...\"]\n...\n\n1.Do1-Do2/Do8-Do7  2...",
                                     size_hint=(1, 1))
        wrap = BoxLayout(padding=(12, 8, 12, 8))
        wrap.add_widget(self.text_input)
        root.add_widget(wrap)

        # Bouton Lire
        btn_box = BoxLayout(size_hint=(1, None), height=S(60), padding=(12, 4, 12, 12))
        play_btn = RoundButton(text="Lire", bg_color=COL_ORANGE,
                               color=(1, 1, 1, 1), font_size=SF("16sp"), bold=True,
                               size_hint=(1, None), height=S(50))
        play_btn.bind(on_release=lambda *a: self._read())
        btn_box.add_widget(play_btn)
        root.add_widget(btn_box)
        self.add_widget(root)

    def _read(self):
        text = self.text_input.text.strip()
        if not text:
            self._show_error()
            return
        meta, moves_text = parse_nmc_content(text)
        game = self.manager.get_screen("game")
        if game.load_replay(meta, moves_text):
            self.manager.current = "game"
        else:
            self._show_error()

    def _show_error(self):
        p = Popup(title="Erreur",
                  content=Label(text="désolé, le fichier nmc est invalide,\nla lecture ne peut pas s effectuer",
                                color=(1, 1, 1, 1), font_size=SF("13sp")),
                  size_hint=(0.85, 0.3))
        p.open()


class ThemePreview(Widget):
    """Affiche 4 cases avec pièces (héritier blanc/noir, garde blanc, soldat noir)
    sur le fond du plateau, pour prévisualiser un thème."""
    def __init__(self, theme_name, **kw):
        super().__init__(**kw)
        self.theme_name = theme_name
        self.bind(pos=self._redraw, size=self._redraw)

    def set_theme(self, name):
        self.theme_name = name
        self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        t = THEMES.get(self.theme_name, THEMES["original"])
        n = 4
        cs = min(self.width / n, self.height)
        ox = self.x + (self.width - cs * n) / 2
        oy = self.y + (self.height - cs) / 2
        # Pièces : (type, camp), l'accent prend la couleur du thème
        specs = [("Héritier", "Blanc"), ("Héritier", "Noir"),
                 ("Garde", "Blanc"), ("Soldat", "Noir")]
        img_dir = _theme_image_dir(self.theme_name)   # dossier si thème à images
        is_img = img_dir is not None
        with self.canvas:
            if is_img:
                # Aperçu d'un thème à images : fond image (plateau.png) si dispo
                tex = _theme_bg_texture("plateau.png", theme=self.theme_name)
                if tex is not None:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex, pos=(ox, oy), size=(cs * n, cs))
                else:
                    Color(*t["board"])
                    Rectangle(pos=(ox, oy), size=(cs * n, cs))
            else:
                Color(*t["board"])
                Rectangle(pos=(ox, oy), size=(cs * n, cs))
            Color(*t["grid"])
            for i in range(n + 1):
                Line(points=[ox + i * cs, oy, ox + i * cs, oy + cs], width=S(1))
            Line(points=[ox, oy, ox + cs * n, oy], width=S(1))
            Line(points=[ox, oy + cs, ox + cs * n, oy + cs], width=S(1))
        # Pièces : pour un thème à images, afficher les images via preview_theme
        # (pas de modification de la globale CURRENT_THEME -> aucun effet de bord)
        if is_img:
            for i, (ptype, camp) in enumerate(specs):
                piece = {"type": ptype, "camp": camp}
                x = ox + i * cs
                draw_piece(self.canvas, x, oy, cs, piece,
                           preview_theme=self.theme_name)
        else:
            for i, (ptype, camp) in enumerate(specs):
                piece = {"type": ptype, "camp": camp}
                x = ox + i * cs
                draw_piece_themed(self.canvas, x, oy, cs, piece,
                                  accent_clair=t["clair"], accent_fonce=t["fonce"],
                                  board_col=t["board"])


def draw_piece_themed(canvas, x, y, sz, piece, accent_clair, accent_fonce, board_col=None):
    """Comme draw_piece mais avec des accents de couleur fournis (pour l'aperçu)."""
    global COL_ORANGE, COL_BLUE, COL_BG_BOARD
    save_o, save_b, save_bg = COL_ORANGE, COL_BLUE, COL_BG_BOARD
    COL_ORANGE = accent_clair
    COL_BLUE = accent_fonce
    if board_col is not None:
        COL_BG_BOARD = board_col
    try:
        draw_piece(canvas, x, y, sz, piece, force_normal=True)
    finally:
        COL_ORANGE = save_o
        COL_BLUE = save_b
        COL_BG_BOARD = save_bg


def open_settings_popup(app_or_game):
    """Ouvre la popup de réglages (son + thème).
    app_or_game : soit le GameScreen (pour rafraîchir en direct), soit None."""
    # Trouver le ScreenManager
    from kivy.app import App
    app = App.get_running_app()
    sm = app.sm if hasattr(app, "sm") else None

    cfg = load_config()

    root = BoxLayout(orientation="vertical", spacing=S(6), padding=S(16))

    # ── Section Son ──
    root.add_widget(Label(text="Volume", font_size=SF("17sp"), bold=True,
                          color=(1, 1, 1, 1), size_hint=(1, 0.07)))
    vol_slider = Slider(min=0, max=1, value=SOUNDS.volume,
                        size_hint=(1, 0.08))
    vol_label = Label(text=f"{int(SOUNDS.volume * 100)}%", font_size=SF("13sp"),
                      color=(0.85, 0.85, 0.85, 1), size_hint=(1, 0.05))
    def on_vol(inst, val):
        SOUNDS.set_volume(val)
        vol_label.text = f"{int(val * 100)}%"
        save_config(volume=val)
    vol_slider.bind(value=on_vol)
    root.add_widget(vol_slider)
    root.add_widget(vol_label)

    # ── Sélecteur d'instrument (sous le volume) ──
    inst_row = BoxLayout(orientation="horizontal", size_hint=(1, 0.09), spacing=S(6))
    inst_state = {"idx": INSTRUMENT_ORDER.index(SOUNDS.instrument)
                  if SOUNDS.instrument in INSTRUMENT_ORDER else 0}
    inst_prev = RoundButton(text="<", font_size=SF("16sp"), bold=True,
                            bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                            size_hint=(0.16, 1))
    inst_lbl = Label(text=INSTRUMENT_LABELS[INSTRUMENT_ORDER[inst_state["idx"]]],
                     font_size=SF("14sp"), bold=True, color=(1, 1, 1, 1),
                     halign="center", valign="middle", size_hint=(0.68, 1))
    inst_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    inst_next = RoundButton(text=">", font_size=SF("16sp"), bold=True,
                            bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                            size_hint=(0.16, 1))
    def _set_instrument(*a):
        name = INSTRUMENT_ORDER[inst_state["idx"]]
        inst_lbl.text = INSTRUMENT_LABELS[name]
        SOUNDS.set_instrument(name)
        save_config(instrument=name)
        # Petit aperçu sonore
        SOUNDS._play("do4")
    def inst_go_prev(*a):
        inst_state["idx"] = (inst_state["idx"] - 1) % len(INSTRUMENT_ORDER)
        _set_instrument()
    def inst_go_next(*a):
        inst_state["idx"] = (inst_state["idx"] + 1) % len(INSTRUMENT_ORDER)
        _set_instrument()
    inst_prev.bind(on_release=inst_go_prev)
    inst_next.bind(on_release=inst_go_next)
    inst_row.add_widget(inst_prev)
    inst_row.add_widget(inst_lbl)
    inst_row.add_widget(inst_next)
    root.add_widget(inst_row)

    # ── Section Vitesse d'animation des pièces ──
    root.add_widget(Label(text="Vitesse de glissée des pièces", font_size=SF("17sp"),
                          bold=True, color=(1, 1, 1, 1), size_hint=(1, 0.07)))
    # Valeur stockée = durée de l'animation en secondes (0 = instantané).
    # Curseur : gauche = instantané (0s), droite = lent (0.6s).
    try:
        cur_speed = float(cfg.get("slide_speed", "0.18"))
    except (ValueError, TypeError):
        cur_speed = 0.18
    speed_slider = Slider(min=0.0, max=0.6, value=cur_speed, size_hint=(1, 0.08))
    def speed_text(v):
        if v < 0.02: return "Instantané"
        if v < 0.20: return "Rapide"
        if v < 0.40: return "Moyen"
        return "Lent"
    speed_label = Label(text=speed_text(cur_speed), font_size=SF("13sp"),
                        color=(0.85, 0.85, 0.85, 1), size_hint=(1, 0.05))
    def on_speed(inst, val):
        speed_label.text = speed_text(val)
        save_config(slide_speed=round(val, 3))
        global SLIDE_SPEED
        SLIDE_SPEED = round(val, 3)
    speed_slider.bind(value=on_speed)
    root.add_widget(speed_slider)
    root.add_widget(speed_label)

    # ── Section Thème ──
    root.add_widget(Label(text="Thème", font_size=SF("17sp"), bold=True,
                          color=(1, 1, 1, 1), size_hint=(1, 0.07)))

    # État local de l'index de thème affiché
    state = {"idx": THEME_ORDER.index(CURRENT_THEME) if CURRENT_THEME in THEME_ORDER else 0}

    # Ligne : < nom_thème >  +  aperçu  (boutons réduits)
    theme_row = BoxLayout(orientation="horizontal", size_hint=(1, 0.14), spacing=S(6))
    btn_prev = RoundButton(text="<", font_size=SF("16sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(0.14, 1))
    name_box = BoxLayout(orientation="vertical", size_hint=(0.32, 1))
    theme_name_lbl = Label(text=THEME_LABELS[THEME_ORDER[state["idx"]]],
                           font_size=SF("14sp"), bold=True, color=(1, 1, 1, 1),
                           halign="center", valign="middle")
    theme_name_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    name_box.add_widget(theme_name_lbl)
    preview = ThemePreview(THEME_ORDER[state["idx"]], size_hint=(0.36, 1))
    btn_next = RoundButton(text=">", font_size=SF("16sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(0.14, 1))
    theme_row.add_widget(btn_prev)
    theme_row.add_widget(name_box)
    theme_row.add_widget(preview)
    theme_row.add_widget(btn_next)
    root.add_widget(theme_row)

    def update_preview():
        name = THEME_ORDER[state["idx"]]
        theme_name_lbl.text = THEME_LABELS[name]
        preview.set_theme(name)

    def go_prev(*a):
        state["idx"] = (state["idx"] - 1) % len(THEME_ORDER)
        update_preview()
    def go_next(*a):
        state["idx"] = (state["idx"] + 1) % len(THEME_ORDER)
        update_preview()
    btn_prev.bind(on_release=go_prev)
    btn_next.bind(on_release=go_next)

    # Boutons appliquer / fermer (réduits)
    btn_box = BoxLayout(orientation="horizontal", size_hint=(1, 0.085), spacing=S(8))
    btn_apply = RoundButton(text="Appliquer ce thème", bg_color=COL_ORANGE,
                            color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True,
                            size_hint=(0.72, 1))
    btn_close = RoundButton(text="Fermer", bg_color=COL_BTN_GREY,
                            color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True,
                            size_hint=(0.28, 1))
    btn_box.add_widget(btn_apply)
    btn_box.add_widget(btn_close)
    root.add_widget(btn_box)

    popup = Popup(title="Réglages", content=root, size_hint=(0.92, 0.8),
                  auto_dismiss=True)

    def apply_theme_now(*a):
        name = THEME_ORDER[state["idx"]]
        apply_theme(name)
        save_config(theme=name)
        if sm:
            refresh_all_screens(sm)
        # Rafraîchir TOUS les boutons de la popup de réglages elle-même
        # (elle n'est pas dans sm.screens)
        _refresh_all_buttons(root)
        btn_apply.set_bg(COL_ORANGE)
        btn_close.set_bg(COL_BTN_GREY)
        # Rafraîchir aussi les boutons du popup PAUSE s'il est ouvert dessous
        # (sinon ils gardent les couleurs de l'ancien thème).
        try:
            if app_or_game is not None and \
                    hasattr(app_or_game, "_pause_theme_refresh"):
                app_or_game._pause_theme_refresh()
        except Exception:
            pass
        # Rafraîchir l'aperçu courant
        preview.set_theme(name)
    btn_apply.bind(on_release=apply_theme_now)
    btn_close.bind(on_release=lambda *a: popup.dismiss())

    popup.open()


def _refresh_all_buttons(widget):
    """Force le redessin de tous les RoundButton sous un widget (récursif).
    Nécessaire au changement de thème : un bouton non rafraîchi garderait son
    ancien dessin (ex. un dégradé arc-en-ciel resté sur un autre thème)."""
    try:
        if isinstance(widget, RoundButton):
            widget.refresh_theme_color()
    except Exception:
        pass
    for child in getattr(widget, "children", []):
        _refresh_all_buttons(child)


def refresh_all_screens(sm):
    """Met à jour les couleurs de tous les écrans après un changement de thème."""
    for screen in sm.screens:
        # Fond des écrans menu
        if hasattr(screen, "_bg_col"):
            try:
                screen._bg_col.rgba = COL_BG_MENU
            except Exception:
                pass
        # Écran de jeu : rafraîchir bandeaux + plateau
        if hasattr(screen, "apply_theme_colors"):
            try:
                screen.apply_theme_colors()
            except Exception:
                pass
        # Forcer le redessin de TOUS les boutons de l'écran (évite qu'un dégradé
        # arc-en-ciel reste collé sur un autre thème).
        try:
            _refresh_all_buttons(screen)
        except Exception:
            pass
    # Rafraîchir les listes/menus qui ont des boutons colorés
    for name in ("history_local",):
        try:
            scr = sm.get_screen(name)
            if hasattr(scr, "_refresh_list"):
                scr._refresh_list()
        except Exception:
            pass


def _enable_immersive_mode(*args):
    """Active le mode plein écran immersif sur Android : masque la barre du haut
    (batterie/heure) et celle du bas (boutons de navigation). Les barres
    réapparaissent quand l'utilisateur glisse depuis un bord, puis se recachent.
    Sans effet hors Android."""
    try:
        from kivy.utils import platform
        if platform != "android":
            return
        from jnius import autoclass
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        View = autoclass("android.view.View")
        activity = PythonActivity.mActivity

        def _apply(*a):
            try:
                window = activity.getWindow()
                decor = window.getDecorView()
                flags = (
                    View.SYSTEM_UI_FLAG_LAYOUT_STABLE
                    | View.SYSTEM_UI_FLAG_LAYOUT_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_LAYOUT_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                    | View.SYSTEM_UI_FLAG_FULLSCREEN
                    | View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
                )
                decor.setSystemUiVisibility(flags)
            except Exception:
                pass

        try:
            activity.runOnUiThread(_apply)
        except Exception:
            _apply()
    except Exception:
        # En cas de souci, on ne casse pas l'appli (juste pas de plein écran)
        pass


class _DummyDismiss:
    """Objet factice avec une méthode dismiss() sans effet. Sert à réutiliser
    _confirm_cancel_match depuis le bouton retour Android, où aucun popup de
    pause n'est ouvert à refermer."""
    def dismiss(self, *a, **k):
        pass


class FugaApp(App):
    def build(self):
        # DIAGNOSTIC : si le démarrage plante, on AFFICHE l'erreur à l'écran au
        # lieu de fermer l'appli (écran noir / retour au menu). C'est sûr : si
        # tout va bien, l'appli démarre normalement.
        try:
            return self._build_real()
        except Exception:
            import traceback
            err = traceback.format_exc()
            try:
                from kivy.uix.scrollview import ScrollView
                from kivy.uix.label import Label
                sv = ScrollView()
                lbl = Label(text="ERREUR AU DEMARRAGE :\n\n" + err,
                            font_size="13sp", color=(1, 1, 1, 1),
                            size_hint=(1, None), halign="left", valign="top",
                            padding=(20, 40))
                lbl.bind(texture_size=lambda w, s: setattr(
                    w, "height", s[1] + 80))
                lbl.bind(width=lambda w, v: setattr(
                    w, "text_size", (v - 40, None)))
                sv.add_widget(lbl)
                return sv
            except Exception:
                from kivy.uix.label import Label
                return Label(text=err[-800:])

    def _build_real(self):
        self.title = "La Fuga"
        # Charger la config (thème + volume + en ligne)
        cfg = load_config()
        apply_theme(cfg["theme"])
        # Mode Random Fuga (interrupteur global) : se réinitialise à CHAQUE
        # lancement de l'appli (il n'est plus mémorisé entre deux sessions).
        global RANDOM_MODE
        RANDOM_MODE = False
        # Vitesse de glissée des pièces
        global SLIDE_SPEED
        try:
            SLIDE_SPEED = float(cfg.get("slide_speed", "0.18"))
        except (ValueError, TypeError):
            SLIDE_SPEED = 0.18
        # URL serveur (modifiable dans config.txt sous la clé 'server_url')
        if cfg.get("server_url"):
            ONLINE.server_url = cfg["server_url"]
        # Reconnexion automatique si un token est sauvegardé (rester connecté
        # entre deux ouvertures de l'appli).
        token = cfg.get("online_token")
        if token:
            ONLINE.token = token
            ONLINE.pseudo = cfg.get("online_pseudo")
            try:
                ONLINE.melo = int(cfg.get("online_melo", "1500"))
            except (ValueError, TypeError):
                ONLINE.melo = 1500
            def on_auto_login(ok):
                if not ok:
                    ONLINE.logout()
                    clear_online_session()
                try:
                    menu = self.sm.get_screen("menu")
                    if hasattr(menu, "_refresh_online_ui"):
                        menu._refresh_online_ui()
                except Exception:
                    pass
            ONLINE.auto_login_with_token(token, on_auto_login)
        # Charger les sons (en différé pour ne pas ralentir le démarrage)
        def _init_sounds(dt):
            # Instrument sauvegardé (avant de charger, pour charger le bon)
            inst = cfg.get("instrument", "piano")
            if inst in INSTRUMENT_ORDER:
                SOUNDS.instrument = inst
            SOUNDS.load()
            SOUNDS.set_volume(cfg["volume"])
        Clock.schedule_once(_init_sounds, 0.5)
        sm = ScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(LoginScreen(name="login"))
        # Le tuto ne doit jamais empêcher l'appli de démarrer : s'il plante, on
        # continue sans lui (le bouton Plus > Tuto sera simplement sans effet).
        try:
            sm.add_widget(TutoScreen(name="tuto"))
        except Exception:
            import traceback
            traceback.print_exc()
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(PartiesMenuScreen(name="parties_menu"))
        sm.add_widget(HistoryScreen(name="history_local"))
        sm.add_widget(OnlineHistoryScreen(name="history_online"))
        sm.add_widget(ReaderScreen(name="reader"))
        self.sm = sm
        # Premier lancement de l'appli : ouvrir directement le tutoriel (une
        # seule fois). Le joueur peut le quitter quand il veut. Ensuite on va au
        # menu comme d'habitude.
        # Au tout premier lancement, on ouvre le tuto automatiquement. On le fait
        # APRÈS l'affichage de l'appli (Clock) pour ne pas basculer d'écran
        # pendant la construction.
        if str(cfg.get("tuto_seen", "0")) not in ("1", "True", "true"):
            try:
                Clock.schedule_once(
                    lambda dt: setattr(sm, "current", "tuto"), 0.4)
                save_config(tuto_seen="1")
            except Exception:
                pass
        # Gestion du bouton RETOUR Android (touche 27). Par défaut Android
        # quitterait l'app ; on intercepte pour naviguer dans l'app à la place.
        Window.bind(on_keyboard=self._on_key)
        return sm

    def _on_key(self, window, key, *args):
        """Bouton retour Android (key == 27) / Échap. Renvoie True pour dire
        'géré' (ne pas quitter l'app), False pour laisser le comportement par
        défaut (quitter, seulement depuis le menu d'accueil)."""
        if key != 27:
            return False
        # 1) Un popup ouvert ? Le fermer en priorité.
        try:
            from kivy.core.window import Window as _W
            for child in list(_W.children):
                if isinstance(child, Popup):
                    # Popup d'abandon, réglages, etc. : le retour le ferme.
                    child.dismiss()
                    return True
        except Exception:
            pass
        sm = self.sm
        cur = sm.current
        # 2) En jeu : dépend du mode.
        if cur == "game":
            try:
                game = sm.get_screen("game")
            except Exception:
                return True
            if getattr(game, "corr_mode", False):
                # Correspondance : revenir au menu SANS abandonner.
                try: game._back_to_menu()
                except Exception: sm.current = "menu"
                return True
            # EN LIGNE (matchmaking/défi) : le retour Android ouvre simplement le
            # menu pause (pas d'abandon de match ici : on abandonne la PARTIE via
            # le bouton [×], et le MATCH via "Quitter le match" entre deux parties).
            if getattr(game, "online_mode", False):
                try:
                    if not getattr(game, "_game_over", False):
                        open_pause_popup(game)
                except Exception:
                    pass
                return True
            # Partie directe (vs IA ou locale) : même popup que le bouton pause
            # "Annuler le match".
            try:
                if not getattr(game, "_game_over", False):
                    _confirm_cancel_match(game, _DummyDismiss())
            except Exception:
                pass
            return True
        # 3) Autres écrans (règles, historique, parties, login, lecteur...) :
        #    revenir au menu.
        if cur != "menu":
            sm.current = "menu"
            return True
        # 4) Déjà au menu : laisser Android quitter l'app normalement.
        return False

    def on_start(self):
        """Au démarrage : activer le plein écran immersif (Android)."""
        _enable_immersive_mode()
        # Réappliquer peu après (certains téléphones réaffichent les barres au
        # tout début), puis périodiquement par sécurité.
        Clock.schedule_once(_enable_immersive_mode, 1.0)
        Clock.schedule_interval(_enable_immersive_mode, 3.0)

    def on_resume(self):
        """Au retour de veille / d'arrière-plan : réactiver le plein écran,
        FORCER un redessin complet (sinon le contexte graphique perdu laisse un
        écran où l'on ne voit que le fond du thème), et rétablir la connexion."""
        _enable_immersive_mode()

        def _force_redraw(*a):
            try:
                from kivy.core.window import Window as _W
                # Astuce robuste : provoquer un "faux redimensionnement" de la
                # fenêtre. Cela force Kivy à recalculer TOUTE la disposition et à
                # redessiner l'intégralité de l'arbre de widgets (boutons inclus),
                # pas seulement les fonds liés à Window.size.
                w, h = _W.size
                _W.dispatch("on_resize", w, h - 1)
                _W.dispatch("on_resize", w, h)
                _W.canvas.ask_update()
            except Exception:
                pass
            # Forcer le redessin de chaque widget de l'écran courant
            try:
                scr = self.sm.current_screen
                if scr is not None:
                    self._deep_redraw(scr)
                    if self.sm.current == "game":
                        g = self.sm.get_screen("game")
                        if getattr(g, "board_w", None) is not None:
                            g.board_w._redraw()
                        if hasattr(g, "_refresh_ui"):
                            g._refresh_ui()
                    # MENU : au retour d'arrière-plan, le ScrollView peut se
                    # retrouver mal recalculé (contenu hors zone tactile), ce qui
                    # rend les boutons internes inaccessibles alors que le bouton
                    # compte (hors du scroll) reste cliquable. On le remet en haut
                    # et on force le recalcul de sa zone.
                    if self.sm.current == "menu":
                        m = self.sm.get_screen("menu")
                        sc = getattr(m, "_menu_scroll", None)
                        if sc is not None:
                            sc.scroll_y = 1
                            sc.do_layout()
                            sc._trigger_layout()
            except Exception:
                pass

        # Tout de suite, puis à plusieurs reprises (la surface graphique Android
        # peut mettre un peu de temps à être de nouveau prête).
        _force_redraw()
        for delay in (0.2, 0.5, 1.0):
            try:
                Clock.schedule_once(_force_redraw, delay)
            except Exception:
                pass
        try:
            if ONLINE.is_logged_in():
                ONLINE.sio_connect()
        except Exception:
            pass
        return True

    def _deep_redraw(self, widget):
        """Parcourt récursivement l'arbre de widgets et force chacun à se
        redessiner (utile après une perte de contexte graphique Android)."""
        try:
            widget.canvas.ask_update()
        except Exception:
            pass
        for child in getattr(widget, "children", []):
            self._deep_redraw(child)

    def on_pause(self):
        """Mise en pause (arrière-plan) : on garde l'app vivante pour préserver
        la connexion le plus longtemps possible."""
        return True


if __name__ == "__main__":
    import traceback, os, sys
    try:
        FugaApp().run()
    except Exception:
        # Écrit l'erreur dans un fichier à côté du script pour qu'on puisse la lire
        err_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "fuga_error.txt")
        with open(err_path, "w", encoding="utf-8") as f:
            f.write("Erreur au lancement de La Fuga :\n\n")
            traceback.print_exc(file=f)
        # Réaffiche aussi sur stderr au cas où
        traceback.print_exc()
        sys.exit(1)
