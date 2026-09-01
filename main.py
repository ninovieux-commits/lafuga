"""
La Fuga – Version Kivy complète
Compatible Pydroid 3 / Build APK via buildozer
"""
# ── Réglages de performance (À DÉFINIR AVANT tout import créant la fenêtre) ──
# On désactive l'anti-aliasing MSAA, coûteux sur GPU mobile : cela améliore la
# fluidité générale (menus ET parties), surtout sur les écrans haute résolution.
# Réversible : remettre "2" pour réactiver l'anti-aliasing.
from kivy.config import Config
Config.set("graphics", "multisamples", "0")

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
import math
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
# URL du serveur en ligne (VPS OVH, en HTTPS via le domaine fuga-online.fr).
# Modifiable sans recompiler via les Réglages (ou config.txt, clé 'server_url').
SERVER_URL_DEFAULT = "https://fuga-online.fr"

# Liens de don pour le bouton T("Soutenir les devs").
# À COMPLÉTER quand les comptes seront créés (laisser "" = bouton "bientôt").
# Exemple PayPal : "https://paypal.me/tonpseudo"
SUPPORT_LINKS = {
    "paypal":    "https://paypal.me/lafugaonline",
    "kofi":      "",   # ex: https://ko-fi.com/...
    "bmac":      "",   # ex: https://buymeacoffee.com/...
    "liberapay": "",   # ex: https://liberapay.com/...
}

# Histoire affichée au clic sur le logo du menu (bouton fermer).
STORY_TEXT = (
    "Deux frères perdirent la vie dans un duel à mort. Ils régnaient sur le " +
    "royaume ensemble jusqu'à ce qu'un désaccord les pousse à s'affronter. " +
    "Chacun avait un fils, aujourd'hui prétendant au trône.\n\n" +
    "Les sujets des deux partis opposés décidèrent de pousser les deux cousins " +
    "héritiers dans une course mortelle pour désigner lequel des deux prendrait " +
    "le pouvoir et ainsi profiter du jeune âge de ceux-ci afin de les manipuler " +
    "à leur avantage.\n\n" +
    "Les deux rivaux involontaires, épaulés par les nurses les ayant élevés et " +
    "tenant à eux plus qu'à leur propre vie, se virent obligés d'entrer dans une " +
    "poursuite sans merci, et seront peut-être même contraints d'assassiner leur " +
    "seule famille restante afin de survivre et de s'asseoir sur le trône."
)

STORY_I18N = {
    'en': 'Two brothers lost their lives in a duel to the death. They ruled the kingdom together until a disagreement drove them to fight. Each had a son, now a claimant to the throne.\n\nThe subjects of the two opposing camps decided to push the two heir cousins into a deadly race to decide which of them would seize power, taking advantage of their youth to manipulate them to their own ends.\n\nThe two unwilling rivals, supported by the nurses who raised them and cherished them more than their own lives, found themselves forced into a merciless pursuit, and may even be compelled to kill their only remaining family in order to survive and sit upon the throne.',
    'de': 'Zwei Brüder verloren ihr Leben in einem Duell auf Leben und Tod. Sie herrschten gemeinsam über das Königreich, bis ein Streit sie gegeneinander aufbrachte. Jeder hatte einen Sohn, der heute Anwärter auf den Thron ist.\n\nDie Untertanen der beiden verfeindeten Lager beschlossen, die beiden Cousins und Erben in ein tödliches Rennen zu treiben, um zu bestimmen, wer von beiden die Macht ergreifen würde – und ihre Jugend auszunutzen, um sie zu ihrem Vorteil zu manipulieren.\n\nDie beiden unfreiwilligen Rivalen, unterstützt von den Ammen, die sie großzogen und mehr als ihr eigenes Leben liebten, sahen sich zu einer erbarmungslosen Verfolgung gezwungen und müssen vielleicht sogar ihre einzige verbliebene Familie töten, um zu überleben und den Thron zu besteigen.',
    'es': 'Dos hermanos perdieron la vida en un duelo a muerte. Reinaban juntos sobre el reino hasta que un desacuerdo los llevó a enfrentarse. Cada uno tenía un hijo, hoy pretendiente al trono.\n\nLos súbditos de los dos bandos opuestos decidieron empujar a los dos primos herederos a una carrera mortal para designar cuál de los dos tomaría el poder, y así aprovechar su corta edad para manipularlos en su beneficio.\n\nLos dos rivales involuntarios, apoyados por las nodrizas que los criaron y que los querían más que a su propia vida, se vieron obligados a entrar en una persecución sin piedad, y quizá se vean incluso forzados a asesinar a su única familia restante para sobrevivir y sentarse en el trono.',
    'it': "Due fratelli persero la vita in un duello all'ultimo sangue. Regnavano insieme sul regno finché un disaccordo non li spinse a scontrarsi. Ciascuno aveva un figlio, oggi pretendente al trono.\n\nI sudditi delle due fazioni opposte decisero di spingere i due cugini eredi in una corsa mortale per stabilire chi dei due avrebbe preso il potere, approfittando così della loro giovane età per manipolarli a proprio vantaggio.\n\nI due rivali involontari, sostenuti dalle balie che li avevano cresciuti e a cui tenevano più della propria vita, si videro costretti a entrare in un inseguimento senza pietà, e forse saranno persino costretti a uccidere la loro unica famiglia rimasta per sopravvivere e sedersi sul trono.",
    'pt': 'Dois irmãos perderam a vida num duelo até a morte. Reinavam juntos sobre o reino até que um desentendimento os levou a se enfrentar. Cada um tinha um filho, hoje pretendente ao trono.\n\nOs súditos dos dois partidos opostos decidiram lançar os dois primos herdeiros numa corrida mortal para definir qual dos dois tomaria o poder, aproveitando assim a pouca idade deles para manipulá-los em seu benefício.\n\nOs dois rivais involuntários, apoiados pelas amas que os criaram e que os estimavam mais do que a própria vida, viram-se obrigados a entrar numa perseguição implacável, e talvez sejam até forçados a assassinar sua única família restante para sobreviver e sentar-se no trono.',
    'zh': '两兄弟在一场生死决斗中丧命。他们本共同统治王国，直到一场纷争使他们兵戎相见。二人各有一子，如今都是王位的继承者。\n\n对立两派的臣民决定将这两位堂兄弟继承人推入一场致命的角逐，以决出由谁掌权，并借他们年幼之机加以操纵，谋取私利。\n\n这两位身不由己的对手，由抚养他们、爱他们胜过自己生命的乳母相伴，被迫踏入一场毫不留情的追逐；为了生存并登上王位，他们甚至可能被迫杀死自己仅存的亲人。',
    'ja': '二人の兄弟が死闘の末に命を落とした。彼らは共に王国を治めていたが、ある対立が二人を争いへと駆り立てた。それぞれに息子がおり、今や王位の継承者である。\n\n対立する二つの陣営の民は、二人の従兄弟である後継者を死のレースへと追い込み、どちらが権力を握るかを決めさせ、その幼さにつけ込んで自分たちの都合のよいように操ろうと決めた。\n\n望まずして敵となった二人は、自らを育て、我が身以上に慈しんだ乳母たちに支えられながら、容赦なき追跡に身を投じることを余儀なくされる。生き延びて王座に就くために、唯一残された肉親を手にかけることさえ強いられるかもしれない。',
    'ko': '두 형제가 목숨을 건 결투 끝에 목숨을 잃었다. 그들은 함께 왕국을 다스렸으나, 한 번의 불화가 서로를 겨루게 만들었다. 각자에게 아들이 있었으니, 이제는 왕좌를 노리는 후계자들이다.\n\n대립하는 두 진영의 백성들은 두 사촌 후계자를 죽음의 경주로 몰아넣어 누가 권력을 쥘지 가리게 하고, 그들의 어린 나이를 이용해 자신들에게 유리하도록 조종하기로 했다.\n\n원치 않게 맞수가 된 두 사람은, 그들을 길러 내고 제 목숨보다 아꼈던 유모들의 도움을 받으며, 무자비한 추격에 나설 수밖에 없었다. 살아남아 왕좌에 앉기 위해, 남은 유일한 혈육마저 죽여야 할지도 모른다.',
    'ru': 'Два брата погибли в смертельном поединке. Они правили королевством вместе, пока раздор не заставил их сойтись в схватке. У каждого был сын — ныне претендент на трон.\n\nПодданные двух враждующих сторон решили толкнуть двоюродных братьев-наследников в смертельную гонку, чтобы определить, кто из них захватит власть, и, пользуясь их юностью, манипулировать ими в своих интересах.\n\nДвое невольных соперников, поддерживаемые няньками, что вырастили их и дорожили ими больше собственной жизни, оказались вынуждены вступить в беспощадную погоню и, быть может, даже будут принуждены убить единственную оставшуюся родню, чтобы выжить и взойти на трон.',
}


def story_text():
    """Renvoie l'histoire dans la langue courante (repli français)."""
    return STORY_I18N.get(LANG, STORY_TEXT)


_CA_PATH_CACHE = None


def _ca_bundle_path():
    """Renvoie un chemin de fichier de certificats racine UTILISABLE (pour la
    session requests du multijoueur). Sur Android, le fichier de certifi n'est
    pas toujours accessible par son chemin : dans ce cas, on écrit son contenu
    dans un fichier temporaire et on renvoie CE chemin."""
    global _CA_PATH_CACHE
    if _CA_PATH_CACHE is not None:
        return _CA_PATH_CACHE or None
    try:
        import certifi
        p = certifi.where()
        if p and os.path.exists(p):
            _CA_PATH_CACHE = p
            return p
        # Fichier inaccessible : on recopie le contenu dans un fichier temporaire.
        import tempfile
        data = certifi.contents()
        tmp = os.path.join(tempfile.gettempdir(), "lafuga_cacert.pem")
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(data)
        _CA_PATH_CACHE = tmp
        return tmp
    except Exception:
        _CA_PATH_CACHE = ""
        return None


def _online_ssl_context(unverified=False):
    """Contexte SSL pour les connexions HTTPS.
    - Par défaut : vérifie le certificat avec les certificats racine de certifi.
      On charge le CONTENU des certificats (plus fiable sur Android que passer
      un chemin de fichier, souvent inaccessible dans l'APK).
    - unverified=True : ne vérifie pas le certificat (repli ; reste chiffré)."""
    import ssl
    if unverified:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        return ctx
    ctx = ssl.create_default_context()
    try:
        import certifi
        try:
            # Charger les certificats par leur CONTENU (robuste sur Android).
            ctx.load_verify_locations(cadata=certifi.contents())
        except Exception:
            cp = _ca_bundle_path()
            if cp:
                ctx.load_verify_locations(cafile=cp)
    except Exception:
        pass
    return ctx


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
        self.melo = 1500          # mélo STANDARD
        self.melo_random = 1500   # mélo RANDOM FUGA
        self.theme = "original"   # thème enregistré côté serveur
        self.photo = ""           # photo de profil (mot theme|Pièce)

    def is_logged_in(self):
        return self.token is not None and self.pseudo is not None

    def logout(self):
        self.token = None
        self.pseudo = None
        self.melo = 1500
        self.melo_random = 1500
        self.theme = "original"
        self.photo = ""
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

            def _do(ctx):
                req = urllib.request.Request(
                    url, data=data,
                    headers={"Content-Type": "application/json"},
                    method="POST")
                try:
                    with urllib.request.urlopen(
                            req, timeout=15, context=ctx) as resp:
                        body = resp.read().decode("utf-8")
                        return (json.loads(body) if body else {}), None
                except urllib.error.HTTPError as e:
                    # Le serveur a répondu (code d'erreur) : on parse le JSON.
                    try:
                        body = e.read().decode("utf-8")
                        return (json.loads(body) if body else {}), None
                    except Exception:
                        return None, T("Erreur serveur (%d)") % e.code
                # URLError / SSLError : on laisse remonter (déclenche le repli).

            try:
                result, err = _do(_online_ssl_context())
            except Exception:
                # Repli sans vérification du certificat (Android manque parfois
                # des certificats racine). La connexion reste chiffrée.
                try:
                    result, err = _do(_online_ssl_context(unverified=True))
                except Exception as e2:
                    reason = str(getattr(e2, "reason", e2)) or str(e2)
                    result, err = None, T("Erreur réseau : ") + reason
            Clock.schedule_once(
                lambda dt, r=result, er=err: callback(r, er), 0)

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
                self.melo_random = result.get("melo_random", 1500)
                self.theme = _reconcile_theme(result.get("theme", "original"))
                save_online_session(self.token, self.pseudo, self.melo, self.melo_random)
                callback(True, T("Compte créé !"))
            else:
                callback(False, (result or {}).get("error", T("Erreur inconnue")))
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
                self.melo_random = result.get("melo_random", 1500)
                self.theme = _reconcile_theme(result.get("theme", "original"))
                self.photo = result.get("photo", "")   # si le serveur la renvoie
                self._fetch_my_photo()                  # sinon on la récupère
                save_online_session(self.token, self.pseudo, self.melo, self.melo_random)
                callback(True, T("Connecté !"))
            else:
                callback(False, (result or {}).get("error", T("Erreur inconnue")))
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
            self.melo_random = result.get("melo_random", 1500)
            self.theme = _reconcile_theme(result.get("theme", "original"))
            self.photo = result.get("photo", "")   # si le serveur la renvoie
            self._fetch_my_photo()                  # sinon on la récupère
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
        self._sio = None
        # Session HTTP avec les certificats de certifi (indispensable en HTTPS
        # sur Android, sinon la connexion temps réel échoue aussi).
        _kwargs = dict(reconnection=True,
                       reconnection_attempts=0,  # infini
                       logger=False, engineio_logger=False)
        try:
            import requests
            _sess = requests.Session()
            # Certificats racine (via un fichier accessible, cf _ca_bundle_path).
            # Si vraiment indisponible, on ne vérifie pas (connexion chiffrée).
            _ca = _ca_bundle_path()
            _sess.verify = _ca if _ca else False
            _kwargs["http_session"] = _sess
        except Exception:
            pass
        self._sio = _sio_lib.Client(**_kwargs)
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
                on_ready(False, T("Module réseau indisponible"))
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
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result, None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/search_user", {"token": self.token, "pseudo": pseudo}, on_resp)

    def add_favorite(self, pseudo, callback=None):
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/add_favorite", {"token": self.token, "pseudo": pseudo}, on_resp)

    def remove_favorite(self, pseudo, callback=None):
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/remove_favorite", {"token": self.token, "pseudo": pseudo}, on_resp)

    def list_favorites(self, callback):
        """callback(favorites_list_or_None, error)."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result.get("favorites", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/list_favorites", {"token": self.token}, on_resp)

    def block_user(self, pseudo, callback=None):
        """Bloque un joueur : plus de matchmaking ni de défi entre vous."""
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/block_user", {"token": self.token, "pseudo": pseudo}, on_resp)

    def unblock_user(self, pseudo, callback=None):
        """Débloque un joueur."""
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/unblock_user", {"token": self.token, "pseudo": pseudo}, on_resp)

    def list_blocked(self, callback):
        """callback(blocked_list_or_None, error). Les joueurs que j'ai bloqués."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result.get("blocked", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/list_blocked", {"token": self.token}, on_resp)

    def get_profile(self, pseudo, callback):
        """Profil d'un joueur (pseudo=None => le mien). callback(profile, error)."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result, None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/get_profile",
                   {"token": self.token, "pseudo": pseudo or ""}, on_resp)

    def _fetch_my_photo(self):
        """Charge ma photo de profil depuis le serveur (le login ne la renvoie pas)
        et la stocke dans self.photo, pour qu'elle soit prête partout dès l'entrée."""
        if not self.is_logged_in():
            return
        def on_prof(prof, err):
            if not err and prof is not None:
                self.photo = prof.get("photo", "") or ""
        try:
            self.get_profile(None, on_prof)
        except Exception:
            pass

    def set_photo(self, photo, callback=None):
        """Définit la photo de profil (mot 'theme|Pièce')."""
        self.photo = photo
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback: callback(bool(result and result.get("ok")), err)
        self._post("/set_photo", {"token": self.token, "photo": photo}, on_resp)

    def set_description(self, description, callback=None):
        """Définit la description du profil."""
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback: callback(bool(result and result.get("ok")), err)
        self._post("/set_description",
                   {"token": self.token, "description": description}, on_resp)

    def list_games(self, pseudo, callback):
        """Liste des parties (pseudo=None => les miennes). callback(games, error)."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result.get("games", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/list_games",
                   {"token": self.token, "pseudo": pseudo or ""}, on_resp)

    def send_message(self, pseudo, text, callback=None):
        """Envoie un message à un joueur (messagerie unifiée). callback(ok, err)."""
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/send_message",
                   {"token": self.token, "pseudo": pseudo, "text": text}, on_resp)

    def list_conversation(self, pseudo, callback):
        """Conversation avec un joueur. callback(messages_or_None, error)."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"):
                callback(result.get("messages", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/list_conversation",
                   {"token": self.token, "pseudo": pseudo}, on_resp)

    def list_conversations(self, callback):
        """Toutes mes conversations. callback(list_or_None, total_unread, error)."""
        if not self.is_logged_in():
            callback(None, 0, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, 0, err); return
            if result and result.get("ok"):
                callback(result.get("conversations", []),
                         result.get("total_unread", 0), None)
            else: callback(None, 0, (result or {}).get("error", "Erreur"))
        self._post("/list_conversations", {"token": self.token}, on_resp)

    def mark_read(self, pseudo, callback=None):
        """Marque comme lus les messages reçus d'un joueur. callback(ok, err)."""
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if callback:
                callback(bool(result and result.get("ok")),
                         err or (result or {}).get("error", ""))
        self._post("/mark_read", {"token": self.token, "pseudo": pseudo}, on_resp)

    def account_info(self, callback):
        """callback(info_dict_or_None, error). info = {pseudo, melo, email, notif}."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result, None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/account_info", {"token": self.token}, on_resp)

    def set_email(self, email, callback=None):
        """Change l'email du compte. callback(ok_bool, error)."""
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if not callback: return
            if err: callback(False, err); return
            if result and result.get("ok"): callback(True, None)
            else: callback(False, (result or {}).get("error", "Erreur"))
        self._post("/set_email", {"token": self.token, "email": email}, on_resp)

    def set_notif_prefs(self, prefs, callback=None):
        """Met à jour les préférences de notif. prefs = dict de booléens
        (mail, turn, msg, defi_corr, defi_direct). callback(ok_bool, error)."""
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if not callback: return
            if err: callback(False, err); return
            callback(bool(result and result.get("ok")), None)
        payload = {"token": self.token}
        payload.update(prefs)
        self._post("/set_notif_prefs", payload, on_resp)

    def set_theme(self, theme, callback=None):
        """Enregistre le thème sur le serveur (retrouvé à chaque connexion)."""
        self.theme = theme
        if not self.is_logged_in():
            if callback: callback(False, T("Non connecté"))
            return
        def on_resp(result, err):
            if not callback: return
            callback(bool(result and result.get("ok")), err)
        self._post("/set_theme", {"token": self.token, "theme": theme}, on_resp)

    def list_followers(self, callback):
        """callback(followers_list_or_None, error). Ceux qui m'ont en favori."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result.get("followers", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/list_followers", {"token": self.token}, on_resp)

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
            callback(None, T("Non connecté")); return
        def on_resp(result, err):
            if err: callback(None, err); return
            if result and result.get("ok"): callback(result.get("games", []), None)
            else: callback(None, (result or {}).get("error", "Erreur"))
        self._post("/corr_list", {"token": self.token}, on_resp)

    def corr_defier(self, pseudo, objectif, callback):
        """Défie un pote par correspondance. callback(result_dict, err)."""
        if not self.is_logged_in():
            callback(None, T("Non connecté")); return
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
            if callback: callback(False, T("Non connecté"))
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
            callback(None, T("Non connecté")); return
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
            callback(None, T("Non connecté")); return
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


def save_online_session(token, pseudo, melo, melo_random=None):
    """Sauvegarde la session dans config.txt pour reconnexion auto."""
    try:
        cfg = load_config()
        cfg["online_token"] = token or ""
        cfg["online_pseudo"] = pseudo or ""
        cfg["online_melo"] = str(melo or 1500)
        if melo_random is not None:
            cfg["online_melo_random"] = str(melo_random or 1500)
        save_config(cfg)
    except Exception:
        pass


def clear_online_session():
    """Supprime VRAIMENT les infos de connexion du config.txt. On réécrit le
    fichier en omettant les clés online (save_config ne peut pas supprimer une
    clé car il fusionne avec l'existant, d'où l'écriture directe ici)."""
    try:
        cfg = load_config()
        for k in ("online_token", "online_pseudo", "online_melo", "online_melo_random"):
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
    "deepgrey": {
        # Gris PILE au milieu (0.5) : tout ce qui était orange/bleu devient ce
        # gris dans l'appli. Les pièces ont un rendu spécial (voir draw_piece).
        "clair":     (0.5, 0.5, 0.5, 1),      # ex-orange -> gris médian
        "fonce":     (0.5, 0.5, 0.5, 1),      # ex-bleu   -> gris médian
        "clair_dim": (0.25, 0.25, 0.25, 1),
        "fonce_dim": (0.25, 0.25, 0.25, 1),
        "board":     (0.50, 0.50, 0.50, 1),   # remplacé par theme_deepgrey/plateau.png
        "menu":      (0.72, 0.72, 0.72, 1),   # remplacé par theme_deepgrey/fond.png
        "grid":      (0.40, 0.40, 0.40, 1),
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
               "arcenciel", "etoile", "medieval", "fleur", "insectes",
               "deepgrey"]
THEME_LABELS = {
    "original": "Original", "foret": "Forêt", "ocean": "Océan",
    "volcan": "Volcan", "hemo": "Hémo", "spatial": "Spatial",
    "imperial": "Impérial", "royal": "Royal",
    "terre": "Terre", "bonbon": "Bonbon",
    "arcenciel": "Arc-en-ciel", "etoile": "Étoile", "medieval": "Médiéval",
    "fleur": "Fleur", "insectes": "Insectes", "deepgrey": "Deep Grey",
}

CURRENT_THEME = "original"

# Mode Random Fuga (variante Fischer-random) : interrupteur global. Quand il est
# allumé, chaque nouvelle partie démarre sur une position aléatoire parmi 3500.
# Sauvegardé dans config.txt (clé "random_mode").
RANDOM_MODE = False

# Couleurs dynamiques (mises à jour par apply_theme)
COL_BG_MENU    = THEMES["original"]["menu"]
COL_MENU_BG    = THEMES["original"]["menu"]   # fond du menu (axe "fond menu")
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


# ── Système de langues (multilingue) ─────────────────────────────────────────
# Principe : la CLÉ d'une traduction est le texte FRANÇAIS d'origine. Pour le
# français, T(x) renvoie x tel quel. Pour les autres langues, il renvoie la
# traduction si elle existe, sinon le français (repli). Ainsi on peut traduire
# progressivement, écran par écran, sans jamais casser l'affichage.
LANG = "fr"
LANG_ORDER = ["fr", "en", "de", "es", "it", "zh", "ja", "ko", "ru", "pt"]
LANG_LABELS = {
    "fr": "Français", "en": "English", "de": "Deutsch", "es": "Español",
    "it": "Italiano", "zh": "中文", "ja": "日本語", "ko": "한국어",
    "ru": "Русский", "pt": "Português",
}

# Dictionnaire des traductions : { "texte français" : { "en": "...", ... } }.
# On le remplit progressivement. Le français n'a pas besoin d'y figurer.
TRANSLATIONS = {
    # ── Écran de connexion / inscription ──
    "< Menu": {"en": "< Menu", "de": "< Menü", "es": "< Menú", "it": "< Menu",
               "zh": "< 菜单", "ja": "< メニュー", "ko": "< 메뉴",
               "ru": "< Меню", "pt": "< Menu"},
    "Connexion": {"en": "Login", "de": "Anmeldung", "es": "Iniciar sesión",
                  "it": "Accesso", "zh": "登录", "ja": "ログイン", "ko": "로그인",
                  "ru": "Вход", "pt": "Entrar"},
    "Inscription": {"en": "Sign up", "de": "Registrierung", "es": "Registro",
                    "it": "Registrazione", "zh": "注册", "ja": "登録",
                    "ko": "회원가입", "ru": "Регистрация", "pt": "Cadastro"},
    "Pseudo": {"en": "Username", "de": "Benutzername", "es": "Usuario",
               "it": "Nome utente", "zh": "用户名", "ja": "ユーザー名",
               "ko": "사용자 이름", "ru": "Имя пользователя", "pt": "Usuário"},
    "Mot de passe": {"en": "Password", "de": "Passwort", "es": "Contraseña",
                     "it": "Password", "zh": "密码", "ja": "パスワード",
                     "ko": "비밀번호", "ru": "Пароль", "pt": "Senha"},
    "Email (optionnel)": {"en": "Email (optional)", "de": "E-Mail (optional)",
                          "es": "Correo (opcional)", "it": "Email (facoltativo)",
                          "zh": "电子邮件（可选）", "ja": "メール（任意）",
                          "ko": "이메일 (선택)", "ru": "Эл. почта (необязательно)",
                          "pt": "E-mail (opcional)"},
    "Se connecter": {"en": "Log in", "de": "Anmelden", "es": "Conectarse",
                     "it": "Accedi", "zh": "登录", "ja": "ログイン", "ko": "로그인",
                     "ru": "Войти", "pt": "Entrar"},
    "S'inscrire": {"en": "Register", "de": "Registrieren", "es": "Registrarse",
                   "it": "Registrati", "zh": "注册", "ja": "登録する",
                   "ko": "가입하기", "ru": "Зарегистрироваться", "pt": "Cadastrar"},
    "Pas encore inscrit ?": {"en": "Not registered yet?",
                             "de": "Noch nicht registriert?",
                             "es": "¿Aún no registrado?",
                             "it": "Non ancora registrato?",
                             "zh": "还没有账号？", "ja": "アカウントがありませんか？",
                             "ko": "아직 가입하지 않으셨나요?",
                             "ru": "Ещё не зарегистрированы?",
                             "pt": "Ainda não tem conta?"},
    "Déjà un compte ?": {"en": "Already have an account?",
                         "de": "Schon ein Konto?", "es": "¿Ya tienes una cuenta?",
                         "it": "Hai già un account?", "zh": "已有账号？",
                         "ja": "すでにアカウントをお持ちですか？",
                         "ko": "이미 계정이 있으신가요?", "ru": "Уже есть аккаунт?",
                         "pt": "Já tem uma conta?"},
    # ── Réglages : intitulé de la langue ──
    "Langue": {"en": "Language", "de": "Sprache", "es": "Idioma", "it": "Lingua",
               "zh": "语言", "ja": "言語", "ko": "언어", "ru": "Язык",
               "pt": "Idioma"},
    "J'ai déjà un compte": {"en": "I already have an account",
                            "de": "Ich habe bereits ein Konto",
                            "es": "Ya tengo una cuenta",
                            "it": "Ho già un account", "zh": "我已有账号",
                            "ja": "すでにアカウントを持っています",
                            "ko": "이미 계정이 있습니다", "ru": "У меня уже есть аккаунт",
                            "pt": "Já tenho uma conta"},
    "Créer le compte": {"en": "Create account", "de": "Konto erstellen",
                        "es": "Crear cuenta", "it": "Crea account", "zh": "创建账号",
                        "ja": "アカウントを作成", "ko": "계정 만들기",
                        "ru": "Создать аккаунт", "pt": "Criar conta"},
    "Pseudo et mot de passe requis": {
        "en": "Username and password required",
        "de": "Benutzername und Passwort erforderlich",
        "es": "Se requieren usuario y contraseña",
        "it": "Nome utente e password richiesti",
        "zh": "需要用户名和密码", "ja": "ユーザー名とパスワードが必要です",
        "ko": "사용자 이름과 비밀번호가 필요합니다",
        "ru": "Требуются имя пользователя и пароль",
        "pt": "Usuário e senha obrigatórios"},
    "Connexion au serveur...": {
        "en": "Connecting to server...", "de": "Verbinde mit Server...",
        "es": "Conectando al servidor...", "it": "Connessione al server...",
        "zh": "正在连接服务器...", "ja": "サーバーに接続中...",
        "ko": "서버에 연결 중...", "ru": "Подключение к серверу...",
        "pt": "Conectando ao servidor..."},
}


TRANSLATIONS.update({
    'Accepter': {'en': 'Accept', 'de': 'Annehmen', 'es': 'Aceptar', 'it': 'Accetta', 'zh': '接受', 'ja': '承諾', 'ko': '수락', 'ru': 'Принять', 'pt': 'Aceitar'},
    'Actualiser': {'en': 'Refresh', 'de': 'Aktualisieren', 'es': 'Actualizar', 'it': 'Aggiorna', 'zh': '刷新', 'ja': '更新', 'ko': '새로고침', 'ru': 'Обновить', 'pt': 'Atualizar'},
    'Aléatoire': {'en': 'Random', 'de': 'Zufällig', 'es': 'Aleatorio', 'it': 'Casuale', 'zh': '随机', 'ja': 'ランダム', 'ko': '무작위', 'ru': 'Случайно', 'pt': 'Aleatório'},
    'Annuler': {'en': 'Cancel', 'de': 'Abbrechen', 'es': 'Cancelar', 'it': 'Annulla', 'zh': '取消', 'ja': 'キャンセル', 'ko': '취소', 'ru': 'Отмена', 'pt': 'Cancelar'},
    'Cadence (min / joueur)': {'en': 'Time (min / player)', 'de': 'Zeit (Min / Spieler)', 'es': 'Tiempo (min / jugador)', 'it': 'Tempo (min / giocatore)', 'zh': '时间（分钟/玩家）', 'ja': '持ち時間（分/人）', 'ko': '시간 (분/사람)', 'ru': 'Время (мин / игрок)', 'pt': 'Tempo (min / jogador)'},
    'Chargement…': {'en': 'Loading…', 'de': 'Lädt…', 'es': 'Cargando…', 'it': 'Caricamento…', 'zh': '加载中…', 'ja': '読み込み中…', 'ko': '불러오는 중…', 'ru': 'Загрузка…', 'pt': 'Carregando…'},
    'Choisissez votre couleur': {'en': 'Choose your color', 'de': 'Wähle deine Farbe', 'es': 'Elige tu color', 'it': 'Scegli il tuo colore', 'zh': '选择你的颜色', 'ja': '色を選んでください', 'ko': '색을 선택하세요', 'ru': 'Выберите цвет', 'pt': 'Escolha sua cor'},
    'Compte': {'en': 'Account', 'de': 'Konto', 'es': 'Cuenta', 'it': 'Account', 'zh': '账号', 'ja': 'アカウント', 'ko': '계정', 'ru': 'Аккаунт', 'pt': 'Conta'},
    'Défier': {'en': 'Challenge', 'de': 'Herausfordern', 'es': 'Desafiar', 'it': 'Sfida', 'zh': '挑战', 'ja': '挑戦', 'ko': '도전', 'ru': 'Вызов', 'pt': 'Desafiar'},
    'En attente…': {'en': 'Waiting…', 'de': 'Warten…', 'es': 'Esperando…', 'it': 'In attesa…', 'zh': '等待中…', 'ja': '待機中…', 'ko': '대기 중…', 'ru': 'Ожидание…', 'pt': 'Aguardando…'},
    'Fermer': {'en': 'Close', 'de': 'Schließen', 'es': 'Cerrar', 'it': 'Chiudi', 'zh': '关闭', 'ja': '閉じる', 'ko': '닫기', 'ru': 'Закрыть', 'pt': 'Fechar'},
    'Jouer avec les Blancs': {'en': 'Play as White', 'de': 'Weiß spielen', 'es': 'Jugar con Blancas', 'it': 'Gioca col Bianco', 'zh': '执白方', 'ja': '白でプレイ', 'ko': '백으로 플레이', 'ru': 'Играть белыми', 'pt': 'Jogar de Brancas'},
    'Jouer avec les Noirs': {'en': 'Play as Black', 'de': 'Schwarz spielen', 'es': 'Jugar con Negras', 'it': 'Gioca col Nero', 'zh': '执黑方', 'ja': '黒でプレイ', 'ko': '흑으로 플레이', 'ru': 'Играть чёрными', 'pt': 'Jogar de Pretas'},
    "L'histoire de La Fuga": {'en': 'The story of La Fuga', 'de': 'Die Geschichte von La Fuga', 'es': 'La historia de La Fuga', 'it': 'La storia di La Fuga', 'zh': 'La Fuga 的故事', 'ja': 'La Fuga の物語', 'ko': 'La Fuga 이야기', 'ru': 'История La Fuga', 'pt': 'A história de La Fuga'},
    'Mes favoris': {'en': 'My favorites', 'de': 'Meine Favoriten', 'es': 'Mis favoritos', 'it': 'I miei preferiti', 'zh': '我的收藏', 'ja': 'お気に入り', 'ko': '즐겨찾기', 'ru': 'Избранное', 'pt': 'Meus favoritos'},
    'Objectif': {'en': 'Objective', 'de': 'Ziel', 'es': 'Objetivo', 'it': 'Obiettivo', 'zh': '目标', 'ja': '目標', 'ko': '목표', 'ru': 'Цель', 'pt': 'Objetivo'},
    'Parties par correspondance': {'en': 'Correspondence games', 'de': 'Fernpartien', 'es': 'Partidas por correspondencia', 'it': 'Partite per corrispondenza', 'zh': '通信对局', 'ja': '通信対局', 'ko': '통신 대국', 'ru': 'Игры по переписке', 'pt': 'Partidas por correspondência'},
    'Rechercher un joueur…': {'en': 'Search for a player…', 'de': 'Spieler suchen…', 'es': 'Buscar un jugador…', 'it': 'Cerca un giocatore…', 'zh': '搜索玩家…', 'ja': 'プレイヤーを検索…', 'ko': '플레이어 검색…', 'ru': 'Найти игрока…', 'pt': 'Procurar um jogador…'},
    'Refuser': {'en': 'Decline', 'de': 'Ablehnen', 'es': 'Rechazar', 'it': 'Rifiuta', 'zh': '拒绝', 'ja': '辞退', 'ko': '거절', 'ru': 'Отклонить', 'pt': 'Recusar'},
    'Retirer': {'en': 'Remove', 'de': 'Entfernen', 'es': 'Quitar', 'it': 'Rimuovi', 'zh': '移除', 'ja': '削除', 'ko': '제거', 'ru': 'Убрать', 'pt': 'Remover'},
    'Revanche': {'en': 'Rematch', 'de': 'Revanche', 'es': 'Revancha', 'it': 'Rivincita', 'zh': '再战', 'ja': '再戦', 'ko': '재대국', 'ru': 'Реванш', 'pt': 'Revanche'},
    'Se déconnecter': {'en': 'Log out', 'de': 'Abmelden', 'es': 'Cerrar sesión', 'it': 'Disconnetti', 'zh': '退出登录', 'ja': 'ログアウト', 'ko': '로그아웃', 'ru': 'Выйти', 'pt': 'Sair'},
    'Défi refusé': {'en': 'Challenge declined', 'de': 'Herausforderung abgelehnt', 'es': 'Desafío rechazado', 'it': 'Sfida rifiutata', 'zh': '挑战被拒绝', 'ja': '挑戦が辞退されました', 'ko': '도전이 거절됨', 'ru': 'Вызов отклонён', 'pt': 'Desafio recusado'},
    'Bientôt': {'en': 'Soon', 'de': 'Bald', 'es': 'Pronto', 'it': 'Presto', 'zh': '即将推出', 'ja': '近日公開', 'ko': '곧 출시', 'ru': 'Скоро', 'pt': 'Em breve'},
    'Défier un favori\n(par correspondance)': {'en': 'Challenge a favorite\n(by correspondence)', 'de': 'Favorit herausfordern\n(per Fernpartie)', 'es': 'Desafiar a un favorito\n(por correspondencia)', 'it': 'Sfida un preferito\n(per corrispondenza)', 'zh': '挑战收藏的玩家\n（通信对局）', 'ja': 'お気に入りに挑戦\n（通信対局）', 'ko': '즐겨찾기에 도전\n(통신 대국)', 'ru': 'Вызвать из избранного\n(по переписке)', 'pt': 'Desafiar um favorito\n(por correspondência)'},
    "Le mode en ligne n'est pas\nencore disponible.": {'en': 'Online mode is not\navailable yet.', 'de': 'Der Online-Modus ist noch\nnicht verfügbar.', 'es': 'El modo en línea aún\nno está disponible.', 'it': 'La modalità online non è\nancora disponibile.', 'zh': '在线模式尚未\n开放。', 'ja': 'オンラインモードはまだ\n利用できません。', 'ko': '온라인 모드는 아직\n이용할 수 없습니다.', 'ru': 'Онлайн-режим пока\nнедоступен.', 'pt': 'O modo online ainda\nnão está disponível.'},
    'Merci de soutenir le développement de La Fuga !\n': {'en': 'Thank you for supporting the development of La Fuga!\n', 'de': 'Danke, dass du die Entwicklung von La Fuga unterstützt!\n', 'es': '¡Gracias por apoyar el desarrollo de La Fuga!\n', 'it': 'Grazie per supportare lo sviluppo di La Fuga!\n', 'zh': '感谢您支持 La Fuga 的开发！\n', 'ja': 'La Fuga の開発を応援していただきありがとうございます！\n', 'ko': 'La Fuga 개발을 응원해 주셔서 감사합니다!\n', 'ru': 'Спасибо за поддержку разработки La Fuga!\n', 'pt': 'Obrigado por apoiar o desenvolvimento de La Fuga!\n'},
    'Aucun favori.\nAjoutez des favoris via la recherche.': {'en': 'No favorites.\nAdd favorites via search.', 'de': 'Keine Favoriten.\nFüge Favoriten über die Suche hinzu.', 'es': 'Sin favoritos.\nAgrega favoritos mediante la búsqueda.', 'it': 'Nessun preferito.\nAggiungi preferiti tramite la ricerca.', 'zh': '暂无收藏。\n通过搜索添加收藏。', 'ja': 'お気に入りがありません。\n検索から追加してください。', 'ko': '즐겨찾기가 없습니다.\n검색으로 추가하세요.', 'ru': 'Нет избранного.\nДобавьте через поиск.', 'pt': 'Sem favoritos.\nAdicione favoritos pela busca.'},
})

TRANSLATIONS.update({
    "Votre aide compte beaucoup.": {
        "en": "Your help means a lot.", "de": "Deine Hilfe bedeutet viel.",
        "es": "Tu ayuda significa mucho.", "it": "Il tuo aiuto conta molto.",
        "zh": "你的帮助意义重大。", "ja": "あなたの支援がとても力になります。",
        "ko": "여러분의 도움이 큰 힘이 됩니다.", "ru": "Ваша помощь очень важна.",
        "pt": "Sua ajuda significa muito."},
})


TRANSLATIONS.update({
    'Volume': {'en': 'Volume', 'de': 'Lautstärke', 'es': 'Volumen', 'it': 'Volume', 'zh': '音量', 'ja': '音量', 'ko': '볼륨', 'ru': 'Громкость', 'pt': 'Volume'},
    'Réglages': {'en': 'Settings', 'de': 'Einstellungen', 'es': 'Ajustes', 'it': 'Impostazioni', 'zh': '设置', 'ja': '設定', 'ko': '설정', 'ru': 'Настройки', 'pt': 'Configurações'},
    'Thème': {'en': 'Theme', 'de': 'Thema', 'es': 'Tema', 'it': 'Tema', 'zh': '主题', 'ja': 'テーマ', 'ko': '테마', 'ru': 'Тема', 'pt': 'Tema'},
    'Vitesse de glissée des pièces': {'en': 'Piece sliding speed', 'de': 'Gleitgeschwindigkeit der Steine', 'es': 'Velocidad de deslizamiento', 'it': 'Velocità di scorrimento', 'zh': '棋子滑动速度', 'ja': '駒のスライド速度', 'ko': '말 이동 속도', 'ru': 'Скорость скольжения фишек', 'pt': 'Velocidade de deslize das peças'},
    'Appliquer ce thème': {'en': 'Apply this theme', 'de': 'Dieses Thema anwenden', 'es': 'Aplicar este tema', 'it': 'Applica questo tema', 'zh': '应用此主题', 'ja': 'このテーマを適用', 'ko': '이 테마 적용', 'ru': 'Применить тему', 'pt': 'Aplicar este tema'},
    'Valider la langue': {'en': 'Apply language', 'de': 'Sprache übernehmen', 'es': 'Aplicar idioma', 'it': 'Applica lingua', 'zh': '应用语言', 'ja': '言語を適用', 'ko': '언어 적용', 'ru': 'Применить язык', 'pt': 'Aplicar idioma'},
})


TRANSLATIONS.update({
    '< Historique': {'en': '< History', 'de': '< Verlauf', 'es': '< Historial', 'it': '< Cronologia', 'zh': '< 历史', 'ja': '< 履歴', 'ko': '< 기록', 'ru': '< История', 'pt': '< Histórico'},
    'Historique': {'en': 'History', 'de': 'Verlauf', 'es': 'Historial', 'it': 'Cronologia', 'zh': '历史', 'ja': '履歴', 'ko': '기록', 'ru': 'История', 'pt': 'Histórico'},
    'Historique en ligne': {'en': 'Online history', 'de': 'Online-Verlauf', 'es': 'Historial en línea', 'it': 'Cronologia online', 'zh': '在线历史', 'ja': 'オンライン履歴', 'ko': '온라인 기록', 'ru': 'История онлайн', 'pt': 'Histórico online'},
    'Historique en local': {'en': 'Local history', 'de': 'Lokaler Verlauf', 'es': 'Historial local', 'it': 'Cronologia locale', 'zh': '本地历史', 'ja': 'ローカル履歴', 'ko': '로컬 기록', 'ru': 'Локальная история', 'pt': 'Histórico local'},
    'Lecteur nmc': {'en': 'nmc reader', 'de': 'nmc-Leser', 'es': 'Lector nmc', 'it': 'Lettore nmc', 'zh': 'nmc 阅读器', 'ja': 'nmc ビューア', 'ko': 'nmc 뷰어', 'ru': 'Просмотр nmc', 'pt': 'Leitor nmc'},
    'En ligne': {'en': 'Online', 'de': 'Online', 'es': 'En línea', 'it': 'Online', 'zh': '在线', 'ja': 'オンライン', 'ko': '온라인', 'ru': 'Онлайн', 'pt': 'Online'},
    'En local': {'en': 'Local', 'de': 'Lokal', 'es': 'Local', 'it': 'Locale', 'zh': '本地', 'ja': 'ローカル', 'ko': '로컬', 'ru': 'Локально', 'pt': 'Local'},
    'Copier': {'en': 'Copy', 'de': 'Kopieren', 'es': 'Copiar', 'it': 'Copia', 'zh': '复制', 'ja': 'コピー', 'ko': '복사', 'ru': 'Копировать', 'pt': 'Copiar'},
    'Erreur': {'en': 'Error', 'de': 'Fehler', 'es': 'Error', 'it': 'Errore', 'zh': '错误', 'ja': 'エラー', 'ko': '오류', 'ru': 'Ошибка', 'pt': 'Erro'},
    'Partie La Fuga': {'en': 'La Fuga game', 'de': 'La Fuga (Partie)', 'es': 'Partida de La Fuga', 'it': 'Partita di La Fuga', 'zh': 'La Fuga 对局', 'ja': 'La Fuga の対局', 'ko': 'La Fuga 대국', 'ru': 'Партия La Fuga', 'pt': 'Partida de La Fuga'},
    'Contenu .nmc': {'en': '.nmc content', 'de': '.nmc-Inhalt', 'es': 'Contenido .nmc', 'it': 'Contenuto .nmc', 'zh': '.nmc 内容', 'ja': '.nmc の内容', 'ko': '.nmc 내용', 'ru': 'Содержимое .nmc', 'pt': 'Conteúdo .nmc'},
    'Connectez-vous à un compte\npour voir vos parties en ligne.': {'en': 'Log in to an account\nto see your online games.', 'de': 'Melde dich an,\num deine Online-Partien zu sehen.', 'es': 'Inicia sesión\npara ver tus partidas en línea.', 'it': 'Accedi a un account\nper vedere le tue partite online.', 'zh': '登录账号\n以查看你的在线对局。', 'ja': 'アカウントにログインすると\nオンライン対局を表示できます。', 'ko': '계정에 로그인하면\n온라인 대국을 볼 수 있습니다.', 'ru': 'Войдите в аккаунт,\nчтобы видеть онлайн-партии.', 'pt': 'Entre em uma conta\npara ver seus jogos online.'},
    'Connectez-vous pour voir vos parties en ligne.': {'en': 'Log in to see your online games.', 'de': 'Melde dich an, um deine Online-Partien zu sehen.', 'es': 'Inicia sesión para ver tus partidas en línea.', 'it': 'Accedi per vedere le tue partite online.', 'zh': '登录以查看你的在线对局。', 'ja': 'ログインしてオンライン対局を表示。', 'ko': '로그인하여 온라인 대국을 보세요.', 'ru': 'Войдите, чтобы видеть онлайн-партии.', 'pt': 'Entre para ver seus jogos online.'},
    'Aucune partie en ligne.\nJouez une partie en ligne pour la voir ici !': {'en': 'No online games.\nPlay an online game to see it here!', 'de': 'Keine Online-Partien.\nSpiele eine Online-Partie, um sie hier zu sehen!', 'es': 'Sin partidas en línea.\n¡Juega una partida en línea para verla aquí!', 'it': 'Nessuna partita online.\nGioca una partita online per vederla qui!', 'zh': '暂无在线对局。\n进行一局在线对局即可在此查看！', 'ja': 'オンライン対局がありません。\nオンラインで対局するとここに表示されます！', 'ko': '온라인 대국이 없습니다.\n온라인 대국을 하면 여기에 표시됩니다!', 'ru': 'Нет онлайн-партий.\nСыграйте онлайн, чтобы увидеть её здесь!', 'pt': 'Nenhum jogo online.\nJogue uma partida online para vê-la aqui!'},
    'Chargement des parties en ligne…': {'en': 'Loading online games…', 'de': 'Lade Online-Partien…', 'es': 'Cargando partidas en línea…', 'it': 'Caricamento partite online…', 'zh': '正在加载在线对局…', 'ja': 'オンライン対局を読み込み中…', 'ko': '온라인 대국 불러오는 중…', 'ru': 'Загрузка онлайн-партий…', 'pt': 'Carregando jogos online…'},
    "Impossible de charger l'historique\n(%s)": {'en': 'Cannot load history\n(%s)', 'de': 'Verlauf kann nicht geladen werden\n(%s)', 'es': 'No se puede cargar el historial\n(%s)', 'it': 'Impossibile caricare la cronologia\n(%s)', 'zh': '无法加载历史\n(%s)', 'ja': '履歴を読み込めません\n(%s)', 'ko': '기록을 불러올 수 없습니다\n(%s)', 'ru': 'Не удалось загрузить историю\n(%s)', 'pt': 'Não foi possível carregar o histórico\n(%s)'},
    "Aucune partie locale.\nJouez en local ou contre l'IA pour la voir ici !": {'en': 'No local games.\nPlay locally or vs AI to see it here!', 'de': 'Keine lokalen Partien.\nSpiele lokal oder gegen die KI, um sie hier zu sehen!', 'es': 'Sin partidas locales.\n¡Juega en local o contra la IA para verla aquí!', 'it': "Nessuna partita locale.\nGioca in locale o contro l'IA per vederla qui!", 'zh': '暂无本地对局。\n进行本地或人机对局即可在此查看！', 'ja': 'ローカル対局がありません。\nローカルまたはAI対戦でここに表示されます！', 'ko': '로컬 대국이 없습니다.\n로컬 또는 AI 대국을 하면 표시됩니다!', 'ru': 'Нет локальных партий.\nСыграйте локально или против ИИ!', 'pt': 'Nenhum jogo local.\nJogue localmente ou contra a IA para vê-la aqui!'},
    'Impossible de charger la partie.': {'en': 'Cannot load the game.', 'de': 'Partie kann nicht geladen werden.', 'es': 'No se puede cargar la partida.', 'it': 'Impossibile caricare la partita.', 'zh': '无法加载对局。', 'ja': '対局を読み込めません。', 'ko': '대국을 불러올 수 없습니다.', 'ru': 'Не удалось загрузить партию.', 'pt': 'Não foi possível carregar a partida.'},
    'Sélectionnez tout le texte ci-dessous,\npuis copiez-le.': {'en': 'Select all the text below,\nthen copy it.', 'de': 'Markiere den gesamten Text unten\nund kopiere ihn.', 'es': 'Selecciona todo el texto de abajo\ny cópialo.', 'it': 'Seleziona tutto il testo qui sotto,\npoi copialo.', 'zh': '选择下方全部文本，\n然后复制。', 'ja': '下のテキストをすべて選択して\nコピーしてください。', 'ko': '아래 텍스트를 모두 선택한 뒤\n복사하세요.', 'ru': 'Выделите весь текст ниже\nи скопируйте.', 'pt': 'Selecione todo o texto abaixo\ne copie-o.'},
    'désolé, le fichier nmc est invalide,\nla lecture ne peut pas s effectuer': {'en': 'sorry, the nmc file is invalid,\nit cannot be read', 'de': 'Entschuldigung, die nmc-Datei ist ungültig,\nsie kann nicht gelesen werden', 'es': 'lo sentimos, el archivo nmc no es válido,\nno se puede leer', 'it': 'spiacenti, il file nmc non è valido,\nnon può essere letto', 'zh': '抱歉，nmc 文件无效，\n无法读取', 'ja': '申し訳ありません、nmc ファイルが無効で\n読み込めません', 'ko': '죄송합니다, nmc 파일이 잘못되어\n읽을 수 없습니다', 'ru': 'извините, файл nmc недействителен,\nчтение невозможно', 'pt': 'desculpe, o arquivo nmc é inválido,\nnão pode ser lido'},
})


TRANSLATIONS.update({
    'Analyser': {'en': 'Analyze', 'de': 'Analysieren', 'es': 'Analizar', 'it': 'Analizza', 'zh': '分析', 'ja': '解析', 'ko': '분석', 'ru': 'Анализ', 'pt': 'Analisar'},
    'Blancs': {'en': 'White', 'de': 'Weiß', 'es': 'Blancas', 'it': 'Bianco', 'zh': '白方', 'ja': '白', 'ko': '백', 'ru': 'Белые', 'pt': 'Brancas'},
    'Noirs': {'en': 'Black', 'de': 'Schwarz', 'es': 'Negras', 'it': 'Nero', 'zh': '黑方', 'ja': '黒', 'ko': '흑', 'ru': 'Чёрные', 'pt': 'Pretas'},
    'Chat': {'en': 'Chat', 'de': 'Chat', 'es': 'Chat', 'it': 'Chat', 'zh': '聊天', 'ja': 'チャット', 'ko': '채팅', 'ru': 'Чат', 'pt': 'Chat'},
    'Envoyer': {'en': 'Send', 'de': 'Senden', 'es': 'Enviar', 'it': 'Invia', 'zh': '发送', 'ja': '送信', 'ko': '보내기', 'ru': 'Отправить', 'pt': 'Enviar'},
    'Joueur 1': {'en': 'Player 1', 'de': 'Spieler 1', 'es': 'Jugador 1', 'it': 'Giocatore 1', 'zh': '玩家 1', 'ja': 'プレイヤー1', 'ko': '플레이어 1', 'ru': 'Игрок 1', 'pt': 'Jogador 1'},
    'Joueur 2': {'en': 'Player 2', 'de': 'Spieler 2', 'es': 'Jugador 2', 'it': 'Giocatore 2', 'zh': '玩家 2', 'ja': 'プレイヤー2', 'ko': '플레이어 2', 'ru': 'Игрок 2', 'pt': 'Jogador 2'},
    'Match nul': {'en': 'Draw', 'de': 'Unentschieden', 'es': 'Tablas', 'it': 'Patta', 'zh': '平局', 'ja': '引き分け', 'ko': '무승부', 'ru': 'Ничья', 'pt': 'Empate'},
    'Mise à jour du mélo…': {'en': 'Updating Mélo…', 'de': 'Mélo wird aktualisiert…', 'es': 'Actualizando Mélo…', 'it': 'Aggiornamento Mélo…', 'zh': '正在更新 Mélo…', 'ja': 'Mélo を更新中…', 'ko': 'Mélo 업데이트 중…', 'ru': 'Обновление Mélo…', 'pt': 'Atualizando Mélo…'},
    'Partie suivante': {'en': 'Next game', 'de': 'Nächste Partie', 'es': 'Siguiente partida', 'it': 'Partita successiva', 'zh': '下一局', 'ja': '次の対局', 'ko': '다음 대국', 'ru': 'Следующая партия', 'pt': 'Próxima partida'},
    'Quitter le match': {'en': 'Quit match', 'de': 'Match verlassen', 'es': 'Salir del match', 'it': 'Abbandona il match', 'zh': '退出比赛', 'ja': 'マッチを退出', 'ko': '매치 나가기', 'ru': 'Выйти из матча', 'pt': 'Sair da partida'},
    'Retour au menu': {'en': 'Back to menu', 'de': 'Zurück zum Menü', 'es': 'Volver al menú', 'it': 'Torna al menu', 'zh': '返回菜单', 'ja': 'メニューに戻る', 'ko': '메뉴로 돌아가기', 'ru': 'В меню', 'pt': 'Voltar ao menu'},
    'Votre message…': {'en': 'Your message…', 'de': 'Deine Nachricht…', 'es': 'Tu mensaje…', 'it': 'Il tuo messaggio…', 'zh': '你的消息…', 'ja': 'メッセージ…', 'ko': '메시지…', 'ru': 'Ваше сообщение…', 'pt': 'Sua mensagem…'},
    'Clique sur « Partie suivante » pour continuer le match.': {'en': 'Tap “Next game” to continue the match.', 'de': 'Tippe auf „Nächste Partie“, um das Match fortzusetzen.', 'es': 'Pulsa «Siguiente partida» para continuar el match.', 'it': 'Tocca «Partita successiva» per continuare il match.', 'zh': '点击“下一局”继续比赛。', 'ja': '「次の対局」を押してマッチを続けます。', 'ko': '“다음 대국”을 눌러 매치를 계속하세요.', 'ru': 'Нажмите «Следующая партия», чтобы продолжить матч.', 'pt': 'Toque em «Próxima partida» para continuar.'},
    'Jouer contre Deep Grey depuis cette position.\n': {'en': 'Play against Deep Grey from this position.\n', 'de': 'Ab dieser Stellung gegen Deep Grey spielen.\n', 'es': 'Jugar contra Deep Grey desde esta posición.\n', 'it': 'Gioca contro Deep Grey da questa posizione.\n', 'zh': '从此局面对战 Deep Grey。\n', 'ja': 'この局面から Deep Grey と対戦。\n', 'ko': '이 위치에서 Deep Grey와 대국.\n', 'ru': 'Играть против Deep Grey с этой позиции.\n', 'pt': 'Jogar contra Deep Grey a partir desta posição.\n'},
    'Proposition de nulle envoyée\nà votre adversaire.': {'en': 'Draw offer sent\nto your opponent.', 'de': 'Remisangebot an deinen\nGegner gesendet.', 'es': 'Oferta de tablas enviada\na tu rival.', 'it': 'Offerta di patta inviata\nal tuo avversario.', 'zh': '和棋提议已发送\n给对手。', 'ja': '引き分けの申し出を\n相手に送信しました。', 'ko': '무승부 제안을\n상대에게 보냈습니다.', 'ru': 'Предложение ничьей\nотправлено сопернику.', 'pt': 'Oferta de empate enviada\nao seu adversário.'},
    '%s propose la nulle.': {'en': '%s offers a draw.', 'de': '%s bietet Remis an.', 'es': '%s ofrece tablas.', 'it': '%s propone la patta.', 'zh': '%s 提议和棋。', 'ja': '%s が引き分けを提案。', 'ko': '%s 님이 무승부를 제안합니다.', 'ru': '%s предлагает ничью.', 'pt': '%s propõe empate.'},
    '%s propose une partie nulle.': {'en': '%s offers a draw.', 'de': '%s bietet ein Unentschieden an.', 'es': '%s ofrece unas tablas.', 'it': '%s propone una patta.', 'zh': '%s 提议和棋。', 'ja': '%s が引き分けを提案します。', 'ko': '%s 님이 무승부를 제안합니다.', 'ru': '%s предлагает ничью.', 'pt': '%s propõe um empate.'},
    'Mélo : %d  (%s%d)': {'en': 'Mélo: %d  (%s%d)', 'de': 'Mélo: %d  (%s%d)', 'es': 'Mélo: %d  (%s%d)', 'it': 'Mélo: %d  (%s%d)', 'zh': 'Mélo：%d  (%s%d)', 'ja': 'Mélo：%d  (%s%d)', 'ko': 'Mélo: %d  (%s%d)', 'ru': 'Mélo: %d  (%s%d)', 'pt': 'Mélo: %d  (%s%d)'},
})


TRANSLATIONS.update({
    'Choisissez votre camp :': {'en': 'Choose your side:', 'de': 'Wähle deine Seite:', 'es': 'Elige tu bando:', 'it': 'Scegli la tua parte:', 'zh': '选择你的一方：', 'ja': '陣営を選んでください：', 'ko': '진영을 선택하세요:', 'ru': 'Выберите сторону:', 'pt': 'Escolha seu lado:'},
})


TRANSLATIONS.update({
    'Aucun point accordé.': {'en': 'No points awarded.', 'de': 'Keine Punkte vergeben.', 'es': 'No se otorgan puntos.', 'it': 'Nessun punto assegnato.', 'zh': '不计分。', 'ja': 'ポイントなし。', 'ko': '점수 없음.', 'ru': 'Очки не начислены.', 'pt': 'Nenhum ponto concedido.'},
    "L'adversaire est prêt !\n": {'en': 'Your opponent is ready!\n', 'de': 'Dein Gegner ist bereit!\n', 'es': '¡Tu rival está listo!\n', 'it': 'Il tuo avversario è pronto!\n', 'zh': '对手已准备好！\n', 'ja': '相手の準備ができました！\n', 'ko': '상대가 준비되었습니다!\n', 'ru': 'Соперник готов!\n', 'pt': 'Seu adversário está pronto!\n'},
    "La même position s'est répétée 4 fois.\n\n": {'en': 'The same position has occurred 4 times.\n\n', 'de': 'Dieselbe Stellung trat 4 Mal auf.\n\n', 'es': 'La misma posición se ha repetido 4 veces.\n\n', 'it': 'La stessa posizione si è ripetuta 4 volte.\n\n', 'zh': '同一局面已出现 4 次。\n\n', 'ja': '同じ局面が4回現れました。\n\n', 'ko': '같은 위치가 4번 나왔습니다.\n\n', 'ru': 'Одна и та же позиция возникла 4 раза.\n\n', 'pt': 'A mesma posição ocorreu 4 vezes.\n\n'},
    'Les deux Héritiers ont fugué.\nAucun point accordé.': {'en': 'Both Heirs have fled.\nNo points awarded.', 'de': 'Beide Erben sind geflohen.\nKeine Punkte vergeben.', 'es': 'Ambos Herederos han huido.\nNo se otorgan puntos.', 'it': 'Entrambi gli Eredi sono fuggiti.\nNessun punto assegnato.', 'zh': '两位继承人都逃脱了。\n不计分。', 'ja': '両方の跡継ぎが逃げ切りました。\nポイントなし。', 'ko': '두 후계자가 모두 도망쳤습니다.\n점수 없음.', 'ru': 'Оба Наследника сбежали.\nОчки не начислены.', 'pt': 'Ambos os Herdeiros fugiram.\nNenhum ponto concedido.'},
    'Match gagné': {'en': 'Match won', 'de': 'Match gewonnen', 'es': 'Match ganado', 'it': 'Match vinto', 'zh': '比赛胜利', 'ja': 'マッチ勝利', 'ko': '매치 승리', 'ru': 'Матч выигран', 'pt': 'Partida vencida'},
    'Match nul par répétition': {'en': 'Draw by repetition', 'de': 'Remis durch Wiederholung', 'es': 'Tablas por repetición', 'it': 'Patta per ripetizione', 'zh': '重复局面和棋', 'ja': '同形反復で引き分け', 'ko': '반복으로 무승부', 'ru': 'Ничья по повторению', 'pt': 'Empate por repetição'},
    'Match terminé': {'en': 'Match over', 'de': 'Match beendet', 'es': 'Match terminado', 'it': 'Match concluso', 'zh': '比赛结束', 'ja': 'マッチ終了', 'ko': '매치 종료', 'ru': 'Матч окончен', 'pt': 'Partida encerrada'},
    'Nulle par accord mutuel.\nAucun point accordé.': {'en': 'Draw by mutual agreement.\nNo points awarded.', 'de': 'Remis durch gegenseitige Einigung.\nKeine Punkte vergeben.', 'es': 'Tablas por acuerdo mutuo.\nNo se otorgan puntos.', 'it': 'Patta per accordo reciproco.\nNessun punto assegnato.', 'zh': '双方同意和棋。\n不计分。', 'ja': '合意により引き分け。\nポイントなし。', 'ko': '합의로 무승부.\n점수 없음.', 'ru': 'Ничья по соглашению.\nОчки не начислены.', 'pt': 'Empate por acordo mútuo.\nNenhum ponto concedido.'},
    'Nulle proposée': {'en': 'Draw offered', 'de': 'Remis angeboten', 'es': 'Tablas ofrecidas', 'it': 'Patta proposta', 'zh': '提议和棋', 'ja': '引き分けの提案', 'ko': '무승부 제안', 'ru': 'Предложена ничья', 'pt': 'Empate proposto'},
    'Partie terminée': {'en': 'Game over', 'de': 'Partie beendet', 'es': 'Partida terminada', 'it': 'Partita finita', 'zh': '对局结束', 'ja': '対局終了', 'ko': '대국 종료', 'ru': 'Партия окончена', 'pt': 'Partida encerrada'},
    'Temps écoulé…': {'en': "Time's up…", 'de': 'Zeit abgelaufen…', 'es': 'Tiempo agotado…', 'it': 'Tempo scaduto…', 'zh': '时间到…', 'ja': '時間切れ…', 'ko': '시간 초과…', 'ru': 'Время вышло…', 'pt': 'Tempo esgotado…'},
    'Trêve : plus aucune pièce carrée ne peut bouger.\n': {'en': 'Truce: no square piece can move anymore.\n', 'de': 'Waffenstillstand: kein quadratischer Stein kann sich mehr bewegen.\n', 'es': 'Tregua: ninguna pieza cuadrada puede moverse.\n', 'it': 'Tregua: nessun pezzo quadrato può più muoversi.\n', 'zh': '停战：任何方形棋子都无法移动。\n', 'ja': '休戦：四角い駒がもう動けません。\n', 'ko': '휴전: 사각 말이 더 이상 움직일 수 없습니다.\n', 'ru': 'Перемирие: ни одна квадратная фишка не может ходить.\n', 'pt': 'Trégua: nenhuma peça quadrada pode se mover.\n'},
    'Vous avez accepté la nulle.': {'en': 'You accepted the draw.', 'de': 'Du hast das Remis angenommen.', 'es': 'Aceptaste las tablas.', 'it': 'Hai accettato la patta.', 'zh': '你接受了和棋。', 'ja': '引き分けを承諾しました。', 'ko': '무승부를 수락했습니다.', 'ru': 'Вы приняли ничью.', 'pt': 'Você aceitou o empate.'},
    "Vous n'avez pas rejoint la partie suivante à temps.\n": {'en': "You didn't join the next game in time.\n", 'de': 'Du bist der nächsten Partie nicht rechtzeitig beigetreten.\n', 'es': 'No te uniste a la siguiente partida a tiempo.\n', 'it': 'Non ti sei unito alla partita successiva in tempo.\n', 'zh': '你未能及时加入下一局。\n', 'ja': '次の対局に間に合いませんでした。\n', 'ko': '다음 대국에 제때 참여하지 못했습니다.\n', 'ru': 'Вы не успели присоединиться к следующей партии.\n', 'pt': 'Você não entrou na próxima partida a tempo.\n'},
    'Échec de la proposition.': {'en': 'The offer failed.', 'de': 'Angebot fehlgeschlagen.', 'es': 'La oferta falló.', 'it': 'Proposta non riuscita.', 'zh': '提议失败。', 'ja': '提案に失敗しました。', 'ko': '제안에 실패했습니다.', 'ru': 'Не удалось отправить предложение.', 'pt': 'A oferta falhou.'},
    'Échec.': {'en': 'Failed.', 'de': 'Fehlgeschlagen.', 'es': 'Falló.', 'it': 'Non riuscito.', 'zh': '失败。', 'ja': '失敗しました。', 'ko': '실패했습니다.', 'ru': 'Ошибка.', 'pt': 'Falhou.'},
    '  (égalité)': {'en': '  (tie)', 'de': '  (Gleichstand)', 'es': '  (empate)', 'it': '  (parità)', 'zh': '  （平局）', 'ja': '  （同点）', 'ko': '  (동점)', 'ru': '  (равенство)', 'pt': '  (empate)'},
    '%s (déco %ds)': {'en': '%s (disc. %ds)', 'de': '%s (getr. %ds)', 'es': '%s (desc. %ds)', 'it': '%s (disc. %ds)', 'zh': '%s（断线 %d秒）', 'ja': '%s（切断 %d秒）', 'ko': '%s (연결 끊김 %d초)', 'ru': '%s (отключён %dс)', 'pt': '%s (desc. %ds)'},
    '  •  Ultime partie pour {loser}': {'en': '  •  Last game for {loser}', 'de': '  •  Letzte Partie für {loser}', 'es': '  •  Última partida para {loser}', 'it': '  •  Ultima partita per {loser}', 'zh': '  •  {loser} 的最后一局', 'ja': '  •  {loser} の最終対局', 'ko': '  •  {loser}의 마지막 대국', 'ru': '  •  Последняя партия для {loser}', 'pt': '  •  Última partida para {loser}'},
    'papatte (adversaire bloqué)': {'en': 'papatte (opponent blocked)', 'de': 'papatte (Gegner blockiert)', 'es': 'papatte (rival bloqueado)', 'it': 'papatte (avversario bloccato)', 'zh': 'papatte（对手被封锁）', 'ja': 'papatte（相手が動けない）', 'ko': 'papatte (상대 봉쇄)', 'ru': 'papatte (соперник заблокирован)', 'pt': 'papatte (adversário bloqueado)'},
})


TRANSLATIONS.update({
    'Clique sur « Partie suivante ».': {'en': 'Tap “Next game”.', 'de': 'Tippe auf „Nächste Partie“.', 'es': 'Pulsa «Siguiente partida».', 'it': 'Tocca «Partita successiva».', 'zh': '点击“下一局”。', 'ja': '「次の対局」を押してください。', 'ko': '“다음 대국”을 누르세요.', 'ru': 'Нажмите «Следующая партия».', 'pt': 'Toque em «Próxima partida».'},
})


TRANSLATIONS.update({
    'Le match est perdu.\n\n(Aucun point Mélo : pas de partie en cours.)': {'en': 'The match is lost.\n\n(No Mélo points: no game in progress.)', 'de': 'Das Match ist verloren.\n\n(Keine Mélo-Punkte: keine laufende Partie.)', 'es': 'El match está perdido.\n\n(Sin puntos Mélo: no hay partida en curso.)', 'it': 'Il match è perso.\n\n(Nessun punto Mélo: nessuna partita in corso.)', 'zh': '比赛失败。\n\n（无 Mélo 分：没有进行中的对局。）', 'ja': 'マッチに敗れました。\n\n（Mélo ポイントなし：進行中の対局がありません。）', 'ko': '매치에서 졌습니다.\n\n(Mélo 점수 없음: 진행 중인 대국 없음.)', 'ru': 'Матч проигран.\n\n(Без очков Mélo: партия не идёт.)', 'pt': 'A partida foi perdida.\n\n(Sem pontos Mélo: nenhuma partida em andamento.)'},
    "Votre adversaire n'a pas rejoint la partie suivante.\n": {'en': "Your opponent didn't join the next game.\n", 'de': 'Dein Gegner ist der nächsten Partie nicht beigetreten.\n', 'es': 'Tu rival no se unió a la siguiente partida.\n', 'it': 'Il tuo avversario non si è unito alla partita successiva.\n', 'zh': '你的对手未加入下一局。\n', 'ja': '相手が次の対局に参加しませんでした。\n', 'ko': '상대가 다음 대국에 참여하지 않았습니다.\n', 'ru': 'Соперник не присоединился к следующей партии.\n', 'pt': 'Seu adversário não entrou na próxima partida.\n'},
    'Vous remportez le match.\n\n(Aucun point Mélo : pas de partie en cours.)': {'en': 'You win the match.\n\n(No Mélo points: no game in progress.)', 'de': 'Du gewinnst das Match.\n\n(Keine Mélo-Punkte: keine laufende Partie.)', 'es': 'Ganas el match.\n\n(Sin puntos Mélo: no hay partida en curso.)', 'it': 'Vinci il match.\n\n(Nessun punto Mélo: nessuna partita in corso.)', 'zh': '你赢得了比赛。\n\n（无 Mélo 分：没有进行中的对局。）', 'ja': 'マッチに勝利しました。\n\n（Mélo ポイントなし：進行中の対局がありません。）', 'ko': '매치에서 승리했습니다.\n\n(Mélo 점수 없음: 진행 중인 대국 없음.)', 'ru': 'Вы выигрываете матч.\n\n(Без очков Mélo: партия не идёт.)', 'pt': 'Você vence a partida.\n\n(Sem pontos Mélo: nenhuma partida em andamento.)'},
})


TRANSLATIONS.update({
    "En attente de l'adversaire…": {'en': 'Waiting for opponent…', 'de': 'Warte auf Gegner…', 'es': 'Esperando al rival…', 'it': "In attesa dell'avversario…", 'zh': '等待对手…', 'ja': '相手を待っています…', 'ko': '상대를 기다리는 중…', 'ru': 'Ожидание соперника…', 'pt': 'Aguardando o adversário…'},
    "En attente de l'adversaire…  (%ds)": {'en': 'Waiting for opponent…  (%ds)', 'de': 'Warte auf Gegner…  (%ds)', 'es': 'Esperando al rival…  (%ds)', 'it': "In attesa dell'avversario…  (%ds)", 'zh': '等待对手…  (%d秒)', 'ja': '相手を待っています…  (%d秒)', 'ko': '상대를 기다리는 중…  (%d초)', 'ru': 'Ожидание соперника…  (%dс)', 'pt': 'Aguardando o adversário…  (%ds)'},
    'Proposition de nulle envoyée.\nVotre adversaire la verra en ouvrant la partie.': {'en': 'Draw offer sent.\nYour opponent will see it when opening the game.', 'de': 'Remisangebot gesendet.\nDein Gegner sieht es beim Öffnen der Partie.', 'es': 'Oferta de tablas enviada.\nTu rival la verá al abrir la partida.', 'it': 'Offerta di patta inviata.\nIl tuo avversario la vedrà aprendo la partita.', 'zh': '和棋提议已发送。\n对手打开对局时会看到。', 'ja': '引き分けの申し出を送信しました。\n相手が対局を開くと表示されます。', 'ko': '무승부 제안을 보냈습니다.\n상대가 대국을 열면 보게 됩니다.', 'ru': 'Предложение ничьей отправлено.\nСоперник увидит его, открыв партию.', 'pt': 'Oferta de empate enviada.\nSeu adversário verá ao abrir a partida.'},
})


TRANSLATIONS.update({
    'Adversaire': {'en': 'Opponent', 'de': 'Gegner', 'es': 'Rival', 'it': 'Avversario', 'zh': '对手', 'ja': '相手', 'ko': '상대', 'ru': 'Соперник', 'pt': 'Adversário'},
    "L'adversaire": {'en': 'Opponent', 'de': 'Der Gegner', 'es': 'El rival', 'it': "L'avversario", 'zh': '对手', 'ja': '相手', 'ko': '상대', 'ru': 'Соперник', 'pt': 'O adversário'},
    '%s (abandon…)': {'en': '%s (resigns…)', 'de': '%s (gibt auf…)', 'es': '%s (abandona…)', 'it': '%s (abbandona…)', 'zh': '%s（认输…）', 'ja': '%s（投了…）', 'ko': '%s (기권…)', 'ru': '%s (сдаётся…)', 'pt': '%s (desiste…)'},
})


TRANSLATIONS.update({
    'Nulle': {'en': 'Draw', 'de': 'Remis', 'es': 'Tablas', 'it': 'Patta', 'zh': '和棋', 'ja': '引き分け', 'ko': '무승부', 'ru': 'Ничья', 'pt': 'Empate'},
    'Match nul !': {'en': 'Draw!', 'de': 'Unentschieden!', 'es': '¡Tablas!', 'it': 'Patta!', 'zh': '平局！', 'ja': '引き分け！', 'ko': '무승부!', 'ru': 'Ничья!', 'pt': 'Empate!'},
    'Partie nulle': {'en': 'Drawn game', 'de': 'Remispartie', 'es': 'Partida en tablas', 'it': 'Partita patta', 'zh': '和棋', 'ja': '引き分け', 'ko': '무승부 대국', 'ru': 'Ничья', 'pt': 'Partida empatada'},
})


TRANSLATIONS.update({
    "Bienvenue. À La Fuga, le but du jeu est d'emmener l'Héritier (pièce encadrée) jusqu'à sa zone de ralliement, à l'autre bout du plateau. Bien sûr, vous devrez aussi empêcher votre adversaire d'y parvenir. Il peut y parvenir par lui-même ou en étant poussé.": {'en': 'Welcome. In La Fuga, the goal is to bring your Heir (the framed piece) to its rally zone at the far end of the board. Of course, you must also stop your opponent from doing the same. The Heir can get there on its own or by being pushed.', 'de': 'Willkommen. Bei La Fuga besteht das Ziel darin, deinen Erben (die umrahmte Figur) zu seiner Sammelzone am anderen Ende des Bretts zu bringen. Natürlich musst du auch deinen Gegner daran hindern. Der Erbe kann von selbst dorthin gelangen oder geschoben werden.', 'es': 'Bienvenido. En La Fuga, el objetivo es llevar a tu Heredero (la pieza enmarcada) a su zona de reunión, al otro extremo del tablero. Por supuesto, también debes impedir que tu rival lo logre. El Heredero puede llegar por sí mismo o siendo empujado.', 'it': "Benvenuto. In La Fuga, lo scopo è portare il tuo Erede (il pezzo incorniciato) alla sua zona di raccolta, all'altro capo della scacchiera. Naturalmente devi anche impedire al tuo avversario di riuscirci. L'Erede può arrivarci da solo o venendo spinto.", 'pt': 'Bem-vindo. Em La Fuga, o objetivo é levar seu Herdeiro (a peça emoldurada) até sua zona de reunião, no outro extremo do tabuleiro. Claro, você também deve impedir que seu adversário consiga. O Herdeiro pode chegar sozinho ou sendo empurrado.', 'zh': '欢迎。在 La Fuga 中，目标是把你的继承人（有边框的棋子）带到棋盘另一端的集结区。当然，你也必须阻止对手做到这一点。继承人可以自己抵达，也可以被推过去。', 'ja': 'ようこそ。La Fuga の目的は、あなたの跡継ぎ（枠で囲まれた駒）を盤の反対側の集結地点まで導くことです。もちろん、相手が同じことをするのも防がねばなりません。跡継ぎは自力でも、押されても到達できます。', 'ko': '환영합니다. La Fuga의 목표는 당신의 후계자(테두리가 있는 말)를 반대편 끝의 집결 구역으로 데려가는 것입니다. 물론 상대가 그렇게 하는 것도 막아야 합니다. 후계자는 스스로 갈 수도, 밀려서 갈 수도 있습니다.', 'ru': 'Добро пожаловать. В La Fuga цель — привести вашего Наследника (фигура в рамке) в его зону сбора на другом конце доски. Разумеется, нужно также помешать сопернику сделать то же самое. Наследник может дойти сам или быть вытолкнут туда.'},
    "Clique sur l'Héritier pour le sélectionner.": {'en': 'Tap the Heir to select it.', 'de': 'Tippe auf den Erben, um ihn auszuwählen.', 'es': 'Toca al Heredero para seleccionarlo.', 'it': "Tocca l'Erede per selezionarlo.", 'pt': 'Toque no Herdeiro para selecioná-lo.', 'zh': '点击继承人以选中它。', 'ja': '跡継ぎをタップして選択します。', 'ko': '후계자를 눌러 선택하세요.', 'ru': 'Нажмите на Наследника, чтобы выбрать его.'},
    "Toutes les pièces peuvent se déplacer d'une case dans n'importe quelle direction. Déplace l'Héritier sur une case voisine.": {'en': 'Every piece can move one square in any direction. Move the Heir to an adjacent square.', 'de': 'Jede Figur kann sich ein Feld in jede Richtung bewegen. Bewege den Erben auf ein Nachbarfeld.', 'es': 'Todas las piezas pueden moverse una casilla en cualquier dirección. Mueve al Heredero a una casilla vecina.', 'it': "Ogni pezzo può muoversi di una casella in qualsiasi direzione. Sposta l'Erede su una casella vicina.", 'pt': 'Todas as peças podem mover-se uma casa em qualquer direção. Mova o Herdeiro para uma casa vizinha.', 'zh': '所有棋子都可以朝任意方向移动一格。把继承人移到相邻的一格。', 'ja': 'すべての駒は好きな方向に1マス動けます。跡継ぎを隣のマスへ動かしましょう。', 'ko': '모든 말은 어느 방향으로든 한 칸 움직일 수 있습니다. 후계자를 이웃 칸으로 옮기세요.', 'ru': 'Каждая фигура может двигаться на одну клетку в любом направлении. Переместите Наследника на соседнюю клетку.'},
    'Pour valider ton coup, clique à nouveau sur la pièce, sur sa nouvelle case.': {'en': 'To confirm your move, tap the piece again on its new square.', 'de': 'Um deinen Zug zu bestätigen, tippe erneut auf die Figur auf ihrem neuen Feld.', 'es': 'Para confirmar tu jugada, vuelve a tocar la pieza en su nueva casilla.', 'it': 'Per confermare la mossa, tocca di nuovo il pezzo sulla sua nuova casella.', 'pt': 'Para confirmar sua jogada, toque novamente na peça, na sua nova casa.', 'zh': '要确认这一步，请在棋子的新位置再次点击它。', 'ja': '手を確定するには、新しいマスにある駒をもう一度タップします。', 'ko': '수를 확정하려면 새 칸에 있는 말을 다시 누르세요.', 'ru': 'Чтобы подтвердить ход, снова нажмите на фигуру на её новой клетке.'},
    'Parfait ! Clique sur « Suivant » pour continuer.': {'en': 'Perfect! Tap “Next” to continue.', 'de': 'Perfekt! Tippe auf „Weiter“, um fortzufahren.', 'es': '¡Perfecto! Toca «Siguiente» para continuar.', 'it': 'Perfetto! Tocca «Avanti» per continuare.', 'pt': 'Perfeito! Toque em «Próximo» para continuar.', 'zh': '完美！点击“下一步”继续。', 'ja': '完璧です！「次へ」を押して続けましょう。', 'ko': '완벽합니다! “다음”을 눌러 계속하세요.', 'ru': 'Отлично! Нажмите «Далее», чтобы продолжить.'},
    'Pour se déplacer, une pièce RONDE doit toucher une autre ronde (alliée ou adverse), et une pièce CARRÉE doit toucher une autre carrée. En vert : les pièces qui peuvent bouger. En rouge : les pièces bloquées (aucune pièce de leur forme à côté).': {'en': 'To move, a ROUND piece must touch another round one (friendly or enemy), and a SQUARE piece must touch another square one. In green: pieces that can move. In red: blocked pieces (no piece of their shape beside them).', 'de': 'Um sich zu bewegen, muss eine RUNDE Figur eine andere runde berühren (eigene oder gegnerische), und eine ECKIGE Figur eine andere eckige. In Grün: Figuren, die ziehen können. In Rot: blockierte Figuren (keine Figur ihrer Form daneben).', 'es': 'Para moverse, una pieza REDONDA debe tocar otra redonda (aliada o rival), y una pieza CUADRADA debe tocar otra cuadrada. En verde: las piezas que pueden moverse. En rojo: las piezas bloqueadas (ninguna pieza de su forma al lado).', 'it': 'Per muoversi, un pezzo TONDO deve toccarne un altro tondo (alleato o avversario), e un pezzo QUADRATO un altro quadrato. In verde: i pezzi che possono muoversi. In rosso: i pezzi bloccati (nessun pezzo della loro forma accanto).', 'pt': 'Para se mover, uma peça REDONDA deve tocar outra redonda (aliada ou adversária), e uma peça QUADRADA deve tocar outra quadrada. Em verde: as peças que podem mover-se. Em vermelho: as peças bloqueadas (nenhuma peça da sua forma ao lado).', 'zh': '要移动，圆形棋子必须接触另一枚圆形棋子（己方或对方），方形棋子必须接触另一枚方形棋子。绿色：可以移动的棋子。红色：被封锁的棋子（旁边没有同形状的棋子）。', 'ja': '動くには、丸い駒は別の丸い駒（味方でも敵でも）に接し、四角い駒は別の四角い駒に接している必要があります。緑：動ける駒。赤：動けない駒（隣に同じ形の駒がない）。', 'ko': '움직이려면 둥근 말은 다른 둥근 말(아군이든 적이든)에, 사각 말은 다른 사각 말에 닿아야 합니다. 초록색: 움직일 수 있는 말. 빨간색: 막힌 말(옆에 같은 모양의 말이 없음).', 'ru': 'Чтобы ходить, КРУГЛАЯ фигура должна касаться другой круглой (своей или чужой), а КВАДРАТНАЯ — другой квадратной. Зелёные: фигуры, которые могут ходить. Красные: заблокированные (рядом нет фигуры их формы).'},
    'Une pièce ronde saute par-dessus une autre ronde (alliée ou adverse), en ligne DROITE ou en DIAGONALE, et peut enchaîner les sauts ! Clique sur la Nurse.': {'en': 'A round piece jumps over another round one (friendly or enemy), STRAIGHT or DIAGONALLY, and can chain jumps! Tap the Nurse.', 'de': 'Eine runde Figur springt über eine andere runde (eigene oder gegnerische), GERADE oder DIAGONAL, und kann Sprünge aneinanderreihen! Tippe auf die Amme.', 'es': 'Una pieza redonda salta sobre otra redonda (aliada o rival), en LÍNEA RECTA o en DIAGONAL, ¡y puede encadenar saltos! Toca a la Nodriza.', 'it': 'Un pezzo tondo salta sopra un altro tondo (alleato o avversario), in LINEA RETTA o in DIAGONALE, e può concatenare i salti! Tocca la Balia.', 'pt': 'Uma peça redonda salta por cima de outra redonda (aliada ou adversária), em LINHA RETA ou na DIAGONAL, e pode encadear saltos! Toque na Ama.', 'zh': '圆形棋子可以直线或斜线跳过另一枚圆形棋子（己方或对方），并且可以连续跳跃！点击乳母。', 'ja': '丸い駒は別の丸い駒（味方でも敵でも）を、まっすぐでも斜めでも飛び越え、続けて跳ぶことができます！乳母をタップしましょう。', 'ko': '둥근 말은 다른 둥근 말(아군이든 적이든)을 직선 또는 대각선으로 뛰어넘고, 연속으로 점프할 수 있습니다! 유모를 누르세요.', 'ru': 'Круглая фигура перепрыгивает через другую круглую (свою или чужую) — ПО ПРЯМОЙ или ПО ДИАГОНАЛИ — и может делать серию прыжков! Нажмите на Няньку.'},
    'Clique à nouveau sur la Nurse pour valider ton multisaut.': {'en': 'Tap the Nurse again to confirm your multi-jump.', 'de': 'Tippe erneut auf die Amme, um deinen Mehrfachsprung zu bestätigen.', 'es': 'Vuelve a tocar a la Nodriza para confirmar tu salto múltiple.', 'it': 'Tocca di nuovo la Balia per confermare il tuo multi-salto.', 'pt': 'Toque novamente na Ama para confirmar seu salto múltiplo.', 'zh': '再次点击乳母以确认你的连跳。', 'ja': 'もう一度乳母をタップして連続ジャンプを確定します。', 'ko': '유모를 다시 눌러 멀티 점프를 확정하세요.', 'ru': 'Снова нажмите на Няньку, чтобы подтвердить серию прыжков.'},
    'Bravo ! Sauts droits et diagonaux : tu maîtrises le multisaut.': {'en': "Well done! Straight and diagonal jumps: you've mastered the multi-jump.", 'de': 'Gut gemacht! Gerade und diagonale Sprünge: Du beherrschst den Mehrfachsprung.', 'es': '¡Bien hecho! Saltos rectos y diagonales: dominas el salto múltiple.', 'it': 'Bravo! Salti dritti e diagonali: padroneggi il multi-salto.', 'pt': 'Muito bem! Saltos retos e diagonais: você domina o salto múltiplo.', 'zh': '做得好！直线和斜线跳跃：你已掌握连跳。', 'ja': 'お見事！まっすぐと斜めのジャンプ、連続ジャンプをマスターしました。', 'ko': '잘했습니다! 직선과 대각선 점프, 멀티 점프를 익혔군요.', 'ru': 'Отлично! Прямые и диагональные прыжки — вы освоили серию прыжков.'},
    "L'Héritier peut lui aussi enchaîner les sauts, droits ou diagonaux, et même FUGUER en sautant. Clique sur l'Héritier.": {'en': 'The Heir can also chain jumps, straight or diagonal, and even ESCAPE by jumping. Tap the Heir.', 'de': 'Auch der Erbe kann Sprünge aneinanderreihen, gerade oder diagonal, und sogar durch Springen FLIEHEN. Tippe auf den Erben.', 'es': 'El Heredero también puede encadenar saltos, rectos o diagonales, e incluso FUGARSE saltando. Toca al Heredero.', 'it': "Anche l'Erede può concatenare salti, dritti o diagonali, e persino FUGGIRE saltando. Tocca l'Erede.", 'pt': 'O Herdeiro também pode encadear saltos, retos ou diagonais, e até FUGIR saltando. Toque no Herdeiro.', 'zh': '继承人同样可以连续直线或斜线跳跃，甚至可以通过跳跃“逃脱”。点击继承人。', 'ja': '跡継ぎも、まっすぐや斜めのジャンプを続けられ、跳んで「脱出（フーガ）」することさえできます。跡継ぎをタップしましょう。', 'ko': '후계자도 직선이나 대각선으로 연속 점프할 수 있고, 점프로 “탈출(푸가)”할 수도 있습니다. 후계자를 누르세요.', 'ru': 'Наследник тоже может делать серию прыжков — прямых или диагональных — и даже СБЕЖАТЬ прыжком. Нажмите на Наследника.'},
    "Fugue réussie ! L'Héritier a atteint son ralliement : VICTOIRE !": {'en': 'Escape successful! The Heir reached its rally zone: VICTORY!', 'de': 'Flucht gelungen! Der Erbe hat seine Sammelzone erreicht: SIEG!', 'es': '¡Fuga lograda! El Heredero alcanzó su zona de reunión: ¡VICTORIA!', 'it': "Fuga riuscita! L'Erede ha raggiunto la sua zona di raccolta: VITTORIA!", 'pt': 'Fuga bem-sucedida! O Herdeiro alcançou sua zona de reunião: VITÓRIA!', 'zh': '逃脱成功！继承人到达了集结区：胜利！', 'ja': '脱出成功！跡継ぎが集結地点に到達：勝利です！', 'ko': '탈출 성공! 후계자가 집결 구역에 도달했습니다: 승리!', 'ru': 'Побег удался! Наследник достиг зоны сбора: ПОБЕДА!'},
    "Saut en DIAGONALE par-dessus ré2, jusqu'en mi3.": {'en': 'DIAGONAL jump over ré2, to mi3.', 'de': 'DIAGONALER Sprung über ré2 bis mi3.', 'es': 'Salto en DIAGONAL sobre ré2, hasta mi3.', 'it': 'Salto in DIAGONALE oltre ré2, fino a mi3.', 'pt': 'Salto na DIAGONAL sobre ré2, até mi3.', 'zh': '斜跳越过 ré2，到达 mi3。', 'ja': 'ré2 を斜めに飛び越えて mi3 へ。', 'ko': 'ré2 위로 대각선 점프하여 mi3로.', 'ru': 'ДИАГОНАЛЬНЫЙ прыжок через ré2 на mi3.'},
    "Saut tout DROIT par-dessus fa3, jusqu'en sol3.": {'en': 'STRAIGHT jump over fa3, to sol3.', 'de': 'GERADER Sprung über fa3 bis sol3.', 'es': 'Salto RECTO sobre fa3, hasta sol3.', 'it': 'Salto DRITTO oltre fa3, fino a sol3.', 'pt': 'Salto RETO sobre fa3, até sol3.', 'zh': '直跳越过 fa3，到达 sol3。', 'ja': 'fa3 をまっすぐ飛び越えて sol3 へ。', 'ko': 'fa3 위로 직선 점프하여 sol3로.', 'ru': 'ПРЯМОЙ прыжок через fa3 на sol3.'},
    "De nouveau en DIAGONALE par-dessus fa4, jusqu'en mi5.": {'en': 'Again DIAGONALLY over fa4, to mi5.', 'de': 'Wieder DIAGONAL über fa4 bis mi5.', 'es': 'De nuevo en DIAGONAL sobre fa4, hasta mi5.', 'it': 'Di nuovo in DIAGONALE oltre fa4, fino a mi5.', 'pt': 'Novamente na DIAGONAL sobre fa4, até mi5.', 'zh': '再次斜跳越过 fa4，到达 mi5。', 'ja': '再び fa4 を斜めに飛び越えて mi5 へ。', 'ko': '다시 fa4 위로 대각선으로 mi5까지.', 'ru': 'Снова ПО ДИАГОНАЛИ через fa4 на mi5.'},
    "Et tout DROIT par-dessus mi6, jusqu'en mi7.": {'en': 'And STRAIGHT over mi6, to mi7.', 'de': 'Und GERADE über mi6 bis mi7.', 'es': 'Y RECTO sobre mi6, hasta mi7.', 'it': 'E DRITTO oltre mi6, fino a mi7.', 'pt': 'E RETO sobre mi6, até mi7.', 'zh': '然后直跳越过 mi6，到达 mi7。', 'ja': 'そしてまっすぐ mi6 を越えて mi7 へ。', 'ko': '그리고 mi6 위로 직선으로 mi7까지.', 'ru': 'И ПО ПРЯМОЙ через mi6 на mi7.'},
    "Saut en DIAGONALE par-dessus fa4, jusqu'en sol5.": {'en': 'DIAGONAL jump over fa4, to sol5.', 'de': 'DIAGONALER Sprung über fa4 bis sol5.', 'es': 'Salto en DIAGONAL sobre fa4, hasta sol5.', 'it': 'Salto in DIAGONALE oltre fa4, fino a sol5.', 'pt': 'Salto na DIAGONAL sobre fa4, até sol5.', 'zh': '斜跳越过 fa4，到达 sol5。', 'ja': 'fa4 を斜めに飛び越えて sol5 へ。', 'ko': 'fa4 위로 대각선 점프하여 sol5로.', 'ru': 'ДИАГОНАЛЬНЫЙ прыжок через fa4 на sol5.'},
    "Saut tout DROIT par-dessus sol6, jusqu'en sol7.": {'en': 'STRAIGHT jump over sol6, to sol7.', 'de': 'GERADER Sprung über sol6 bis sol7.', 'es': 'Salto RECTO sobre sol6, hasta sol7.', 'it': 'Salto DRITTO oltre sol6, fino a sol7.', 'pt': 'Salto RETO sobre sol6, até sol7.', 'zh': '直跳越过 sol6，到达 sol7。', 'ja': 'sol6 をまっすぐ飛び越えて sol7 へ。', 'ko': 'sol6 위로 직선 점프하여 sol7로.', 'ru': 'ПРЯМОЙ прыжок через sol6 на sol7.'},
    "Dernier saut, en DIAGONALE par-dessus fa8 : l'Héritier SORT du plateau et rejoint son ralliement !": {'en': 'Final jump, DIAGONALLY over fa8: the Heir LEAVES the board and reaches its rally zone!', 'de': 'Letzter Sprung, DIAGONAL über fa8: Der Erbe VERLÄSST das Brett und erreicht seine Sammelzone!', 'es': 'Último salto, en DIAGONAL sobre fa8: ¡el Heredero SALE del tablero y alcanza su zona de reunión!', 'it': "Ultimo salto, in DIAGONALE oltre fa8: l'Erede ESCE dalla scacchiera e raggiunge la sua zona di raccolta!", 'pt': 'Último salto, na DIAGONAL sobre fa8: o Herdeiro SAI do tabuleiro e alcança sua zona de reunião!', 'zh': '最后一跳，斜跳越过 fa8：继承人离开棋盘，抵达集结区！', 'ja': '最後のジャンプ、fa8 を斜めに飛び越え：跡継ぎが盤外へ出て集結地点に到達！', 'ko': '마지막 점프, fa8 위로 대각선: 후계자가 판을 벗어나 집결 구역에 도달합니다!', 'ru': 'Последний прыжок, ПО ДИАГОНАЛИ через fa8: Наследник ПОКИДАЕТ доску и достигает зоны сбора!'},
})


TRANSLATIONS.update({
    "Les pièces carrées d'un même camp qui se touchent, même en diagonale, forment une UNITÉ. Plusieurs pièces de la même unité peuvent se déplacer en même temps, dans la même direction. Déplaçons plusieurs pièces de l'unité en vert ; clique sur do2, qui sera la meneuse.": {'en': "Square pieces of the same side that touch, even diagonally, form a UNIT. Several pieces of the same unit can move at once, in the same direction. Let's move several pieces of the green unit; tap do2, which will be the leader.", 'de': 'Eckige Figuren derselben Seite, die sich berühren – auch diagonal – bilden eine EINHEIT. Mehrere Figuren derselben Einheit können sich gleichzeitig in dieselbe Richtung bewegen. Bewegen wir mehrere Figuren der grünen Einheit; tippe auf do2, die Anführerin.', 'es': 'Las piezas cuadradas de un mismo bando que se tocan, incluso en diagonal, forman una UNIDAD. Varias piezas de la misma unidad pueden moverse a la vez, en la misma dirección. Movamos varias piezas de la unidad verde; toca do2, que será la líder.', 'it': "I pezzi quadrati dello stesso schieramento che si toccano, anche in diagonale, formano un'UNITÀ. Più pezzi della stessa unità possono muoversi insieme, nella stessa direzione. Muoviamo più pezzi dell'unità verde; tocca do2, che sarà la guida.", 'pt': 'As peças quadradas do mesmo lado que se tocam, mesmo na diagonal, formam uma UNIDADE. Várias peças da mesma unidade podem mover-se ao mesmo tempo, na mesma direção. Vamos mover várias peças da unidade verde; toque em do2, que será a líder.', 'zh': '同一方相互接触（包括斜向接触）的方形棋子组成一个“单位”。同一单位的多枚棋子可以同时朝同一方向移动。我们来移动绿色单位的几枚棋子；点击 do2，它将作为领棋。', 'ja': '接している（斜めも含む）同じ陣営の四角い駒は「ユニット」を作ります。同じユニットの複数の駒は、同じ方向へ同時に動けます。緑のユニットの駒をいくつか動かしましょう。do2 をタップ、これがリーダーです。', 'ko': '서로 닿아 있는(대각선 포함) 같은 편 사각 말들은 “유닛”을 이룹니다. 같은 유닛의 여러 말은 같은 방향으로 동시에 움직일 수 있습니다. 초록 유닛의 말 몇 개를 옮겨 봅시다. do2를 누르세요, 이것이 리더입니다.', 'ru': 'Квадратные фигуры одной стороны, касающиеся друг друга (даже по диагонали), образуют ОТРЯД. Несколько фигур одного отряда могут ходить одновременно в одном направлении. Подвинем несколько фигур зелёного отряда; нажмите do2 — это будет ведущая.'},
    "Ajoute ré2 puis fa3 à la sélection (on laisse mi2 de côté : tu n'es pas obligé de tout prendre).": {'en': "Add ré2 then fa3 to the selection (we leave mi2 out: you don't have to take them all).", 'de': 'Füge ré2 und dann fa3 zur Auswahl hinzu (mi2 lassen wir weg: du musst nicht alle nehmen).', 'es': 'Añade ré2 y luego fa3 a la selección (dejamos mi2 fuera: no tienes que tomarlas todas).', 'it': 'Aggiungi ré2 e poi fa3 alla selezione (lasciamo fuori mi2: non sei obbligato a prenderli tutti).', 'pt': 'Adicione ré2 e depois fa3 à seleção (deixamos mi2 de fora: você não precisa pegar todas).', 'zh': '把 ré2 和 fa3 加入选择（把 mi2 留下：你不必全选）。', 'ja': 'ré2 と fa3 を選択に加えます（mi2 は外します。すべてを取る必要はありません）。', 'ko': 'ré2와 fa3을 선택에 추가하세요(mi2는 제외: 모두 고를 필요는 없습니다).', 'ru': 'Добавьте ré2, затем fa3 к выбору (mi2 оставляем: брать все необязательно).'},
    "L'unité se déplace selon la meneuse. Clique en do3 pour monter les pièces choisies d'une case.": {'en': 'The unit moves according to the leader. Tap do3 to move the chosen pieces up one square.', 'de': 'Die Einheit bewegt sich nach der Anführerin. Tippe auf do3, um die gewählten Figuren ein Feld nach oben zu ziehen.', 'es': 'La unidad se mueve según la líder. Toca do3 para subir una casilla las piezas elegidas.', 'it': "L'unità si muove secondo la guida. Tocca do3 per far salire di una casella i pezzi scelti.", 'pt': 'A unidade move-se conforme a líder. Toque em do3 para subir uma casa as peças escolhidas.', 'zh': '单位随领棋移动。点击 do3，把所选棋子向上移动一格。', 'ja': 'ユニットはリーダーに従って動きます。do3 をタップして、選んだ駒を1マス上げましょう。', 'ko': '유닛은 리더를 따라 움직입니다. do3을 눌러 선택한 말들을 한 칸 위로 올리세요.', 'ru': 'Отряд движется вслед за ведущей. Нажмите do3, чтобы поднять выбранные фигуры на одну клетку.'},
    'Clique sur la meneuse pour valider ton coup.': {'en': 'Tap the leader to confirm your move.', 'de': 'Tippe auf die Anführerin, um deinen Zug zu bestätigen.', 'es': 'Toca a la líder para confirmar tu jugada.', 'it': 'Tocca la guida per confermare la mossa.', 'pt': 'Toque na líder para confirmar sua jogada.', 'zh': '点击领棋以确认这一步。', 'ja': 'リーダーをタップして手を確定します。', 'ko': '리더를 눌러 수를 확정하세요.', 'ru': 'Нажмите на ведущую, чтобы подтвердить ход.'},
    "En montant, la pièce en fa s'est retrouvée seule (encadrée) ! Une manœuvre peut donc IMMOBILISER une pièce : fa n'a plus aucune carrée à côté.": {'en': 'By moving up, the piece on fa ended up alone (framed)! A maneuver can thus IMMOBILIZE a piece: fa no longer has any square piece beside it.', 'de': 'Beim Hochziehen blieb die Figur auf fa allein (umrahmt)! Ein Manöver kann eine Figur also LAHMLEGEN: fa hat keine eckige Figur mehr neben sich.', 'es': 'Al subir, la pieza en fa quedó sola (enmarcada). Una maniobra puede, pues, INMOVILIZAR una pieza: fa ya no tiene ninguna cuadrada al lado.', 'it': 'Salendo, il pezzo su fa è rimasto solo (incorniciato)! Una manovra può quindi IMMOBILIZZARE un pezzo: fa non ha più alcun quadrato accanto.', 'pt': 'Ao subir, a peça em fa ficou sozinha (emoldurada)! Uma manobra pode, portanto, IMOBILIZAR uma peça: fa já não tem nenhuma quadrada ao lado.', 'zh': '上移之后，fa 上的棋子变得孤立（有边框）！所以一次调动可以“困住”一枚棋子：fa 旁边不再有方形棋子。', 'ja': '上げたことで、fa の駒が孤立しました（枠付き）！つまり手順によって駒を「動けなく」できます。fa の隣にはもう四角い駒がありません。', 'ko': '위로 올리면서 fa의 말이 홀로 남았습니다(테두리 표시)! 이렇게 기동으로 말을 “묶을” 수 있습니다. fa 옆에는 더 이상 사각 말이 없습니다.', 'ru': 'Поднявшись, фигура на fa осталась одна (в рамке)! Манёвром можно ОБЕЗДВИЖИТЬ фигуру: рядом с fa больше нет квадратной.'},
    'Le GARDE (croix ×) se déplace en diagonale et POUSSE en ligne droite. Clique sur le Garde.': {'en': 'The GUARD (× cross) moves diagonally and PUSHES in a straight line. Tap the Guard.', 'de': 'Der WÄCHTER (Kreuz ×) zieht diagonal und SCHIEBT gerade. Tippe auf den Wächter.', 'es': 'El GUARDIA (cruz ×) se mueve en diagonal y EMPUJA en línea recta. Toca al Guardia.', 'it': 'La GUARDIA (croce ×) si muove in diagonale e SPINGE in linea retta. Tocca la Guardia.', 'pt': 'O GUARDA (cruz ×) move-se na diagonal e EMPURRA em linha reta. Toque no Guarda.', 'zh': '守卫（× 十字）斜向移动，直线方向进行推挤。点击守卫。', 'ja': 'ガード（× 十字）は斜めに動き、まっすぐ「押し」ます。ガードをタップしましょう。', 'ko': '가드(× 십자)는 대각선으로 움직이고 직선 방향으로 “밀기”를 합니다. 가드를 누르세요.', 'ru': 'СТРАЖ (крест ×) ходит по диагонали и ТОЛКАЕТ по прямой. Нажмите на Стража.'},
    "Déplace le Garde en diagonale, jusqu'en fa4.": {'en': 'Move the Guard diagonally, to fa4.', 'de': 'Bewege den Wächter diagonal bis fa4.', 'es': 'Mueve al Guardia en diagonal, hasta fa4.', 'it': 'Sposta la Guardia in diagonale, fino a fa4.', 'pt': 'Mova o Guarda na diagonal, até fa4.', 'zh': '把守卫斜向移动到 fa4。', 'ja': 'ガードを斜めに fa4 まで動かします。', 'ko': '가드를 대각선으로 fa4까지 옮기세요.', 'ru': 'Переместите Стража по диагонали на fa4.'},
    "Maintenant POUSSE : clique en sol4. Toute la ligne est repoussée d'une case, et la pièce du bord tombe du plateau (éliminée) !": {'en': 'Now PUSH: tap sol4. The whole line is pushed one square, and the edge piece falls off the board (eliminated)!', 'de': 'Jetzt SCHIEBEN: tippe auf sol4. Die ganze Reihe wird ein Feld geschoben, und die Randfigur fällt vom Brett (eliminiert)!', 'es': 'Ahora EMPUJA: toca sol4. Toda la línea se empuja una casilla, y la pieza del borde cae del tablero (eliminada).', 'it': 'Ora SPINGI: tocca sol4. Tutta la fila viene spinta di una casella e il pezzo di bordo cade dalla scacchiera (eliminato)!', 'pt': 'Agora EMPURRE: toque em sol4. Toda a linha é empurrada uma casa, e a peça da borda cai do tabuleiro (eliminada)!', 'zh': '现在推挤：点击 sol4。整行被推动一格，边缘的棋子掉出棋盘（被淘汰）！', 'ja': 'では「押し」ます：sol4 をタップ。列全体が1マス押され、端の駒が盤外へ落ちます（除外）！', 'ko': '이제 “밀기”: sol4를 누르세요. 줄 전체가 한 칸 밀리고, 가장자리 말이 판 밖으로 떨어집니다(제거)!', 'ru': 'Теперь ТОЛКАЙТЕ: нажмите sol4. Весь ряд сдвигается на клетку, и крайняя фигура падает с доски (устранена)!'},
    'Clique sur le Garde pour valider ton coup.': {'en': 'Tap the Guard to confirm your move.', 'de': 'Tippe auf den Wächter, um deinen Zug zu bestätigen.', 'es': 'Toca al Guardia para confirmar tu jugada.', 'it': 'Tocca la Guardia per confermare la mossa.', 'pt': 'Toque no Guarda para confirmar sua jogada.', 'zh': '点击守卫以确认这一步。', 'ja': 'ガードをタップして手を確定します。', 'ko': '가드를 눌러 수를 확정하세요.', 'ru': 'Нажмите на Стража, чтобы подтвердить ход.'},
    "Bravo ! Le Garde a poussé la ligne et éliminé une pièce. C'est le SEUL moyen d'éliminer une pièce : la pousser hors du plateau. Et tu peux même éliminer tes PROPRES pièces !": {'en': 'Well done! The Guard pushed the line and eliminated a piece. This is the ONLY way to eliminate a piece: push it off the board. And you can even eliminate your OWN pieces!', 'de': 'Gut gemacht! Der Wächter hat die Reihe geschoben und eine Figur eliminiert. Das ist die EINZIGE Art, eine Figur zu eliminieren: sie vom Brett schieben. Und du kannst sogar deine EIGENEN Figuren eliminieren!', 'es': '¡Bien hecho! El Guardia empujó la línea y eliminó una pieza. Es la ÚNICA forma de eliminar una pieza: empujarla fuera del tablero. ¡E incluso puedes eliminar tus PROPIAS piezas!', 'it': "Bravo! La Guardia ha spinto la fila ed eliminato un pezzo. È l'UNICO modo per eliminare un pezzo: spingerlo fuori dalla scacchiera. E puoi persino eliminare i TUOI pezzi!", 'pt': 'Muito bem! O Guarda empurrou a linha e eliminou uma peça. É a ÚNICA forma de eliminar uma peça: empurrá-la para fora do tabuleiro. E você pode até eliminar suas PRÓPRIAS peças!', 'zh': '做得好！守卫推动整行，淘汰了一枚棋子。这是淘汰棋子的唯一方式：把它推出棋盘。你甚至可以淘汰自己的棋子！', 'ja': 'お見事！ガードが列を押して駒を除外しました。駒を除外する唯一の方法は、盤外へ押し出すことです。しかも自分の駒さえ除外できます！', 'ko': '잘했습니다! 가드가 줄을 밀어 말 하나를 제거했습니다. 말을 제거하는 유일한 방법은 판 밖으로 미는 것입니다. 심지어 자신의 말도 제거할 수 있습니다!', 'ru': 'Отлично! Страж толкнул ряд и устранил фигуру. Это ЕДИНСТВЕННЫЙ способ убрать фигуру: вытолкнуть её с доски. И вы можете убрать даже СВОИ фигуры!'},
    'Le SOLDAT (croix +) se déplace en ligne droite et POUSSE en diagonale. Clique sur le Soldat.': {'en': 'The SOLDIER (+ cross) moves in a straight line and PUSHES diagonally. Tap the Soldier.', 'de': 'Der SOLDAT (Kreuz +) zieht gerade und SCHIEBT diagonal. Tippe auf den Soldaten.', 'es': 'El SOLDADO (cruz +) se mueve en línea recta y EMPUJA en diagonal. Toca al Soldado.', 'it': 'Il SOLDATO (croce +) si muove in linea retta e SPINGE in diagonale. Tocca il Soldato.', 'pt': 'O SOLDADO (cruz +) move-se em linha reta e EMPURRA na diagonal. Toque no Soldado.', 'zh': '士兵（+ 十字）直线移动，斜向进行推挤。点击士兵。', 'ja': 'ソルジャー（+ 十字）はまっすぐ動き、斜めに「押し」ます。ソルジャーをタップしましょう。', 'ko': '솔저(+ 십자)는 직선으로 움직이고 대각선으로 “밀기”를 합니다. 솔저를 누르세요.', 'ru': 'СОЛДАТ (крест +) ходит по прямой и ТОЛКАЕТ по диагонали. Нажмите на Солдата.'},
    'Déplace le Soldat tout droit, en do4.': {'en': 'Move the Soldier straight, to do4.', 'de': 'Bewege den Soldaten gerade nach do4.', 'es': 'Mueve al Soldado en recto, hasta do4.', 'it': 'Sposta il Soldato dritto, fino a do4.', 'pt': 'Mova o Soldado em linha reta, até do4.', 'zh': '把士兵直线移动到 do4。', 'ja': 'ソルジャーをまっすぐ do4 へ動かします。', 'ko': '솔저를 직선으로 do4로 옮기세요.', 'ru': 'Переместите Солдата по прямой на do4.'},
    'POUSSE en diagonale : clique en ré5 pour repousser la pièce.': {'en': 'PUSH diagonally: tap ré5 to push the piece back.', 'de': 'SCHIEBE diagonal: tippe auf ré5, um die Figur wegzuschieben.', 'es': 'EMPUJA en diagonal: toca ré5 para empujar la pieza.', 'it': 'SPINGI in diagonale: tocca ré5 per respingere il pezzo.', 'pt': 'EMPURRE na diagonal: toque em ré5 para empurrar a peça.', 'zh': '斜向推挤：点击 ré5 把棋子推开。', 'ja': '斜めに「押し」ます：ré5 をタップして駒を押しやります。', 'ko': '대각선으로 “밀기”: ré5를 눌러 말을 밀어내세요.', 'ru': 'ТОЛКАЙТЕ по диагонали: нажмите ré5, чтобы оттолкнуть фигуру.'},
    'Clique sur le Soldat pour valider ton coup.': {'en': 'Tap the Soldier to confirm your move.', 'de': 'Tippe auf den Soldaten, um deinen Zug zu bestätigen.', 'es': 'Toca al Soldado para confirmar tu jugada.', 'it': 'Tocca il Soldato per confermare la mossa.', 'pt': 'Toque no Soldado para confirmar sua jogada.', 'zh': '点击士兵以确认这一步。', 'ja': 'ソルジャーをタップして手を確定します。', 'ko': '솔저를 눌러 수를 확정하세요.', 'ru': 'Нажмите на Солдата, чтобы подтвердить ход.'},
    "Attention : en se déplaçant, le Soldat s'est éloigné de son allié et n'a plus de carrée à côté, il est maintenant BLOQUÉ (encadré) jusqu'à ce qu'une carrée le rejoigne.": {'en': 'Careful: by moving, the Soldier drifted away from its ally and no longer has a square piece beside it; it is now BLOCKED (framed) until a square piece joins it.', 'de': 'Achtung: Durch den Zug hat sich der Soldat von seinem Verbündeten entfernt und hat keine eckige Figur mehr daneben; er ist nun BLOCKIERT (umrahmt), bis eine eckige Figur zu ihm stößt.', 'es': 'Cuidado: al moverse, el Soldado se alejó de su aliado y ya no tiene una cuadrada al lado; ahora está BLOQUEADO (enmarcado) hasta que una cuadrada se le una.', 'it': 'Attenzione: muovendosi, il Soldato si è allontanato dal suo alleato e non ha più un quadrato accanto; ora è BLOCCATO (incorniciato) finché un quadrato non lo raggiunge.', 'pt': 'Atenção: ao mover-se, o Soldado afastou-se do seu aliado e já não tem uma quadrada ao lado; agora está BLOQUEADO (emoldurado) até que uma quadrada o alcance.', 'zh': '注意：士兵移动后远离了盟友，旁边不再有方形棋子，现在被“封锁”（有边框），直到有方形棋子靠近它。', 'ja': '注意：動いたことでソルジャーは味方から離れ、隣に四角い駒がなくなりました。四角い駒が来るまで「動けない」状態です（枠付き）。', 'ko': '주의: 움직이면서 솔저가 아군에서 멀어져 옆에 사각 말이 없어졌습니다. 이제 사각 말이 올 때까지 “묶인” 상태입니다(테두리 표시).', 'ru': 'Осторожно: сдвинувшись, Солдат отдалился от союзника и остался без квадратной рядом; теперь он ЗАБЛОКИРОВАН (в рамке), пока квадратная не подойдёт.'},
    "Après s'être déplacée, une carrée peut pousser dans PLUSIEURS directions, autant que tu veux. Clique sur le Garde.": {'en': 'After moving, a square piece can push in SEVERAL directions, as many as you like. Tap the Guard.', 'de': 'Nach dem Ziehen kann eine eckige Figur in MEHRERE Richtungen schieben, so viele du willst. Tippe auf den Wächter.', 'es': 'Tras moverse, una cuadrada puede empujar en VARIAS direcciones, tantas como quieras. Toca al Guardia.', 'it': 'Dopo essersi mossa, una quadrata può spingere in PIÙ direzioni, quante ne vuoi. Tocca la Guardia.', 'pt': 'Após mover-se, uma quadrada pode empurrar em VÁRIAS direções, quantas quiser. Toque no Guarda.', 'zh': '移动之后，方形棋子可以朝多个方向推挤，想推几次都行。点击守卫。', 'ja': '動いた後、四角い駒は好きなだけ複数の方向へ「押す」ことができます。ガードをタップしましょう。', 'ko': '움직인 뒤, 사각 말은 원하는 만큼 여러 방향으로 밀 수 있습니다. 가드를 누르세요.', 'ru': 'После хода квадратная фигура может толкать в НЕСКОЛЬКО направлений, сколько угодно. Нажмите на Стража.'},
    'Déplace le Garde en diagonale, en fa4.': {'en': 'Move the Guard diagonally, to fa4.', 'de': 'Bewege den Wächter diagonal nach fa4.', 'es': 'Mueve al Guardia en diagonal, a fa4.', 'it': 'Sposta la Guardia in diagonale, a fa4.', 'pt': 'Mova o Guarda na diagonal, para fa4.', 'zh': '把守卫斜向移动到 fa4。', 'ja': 'ガードを斜めに fa4 へ動かします。', 'ko': '가드를 대각선으로 fa4로 옮기세요.', 'ru': 'Переместите Стража по диагонали на fa4.'},
    "Bravo ! Tu as poussé en haut et à droite. Remarque : fa3 (en bas) pouvait aussi être poussée, mais on l'a laissée, c'est toi qui choisis quelles directions pousser.": {'en': 'Well done! You pushed up and to the right. Note: fa3 (below) could also have been pushed, but we left it—you choose which directions to push.', 'de': 'Gut gemacht! Du hast nach oben und nach rechts geschoben. Beachte: fa3 (unten) hätte auch geschoben werden können, aber wir haben es gelassen—du wählst, in welche Richtungen du schiebst.', 'es': '¡Bien hecho! Empujaste hacia arriba y a la derecha. Nota: fa3 (abajo) también podía empujarse, pero la dejamos; tú eliges en qué direcciones empujar.', 'it': "Bravo! Hai spinto in alto e a destra. Nota: anche fa3 (in basso) poteva essere spinta, ma l'abbiamo lasciata; sei tu a scegliere in quali direzioni spingere.", 'pt': 'Muito bem! Você empurrou para cima e para a direita. Nota: fa3 (abaixo) também podia ser empurrada, mas a deixamos; você escolhe em quais direções empurrar.', 'zh': '做得好！你向上和向右推了。注意：fa3（下方）本也可以被推，但我们留下了它——由你选择朝哪些方向推。', 'ja': 'お見事！上と右へ押しました。補足：fa3（下）も押せましたが、あえて残しました。どの方向へ押すかはあなたが選びます。', 'ko': '잘했습니다! 위쪽과 오른쪽으로 밀었습니다. 참고: fa3(아래)도 밀 수 있었지만 남겨 두었습니다. 어느 방향으로 밀지는 당신이 정합니다.', 'ru': 'Отлично! Вы толкнули вверх и вправо. Заметьте: fa3 (внизу) тоже можно было толкнуть, но мы оставили её — вы сами выбираете направления толчка.'},
    'Pousse une 1re direction : clique en fa5 (vers le haut).': {'en': 'Push a first direction: tap fa5 (upward).', 'de': 'Schiebe eine erste Richtung: tippe auf fa5 (nach oben).', 'es': 'Empuja una primera dirección: toca fa5 (hacia arriba).', 'it': "Spingi una prima direzione: tocca fa5 (verso l'alto).", 'pt': 'Empurre uma primeira direção: toque em fa5 (para cima).', 'zh': '先推一个方向：点击 fa5（向上）。', 'ja': 'まず1方向へ押します：fa5 をタップ（上へ）。', 'ko': '첫 번째 방향으로 미세요: fa5를 누르세요(위쪽).', 'ru': 'Толкните в первом направлении: нажмите fa5 (вверх).'},
    'Tu peux pousser une AUTRE direction ! Clique en sol4 (vers la droite).': {'en': 'You can push ANOTHER direction! Tap sol4 (to the right).', 'de': 'Du kannst in eine WEITERE Richtung schieben! Tippe auf sol4 (nach rechts).', 'es': '¡Puedes empujar OTRA dirección! Toca sol4 (a la derecha).', 'it': "Puoi spingere in un'ALTRA direzione! Tocca sol4 (verso destra).", 'pt': 'Você pode empurrar OUTRA direção! Toque em sol4 (para a direita).', 'zh': '你可以再推另一个方向！点击 sol4（向右）。', 'ja': '別の方向にも押せます！sol4 をタップ（右へ）。', 'ko': '다른 방향으로도 밀 수 있습니다! sol4를 누르세요(오른쪽).', 'ru': 'Можно толкнуть в ДРУГОМ направлении! Нажмите sol4 (вправо).'},
})


TRANSLATIONS.update({
    'On peut aussi POUSSER son propre Héritier ! Clique sur le Garde.': {'en': 'You can also PUSH your own Heir! Tap the Guard.', 'de': 'Du kannst auch deinen eigenen Erben SCHIEBEN! Tippe auf den Wächter.', 'es': '¡También puedes EMPUJAR a tu propio Heredero! Toca al Guardia.', 'it': 'Puoi anche SPINGERE il tuo Erede! Tocca la Guardia.', 'pt': 'Você também pode EMPURRAR seu próprio Herdeiro! Toque no Guarda.', 'zh': '你也可以推自己的继承人！点击守卫。', 'ja': '自分の跡継ぎを「押す」こともできます！ガードをタップしましょう。', 'ko': '자신의 후계자도 “밀” 수 있습니다! 가드를 누르세요.', 'ru': 'Можно ТОЛКНУТЬ и своего Наследника! Нажмите на Стража.'},
    "Déplace le Garde en diagonale, en fa7 (sous l'Héritier).": {'en': 'Move the Guard diagonally, to fa7 (below the Heir).', 'de': 'Bewege den Wächter diagonal nach fa7 (unter den Erben).', 'es': 'Mueve al Guardia en diagonal, a fa7 (debajo del Heredero).', 'it': "Sposta la Guardia in diagonale, a fa7 (sotto l'Erede).", 'pt': 'Mova o Guarda na diagonal, para fa7 (abaixo do Herdeiro).', 'zh': '把守卫斜向移动到 fa7（继承人下方）。', 'ja': 'ガードを斜めに fa7 へ（跡継ぎの下）。', 'ko': '가드를 대각선으로 fa7로 옮기세요(후계자 아래).', 'ru': 'Переместите Стража по диагонали на fa7 (под Наследником).'},
    "POUSSE vers le haut : clique en fa8. L'Héritier est poussé dans son ralliement !": {'en': 'PUSH upward: tap fa8. The Heir is pushed into its rally zone!', 'de': 'SCHIEBE nach oben: tippe auf fa8. Der Erbe wird in seine Sammelzone geschoben!', 'es': 'EMPUJA hacia arriba: toca fa8. ¡El Heredero es empujado a su zona de reunión!', 'it': "SPINGI verso l'alto: tocca fa8. L'Erede viene spinto nella sua zona di raccolta!", 'pt': 'EMPURRE para cima: toque em fa8. O Herdeiro é empurrado para sua zona de reunião!', 'zh': '向上推：点击 fa8。继承人被推入集结区！', 'ja': '上へ「押す」：fa8 をタップ。跡継ぎが集結地点へ押し込まれます！', 'ko': '위로 “밀기”: fa8을 누르세요. 후계자가 집결 구역으로 밀려 들어갑니다!', 'ru': 'ТОЛКАЙТЕ вверх: нажмите fa8. Наследника вталкивают в его зону сбора!'},
    'Fugue ! Tu as poussé ton Héritier dans son ralliement : VICTOIRE !': {'en': 'Escape! You pushed your Heir into its rally zone: VICTORY!', 'de': 'Flucht! Du hast deinen Erben in seine Sammelzone geschoben: SIEG!', 'es': '¡Fuga! Empujaste a tu Heredero a su zona de reunión: ¡VICTORIA!', 'it': 'Fuga! Hai spinto il tuo Erede nella sua zona di raccolta: VITTORIA!', 'pt': 'Fuga! Você empurrou seu Herdeiro para sua zona de reunião: VITÓRIA!', 'zh': '逃脱！你把继承人推入了集结区：胜利！', 'ja': '脱出！跡継ぎを集結地点へ押し込みました：勝利です！', 'ko': '탈출! 후계자를 집결 구역으로 밀어 넣었습니다: 승리!', 'ru': 'Побег! Вы втолкнули своего Наследника в зону сбора: ПОБЕДА!'},
    "Enfin, pousser l'Héritier ADVERSE hors du plateau le met MAT. Clique sur le Garde.": {'en': 'Finally, pushing the ENEMY Heir off the board is CHECKMATE. Tap the Guard.', 'de': 'Schließlich ist es MATT, den GEGNERISCHEN Erben vom Brett zu schieben. Tippe auf den Wächter.', 'es': 'Por último, empujar al Heredero RIVAL fuera del tablero es MATE. Toca al Guardia.', 'it': "Infine, spingere l'Erede AVVERSARIO fuori dalla scacchiera è MATTO. Tocca la Guardia.", 'pt': 'Por fim, empurrar o Herdeiro ADVERSÁRIO para fora do tabuleiro é XEQUE-MATE. Toque no Guarda.', 'zh': '最后，把对方的继承人推出棋盘就是“将死”。点击守卫。', 'ja': '最後に、相手の跡継ぎを盤外へ押し出すと「詰み」です。ガードをタップしましょう。', 'ko': '마지막으로, 상대 후계자를 판 밖으로 밀어내면 “외통”입니다. 가드를 누르세요.', 'ru': 'Наконец, вытолкнуть ВРАЖЕСКОГО Наследника с доски — это МАТ. Нажмите на Стража.'},
    "Déplace le Garde en diagonale, en la7 (sous l'Héritier adverse).": {'en': 'Move the Guard diagonally, to la7 (below the enemy Heir).', 'de': 'Bewege den Wächter diagonal nach la7 (unter den gegnerischen Erben).', 'es': 'Mueve al Guardia en diagonal, a la7 (debajo del Heredero rival).', 'it': "Sposta la Guardia in diagonale, a la7 (sotto l'Erede avversario).", 'pt': 'Mova o Guarda na diagonal, para la7 (abaixo do Herdeiro adversário).', 'zh': '把守卫斜向移动到 la7（对方继承人下方）。', 'ja': 'ガードを斜めに la7 へ（相手の跡継ぎの下）。', 'ko': '가드를 대각선으로 la7로 옮기세요(상대 후계자 아래).', 'ru': 'Переместите Стража по диагонали на la7 (под вражеским Наследником).'},
    "POUSSE vers le haut : clique en la8. L'Héritier adverse est éjecté du plateau !": {'en': 'PUSH upward: tap la8. The enemy Heir is ejected from the board!', 'de': 'SCHIEBE nach oben: tippe auf la8. Der gegnerische Erbe wird vom Brett geworfen!', 'es': 'EMPUJA hacia arriba: toca la8. ¡El Heredero rival es expulsado del tablero!', 'it': "SPINGI verso l'alto: tocca la8. L'Erede avversario viene espulso dalla scacchiera!", 'pt': 'EMPURRE para cima: toque em la8. O Herdeiro adversário é expulso do tabuleiro!', 'zh': '向上推：点击 la8。对方的继承人被逐出棋盘！', 'ja': '上へ「押す」：la8 をタップ。相手の跡継ぎが盤外へ弾き出されます！', 'ko': '위로 “밀기”: la8을 누르세요. 상대 후계자가 판 밖으로 밀려납니다!', 'ru': 'ТОЛКАЙТЕ вверх: нажмите la8. Вражеского Наследника выбрасывают с доски!'},
    "Mat ! Tu as poussé l'Héritier adverse hors du plateau : VICTOIRE !": {'en': 'Checkmate! You pushed the enemy Heir off the board: VICTORY!', 'de': 'Matt! Du hast den gegnerischen Erben vom Brett geschoben: SIEG!', 'es': '¡Mate! Empujaste al Heredero rival fuera del tablero: ¡VICTORIA!', 'it': "Matto! Hai spinto l'Erede avversario fuori dalla scacchiera: VITTORIA!", 'pt': 'Xeque-mate! Você empurrou o Herdeiro adversário para fora do tabuleiro: VITÓRIA!', 'zh': '将死！你把对方的继承人推出了棋盘：胜利！', 'ja': '詰み！相手の跡継ぎを盤外へ押し出しました：勝利です！', 'ko': '외통! 상대 후계자를 판 밖으로 밀어냈습니다: 승리!', 'ru': 'Мат! Вы вытолкнули вражеского Наследника с доски: ПОБЕДА!'},
    "Le CHEVALIER (l'hexagone) est une pièce à part, avec deux pouvoirs. INÉBRANLABLE : il ne peut jamais être poussé, une poussée s'arrête net sur lui. INDÉPENDANT : il peut se déplacer même s'il ne touche aucune pièce de sa forme (il n'a pas besoin de voisine pour bouger).": {'en': 'The KNIGHT (the hexagon) is a special piece with two powers. UNMOVABLE: it can never be pushed—a push stops dead against it. INDEPENDENT: it can move even without touching any piece of its shape (it needs no neighbor to move).', 'de': 'Der RITTER (das Sechseck) ist eine besondere Figur mit zwei Kräften. UNVERRÜCKBAR: Er kann nie geschoben werden—ein Schub stoppt an ihm. UNABHÄNGIG: Er kann ziehen, auch ohne eine Figur seiner Form zu berühren (er braucht keinen Nachbarn).', 'es': 'El CABALLERO (el hexágono) es una pieza especial con dos poderes. INAMOVIBLE: nunca puede ser empujado; un empuje se detiene en seco contra él. INDEPENDIENTE: puede moverse aunque no toque ninguna pieza de su forma (no necesita vecina para moverse).', 'it': "Il CAVALIERE (l'esagono) è un pezzo speciale con due poteri. INAMOVIBILE: non può mai essere spinto, una spinta si arresta di colpo su di lui. INDIPENDENTE: può muoversi anche senza toccare alcun pezzo della sua forma (non gli serve una vicina per muoversi).", 'pt': 'O CAVALEIRO (o hexágono) é uma peça especial com dois poderes. INABALÁVEL: nunca pode ser empurrado; um empurrão para de vez contra ele. INDEPENDENTE: pode mover-se mesmo sem tocar nenhuma peça da sua forma (não precisa de vizinha para mover-se).', 'zh': '骑士（六边形）是一枚特殊棋子，拥有两种能力。不可推动：它永远不会被推，推挤在它面前立刻停止。独立：即使不接触任何同形状的棋子它也能移动（无需邻居即可移动）。', 'ja': 'ナイト（六角形）は特別な駒で、2つの力を持ちます。不動：決して押されず、押しはその手前で止まります。独立：同じ形の駒に接していなくても動けます（動くのに隣の駒が要りません）。', 'ko': '나이트(육각형)는 두 가지 능력을 지닌 특별한 말입니다. 불변: 절대 밀리지 않으며, 밀기는 그 앞에서 즉시 멈춥니다. 독립: 같은 모양의 말에 닿지 않아도 움직일 수 있습니다(움직이는 데 이웃이 필요 없음).', 'ru': 'РЫЦАРЬ (шестиугольник) — особая фигура с двумя свойствами. НЕСДВИГАЕМЫЙ: его нельзя толкнуть, толчок останавливается на нём. НЕЗАВИСИМЫЙ: он может ходить, даже не касаясь фигур своей формы (ему не нужен сосед).'},
    "Puisqu'il ne peut être poussé, le Chevalier sert de MUR : il bloque les poussées. Ici, même si le Garde adverse s'avance en fa3 pour pousser vers le haut, le Chevalier (fa4) arrête tout : l'Héritier (fa5) est protégé.": {'en': "Since it can't be pushed, the Knight acts as a WALL: it blocks pushes. Here, even if the enemy Guard advances to fa3 to push upward, the Knight (fa4) stops everything: the Heir (fa5) is protected.", 'de': 'Da er nicht geschoben werden kann, dient der Ritter als MAUER: Er blockiert Schübe. Selbst wenn der gegnerische Wächter hier auf fa3 vorrückt, um nach oben zu schieben, stoppt der Ritter (fa4) alles: Der Erbe (fa5) ist geschützt.', 'es': 'Como no puede ser empujado, el Caballero actúa como MURO: bloquea los empujes. Aquí, aunque el Guardia rival avance a fa3 para empujar hacia arriba, el Caballero (fa4) lo detiene todo: el Heredero (fa5) está protegido.', 'it': "Poiché non può essere spinto, il Cavaliere funge da MURO: blocca le spinte. Qui, anche se la Guardia avversaria avanza in fa3 per spingere verso l'alto, il Cavaliere (fa4) ferma tutto: l'Erede (fa5) è protetto.", 'pt': 'Como não pode ser empurrado, o Cavaleiro serve de MURO: bloqueia os empurrões. Aqui, mesmo que o Guarda adversário avance para fa3 para empurrar para cima, o Cavaleiro (fa4) detém tudo: o Herdeiro (fa5) está protegido.', 'zh': '由于无法被推动，骑士充当“墙”：它阻挡推挤。这里，即使对方守卫前进到 fa3 想向上推，骑士（fa4）也会挡住一切：继承人（fa5）受到保护。', 'ja': '押されないため、ナイトは「壁」として働き、押しを止めます。ここでは、相手のガードが fa3 に進んで上へ押そうとしても、ナイト（fa4）がすべてを止めます。跡継ぎ（fa5）は守られます。', 'ko': '밀리지 않으므로 나이트는 “벽” 역할을 하여 밀기를 막습니다. 여기서 상대 가드가 fa3으로 나아가 위로 밀려 해도, 나이트(fa4)가 모든 것을 막습니다. 후계자(fa5)는 보호됩니다.', 'ru': 'Поскольку его нельзя толкнуть, Рыцарь служит СТЕНОЙ: он блокирует толчки. Здесь, даже если вражеский Страж выйдет на fa3, чтобы толкнуть вверх, Рыцарь (fa4) всё остановит: Наследник (fa5) защищён.'},
    'Voici toutes les façons dont une partie peut se terminer, et combien de points chacune rapporte.': {'en': 'Here are all the ways a game can end, and how many points each is worth.', 'de': 'Hier sind alle Arten, wie eine Partie enden kann, und wie viele Punkte jede bringt.', 'es': 'Estas son todas las formas en que puede terminar una partida, y cuántos puntos otorga cada una.', 'it': 'Ecco tutti i modi in cui una partita può finire, e quanti punti vale ciascuno.', 'pt': 'Aqui estão todas as formas de uma partida terminar, e quantos pontos cada uma vale.', 'zh': '以下是一局对局可能结束的所有方式，以及各自的得分。', 'ja': '対局が終わるすべての形と、それぞれの得点を紹介します。', 'ko': '대국이 끝나는 모든 방식과 각각의 점수를 소개합니다.', 'ru': 'Вот все способы, которыми может закончиться партия, и сколько очков даёт каждый.'},
    "FUGUE (+2 points). Ton Héritier atteint son ralliement (la flèche) : tu gagnes la partie ! C'est la victoire la plus valorisée. Une Nurse à son contact lui permet de bouger.": {'en': "ESCAPE (+2 points). Your Heir reaches its rally zone (the arrow): you win the game! It's the most valued victory. A Nurse in contact lets it move.", 'de': 'FLUCHT (+2 Punkte). Dein Erbe erreicht seine Sammelzone (der Pfeil): Du gewinnst die Partie! Der wertvollste Sieg. Eine Amme in Kontakt lässt ihn ziehen.', 'es': 'FUGA (+2 puntos). Tu Heredero alcanza su zona de reunión (la flecha): ¡ganas la partida! Es la victoria más valiosa. Una Nodriza en contacto le permite moverse.', 'it': 'FUGA (+2 punti). Il tuo Erede raggiunge la sua zona di raccolta (la freccia): vinci la partita! È la vittoria più preziosa. Una Balia a contatto gli permette di muoversi.', 'pt': 'FUGA (+2 pontos). Seu Herdeiro alcança sua zona de reunião (a seta): você vence a partida! É a vitória mais valiosa. Uma Ama em contato permite que ele se mova.', 'zh': '逃脱（+2 分）。你的继承人到达集结区（箭头）：你赢得对局！这是最有价值的胜利。相邻的乳母可让它移动。', 'ja': '脱出（+2点）。跡継ぎが集結地点（矢印）に到達：対局に勝利！最も価値ある勝ち方です。接している乳母がいれば動けます。', 'ko': '탈출(+2점). 후계자가 집결 구역(화살표)에 도달: 대국에서 승리! 가장 가치 있는 승리입니다. 닿아 있는 유모가 있으면 움직일 수 있습니다.', 'ru': 'ПОБЕГ (+2 очка). Ваш Наследник достигает зоны сбора (стрелка): вы выигрываете партию! Самая ценная победа. Нянька рядом позволяет ему двигаться.'},
    "DOUBLE FUGUE (0 point). Quand les Blancs fuguent, les Noirs ont droit à un DERNIER coup pour égaliser. Si les deux Héritiers rejoignent leur ralliement, la partie est nulle. Ici, c'est aux Blancs de jouer, et les deux Héritiers peuvent fuguer (flèches).": {'en': "DOUBLE ESCAPE (0 points). When White escapes, Black gets one LAST move to equalize. If both Heirs reach their rally zones, the game is a draw. Here it's White to move, and both Heirs can escape (arrows).", 'de': 'DOPPELTE FLUCHT (0 Punkte). Wenn Weiß flieht, hat Schwarz einen LETZTEN Zug zum Ausgleich. Erreichen beide Erben ihre Sammelzone, ist die Partie remis. Hier ist Weiß am Zug, und beide Erben können fliehen (Pfeile).', 'es': 'DOBLE FUGA (0 puntos). Cuando las Blancas se fugan, las Negras tienen un ÚLTIMO movimiento para igualar. Si ambos Herederos alcanzan su zona de reunión, la partida es tablas. Aquí juegan las Blancas, y ambos Herederos pueden fugarse (flechas).', 'it': "DOPPIA FUGA (0 punti). Quando il Bianco fugge, il Nero ha un'ULTIMA mossa per pareggiare. Se entrambi gli Eredi raggiungono la loro zona di raccolta, la partita è patta. Qui muove il Bianco, ed entrambi gli Eredi possono fuggire (frecce).", 'pt': 'FUGA DUPLA (0 pontos). Quando as Brancas fogem, as Pretas têm um ÚLTIMO lance para igualar. Se ambos os Herdeiros alcançarem sua zona de reunião, a partida é empate. Aqui jogam as Brancas, e ambos os Herdeiros podem fugir (setas).', 'zh': '双重逃脱（0 分）。白方逃脱后，黑方有最后一步来扳平。若两位继承人都抵达各自集结区，则和棋。此处轮到白方，两位继承人都可逃脱（箭头）。', 'ja': 'ダブル脱出（0点）。白が脱出すると、黒は同点にするための最後の1手を得ます。両方の跡継ぎが集結地点に到達すれば引き分けです。ここは白番で、両方の跡継ぎが脱出できます（矢印）。', 'ko': '이중 탈출(0점). 백이 탈출하면 흑에게 동점을 위한 마지막 한 수가 주어집니다. 두 후계자가 모두 집결 구역에 도달하면 무승부입니다. 여기는 백 차례이며, 두 후계자 모두 탈출할 수 있습니다(화살표).', 'ru': 'ДВОЙНОЙ ПОБЕГ (0 очков). Когда белые сбегают, у чёрных есть ПОСЛЕДНИЙ ход, чтобы сравнять. Если оба Наследника достигают зоны сбора — ничья. Здесь ход белых, и оба Наследника могут сбежать (стрелки).'},
    "MAT (+1 point). Le Garde (si6) se déplace en la7, puis pousse l'Héritier adverse (la8) hors du plateau : il est éjecté, tu gagnes.": {'en': "CHECKMATE (+1 point). The Guard (si6) moves to la7, then pushes the enemy Heir (la8) off the board: it's ejected, you win.", 'de': 'MATT (+1 Punkt). Der Wächter (si6) zieht nach la7 und schiebt dann den gegnerischen Erben (la8) vom Brett: Er wird geworfen, du gewinnst.', 'es': 'MATE (+1 punto). El Guardia (si6) se mueve a la7 y luego empuja al Heredero rival (la8) fuera del tablero: es expulsado, ganas.', 'it': "MATTO (+1 punto). La Guardia (si6) si sposta in la7, poi spinge l'Erede avversario (la8) fuori dalla scacchiera: viene espulso, vinci.", 'pt': 'XEQUE-MATE (+1 ponto). O Guarda (si6) move-se para la7 e depois empurra o Herdeiro adversário (la8) para fora do tabuleiro: é expulso, você vence.', 'zh': '将死（+1 分）。守卫（si6）移动到 la7，然后把对方继承人（la8）推出棋盘：它被逐出，你获胜。', 'ja': '詰み（+1点）。ガード（si6）が la7 へ動き、相手の跡継ぎ（la8）を盤外へ押し出します：弾き出されてあなたの勝ちです。', 'ko': '외통(+1점). 가드(si6)가 la7로 이동한 뒤 상대 후계자(la8)를 판 밖으로 밉니다: 밀려나고 당신이 승리합니다.', 'ru': 'МАТ (+1 очко). Страж (si6) идёт на la7, затем выталкивает вражеского Наследника (la8) с доски: он выброшен, вы побеждаете.'},
    "GUILLOTINE. L'adversaire va fuguer (son Héritier fa1, mobile grâce à sa Nurse, atteint son ralliement en bas : +2 pour lui). Pour limiter la casse, ton Garde (si6 vers la7) pousse TON PROPRE Héritier (la8) hors du plateau : c'est un mat sur toi-même, l'adversaire ne prend que +1 au lieu de +2.": {'en': "GUILLOTINE. The opponent is about to escape (their Heir fa1, mobile thanks to its Nurse, reaches its rally zone below: +2 for them). To limit the damage, your Guard (si6 to la7) pushes YOUR OWN Heir (la8) off the board: it's a self-checkmate, and the opponent gets only +1 instead of +2.", 'de': 'GUILLOTINE. Der Gegner wird fliehen (sein Erbe fa1, dank seiner Amme beweglich, erreicht unten seine Sammelzone: +2 für ihn). Um den Schaden zu begrenzen, schiebt dein Wächter (si6 nach la7) DEINEN EIGENEN Erben (la8) vom Brett: ein Selbstmatt, und der Gegner erhält nur +1 statt +2.', 'es': 'GUILLOTINA. El rival va a fugarse (su Heredero fa1, móvil gracias a su Nodriza, alcanza su zona de reunión abajo: +2 para él). Para limitar el daño, tu Guardia (si6 a la7) empuja a TU PROPIO Heredero (la8) fuera del tablero: es un mate a ti mismo, y el rival solo obtiene +1 en vez de +2.', 'it': "GHIGLIOTTINA. L'avversario sta per fuggire (il suo Erede fa1, mobile grazie alla sua Balia, raggiunge in basso la sua zona di raccolta: +2 per lui). Per limitare i danni, la tua Guardia (si6 verso la7) spinge il TUO Erede (la8) fuori dalla scacchiera: è un matto su te stesso, e l'avversario prende solo +1 invece di +2.", 'pt': 'GUILHOTINA. O adversário vai fugir (seu Herdeiro fa1, móvel graças à sua Ama, alcança sua zona de reunião abaixo: +2 para ele). Para limitar o estrago, seu Guarda (si6 para la7) empurra seu PRÓPRIO Herdeiro (la8) para fora do tabuleiro: é um xeque-mate em si mesmo, e o adversário recebe só +1 em vez de +2.', 'zh': '断头台。对手即将逃脱（他的继承人 fa1 靠乳母得以移动，抵达下方集结区：他得 +2）。为减少损失，你的守卫（si6 到 la7）把你自己的继承人（la8）推出棋盘：这是对自己的将死，对手只得 +1 而非 +2。', 'ja': 'ギロチン。相手が脱出しようとしています（乳母のおかげで動ける相手の跡継ぎ fa1 が下の集結地点に到達：相手に+2）。被害を抑えるため、あなたのガード（si6→la7）が自分の跡継ぎ（la8）を盤外へ押し出します：自分への詰みで、相手は+2ではなく+1だけになります。', 'ko': '기요틴. 상대가 탈출하려 합니다(유모 덕분에 움직이는 상대 후계자 fa1이 아래 집결 구역에 도달: 상대 +2). 피해를 줄이기 위해, 당신의 가드(si6→la7)가 자신의 후계자(la8)를 판 밖으로 밉니다: 자신에 대한 외통이며, 상대는 +2 대신 +1만 얻습니다.', 'ru': 'ГИЛЬОТИНА. Соперник вот-вот сбежит (его Наследник fa1, подвижный благодаря Няньке, достигает своей зоны сбора внизу: +2 ему). Чтобы уменьшить потери, ваш Страж (si6 на la7) выталкивает ВАШЕГО СОБСТВЕННОГО Наследника (la8) с доски: это мат самому себе, и соперник получает только +1 вместо +2.'},
    "PAPATTE (+1 point). C'est à l'adversaire de jouer, mais il n'a AUCUN coup légal : son Chevalier (do8) est coincé, et son Héritier (si8) est isolé (aucune ronde à côté). Il perd. Très rare !": {'en': "PAPATTE (+1 point). It's the opponent's turn, but they have NO legal move: their Knight (do8) is stuck, and their Heir (si8) is isolated (no round piece beside it). They lose. Very rare!", 'de': 'PAPATTE (+1 Punkt). Der Gegner ist am Zug, hat aber KEINEN legalen Zug: Sein Ritter (do8) steckt fest, und sein Erbe (si8) ist isoliert (keine runde Figur daneben). Er verliert. Sehr selten!', 'es': 'PAPATTE (+1 punto). Le toca al rival, pero no tiene NINGÚN movimiento legal: su Caballero (do8) está atascado y su Heredero (si8) está aislado (ninguna redonda al lado). Pierde. ¡Muy raro!', 'it': "PAPATTE (+1 punto). Tocca all'avversario, ma non ha ALCUNA mossa legale: il suo Cavaliere (do8) è bloccato e il suo Erede (si8) è isolato (nessun tondo accanto). Perde. Molto raro!", 'pt': 'PAPATTE (+1 ponto). É a vez do adversário, mas ele não tem NENHUM lance legal: seu Cavaleiro (do8) está preso e seu Herdeiro (si8) está isolado (nenhuma redonda ao lado). Ele perde. Muito raro!', 'zh': 'papatte（+1 分）。轮到对手行棋，但他没有任何合法着法：他的骑士（do8）被卡住，继承人（si8）被孤立（旁边没有圆形棋子）。他输了。非常罕见！', 'ja': 'パパット（+1点）。相手の番ですが、合法手が1つもありません：相手のナイト（do8）は動けず、跡継ぎ（si8）は孤立（隣に丸い駒なし）。相手の負けです。とても珍しい！', 'ko': '파파트(+1점). 상대 차례이지만 합법적인 수가 전혀 없습니다: 상대 나이트(do8)는 갇혀 있고, 후계자(si8)는 고립되어 있습니다(옆에 둥근 말 없음). 상대가 집니다. 매우 드뭅니다!', 'ru': 'ПАПАТТ (+1 очко). Ход соперника, но у него НЕТ ни одного легального хода: его Рыцарь (do8) застрял, а Наследник (si8) изолирован (рядом нет круглой фигуры). Он проигрывает. Очень редко!'},
    "TRÊVE (0 point). Quand plus AUCUN joueur n'a de carrée qui peut bouger (peu importe à qui c'est de jouer), la partie est nulle : sans carrée mobile, plus aucune poussée n'est possible. Ici, les deux carrées (encadrées) sont isolées.": {'en': "TRUCE (0 points). When NEITHER player has a square piece that can move (whoever's turn it is), the game is a draw: with no mobile square piece, no push is possible. Here, both square pieces (framed) are isolated.", 'de': 'WAFFENSTILLSTAND (0 Punkte). Wenn KEIN Spieler mehr eine bewegliche eckige Figur hat (egal wer am Zug ist), ist die Partie remis: ohne bewegliche eckige Figur ist kein Schub möglich. Hier sind beide eckigen Figuren (umrahmt) isoliert.', 'es': 'TREGUA (0 puntos). Cuando NINGÚN jugador tiene una cuadrada que pueda moverse (sea de quien sea el turno), la partida es tablas: sin cuadrada móvil, no es posible ningún empuje. Aquí, ambas cuadradas (enmarcadas) están aisladas.', 'it': 'TREGUA (0 punti). Quando NESSUN giocatore ha un quadrato che può muoversi (chiunque sia di turno), la partita è patta: senza quadrato mobile, nessuna spinta è possibile. Qui, entrambi i quadrati (incorniciati) sono isolati.', 'pt': 'TRÉGUA (0 pontos). Quando NENHUM jogador tem uma quadrada que possa mover-se (seja de quem for a vez), a partida é empate: sem quadrada móvel, nenhum empurrão é possível. Aqui, ambas as quadradas (emolduradas) estão isoladas.', 'zh': '停战（0 分）。当双方都没有可移动的方形棋子时（无论轮到谁），和棋：没有可动的方形棋子，就无法进行任何推挤。此处，两枚方形棋子（有边框）都被孤立。', 'ja': '休戦（0点）。どちらのプレイヤーにも動ける四角い駒が1つもなくなると（手番に関係なく）引き分けです：動ける四角い駒がなければ押しは不可能。ここでは両方の四角い駒（枠付き）が孤立しています。', 'ko': '휴전(0점). 어느 쪽도 움직일 수 있는 사각 말이 없을 때(누구 차례든), 무승부입니다: 움직일 사각 말이 없으면 어떤 밀기도 불가능합니다. 여기서는 두 사각 말(테두리)이 모두 고립되어 있습니다.', 'ru': 'ПЕРЕМИРИЕ (0 очков). Когда НИ У ОДНОГО игрока нет подвижной квадратной фигуры (чей бы ход ни был) — ничья: без подвижной квадратной толчок невозможен. Здесь обе квадратные (в рамке) изолированы.'},
    "NULLE PAR ACCORD (0 point). Pendant une partie, tu peux proposer la nulle avec le bouton « ½ » (entouré) ; si l'adversaire accepte, la partie est nulle. RÉPÉTITION : si la même position revient 4 fois, la nulle est automatique.": {'en': 'DRAW BY AGREEMENT (0 points). During a game, you can offer a draw with the “½” button (circled); if the opponent accepts, the game is a draw. REPETITION: if the same position recurs 4 times, the draw is automatic.', 'de': 'REMIS DURCH EINIGUNG (0 Punkte). Während einer Partie kannst du mit der „½“-Schaltfläche (eingekreist) Remis anbieten; nimmt der Gegner an, ist die Partie remis. WIEDERHOLUNG: Tritt dieselbe Stellung 4-mal auf, ist das Remis automatisch.', 'es': 'TABLAS POR ACUERDO (0 puntos). Durante una partida, puedes ofrecer tablas con el botón «½» (rodeado); si el rival acepta, la partida es tablas. REPETICIÓN: si la misma posición se repite 4 veces, las tablas son automáticas.', 'it': "PATTA PER ACCORDO (0 punti). Durante una partita puoi proporre la patta con il pulsante «½» (cerchiato); se l'avversario accetta, la partita è patta. RIPETIZIONE: se la stessa posizione si ripete 4 volte, la patta è automatica.", 'pt': 'EMPATE POR ACORDO (0 pontos). Durante uma partida, você pode propor empate com o botão «½» (circulado); se o adversário aceitar, a partida é empate. REPETIÇÃO: se a mesma posição se repetir 4 vezes, o empate é automático.', 'zh': '协议和棋（0 分）。对局中，你可以用“½”按钮（圈出）提议和棋；对手接受则和棋。重复：若同一局面出现 4 次，则自动和棋。', 'ja': '合意による引き分け（0点）。対局中、「½」ボタン（丸で囲み）で引き分けを提案できます。相手が承諾すれば引き分けです。反復：同じ局面が4回現れると自動的に引き分けになります。', 'ko': '합의 무승부(0점). 대국 중 “½” 버튼(동그라미)으로 무승부를 제안할 수 있습니다. 상대가 수락하면 무승부입니다. 반복: 같은 위치가 4번 나오면 자동으로 무승부가 됩니다.', 'ru': 'НИЧЬЯ ПО СОГЛАШЕНИЮ (0 очков). Во время партии можно предложить ничью кнопкой «½» (обведена); если соперник согласен — ничья. ПОВТОРЕНИЕ: если одна и та же позиция возникает 4 раза, ничья автоматическая.'},
    "ABANDON / TEMPS / DÉCONNEXION (+2 points chacun). Trois façons de gagner sans jouer : si l'adversaire ABANDONNE (le bouton « X »), si son TEMPS tombe à 0:00 (la pendule), ou s'il se DÉCONNECTE. Dans les trois cas, tu gagnes +2 points.": {'en': 'RESIGNATION / TIME / DISCONNECTION (+2 points each). Three ways to win without playing: if the opponent RESIGNS (the “X” button), if their TIME hits 0:00 (the clock), or if they DISCONNECT. In all three cases, you win +2 points.', 'de': 'AUFGABE / ZEIT / TRENNUNG (+2 Punkte je). Drei Wege, ohne Zug zu gewinnen: wenn der Gegner AUFGIBT (die „X“-Schaltfläche), wenn seine ZEIT auf 0:00 fällt (die Uhr) oder wenn er die VERBINDUNG verliert. In allen drei Fällen gewinnst du +2 Punkte.', 'es': 'ABANDONO / TIEMPO / DESCONEXIÓN (+2 puntos cada uno). Tres formas de ganar sin jugar: si el rival ABANDONA (el botón «X»), si su TIEMPO llega a 0:00 (el reloj), o si se DESCONECTA. En los tres casos, ganas +2 puntos.', 'it': "ABBANDONO / TEMPO / DISCONNESSIONE (+2 punti ciascuno). Tre modi per vincere senza giocare: se l'avversario ABBANDONA (il pulsante «X»), se il suo TEMPO arriva a 0:00 (l'orologio), o se si DISCONNETTE. In tutti e tre i casi vinci +2 punti.", 'pt': 'DESISTÊNCIA / TEMPO / DESCONEXÃO (+2 pontos cada). Três formas de vencer sem jogar: se o adversário DESISTE (o botão «X»), se o TEMPO dele chega a 0:00 (o relógio), ou se ele se DESCONECTA. Nos três casos, você ganha +2 pontos.', 'zh': '认输 / 超时 / 掉线（各 +2 分）。三种不用行棋就能获胜的方式：对手认输（“X”按钮）、他的时间归零 0:00（时钟）、或他掉线。三种情况你都得 +2 分。', 'ja': '投了 / 時間切れ / 切断（各+2点）。指さずに勝つ3つの方法：相手が投了（「X」ボタン）、相手の時間が 0:00 になる（時計）、または相手が切断。いずれの場合も+2点を得ます。', 'ko': '기권 / 시간패 / 연결 끊김(각 +2점). 두지 않고 이기는 세 가지 방법: 상대가 기권(“X” 버튼), 상대 시간이 0:00이 됨(시계), 또는 상대가 연결이 끊김. 세 경우 모두 +2점을 얻습니다.', 'ru': 'СДАЧА / ВРЕМЯ / ОТКЛЮЧЕНИЕ (по +2 очка). Три способа выиграть без игры: если соперник СДАЁТСЯ (кнопка «X»), если его ВРЕМЯ доходит до 0:00 (часы) или если он ОТКЛЮЧАЕТСЯ. Во всех трёх случаях вы получаете +2 очка.'},
    'Joueur 1 deconnecte': {'en': 'Player 1 disconnected', 'de': 'Spieler 1 getrennt', 'es': 'Jugador 1 desconectado', 'it': 'Giocatore 1 disconnesso', 'pt': 'Jogador 1 desconectado', 'zh': '玩家 1 已掉线', 'ja': 'プレイヤー1 切断', 'ko': '플레이어 1 연결 끊김', 'ru': 'Игрок 1 отключился'},
})


TRANSLATIONS.update({
    'Le but du jeu': {'en': 'The goal', 'de': 'Das Spielziel', 'es': 'El objetivo', 'it': 'Lo scopo', 'zh': '游戏目标', 'ja': 'ゲームの目的', 'ko': '게임 목표', 'ru': 'Цель игры', 'pt': 'O objetivo'},
    "Bienvenue. À La Fuga, le but du jeu est d'emmener l'Héritier (pièce encadrée) jusqu'à sa zone de ralliement, à l'autre bout du plateau. Bien sûr, vous devrez aussi empêcher votre adversaire d'y parvenir. Il peut y parvenir par lui-même ou en étant poussé.": {'en': 'Welcome. In La Fuga, the goal is to bring your Heir (the framed piece) to its rally zone at the far end of the board. Of course, you must also stop your opponent from doing the same. The Heir can get there on its own or by being pushed.', 'de': 'Willkommen. Bei La Fuga ist das Ziel, deinen Erben (die umrahmte Figur) in seine Sammelzone am anderen Ende des Bretts zu bringen. Natürlich musst du auch deinen Gegner daran hindern. Der Erbe kann selbst dorthin gelangen oder geschoben werden.', 'es': 'Bienvenido. En La Fuga, el objetivo es llevar a tu Heredero (la pieza enmarcada) a su zona de reunión, al otro extremo del tablero. Por supuesto, también debes impedir que tu rival lo logre. El Heredero puede llegar por sí mismo o siendo empujado.', 'it': "Benvenuto. In La Fuga lo scopo è portare il tuo Erede (il pezzo incorniciato) nella sua zona di raduno, all'altro capo della scacchiera. Naturalmente devi anche impedire al tuo avversario di riuscirci. L'Erede può arrivarci da solo o venendo spinto.", 'zh': '欢迎。在《La Fuga》中，目标是把你的继承人（带框的棋子）带到棋盘另一端的集结区。当然，你也必须阻止对手做到这一点。继承人可以自己抵达，也可以被推动到达。', 'ja': 'ようこそ。La Fuga の目的は、あなたの後継者（枠で囲まれた駒）を盤の反対側にある集結ゾーンへ導くことです。もちろん、相手が同じことをするのも阻止しなければなりません。後継者は自力でも、押されても到達できます。', 'ko': '환영합니다. La Fuga의 목표는 후계자(테두리가 있는 말)를 반대편 끝의 집결 구역까지 데려가는 것입니다. 물론 상대가 그렇게 하는 것도 막아야 합니다. 후계자는 스스로 가거나 밀려서 도달할 수 있습니다.', 'ru': 'Добро пожаловать. В La Fuga цель — привести вашего Наследника (фигуру в рамке) в зону сбора на другом конце доски. Разумеется, нужно помешать сопернику сделать то же самое. Наследник может добраться сам или быть вытолкнутым туда.', 'pt': 'Bem-vindo. Em La Fuga, o objetivo é levar seu Herdeiro (a peça emoldurada) até sua zona de reunião, no outro extremo do tabuleiro. Claro, você também deve impedir que o adversário consiga. O Herdeiro pode chegar sozinho ou sendo empurrado.'},
    'Le déplacement': {'en': 'Movement', 'de': 'Die Bewegung', 'es': 'El movimiento', 'it': 'Il movimento', 'zh': '移动', 'ja': '移動', 'ko': '이동', 'ru': 'Перемещение', 'pt': 'O movimento'},
    "Clique sur l'Héritier pour le sélectionner.": {'en': 'Tap the Heir to select it.', 'de': 'Tippe auf den Erben, um ihn auszuwählen.', 'es': 'Toca al Heredero para seleccionarlo.', 'it': "Tocca l'Erede per selezionarlo.", 'zh': '点击继承人以选中它。', 'ja': '後継者をタップして選択します。', 'ko': '후계자를 눌러 선택하세요.', 'ru': 'Нажмите на Наследника, чтобы выбрать его.', 'pt': 'Toque no Herdeiro para selecioná-lo.'},
    "Toutes les pièces peuvent se déplacer d'une case dans n'importe quelle direction. Déplace l'Héritier sur une case voisine.": {'en': 'Every piece can move one square in any direction. Move the Heir to an adjacent square.', 'de': 'Jede Figur kann sich ein Feld in jede Richtung bewegen. Bewege den Erben auf ein Nachbarfeld.', 'es': 'Cada pieza puede moverse una casilla en cualquier dirección. Mueve al Heredero a una casilla contigua.', 'it': "Ogni pezzo può muoversi di una casella in qualsiasi direzione. Sposta l'Erede su una casella adiacente.", 'zh': '每个棋子都可以向任意方向移动一格。把继承人移动到相邻的格子。', 'ja': 'すべての駒は任意の方向へ1マス移動できます。後継者を隣のマスへ動かしましょう。', 'ko': '모든 말은 어느 방향으로든 한 칸 이동할 수 있습니다. 후계자를 인접한 칸으로 옮기세요.', 'ru': 'Каждая фигура может ходить на одну клетку в любом направлении. Переместите Наследника на соседнюю клетку.', 'pt': 'Cada peça pode mover-se uma casa em qualquer direção. Mova o Herdeiro para uma casa vizinha.'},
    'Pour valider ton coup, clique à nouveau sur la pièce, sur sa nouvelle case.': {'en': 'To confirm your move, tap the piece again on its new square.', 'de': 'Um deinen Zug zu bestätigen, tippe die Figur erneut auf ihrem neuen Feld an.', 'es': 'Para confirmar tu jugada, vuelve a tocar la pieza en su nueva casilla.', 'it': 'Per confermare la mossa, tocca di nuovo il pezzo sulla sua nuova casella.', 'zh': '要确认走子，请在新格子上再次点击该棋子。', 'ja': '手を確定するには、新しいマスの上で駒をもう一度タップします。', 'ko': '수를 확정하려면 새 칸에 있는 말을 다시 누르세요.', 'ru': 'Чтобы подтвердить ход, снова нажмите на фигуру на её новой клетке.', 'pt': 'Para confirmar sua jogada, toque na peça novamente em sua nova casa.'},
    'Parfait ! Clique sur « Suivant » pour continuer.': {'en': 'Perfect! Tap “Next” to continue.', 'de': 'Perfekt! Tippe auf „Weiter“, um fortzufahren.', 'es': '¡Perfecto! Toca «Siguiente» para continuar.', 'it': 'Perfetto! Tocca «Avanti» per continuare.', 'zh': '完美！点击“下一步”继续。', 'ja': '完璧です！「次へ」を押して続けます。', 'ko': '완벽합니다! “다음”을 눌러 계속하세요.', 'ru': 'Отлично! Нажмите «Далее», чтобы продолжить.', 'pt': 'Perfeito! Toque em «Próximo» para continuar.'},
    'La règle de contact': {'en': 'The contact rule', 'de': 'Die Kontaktregel', 'es': 'La regla de contacto', 'it': 'La regola del contatto', 'zh': '接触规则', 'ja': '接触のルール', 'ko': '접촉 규칙', 'ru': 'Правило контакта', 'pt': 'A regra de contato'},
    'Pour se déplacer, une pièce RONDE doit toucher une autre ronde (alliée ou adverse), et une pièce CARRÉE doit toucher une autre carrée. En vert : les pièces qui peuvent bouger. En rouge : les pièces bloquées (aucune pièce de leur forme à côté).': {'en': 'To move, a ROUND piece must touch another round piece (friendly or enemy), and a SQUARE piece must touch another square piece. In green: the pieces that can move. In red: the blocked pieces (no piece of their shape beside them).', 'de': 'Um sich zu bewegen, muss eine RUNDE Figur eine andere runde berühren (eigen oder gegnerisch), und eine ECKIGE Figur eine andere eckige. In Grün: die Figuren, die sich bewegen können. In Rot: die blockierten Figuren (keine Figur ihrer Form daneben).', 'es': 'Para moverse, una pieza REDONDA debe tocar otra redonda (aliada o enemiga), y una pieza CUADRADA debe tocar otra cuadrada. En verde: las piezas que pueden moverse. En rojo: las piezas bloqueadas (ninguna pieza de su forma al lado).', 'it': 'Per muoversi, un pezzo ROTONDO deve toccare un altro rotondo (alleato o avversario), e un pezzo QUADRATO deve toccare un altro quadrato. In verde: i pezzi che possono muoversi. In rosso: i pezzi bloccati (nessun pezzo della loro forma accanto).', 'zh': '要移动，圆形棋子必须接触另一枚圆形棋子（己方或对方），方形棋子必须接触另一枚方形棋子。绿色：可以移动的棋子。红色：被封锁的棋子（旁边没有同形棋子）。', 'ja': '移動するには、丸い駒は別の丸い駒（味方でも敵でも）に接していなければならず、四角い駒は別の四角い駒に接していなければなりません。緑：動ける駒。赤：動けない駒（隣に同じ形の駒がない）。', 'ko': '이동하려면 둥근 말은 다른 둥근 말(아군이든 적군이든)에, 사각 말은 다른 사각 말에 닿아 있어야 합니다. 초록색: 움직일 수 있는 말. 빨간색: 막힌 말(옆에 같은 모양의 말이 없음).', 'ru': 'Чтобы ходить, КРУГЛАЯ фигура должна касаться другой круглой (своей или чужой), а КВАДРАТНАЯ — другой квадратной. Зелёные: фигуры, которые могут ходить. Красные: заблокированные фигуры (рядом нет фигуры их формы).', 'pt': 'Para se mover, uma peça REDONDA deve tocar outra redonda (aliada ou inimiga), e uma peça QUADRADA deve tocar outra quadrada. Em verde: as peças que podem mover-se. Em vermelho: as peças bloqueadas (nenhuma peça da sua forma ao lado).'},
    'Le multisaut': {'en': 'The multi-jump', 'de': 'Der Mehrfachsprung', 'es': 'El multisalto', 'it': 'Il multisalto', 'zh': '连跳', 'ja': '連続ジャンプ', 'ko': '연속 점프', 'ru': 'Мультипрыжок', 'pt': 'O multissalto'},
    'Une pièce ronde saute par-dessus une autre ronde (alliée ou adverse), en ligne DROITE ou en DIAGONALE, et peut enchaîner les sauts ! Clique sur la Nurse.': {'en': 'A round piece jumps over another round piece (friendly or enemy), in a STRAIGHT line or DIAGONALLY, and can chain jumps! Tap the Nurse.', 'de': 'Eine runde Figur springt über eine andere runde (eigen oder gegnerisch), GERADE oder DIAGONAL, und kann Sprünge aneinanderreihen! Tippe auf die Amme.', 'es': 'Una pieza redonda salta sobre otra redonda (aliada o enemiga), en línea RECTA o en DIAGONAL, ¡y puede encadenar saltos! Toca a la Nodriza.', 'it': 'Un pezzo rotondo salta sopra un altro rotondo (alleato o avversario), in linea RETTA o in DIAGONALE, e può concatenare i salti! Tocca la Balia.', 'zh': '圆形棋子可以沿直线或对角线跳过另一枚圆形棋子（己方或对方），并且可以连续跳跃！点击乳母。', 'ja': '丸い駒は別の丸い駒（味方でも敵でも）を、直線または斜めに跳び越え、連続して跳べます！乳母をタップしましょう。', 'ko': '둥근 말은 다른 둥근 말(아군이든 적군이든)을 직선 또는 대각선으로 뛰어넘으며, 점프를 연이어 할 수 있습니다! 유모를 누르세요.', 'ru': 'Круглая фигура перепрыгивает через другую круглую (свою или чужую) по ПРЯМОЙ или по ДИАГОНАЛИ и может делать цепочку прыжков! Нажмите на Няньку.', 'pt': 'Uma peça redonda salta sobre outra redonda (aliada ou inimiga), em linha RETA ou na DIAGONAL, e pode encadear saltos! Toque na Ama.'},
    'Clique à nouveau sur la Nurse pour valider ton multisaut.': {'en': 'Tap the Nurse again to confirm your multi-jump.', 'de': 'Tippe erneut auf die Amme, um deinen Mehrfachsprung zu bestätigen.', 'es': 'Vuelve a tocar a la Nodriza para confirmar tu multisalto.', 'it': 'Tocca di nuovo la Balia per confermare il multisalto.', 'zh': '再次点击乳母以确认你的连跳。', 'ja': '乳母をもう一度タップして連続ジャンプを確定します。', 'ko': '유모를 다시 눌러 연속 점프를 확정하세요.', 'ru': 'Нажмите на Няньку ещё раз, чтобы подтвердить мультипрыжок.', 'pt': 'Toque na Ama novamente para confirmar seu multissalto.'},
    'Bravo ! Sauts droits et diagonaux : tu maîtrises le multisaut.': {'en': "Well done! Straight and diagonal jumps: you've mastered the multi-jump.", 'de': 'Gut gemacht! Gerade und diagonale Sprünge: Du beherrschst den Mehrfachsprung.', 'es': '¡Bien hecho! Saltos rectos y diagonales: dominas el multisalto.', 'it': 'Ben fatto! Salti dritti e diagonali: padroneggi il multisalto.', 'zh': '做得好！直跳和斜跳：你已经掌握了连跳。', 'ja': 'お見事！直線と斜めのジャンプ：連続ジャンプをマスターしました。', 'ko': '잘했습니다! 직선과 대각선 점프: 연속 점프를 익혔습니다.', 'ru': 'Отлично! Прямые и диагональные прыжки: вы освоили мультипрыжок.', 'pt': 'Muito bem! Saltos retos e diagonais: você domina o multissalto.'},
    'Fuguer en sautant': {'en': 'Fleeing by jumping', 'de': 'Fliehen durch Springen', 'es': 'Huir saltando', 'it': 'Fuggire saltando', 'zh': '跳跃出逃', 'ja': 'ジャンプで逃げる', 'ko': '점프로 탈출', 'ru': 'Побег прыжком', 'pt': 'Fugir saltando'},
    "L'Héritier peut lui aussi enchaîner les sauts, droits ou diagonaux, et même FUGUER en sautant. Clique sur l'Héritier.": {'en': 'The Heir can also chain jumps, straight or diagonal, and even FLEE by jumping. Tap the Heir.', 'de': 'Auch der Erbe kann Sprünge aneinanderreihen, gerade oder diagonal, und sogar durch Springen FLIEHEN. Tippe auf den Erben.', 'es': 'El Heredero también puede encadenar saltos, rectos o diagonales, e incluso HUIR saltando. Toca al Heredero.', 'it': "Anche l'Erede può concatenare salti, dritti o diagonali, e persino FUGGIRE saltando. Tocca l'Erede.", 'zh': '继承人同样可以连续跳跃，直跳或斜跳，甚至可以跳跃出逃！点击继承人。', 'ja': '後継者も直線や斜めのジャンプを連続でき、ジャンプで逃げ切る（フーグ）ことさえできます。後継者をタップしましょう。', 'ko': '후계자도 직선이나 대각선 점프를 이어서 할 수 있고, 점프로 탈출까지 할 수 있습니다. 후계자를 누르세요.', 'ru': 'Наследник тоже может делать цепочку прыжков, прямых или диагональных, и даже СБЕЖАТЬ прыжком. Нажмите на Наследника.', 'pt': 'O Herdeiro também pode encadear saltos, retos ou diagonais, e até FUGIR saltando. Toque no Herdeiro.'},
    "Fugue réussie ! L'Héritier a atteint son ralliement : VICTOIRE !": {'en': 'Successful escape! The Heir reached its rally zone: VICTORY!', 'de': 'Flucht gelungen! Der Erbe hat seine Sammelzone erreicht: SIEG!', 'es': '¡Huida lograda! El Heredero alcanzó su zona de reunión: ¡VICTORIA!', 'it': "Fuga riuscita! L'Erede ha raggiunto la sua zona di raduno: VITTORIA!", 'zh': '出逃成功！继承人抵达了集结区：胜利！', 'ja': 'フーグ成功！後継者が集結ゾーンに到達しました：勝利！', 'ko': '탈출 성공! 후계자가 집결 구역에 도달했습니다: 승리!', 'ru': 'Побег удался! Наследник достиг зоны сбора: ПОБЕДА!', 'pt': 'Fuga bem-sucedida! O Herdeiro chegou à sua zona de reunião: VITÓRIA!'},
    'Les unités': {'en': 'Units', 'de': 'Die Einheiten', 'es': 'Las unidades', 'it': 'Le unità', 'zh': '编队', 'ja': 'ユニット', 'ko': '유닛', 'ru': 'Отряды', 'pt': 'As unidades'},
    "Les pièces carrées d'un même camp qui se touchent, même en diagonale, forment une UNITÉ. Plusieurs pièces de la même unité peuvent se déplacer en même temps, dans la même direction. Déplaçons plusieurs pièces de l'unité en vert ; clique sur do2, qui sera la meneuse.": {'en': "Square pieces of the same side that touch, even diagonally, form a UNIT. Several pieces of the same unit can move together, in the same direction. Let's move several pieces of the green unit; tap do2, which will be the leader.", 'de': 'Eckige Figuren derselben Seite, die sich berühren – auch diagonal – bilden eine EINHEIT. Mehrere Figuren derselben Einheit können sich gemeinsam in dieselbe Richtung bewegen. Bewegen wir mehrere Figuren der grünen Einheit; tippe auf do2, die Anführerin.', 'es': 'Las piezas cuadradas del mismo bando que se tocan, incluso en diagonal, forman una UNIDAD. Varias piezas de la misma unidad pueden moverse juntas, en la misma dirección. Movamos varias piezas de la unidad verde; toca do2, que será la líder.', 'it': "I pezzi quadrati dello stesso schieramento che si toccano, anche in diagonale, formano un'UNITÀ. Più pezzi della stessa unità possono muoversi insieme, nella stessa direzione. Muoviamo più pezzi dell'unità verde; tocca do2, che sarà la guida.", 'zh': '同一方相互接触（包括对角接触）的方形棋子组成一个编队。同一编队的多枚棋子可以朝同一方向一起移动。让我们移动绿色编队中的几枚棋子；点击 do2，它将作为领队。', 'ja': '同じ陣営の四角い駒が、斜めも含めて接していると「ユニット」を作ります。同じユニットの複数の駒は、同じ方向へ一緒に動けます。緑のユニットの駒をいくつか動かしましょう。リーダーとなる do2 をタップします。', 'ko': '같은 편의 사각 말이 대각선으로라도 맞닿으면 유닛을 이룹니다. 같은 유닛의 여러 말은 같은 방향으로 함께 움직일 수 있습니다. 초록 유닛의 말 몇 개를 옮겨 봅시다. 리더가 될 do2를 누르세요.', 'ru': 'Квадратные фигуры одной стороны, соприкасающиеся даже по диагонали, образуют ОТРЯД. Несколько фигур одного отряда могут двигаться вместе в одном направлении. Подвинем несколько фигур зелёного отряда; нажмите do2 — это будет ведущая.', 'pt': 'As peças quadradas do mesmo lado que se tocam, mesmo na diagonal, formam uma UNIDADE. Várias peças da mesma unidade podem mover-se juntas, na mesma direção. Vamos mover várias peças da unidade verde; toque em do2, que será a líder.'},
    "Ajoute ré2 puis fa3 à la sélection (on laisse mi2 de côté : tu n'es pas obligé de tout prendre).": {'en': "Add ré2 then fa3 to the selection (we leave mi2 out: you don't have to take them all).", 'de': 'Füge ré2 und dann fa3 zur Auswahl hinzu (mi2 lassen wir weg: du musst nicht alle nehmen).', 'es': 'Añade ré2 y luego fa3 a la selección (dejamos mi2 fuera: no tienes que tomarlas todas).', 'it': 'Aggiungi ré2 e poi fa3 alla selezione (lasciamo fuori mi2: non sei obbligato a prenderle tutte).', 'zh': '把 ré2 然后 fa3 加入选择（我们把 mi2 留下：你不必全部选中）。', 'ja': 'ré2、続いて fa3 を選択に加えます（mi2 は外します：すべてを選ぶ必要はありません）。', 'ko': 'ré2 다음 fa3를 선택에 추가하세요 (mi2는 빼둡니다: 전부 고를 필요는 없습니다).', 'ru': 'Добавьте ré2, затем fa3 к выбору (mi2 оставляем: брать все необязательно).', 'pt': 'Adicione ré2 e depois fa3 à seleção (deixamos mi2 de fora: você não precisa pegar todas).'},
    "L'unité se déplace selon la meneuse. Clique en do3 pour monter les pièces choisies d'une case.": {'en': 'The unit moves according to the leader. Tap do3 to move the chosen pieces up one square.', 'de': 'Die Einheit bewegt sich gemäß der Anführerin. Tippe auf do3, um die gewählten Figuren ein Feld nach oben zu ziehen.', 'es': 'La unidad se mueve según la líder. Toca do3 para subir las piezas elegidas una casilla.', 'it': "L'unità si muove secondo la guida. Tocca do3 per salire di una casella con i pezzi scelti.", 'zh': '编队按领队移动。点击 do3，把所选棋子向上移动一格。', 'ja': 'ユニットはリーダーに従って動きます。do3 をタップして、選んだ駒を1マス上へ動かします。', 'ko': '유닛은 리더를 따라 움직입니다. do3를 눌러 선택한 말들을 한 칸 위로 올리세요.', 'ru': 'Отряд движется вслед за ведущей. Нажмите do3, чтобы поднять выбранные фигуры на одну клетку.', 'pt': 'A unidade se move conforme a líder. Toque em do3 para subir as peças escolhidas uma casa.'},
    'Clique sur la meneuse pour valider ton coup.': {'en': 'Tap the leader to confirm your move.', 'de': 'Tippe auf die Anführerin, um deinen Zug zu bestätigen.', 'es': 'Toca a la líder para confirmar tu jugada.', 'it': 'Tocca la guida per confermare la mossa.', 'zh': '点击领队以确认走子。', 'ja': 'リーダーをタップして手を確定します。', 'ko': '리더를 눌러 수를 확정하세요.', 'ru': 'Нажмите на ведущую, чтобы подтвердить ход.', 'pt': 'Toque na líder para confirmar sua jogada.'},
    "En montant, la pièce en fa s'est retrouvée seule (encadrée) ! Une manœuvre peut donc IMMOBILISER une pièce : fa n'a plus aucune carrée à côté.": {'en': 'By moving up, the piece on fa ended up alone (framed)! A maneuver can thus IMMOBILIZE a piece: fa no longer has any square piece beside it.', 'de': 'Beim Aufrücken blieb die Figur auf fa allein (umrahmt)! Ein Manöver kann also eine Figur LAHMLEGEN: fa hat keine eckige Figur mehr neben sich.', 'es': 'Al subir, la pieza en fa se quedó sola (enmarcada). Una maniobra puede así INMOVILIZAR una pieza: fa ya no tiene ninguna cuadrada al lado.', 'it': 'Salendo, il pezzo su fa è rimasto solo (incorniciato)! Una manovra può quindi IMMOBILIZZARE un pezzo: fa non ha più alcun quadrato accanto.', 'zh': '向上移动后，fa 上的棋子落了单（被框住）！因此一次调动可以使棋子被封锁：fa 旁边再也没有方形棋子了。', 'ja': '上に動いたことで、fa の駒が孤立しました（枠付き）！このように、手順次第で駒を動けなくできます：fa の隣にはもう四角い駒がありません。', 'ko': '위로 올라가면서 fa의 말이 홀로 남았습니다(테두리 표시)! 이렇게 기동으로 말을 묶을 수 있습니다: fa 옆에는 더 이상 사각 말이 없습니다.', 'ru': 'Поднявшись, фигура на fa осталась одна (в рамке)! Так манёвр может ОБЕЗДВИЖИТЬ фигуру: рядом с fa больше нет квадратной фигуры.', 'pt': 'Ao subir, a peça em fa ficou sozinha (emoldurada)! Uma manobra pode assim IMOBILIZAR uma peça: fa não tem mais nenhuma quadrada ao lado.'},
})


TRANSLATIONS.update({
    'La poussée : le Garde': {'en': 'Pushing: the Guard', 'de': 'Das Schieben: der Wächter', 'es': 'El empuje: el Guardia', 'it': 'La spinta: la Guardia', 'zh': '推动：卫兵', 'ja': '押し：衛兵', 'ko': '밀기: 근위병', 'ru': 'Толчок: Страж', 'pt': 'O empurrão: o Guarda'},
    'Le GARDE (croix ×) se déplace en diagonale et POUSSE en ligne droite. Clique sur le Garde.': {'en': 'The GUARD (× cross) moves diagonally and PUSHES in a straight line. Tap the Guard.', 'de': 'Der WÄCHTER (×-Kreuz) zieht diagonal und SCHIEBT geradlinig. Tippe auf den Wächter.', 'es': 'El GUARDIA (cruz ×) se mueve en diagonal y EMPUJA en línea recta. Toca al Guardia.', 'it': 'La GUARDIA (croce ×) si muove in diagonale e SPINGE in linea retta. Tocca la Guardia.', 'zh': '卫兵（× 十字）沿对角线移动，并沿直线推动。点击卫兵。', 'ja': '衛兵（×の十字）は斜めに動き、直線方向に押します。衛兵をタップしましょう。', 'ko': '근위병(× 십자)은 대각선으로 이동하고 직선으로 밉니다. 근위병을 누르세요.', 'ru': 'СТРАЖ (крест ×) ходит по диагонали и ТОЛКАЕТ по прямой. Нажмите на Стража.', 'pt': 'O GUARDA (cruz ×) move-se na diagonal e EMPURRA em linha reta. Toque no Guarda.'},
    "Déplace le Garde en diagonale, jusqu'en fa4.": {'en': 'Move the Guard diagonally, to fa4.', 'de': 'Ziehe den Wächter diagonal nach fa4.', 'es': 'Mueve al Guardia en diagonal, hasta fa4.', 'it': 'Sposta la Guardia in diagonale, fino a fa4.', 'zh': '把卫兵沿对角线移动到 fa4。', 'ja': '衛兵を斜めに fa4 まで動かします。', 'ko': '근위병을 대각선으로 fa4까지 옮기세요.', 'ru': 'Переместите Стража по диагонали на fa4.', 'pt': 'Mova o Guarda na diagonal, até fa4.'},
    "Maintenant POUSSE : clique en sol4. Toute la ligne est repoussée d'une case, et la pièce du bord tombe du plateau (éliminée) !": {'en': 'Now PUSH: tap sol4. The whole line is pushed back one square, and the piece at the edge falls off the board (eliminated)!', 'de': 'Jetzt SCHIEBEN: tippe auf sol4. Die ganze Reihe wird ein Feld zurückgeschoben, und die Figur am Rand fällt vom Brett (eliminiert)!', 'es': 'Ahora EMPUJA: toca sol4. Toda la fila retrocede una casilla, y la pieza del borde cae del tablero (¡eliminada!).', 'it': "Ora SPINGI: tocca sol4. L'intera fila è respinta di una casella, e il pezzo sul bordo cade dalla scacchiera (eliminato)!", 'zh': '现在推动：点击 sol4。整行被推后一格，边缘的棋子掉出棋盘（被淘汰）！', 'ja': 'では押します：sol4 をタップ。列全体が1マス押し戻され、端の駒が盤外に落ちます（除外）！', 'ko': '이제 미세요: sol4를 누르세요. 줄 전체가 한 칸 밀리고, 가장자리의 말이 판 밖으로 떨어집니다(제거)!', 'ru': 'Теперь ТОЛКНИТЕ: нажмите sol4. Весь ряд сдвигается на клетку, и фигура с края падает с доски (устранена)!', 'pt': 'Agora EMPURRE: toque em sol4. Toda a linha é empurrada uma casa, e a peça da borda cai do tabuleiro (eliminada)!'},
    'Clique sur le Garde pour valider ton coup.': {'en': 'Tap the Guard to confirm your move.', 'de': 'Tippe auf den Wächter, um deinen Zug zu bestätigen.', 'es': 'Toca al Guardia para confirmar tu jugada.', 'it': 'Tocca la Guardia per confermare la mossa.', 'zh': '点击卫兵以确认走子。', 'ja': '衛兵をタップして手を確定します。', 'ko': '근위병을 눌러 수를 확정하세요.', 'ru': 'Нажмите на Стража, чтобы подтвердить ход.', 'pt': 'Toque no Guarda para confirmar sua jogada.'},
    "Bravo ! Le Garde a poussé la ligne et éliminé une pièce. C'est le SEUL moyen d'éliminer une pièce : la pousser hors du plateau. Et tu peux même éliminer tes PROPRES pièces !": {'en': 'Well done! The Guard pushed the line and eliminated a piece. This is the ONLY way to eliminate a piece: push it off the board. And you can even eliminate your OWN pieces!', 'de': 'Gut gemacht! Der Wächter hat die Reihe geschoben und eine Figur eliminiert. Das ist die EINZIGE Art, eine Figur zu eliminieren: sie vom Brett schieben. Und du kannst sogar deine EIGENEN Figuren eliminieren!', 'es': '¡Bien hecho! El Guardia empujó la fila y eliminó una pieza. Es la ÚNICA forma de eliminar una pieza: empujarla fuera del tablero. ¡Y puedes incluso eliminar tus PROPIAS piezas!', 'it': "Ben fatto! La Guardia ha spinto la fila ed eliminato un pezzo. È l'UNICO modo di eliminare un pezzo: spingerlo fuori dalla scacchiera. E puoi persino eliminare i TUOI pezzi!", 'zh': '做得好！卫兵推动整行并淘汰了一枚棋子。这是淘汰棋子的唯一方法：把它推出棋盘。你甚至可以淘汰自己的棋子！', 'ja': 'お見事！衛兵が列を押し、駒を1つ除外しました。駒を除外する唯一の方法は、盤の外へ押し出すことです。しかも自分の駒さえ除外できます！', 'ko': '잘했습니다! 근위병이 줄을 밀어 말 하나를 제거했습니다. 말을 제거하는 유일한 방법은 판 밖으로 미는 것입니다. 심지어 자기 말도 제거할 수 있습니다!', 'ru': 'Отлично! Страж толкнул ряд и устранил фигуру. Это ЕДИНСТВЕННЫЙ способ убрать фигуру — вытолкнуть её с доски. И вы можете убрать даже СВОИ фигуры!', 'pt': 'Muito bem! O Guarda empurrou a linha e eliminou uma peça. Esta é a ÚNICA forma de eliminar uma peça: empurrá-la para fora do tabuleiro. E você pode até eliminar suas PRÓPRIAS peças!'},
    'La poussée : le Soldat': {'en': 'Pushing: the Soldier', 'de': 'Das Schieben: der Soldat', 'es': 'El empuje: el Soldado', 'it': 'La spinta: il Soldato', 'zh': '推动：士兵', 'ja': '押し：兵士', 'ko': '밀기: 병사', 'ru': 'Толчок: Солдат', 'pt': 'O empurrão: o Soldado'},
    'Le SOLDAT (croix +) se déplace en ligne droite et POUSSE en diagonale. Clique sur le Soldat.': {'en': 'The SOLDIER (+ cross) moves in a straight line and PUSHES diagonally. Tap the Soldier.', 'de': 'Der SOLDAT (+-Kreuz) zieht geradlinig und SCHIEBT diagonal. Tippe auf den Soldaten.', 'es': 'El SOLDADO (cruz +) se mueve en línea recta y EMPUJA en diagonal. Toca al Soldado.', 'it': 'Il SOLDATO (croce +) si muove in linea retta e SPINGE in diagonale. Tocca il Soldato.', 'zh': '士兵（+ 十字）沿直线移动，并沿对角线推动。点击士兵。', 'ja': '兵士（+の十字）は直線に動き、斜め方向に押します。兵士をタップしましょう。', 'ko': '병사(+ 십자)는 직선으로 이동하고 대각선으로 밉니다. 병사를 누르세요.', 'ru': 'СОЛДАТ (крест +) ходит по прямой и ТОЛКАЕТ по диагонали. Нажмите на Солдата.', 'pt': 'O SOLDADO (cruz +) move-se em linha reta e EMPURRA na diagonal. Toque no Soldado.'},
    'Déplace le Soldat tout droit, en do4.': {'en': 'Move the Soldier straight, to do4.', 'de': 'Ziehe den Soldaten gerade nach do4.', 'es': 'Mueve al Soldado en línea recta, hasta do4.', 'it': 'Sposta il Soldato in linea retta, fino a do4.', 'zh': '把士兵沿直线移动到 do4。', 'ja': '兵士をまっすぐ do4 まで動かします。', 'ko': '병사를 직선으로 do4까지 옮기세요.', 'ru': 'Переместите Солдата по прямой на do4.', 'pt': 'Mova o Soldado em linha reta, até do4.'},
    'POUSSE en diagonale : clique en ré5 pour repousser la pièce.': {'en': 'PUSH diagonally: tap ré5 to push the piece back.', 'de': 'Schiebe DIAGONAL: tippe auf ré5, um die Figur zurückzuschieben.', 'es': 'EMPUJA en diagonal: toca ré5 para desplazar la pieza.', 'it': 'SPINGI in diagonale: tocca ré5 per respingere il pezzo.', 'zh': '沿对角线推动：点击 ré5 把棋子推开。', 'ja': '斜めに押します：ré5 をタップして駒を押し出します。', 'ko': '대각선으로 미세요: ré5를 눌러 말을 밀어내세요.', 'ru': 'ТОЛКНИТЕ по диагонали: нажмите ré5, чтобы оттолкнуть фигуру.', 'pt': 'EMPURRE na diagonal: toque em ré5 para empurrar a peça.'},
    'Clique sur le Soldat pour valider ton coup.': {'en': 'Tap the Soldier to confirm your move.', 'de': 'Tippe auf den Soldaten, um deinen Zug zu bestätigen.', 'es': 'Toca al Soldado para confirmar tu jugada.', 'it': 'Tocca il Soldato per confermare la mossa.', 'zh': '点击士兵以确认走子。', 'ja': '兵士をタップして手を確定します。', 'ko': '병사를 눌러 수를 확정하세요.', 'ru': 'Нажмите на Солдата, чтобы подтвердить ход.', 'pt': 'Toque no Soldado para confirmar sua jogada.'},
    "Attention : en se déplaçant, le Soldat s'est éloigné de son allié et n'a plus de carrée à côté, il est maintenant BLOQUÉ (encadré) jusqu'à ce qu'une carrée le rejoigne.": {'en': 'Careful: by moving, the Soldier moved away from its ally and no longer has a square piece beside it; it is now BLOCKED (framed) until a square piece joins it.', 'de': 'Achtung: Durch den Zug entfernte sich der Soldat von seinem Verbündeten und hat keine eckige Figur mehr neben sich; er ist jetzt BLOCKIERT (umrahmt), bis eine eckige Figur zu ihm stößt.', 'es': 'Cuidado: al moverse, el Soldado se alejó de su aliado y ya no tiene una cuadrada al lado; ahora está BLOQUEADO (enmarcado) hasta que una cuadrada se le una.', 'it': 'Attenzione: muovendosi, il Soldato si è allontanato dal suo alleato e non ha più un quadrato accanto; ora è BLOCCATO (incorniciato) finché un quadrato non lo raggiunge.', 'zh': '注意：士兵移动后远离了同伴，旁边不再有方形棋子，现在它被封锁（带框），直到有方形棋子靠近它。', 'ja': '注意：兵士は動いたことで味方から離れ、隣に四角い駒がなくなりました。今は四角い駒が来るまで動けません（枠付き）。', 'ko': '주의: 병사가 움직이면서 아군에게서 멀어져 옆에 사각 말이 없어졌습니다. 이제 사각 말이 올 때까지 막혀 있습니다(테두리 표시).', 'ru': 'Осторожно: сделав ход, Солдат отдалился от союзника, и рядом больше нет квадратной фигуры; теперь он ЗАБЛОКИРОВАН (в рамке), пока к нему не подойдёт квадратная фигура.', 'pt': 'Cuidado: ao mover-se, o Soldado afastou-se do aliado e não tem mais uma quadrada ao lado; agora está BLOQUEADO (emoldurado) até que uma quadrada se junte a ele.'},
    'Pousser plusieurs directions': {'en': 'Pushing in several directions', 'de': 'In mehrere Richtungen schieben', 'es': 'Empujar en varias direcciones', 'it': 'Spingere in più direzioni', 'zh': '向多个方向推动', 'ja': '複数方向へ押す', 'ko': '여러 방향으로 밀기', 'ru': 'Толчок в несколько сторон', 'pt': 'Empurrar em várias direções'},
    "Après s'être déplacée, une carrée peut pousser dans PLUSIEURS directions, autant que tu veux. Clique sur le Garde.": {'en': 'After moving, a square piece can push in SEVERAL directions, as many as you like. Tap the Guard.', 'de': 'Nach dem Ziehen kann eine eckige Figur in MEHRERE Richtungen schieben, so viele du willst. Tippe auf den Wächter.', 'es': 'Tras moverse, una cuadrada puede empujar en VARIAS direcciones, tantas como quieras. Toca al Guardia.', 'it': 'Dopo essersi mosso, un quadrato può spingere in PIÙ direzioni, quante ne vuoi. Tocca la Guardia.', 'zh': '移动之后，方形棋子可以向多个方向推动，想推几次都行。点击卫兵。', 'ja': '移動した後、四角い駒は好きなだけ複数の方向へ押せます。衛兵をタップしましょう。', 'ko': '이동한 뒤, 사각 말은 원하는 만큼 여러 방향으로 밀 수 있습니다. 근위병을 누르세요.', 'ru': 'После хода квадратная фигура может толкать в НЕСКОЛЬКИХ направлениях, сколько угодно. Нажмите на Стража.', 'pt': 'Depois de mover-se, uma quadrada pode empurrar em VÁRIAS direções, quantas quiser. Toque no Guarda.'},
    'Déplace le Garde en diagonale, en fa4.': {'en': 'Move the Guard diagonally, to fa4.', 'de': 'Ziehe den Wächter diagonal nach fa4.', 'es': 'Mueve al Guardia en diagonal, a fa4.', 'it': 'Sposta la Guardia in diagonale, a fa4.', 'zh': '把卫兵沿对角线移动到 fa4。', 'ja': '衛兵を斜めに fa4 へ動かします。', 'ko': '근위병을 대각선으로 fa4로 옮기세요.', 'ru': 'Переместите Стража по диагонали на fa4.', 'pt': 'Mova o Guarda na diagonal, para fa4.'},
    "Bravo ! Tu as poussé en haut et à droite. Remarque : fa3 (en bas) pouvait aussi être poussée, mais on l'a laissée, c'est toi qui choisis quelles directions pousser.": {'en': 'Well done! You pushed up and to the right. Note: fa3 (below) could also have been pushed, but we left it — you choose which directions to push.', 'de': 'Gut gemacht! Du hast nach oben und nach rechts geschoben. Beachte: fa3 (unten) hätte auch geschoben werden können, aber wir ließen es – du wählst, in welche Richtungen du schiebst.', 'es': '¡Bien hecho! Empujaste hacia arriba y hacia la derecha. Nota: fa3 (abajo) también podía empujarse, pero la dejamos: tú eliges en qué direcciones empujar.', 'it': "Ben fatto! Hai spinto in alto e a destra. Nota: anche fa3 (in basso) poteva essere spinto, ma l'abbiamo lasciato: sei tu a scegliere in quali direzioni spingere.", 'zh': '做得好！你向上和向右推动了。注意：fa3（下方）本也可以被推动，但我们没推——由你决定往哪些方向推。', 'ja': 'お見事！上と右へ押しました。なお、fa3（下）も押せましたが残しました。どの方向へ押すかはあなたが選びます。', 'ko': '잘했습니다! 위쪽과 오른쪽으로 밀었습니다. 참고: fa3(아래)도 밀 수 있었지만 남겨 두었습니다. 어느 방향으로 밀지는 당신이 정합니다.', 'ru': 'Отлично! Вы толкнули вверх и вправо. Заметьте: fa3 (внизу) тоже можно было толкнуть, но мы оставили её — вы сами выбираете, в какие стороны толкать.', 'pt': 'Muito bem! Você empurrou para cima e para a direita. Nota: fa3 (abaixo) também podia ser empurrada, mas a deixamos — você escolhe em quais direções empurrar.'},
    'Fuguer en poussant': {'en': 'Fleeing by pushing', 'de': 'Fliehen durch Schieben', 'es': 'Huir empujando', 'it': 'Fuggire spingendo', 'zh': '推动出逃', 'ja': '押して逃げる', 'ko': '밀어서 탈출', 'ru': 'Побег толчком', 'pt': 'Fugir empurrando'},
    'On peut aussi POUSSER son propre Héritier ! Clique sur le Garde.': {'en': 'You can also PUSH your own Heir! Tap the Guard.', 'de': 'Du kannst auch deinen eigenen Erben SCHIEBEN! Tippe auf den Wächter.', 'es': '¡También puedes EMPUJAR a tu propio Heredero! Toca al Guardia.', 'it': 'Puoi anche SPINGERE il tuo stesso Erede! Tocca la Guardia.', 'zh': '你也可以推动自己的继承人！点击卫兵。', 'ja': '自分の後継者を押すこともできます！衛兵をタップしましょう。', 'ko': '자기 후계자를 밀 수도 있습니다! 근위병을 누르세요.', 'ru': 'Вы также можете ТОЛКНУТЬ собственного Наследника! Нажмите на Стража.', 'pt': 'Você também pode EMPURRAR o seu próprio Herdeiro! Toque no Guarda.'},
    "Déplace le Garde en diagonale, en fa7 (sous l'Héritier).": {'en': 'Move the Guard diagonally, to fa7 (below the Heir).', 'de': 'Ziehe den Wächter diagonal nach fa7 (unter den Erben).', 'es': 'Mueve al Guardia en diagonal, a fa7 (debajo del Heredero).', 'it': "Sposta la Guardia in diagonale, a fa7 (sotto l'Erede).", 'zh': '把卫兵沿对角线移动到 fa7（继承人下方）。', 'ja': '衛兵を斜めに fa7（後継者の下）へ動かします。', 'ko': '근위병을 대각선으로 fa7(후계자 아래)로 옮기세요.', 'ru': 'Переместите Стража по диагонали на fa7 (под Наследником).', 'pt': 'Mova o Guarda na diagonal, para fa7 (abaixo do Herdeiro).'},
    "POUSSE vers le haut : clique en fa8. L'Héritier est poussé dans son ralliement !": {'en': 'PUSH upward: tap fa8. The Heir is pushed into its rally zone!', 'de': 'Schiebe nach OBEN: tippe auf fa8. Der Erbe wird in seine Sammelzone geschoben!', 'es': 'EMPUJA hacia arriba: toca fa8. ¡El Heredero es empujado a su zona de reunión!', 'it': "SPINGI verso l'alto: tocca fa8. L'Erede è spinto nella sua zona di raduno!", 'zh': '向上推动：点击 fa8。继承人被推入自己的集结区！', 'ja': '上へ押します：fa8 をタップ。後継者が集結ゾーンへ押し込まれます！', 'ko': '위로 미세요: fa8을 누르세요. 후계자가 집결 구역으로 밀려 들어갑니다!', 'ru': 'ТОЛКНИТЕ вверх: нажмите fa8. Наследник вытолкнут в свою зону сбора!', 'pt': 'EMPURRE para cima: toque em fa8. O Herdeiro é empurrado para sua zona de reunião!'},
    'Fugue ! Tu as poussé ton Héritier dans son ralliement : VICTOIRE !': {'en': 'Escape! You pushed your Heir into its rally zone: VICTORY!', 'de': 'Flucht! Du hast deinen Erben in seine Sammelzone geschoben: SIEG!', 'es': '¡Huida! Empujaste a tu Heredero a su zona de reunión: ¡VICTORIA!', 'it': 'Fuga! Hai spinto il tuo Erede nella sua zona di raduno: VITTORIA!', 'zh': '出逃！你把自己的继承人推入了集结区：胜利！', 'ja': 'フーグ！後継者を集結ゾーンへ押し込みました：勝利！', 'ko': '탈출! 후계자를 집결 구역으로 밀어 넣었습니다: 승리!', 'ru': 'Побег! Вы втолкнули своего Наследника в зону сбора: ПОБЕДА!', 'pt': 'Fuga! Você empurrou seu Herdeiro para a zona de reunião: VITÓRIA!'},
    'Mater en poussant': {'en': 'Mating by pushing', 'de': 'Mattsetzen durch Schieben', 'es': 'Dar mate empujando', 'it': 'Dare matto spingendo', 'zh': '推动将杀', 'ja': '押して詰ます', 'ko': '밀어서 메이트', 'ru': 'Мат толчком', 'pt': 'Dar mate empurrando'},
    "Enfin, pousser l'Héritier ADVERSE hors du plateau le met MAT. Clique sur le Garde.": {'en': "Finally, pushing the OPPONENT's Heir off the board checkmates it. Tap the Guard.", 'de': 'Schließlich setzt das Schieben des GEGNERISCHEN Erben vom Brett ihn matt. Tippe auf den Wächter.', 'es': 'Por último, empujar al Heredero RIVAL fuera del tablero lo deja en MATE. Toca al Guardia.', 'it': "Infine, spingere l'Erede AVVERSARIO fuori dalla scacchiera lo mette in MATTO. Tocca la Guardia.", 'zh': '最后，把对方的继承人推出棋盘即将其将杀。点击卫兵。', 'ja': '最後に、相手の後継者を盤外へ押し出すと詰みになります。衛兵をタップしましょう。', 'ko': '마지막으로, 상대 후계자를 판 밖으로 밀면 메이트가 됩니다. 근위병을 누르세요.', 'ru': 'Наконец, выталкивание Наследника СОПЕРНИКА с доски ставит ему мат. Нажмите на Стража.', 'pt': 'Por fim, empurrar o Herdeiro do ADVERSÁRIO para fora do tabuleiro o deixa em MATE. Toque no Guarda.'},
    "Déplace le Garde en diagonale, en la7 (sous l'Héritier adverse).": {'en': 'Move the Guard diagonally, to la7 (below the enemy Heir).', 'de': 'Ziehe den Wächter diagonal nach la7 (unter den gegnerischen Erben).', 'es': 'Mueve al Guardia en diagonal, a la7 (debajo del Heredero rival).', 'it': "Sposta la Guardia in diagonale, a la7 (sotto l'Erede avversario).", 'zh': '把卫兵沿对角线移动到 la7（对方继承人下方）。', 'ja': '衛兵を斜めに la7（相手の後継者の下）へ動かします。', 'ko': '근위병을 대각선으로 la7(상대 후계자 아래)로 옮기세요.', 'ru': 'Переместите Стража по диагонали на la7 (под Наследником соперника).', 'pt': 'Mova o Guarda na diagonal, para la7 (abaixo do Herdeiro adversário).'},
    "POUSSE vers le haut : clique en la8. L'Héritier adverse est éjecté du plateau !": {'en': 'PUSH upward: tap la8. The enemy Heir is ejected from the board!', 'de': 'Schiebe nach OBEN: tippe auf la8. Der gegnerische Erbe wird vom Brett geworfen!', 'es': 'EMPUJA hacia arriba: toca la8. ¡El Heredero rival es expulsado del tablero!', 'it': "SPINGI verso l'alto: tocca la8. L'Erede avversario è espulso dalla scacchiera!", 'zh': '向上推动：点击 la8。对方的继承人被逐出棋盘！', 'ja': '上へ押します：la8 をタップ。相手の後継者が盤外へ弾き出されます！', 'ko': '위로 미세요: la8을 누르세요. 상대 후계자가 판 밖으로 밀려납니다!', 'ru': 'ТОЛКНИТЕ вверх: нажмите la8. Наследник соперника вытолкнут с доски!', 'pt': 'EMPURRE para cima: toque em la8. O Herdeiro adversário é expulso do tabuleiro!'},
    "Mat ! Tu as poussé l'Héritier adverse hors du plateau : VICTOIRE !": {'en': 'Checkmate! You pushed the enemy Heir off the board: VICTORY!', 'de': 'Matt! Du hast den gegnerischen Erben vom Brett geschoben: SIEG!', 'es': '¡Mate! Empujaste al Heredero rival fuera del tablero: ¡VICTORIA!', 'it': "Matto! Hai spinto l'Erede avversario fuori dalla scacchiera: VITTORIA!", 'zh': '将杀！你把对方的继承人推出了棋盘：胜利！', 'ja': '詰み！相手の後継者を盤外へ押し出しました：勝利！', 'ko': '메이트! 상대 후계자를 판 밖으로 밀어냈습니다: 승리!', 'ru': 'Мат! Вы вытолкнули Наследника соперника с доски: ПОБЕДА!', 'pt': 'Mate! Você empurrou o Herdeiro adversário para fora do tabuleiro: VITÓRIA!'},
})


TRANSLATIONS.update({
    'Le Chevalier': {'en': 'The Knight', 'de': 'Der Ritter', 'es': 'El Caballero', 'it': 'Il Cavaliere', 'zh': '骑士', 'ja': '騎士', 'ko': '기사', 'ru': 'Рыцарь', 'pt': 'O Cavaleiro'},
    "Le CHEVALIER (l'hexagone) est une pièce à part, avec deux pouvoirs. INÉBRANLABLE : il ne peut jamais être poussé, une poussée s'arrête net sur lui. INDÉPENDANT : il peut se déplacer même s'il ne touche aucune pièce de sa forme (il n'a pas besoin de voisine pour bouger).": {'en': 'The KNIGHT (the hexagon) is a special piece with two powers. UNSHAKABLE: it can never be pushed; a push stops dead against it. INDEPENDENT: it can move even if it touches no piece of its shape (it needs no neighbor to move).', 'de': 'Der RITTER (das Sechseck) ist eine besondere Figur mit zwei Kräften. UNERSCHÜTTERLICH: Er kann nie geschoben werden; ein Schub stoppt an ihm. UNABHÄNGIG: Er kann sich bewegen, auch ohne eine Figur seiner Form zu berühren (er braucht keinen Nachbarn).', 'es': 'El CABALLERO (el hexágono) es una pieza especial con dos poderes. INQUEBRANTABLE: nunca puede ser empujado; un empuje se detiene en seco contra él. INDEPENDIENTE: puede moverse aunque no toque ninguna pieza de su forma (no necesita vecina para moverse).', 'it': "Il CAVALIERE (l'esagono) è un pezzo speciale con due poteri. IRREMOVIBILE: non può mai essere spinto; una spinta si ferma di netto contro di lui. INDIPENDENTE: può muoversi anche se non tocca alcun pezzo della sua forma (non ha bisogno di una vicina).", 'zh': '骑士（六边形）是一枚特殊棋子，拥有两种能力。不可撼动：永远不能被推动，推动到它这里就会停下。独立：即使不接触任何同形棋子也能移动（无需邻子即可行动）。', 'ja': '騎士（六角形）は二つの力を持つ特別な駒です。不動：決して押されず、押しは騎士の手前で止まります。独立：同じ形の駒に接していなくても動けます（動くのに隣の駒を必要としません）。', 'ko': '기사(육각형)는 두 가지 능력을 가진 특별한 말입니다. 불굴: 결코 밀리지 않으며, 밀기는 기사 앞에서 멈춥니다. 독립: 같은 모양의 말에 닿지 않아도 움직일 수 있습니다(옆의 말이 필요 없습니다).', 'ru': 'РЫЦАРЬ (шестиугольник) — особая фигура с двумя способностями. НЕСОКРУШИМЫЙ: его нельзя толкнуть; толчок останавливается прямо перед ним. НЕЗАВИСИМЫЙ: он может ходить, даже не касаясь фигур своей формы (для хода ему не нужен сосед).', 'pt': 'O CAVALEIRO (o hexágono) é uma peça especial com dois poderes. INABALÁVEL: nunca pode ser empurrado; um empurrão para de imediato contra ele. INDEPENDENTE: pode mover-se mesmo sem tocar em nenhuma peça da sua forma (não precisa de vizinha para mover-se).'},
    'Le Chevalier bloque': {'en': 'The Knight blocks', 'de': 'Der Ritter blockiert', 'es': 'El Caballero bloquea', 'it': 'Il Cavaliere blocca', 'zh': '骑士的封锁', 'ja': '騎士は防ぐ', 'ko': '기사의 봉쇄', 'ru': 'Рыцарь блокирует', 'pt': 'O Cavaleiro bloqueia'},
    "Puisqu'il ne peut être poussé, le Chevalier sert de MUR : il bloque les poussées. Ici, même si le Garde adverse s'avance en fa3 pour pousser vers le haut, le Chevalier (fa4) arrête tout : l'Héritier (fa5) est protégé.": {'en': "Since it can't be pushed, the Knight acts as a WALL: it blocks pushes. Here, even if the enemy Guard advances to fa3 to push upward, the Knight (fa4) stops everything: the Heir (fa5) is protected.", 'de': 'Da er nicht geschoben werden kann, dient der Ritter als MAUER: Er blockiert Schübe. Selbst wenn der gegnerische Wächter nach fa3 vorrückt, um nach oben zu schieben, stoppt der Ritter (fa4) alles: der Erbe (fa5) ist geschützt.', 'es': 'Como no puede ser empujado, el Caballero actúa como un MURO: bloquea los empujes. Aquí, aunque el Guardia rival avance a fa3 para empujar hacia arriba, el Caballero (fa4) lo detiene todo: el Heredero (fa5) está protegido.', 'it': "Poiché non può essere spinto, il Cavaliere funge da MURO: blocca le spinte. Qui, anche se la Guardia avversaria avanza in fa3 per spingere verso l'alto, il Cavaliere (fa4) ferma tutto: l'Erede (fa5) è protetto.", 'zh': '由于不能被推动，骑士就像一堵墙：它挡住推动。这里，即使对方卫兵前进到 fa3 想向上推，骑士（fa4）也会挡住一切：继承人（fa5）受到保护。', 'ja': '押されないため、騎士は壁の役割を果たし、押しを防ぎます。ここでは、相手の衛兵が fa3 に進んで上へ押そうとしても、騎士（fa4）がすべてを止め、後継者（fa5）は守られます。', 'ko': '밀리지 않으므로 기사는 벽 역할을 하여 밀기를 막습니다. 여기서 상대 근위병이 fa3로 나아가 위로 밀려 해도, 기사(fa4)가 모두 막아 후계자(fa5)는 보호됩니다.', 'ru': 'Поскольку его нельзя толкнуть, Рыцарь служит СТЕНОЙ: он блокирует толчки. Здесь, даже если вражеский Страж выйдет на fa3, чтобы толкнуть вверх, Рыцарь (fa4) остановит всё: Наследник (fa5) защищён.', 'pt': 'Como não pode ser empurrado, o Cavaleiro atua como uma PAREDE: bloqueia os empurrões. Aqui, mesmo que o Guarda adversário avance para fa3 para empurrar para cima, o Cavaleiro (fa4) para tudo: o Herdeiro (fa5) está protegido.'},
    'Fins de partie': {'en': 'Endgames', 'de': 'Spielenden', 'es': 'Finales de partida', 'it': 'Finali di partita', 'zh': '对局结束方式', 'ja': '対局の終わり方', 'ko': '대국의 끝', 'ru': 'Окончания партии', 'pt': 'Fins de partida'},
    'Voici toutes les façons dont une partie peut se terminer, et combien de points chacune rapporte.': {'en': 'Here are all the ways a game can end, and how many points each one is worth.', 'de': 'Hier sind alle Arten, wie eine Partie enden kann, und wie viele Punkte jede bringt.', 'es': 'Estas son todas las formas en que puede terminar una partida, y cuántos puntos otorga cada una.', 'it': 'Ecco tutti i modi in cui una partita può finire, e quanti punti vale ciascuno.', 'zh': '以下是一局对局可能结束的所有方式，以及各自的得分。', 'ja': '対局が終わるすべての方法と、それぞれの得点を紹介します。', 'ko': '대국이 끝날 수 있는 모든 방식과 각각의 점수를 소개합니다.', 'ru': 'Вот все способы, которыми может закончиться партия, и сколько очков даёт каждый.', 'pt': 'Aqui estão todas as formas de uma partida terminar, e quantos pontos cada uma vale.'},
    'Fin : la fugue': {'en': 'Ending: the escape', 'de': 'Ende: die Flucht', 'es': 'Final: la huida', 'it': 'Finale: la fuga', 'zh': '结束：出逃', 'ja': '終局：フーグ', 'ko': '엔딩: 탈출', 'ru': 'Финал: побег', 'pt': 'Fim: a fuga'},
    "FUGUE (+2 points). Ton Héritier atteint son ralliement (la flèche) : tu gagnes la partie ! C'est la victoire la plus valorisée. Une Nurse à son contact lui permet de bouger.": {'en': "ESCAPE (+2 points). Your Heir reaches its rally zone (the arrow): you win the game! It's the most valued victory. A Nurse in contact lets it move.", 'de': 'FLUCHT (+2 Punkte). Dein Erbe erreicht seine Sammelzone (der Pfeil): Du gewinnst die Partie! Es ist der wertvollste Sieg. Eine Amme in Kontakt lässt ihn ziehen.', 'es': 'HUIDA (+2 puntos). Tu Heredero alcanza su zona de reunión (la flecha): ¡ganas la partida! Es la victoria más valorada. Una Nodriza en contacto le permite moverse.', 'it': 'FUGA (+2 punti). Il tuo Erede raggiunge la sua zona di raduno (la freccia): vinci la partita! È la vittoria più preziosa. Una Balia a contatto gli permette di muoversi.', 'zh': '出逃（+2 分）。你的继承人抵达集结区（箭头处）：你赢得对局！这是最有价值的胜利。与其接触的乳母可让它移动。', 'ja': 'フーグ（+2点）。後継者が集結ゾーン（矢印）に到達：対局に勝利！最も価値の高い勝ち方です。接している乳母がいれば動けます。', 'ko': '탈출(+2점). 후계자가 집결 구역(화살표)에 도달: 대국 승리! 가장 값진 승리입니다. 접해 있는 유모가 있으면 움직일 수 있습니다.', 'ru': 'ПОБЕГ (+2 очка). Ваш Наследник достигает зоны сбора (стрелка): вы выигрываете партию! Это самая ценная победа. Соприкасающаяся Нянька позволяет ему ходить.', 'pt': 'FUGA (+2 pontos). Seu Herdeiro chega à zona de reunião (a seta): você vence a partida! É a vitória mais valorizada. Uma Ama em contato permite que ele se mova.'},
    'Fin : la double fugue': {'en': 'Ending: the double escape', 'de': 'Ende: die Doppelflucht', 'es': 'Final: la doble huida', 'it': 'Finale: la doppia fuga', 'zh': '结束：双出逃', 'ja': '終局：ダブルフーグ', 'ko': '엔딩: 이중 탈출', 'ru': 'Финал: двойной побег', 'pt': 'Fim: a dupla fuga'},
    "DOUBLE FUGUE (0 point). Quand les Blancs fuguent, les Noirs ont droit à un DERNIER coup pour égaliser. Si les deux Héritiers rejoignent leur ralliement, la partie est nulle. Ici, c'est aux Blancs de jouer, et les deux Héritiers peuvent fuguer (flèches).": {'en': "DOUBLE ESCAPE (0 points). When White escapes, Black gets a LAST move to equalize. If both Heirs reach their rally zone, the game is drawn. Here it's White to move, and both Heirs can escape (arrows).", 'de': 'DOPPELFLUCHT (0 Punkte). Wenn Weiß flieht, erhält Schwarz einen LETZTEN Zug zum Ausgleich. Erreichen beide Erben ihre Sammelzone, endet die Partie remis. Hier ist Weiß am Zug, und beide Erben können fliehen (Pfeile).', 'es': 'DOBLE HUIDA (0 puntos). Cuando las Blancas huyen, las Negras tienen una ÚLTIMA jugada para igualar. Si ambos Herederos alcanzan su zona de reunión, la partida es tablas. Aquí juegan las Blancas, y ambos Herederos pueden huir (flechas).', 'it': "DOPPIA FUGA (0 punti). Quando il Bianco fugge, il Nero ha un'ULTIMA mossa per pareggiare. Se entrambi gli Eredi raggiungono la loro zona di raduno, la partita è patta. Qui muove il Bianco, ed entrambi gli Eredi possono fuggire (frecce).", 'zh': '双出逃（0 分）。当白方出逃时，黑方有最后一手机会追平。若两位继承人都抵达各自的集结区，则和棋。此处轮到白方走子，且两位继承人都能出逃（箭头）。', 'ja': 'ダブルフーグ（0点）。白がフーグすると、黒には同点にするための最後の一手が与えられます。両方の後継者が集結ゾーンに達すると引き分けです。ここは白の手番で、両方の後継者がフーグできます（矢印）。', 'ko': '이중 탈출(0점). 백이 탈출하면 흑에게 동점을 위한 마지막 한 수가 주어집니다. 두 후계자가 모두 집결 구역에 도달하면 무승부입니다. 여기서는 백이 둘 차례이며, 두 후계자 모두 탈출할 수 있습니다(화살표).', 'ru': 'ДВОЙНОЙ ПОБЕГ (0 очков). Когда белые сбегают, у чёрных есть ПОСЛЕДНИЙ ход, чтобы сравнять. Если оба Наследника достигнут своей зоны сбора, партия ничья. Здесь ход белых, и оба Наследника могут сбежать (стрелки).', 'pt': 'DUPLA FUGA (0 pontos). Quando as Brancas fogem, as Pretas têm uma ÚLTIMA jogada para empatar. Se ambos os Herdeiros chegarem à sua zona de reunião, a partida é empate. Aqui é a vez das Brancas, e ambos os Herdeiros podem fugir (setas).'},
    'Fin : le mat': {'en': 'Ending: the mate', 'de': 'Ende: das Matt', 'es': 'Final: el mate', 'it': 'Finale: il matto', 'zh': '结束：将杀', 'ja': '終局：詰み', 'ko': '엔딩: 메이트', 'ru': 'Финал: мат', 'pt': 'Fim: o mate'},
    "MAT (+1 point). Le Garde (si6) se déplace en la7, puis pousse l'Héritier adverse (la8) hors du plateau : il est éjecté, tu gagnes.": {'en': 'MATE (+1 point). The Guard (si6) moves to la7, then pushes the enemy Heir (la8) off the board: it is ejected, you win.', 'de': 'MATT (+1 Punkt). Der Wächter (si6) zieht nach la7 und schiebt dann den gegnerischen Erben (la8) vom Brett: Er wird hinausgeworfen, du gewinnst.', 'es': 'MATE (+1 punto). El Guardia (si6) se mueve a la7 y luego empuja al Heredero rival (la8) fuera del tablero: es expulsado, ganas.', 'it': "MATTO (+1 punto). La Guardia (si6) si sposta in la7, poi spinge l'Erede avversario (la8) fuori dalla scacchiera: viene espulso, vinci.", 'zh': '将杀（+1 分）。卫兵（si6）移动到 la7，然后把对方继承人（la8）推出棋盘：它被逐出，你获胜。', 'ja': '詰み（+1点）。衛兵（si6）が la7 へ動き、相手の後継者（la8）を盤外へ押し出します：弾き出され、あなたの勝ちです。', 'ko': '메이트(+1점). 근위병(si6)이 la7로 이동한 뒤, 상대 후계자(la8)를 판 밖으로 밉니다: 밀려나고, 당신이 이깁니다.', 'ru': 'МАТ (+1 очко). Страж (si6) идёт на la7, затем выталкивает Наследника соперника (la8) с доски: он выброшен, вы побеждаете.', 'pt': 'MATE (+1 ponto). O Guarda (si6) move-se para la7, depois empurra o Herdeiro adversário (la8) para fora do tabuleiro: ele é expulso, você vence.'},
    'Fin : la guillotine': {'en': 'Ending: the guillotine', 'de': 'Ende: die Guillotine', 'es': 'Final: la guillotina', 'it': 'Finale: la ghigliottina', 'zh': '结束：断头台', 'ja': '終局：ギロチン', 'ko': '엔딩: 단두대', 'ru': 'Финал: гильотина', 'pt': 'Fim: a guilhotina'},
    "GUILLOTINE. L'adversaire va fuguer (son Héritier fa1, mobile grâce à sa Nurse, atteint son ralliement en bas : +2 pour lui). Pour limiter la casse, ton Garde (si6 vers la7) pousse TON PROPRE Héritier (la8) hors du plateau : c'est un mat sur toi-même, l'adversaire ne prend que +1 au lieu de +2.": {'en': "GUILLOTINE. The opponent is about to escape (their Heir fa1, mobile thanks to its Nurse, reaches its rally zone at the bottom: +2 for them). To limit the damage, your Guard (si6 to la7) pushes YOUR OWN Heir (la8) off the board: it's a self-mate, the opponent gets only +1 instead of +2.", 'de': 'GUILLOTINE. Der Gegner wird gleich fliehen (sein Erbe fa1, dank seiner Amme beweglich, erreicht unten seine Sammelzone: +2 für ihn). Um den Schaden zu begrenzen, schiebt dein Wächter (si6 nach la7) DEINEN EIGENEN Erben (la8) vom Brett: ein Selbstmatt, der Gegner erhält nur +1 statt +2.', 'es': 'GUILLOTINA. El rival está a punto de huir (su Heredero fa1, móvil gracias a su Nodriza, alcanza su zona de reunión abajo: +2 para él). Para limitar el daño, tu Guardia (si6 a la7) empuja a TU PROPIO Heredero (la8) fuera del tablero: es un automate, el rival solo obtiene +1 en vez de +2.', 'it': "GHIGLIOTTINA. L'avversario sta per fuggire (il suo Erede fa1, mobile grazie alla Balia, raggiunge la sua zona di raduno in basso: +2 per lui). Per limitare i danni, la tua Guardia (si6 in la7) spinge il TUO Erede (la8) fuori dalla scacchiera: è un automatto, l'avversario ottiene solo +1 invece di +2.", 'zh': '断头台。对手即将出逃（其继承人 fa1 借助乳母可移动，抵达下方的集结区：他得 +2）。为减少损失，你的卫兵（si6 到 la7）把你自己的继承人（la8）推出棋盘：这是自将，对手只得 +1 而非 +2。', 'ja': 'ギロチン。相手はまさにフーグ寸前です（乳母のおかげで動ける後継者 fa1 が下の集結ゾーンに到達：相手に +2）。損害を抑えるため、あなたの衛兵（si6 から la7）が自分の後継者（la8）を盤外へ押し出します：自詰みで、相手は +2 ではなく +1 だけになります。', 'ko': '단두대. 상대가 곧 탈출하려 합니다(유모 덕분에 움직일 수 있는 후계자 fa1이 아래쪽 집결 구역에 도달: 상대에게 +2). 피해를 줄이기 위해, 당신의 근위병(si6→la7)이 자기 후계자(la8)를 판 밖으로 밉니다: 자기 메이트로, 상대는 +2 대신 +1만 얻습니다.', 'ru': 'ГИЛЬОТИНА. Соперник вот-вот сбежит (его Наследник fa1, подвижный благодаря Няньке, достигает своей зоны сбора внизу: +2 ему). Чтобы уменьшить урон, ваш Страж (si6 на la7) выталкивает ВАШЕГО СОБСТВЕННОГО Наследника (la8) с доски: это самомат, соперник получает лишь +1 вместо +2.', 'pt': 'GUILHOTINA. O adversário está prestes a fugir (o Herdeiro dele fa1, móvel graças à Ama, chega à zona de reunião embaixo: +2 para ele). Para limitar o dano, seu Guarda (si6 para la7) empurra o SEU PRÓPRIO Herdeiro (la8) para fora do tabuleiro: é um automate, o adversário ganha só +1 em vez de +2.'},
    'Fin : la papatte': {'en': 'Ending: the papatte', 'de': 'Ende: die Papatte', 'es': 'Final: la papatte', 'it': 'Finale: la papatte', 'zh': '结束：papatte', 'ja': '終局：papatte', 'ko': '엔딩: papatte', 'ru': 'Финал: papatte', 'pt': 'Fim: a papatte'},
    "PAPATTE (+1 point). C'est à l'adversaire de jouer, mais il n'a AUCUN coup légal : son Chevalier (do8) est coincé, et son Héritier (si8) est isolé (aucune ronde à côté). Il perd. Très rare !": {'en': "PAPATTE (+1 point). It's the opponent's turn, but they have NO legal move: their Knight (do8) is stuck, and their Heir (si8) is isolated (no round piece beside it). They lose. Very rare!", 'de': 'PAPATTE (+1 Punkt). Der Gegner ist am Zug, hat aber KEINEN legalen Zug: Sein Ritter (do8) sitzt fest, und sein Erbe (si8) ist isoliert (keine runde Figur daneben). Er verliert. Sehr selten!', 'es': 'PAPATTE (+1 punto). Es el turno del rival, pero no tiene NINGUNA jugada legal: su Caballero (do8) está atascado y su Heredero (si8) está aislado (ninguna redonda al lado). Pierde. ¡Muy raro!', 'it': "PAPATTE (+1 punto). Tocca all'avversario, ma non ha ALCUNA mossa legale: il suo Cavaliere (do8) è bloccato e il suo Erede (si8) è isolato (nessun pezzo rotondo accanto). Perde. Molto raro!", 'zh': 'papatte（+1 分）。轮到对手走子，但他没有任何合法着法：他的骑士（do8）被卡住，继承人（si8）被孤立（旁边没有圆形棋子）。他告负。非常罕见！', 'ja': 'papatte（+1点）。相手の手番ですが、合法手が一つもありません：騎士（do8）は動けず、後継者（si8）は孤立（隣に丸い駒がない）。相手の負けです。非常に稀！', 'ko': 'papatte(+1점). 상대 차례이지만 합법적인 수가 전혀 없습니다: 기사(do8)가 막혀 있고, 후계자(si8)가 고립되어 있습니다(옆에 둥근 말이 없음). 상대가 집니다. 매우 드뭅니다!', 'ru': 'PAPATTE (+1 очко). Ход соперника, но у него НЕТ ни одного законного хода: его Рыцарь (do8) застрял, а Наследник (si8) изолирован (рядом нет круглой фигуры). Он проигрывает. Очень редко!', 'pt': 'PAPATTE (+1 ponto). É a vez do adversário, mas ele não tem NENHUMA jogada legal: seu Cavaleiro (do8) está preso e seu Herdeiro (si8) está isolado (nenhuma redonda ao lado). Ele perde. Muito raro!'},
    'Fin : la trêve': {'en': 'Ending: the truce', 'de': 'Ende: der Waffenstillstand', 'es': 'Final: la tregua', 'it': 'Finale: la tregua', 'zh': '结束：停战', 'ja': '終局：休戦', 'ko': '엔딩: 휴전', 'ru': 'Финал: перемирие', 'pt': 'Fim: a trégua'},
    "TRÊVE (0 point). Quand plus AUCUN joueur n'a de carrée qui peut bouger (peu importe à qui c'est de jouer), la partie est nulle : sans carrée mobile, plus aucune poussée n'est possible. Ici, les deux carrées (encadrées) sont isolées.": {'en': 'TRUCE (0 points). When NEITHER player has a square piece that can move (no matter whose turn it is), the game is drawn: with no mobile square piece, no push is possible. Here, both square pieces (framed) are isolated.', 'de': 'WAFFENSTILLSTAND (0 Punkte). Wenn KEIN Spieler eine bewegliche eckige Figur hat (egal, wer am Zug ist), endet die Partie remis: ohne bewegliche eckige Figur ist kein Schub möglich. Hier sind beide eckigen Figuren (umrahmt) isoliert.', 'es': 'TREGUA (0 puntos). Cuando NINGÚN jugador tiene una cuadrada que pueda moverse (sin importar de quién sea el turno), la partida es tablas: sin cuadrada móvil, ningún empuje es posible. Aquí, ambas cuadradas (enmarcadas) están aisladas.', 'it': 'TREGUA (0 punti). Quando NESSUN giocatore ha un quadrato che possa muoversi (non importa di chi sia il turno), la partita è patta: senza un quadrato mobile, nessuna spinta è possibile. Qui, entrambi i quadrati (incorniciati) sono isolati.', 'zh': '停战（0 分）。当双方都没有可移动的方形棋子时（无论轮到谁走子），和棋：没有可动的方形棋子，就无法推动。此处两枚方形棋子（带框）都被孤立。', 'ja': '休戦（0点）。どちらの手番であっても、両者とも動かせる四角い駒が一つもないとき、引き分けです：動ける四角い駒がなければ押しは不可能です。ここでは両方の四角い駒（枠付き）が孤立しています。', 'ko': '휴전(0점). 누구 차례든 상관없이, 양쪽 모두 움직일 수 있는 사각 말이 없으면 무승부입니다: 움직일 사각 말이 없으면 밀기가 불가능합니다. 여기서는 두 사각 말(테두리) 모두 고립되어 있습니다.', 'ru': 'ПЕРЕМИРИЕ (0 очков). Когда НИ У ОДНОГО игрока нет квадратной фигуры, способной ходить (независимо от того, чей ход), партия ничья: без подвижной квадратной фигуры толчок невозможен. Здесь обе квадратные фигуры (в рамке) изолированы.', 'pt': 'TRÉGUA (0 pontos). Quando NENHUM jogador tem uma quadrada que possa mover-se (não importa de quem é a vez), a partida é empate: sem quadrada móvel, nenhum empurrão é possível. Aqui, ambas as quadradas (emolduradas) estão isoladas.'},
    'Fin : nulle par accord': {'en': 'Ending: draw by agreement', 'de': 'Ende: Remis durch Einigung', 'es': 'Final: tablas por acuerdo', 'it': 'Finale: patta per accordo', 'zh': '结束：协议和棋', 'ja': '終局：合意による引き分け', 'ko': '엔딩: 합의 무승부', 'ru': 'Финал: ничья по соглашению', 'pt': 'Fim: empate por acordo'},
    "NULLE PAR ACCORD (0 point). Pendant une partie, tu peux proposer la nulle avec le bouton « ½ » (entouré) ; si l'adversaire accepte, la partie est nulle. RÉPÉTITION : si la même position revient 4 fois, la nulle est automatique.": {'en': 'DRAW BY AGREEMENT (0 points). During a game, you can offer a draw with the “½” button (circled); if the opponent accepts, the game is drawn. REPETITION: if the same position occurs 4 times, the draw is automatic.', 'de': 'REMIS DURCH EINIGUNG (0 Punkte). Während einer Partie kannst du mit der „½“-Schaltfläche (eingekreist) Remis anbieten; nimmt der Gegner an, endet die Partie remis. WIEDERHOLUNG: Tritt dieselbe Stellung 4-mal auf, ist das Remis automatisch.', 'es': 'TABLAS POR ACUERDO (0 puntos). Durante una partida, puedes ofrecer tablas con el botón «½» (rodeado); si el rival acepta, la partida es tablas. REPETICIÓN: si la misma posición se repite 4 veces, las tablas son automáticas.', 'it': "PATTA PER ACCORDO (0 punti). Durante una partita puoi proporre la patta con il pulsante «½» (cerchiato); se l'avversario accetta, la partita è patta. RIPETIZIONE: se la stessa posizione si ripete 4 volte, la patta è automatica.", 'zh': '协议和棋（0 分）。对局中，你可以用“½”按钮（圈出）提议和棋；若对手接受，则和棋。重复：若同一局面出现 4 次，则自动和棋。', 'ja': '合意による引き分け（0点）。対局中、「½」ボタン（丸で囲み）で引き分けを提案できます。相手が承諾すれば引き分けです。反復：同じ局面が4回現れると自動的に引き分けになります。', 'ko': '합의 무승부(0점). 대국 중 “½” 버튼(원으로 표시)으로 무승부를 제안할 수 있습니다. 상대가 수락하면 무승부입니다. 반복: 같은 위치가 4번 나오면 자동으로 무승부가 됩니다.', 'ru': 'НИЧЬЯ ПО СОГЛАШЕНИЮ (0 очков). Во время партии вы можете предложить ничью кнопкой «½» (обведена); если соперник согласится, партия ничья. ПОВТОРЕНИЕ: если одна и та же позиция возникает 4 раза, ничья засчитывается автоматически.', 'pt': 'EMPATE POR ACORDO (0 pontos). Durante uma partida, você pode oferecer empate com o botão «½» (circulado); se o adversário aceitar, a partida é empate. REPETIÇÃO: se a mesma posição ocorrer 4 vezes, o empate é automático.'},
    'Fin : abandon, temps, déco': {'en': 'Ending: resign, time, disconnect', 'de': 'Ende: Aufgabe, Zeit, Trennung', 'es': 'Final: abandono, tiempo, desconexión', 'it': 'Finale: abbandono, tempo, disconnessione', 'zh': '结束：认输、超时、断线', 'ja': '終局：投了・時間切れ・切断', 'ko': '엔딩: 기권·시간·연결 끊김', 'ru': 'Финал: сдача, время, отключение', 'pt': 'Fim: desistência, tempo, desconexão'},
    "ABANDON / TEMPS / DÉCONNEXION (+2 points chacun). Trois façons de gagner sans jouer : si l'adversaire ABANDONNE (le bouton « X »), si son TEMPS tombe à 0:00 (la pendule), ou s'il se DÉCONNECTE. Dans les trois cas, tu gagnes +2 points.": {'en': 'RESIGN / TIME / DISCONNECT (+2 points each). Three ways to win without playing: if the opponent RESIGNS (the “X” button), if their TIME reaches 0:00 (the clock), or if they DISCONNECT. In all three cases, you win +2 points.', 'de': 'AUFGABE / ZEIT / TRENNUNG (je +2 Punkte). Drei Arten, ohne zu spielen zu gewinnen: wenn der Gegner AUFGIBT (die „X“-Schaltfläche), wenn seine ZEIT auf 0:00 fällt (die Uhr) oder wenn er die VERBINDUNG verliert. In allen drei Fällen gewinnst du +2 Punkte.', 'es': 'ABANDONO / TIEMPO / DESCONEXIÓN (+2 puntos cada uno). Tres formas de ganar sin jugar: si el rival ABANDONA (el botón «X»), si su TIEMPO llega a 0:00 (el reloj), o si se DESCONECTA. En los tres casos, ganas +2 puntos.', 'it': "ABBANDONO / TEMPO / DISCONNESSIONE (+2 punti ciascuno). Tre modi di vincere senza giocare: se l'avversario ABBANDONA (il pulsante «X»), se il suo TEMPO arriva a 0:00 (l'orologio), o se si DISCONNETTE. In tutti e tre i casi vinci +2 punti.", 'zh': '认输 / 超时 / 断线（各 +2 分）。三种无需走子即可获胜的方式：对手认输（“X”按钮）、其时间归零 0:00（时钟），或其断线。这三种情况下，你都赢得 +2 分。', 'ja': '投了 / 時間切れ / 切断（各 +2点）。指さずに勝つ三つの方法：相手が投了する（「X」ボタン）、相手の時間が 0:00 になる（時計）、または相手が切断する。いずれの場合も +2点を得ます。', 'ko': '기권 / 시간 / 연결 끊김(각 +2점). 두지 않고 이기는 세 가지 방법: 상대가 기권하거나(“X” 버튼), 상대의 시간이 0:00이 되거나(시계), 상대가 연결이 끊기는 경우입니다. 세 경우 모두 +2점을 얻습니다.', 'ru': 'СДАЧА / ВРЕМЯ / ОТКЛЮЧЕНИЕ (+2 очка за каждое). Три способа победить, не играя: если соперник СДАЁТСЯ (кнопка «X»), если его ВРЕМЯ доходит до 0:00 (часы) или если он ОТКЛЮЧАЕТСЯ. Во всех трёх случаях вы получаете +2 очка.', 'pt': 'DESISTÊNCIA / TEMPO / DESCONEXÃO (+2 pontos cada). Três formas de vencer sem jogar: se o adversário DESISTIR (o botão «X»), se o TEMPO dele chegar a 0:00 (o relógio), ou se ele se DESCONECTAR. Nos três casos, você ganha +2 pontos.'},
})


TRANSLATIONS.update({
    '< Précédent': {'en': '< Previous', 'de': '< Zurück', 'es': '< Anterior', 'it': '< Indietro', 'zh': '< 上一步', 'ja': '< 前へ', 'ko': '< 이전', 'ru': '< Назад', 'pt': '< Anterior'},
    "Impossible d'envoyer le défi.": {'en': 'Cannot send the challenge.', 'de': 'Herausforderung kann nicht gesendet werden.', 'es': 'No se puede enviar el desafío.', 'it': 'Impossibile inviare la sfida.', 'zh': '无法发送挑战。', 'ja': '挑戦を送信できません。', 'ko': '도전을 보낼 수 없습니다.', 'ru': 'Не удалось отправить вызов.', 'pt': 'Não foi possível enviar o desafio.'},
    "Le chrono du joueur au trait continue à s'écouler.": {'en': 'The clock of the player to move keeps running.', 'de': 'Die Uhr des Spielers am Zug läuft weiter.', 'es': 'El reloj del jugador en turno sigue corriendo.', 'it': "L'orologio del giocatore di turno continua a scorrere.", 'zh': '轮到走子的一方的计时仍在继续。', 'ja': '手番のプレイヤーの時計は動き続けます。', 'ko': '둘 차례인 사람의 시계는 계속 흘러갑니다.', 'ru': 'Часы игрока, чей ход, продолжают идти.', 'pt': 'O relógio do jogador da vez continua correndo.'},
    'vous défie !\nMélo %d%s': {'en': 'challenges you!\nMélo %d%s', 'de': 'fordert dich heraus!\nMélo %d%s', 'es': 'te desafía!\nMélo %d%s', 'it': 'ti sfida!\nMélo %d%s', 'zh': '向你发起挑战！\nMélo %d%s', 'ja': 'があなたに挑戦！\nMélo %d%s', 'ko': '님이 도전합니다!\nMélo %d%s', 'ru': 'бросает вам вызов!\nMélo %d%s', 'pt': 'desafia você!\nMélo %d%s'},
    'Défi envoyé à %s…\n\nObjectif : %s\nCadence : %s\n\n': {'en': 'Challenge sent to %s…\n\nObjective: %s\nTime: %s\n\n', 'de': 'Herausforderung an %s gesendet…\n\nZiel: %s\nZeit: %s\n\n', 'es': 'Desafío enviado a %s…\n\nObjetivo: %s\nTiempo: %s\n\n', 'it': 'Sfida inviata a %s…\n\nObiettivo: %s\nTempo: %s\n\n', 'zh': '已向 %s 发送挑战…\n\n目标：%s\n时间：%s\n\n', 'ja': '%s に挑戦を送信…\n\n目標：%s\n持ち時間：%s\n\n', 'ko': '%s 님에게 도전을 보냈습니다…\n\n목표: %s\n시간: %s\n\n', 'ru': 'Вызов отправлен %s…\n\nЦель: %s\nВремя: %s\n\n', 'pt': 'Desafio enviado a %s…\n\nObjetivo: %s\nTempo: %s\n\n'},
    '[b]%s[/b] (Mélo %d)\nvous défie !\n\nObjectif : %s\nCadence : %s%s': {'en': '[b]%s[/b] (Mélo %d)\nchallenges you!\n\nObjective: %s\nTime: %s%s', 'de': '[b]%s[/b] (Mélo %d)\nfordert dich heraus!\n\nZiel: %s\nZeit: %s%s', 'es': '[b]%s[/b] (Mélo %d)\nte desafía!\n\nObjetivo: %s\nTiempo: %s%s', 'it': '[b]%s[/b] (Mélo %d)\nti sfida!\n\nObiettivo: %s\nTempo: %s%s', 'zh': '[b]%s[/b]（Mélo %d）\n向你发起挑战！\n\n目标：%s\n时间：%s%s', 'ja': '[b]%s[/b]（Mélo %d）\nがあなたに挑戦！\n\n目標：%s\n持ち時間：%s%s', 'ko': '[b]%s[/b] (Mélo %d)\n님이 도전합니다!\n\n목표: %s\n시간: %s%s', 'ru': '[b]%s[/b] (Mélo %d)\nбросает вам вызов!\n\nЦель: %s\nВремя: %s%s', 'pt': '[b]%s[/b] (Mélo %d)\ndesafia você!\n\nObjetivo: %s\nTempo: %s%s'},
    'Connecté en tant que :\n[b]%s[/b]\n\nMélo : %d': {'en': 'Logged in as:\n[b]%s[/b]\n\nMélo: %d', 'de': 'Angemeldet als:\n[b]%s[/b]\n\nMélo: %d', 'es': 'Conectado como:\n[b]%s[/b]\n\nMélo: %d', 'it': 'Connesso come:\n[b]%s[/b]\n\nMélo: %d', 'zh': '已登录为：\n[b]%s[/b]\n\nMélo：%d', 'ja': 'ログイン中：\n[b]%s[/b]\n\nMélo：%d', 'ko': '로그인: \n[b]%s[/b]\n\nMélo: %d', 'ru': 'Вы вошли как:\n[b]%s[/b]\n\nMélo: %d', 'pt': 'Conectado como:\n[b]%s[/b]\n\nMélo: %d'},
})


TRANSLATIONS.update({
    'MOTIFS DE\nFIN DE PARTIE': {'en': 'HOW GAMES\nEND', 'de': 'SO ENDEN\nPARTIEN', 'es': 'FORMAS DE\nTERMINAR', 'it': 'MODI DI\nFINIRE', 'zh': '对局\n结束方式', 'ja': '対局の\n終わり方', 'ko': '대국\n종료 방식', 'ru': 'КАК\nЗАВЕРШАЕТСЯ', 'pt': 'FORMAS DE\nTERMINAR'},
    'Suivant >': {'en': 'Next >', 'de': 'Weiter >', 'es': 'Siguiente >', 'it': 'Avanti >', 'zh': '下一步 >', 'ja': '次へ >', 'ko': '다음 >', 'ru': 'Далее >', 'pt': 'Próximo >'},
    'Le menu >': {'en': 'The menu >', 'de': 'Das Menü >', 'es': 'El menú >', 'it': 'Il menu >', 'zh': '菜单 >', 'ja': 'メニュー >', 'ko': '메뉴 >', 'ru': 'Меню >', 'pt': 'O menu >'},
    'Continuer >': {'en': 'Continue >', 'de': 'Weiter >', 'es': 'Continuar >', 'it': 'Continua >', 'zh': '继续 >', 'ja': '続ける >', 'ko': '계속 >', 'ru': 'Продолжить >', 'pt': 'Continuar >'},
    'Fermer le tuto': {'en': 'Close tutorial', 'de': 'Tutorial schließen', 'es': 'Cerrar tutorial', 'it': 'Chiudi tutorial', 'zh': '关闭教程', 'ja': 'チュートリアルを閉じる', 'ko': '튜토리얼 닫기', 'ru': 'Закрыть обучение', 'pt': 'Fechar tutorial'},
    'Bonne fugue !': {'en': 'Happy escaping!', 'de': 'Gute Flucht!', 'es': '¡Buena huida!', 'it': 'Buona fuga!', 'zh': '祝出逃顺利！', 'ja': 'よい逃走を！', 'ko': '멋진 탈출을!', 'ru': 'Удачного побега!', 'pt': 'Boa fuga!'},
    'Jouer en local': {'en': 'Play locally', 'de': 'Lokal spielen', 'es': 'Jugar en local', 'it': 'Gioca in locale', 'zh': '本地对战', 'ja': 'ローカル対戦', 'ko': '로컬 대전', 'ru': 'Игра локально', 'pt': 'Jogar local'},
    'Jouer en ligne': {'en': 'Play online', 'de': 'Online spielen', 'es': 'Jugar en línea', 'it': 'Gioca online', 'zh': '在线对战', 'ja': 'オンライン対戦', 'ko': '온라인 대전', 'ru': 'Игра онлайн', 'pt': 'Jogar online'},
    'Jouer contre Deep Grey': {'en': 'Play against Deep Grey', 'de': 'Gegen Deep Grey spielen', 'es': 'Jugar contra Deep Grey', 'it': 'Gioca contro Deep Grey', 'zh': '对战 Deep Grey', 'ja': 'Deep Grey と対戦', 'ko': 'Deep Grey와 대전', 'ru': 'Играть против Deep Grey', 'pt': 'Jogar contra Deep Grey'},
    'Plus': {'en': 'More', 'de': 'Mehr', 'es': 'Más', 'it': 'Altro', 'zh': '更多', 'ja': 'その他', 'ko': '더보기', 'ru': 'Ещё', 'pt': 'Mais'},
    'Mon compte': {'en': 'My account', 'de': 'Mein Konto', 'es': 'Mi cuenta', 'it': 'Il mio account', 'zh': '我的账号', 'ja': 'アカウント', 'ko': '내 계정', 'ru': 'Мой аккаунт', 'pt': 'Minha conta'},
    'Soutenir les devs': {'en': 'Support the devs', 'de': 'Entwickler unterstützen', 'es': 'Apoyar a los devs', 'it': 'Sostieni gli sviluppatori', 'zh': '支持开发者', 'ja': '開発者を支援', 'ko': '개발자 후원', 'ru': 'Поддержать разработчиков', 'pt': 'Apoiar os devs'},
    'Tuto': {'en': 'Tutorial', 'de': 'Tutorial', 'es': 'Tutorial', 'it': 'Tutorial', 'zh': '教程', 'ja': 'チュートリアル', 'ko': '튜토리얼', 'ru': 'Обучение', 'pt': 'Tutorial'},
    'Analyse': {'en': 'Analysis', 'de': 'Analyse', 'es': 'Análisis', 'it': 'Analisi', 'zh': '分析', 'ja': '解析', 'ko': '분석', 'ru': 'Анализ', 'pt': 'Análise'},
    'Lien': {'en': 'Link', 'de': 'Link', 'es': 'Enlace', 'it': 'Link', 'zh': '链接', 'ja': 'リンク', 'ko': '링크', 'ru': 'Ссылка', 'pt': 'Link'},
    'Partie': {'en': 'Game', 'de': 'Partie', 'es': 'Partida', 'it': 'Partita', 'zh': '对局', 'ja': '対局', 'ko': '대국', 'ru': 'Партия', 'pt': 'Partida'},
    'Partie unique': {'en': 'Single game', 'de': 'Einzelpartie', 'es': 'Partida única', 'it': 'Partita singola', 'zh': '单局', 'ja': '1局', 'ko': '단판', 'ru': 'Одна партия', 'pt': 'Partida única'},
    '1 partie': {'en': '1 game', 'de': '1 Partie', 'es': '1 partida', 'it': '1 partita', 'zh': '1 局', 'ja': '1 局', 'ko': '1 판', 'ru': '1 партия', 'pt': '1 partida'},
    'Flash': {'en': 'Flash', 'de': 'Flash', 'es': 'Flash', 'it': 'Flash', 'zh': '闪电', 'ja': 'フラッシュ', 'ko': '플래시', 'ru': 'Флеш', 'pt': 'Flash'},
    'Zen': {'en': 'Zen', 'de': 'Zen', 'es': 'Zen', 'it': 'Zen', 'zh': '禅', 'ja': '禅', 'ko': '젠', 'ru': 'Дзен', 'pt': 'Zen'},
    'Zen (illimité)': {'en': 'Zen (unlimited)', 'de': 'Zen (unbegrenzt)', 'es': 'Zen (ilimitado)', 'it': 'Zen (illimitato)', 'zh': '禅（无限）', 'ja': '禅（無制限）', 'ko': '젠 (무제한)', 'ru': 'Дзен (без лимита)', 'pt': 'Zen (ilimitado)'},
    '%s min': {'en': '%s min', 'de': '%s Min', 'es': '%s min', 'it': '%s min', 'zh': '%s 分钟', 'ja': '%s 分', 'ko': '%s 분', 'ru': '%s мин', 'pt': '%s min'},
    '2 points': {'en': '2 points', 'de': '2 Punkte', 'es': '2 puntos', 'it': '2 punti', 'zh': '2 分', 'ja': '2 点', 'ko': '2점', 'ru': '2 очка', 'pt': '2 pontos'},
    '3 points': {'en': '3 points', 'de': '3 Punkte', 'es': '3 puntos', 'it': '3 punti', 'zh': '3 分', 'ja': '3 点', 'ko': '3점', 'ru': '3 очка', 'pt': '3 pontos'},
    '5 points': {'en': '5 points', 'de': '5 Punkte', 'es': '5 puntos', 'it': '5 punti', 'zh': '5 分', 'ja': '5 点', 'ko': '5점', 'ru': '5 очков', 'pt': '5 pontos'},
    'Standard': {'en': 'Standard', 'de': 'Standard', 'es': 'Estándar', 'it': 'Standard', 'zh': '标准', 'ja': '標準', 'ko': '표준', 'ru': 'Стандарт', 'pt': 'Padrão'},
    'Profond': {'en': 'Deep', 'de': 'Tief', 'es': 'Profundo', 'it': 'Profondo', 'zh': '深度', 'ja': '深い', 'ko': '깊이', 'ru': 'Глубокий', 'pt': 'Profundo'},
    'Rapide': {'en': 'Fast', 'de': 'Schnell', 'es': 'Rápido', 'it': 'Veloce', 'zh': '快速', 'ja': '高速', 'ko': '빠름', 'ru': 'Быстрый', 'pt': 'Rápido'},
    'Instantané': {'en': 'Instant', 'de': 'Sofort', 'es': 'Instantáneo', 'it': 'Istantaneo', 'zh': '瞬间', 'ja': '即時', 'ko': '즉시', 'ru': 'Мгновенно', 'pt': 'Instantâneo'},
    'Moyen': {'en': 'Medium', 'de': 'Mittel', 'es': 'Medio', 'it': 'Medio', 'zh': '中等', 'ja': '中', 'ko': '보통', 'ru': 'Средне', 'pt': 'Médio'},
    'Lent': {'en': 'Slow', 'de': 'Langsam', 'es': 'Lento', 'it': 'Lento', 'zh': '慢速', 'ja': '遅い', 'ko': '느림', 'ru': 'Медленно', 'pt': 'Lento'},
    'Pause': {'en': 'Pause', 'de': 'Pause', 'es': 'Pausa', 'it': 'Pausa', 'zh': '暂停', 'ja': '一時停止', 'ko': '일시정지', 'ru': 'Пауза', 'pt': 'Pausa'},
    'Reprendre': {'en': 'Resume', 'de': 'Fortsetzen', 'es': 'Reanudar', 'it': 'Riprendi', 'zh': '继续', 'ja': '再開', 'ko': '계속', 'ru': 'Продолжить', 'pt': 'Retomar'},
    'Revenir au menu': {'en': 'Back to menu', 'de': 'Zurück zum Menü', 'es': 'Volver al menú', 'it': 'Torna al menu', 'zh': '返回菜单', 'ja': 'メニューに戻る', 'ko': '메뉴로', 'ru': 'В меню', 'pt': 'Voltar ao menu'},
    'Continuer': {'en': 'Continue', 'de': 'Fortsetzen', 'es': 'Continuar', 'it': 'Continua', 'zh': '继续', 'ja': '続ける', 'ko': '계속', 'ru': 'Продолжить', 'pt': 'Continuar'},
    'Abandonner': {'en': 'Resign', 'de': 'Aufgeben', 'es': 'Abandonar', 'it': 'Abbandona', 'zh': '认输', 'ja': '投了', 'ko': '기권', 'ru': 'Сдаться', 'pt': 'Desistir'},
    'Abandonner ?': {'en': 'Resign?', 'de': 'Aufgeben?', 'es': '¿Abandonar?', 'it': 'Abbandonare?', 'zh': '认输？', 'ja': '投了しますか？', 'ko': '기권할까요?', 'ru': 'Сдаться?', 'pt': 'Desistir?'},
    'Oui, abandonner': {'en': 'Yes, resign', 'de': 'Ja, aufgeben', 'es': 'Sí, abandonar', 'it': 'Sì, abbandona', 'zh': '是的，认输', 'ja': 'はい、投了', 'ko': '네, 기권', 'ru': 'Да, сдаться', 'pt': 'Sim, desistir'},
    'Annuler le match ?': {'en': 'Cancel the match?', 'de': 'Match abbrechen?', 'es': '¿Cancelar el match?', 'it': 'Annullare il match?', 'zh': '取消比赛？', 'ja': 'マッチを中止しますか？', 'ko': '매치를 취소할까요?', 'ru': 'Отменить матч?', 'pt': 'Cancelar a partida?'},
    'Annuler le match': {'en': 'Cancel the match', 'de': 'Match abbrechen', 'es': 'Cancelar el match', 'it': 'Annulla il match', 'zh': '取消比赛', 'ja': 'マッチを中止', 'ko': '매치 취소', 'ru': 'Отменить матч', 'pt': 'Cancelar a partida'},
    'Proposition de nulle': {'en': 'Draw offer', 'de': 'Remisangebot', 'es': 'Oferta de tablas', 'it': 'Offerta di patta', 'zh': '和棋提议', 'ja': '引き分けの申し出', 'ko': '무승부 제안', 'ru': 'Предложение ничьей', 'pt': 'Oferta de empate'},
    'Gagné !': {'en': 'Won!', 'de': 'Gewonnen!', 'es': '¡Ganado!', 'it': 'Vinto!', 'zh': '胜利！', 'ja': '勝ち！', 'ko': '승리!', 'ru': 'Победа!', 'pt': 'Venceu!'},
    'Perdu': {'en': 'Lost', 'de': 'Verloren', 'es': 'Perdido', 'it': 'Perso', 'zh': '失败', 'ja': '負け', 'ko': '패배', 'ru': 'Поражение', 'pt': 'Perdeu'},
    'Moi': {'en': 'Me', 'de': 'Ich', 'es': 'Yo', 'it': 'Io', 'zh': '我', 'ja': '自分', 'ko': '나', 'ru': 'Я', 'pt': 'Eu'},
    'À vous de jouer': {'en': 'Your turn', 'de': 'Du bist am Zug', 'es': 'Tu turno', 'it': 'Tocca a te', 'zh': '轮到你', 'ja': 'あなたの手番', 'ko': '당신 차례', 'ru': 'Ваш ход', 'pt': 'Sua vez'},
    'À votre adversaire\nde jouer': {'en': "Opponent's\nturn", 'de': 'Gegner\nam Zug', 'es': 'Turno del\nrival', 'it': "Turno\ndell'avversario", 'zh': '对手\n的回合', 'ja': '相手の\n手番', 'ko': '상대\n차례', 'ru': 'Ход\nсоперника', 'pt': 'Vez do\nadversário'},
})


TRANSLATIONS.update({
    "Avant une partie, choisis un OBJECTIF (Partie = une seule ; 3/5/7 = premier à ce nombre de points) et une CADENCE (minutes par joueur). En 3/5/7, si l'adversaire atteint le score alors que tu as joué une partie de MOINS que lui en Blanc, tu joues une ULTIME partie en Blanc pour égaliser les couleurs.": {'en': "Before a game, choose an OBJECTIVE (Game = a single one; 3/5/7 = first to that many points) and a TIME control (minutes per player). In 3/5/7, if the opponent reaches the score while you've played one fewer game as White, you play a FINAL game as White to even out the colors.", 'de': 'Wähle vor einer Partie ein ZIEL (Partie = eine einzige; 3/5/7 = zuerst zu dieser Punktzahl) und eine BEDENKZEIT (Minuten pro Spieler). Bei 3/5/7: Erreicht der Gegner den Punktstand, während du eine Partie WENIGER mit Weiß gespielt hast, spielst du eine LETZTE Partie mit Weiß, um die Farben auszugleichen.', 'es': 'Antes de una partida, elige un OBJETIVO (Partida = una sola; 3/5/7 = primero en llegar a esos puntos) y un TIEMPO (minutos por jugador). En 3/5/7, si el rival alcanza el marcador mientras jugaste una partida MENOS con Blancas, juegas una ÚLTIMA partida con Blancas para igualar los colores.', 'it': "Prima di una partita, scegli un OBIETTIVO (Partita = una sola; 3/5/7 = primo a quel punteggio) e un TEMPO (minuti per giocatore). In 3/5/7, se l'avversario raggiunge il punteggio mentre hai giocato una partita in MENO col Bianco, giochi un'ULTIMA partita col Bianco per pareggiare i colori.", 'zh': '对局前，选择一个目标（对局 = 仅一局；3/5/7 = 先达到该分数者胜）和一个时间（每位玩家的分钟数）。在 3/5/7 中，若对手达到分数时你执白比他少下一局，你将执白再下最后一局以平衡先后手。', 'ja': '対局前に、目標（対局＝1局のみ；3/5/7＝先取した方が勝ち）と持ち時間（1人あたりの分）を選びます。3/5/7では、あなたが相手より白番を1局少なく指している間に相手が点数に達した場合、色を均等にするため白番で最終局を指します。', 'ko': '대국 전에 목표(대국 = 단 한 판; 3/5/7 = 해당 점수 선취)와 시간(플레이어당 분)을 고르세요. 3/5/7에서 상대가 점수에 도달했는데 당신이 백으로 한 판 적게 두었다면, 색을 맞추기 위해 백으로 마지막 한 판을 둡니다.', 'ru': 'Перед партией выберите ЦЕЛЬ (Партия = одна; 3/5/7 = первым до этого числа очков) и КОНТРОЛЬ ВРЕМЕНИ (минуты на игрока). В 3/5/7, если соперник набирает счёт, а вы сыграли на одну партию МЕНЬШЕ белыми, вы играете ПОСЛЕДНЮЮ партию белыми, чтобы уравнять цвета.', 'pt': 'Antes de uma partida, escolha um OBJETIVO (Partida = uma só; 3/5/7 = primeiro a atingir esses pontos) e um TEMPO (minutos por jogador). Em 3/5/7, se o adversário atingir a pontuação enquanto você jogou uma partida a MENOS de Brancas, você joga uma ÚLTIMA partida de Brancas para igualar as cores.'},
    "Puis lance : « Jouer en local » (à deux sur le même appareil) ou « Jouer en ligne ». En ligne, le matchmaking te trouve un adversaire de ton niveau ; c'est le SEUL mode qui fait bouger ton MÉLO, ton classement (~1500 au départ), qui monte quand tu gagnes et baisse quand tu perds.": {'en': "Then start: “Play locally” (two players on the same device) or “Play online”. Online, matchmaking finds you an opponent of your level; it's the ONLY mode that changes your MÉLO, your rating (~1500 at the start), which goes up when you win and down when you lose.", 'de': 'Starte dann: „Lokal spielen“ (zwei Spieler am selben Gerät) oder „Online spielen“. Online sucht dir das Matchmaking einen Gegner deines Niveaus; es ist der EINZIGE Modus, der dein MÉLO ändert, deine Wertung (~1500 zu Beginn), die steigt, wenn du gewinnst, und sinkt, wenn du verlierst.', 'es': 'Luego empieza: «Jugar en local» (dos jugadores en el mismo dispositivo) o «Jugar en línea». En línea, el emparejamiento te busca un rival de tu nivel; es el ÚNICO modo que cambia tu MÉLO, tu clasificación (~1500 al inicio), que sube cuando ganas y baja cuando pierdes.', 'it': "Poi avvia: «Gioca in locale» (due giocatori sullo stesso dispositivo) o «Gioca online». Online, il matchmaking ti trova un avversario del tuo livello; è l'UNICA modalità che cambia il tuo MÉLO, il tuo punteggio (~1500 all'inizio), che sale quando vinci e scende quando perdi.", 'zh': '然后开始：“本地对战”（同一设备上两名玩家）或“在线对战”。在线时，匹配系统为你找到同水平的对手；这是唯一会改变你 MÉLO（你的等级分，起始约 1500，胜则升、负则降）的模式。', 'ja': 'それから開始します：「ローカル対戦」（同じ端末で2人）または「オンライン対戦」。オンラインではマッチングが同じ実力の相手を見つけます。あなたの MÉLO（レーティング、開始時約1500、勝てば上がり負ければ下がる）が変わる唯一のモードです。', 'ko': '그런 다음 시작하세요: “로컬 대전”(같은 기기에서 두 명) 또는 “온라인 대전”. 온라인에서는 매칭이 같은 수준의 상대를 찾아줍니다. MÉLO(레이팅, 시작 약 1500, 이기면 오르고 지면 내려감)가 바뀌는 유일한 모드입니다.', 'ru': 'Затем начните: «Игра локально» (два игрока на одном устройстве) или «Игра онлайн». Онлайн подбор находит соперника вашего уровня; это ЕДИНСТВЕННЫЙ режим, меняющий ваш MÉLO — рейтинг (~1500 в начале), который растёт при победах и падает при поражениях.', 'pt': 'Depois comece: «Jogar local» (dois jogadores no mesmo aparelho) ou «Jogar online». Online, o emparelhamento encontra um adversário do seu nível; é o ÚNICO modo que altera seu MÉLO, sua classificação (~1500 no início), que sobe quando você ganha e desce quando perde.'},
    "« deep grey » est l'intelligence artificielle du jeu : affronte-la pour t'entraîner quand tu veux.": {'en': "“Deep Grey” is the game's artificial intelligence: play against it to train whenever you like.", 'de': '„Deep Grey“ ist die künstliche Intelligenz des Spiels: Spiele gegen sie, um zu üben, wann immer du willst.', 'es': '«Deep Grey» es la inteligencia artificial del juego: juega contra ella para entrenar cuando quieras.', 'it': "«Deep Grey» è l'intelligenza artificiale del gioco: gioca contro di essa per allenarti quando vuoi.", 'zh': '“Deep Grey”是游戏的人工智能：随时可以与它对战来训练。', 'ja': '「Deep Grey」はゲームの人工知能です。好きなときに対戦して練習できます。', 'ko': '“Deep Grey”는 게임의 인공지능입니다. 언제든지 대결하며 연습하세요.', 'ru': '«Deep Grey» — это искусственный интеллект игры: играйте против него, чтобы тренироваться, когда захотите.', 'pt': '«Deep Grey» é a inteligência artificial do jogo: jogue contra ela para treinar quando quiser.'},
    "Cherche un joueur par son nom pour le défier directement ; l'étoile gère tes favoris.": {'en': 'Search for a player by name to challenge them directly; the star manages your favorites.', 'de': 'Suche einen Spieler mit Namen, um ihn direkt herauszufordern; der Stern verwaltet deine Favoriten.', 'es': 'Busca a un jugador por su nombre para desafiarlo directamente; la estrella gestiona tus favoritos.', 'it': 'Cerca un giocatore per nome per sfidarlo direttamente; la stella gestisce i tuoi preferiti.', 'zh': '按名字搜索玩家以直接向其发起挑战；星标用于管理你的收藏。', 'ja': '名前でプレイヤーを検索して直接挑戦できます。星印でお気に入りを管理します。', 'ko': '이름으로 플레이어를 검색해 바로 도전하세요. 별표로 즐겨찾기를 관리합니다.', 'ru': 'Найдите игрока по имени, чтобы бросить ему вызов напрямую; звёздочка управляет избранным.', 'pt': 'Procure um jogador pelo nome para desafiá-lo diretamente; a estrela gerencia seus favoritos.'},
    "Fais glisser l'écran vers le BAS pour la CORRESPONDANCE : des parties sans limite de temps, contre des joueurs enregistrés. Pour en lancer une, clique sur un plateau vide, puis choisis ton adversaire parmi tes favoris.": {'en': 'Swipe the screen DOWN for CORRESPONDENCE: games with no time limit, against registered players. To start one, tap an empty board, then choose your opponent from your favorites.', 'de': 'Wische den Bildschirm nach UNTEN für FERNPARTIEN: Partien ohne Zeitlimit gegen registrierte Spieler. Um eine zu starten, tippe auf ein leeres Brett und wähle dann deinen Gegner aus deinen Favoriten.', 'es': 'Desliza la pantalla hacia ABAJO para la CORRESPONDENCIA: partidas sin límite de tiempo, contra jugadores registrados. Para iniciar una, toca un tablero vacío y elige a tu rival entre tus favoritos.', 'it': 'Scorri lo schermo verso il BASSO per la CORRISPONDENZA: partite senza limite di tempo, contro giocatori registrati. Per iniziarne una, tocca una scacchiera vuota, poi scegli il tuo avversario tra i preferiti.', 'zh': '向下滑动屏幕进入通信对局：不限时的对局，对手为注册玩家。要开始一局，点击空棋盘，然后从收藏中选择对手。', 'ja': '画面を下にスワイプすると通信対局になります：時間無制限で、登録済みのプレイヤーと対戦します。始めるには空の盤をタップし、お気に入りから相手を選びます。', 'ko': '화면을 아래로 밀면 통신 대국입니다: 시간 제한 없이 등록된 플레이어와 둡니다. 시작하려면 빈 판을 누른 뒤 즐겨찾기에서 상대를 고르세요.', 'ru': 'Проведите по экрану ВНИЗ для ИГР ПО ПЕРЕПИСКЕ: партии без ограничения времени против зарегистрированных игроков. Чтобы начать, нажмите на пустую доску и выберите соперника из избранного.', 'pt': 'Deslize a tela para BAIXO para a CORRESPONDÊNCIA: partidas sem limite de tempo, contra jogadores registrados. Para iniciar uma, toque em um tabuleiro vazio e escolha seu adversário entre os favoritos.'},
    '« Compte » : crée ton compte ici. Il est OBLIGATOIRE pour jouer en ligne et en correspondance.': {'en': '“Account”: create your account here. It is REQUIRED to play online and by correspondence.', 'de': '„Konto“: Erstelle hier dein Konto. Es ist ERFORDERLICH, um online und per Fernpartie zu spielen.', 'es': '«Cuenta»: crea tu cuenta aquí. Es OBLIGATORIA para jugar en línea y por correspondencia.', 'it': '«Account»: crea qui il tuo account. È OBBLIGATORIO per giocare online e per corrispondenza.', 'zh': '“账号”：在此创建你的账号。在线对战和通信对局都必须拥有账号。', 'ja': '「アカウント」：ここでアカウントを作成します。オンライン対戦と通信対局には必須です。', 'ko': '“계정”: 여기서 계정을 만드세요. 온라인 대전과 통신 대국에 필수입니다.', 'ru': '«Аккаунт»: создайте здесь свой аккаунт. Он ОБЯЗАТЕЛЕН для игры онлайн и по переписке.', 'pt': '«Conta»: crie sua conta aqui. É OBRIGATÓRIA para jogar online e por correspondência.'},
    '« Random » active la variante Random Fuga : la position de départ est tirée au hasard parmi 1750 positions x 2 types de symétrie, soit 3500 débuts possibles. Il se réinitialise à chaque lancement.': {'en': '“Random” enables the Random Fuga variant: the starting position is drawn at random from 1750 positions × 2 types of symmetry, i.e. 3500 possible openings. It resets on every launch.', 'de': '„Random“ aktiviert die Variante Random Fuga: Die Startstellung wird zufällig aus 1750 Stellungen × 2 Symmetriearten gezogen, also 3500 mögliche Eröffnungen. Sie wird bei jedem Start neu gesetzt.', 'es': '«Random» activa la variante Random Fuga: la posición inicial se sortea entre 1750 posiciones × 2 tipos de simetría, es decir 3500 aperturas posibles. Se reinicia en cada arranque.', 'it': '«Random» attiva la variante Random Fuga: la posizione iniziale è estratta a caso tra 1750 posizioni × 2 tipi di simmetria, cioè 3500 aperture possibili. Si reimposta a ogni avvio.', 'zh': '“Random”启用 Random Fuga 变体：起始局面从 1750 个局面 × 2 种对称类型中随机抽取，即 3500 种可能开局。每次启动都会重置。', 'ja': '「Random」は Random Fuga のバリアントを有効にします：初期局面は1750局面×2種類の対称から無作為に選ばれ、計3500通りの開始があります。起動ごとにリセットされます。', 'ko': '“Random”은 Random Fuga 변형을 켭니다: 시작 위치는 1750개 위치 × 2가지 대칭 유형에서 무작위로 뽑히며, 즉 3500가지 오프닝이 있습니다. 실행할 때마다 초기화됩니다.', 'ru': '«Random» включает вариант Random Fuga: начальная позиция выбирается случайно из 1750 позиций × 2 типа симметрии, то есть 3500 возможных начал. Сбрасывается при каждом запуске.', 'pt': '«Random» ativa a variante Random Fuga: a posição inicial é sorteada entre 1750 posições × 2 tipos de simetria, ou seja 3500 aberturas possíveis. Reinicia a cada inicialização.'},
    "« Plus » donne accès à ce tuto, à l'historique de tes parties, à l'analyse, aux réglages, et à SOUTENIR LES DÉVELOPPEURS (un petit don pour aider le jeu).": {'en': '“More” gives access to this tutorial, your game history, analysis, settings, and to SUPPORTING THE DEVELOPERS (a small donation to help the game).', 'de': '„Mehr“ gibt Zugang zu diesem Tutorial, deinem Partienverlauf, der Analyse, den Einstellungen und dazu, DIE ENTWICKLER ZU UNTERSTÜTZEN (eine kleine Spende, um dem Spiel zu helfen).', 'es': '«Más» da acceso a este tutorial, al historial de tus partidas, al análisis, a los ajustes y a APOYAR A LOS DESARROLLADORES (una pequeña donación para ayudar al juego).', 'it': "«Altro» dà accesso a questo tutorial, alla cronologia delle tue partite, all'analisi, alle impostazioni e a SOSTENERE GLI SVILUPPATORI (una piccola donazione per aiutare il gioco).", 'zh': '“更多”可访问本教程、你的对局历史、分析、设置，以及支持开发者（一点小额捐赠来帮助游戏）。', 'ja': '「その他」から、このチュートリアル、対局履歴、解析、設定、そして開発者を支援する（ゲームを助ける少額の寄付）にアクセスできます。', 'ko': '“더보기”에서 이 튜토리얼, 대국 기록, 분석, 설정, 그리고 개발자 후원(게임을 돕는 소액 기부)에 접근할 수 있습니다.', 'ru': '«Ещё» даёт доступ к этому обучению, истории ваших партий, анализу, настройкам и к ПОДДЕРЖКЕ РАЗРАБОТЧИКОВ (небольшое пожертвование в помощь игре).', 'pt': '«Mais» dá acesso a este tutorial, ao histórico das suas partidas, à análise, às configurações e a APOIAR OS DESENVOLVEDORES (uma pequena doação para ajudar o jogo).'},
    'Et voilà, tu sais tout ! Le reste (thèmes, réglages, historique, analyse), tu le découvriras toi-même. Bonne fugue !': {'en': "That's it, you know everything! The rest (themes, settings, history, analysis) you'll discover on your own. Happy escaping!", 'de': "Das war's, du weißt alles! Den Rest (Themen, Einstellungen, Verlauf, Analyse) entdeckst du selbst. Gute Flucht!", 'es': '¡Y ya está, lo sabes todo! El resto (temas, ajustes, historial, análisis) lo descubrirás por ti mismo. ¡Buena huida!', 'it': 'Ecco, sai tutto! Il resto (temi, impostazioni, cronologia, analisi) lo scoprirai da solo. Buona fuga!', 'zh': '就是这样，你已经全知道了！其余的（主题、设置、历史、分析）你会自己发现。祝出逃顺利！', 'ja': 'これで全部わかりました！残り（テーマ、設定、履歴、解析）は自分で見つけてください。よい逃走を！', 'ko': '이제 다 아셨습니다! 나머지(테마, 설정, 기록, 분석)는 스스로 발견하게 됩니다. 멋진 탈출을!', 'ru': 'Вот и всё, вы знаете всё! Остальное (темы, настройки, история, анализ) вы откроете сами. Удачного побега!', 'pt': 'É isso, você sabe tudo! O resto (temas, configurações, histórico, análise) você descobrirá sozinho. Boa fuga!'},
})


TRANSLATIONS.update({
    'Compte créé !': {'en': 'Account created!', 'de': 'Konto erstellt!', 'es': '¡Cuenta creada!', 'it': 'Account creato!', 'zh': '账号已创建！', 'ja': 'アカウントを作成しました！', 'ko': '계정이 생성되었습니다!', 'ru': 'Аккаунт создан!', 'pt': 'Conta criada!'},
    'Connecté !': {'en': 'Connected!', 'de': 'Verbunden!', 'es': '¡Conectado!', 'it': 'Connesso!', 'zh': '已连接！', 'ja': '接続しました！', 'ko': '연결되었습니다!', 'ru': 'Подключено!', 'pt': 'Conectado!'},
    'Erreur inconnue': {'en': 'Unknown error', 'de': 'Unbekannter Fehler', 'es': 'Error desconocido', 'it': 'Errore sconosciuto', 'zh': '未知错误', 'ja': '不明なエラー', 'ko': '알 수 없는 오류', 'ru': 'Неизвестная ошибка', 'pt': 'Erro desconhecido'},
    'Erreur serveur (%d)': {'en': 'Server error (%d)', 'de': 'Serverfehler (%d)', 'es': 'Error del servidor (%d)', 'it': 'Errore del server (%d)', 'zh': '服务器错误 (%d)', 'ja': 'サーバーエラー (%d)', 'ko': '서버 오류 (%d)', 'ru': 'Ошибка сервера (%d)', 'pt': 'Erro do servidor (%d)'},
    'Erreur réseau : ': {'en': 'Network error: ', 'de': 'Netzwerkfehler: ', 'es': 'Error de red: ', 'it': 'Errore di rete: ', 'zh': '网络错误：', 'ja': 'ネットワークエラー：', 'ko': '네트워크 오류: ', 'ru': 'Ошибка сети: ', 'pt': 'Erro de rede: '},
    'Module réseau indisponible': {'en': 'Network module unavailable', 'de': 'Netzwerkmodul nicht verfügbar', 'es': 'Módulo de red no disponible', 'it': 'Modulo di rete non disponibile', 'zh': '网络模块不可用', 'ja': 'ネットワークモジュールが利用できません', 'ko': '네트워크 모듈을 사용할 수 없습니다', 'ru': 'Сетевой модуль недоступен', 'pt': 'Módulo de rede indisponível'},
    'Non connecté': {'en': 'Not connected', 'de': 'Nicht verbunden', 'es': 'No conectado', 'it': 'Non connesso', 'zh': '未连接', 'ja': '未接続', 'ko': '연결되지 않음', 'ru': 'Не подключено', 'pt': 'Não conectado'},
    'Connexion requise': {'en': 'Login required', 'de': 'Anmeldung erforderlich', 'es': 'Inicio de sesión requerido', 'it': 'Accesso richiesto', 'zh': '需要登录', 'ja': 'ログインが必要です', 'ko': '로그인이 필요합니다', 'ru': 'Требуется вход', 'pt': 'Login necessário'},
    'Connectez-vous (bouton Compte)\npour jouer en ligne.': {'en': 'Log in (Account button)\nto play online.', 'de': 'Melde dich an (Konto-Schaltfläche),\num online zu spielen.', 'es': 'Inicia sesión (botón Cuenta)\npara jugar en línea.', 'it': 'Accedi (pulsante Account)\nper giocare online.', 'zh': '请登录（账号按钮）\n以进行在线对战。', 'ja': 'オンラインで遊ぶには\nログインしてください（アカウントボタン）。', 'ko': '온라인 플레이를 하려면\n로그인하세요 (계정 버튼).', 'ru': 'Войдите (кнопка «Аккаунт»),\nчтобы играть онлайн.', 'pt': 'Entre (botão Conta)\npara jogar online.'},
    'Connexion impossible :\n%s': {'en': 'Connection failed:\n%s', 'de': 'Verbindung fehlgeschlagen:\n%s', 'es': 'Conexión fallida:\n%s', 'it': 'Connessione non riuscita:\n%s', 'zh': '连接失败：\n%s', 'ja': '接続に失敗しました：\n%s', 'ko': '연결 실패:\n%s', 'ru': 'Не удалось подключиться:\n%s', 'pt': 'Falha na conexão:\n%s'},
    "Recherche d'un adversaire…\n\nObjectif : %s\nCadence : %s": {'en': 'Searching for an opponent…\n\nObjective: %s\nTime: %s', 'de': 'Suche nach einem Gegner…\n\nZiel: %s\nZeit: %s', 'es': 'Buscando un rival…\n\nObjetivo: %s\nTiempo: %s', 'it': 'Ricerca di un avversario…\n\nObiettivo: %s\nTempo: %s', 'zh': '正在寻找对手…\n\n目标：%s\n时间：%s', 'ja': '対戦相手を検索中…\n\n目標：%s\n持ち時間：%s', 'ko': '상대를 찾는 중…\n\n목표: %s\n시간: %s', 'ru': 'Поиск соперника…\n\nЦель: %s\nВремя: %s', 'pt': 'Procurando um adversário…\n\nObjetivo: %s\nTempo: %s'},
    "Toujours en recherche…\n\nEssayez une autre cadence si l'attente\nse prolonge.": {'en': 'Still searching…\n\nTry another time control if the wait\ngoes on.', 'de': 'Suche läuft noch…\n\nProbiere eine andere Bedenkzeit, wenn das\nWarten andauert.', 'es': 'Sigue buscando…\n\nPrueba otro tiempo si la espera\nse prolonga.', 'it': "Ancora in ricerca…\n\nProva un altro tempo se l'attesa\nsi prolunga.", 'zh': '仍在搜索…\n\n若等待时间过长，\n请尝试其他时间设置。', 'ja': 'まだ検索中…\n\n待ち時間が長い場合は\n別の持ち時間をお試しください。', 'ko': '계속 찾는 중…\n\n기다림이 길어지면\n다른 시간을 시도해 보세요.', 'ru': 'Всё ещё идёт поиск…\n\nЕсли ожидание затянулось,\nпопробуйте другой контроль времени.', 'pt': 'Ainda procurando…\n\nTente outro tempo se a espera\nse prolongar.'},
    'Recherche': {'en': 'Search', 'de': 'Suche', 'es': 'Búsqueda', 'it': 'Ricerca', 'zh': '搜索', 'ja': '検索', 'ko': '검색', 'ru': 'Поиск', 'pt': 'Busca'},
    'Erreur : %s': {'en': 'Error: %s', 'de': 'Fehler: %s', 'es': 'Error: %s', 'it': 'Errore: %s', 'zh': '错误：%s', 'ja': 'エラー：%s', 'ko': '오류: %s', 'ru': 'Ошибка: %s', 'pt': 'Erro: %s'},
    'Aucun joueur nommé « %s ».': {'en': 'No player named “%s”.', 'de': 'Kein Spieler namens „%s“.', 'es': 'Ningún jugador llamado «%s».', 'it': 'Nessun giocatore di nome «%s».', 'zh': '没有名为“%s”的玩家。', 'ja': '「%s」という名前のプレイヤーはいません。', 'ko': '“%s”라는 플레이어가 없습니다.', 'ru': 'Нет игрока с именем «%s».', 'pt': 'Nenhum jogador chamado «%s».'},
    "C'est vous !": {'en': "That's you!", 'de': 'Das bist du!', 'es': '¡Eres tú!', 'it': 'Sei tu!', 'zh': '这是你！', 'ja': 'あなたです！', 'ko': '바로 당신입니다!', 'ru': 'Это вы!', 'pt': 'É você!'},
    'Hors ligne': {'en': 'Offline', 'de': 'Offline', 'es': 'Desconectado', 'it': 'Offline', 'zh': '离线', 'ja': 'オフライン', 'ko': '오프라인', 'ru': 'Не в сети', 'pt': 'Offline'},
    'Enregistrer': {'en': 'Save', 'de': 'Speichern', 'es': 'Guardar', 'it': 'Salva', 'zh': '保存', 'ja': '保存', 'ko': '저장', 'ru': 'Сохранить', 'pt': 'Salvar'},
    'Favoris': {'en': 'Favorites', 'de': 'Favoriten', 'es': 'Favoritos', 'it': 'Preferiti', 'zh': '收藏', 'ja': 'お気に入り', 'ko': '즐겨찾기', 'ru': 'Избранное', 'pt': 'Favoritos'},
    'En attente de sa réponse.': {'en': 'Waiting for their reply.', 'de': 'Warte auf seine Antwort.', 'es': 'Esperando su respuesta.', 'it': 'In attesa della sua risposta.', 'zh': '等待对方回复。', 'ja': '相手の返答を待っています。', 'ko': '상대의 응답을 기다리는 중입니다.', 'ru': 'Ожидание его ответа.', 'pt': 'Aguardando a resposta.'},
    'Vous ne pouvez pas vous défier vous-même.': {'en': "You can't challenge yourself.", 'de': 'Du kannst dich nicht selbst herausfordern.', 'es': 'No puedes desafiarte a ti mismo.', 'it': 'Non puoi sfidare te stesso.', 'zh': '你不能向自己发起挑战。', 'ja': '自分自身に挑戦することはできません。', 'ko': '자신에게 도전할 수 없습니다.', 'ru': 'Нельзя бросить вызов самому себе.', 'pt': 'Você não pode desafiar a si mesmo.'},
    "Désolé, cet adversaire n'est pas disponible.": {'en': "Sorry, this opponent isn't available.", 'de': 'Dieser Gegner ist leider nicht verfügbar.', 'es': 'Lo sentimos, este rival no está disponible.', 'it': 'Spiacenti, questo avversario non è disponibile.', 'zh': '抱歉，该对手当前不可用。', 'ja': '申し訳ありません、この相手は対応できません。', 'ko': '죄송합니다, 이 상대는 사용할 수 없습니다.', 'ru': 'Извините, этот соперник недоступен.', 'pt': 'Desculpe, este adversário não está disponível.'},
    'Défi': {'en': 'Challenge', 'de': 'Herausforderung', 'es': 'Desafío', 'it': 'Sfida', 'zh': '挑战', 'ja': '挑戦', 'ko': '도전', 'ru': 'Вызов', 'pt': 'Desafio'},
    'Un joueur': {'en': 'A player', 'de': 'Ein Spieler', 'es': 'Un jugador', 'it': 'Un giocatore', 'zh': '一位玩家', 'ja': 'あるプレイヤー', 'ko': '어떤 플레이어', 'ru': 'Игрок', 'pt': 'Um jogador'},
    '%s a refusé votre défi.': {'en': '%s declined your challenge.', 'de': '%s hat deine Herausforderung abgelehnt.', 'es': '%s rechazó tu desafío.', 'it': '%s ha rifiutato la tua sfida.', 'zh': '%s 拒绝了你的挑战。', 'ja': '%s があなたの挑戦を辞退しました。', 'ko': '%s 님이 당신의 도전을 거절했습니다.', 'ru': '%s отклонил ваш вызов.', 'pt': '%s recusou seu desafio.'},
    'Défi envoyé à %s !': {'en': 'Challenge sent to %s!', 'de': 'Herausforderung an %s gesendet!', 'es': '¡Desafío enviado a %s!', 'it': 'Sfida inviata a %s!', 'zh': '已向 %s 发送挑战！', 'ja': '%s に挑戦を送信しました！', 'ko': '%s 님에게 도전을 보냈습니다!', 'ru': 'Вызов отправлен %s!', 'pt': 'Desafio enviado a %s!'},
    'Revanche envoyée à %s !': {'en': 'Rematch sent to %s!', 'de': 'Revanche an %s gesendet!', 'es': '¡Revancha enviada a %s!', 'it': 'Rivincita inviata a %s!', 'zh': '已向 %s 发送再战请求！', 'ja': '%s に再戦を送信しました！', 'ko': '%s 님에게 재대국을 보냈습니다!', 'ru': 'Реванш отправлен %s!', 'pt': 'Revanche enviada a %s!'},
    '%s ajouté aux favoris !': {'en': '%s added to favorites!', 'de': '%s zu Favoriten hinzugefügt!', 'es': '¡%s añadido a favoritos!', 'it': '%s aggiunto ai preferiti!', 'zh': '已将 %s 加入收藏！', 'ja': '%s をお気に入りに追加しました！', 'ko': '%s 님을 즐겨찾기에 추가했습니다!', 'ru': '%s добавлен в избранное!', 'pt': '%s adicionado aos favoritos!'},
    '%s retiré des favoris.': {'en': '%s removed from favorites.', 'de': '%s aus Favoriten entfernt.', 'es': '%s eliminado de favoritos.', 'it': '%s rimosso dai preferiti.', 'zh': '已将 %s 从收藏移除。', 'ja': '%s をお気に入りから削除しました。', 'ko': '%s 님을 즐겨찾기에서 제거했습니다.', 'ru': '%s удалён из избранного.', 'pt': '%s removido dos favoritos.'},
    'Échec du défi.': {'en': 'Challenge failed.', 'de': 'Herausforderung fehlgeschlagen.', 'es': 'El desafío falló.', 'it': 'Sfida non riuscita.', 'zh': '挑战失败。', 'ja': '挑戦に失敗しました。', 'ko': '도전에 실패했습니다.', 'ru': 'Не удалось отправить вызов.', 'pt': 'O desafio falhou.'},
    'Échec : %s': {'en': 'Failed: %s', 'de': 'Fehlgeschlagen: %s', 'es': 'Falló: %s', 'it': 'Non riuscito: %s', 'zh': '失败：%s', 'ja': '失敗：%s', 'ko': '실패: %s', 'ru': 'Ошибка: %s', 'pt': 'Falhou: %s'},
    'Correspondance': {'en': 'Correspondence', 'de': 'Fernpartie', 'es': 'Correspondencia', 'it': 'Corrispondenza', 'zh': '通信对局', 'ja': '通信対局', 'ko': '통신 대국', 'ru': 'Переписка', 'pt': 'Correspondência'},
    'Corresp': {'en': 'Corresp.', 'de': 'Fern', 'es': 'Corresp.', 'it': 'Corrisp.', 'zh': '通信', 'ja': '通信', 'ko': '통신', 'ru': 'Переп.', 'pt': 'Corresp.'},
    'Ce lien sera bientôt disponible.': {'en': 'This link will be available soon.', 'de': 'Dieser Link ist bald verfügbar.', 'es': 'Este enlace estará disponible pronto.', 'it': 'Questo link sarà presto disponibile.', 'zh': '该链接即将开放。', 'ja': 'このリンクは近日利用可能になります。', 'ko': '이 링크는 곧 제공됩니다.', 'ru': 'Эта ссылка скоро будет доступна.', 'pt': 'Este link estará disponível em breve.'},
    "Aucun favori pour le moment.\nCherchez un joueur pour l'ajouter en favori.": {'en': 'No favorites yet.\nSearch for a player to add them as a favorite.', 'de': 'Noch keine Favoriten.\nSuche einen Spieler, um ihn als Favorit hinzuzufügen.', 'es': 'Aún no hay favoritos.\nBusca a un jugador para añadirlo a favoritos.', 'it': 'Ancora nessun preferito.\nCerca un giocatore per aggiungerlo ai preferiti.', 'zh': '暂无收藏。\n搜索玩家以将其加入收藏。', 'ja': 'まだお気に入りがありません。\nプレイヤーを検索してお気に入りに追加しましょう。', 'ko': '아직 즐겨찾기가 없습니다.\n플레이어를 검색해 즐겨찾기에 추가하세요.', 'ru': 'Пока нет избранного.\nНайдите игрока, чтобы добавить его в избранное.', 'pt': 'Ainda sem favoritos.\nProcure um jogador para adicioná-lo aos favoritos.'},
    'Chat (%d)': {'en': 'Chat (%d)', 'de': 'Chat (%d)', 'es': 'Chat (%d)', 'it': 'Chat (%d)', 'zh': '聊天 (%d)', 'ja': 'チャット (%d)', 'ko': '채팅 (%d)', 'ru': 'Чат (%d)', 'pt': 'Chat (%d)'},
    'Chat, %s': {'en': 'Chat, %s', 'de': 'Chat, %s', 'es': 'Chat, %s', 'it': 'Chat, %s', 'zh': '聊天，%s', 'ja': 'チャット、%s', 'ko': '채팅, %s', 'ru': 'Чат, %s', 'pt': 'Chat, %s'},
    'Score final\n%s : %d    %s : %d': {'en': 'Final score\n%s: %d    %s: %d', 'de': 'Endstand\n%s: %d    %s: %d', 'es': 'Marcador final\n%s: %d    %s: %d', 'it': 'Punteggio finale\n%s: %d    %s: %d', 'zh': '最终比分\n%s：%d    %s：%d', 'ja': '最終スコア\n%s：%d    %s：%d', 'ko': '최종 점수\n%s: %d    %s: %d', 'ru': 'Итоговый счёт\n%s: %d    %s: %d', 'pt': 'Placar final\n%s: %d    %s: %d'},
    "Collez le contenu d'un fichier .nmc ci-dessous :": {'en': 'Paste the contents of a .nmc file below:', 'de': 'Füge unten den Inhalt einer .nmc-Datei ein:', 'es': 'Pega el contenido de un archivo .nmc abajo:', 'it': 'Incolla qui sotto il contenuto di un file .nmc:', 'zh': '在下方粘贴 .nmc 文件的内容：', 'ja': '下に .nmc ファイルの内容を貼り付けてください：', 'ko': '아래에 .nmc 파일 내용을 붙여넣으세요:', 'ru': 'Вставьте содержимое файла .nmc ниже:', 'pt': 'Cole o conteúdo de um arquivo .nmc abaixo:'},
    'Lire': {'en': 'Read', 'de': 'Lesen', 'es': 'Leer', 'it': 'Leggi', 'zh': '读取', 'ja': '読み込む', 'ko': '읽기', 'ru': 'Читать', 'pt': 'Ler'},
    "Dernier saut, en DIAGONALE par-dessus fa8 : l'Héritier SORT du plateau et rejoint son ralliement !": {'en': 'Last jump, DIAGONALLY over fa8: the Heir LEAVES the board and reaches its rally zone!', 'de': 'Letzter Sprung, DIAGONAL über fa8: Der Erbe VERLÄSST das Brett und erreicht seine Sammelzone!', 'es': 'Último salto, en DIAGONAL sobre fa8: ¡el Heredero SALE del tablero y alcanza su zona de reunión!', 'it': "Ultimo salto, in DIAGONALE oltre fa8: l'Erede ESCE dalla scacchiera e raggiunge la sua zona di raduno!", 'zh': '最后一跳，沿对角线跃过 fa8：继承人离开棋盘并抵达集结区！', 'ja': '最後のジャンプ、fa8 を斜めに跳び越え：後継者が盤を出て集結ゾーンに到達します！', 'ko': '마지막 점프, fa8을 대각선으로 넘어: 후계자가 판을 벗어나 집결 구역에 도달합니다!', 'ru': 'Последний прыжок, ПО ДИАГОНАЛИ через fa8: Наследник ПОКИДАЕТ доску и достигает зоны сбора!', 'pt': 'Último salto, na DIAGONAL sobre fa8: o Herdeiro SAI do tabuleiro e chega à sua zona de reunião!'},
    'Tu peux pousser une AUTRE direction ! Clique en sol4 (vers la droite).': {'en': 'You can push in ANOTHER direction! Tap sol4 (to the right).', 'de': 'Du kannst in eine ANDERE Richtung schieben! Tippe auf sol4 (nach rechts).', 'es': '¡Puedes empujar en OTRA dirección! Toca sol4 (a la derecha).', 'it': "Puoi spingere in un'ALTRA direzione! Tocca sol4 (verso destra).", 'zh': '你可以往另一个方向推动！点击 sol4（向右）。', 'ja': '別の方向にも押せます！sol4（右）をタップしましょう。', 'ko': '다른 방향으로도 밀 수 있습니다! sol4(오른쪽)를 누르세요.', 'ru': 'Можно толкнуть в ДРУГОМ направлении! Нажмите sol4 (вправо).', 'pt': 'Você pode empurrar em OUTRA direção! Toque em sol4 (à direita).'},
})


TRANSLATIONS.update({
    '{winner} gagne la partie': {'en': '{winner} wins the game', 'de': '{winner} gewinnt die Partie', 'es': '{winner} gana la partida', 'it': '{winner} vince la partita', 'zh': '{winner} 赢得对局', 'ja': '{winner} が対局に勝利', 'ko': '{winner} 님이 대국에서 승리', 'ru': '{winner} выигрывает партию', 'pt': '{winner} vence a partida'},
    'Victoire par {v} (+{pts} pt)': {'en': 'Victory by {v} (+{pts} pt)', 'de': 'Sieg durch {v} (+{pts} Pkt)', 'es': 'Victoria por {v} (+{pts} pt)', 'it': 'Vittoria per {v} (+{pts} pt)', 'zh': '以{v}获胜（+{pts} 分）', 'ja': '{v}で勝利（+{pts} 点）', 'ko': '{v}(으)로 승리 (+{pts}점)', 'ru': 'Победа: {v} (+{pts} очк.)', 'pt': 'Vitória por {v} (+{pts} pt)'},
    'fugue': {'en': 'escape', 'de': 'Flucht', 'es': 'huida', 'it': 'fuga', 'zh': '出逃', 'ja': 'フーグ', 'ko': '탈출', 'ru': 'побег', 'pt': 'fuga'},
    'mat': {'en': 'checkmate', 'de': 'Matt', 'es': 'mate', 'it': 'matto', 'zh': '将杀', 'ja': '詰み', 'ko': '메이트', 'ru': 'мат', 'pt': 'mate'},
    'temps écoulé': {'en': 'timeout', 'de': 'Zeitüberschreitung', 'es': 'tiempo agotado', 'it': 'tempo scaduto', 'zh': '超时', 'ja': '時間切れ', 'ko': '시간 초과', 'ru': 'истечение времени', 'pt': 'tempo esgotado'},
    'abandon': {'en': 'resignation', 'de': 'Aufgabe', 'es': 'abandono', 'it': 'abbandono', 'zh': '认输', 'ja': '投了', 'ko': '기권', 'ru': 'сдача', 'pt': 'desistência'},
    'Prochaine partie : {name} joue les Blancs': {'en': 'Next game: {name} plays White', 'de': 'Nächste Partie: {name} spielt Weiß', 'es': 'Siguiente partida: {name} juega Blancas', 'it': 'Prossima partita: {name} gioca col Bianco', 'zh': '下一局：{name} 执白', 'ja': '次の対局：{name} が白番', 'ko': '다음 대국: {name} 님이 백', 'ru': 'Следующая партия: {name} играет белыми', 'pt': 'Próxima partida: {name} joga de Brancas'},
    'Victoire de {name} !': {'en': '{name} wins!', 'de': 'Sieg für {name}!', 'es': '¡Gana {name}!', 'it': 'Vince {name}!', 'zh': '{name} 获胜！', 'ja': '{name} の勝利！', 'ko': '{name} 님 승리!', 'ru': 'Победа {name}!', 'pt': '{name} vence!'},
    '  ·  en ligne': {'en': '  ·  online', 'de': '  ·  online', 'es': '  ·  en línea', 'it': '  ·  online', 'zh': '  ·  在线', 'ja': '  ·  オンライン', 'ko': '  ·  온라인', 'ru': '  ·  онлайн', 'pt': '  ·  online'},
    'Original': {'en': 'Original', 'de': 'Original', 'es': 'Original', 'it': 'Originale', 'zh': '原版', 'ja': 'オリジナル', 'ko': '오리지널', 'ru': 'Оригинал', 'pt': 'Original'},
    'Forêt': {'en': 'Forest', 'de': 'Wald', 'es': 'Bosque', 'it': 'Foresta', 'zh': '森林', 'ja': '森', 'ko': '숲', 'ru': 'Лес', 'pt': 'Floresta'},
    'Océan': {'en': 'Ocean', 'de': 'Ozean', 'es': 'Océano', 'it': 'Oceano', 'zh': '海洋', 'ja': '海', 'ko': '바다', 'ru': 'Океан', 'pt': 'Oceano'},
    'Volcan': {'en': 'Volcano', 'de': 'Vulkan', 'es': 'Volcán', 'it': 'Vulcano', 'zh': '火山', 'ja': '火山', 'ko': '화산', 'ru': 'Вулкан', 'pt': 'Vulcão'},
    'Hémo': {'en': 'Hemo', 'de': 'Hämo', 'es': 'Hemo', 'it': 'Emo', 'zh': '血色', 'ja': 'ヘモ', 'ko': '헤모', 'ru': 'Гемо', 'pt': 'Hemo'},
    'Spatial': {'en': 'Space', 'de': 'Weltraum', 'es': 'Espacial', 'it': 'Spaziale', 'zh': '太空', 'ja': '宇宙', 'ko': '우주', 'ru': 'Космос', 'pt': 'Espacial'},
    'Impérial': {'en': 'Imperial', 'de': 'Imperial', 'es': 'Imperial', 'it': 'Imperiale', 'zh': '帝国', 'ja': '帝国', 'ko': '제국', 'ru': 'Имперский', 'pt': 'Imperial'},
    'Royal': {'en': 'Royal', 'de': 'Königlich', 'es': 'Real', 'it': 'Reale', 'zh': '皇家', 'ja': 'ロイヤル', 'ko': '로열', 'ru': 'Королевский', 'pt': 'Real'},
    'Terre': {'en': 'Earth', 'de': 'Erde', 'es': 'Tierra', 'it': 'Terra', 'zh': '大地', 'ja': '大地', 'ko': '대지', 'ru': 'Земля', 'pt': 'Terra'},
    'Bonbon': {'en': 'Candy', 'de': 'Bonbon', 'es': 'Caramelo', 'it': 'Caramella', 'zh': '糖果', 'ja': 'キャンディ', 'ko': '사탕', 'ru': 'Конфета', 'pt': 'Doce'},
    'Arc-en-ciel': {'en': 'Rainbow', 'de': 'Regenbogen', 'es': 'Arcoíris', 'it': 'Arcobaleno', 'zh': '彩虹', 'ja': '虹', 'ko': '무지개', 'ru': 'Радуга', 'pt': 'Arco-íris'},
    'Étoile': {'en': 'Star', 'de': 'Stern', 'es': 'Estrella', 'it': 'Stella', 'zh': '星星', 'ja': '星', 'ko': '별', 'ru': 'Звезда', 'pt': 'Estrela'},
    'Médiéval': {'en': 'Medieval', 'de': 'Mittelalter', 'es': 'Medieval', 'it': 'Medievale', 'zh': '中世纪', 'ja': '中世', 'ko': '중세', 'ru': 'Средневековье', 'pt': 'Medieval'},
    'Fleur': {'en': 'Flower', 'de': 'Blume', 'es': 'Flor', 'it': 'Fiore', 'zh': '花', 'ja': '花', 'ko': '꽃', 'ru': 'Цветок', 'pt': 'Flor'},
    'Insectes': {'en': 'Insects', 'de': 'Insekten', 'es': 'Insectos', 'it': 'Insetti', 'zh': '昆虫', 'ja': '昆虫', 'ko': '곤충', 'ru': 'Насекомые', 'pt': 'Insetos'},
    'Piano': {'en': 'Piano', 'de': 'Klavier', 'es': 'Piano', 'it': 'Piano', 'zh': '钢琴', 'ja': 'ピアノ', 'ko': '피아노', 'ru': 'Пианино', 'pt': 'Piano'},
    'Orgue': {'en': 'Organ', 'de': 'Orgel', 'es': 'Órgano', 'it': 'Organo', 'zh': '管风琴', 'ja': 'オルガン', 'ko': '오르간', 'ru': 'Орган', 'pt': 'Órgão'},
    'Guitare': {'en': 'Guitar', 'de': 'Gitarre', 'es': 'Guitarra', 'it': 'Chitarra', 'zh': '吉他', 'ja': 'ギター', 'ko': '기타', 'ru': 'Гитара', 'pt': 'Violão'},
    'Cloche': {'en': 'Bell', 'de': 'Glocke', 'es': 'Campana', 'it': 'Campana', 'zh': '钟', 'ja': 'ベル', 'ko': '종', 'ru': 'Колокол', 'pt': 'Sino'},
})


TRANSLATIONS.update({
    'Mélo : %d': {'en': 'Mélo: %d', 'de': 'Mélo: %d', 'es': 'Mélo: %d', 'it': 'Mélo: %d', 'zh': 'Mélo：%d', 'ja': 'Mélo：%d', 'ko': 'Mélo: %d', 'ru': 'Mélo: %d', 'pt': 'Mélo: %d'},
})


TRANSLATIONS.update({
    'Historique': {'en': 'History', 'de': 'Verlauf', 'es': 'Historial', 'it': 'Cronologia', 'zh': '历史', 'ja': '履歴', 'ko': '기록', 'ru': 'История', 'pt': 'Histórico'},
    'Héritier': {'en': 'Heir', 'de': 'Erbe', 'es': 'Heredero', 'it': 'Erede', 'zh': '继承人', 'ja': '後継者', 'ko': '후계자', 'ru': 'Наследник', 'pt': 'Herdeiro'},
    'Chevalier': {'en': 'Knight', 'de': 'Ritter', 'es': 'Caballero', 'it': 'Cavaliere', 'zh': '骑士', 'ja': '騎士', 'ko': '기사', 'ru': 'Рыцарь', 'pt': 'Cavaleiro'},
    'Nurse': {'en': 'Nurse', 'de': 'Amme', 'es': 'Nodriza', 'it': 'Balia', 'zh': '乳母', 'ja': '乳母', 'ko': '유모', 'ru': 'Нянька', 'pt': 'Ama'},
    'Soldat': {'en': 'Soldier', 'de': 'Soldat', 'es': 'Soldado', 'it': 'Soldato', 'zh': '士兵', 'ja': '兵士', 'ko': '병사', 'ru': 'Солдат', 'pt': 'Soldado'},
    'Garde': {'en': 'Guard', 'de': 'Wächter', 'es': 'Guardia', 'it': 'Guardia', 'zh': '卫兵', 'ja': '衛兵', 'ko': '근위병', 'ru': 'Страж', 'pt': 'Guarda'},
})


TRANSLATIONS.update({
    'Abandonner compte comme une DÉFAITE.\nVotre adversaire gagne les points.': {'en': 'Resigning counts as a LOSS.\nYour opponent gets the points.', 'de': 'Aufgeben zählt als NIEDERLAGE.\nDein Gegner erhält die Punkte.', 'es': 'Abandonar cuenta como una DERROTA.\nTu rival gana los puntos.', 'it': 'Abbandonare conta come una SCONFITTA.\nIl tuo avversario ottiene i punti.', 'zh': '认输将计为一场失败。\n对手获得分数。', 'ja': '投了は敗北として扱われます。\n相手が得点します。', 'ko': '기권은 패배로 처리됩니다.\n상대가 점수를 얻습니다.', 'ru': 'Сдача засчитывается как ПОРАЖЕНИЕ.\nСоперник получает очки.', 'pt': 'Desistir conta como uma DERROTA.\nSeu adversário ganha os pontos.'},
    'Abandonner compte comme une défaite\ndans cette partie de correspondance.': {'en': 'Resigning counts as a loss\nin this correspondence game.', 'de': 'Aufgeben zählt als Niederlage\nin dieser Fernpartie.', 'es': 'Abandonar cuenta como una derrota\nen esta partida por correspondencia.', 'it': 'Abbandonare conta come una sconfitta\nin questa partita per corrispondenza.', 'zh': '在这局通信对局中，认输将计为一场失败。', 'ja': 'この通信対局では、投了は敗北として扱われます。', 'ko': '이 통신 대국에서 기권은 패배로 처리됩니다.', 'ru': 'Сдача засчитывается как поражение\nв этой партии по переписке.', 'pt': 'Desistir conta como uma derrota\nnesta partida por correspondência.'},
    'La partie en cours sera perdue.': {'en': 'The current game will be lost.', 'de': 'Die laufende Partie geht verloren.', 'es': 'La partida en curso se perderá.', 'it': 'La partita in corso sarà persa.', 'zh': '当前对局将判负。', 'ja': '進行中の対局は負けになります。', 'ko': '진행 중인 대국은 패배가 됩니다.', 'ru': 'Текущая партия будет проиграна.', 'pt': 'A partida em curso será perdida.'},
    'Partie nulle': {'en': 'Draw', 'de': 'Remis', 'es': 'Tablas', 'it': 'Patta', 'zh': '和棋', 'ja': '引き分け', 'ko': '무승부', 'ru': 'Ничья', 'pt': 'Empate'},
})


TRANSLATIONS.update({
    'Joueur 1 deconnecte': {'en': 'Player 1 disconnects', 'de': 'Spieler 1 trennt Verbindung', 'es': 'El Jugador 1 se desconecta', 'it': 'Il Giocatore 1 si disconnette', 'zh': '玩家 1 断线', 'ja': 'プレイヤー1が切断', 'ko': '플레이어 1 연결 끊김', 'ru': 'Игрок 1 отключается', 'pt': 'Jogador 1 desconecta'},
    'Adversaire': {'en': 'Opponent', 'de': 'Gegner', 'es': 'Rival', 'it': 'Avversario', 'zh': '对手', 'ja': '相手', 'ko': '상대', 'ru': 'Соперник', 'pt': 'Adversário'},
    "L'adversaire": {'en': 'The opponent', 'de': 'Der Gegner', 'es': 'El rival', 'it': "L'avversario", 'zh': '对手', 'ja': '相手', 'ko': '상대', 'ru': 'Соперник', 'pt': 'O adversário'},
    "{name} confirme abandonner. L'adversaire marquera 2 points.": {'en': '{name} confirms resignation. The opponent will score 2 points.', 'de': '{name} bestätigt die Aufgabe. Der Gegner erhält 2 Punkte.', 'es': '{name} confirma el abandono. El rival ganará 2 puntos.', 'it': "{name} conferma l'abbandono. L'avversario otterrà 2 punti.", 'zh': '{name} 确认认输。对手将得 2 分。', 'ja': '{name} が投了を確定しました。相手が2点を獲得します。', 'ko': '{name} 님이 기권을 확정했습니다. 상대가 2점을 얻습니다.', 'ru': '{name} подтверждает сдачу. Соперник получит 2 очка.', 'pt': '{name} confirma a desistência. O adversário ganhará 2 pontos.'},
})


TRANSLATIONS.update({
    'Voir': {'en': 'Show', 'de': 'Zeigen', 'es': 'Ver', 'it': 'Vedi', 'zh': '显示', 'ja': '表示', 'ko': '표시', 'ru': 'Показать', 'pt': 'Ver'},
    'Cacher': {'en': 'Hide', 'de': 'Verbergen', 'es': 'Ocultar', 'it': 'Nascondi', 'zh': '隐藏', 'ja': '非表示', 'ko': '숨기기', 'ru': 'Скрыть', 'pt': 'Ocultar'},
})


TRANSLATIONS.update({
    "L'appli n'envoie pas de notifications. Renseignez votre adresse mail pour savoir quand c'est à vous de jouer.": {'en': "The app doesn't send notifications. Enter your email address to know when it's your turn to play.", 'de': 'Die App sendet keine Benachrichtigungen. Gib deine E-Mail-Adresse ein, um zu erfahren, wann du am Zug bist.', 'es': 'La app no envía notificaciones. Introduce tu correo para saber cuándo es tu turno.', 'it': "L'app non invia notifiche. Inserisci la tua email per sapere quando tocca a te.", 'zh': '本应用不发送通知。填写你的邮箱以便知道何时轮到你走子。', 'ja': 'このアプリは通知を送りません。あなたの手番になったら分かるよう、メールアドレスを入力してください。', 'ko': '이 앱은 알림을 보내지 않습니다. 당신 차례를 알 수 있도록 이메일 주소를 입력하세요.', 'ru': 'Приложение не отправляет уведомления. Укажите адрес эл. почты, чтобы узнавать, когда ваш ход.', 'pt': 'O app não envia notificações. Informe seu e-mail para saber quando é a sua vez.'},
})


TRANSLATIONS.update({
    "Renseigner ou changer l'adresse mail": {'en': 'Set or change email address', 'de': 'E-Mail-Adresse eingeben oder ändern', 'es': 'Indicar o cambiar el correo', 'it': "Inserire o cambiare l'email", 'zh': '填写或更改邮箱地址', 'ja': 'メールアドレスを入力・変更', 'ko': '이메일 주소 입력 또는 변경', 'ru': 'Указать или изменить эл. почту', 'pt': 'Informar ou alterar o e-mail'},
    'Recevoir des mails (aucune notification push)': {'en': 'Receive emails (no push notifications)', 'de': 'E-Mails erhalten (keine Push-Benachrichtigungen)', 'es': 'Recibir correos (sin notificaciones push)', 'it': 'Ricevere email (nessuna notifica push)', 'zh': '接收邮件（无推送通知）', 'ja': 'メールを受け取る（プッシュ通知なし）', 'ko': '이메일 받기 (푸시 알림 없음)', 'ru': 'Получать письма (без push-уведомлений)', 'pt': 'Receber e-mails (sem notificações push)'},
    "quand c'est à moi de jouer (corresp.)": {'en': "when it's my turn (corresp.)", 'de': 'wenn ich am Zug bin (Fernp.)', 'es': 'cuando es mi turno (corresp.)', 'it': 'quando tocca a me (corrisp.)', 'zh': '轮到我走子时（通信）', 'ja': '自分の手番のとき（通信）', 'ko': '내 차례일 때 (통신)', 'ru': 'когда мой ход (переписка)', 'pt': 'quando é a minha vez (corresp.)'},
    'quand je reçois un message (corresp.)': {'en': 'when I get a message (corresp.)', 'de': 'wenn ich eine Nachricht erhalte (Fernp.)', 'es': 'cuando recibo un mensaje (corresp.)', 'it': 'quando ricevo un messaggio (corrisp.)', 'zh': '收到消息时（通信）', 'ja': 'メッセージを受け取ったとき（通信）', 'ko': '메시지를 받을 때 (통신)', 'ru': 'когда приходит сообщение (переписка)', 'pt': 'quando recebo uma mensagem (corresp.)'},
    "quand quelqu'un me défie (corresp.)": {'en': 'when someone challenges me (corresp.)', 'de': 'wenn mich jemand herausfordert (Fernp.)', 'es': 'cuando alguien me desafía (corresp.)', 'it': 'quando qualcuno mi sfida (corrisp.)', 'zh': '有人向我挑战时（通信）', 'ja': '誰かが挑戦してきたとき（通信）', 'ko': '누군가 도전할 때 (통신)', 'ru': 'когда мне бросают вызов (переписка)', 'pt': 'quando alguém me desafia (corresp.)'},
    "quand quelqu'un me défie (en direct)": {'en': 'when someone challenges me (live)', 'de': 'wenn mich jemand herausfordert (live)', 'es': 'cuando alguien me desafía (en directo)', 'it': 'quando qualcuno mi sfida (in diretta)', 'zh': '有人实时向我挑战时', 'ja': '誰かがリアルタイムで挑戦してきたとき', 'ko': '누군가 실시간으로 도전할 때', 'ru': 'когда мне бросают вызов (в реальном времени)', 'pt': 'quando alguém me desafia (ao vivo)'},
    'Personnes qui me suivent': {'en': 'People who follow me', 'de': 'Personen, die mir folgen', 'es': 'Personas que me siguen', 'it': 'Persone che mi seguono', 'zh': '关注我的人', 'ja': '自分をフォローしている人', 'ko': '나를 팔로우하는 사람', 'ru': 'Кто на меня подписан', 'pt': 'Pessoas que me seguem'},
    'Personne ne vous suit encore.': {'en': 'No one follows you yet.', 'de': 'Dir folgt noch niemand.', 'es': 'Todavía no te sigue nadie.', 'it': 'Ancora nessuno ti segue.', 'zh': '还没有人关注你。', 'ja': 'まだ誰もあなたをフォローしていません。', 'ko': '아직 아무도 팔로우하지 않습니다.', 'ru': 'На вас пока никто не подписан.', 'pt': 'Ninguém segue você ainda.'},
    'Aucune adresse mail': {'en': 'No email address', 'de': 'Keine E-Mail-Adresse', 'es': 'Sin correo electrónico', 'it': 'Nessuna email', 'zh': '无邮箱地址', 'ja': 'メールアドレスなし', 'ko': '이메일 주소 없음', 'ru': 'Нет адреса эл. почты', 'pt': 'Sem e-mail'},
    'Chargement…': {'en': 'Loading…', 'de': 'Wird geladen…', 'es': 'Cargando…', 'it': 'Caricamento…', 'zh': '加载中…', 'ja': '読み込み中…', 'ko': '불러오는 중…', 'ru': 'Загрузка…', 'pt': 'Carregando…'},
    'Nouvelle adresse mail': {'en': 'New email address', 'de': 'Neue E-Mail-Adresse', 'es': 'Nuevo correo electrónico', 'it': 'Nuova email', 'zh': '新邮箱地址', 'ja': '新しいメールアドレス', 'ko': '새 이메일 주소', 'ru': 'Новый адрес эл. почты', 'pt': 'Novo e-mail'},
    'Adresse mail': {'en': 'Email address', 'de': 'E-Mail-Adresse', 'es': 'Correo electrónico', 'it': 'Email', 'zh': '邮箱地址', 'ja': 'メールアドレス', 'ko': '이메일 주소', 'ru': 'Адрес эл. почты', 'pt': 'E-mail'},
})


TRANSLATIONS.update({
    'Menu': {'en': 'Menu', 'de': 'Menü', 'es': 'Menú', 'it': 'Menu', 'zh': '菜单', 'ja': 'メニュー', 'ko': '메뉴', 'ru': 'Меню', 'pt': 'Menu'},
})


TRANSLATIONS.update({
    'Standard : %d': {'en': 'Standard: %d', 'de': 'Standard: %d', 'es': 'Estándar: %d', 'it': 'Standard: %d', 'zh': '标准：%d', 'ja': '標準：%d', 'ko': '표준: %d', 'ru': 'Стандарт: %d', 'pt': 'Padrão: %d'},
    'Random : %d': {'en': 'Random: %d', 'de': 'Random: %d', 'es': 'Random: %d', 'it': 'Random: %d', 'zh': 'Random：%d', 'ja': 'Random：%d', 'ko': 'Random: %d', 'ru': 'Random: %d', 'pt': 'Random: %d'},
})


TRANSLATIONS.update({
    'Bloquer': {'en': 'Block', 'de': 'Blockieren', 'es': 'Bloquear', 'it': 'Blocca', 'zh': '屏蔽', 'ja': 'ブロック', 'ko': '차단', 'ru': 'Заблокировать', 'pt': 'Bloquear'},
    'Débloquer': {'en': 'Unblock', 'de': 'Freigeben', 'es': 'Desbloquear', 'it': 'Sblocca', 'zh': '取消屏蔽', 'ja': 'ブロック解除', 'ko': '차단 해제', 'ru': 'Разблокировать', 'pt': 'Desbloquear'},
    'Blocage': {'en': 'Blocking', 'de': 'Blockierung', 'es': 'Bloqueo', 'it': 'Blocco', 'zh': '屏蔽', 'ja': 'ブロック', 'ko': '차단', 'ru': 'Блокировка', 'pt': 'Bloqueio'},
    '%s débloqué.': {'en': '%s unblocked.', 'de': '%s freigegeben.', 'es': '%s desbloqueado.', 'it': '%s sbloccato.', 'zh': '已取消屏蔽 %s。', 'ja': '%s のブロックを解除しました。', 'ko': '%s 차단을 해제했습니다.', 'ru': '%s разблокирован.', 'pt': '%s desbloqueado.'},
    '%s bloqué. Vous ne pourrez plus vous croiser ni vous défier.': {'en': '%s blocked. You can no longer be matched or challenge each other.', 'de': '%s blockiert. Ihr könnt euch nicht mehr begegnen oder herausfordern.', 'es': '%s bloqueado. Ya no podréis cruzaros ni desafiaros.', 'it': '%s bloccato. Non potrete più incontrarvi né sfidarvi.', 'zh': '已屏蔽 %s。你们将不再匹配到对方，也无法互相挑战。', 'ja': '%s をブロックしました。今後マッチングも対戦の申し込みもできなくなります。', 'ko': '%s 님을 차단했습니다. 더 이상 매칭되거나 서로 도전할 수 없습니다.', 'ru': '%s заблокирован. Вы больше не встретитесь и не сможете бросить вызов друг другу.', 'pt': '%s bloqueado. Vocês não poderão mais se cruzar nem se desafiar.'},
    'Défi impossible : un blocage est en place entre vous.': {'en': 'Challenge impossible: a block is in place between you.', 'de': 'Herausforderung nicht möglich: Es besteht eine Blockierung zwischen euch.', 'es': 'Desafío imposible: hay un bloqueo entre vosotros.', 'it': "Sfida impossibile: c'è un blocco tra voi.", 'zh': '无法挑战：你们之间存在屏蔽。', 'ja': '対戦を申し込めません：お互いの間にブロックがあります。', 'ko': '도전할 수 없습니다: 서로 간에 차단이 설정되어 있습니다.', 'ru': 'Вызов невозможен: между вами установлена блокировка.', 'pt': 'Desafio impossível: há um bloqueio entre vocês.'},
})


TRANSLATIONS.update({
    '(Aucune description)': {'en': '(No description)', 'de': '(Keine Beschreibung)', 'es': '(Sin descripción)', 'it': '(Nessuna descrizione)', 'zh': '（暂无简介）', 'ja': '（説明なし）', 'ko': '(설명 없음)', 'ru': '(Нет описания)', 'pt': '(Sem descrição)'},
    'Changer la photo': {'en': 'Change photo', 'de': 'Foto ändern', 'es': 'Cambiar foto', 'it': 'Cambia foto', 'zh': '更换头像', 'ja': '写真を変更', 'ko': '사진 변경', 'ru': 'Сменить фото', 'pt': 'Alterar foto'},
    'Modifier la description': {'en': 'Edit description', 'de': 'Beschreibung bearbeiten', 'es': 'Editar descripción', 'it': 'Modifica descrizione', 'zh': '编辑简介', 'ja': '説明を編集', 'ko': '설명 편집', 'ru': 'Изменить описание', 'pt': 'Editar descrição'},
    'Description': {'en': 'Description', 'de': 'Beschreibung', 'es': 'Descripción', 'it': 'Descrizione', 'zh': '简介', 'ja': '説明', 'ko': '설명', 'ru': 'Описание', 'pt': 'Descrição'},
    'Le suivent': {'en': 'Followers', 'de': 'Follower', 'es': 'Seguidores', 'it': 'Follower', 'zh': '关注者', 'ja': 'フォロワー', 'ko': '팔로워', 'ru': 'Подписчики', 'pt': 'Seguidores'},
    'Il suit': {'en': 'Following', 'de': 'Folgt', 'es': 'Siguiendo', 'it': 'Segue', 'zh': '正在关注', 'ja': 'フォロー中', 'ko': '팔로잉', 'ru': 'Подписки', 'pt': 'Seguindo'},
    'Personnes que je suis': {'en': 'People I follow', 'de': 'Personen, denen ich folge', 'es': 'Personas que sigo', 'it': 'Persone che seguo', 'zh': '我关注的人', 'ja': '自分がフォローしている人', 'ko': '내가 팔로우하는 사람', 'ru': 'На кого я подписан', 'pt': 'Pessoas que sigo'},
    'Personne ne le suit encore.': {'en': 'No one follows them yet.', 'de': 'Ihm folgt noch niemand.', 'es': 'Todavía no lo sigue nadie.', 'it': 'Ancora nessuno lo segue.', 'zh': '还没有人关注他。', 'ja': 'まだ誰もフォローしていません。', 'ko': '아직 아무도 팔로우하지 않습니다.', 'ru': 'На него пока никто не подписан.', 'pt': 'Ninguém o segue ainda.'},
    'Ne suit personne.': {'en': 'Not following anyone.', 'de': 'Folgt niemandem.', 'es': 'No sigue a nadie.', 'it': 'Non segue nessuno.', 'zh': '没有关注任何人。', 'ja': '誰もフォローしていません。', 'ko': '아무도 팔로우하지 않습니다.', 'ru': 'Ни на кого не подписан.', 'pt': 'Não segue ninguém.'},
    'Joueurs bloqués': {'en': 'Blocked players', 'de': 'Blockierte Spieler', 'es': 'Jugadores bloqueados', 'it': 'Giocatori bloccati', 'zh': '已屏蔽的玩家', 'ja': 'ブロックした人', 'ko': '차단한 플레이어', 'ru': 'Заблокированные игроки', 'pt': 'Jogadores bloqueados'},
    'Aucun joueur bloqué.': {'en': 'No blocked players.', 'de': 'Keine blockierten Spieler.', 'es': 'Ningún jugador bloqueado.', 'it': 'Nessun giocatore bloccato.', 'zh': '没有屏蔽任何玩家。', 'ja': 'ブロックした人はいません。', 'ko': '차단한 플레이어가 없습니다.', 'ru': 'Нет заблокированных игроков.', 'pt': 'Nenhum jogador bloqueado.'},
    'Historique local': {'en': 'Local history', 'de': 'Lokaler Verlauf', 'es': 'Historial local', 'it': 'Cronologia locale', 'zh': '本地历史', 'ja': 'ローカル履歴', 'ko': '로컬 기록', 'ru': 'Локальная история', 'pt': 'Histórico local'},
    'Profil indisponible.': {'en': 'Profile unavailable.', 'de': 'Profil nicht verfügbar.', 'es': 'Perfil no disponible.', 'it': 'Profilo non disponibile.', 'zh': '资料不可用。', 'ja': 'プロフィールを表示できません。', 'ko': '프로필을 불러올 수 없습니다.', 'ru': 'Профиль недоступен.', 'pt': 'Perfil indisponível.'},
    'Écris ta description…': {'en': 'Write your description…', 'de': 'Schreibe deine Beschreibung…', 'es': 'Escribe tu descripción…', 'it': 'Scrivi la tua descrizione…', 'zh': '写下你的简介…', 'ja': '説明を書いてください…', 'ko': '설명을 작성하세요…', 'ru': 'Напишите описание…', 'pt': 'Escreva sua descrição…'},
    'Choisir cette photo': {'en': 'Choose this photo', 'de': 'Dieses Foto wählen', 'es': 'Elegir esta foto', 'it': 'Scegli questa foto', 'zh': '选择此头像', 'ja': 'この写真にする', 'ko': '이 사진 선택', 'ru': 'Выбрать это фото', 'pt': 'Escolher esta foto'},
    'Photo de profil': {'en': 'Profile photo', 'de': 'Profilfoto', 'es': 'Foto de perfil', 'it': 'Foto del profilo', 'zh': '头像', 'ja': 'プロフィール写真', 'ko': '프로필 사진', 'ru': 'Фото профиля', 'pt': 'Foto de perfil'},
    'Pièce': {'en': 'Piece', 'de': 'Figur', 'es': 'Pieza', 'it': 'Pezzo', 'zh': '棋子', 'ja': '駒', 'ko': '말', 'ru': 'Фигура', 'pt': 'Peça'},
})


TRANSLATIONS.update({
    'Profil': {'en': 'Profile', 'de': 'Profil', 'es': 'Perfil', 'it': 'Profilo', 'zh': '资料', 'ja': 'プロフィール', 'ko': '프로필', 'ru': 'Профиль', 'pt': 'Perfil'},
    'Favori': {'en': 'Favorite', 'de': 'Favorit', 'es': 'Favorito', 'it': 'Preferito', 'zh': '收藏', 'ja': 'お気に入り', 'ko': '즐겨찾기', 'ru': 'Избранное', 'pt': 'Favorito'},
    'Message': {'en': 'Message', 'de': 'Nachricht', 'es': 'Mensaje', 'it': 'Messaggio', 'zh': '消息', 'ja': 'メッセージ', 'ko': '메시지', 'ru': 'Сообщение', 'pt': 'Mensagem'},
    'Messages': {'en': 'Messages', 'de': 'Nachrichten', 'es': 'Mensajes', 'it': 'Messaggi', 'zh': '消息', 'ja': 'メッセージ', 'ko': '메시지', 'ru': 'Сообщения', 'pt': 'Mensagens'},
    '%s ajouté aux favoris.': {'en': '%s added to favorites.', 'de': '%s zu Favoriten hinzugefügt.', 'es': '%s añadido a favoritos.', 'it': '%s aggiunto ai preferiti.', 'zh': '已将 %s 加入收藏。', 'ja': '%s をお気に入りに追加しました。', 'ko': '%s 님을 즐겨찾기에 추가했습니다.', 'ru': '%s добавлен в избранное.', 'pt': '%s adicionado aos favoritos.'},
    '%s bloqué. La partie en cours continue ; le blocage prendra effet à la fin.': {'en': '%s blocked. The current game continues; the block takes effect when it ends.', 'de': '%s blockiert. Die laufende Partie geht weiter; die Blockierung wirkt am Ende.', 'es': '%s bloqueado. La partida actual continúa; el bloqueo se aplica al terminar.', 'it': '%s bloccato. La partita in corso continua; il blocco avrà effetto alla fine.', 'zh': '已屏蔽 %s。当前对局继续；屏蔽将在结束后生效。', 'ja': '%s をブロックしました。進行中の対局は続行され、ブロックは終了後に有効になります。', 'ko': '%s 님을 차단했습니다. 진행 중인 대국은 계속되며 차단은 종료 후 적용됩니다.', 'ru': '%s заблокирован. Текущая партия продолжается; блокировка вступит в силу после её окончания.', 'pt': '%s bloqueado. A partida atual continua; o bloqueio terá efeito ao terminar.'},
    'La messagerie avec %s arrive très bientôt.': {'en': 'Messaging with %s is coming very soon.', 'de': 'Nachrichten mit %s kommen sehr bald.', 'es': 'La mensajería con %s llegará muy pronto.', 'it': 'La messaggistica con %s arriva molto presto.', 'zh': '与 %s 的消息功能即将推出。', 'ja': '%s とのメッセージ機能はまもなく登場します。', 'ko': '%s 님과의 메시지 기능이 곧 제공됩니다.', 'ru': 'Переписка с %s появится совсем скоро.', 'pt': 'As mensagens com %s chegam muito em breve.'},
})


TRANSLATIONS.update({
    '< Retour': {'en': '< Back', 'de': '< Zurück', 'es': '< Volver', 'it': '< Indietro', 'zh': '< 返回', 'ja': '< 戻る', 'ko': '< 뒤로', 'ru': '< Назад', 'pt': '< Voltar'},
    'Conversation indisponible.': {'en': 'Conversation unavailable.', 'de': 'Unterhaltung nicht verfügbar.', 'es': 'Conversación no disponible.', 'it': 'Conversazione non disponibile.', 'zh': '对话不可用。', 'ja': '会話を表示できません。', 'ko': '대화를 불러올 수 없습니다.', 'ru': 'Переписка недоступна.', 'pt': 'Conversa indisponível.'},
    'Aucun message. Écrivez le premier !': {'en': 'No messages. Write the first one!', 'de': 'Keine Nachrichten. Schreib die erste!', 'es': 'Sin mensajes. ¡Escribe el primero!', 'it': 'Nessun messaggio. Scrivi il primo!', 'zh': '还没有消息。发第一条吧！', 'ja': 'メッセージはありません。最初の一通を書きましょう！', 'ko': '메시지가 없습니다. 첫 메시지를 보내보세요!', 'ru': 'Сообщений нет. Напишите первое!', 'pt': 'Sem mensagens. Escreva a primeira!'},
    '(non envoyé : %s)': {'en': '(not sent: %s)', 'de': '(nicht gesendet: %s)', 'es': '(no enviado: %s)', 'it': '(non inviato: %s)', 'zh': '（未发送：%s）', 'ja': '（未送信：%s）', 'ko': '(전송 안 됨: %s)', 'ru': '(не отправлено: %s)', 'pt': '(não enviado: %s)'},
})


TRANSLATIONS.update({
    'Vous : ': {'en': 'You: ', 'de': 'Du: ', 'es': 'Tú: ', 'it': 'Tu: ', 'zh': '你：', 'ja': 'あなた：', 'ko': '나: ', 'ru': 'Вы: ', 'pt': 'Você: '},
    'Aucune conversation pour le moment.': {'en': 'No conversations yet.', 'de': 'Noch keine Unterhaltungen.', 'es': 'Aún no hay conversaciones.', 'it': 'Ancora nessuna conversazione.', 'zh': '暂无对话。', 'ja': 'まだ会話はありません。', 'ko': '아직 대화가 없습니다.', 'ru': 'Пока нет переписок.', 'pt': 'Ainda não há conversas.'},
    'Messagerie indisponible.': {'en': 'Messaging unavailable.', 'de': 'Nachrichten nicht verfügbar.', 'es': 'Mensajería no disponible.', 'it': 'Messaggistica non disponibile.', 'zh': '消息功能不可用。', 'ja': 'メッセージを利用できません。', 'ko': '메시지를 사용할 수 없습니다.', 'ru': 'Переписка недоступна.', 'pt': 'Mensagens indisponíveis.'},
})


TRANSLATIONS.update({
    'Composer le thème': {'en': 'Compose theme', 'de': 'Thema gestalten', 'es': 'Componer tema', 'it': 'Comporre tema', 'zh': '自定义主题', 'ja': 'テーマを作成', 'ko': '테마 구성', 'ru': 'Собрать тему', 'pt': 'Compor tema'},
    'Général': {'en': 'General', 'de': 'Allgemein', 'es': 'General', 'it': 'Generale', 'zh': '通用', 'ja': '全般', 'ko': '일반', 'ru': 'Общее', 'pt': 'Geral'},
    'Pièces': {'en': 'Pieces', 'de': 'Figuren', 'es': 'Piezas', 'it': 'Pezzi', 'zh': '棋子', 'ja': '駒', 'ko': '말', 'ru': 'Фигуры', 'pt': 'Peças'},
    'Logo': {'en': 'Logo', 'de': 'Logo', 'es': 'Logo', 'it': 'Logo', 'zh': '标志', 'ja': 'ロゴ', 'ko': '로고', 'ru': 'Логотип', 'pt': 'Logo'},
    'Fond du menu': {'en': 'Menu background', 'de': 'Menü-Hintergrund', 'es': 'Fondo del menú', 'it': 'Sfondo menu', 'zh': '菜单背景', 'ja': 'メニュー背景', 'ko': '메뉴 배경', 'ru': 'Фон меню', 'pt': 'Fundo do menu'},
    'Plateau': {'en': 'Board', 'de': 'Brett', 'es': 'Tablero', 'it': 'Scacchiera', 'zh': '棋盘', 'ja': 'ボード', 'ko': '보드', 'ru': 'Доска', 'pt': 'Tabuleiro'},
})


def T(s):
    """Renvoie la traduction de la chaîne française `s` dans la langue courante.
    Repli sur le français si la traduction n'existe pas."""
    if LANG == "fr" or not s:
        return s
    entry = TRANSLATIONS.get(s)
    if not entry:
        return s
    return entry.get(LANG, s)


def set_language(code):
    """Change la langue courante et l'enregistre dans la config."""
    global LANG
    if code in LANG_LABELS:
        LANG = code
        try:
            save_config(lang=code)
        except Exception:
            pass


# ── Composition de thème : 5 axes indépendants ──────────────────────────────
# Chaque axe désigne « prends l'aspect X du thème Y ». L'ensemble est stocké en
# un seul texte composite "general|pieces|logo|menu|board" (rétro-compatible :
# un ancien nom de thème seul => les 5 axes identiques).
THEME_GENERAL = "original"   # couleurs des touches / bandeaux / accents / grille
THEME_PIECES  = "original"   # rendu des pièces (couleurs + formes)
THEME_LOGO    = "original"   # logo du menu
THEME_MENU_BG = "original"   # fond du menu
THEME_BOARD   = "original"   # plateau


def _valid_theme(name):
    return name if name in THEMES else "original"


def parse_theme_components(s):
    """'general|pieces|logo|menu|board' -> (general, pieces, logo, menu, board).
    Accepte l'ancien format (un seul nom de thème -> les 5 axes identiques)."""
    s = (s or "original").strip()
    if "|" in s:
        parts = (s.split("|") + ["original"] * 5)[:5]
        return tuple(_valid_theme(p) for p in parts)
    one = _valid_theme(s)
    return (one, one, one, one, one)


def theme_components_to_str(general, pieces, logo, menu, board):
    return "|".join([general, pieces, logo, menu, board])


def current_theme_str():
    """Le texte composite courant (à enregistrer localement / sur le serveur)."""
    return theme_components_to_str(THEME_GENERAL, THEME_PIECES, THEME_LOGO,
                                   THEME_MENU_BG, THEME_BOARD)


def apply_composite_theme(general, pieces, logo, menu, board):
    """Applique les 5 axes. Les couleurs d'INTERFACE (touches, bandeaux, accents,
    grille) viennent de 'general' ; le fond du menu de 'menu' ; le plateau de
    'board'. Les pièces (axe 'pieces') et le logo (axe 'logo') sont gérés au
    rendu via THEME_PIECES / THEME_LOGO."""
    global CURRENT_THEME
    global THEME_GENERAL, THEME_PIECES, THEME_LOGO, THEME_MENU_BG, THEME_BOARD
    global COL_BG_MENU, COL_MENU_BG, COL_BG_BOARD, COL_GRID
    global COL_ORANGE, COL_BLUE, COL_ORANGE_DIM, COL_BLUE_DIM
    THEME_GENERAL = _valid_theme(general)
    THEME_PIECES  = _valid_theme(pieces)
    THEME_LOGO    = _valid_theme(logo)
    THEME_MENU_BG = _valid_theme(menu)
    THEME_BOARD   = _valid_theme(board)
    CURRENT_THEME = THEME_GENERAL      # compat : CURRENT_THEME suit le « général »
    tg = THEMES[THEME_GENERAL]
    COL_ORANGE     = tg["clair"]
    COL_BLUE       = tg["fonce"]
    COL_ORANGE_DIM = tg["clair_dim"]
    COL_BLUE_DIM   = tg["fonce_dim"]
    COL_GRID       = tg["grid"]
    COL_BG_MENU    = tg["menu"]                    # bandeaux + écrans secondaires
    COL_MENU_BG    = THEMES[THEME_MENU_BG]["menu"]  # fond du menu (axe dédié)
    COL_BG_BOARD   = THEMES[THEME_BOARD]["board"]   # couleur plateau (si pas d'image)


def apply_theme(name):
    """Compat : applique un thème unique sur les 5 axes (ancien comportement)."""
    if "|" in (name or ""):
        apply_composite_theme(*parse_theme_components(name))
    else:
        n = _valid_theme(name)
        apply_composite_theme(n, n, n, n, n)


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


def _reconcile_theme(server_theme):
    """Concilie le thème renvoyé par le serveur avec la config LOCALE.

    Le serveur tronque le thème stocké (historiquement à 40 caractères), ce qui
    casse les thèmes COMPOSITES ('general|pieces|logo|menu|board') un peu longs.
    Si le thème local est un composite dont la version tronquée correspond
    exactement au thème serveur, c'est que le serveur n'a que la version coupée :
    on garde alors le thème LOCAL complet. Sinon on prend le thème serveur (ex.
    thème choisi depuis un autre appareil)."""
    try:
        local = (load_config().get("theme", "original") or "").strip()
        srv = (server_theme or "").strip()
        if "|" in local:
            for cut in (40, 100, len(local)):
                if srv == local[:cut]:
                    return local
    except Exception:
        pass
    return server_theme or "original"


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
        f"[Date \"{meta['date']}\"]\n" +
        f"[Joueur1 \"{meta['player1']}\"]\n" +
        f"[Joueur2 \"{meta['player2']}\"]\n" +
        f"[Blanc \"{meta.get('blanc', meta['player1'])}\"]\n" +
        f"[Objectif \"{meta['objectif']}\"]\n" +
        f"[Cadence \"{meta['cadence']}\"]\n" +
        f"[Resultat \"{meta['result']}\"]\n" +
        f"[Methode \"{meta['method']}\"]\n" +
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

# Thèmes ayant SEULEMENT des images de FOND (menu + plateau), mais des pièces
# dessinées normalement (ex. deepgrey). Séparé de _THEME_IMG_DIR pour NE PAS
# déclencher le chargement d'images de pièces.
_THEME_BG_DIR = {"deepgrey": "theme_deepgrey"}


def _theme_image_dir(theme=None):
    """Renvoie le nom du dossier d'images du thème (ou None si le thème n'a pas
    d'images personnalisées)."""
    if theme is None:
        theme = CURRENT_THEME
    return _THEME_IMG_DIR.get(theme)


def _theme_bg_dir(theme=None):
    """Dossier des IMAGES DE FOND (menu/plateau) d'un thème : thèmes à images
    complètes (pièces+fonds) ET thèmes à fonds seuls (deepgrey)."""
    if theme is None:
        theme = CURRENT_THEME
    return _THEME_BG_DIR.get(theme) or _THEME_IMG_DIR.get(theme)


def _theme_bg_texture(fname, theme=None):
    """Renvoie la texture d'un fond (fond.png / plateau.png) du thème à images
    ou à fonds, ou None si absent. Mise en cache (clé incluant le dossier)."""
    folder = _theme_bg_dir(theme)
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


def _fit_cover_rect(tex, screen_w, screen_h):
    """Ajuste l'image pour COUVRIR tout l'écran (remplit entièrement, quitte à
    rogner les bords) — utile sur les téléphones longs."""
    tw, th = tex.width, tex.height
    if tw <= 0 or th <= 0:
        return (0, 0), (screen_w, screen_h)
    scale = max(screen_w / float(tw), screen_h / float(th))
    w, h = tw * scale, th * scale
    x = (screen_w - w) / 2.0
    y = (screen_h - h) / 2.0
    return (x, y), (w, h)


def _fit_menu_bg(tex, screen_w, screen_h):
    """Choisit l'ajustement du fond menu selon le thème : insectes cale sur la
    hauteur, deepgrey COUVRE tout l'écran (remplit), les autres calent sur la
    largeur."""
    if THEME_MENU_BG == "insectes":
        return _fit_height_rect(tex, screen_w, screen_h)
    if THEME_MENU_BG == "deepgrey":
        return _fit_cover_rect(tex, screen_w, screen_h)
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
    img_theme = preview_theme if preview_theme else THEME_PIECES
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
    # Couleur d'accent de la pièce : issue du thème PIÈCES (ou du thème d'aperçu),
    # indépendamment des couleurs générales.
    _render_theme = preview_theme if preview_theme else THEME_PIECES
    if _render_theme == "arcenciel" and rainbow_frac is not None:
        acc = _rainbow_color(rainbow_frac, piece["camp"])
    else:
        _pt = THEMES.get(_render_theme, THEMES["original"])
        acc = _pt["clair"] if piece["camp"] == "Blanc" else _pt["fonce"]
    if outline is None:
        outline = (0.87, 0.87, 0.87, 1) if piece["camp"] == "Blanc" else (0.2, 0.2, 0.33, 1)
    sw  = max(2, inner * 0.10)
    t   = piece["type"]

    # ── Thème deepgrey : corps GRIS (0.5) pour toutes les pièces, détails en
    #    BLANC (pièces blanches) ou NOIR (pièces noires). L'héritier est un
    #    dégradé (voir plus bas). ──
    is_deepgrey = (_render_theme == "deepgrey")
    if is_deepgrey:
        _GREY_MID = (0.5, 0.5, 0.5, 1)
        _detail = (1, 1, 1, 1) if piece["camp"] == "Blanc" else (0, 0, 0, 1)
        bg = _GREY_MID
        acc = _detail
        # Trait par défaut = couleur de la pièce, MAIS on garde un cadre déjà
        # fourni (sélection jaune/rose, immobilisation rouge).
        if outline is None:
            outline = _detail

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
                if is_deepgrey:
                    # Héritier deepgrey : GROS cœur plein (blanc = lumière / noir
                    # = trou) qui se fond vers le gris sur le bord extérieur.
                    _gm = (0.5, 0.5, 0.5, 1)
                    _dc = (1, 1, 1, 1) if piece["camp"] == "Blanc" else (0, 0, 0, 1)
                    steps = 12    # dégradé (12 = quasi identique à 22, 2x plus léger)
                    for i in range(steps):
                        frac = i / float(steps - 1)          # 0 (bord) -> 1 (centre)
                        r = (inner / 2.0) * (1.0 - frac * 0.90)
                        # cœur plein detail dès ~55 % du rayon, dégradé au-delà
                        tt = min(1.0, frac / 0.55)
                        col = tuple(g + (d - g) * tt for g, d in zip(_gm, _dc))
                        Color(*col)
                        Ellipse(pos=(cx - r, cy - r), size=(r * 2, r * 2))
                    Color(*outline); Line(circle=(cx, cy, inner / 2), width=outline_w)
                else:
                    d  = inner * 0.20
                    r2 = inner * 0.14
                    Color(*acc);             Ellipse(pos=(px + d, py + d), size=(inner - 2*d, inner - 2*d))
                    # "Trou" : on peint le centre avec la couleur du plateau → illusion de transparence
                    Color(*COL_BG_BOARD);    Ellipse(pos=(cx - r2, cy - r2), size=(r2*2, r2*2))
            elif is_deepgrey:
                # Nurse deepgrey : cercle gris + centre coloré (blanc/noir)
                rc = inner * 0.24
                Color(*acc)
                Ellipse(pos=(cx - rc, cy - rc), size=(rc * 2, rc * 2))

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
            # deepgrey : hexagone GRIS + centre hexagonal coloré ; sinon coloré.
            Color(*(bg if is_deepgrey else acc))
            Mesh(vertices=mesh_verts, indices=indices, mode="triangles")
            Color(*outline)
            Line(points=pts + [pts[0], pts[1]], width=outline_w)
            if is_deepgrey:
                # Centre HEXAGONAL (même forme, réduit) dans la couleur de la pièce
                sc = 0.45
                cpts = []
                for i in range(0, len(pts), 2):
                    cpts.append(cx + (pts[i] - cx) * sc)
                    cpts.append(cy + (pts[i + 1] - cy) * sc)
                cverts = [cx, cy, 0, 0]
                for i in range(0, len(cpts), 2):
                    cverts.extend([cpts[i], cpts[i + 1], 0, 0])
                cindices = []
                for i in range(1, 6):
                    cindices.extend([0, i, i + 1])
                cindices.extend([0, 6, 1])
                Color(*acc)
                Mesh(vertices=cverts, indices=cindices, mode="triangles")


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
        back = RoundButton(text=T("< Menu"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(0.28, 0.05),
                           pos_hint={"x": 0.04, "top": 0.975})
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        root.add_widget(back)

        # Titre
        self.title_lbl = Label(text=T("Connexion"), font_size=SF("28sp"), bold=True,
                               italic=True, color=(0.05, 0.05, 0.05, 1),
                               size_hint=(1, 0.08),
                               pos_hint={"center_x": 0.5, "top": 0.90})
        root.add_widget(self.title_lbl)

        # Bouton toggle login/inscription
        self.toggle_btn = RoundButton(text=T("Pas encore inscrit ?"),
                                      font_size=SF("13sp"), bold=True,
                                      bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                                      size_hint=(0.5, 0.045),
                                      pos_hint={"center_x": 0.5, "top": 0.80})
        self.toggle_btn.bind(on_release=self._toggle_mode)
        root.add_widget(self.toggle_btn)

        # Champ pseudo
        self.pseudo_input = TextInput(text="", multiline=False,
                                      size_hint=(0.7, 0.06),
                                      hint_text=T("Pseudo"),
                                      font_size=SF("16sp"),
                                      pos_hint={"center_x": 0.5, "top": 0.70})
        root.add_widget(self.pseudo_input)

        # Champ mot de passe (+ bouton Afficher / Masquer)
        self.password_input = TextInput(text="", multiline=False, password=True,
                                        size_hint=(0.52, 0.06),
                                        hint_text=T("Mot de passe"),
                                        font_size=SF("16sp"),
                                        pos_hint={"center_x": 0.41, "top": 0.61})
        root.add_widget(self.password_input)
        self._pw_shown = False
        pw_toggle = RoundButton(text=T("Voir"), bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("10sp"),
                                bold=True, size_hint=(0.16, 0.06),
                                pos_hint={"center_x": 0.78, "top": 0.61})

        def _toggle_pw(*a):
            self._pw_shown = not self._pw_shown
            # password=True masque (points) ; False affiche en clair
            self.password_input.password = not self._pw_shown
            pw_toggle.text = T("Cacher") if self._pw_shown else T("Voir")
        pw_toggle.bind(on_release=_toggle_pw)
        root.add_widget(pw_toggle)

        # Champ email (visible seulement en mode register, optionnel)
        self.email_input = TextInput(text="", multiline=False,
                                     size_hint=(0.7, 0.06),
                                     hint_text=T("Email (optionnel)"),
                                     font_size=SF("16sp"),
                                     pos_hint={"center_x": 0.5, "top": 0.52})
        root.add_widget(self.email_input)
        self.email_input.opacity = 0
        self.email_input.disabled = True

        # Phrase d'explication sous le champ email (visible en inscription)
        self.email_hint_lbl = Label(
            text=T("L'appli n'envoie pas de notifications. Renseignez votre "
                   "adresse mail pour savoir quand c'est à vous de jouer."),
            font_size=SF("10sp"), color=(0.75, 0.75, 0.75, 1),
            halign="center", valign="middle",
            size_hint=(0.84, 0.08),
            pos_hint={"center_x": 0.5, "top": 0.475})
        self.email_hint_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        root.add_widget(self.email_hint_lbl)
        self.email_hint_lbl.opacity = 0

        # Bouton valider
        self.submit_btn = RoundButton(text=T("Se connecter"), font_size=SF("17sp"),
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
            self.title_lbl.text = T("Connexion")
            self.toggle_btn.text = T("Pas encore inscrit ?")
            self.submit_btn.text = T("Se connecter")
            self.email_input.opacity = 0
            self.email_input.disabled = True
            self.email_hint_lbl.opacity = 0
        else:
            self.title_lbl.text = T("Inscription")
            self.toggle_btn.text = T("J'ai déjà un compte")
            self.submit_btn.text = T("Créer le compte")
            self.email_input.opacity = 1
            self.email_input.disabled = False
            self.email_hint_lbl.opacity = 1
        self.status_lbl.text = ""

    def _submit(self, *a):
        pseudo = self.pseudo_input.text.strip()
        password = self.password_input.text
        email = self.email_input.text.strip()
        if not pseudo or not password:
            self.status_lbl.color = (0.7, 0.1, 0.1, 1)
            self.status_lbl.text = T("Pseudo et mot de passe requis")
            return
        self.submit_btn.disabled = True
        self.status_lbl.color = (0.2, 0.2, 0.5, 1)
        self.status_lbl.text = T("Connexion au serveur...")
        def on_done(success, msg):
            self.submit_btn.disabled = False
            if success:
                self.status_lbl.color = (0.1, 0.6, 0.1, 1)
                self.status_lbl.text = msg
                # Appliquer le thème enregistré sur le serveur (retrouvé même
                # depuis un autre appareil / une connexion précédente).
                try:
                    apply_theme(ONLINE.theme)
                    save_config(theme=ONLINE.theme)
                    refresh_all_screens(self.manager)
                except Exception:
                    pass
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
        self.prev_b = RoundButton(text=T("< Précédent"), font_size=SF("14sp"),
                                  bold=True, bg_color=COL_BTN_GREY,
                                  color=(1, 1, 1, 1))
        self.prev_b.bind(on_release=lambda *a: self._prev())
        self.next_b = RoundButton(text=T("Continuer >"), font_size=SF("14sp"),
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
             "text": ("Avant une partie, choisis un OBJECTIF (Partie = une seule ; " +
                      "3/5/7 = premier à ce nombre de points) et une CADENCE " +
                      "(minutes par joueur). En 3/5/7, si " +
                      "l'adversaire atteint le score alors que tu as joué une " +
                      "partie de MOINS que lui en Blanc, tu joues une ULTIME partie " +
                      "en Blanc pour égaliser les couleurs.")},
            {"targets": ["local", "online"], "scroll": "local",
             "text": ("Puis lance : « Jouer en local » (à deux sur le même " +
                      "appareil) ou « Jouer en ligne ». En ligne, le matchmaking " +
                      "te trouve un adversaire de ton niveau ; c'est le SEUL mode " +
                      "qui fait bouger ton MÉLO, ton classement (~1500 au départ), " +
                      "qui monte quand tu gagnes et baisse quand tu perds.")},
            {"targets": ["ai"], "scroll": "ai",
             "text": ("« deep grey » est l'intelligence artificielle du jeu : " +
                      "affronte-la pour t'entraîner quand tu veux.")},
            {"targets": ["search", "fav"], "scroll": "search",
             "text": ("Cherche un joueur par son nom pour le défier directement ; " +
                      "l'étoile gère tes favoris.")},
            {"targets": ["corr"], "scroll": "corr",
             "text": ("Fais glisser l'écran vers le BAS pour la CORRESPONDANCE : " +
                      "des parties sans limite de temps, contre des joueurs " +
                      "enregistrés. Pour en lancer une, clique sur un plateau " +
                      "vide, puis choisis ton adversaire parmi tes favoris.")},
            {"targets": ["compte"], "scroll": "obj",
             "text": ("« Compte » : crée ton compte ici. Il est OBLIGATOIRE pour " +
                      "jouer en ligne et en correspondance.")},
            {"targets": ["random"], "scroll": "obj",
             "text": ("« Random » active la variante Random Fuga : la position de " +
                      "départ est tirée au hasard parmi 1750 positions x 2 types " +
                      "de symétrie, soit 3500 débuts possibles. Il se réinitialise " +
                      "à chaque lancement.")},
            {"targets": ["plus"], "scroll": "plus",
             "text": ("« Plus » donne accès à ce tuto, à l'historique de tes " +
                      "parties, à l'analyse, aux réglages, et à SOUTENIR LES " +
                      "DÉVELOPPEURS (un petit don pour aider le jeu).")},
            {"targets": [], "scroll": "obj",
             "text": ("Et voilà, tu sais tout ! Le reste (thèmes, réglages, " +
                      "historique, analyse), tu le découvriras toi-même. " +
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
        self.text_lbl.text = T(stop["text"])
        last = (self.idx == len(self.stops) - 1)
        self.next_b.text = T("Bonne fugue !") if last else T("Continuer >")
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
            self._bg_col = Color(*COL_MENU_BG)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
            # Thème médiéval : fond image, largeur calée sur l'écran
            self._bg_stone_col = Color(1, 1, 1, 1)
            tex = _theme_bg_texture("fond.png", theme=THEME_MENU_BG) if _theme_bg_dir(THEME_MENU_BG) else None
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
            if THEME_MENU_BG == "fleur" and tex:
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

        # ── Logo ── (nocache : indispensable pour que le logo se rafraîchisse
        # vraiment au changement de thème ; sinon Kivy garde l'ancien en cache)
        self._logo_widget = Image(source=self._theme_logo_path(),
                                  size_hint=(1, None), height=Window.height * 0.13,
                                  allow_stretch=True, keep_ratio=True,
                                  nocache=True)
        self._logo_widget.bind(on_touch_down=self._on_logo_touch)
        col.add_widget(self._logo_widget)

        add_spacer(0.02)

        # ── Objectif ──
        col.add_widget(Label(text=T("Objectif"), font_size=SF("17sp"),
                             color=(0.15, 0.15, 0.15, 1), bold=True,
                             size_hint=(1, None), height=Window.height * 0.04))
        obj_row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                            height=Window.height * 0.05, spacing=S(6),
                            padding=(S(14), 0))
        self.pts_btns = {}
        for v in ["partie", 3, 5, 7]:
            if v == "partie":   label = T("Partie")
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
        col.add_widget(Label(text=T("Cadence (min / joueur)"), font_size=SF("17sp"),
                             color=(0.15, 0.15, 0.15, 1), bold=True,
                             size_hint=(1, None), height=Window.height * 0.04))
        cad_row = BoxLayout(orientation="horizontal", size_hint=(1, None),
                            height=Window.height * 0.05, spacing=S(6),
                            padding=(S(14), 0))
        self.cad_btns = {}
        for v in [5, 15, 30]:
            label = f"{v} min"
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

        self._btn_local = main_btn(T("Jouer en local"), COL_ORANGE, self._start_local)
        add_spacer(0.012)

        # ── Ligne T("Jouer en ligne") + recherche + favoris ──
        # Bouton T("Jouer en ligne") (matchmaking)
        self._btn_online = main_btn(T("Jouer en ligne"), COL_BLUE, self._on_play_online)
        add_spacer(0.012)

        # Barre de recherche de joueurs + bouton favoris
        search_row = BoxLayout(orientation="horizontal", size_hint=(0.7, None),
                               height=Window.height * 0.05, spacing=S(6),
                               pos_hint={"center_x": 0.5})
        self.search_input = TextInput(
            hint_text=T("Rechercher un joueur…"),
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

        # Bouton Messages : accès à toutes les conversations (avec pastille non-lus)
        self._btn_chat = main_btn(T("Messages"), COL_BTN_GREY,
                                  self._open_conversations)
        add_spacer(0.012)

        self._btn_ai = main_btn(T("Jouer contre Deep Grey"), COL_BTN_GREY, self._start_vs_ai)
        add_spacer(0.012)
        self._btn_plus = main_btn(T("Plus"), COL_BTN_GREY, self._open_plus_popup)

        add_spacer(0.02)

        # ── Parties par correspondance : 4 emplacements (2×2) ──
        # Chaque case a la FORME du plateau (ratio 7 colonnes : 8 rangées).
        corr_header = BoxLayout(orientation="horizontal", size_hint=(1, None),
                                height=Window.height * 0.04, spacing=S(8))
        corr_header.add_widget(Label(text=T("Parties par correspondance"),
                                     font_size=SF("15sp"),
                                     color=(0.15, 0.15, 0.15, 1), bold=True,
                                     halign="left", valign="middle"))
        corr_refresh = RoundButton(text=T("Actualiser"), bg_color=COL_BLUE,
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

        # Bouton T("Compte") en haut à droite (un peu plus haut pour tenir le
        # pseudo + le Mélo sur deux lignes une fois connecté).
        self.account_btn = RoundButton(text=T("Compte"), font_size=SF("12sp"), bold=True,
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
                # Fond du plateau : couleur du thème PLATEAU
                Color(*THEMES.get(THEME_BOARD, THEMES["original"])["board"])
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
        mode_txt = "Random" if gd.get("random_code") else T("Standard")

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
                wait = Label(text=T("En attente…"), font_size=SF("11sp"),
                             color=(1, 1, 1, 1), halign="center",
                             size_hint=(0.9, 0.15),
                             pos_hint={"center_x": 0.5, "center_y": 0.5})
                wait.bind(size=lambda w, s: setattr(w, "text_size", s))
                overlay.add_widget(wait)
                annul = RoundButton(text=T("Annuler"), bg_color=(0.55, 0.1, 0.1, 1),
                                    color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                                    size_hint=(0.6, 0.16),
                                    pos_hint={"center_x": 0.5, "y": 0.06})
                annul.bind(on_release=lambda *a, g=gd: self._corr_cancel_defi(g))
                overlay.add_widget(annul)
            else:
                # On me défie : "X vous défie !" + Mélo du défieur + Accepter/Refuser
                defi_melo = gd.get("adversaire_melo", 1500)
                rnd_txt = "\nRandom Fuga" if gd.get("random_code") else ""
                msg = Label(text=T("vous défie !\nMélo %d%s") % (defi_melo, rnd_txt),
                            font_size=SF("10sp"), bold=True,
                            color=(1, 1, 1, 1), halign="center",
                            size_hint=(0.9, 0.16),
                            pos_hint={"center_x": 0.5, "center_y": 0.54})
                msg.bind(size=lambda w, s: setattr(w, "text_size", s))
                overlay.add_widget(msg)
                acc = RoundButton(text=T("Accepter"), bg_color=COL_BLUE,
                                  color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                                  size_hint=(0.8, 0.15),
                                  pos_hint={"center_x": 0.5, "y": 0.24})
                acc.bind(on_release=lambda *a, g=gd: self._corr_accept(g))
                overlay.add_widget(acc)
                ref = RoundButton(text=T("Refuser"), bg_color=(0.55, 0.1, 0.1, 1),
                                  color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                                  size_hint=(0.8, 0.15),
                                  pos_hint={"center_x": 0.5, "y": 0.06})
                ref.bind(on_release=lambda *a, g=gd: self._corr_refuse(g))
                overlay.add_widget(ref)
        elif statut == "en_cours":
            # Statut clair du tour, visible directement dans l'aperçu (sans avoir
            # à ouvrir la partie), comme T("En attente…") pour les défis.
            if gd.get("my_turn"):
                txt = T("À vous de jouer")
                col = (1, 1, 1, 1)
            else:
                txt = T("À votre adversaire\nde jouer")
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
                res_txt = T("Gagné !"); res_col = (0.5, 0.9, 0.5, 1)
            elif gagne is False:
                res_txt = T("Perdu"); res_col = (0.95, 0.5, 0.5, 1)
            else:
                res_txt = T("Nulle"); res_col = (0.9, 0.9, 0.6, 1)
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
            rev = RoundButton(text=T("Revanche"), bg_color=COL_BLUE,
                              color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                              size_hint=(0.8, 0.15),
                              pos_hint={"center_x": 0.5, "y": 0.22})
            rev.bind(on_release=lambda *a, g=gd: self._corr_revanche(g))
            overlay.add_widget(rev)
            ferm = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
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
        lbl = Label(text=T("Recherche d'un adversaire…\n\nObjectif : %s\nCadence : %s")
                         % (self._fmt_objectif(), self._fmt_cadence()),
                    color=(1, 1, 1, 1), halign="center", valign="middle",
                    font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        btn_cancel = RoundButton(text=T("Annuler"), bg_color=COL_BTN_GREY,
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
                self._search_lbl.text = T("Connexion impossible :\n%s") % msg
                return
            ONLINE.chercher_partie(self.target, self.cadence)
        ONLINE.sio_connect(on_ready=_ready)

    def _on_recherche_timeout(self, data):
        """Le serveur signale une longue attente (on reste en file)."""
        if hasattr(self, "_search_lbl"):
            self._search_lbl.text = ("Toujours en recherche…\n\n" +
                                     "Essayez une autre cadence si l'attente\n" +
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
        adversaire = data.get("adversaire", T("Adversaire"))
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
        lbl = Label(text=T("Le mode en ligne n'est pas\nencore disponible."),
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
        if self.target == "partie": return T("Partie unique")
        return str(self.target)

    def _fmt_cadence(self):
        return T("Zen") if self.cadence == "zen" else T("%s min") % self.cadence

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
                self._popup_simple(T("Recherche"), T("Erreur : %s") % err)
                return
            if not res or not res.get("found"):
                self._popup_simple(T("Recherche"),
                                   T("Aucun joueur nommé « %s ».") % query)
                return
            if res.get("is_self"):
                self._popup_simple(T("Recherche"), T("C'est vous !"))
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
        is_blocked = res.get("is_blocked", False)
        statut = "En ligne" if online else T("Hors ligne")
        statut_col = (0.2, 0.7, 0.2, 1) if online else (0.6, 0.6, 0.6, 1)

        content = BoxLayout(orientation="vertical", spacing=S(10), padding=S(16))
        content.add_widget(Label(text="[b]%s[/b]" % pseudo, markup=True,
                                 font_size=SF("20sp"), color=(1, 1, 1, 1),
                                 size_hint=(1, None), height=S(34)))
        content.add_widget(Label(text=T("Mélo : %d") % melo, font_size=SF("14sp"),
                                 color=(0.9, 0.9, 0.9, 1),
                                 size_hint=(1, None), height=S(24)))
        content.add_widget(Label(text=statut, font_size=SF("13sp"), bold=True,
                                 color=statut_col,
                                 size_hint=(1, None), height=S(22)))

        row = BoxLayout(size_hint=(1, None), height=S(48), spacing=S(8))
        defier_btn = RoundButton(text=T("Défier"), bg_color=COL_BLUE,
                                 color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True)
        fav_btn = RoundButton(
            text=T("Retirer") if is_fav else T("Enregistrer"),
            bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
            font_size=SF("14sp"), bold=True)
        row.add_widget(defier_btn)
        row.add_widget(fav_btn)
        content.add_widget(row)

        # Ligne Bloquer / Débloquer (rouge = bloquer, gris = débloquer)
        block_row = BoxLayout(size_hint=(1, None), height=S(44), spacing=S(8))
        block_btn = RoundButton(
            text=T("Débloquer") if is_blocked else T("Bloquer"),
            bg_color=COL_BTN_GREY if is_blocked else (0.72, 0.26, 0.26, 1),
            color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True)
        block_row.add_widget(block_btn)
        content.add_widget(block_row)

        close_btn = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("13sp"),
                                size_hint=(1, None), height=S(40))
        content.add_widget(close_btn)
        pop = Popup(title="", content=content, size_hint=(0.85, 0.58),
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
                        T("Favoris"), T("%s retiré des favoris.") % pseudo if ok
                        else T("Erreur : %s") % e))
            else:
                ONLINE.add_favorite(pseudo,
                    lambda ok, e: self._popup_simple(
                        T("Favoris"), T("%s ajouté aux favoris !") % pseudo if ok
                        else T("Erreur : %s") % e))
            pop.dismiss()
        fav_btn.bind(on_release=_toggle_fav)

        # Bloquer / Débloquer
        def _toggle_block(*a):
            if is_blocked:
                ONLINE.unblock_user(pseudo,
                    lambda ok, e: self._popup_simple(
                        T("Blocage"), T("%s débloqué.") % pseudo if ok
                        else T("Erreur : %s") % e))
            else:
                ONLINE.block_user(pseudo,
                    lambda ok, e: self._popup_simple(
                        T("Blocage"),
                        T("%s bloqué. Vous ne pourrez plus vous croiser ni vous "
                          "défier.") % pseudo if ok else T("Erreur : %s") % e))
            pop.dismiss()
        block_btn.bind(on_release=_toggle_block)
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
        # Messagerie unifiée : messages reçus en temps réel
        ONLINE.on_event("message_recu", self._on_message_recu)

    def _on_message_recu(self, data):
        """Message reçu en temps réel : si la conversation avec l'expéditeur est
        ouverte, l'ajoute en direct ; sinon le message est déjà stocké côté
        serveur et apparaîtra à l'ouverture de la conversation."""
        de = (data or {}).get("de", "")
        texte = (data or {}).get("texte", "")
        try:
            sm = self.manager
            if sm and getattr(sm, "current", None) == "conversation":
                sm.get_screen("conversation").add_incoming(de, texte)
        except Exception:
            pass
        # Mettre à jour les pastilles de non-lus (menu + partie).
        try:
            _refresh_chat_badges(self)
        except Exception:
            pass

    def _open_conversations(self, *a):
        """Ouvre la liste de toutes les conversations."""
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        self.manager.current = "conversations_list"

    def _set_chat_badge(self, count):
        """Affiche le nombre de messages non lus sur le bouton Messages du menu."""
        try:
            if count and count > 0:
                self._btn_chat.text = T("Messages") + "  (%d)" % count
            else:
                self._btn_chat.text = T("Messages")
        except Exception:
            pass

    def _envoyer_defi(self, pseudo_cible):
        """Envoie un défi à un joueur (objectif + cadence courants du menu)."""
        if not ONLINE.is_logged_in():
            self.manager.current = "login"
            return
        self._bind_defi_handlers()
        self._defi_cible = pseudo_cible
        # Popup d'attente "Défi envoyé à X…" avec bouton Annuler
        content = BoxLayout(orientation="vertical", spacing=S(14), padding=S(20))
        lbl = Label(text=(T("Défi envoyé à %s…\n\nObjectif : %s\nCadence : %s\n\n")
                          % (pseudo_cible, self._fmt_objectif(), self._fmt_cadence())
                          + T("En attente de sa réponse.")),
                    color=(1, 1, 1, 1), halign="center", valign="middle",
                    font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        btn_cancel = RoundButton(text=T("Annuler"), bg_color=COL_BTN_GREY,
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
                self._defi_lbl.text = T("Connexion impossible :\n%s") % msg
                return
            try:
                ONLINE.defier(pseudo_cible, self.target, self.cadence)
            except Exception:
                self._defi_lbl.text = T("Impossible d'envoyer le défi.")
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
            msg = T("Vous ne pouvez pas vous défier vous-même.")
        elif raison == "bloque":
            msg = T("Défi impossible : un blocage est en place entre vous.")
        else:
            msg = T("Désolé, cet adversaire n'est pas disponible.")
        self._popup_simple(T("Défi"), msg)
        self._defi_id = None

    def _on_defi_refuse(self, data):
        """La cible a refusé le défi."""
        cible = (data or {}).get("cible", self._defi_cible if hasattr(self, "_defi_cible") else T("L'adversaire"))
        try:
            if hasattr(self, "_defi_popup"):
                self._defi_popup.dismiss()
        except Exception:
            pass
        self._popup_simple(T("Défi refusé"), T("%s a refusé votre défi.") % cible)
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
        defieur = (data or {}).get("defieur", T("Un joueur"))
        defieur_melo = (data or {}).get("defieur_melo", 1500)
        objectif = (data or {}).get("objectif", "partie")
        cadence = (data or {}).get("cadence", 15)
        # S'abonner aux événements de jeu/annulation (pour démarrer la partie)
        self._bind_defi_handlers()

        obj_txt = {"partie": T("1 partie"),
                   2: T("2 points"), 3: T("3 points"), 5: T("5 points"),
                   7: T("7 points")}.get(objectif, str(objectif))
        cad_txt = (T("Zen (illimité)") if cadence == "zen" else T("%s min") % cadence)
        rnd = bool((data or {}).get("random", False))
        extra = "\nMode : Random Fuga" if rnd else ""

        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(18))
        lbl = Label(text=T("[b]%s[/b] (Mélo %d)\nvous défie !\n\nObjectif : %s\nCadence : %s%s")
                         % (defieur, defieur_melo, obj_txt, cad_txt, extra),
                    markup=True, color=(1, 1, 1, 1), halign="center",
                    valign="middle", font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        row = BoxLayout(orientation="horizontal", spacing=S(10), size_hint=(1, 0.4))
        acc = RoundButton(text=T("Accepter"), bg_color=COL_BLUE, color=(1, 1, 1, 1),
                          font_size=SF("14sp"), bold=True)
        ref = RoundButton(text=T("Refuser"), bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
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
        title = Label(text=T("Mes favoris"), font_size=SF("18sp"), bold=True,
                      color=(1, 1, 1, 1), size_hint=(1, None), height=S(40))
        content.add_widget(title)
        scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False)
        self._fav_box = BoxLayout(orientation="vertical", size_hint=(1, None),
                                  spacing=S(6), padding=(S(2), S(2)))
        self._fav_box.bind(minimum_height=self._fav_box.setter("height"))
        scroll.add_widget(self._fav_box)
        content.add_widget(scroll)
        close_btn = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                                size_hint=(1, None), height=S(46))
        content.add_widget(close_btn)
        self._fav_popup = Popup(title="", content=content, size_hint=(0.96, 0.85),
                                separator_height=0)
        close_btn.bind(on_release=lambda *a: self._fav_popup.dismiss())

        # Message de chargement
        loading = Label(text=T("Chargement…"), color=(0.8, 0.8, 0.8, 1),
                        size_hint=(1, None), height=S(40))
        self._fav_box.add_widget(loading)

        def on_favs(favs, err):
            self._fav_box.clear_widgets()
            if err:
                self._fav_box.add_widget(Label(text=T("Erreur : %s") % err,
                    color=(1, 0.5, 0.5, 1), size_hint=(1, None), height=S(40)))
                return
            if not favs:
                self._fav_box.add_widget(Label(
                    text=T("Aucun favori pour le moment.\nCherchez un joueur pour l'ajouter en favori."),
                    color=(0.8, 0.8, 0.8, 1), halign="center",
                    size_hint=(1, None), height=S(60)))
                return
            for fav in favs:
                self._fav_box.add_widget(self._make_fav_row(fav, self._fav_popup))
        ONLINE.list_favorites(on_favs)
        self._fav_popup.open()

    def _make_fav_row(self, fav, parent_popup):
        """Carte d'un favori : pseudo + Mélo + état, puis une rangée de boutons
        Défier / Profil / Message / Bloquer. Élargie pour les pseudos longs."""
        pseudo = fav.get("pseudo", "?")
        melo = fav.get("melo", 1500)
        online = fav.get("online", False)
        card = BoxLayout(orientation="vertical", size_hint=(1, None),
                         height=S(94), spacing=S(4), padding=(S(10), S(6)))
        with card.canvas.before:
            Color(*COL_BTN_GREY)
            card._r = RoundedRectangle(pos=card.pos, size=card.size, radius=[S(10)])
        card.bind(pos=lambda b, *a: setattr(b._r, "pos", b.pos),
                  size=lambda b, *a: setattr(b._r, "size", b.size))
        etat = T("  ·  en ligne") if online else ""
        nom_col = (0.55, 0.9, 0.55, 1) if online else (1, 1, 1, 1)
        info = Label(text="%s  ·  Mélo %d%s" % (pseudo, melo, etat),
                     font_size=SF("14sp"), bold=True, color=nom_col,
                     halign="left", valign="middle", shorten=True,
                     shorten_from="right", size_hint=(1, 0.4))
        info.bind(size=lambda w, s: setattr(w, "text_size", s))
        card.add_widget(info)
        btns = BoxLayout(orientation="horizontal", size_hint=(1, 0.6), spacing=S(6))

        def mk(txt, bg, cb):
            b = RoundButton(text=txt, bg_color=bg, color=(1, 1, 1, 1),
                            font_size=SF("11sp"), bold=True, size_hint=(1, 1))
            b.bind(on_release=lambda *a: cb())
            btns.add_widget(b)

        mk(T("Défier"), COL_BLUE,
           lambda: (parent_popup.dismiss(), self._envoyer_defi(pseudo)))
        mk(T("Profil"), COL_BTN_GREY,
           lambda: (parent_popup.dismiss(), self._fav_open_profile(pseudo)))
        mk(T("Message"), COL_BTN_GREY,
           lambda: (parent_popup.dismiss(), self._fav_open_message(pseudo)))
        mk(T("Bloquer"), (0.72, 0.26, 0.26, 1),
           lambda: self._fav_block(pseudo, card))
        card.add_widget(btns)
        return card

    def _fav_open_profile(self, pseudo):
        try:
            scr = self.manager.get_screen("account")
            scr.target_pseudo = None if pseudo == (ONLINE.pseudo or "") else pseudo
            self.manager.current = "account"
        except Exception:
            pass

    def _fav_open_message(self, pseudo):
        try:
            conv = self.manager.get_screen("conversation")
            conv.target_pseudo = pseudo
            conv.return_screen = "menu"
            self.manager.current = "conversation"
        except Exception:
            pass

    def _fav_block(self, pseudo, card):
        def on_done(ok, err):
            if ok:
                try:
                    self._fav_box.remove_widget(card)
                except Exception:
                    pass
        ONLINE.block_user(pseudo, on_done)
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
        title = Label(text=T("Défier un favori\n(par correspondance)"),
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
        close_btn = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                                size_hint=(1, None), height=S(46))
        content.add_widget(close_btn)
        popup = Popup(title="", content=content, size_hint=(0.9, 0.8),
                      separator_height=0)
        close_btn.bind(on_release=lambda *a: popup.dismiss())

        box.add_widget(Label(text=T("Chargement…"), color=(0.8, 0.8, 0.8, 1),
                             size_hint=(1, None), height=S(40)))

        def on_favs(favs, err):
            box.clear_widgets()
            if err:
                box.add_widget(Label(text=T("Erreur : %s") % err,
                    color=(1, 0.5, 0.5, 1), size_hint=(1, None), height=S(40)))
                return
            if not favs:
                box.add_widget(Label(
                    text=T("Aucun favori.\nAjoutez des favoris via la recherche."),
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
        etat = T("  ·  en ligne") if online else ""
        nom_col = (0.55, 0.9, 0.55, 1) if online else (1, 1, 1, 1)
        info = Label(text="%s  ·  Mélo %d%s" % (pseudo, melo, etat),
                     font_size=SF("13sp"), bold=True, color=nom_col,
                     halign="left", valign="middle",
                     shorten=True, shorten_from="right", size_hint=(1, 1))
        info.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(info)
        btn = RoundButton(text=T("Défier"), bg_color=COL_BLUE, color=(1, 1, 1, 1),
                          font_size=SF("12sp"), bold=True,
                          size_hint=(None, 0.8), width=S(80),
                          pos_hint={"center_y": 0.5})

        def _defi(*a):
            parent_popup.dismiss()
            def on_done(result, err):
                if err or not (result and result.get("ok")):
                    msg = (result or {}).get("message") or err or T("Échec du défi.")
                    self._popup_simple(T("Correspondance"), msg)
                else:
                    self._popup_simple(T("Correspondance"),
                                       T("Défi envoyé à %s !") % pseudo)
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
                self._popup_simple(T("Correspondance"), T("Échec : %s") % (err or ""))
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
                    msg = (result or {}).get("message") or err2 or T("Échec du défi.")
                    self._popup_simple(T("Correspondance"), msg)
                else:
                    self._popup_simple(T("Correspondance"), T("Revanche envoyée à %s !") % adv)
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
        Popup(title=T("Connexion requise"),
              content=Label(text=T("Connectez-vous (bouton Compte)\npour jouer en ligne."), color=(1, 1, 1, 1)),
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

        content.add_widget(make_btn(T("Tuto"),
            lambda: setattr(self.manager, "current", "tuto"), bg=COL_ORANGE))
        content.add_widget(make_btn(T("Historique"),
            lambda: setattr(self.manager, "current", "parties_menu")))
        content.add_widget(make_btn(T("Analyse"),
            lambda: self._start_analysis()))
        content.add_widget(make_btn(T("Réglages"),
            lambda: open_settings_popup(None)))
        content.add_widget(make_btn(T("Soutenir les devs"),
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
            text=T("Merci de soutenir le développement de La Fuga !\n")
                 + T("Votre aide compte beaucoup."),
            font_size=SF("14sp"), color=(1, 1, 1, 1),
            halign="center", valign="middle", size_hint=(1, None), height=S(60))
        intro.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(intro)

        popup = Popup(title=T("Soutenir les devs"), content=content,
                      size_hint=(0.82, 0.6))

        def make_link_btn(label, url):
            b = RoundButton(text=label, font_size=SF("16sp"), bold=True,
                            bg_color=COL_BLUE, color=(1, 1, 1, 1),
                            size_hint=(1, None), height=Window.height * 0.06)
            def _open(*a):
                if not url:
                    self._popup_simple(T("Bientôt"),
                                       T("Ce lien sera bientôt disponible."))
                    return
                # Sur Android, on ouvre le lien via l'intent natif (webbrowser
                # ne marche pas toujours dans l'APK). Repli sur webbrowser (PC).
                opened = False
                try:
                    from jnius import autoclass, cast
                    Intent = autoclass("android.content.Intent")
                    Uri = autoclass("android.net.Uri")
                    PythonActivity = autoclass(
                        "org.kivy.android.PythonActivity")
                    intent = Intent(Intent.ACTION_VIEW, Uri.parse(url))
                    intent.setFlags(0x10000000)  # FLAG_ACTIVITY_NEW_TASK
                    activity = cast("android.app.Activity",
                                    PythonActivity.mActivity)
                    activity.startActivity(intent)
                    opened = True
                except Exception:
                    opened = False
                if not opened:
                    try:
                        import webbrowser
                        webbrowser.open(url)
                        opened = True
                    except Exception:
                        opened = False
                if not opened:
                    self._popup_simple(T("Lien"), url)
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
            self._bg_col.rgba = COL_MENU_BG
        # Fond image (thème médiéval), largeur calée sur l'écran
        if hasattr(self, "_bg_stone") and hasattr(self, "_bg_stone_col"):
            tex = _theme_bg_texture("fond.png", theme=THEME_MENU_BG) if _theme_bg_dir(THEME_MENU_BG) else None
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
            if THEME_MENU_BG == "fleur" and _theme_bg_texture("fond.png", theme=THEME_MENU_BG):
                self._bg_veil_col.rgba = (1, 1, 1, 0.45)
                self._bg_veil.size = Window.size
            else:
                self._bg_veil_col.rgba = (1, 1, 1, 0)
            self._btn_local.set_bg(COL_ORANGE)
        if hasattr(self, "_btn_online"):
            self._btn_online.set_bg(COL_BLUE)
        if hasattr(self, "_logo_widget"):
            p = self._theme_logo_path()
            self._logo_widget.source = p
            # Rechargement radical : on recharge la texture nous-mêmes en
            # contournant tout cache, sinon Kivy garde parfois l'ancien logo.
            try:
                from kivy.core.image import Image as CoreImage
                self._logo_widget.texture = CoreImage(p, nocache=True).texture
            except Exception:
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
        logo_name = logo_special.get(THEME_LOGO, THEME_LOGO)
        themed = os.path.join(base, "logos", f"logo_{logo_name}.png")
        if os.path.exists(themed):
            return themed
        fallback = os.path.join(base, "logo.png")
        return fallback if os.path.exists(fallback) else themed

    def _on_logo_touch(self, widget, touch):
        """Clic sur le logo : ouvre l'histoire de La Fuga."""
        if widget.collide_point(*touch.pos):
            self._show_story_popup()
            return True
        return False

    def _show_story_popup(self, *a):
        """Histoire du jeu en PLEIN ÉCRAN (tout en % d'écran) : texte centré
        horizontalement et verticalement, pièces en bas, croix pour fermer."""
        from kivy.uix.modalview import ModalView
        from kivy.uix.floatlayout import FloatLayout
        from kivy.uix.anchorlayout import AnchorLayout
        from kivy.uix.widget import Widget
        from kivy.graphics import Color, Rectangle

        # Fond thématique (texture du thème si dispo, sinon parchemin uni).
        tex = _theme_bg_texture("fond.png")

        root = FloatLayout()
        with root.canvas.before:
            if tex:
                Color(1, 1, 1, 1)
                root._sbg = Rectangle(texture=tex, pos=root.pos, size=root.size)
                Color(0.95, 0.89, 0.74, 0.86)
                root._sveil = Rectangle(pos=root.pos, size=root.size)
            else:
                Color(0.93, 0.87, 0.72, 1)
                root._sbg = Rectangle(pos=root.pos, size=root.size)
                root._sveil = None

        def _sync(*_):
            root._sbg.pos = root.pos
            root._sbg.size = root.size
            if getattr(root, "_sveil", None) is not None:
                root._sveil.pos = root.pos
                root._sveil.size = root.size
        root.bind(pos=_sync, size=_sync)

        # Colonne : titre (haut) / texte (milieu) / pièces (bas). Tout en %.
        col = BoxLayout(orientation="vertical", size_hint=(1, 1),
                        padding=(Window.width * 0.06, Window.height * 0.02))

        title = Label(text=T("L'histoire de La Fuga"), font_size=SF("21sp"),
                      bold=True, color=(0.22, 0.13, 0.05, 1),
                      size_hint=(1, 0.09), halign="center", valign="middle")
        title.bind(size=lambda w, s: setattr(w, "text_size", s))
        col.add_widget(title)

        # Texte : centré H (largeur contrainte + halign) et V (AnchorLayout).
        mid = AnchorLayout(size_hint=(1, 0.72), anchor_x="center",
                           anchor_y="center")
        lbl = Label(text=story_text(), font_size=SF("17sp"),
                    color=(0.20, 0.12, 0.04, 1), size_hint=(1, None),
                    halign="center", valign="top")
        lbl.bind(width=lambda w, *a: setattr(w, "text_size", (w.width, None)))
        lbl.bind(texture_size=lambda w, s: setattr(w, "height", s[1]))
        mid.add_widget(lbl)
        col.add_widget(mid)

        # Rangée des pièces, nom en dessous.
        def _make_piece_cell(typ, camp):
            cell = BoxLayout(orientation="vertical", size_hint_x=1)
            holder = AnchorLayout(size_hint=(1, 1))
            piece = {"type": typ, "camp": camp}
            isz = Window.height * 0.05
            icon = Widget(size_hint=(None, None), size=(isz, isz))

            def _draw_icon(w, *a):
                w.canvas.clear()
                try:
                    draw_piece(w.canvas, w.x, w.y, min(w.width, w.height),
                               piece, flipped=True, force_normal=True)
                except Exception:
                    pass
            icon.bind(pos=_draw_icon, size=_draw_icon)
            holder.add_widget(icon)
            nm = Label(text=T(typ), font_size=SF("10sp"),
                       color=(0.20, 0.12, 0.04, 1), size_hint=(1, 0.35),
                       halign="center", valign="middle")
            nm.bind(size=lambda w, s: setattr(w, "text_size", s))
            cell.add_widget(holder)
            cell.add_widget(nm)
            return cell

        pieces = [("Héritier", "Blanc"), ("Chevalier", "Noir"),
                  ("Nurse", "Blanc"), ("Soldat", "Noir"), ("Garde", "Blanc")]
        row = BoxLayout(orientation="horizontal", size_hint=(1, 0.19),
                        spacing=Window.width * 0.01)
        for typ, camp in pieces:
            row.add_widget(_make_piece_cell(typ, camp))
        col.add_widget(row)

        root.add_widget(col)

        mv = ModalView(size_hint=(1, 1), background_color=(0, 0, 0, 0),
                       auto_dismiss=True)
        mv.add_widget(root)

        # Croix (X) en haut à droite (ferme le calque).
        x_btn = RoundButton(text="X", font_size=SF("16sp"), bold=True,
                            bg_color=(0.55, 0.16, 0.16, 1), color=(1, 1, 1, 1),
                            size_hint=(None, None),
                            size=(Window.height * 0.05, Window.height * 0.05),
                            pos_hint={"right": 0.99, "top": 0.99})
        x_btn.bind(on_release=lambda *a: mv.dismiss())
        root.add_widget(x_btn)

        mv.open()

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
            # Pastille de messages non lus sur le bouton Messages.
            try:
                _refresh_chat_badges(self)
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
        # Le Mélo affiché dépend du mode : le mettre à jour immédiatement.
        self._refresh_online_ui()

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
        et le Mélo DU MODE EN COURS (standard, ou random si Random Fuga activé)."""
        if not hasattr(self, "account_btn"): return
        if ONLINE.is_logged_in():
            cur_melo = ONLINE.melo_random if RANDOM_MODE else ONLINE.melo
            self.account_btn.text = "%s (%d)" % (ONLINE.pseudo or "?", cur_melo)
        else:
            self.account_btn.text = T("Compte")
        self.account_btn.bg_color = COL_BTN_GREY
        self.account_btn.color = (1, 1, 1, 1)

    def _on_account_press(self, *a):
        """Si connecté : MON profil (on remet la cible à None). Sinon : login."""
        if ONLINE.is_logged_in():
            try:
                self.manager.get_screen("account").target_pseudo = None
            except Exception:
                pass
            self.manager.current = "account"
        else:
            self.manager.current = "login"

    def _show_account_popup(self):
        """Popup d'infos du compte connecté, avec bouton de déconnexion."""
        content = BoxLayout(orientation="vertical", spacing=S(14), padding=S(18))
        info = Label(text=T("Connecté en tant que :\n[b]%s[/b]\n\nMélo : %d")
                          % (ONLINE.pseudo or "?", ONLINE.melo),
                     markup=True, color=(1, 1, 1, 1), halign="center",
                     valign="middle", font_size=SF("16sp"))
        info.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(info)
        btn = RoundButton(text=T("Se déconnecter"), font_size=SF("15sp"), bold=True,
                          bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                          size_hint=(1, None), height=S(48))
        content.add_widget(btn)
        popup = Popup(title=T("Mon compte"), content=content,
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
        lbl = Label(text=T("Choisissez votre couleur"),
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

        b_blanc = RoundButton(text=T("Jouer avec les Blancs"), font_size=SF("16sp"),
                              bold=True, bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                              size_hint=(1, 0.26))
        b_blanc.bind(on_release=lambda *_: launch("Blanc"))

        b_noir = RoundButton(text=T("Jouer avec les Noirs"), font_size=SF("16sp"),
                             bold=True, bg_color=COL_BLUE, color=(1, 1, 1, 1),
                             size_hint=(1, 0.26))
        b_noir.bind(on_release=lambda *_: launch("Noir"))

        b_alea = RoundButton(text=T("Aléatoire"), font_size=SF("16sp"),
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
            "text": ("Bienvenue. À La Fuga, le but du jeu est d'emmener " +
                     "l'Héritier (pièce encadrée) jusqu'à sa zone de ralliement, " +
                     "à l'autre bout du plateau. Bien sûr, vous devrez aussi " +
                     "empêcher votre adversaire d'y parvenir. Il peut y parvenir " +
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
            "text_move": ("Toutes les pièces peuvent se déplacer d'une case dans " +
                          "n'importe quelle direction. Déplace l'Héritier sur " +
                          "une case voisine."),
            "text_validate": ("Pour valider ton coup, clique à nouveau sur la " +
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
            "text": ("Pour se déplacer, une pièce RONDE doit toucher une autre " +
                     "ronde (alliée ou adverse), et une pièce CARRÉE doit toucher " +
                     "une autre carrée. En vert : les pièces qui peuvent bouger. " +
                     "En rouge : les pièces bloquées (aucune pièce de leur forme " +
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
            "text_select": ("Une pièce ronde saute par-dessus une autre ronde " +
                            "(alliée ou adverse), en ligne DROITE ou en DIAGONALE, " +
                            "et peut enchaîner les sauts ! Clique sur la Nurse."),
            "text_validate": ("Clique à nouveau sur la Nurse pour valider ton " +
                              "multisaut."),
            "text_done": ("Bravo ! Sauts droits et diagonaux : tu maîtrises le " +
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
                 "text": "Dernier saut, en DIAGONALE par-dessus fa8 : l'Héritier " +
                         "SORT du plateau et rejoint son ralliement !"},
            ],
            "text_select": ("L'Héritier peut lui aussi enchaîner les sauts, " +
                            "droits ou diagonaux, et même FUGUER en sautant. " +
                            "Clique sur l'Héritier."),
            "text_done": ("Fugue réussie ! L'Héritier a atteint son ralliement : " +
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
            "text_select": ("Les pièces carrées d'un même camp qui se touchent, " +
                            "même en diagonale, forment une UNITÉ. Plusieurs " +
                            "pièces de la même unité peuvent se déplacer en même " +
                            "temps, dans la même direction. Déplaçons plusieurs " +
                            "pièces de l'unité en vert ; clique sur do2, qui sera " +
                            "la meneuse."),
            "text_group": ("Ajoute ré2 puis fa3 à la sélection (on laisse mi2 de " +
                           "côté : tu n'es pas obligé de tout prendre)."),
            "text_move": ("L'unité se déplace selon la meneuse. Clique en do3 " +
                          "pour monter les pièces choisies d'une case."),
            "text_validate": "Clique sur la meneuse pour valider ton coup.",
            "text_done": ("En montant, la pièce en fa s'est retrouvée seule " +
                          "(encadrée) ! Une manœuvre peut donc IMMOBILISER une " +
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
            "text_select": ("Le GARDE (croix ×) se déplace en diagonale et POUSSE " +
                            "en ligne droite. Clique sur le Garde."),
            "text_move": "Déplace le Garde en diagonale, jusqu'en fa4.",
            "text_push": ("Maintenant POUSSE : clique en sol4. Toute la ligne est " +
                          "repoussée d'une case, et la pièce du bord tombe du " +
                          "plateau (éliminée) !"),
            "text_validate": "Clique sur le Garde pour valider ton coup.",
            "text_done": ("Bravo ! Le Garde a poussé la ligne et éliminé une " +
                          "pièce. C'est le SEUL moyen d'éliminer une pièce : la " +
                          "pousser hors du plateau. Et tu peux même éliminer tes " +
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
            "text_select": ("Le SOLDAT (croix +) se déplace en ligne droite et " +
                            "POUSSE en diagonale. Clique sur le Soldat."),
            "text_move": "Déplace le Soldat tout droit, en do4.",
            "text_push": ("POUSSE en diagonale : clique en ré5 pour repousser la " +
                          "pièce."),
            "text_validate": "Clique sur le Soldat pour valider ton coup.",
            "text_done": ("Attention : en se déplaçant, le Soldat s'est éloigné de " +
                          "son allié et n'a plus de carrée à côté, il est " +
                          "maintenant BLOQUÉ (encadré) jusqu'à ce qu'une carrée le " +
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
                 "text": "Tu peux pousser une AUTRE direction ! Clique en sol4 " +
                         "(vers la droite)."},
            ],
            "text_select": ("Après s'être déplacée, une carrée peut pousser dans " +
                            "PLUSIEURS directions, autant que tu veux. Clique sur " +
                            "le Garde."),
            "text_move": "Déplace le Garde en diagonale, en fa4.",
            "text_validate": "Clique sur le Garde pour valider ton coup.",
            "text_done": ("Bravo ! Tu as poussé en haut et à droite. Remarque : " +
                          "fa3 (en bas) pouvait aussi être poussée, mais on l'a " +
                          "laissée, c'est toi qui choisis quelles directions " +
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
            "text_select": ("On peut aussi POUSSER son propre Héritier ! Clique " +
                            "sur le Garde."),
            "text_move": "Déplace le Garde en diagonale, en fa7 (sous l'Héritier).",
            "text_push": ("POUSSE vers le haut : clique en fa8. L'Héritier est " +
                          "poussé dans son ralliement !"),
            "text_done": ("Fugue ! Tu as poussé ton Héritier dans son ralliement : " +
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
            "text_select": ("Enfin, pousser l'Héritier ADVERSE hors du plateau le " +
                            "met MAT. Clique sur le Garde."),
            "text_move": "Déplace le Garde en diagonale, en la7 (sous l'Héritier adverse).",
            "text_push": ("POUSSE vers le haut : clique en la8. L'Héritier adverse " +
                          "est éjecté du plateau !"),
            "text_done": ("Mat ! Tu as poussé l'Héritier adverse hors du plateau : " +
                          "VICTOIRE !"),
        },
        {   # Étape 12, Le Chevalier (illustration : inébranlable + indépendant)
            "title": "Le Chevalier",
            "pieces": [
                ("fa", 3, "Chevalier", "Blanc"),
                ("fa", 6, "Chevalier", "Noir"),
            ],
            "framed_blue": [("fa", 3), ("fa", 6)],
            "text": ("Le CHEVALIER (l'hexagone) est une pièce à part, avec deux " +
                     "pouvoirs. INÉBRANLABLE : il ne peut jamais être poussé, une " +
                     "poussée s'arrête net sur lui. INDÉPENDANT : il peut se " +
                     "déplacer même s'il ne touche aucune pièce de sa forme (il " +
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
            "text": ("Puisqu'il ne peut être poussé, le Chevalier sert de MUR : il " +
                     "bloque les poussées. Ici, même si le Garde adverse s'avance " +
                     "en fa3 pour pousser vers le haut, le Chevalier (fa4) arrête " +
                     "tout : l'Héritier (fa5) est protégé."),
        },
        {   # Transition : bannière "motifs de fin de partie" +
            "title": "Fins de partie",
            "banner": T("MOTIFS DE\nFIN DE PARTIE"),
            "pieces": [],
            "text": ("Voici toutes les façons dont une partie peut se terminer, " +
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
            "text": ("FUGUE (+2 points). Ton Héritier atteint son ralliement (la " +
                     "flèche) : tu gagnes la partie ! C'est la victoire la plus " +
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
            "text": ("DOUBLE FUGUE (0 point). Quand les Blancs fuguent, les Noirs " +
                     "ont droit à un DERNIER coup pour égaliser. Si les deux " +
                     "Héritiers rejoignent leur ralliement, la partie est nulle. " +
                     "Ici, c'est aux Blancs de jouer, et les deux Héritiers peuvent " +
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
            "text": ("MAT (+1 point). Le Garde (si6) se déplace en la7, puis pousse " +
                     "l'Héritier adverse (la8) hors du plateau : il est éjecté, tu " +
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
            "text": ("GUILLOTINE. L'adversaire va fuguer (son Héritier fa1, mobile " +
                     "grâce à sa Nurse, atteint son ralliement en bas : +2 pour " +
                     "lui). Pour limiter la casse, ton Garde (si6 vers la7) pousse " +
                     "TON PROPRE Héritier (la8) hors du plateau : c'est un mat sur " +
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
            "text": ("PAPATTE (+1 point). C'est à l'adversaire de jouer, mais il " +
                     "n'a AUCUN coup légal : son Chevalier (do8) est coincé, et son " +
                     "Héritier (si8) est isolé (aucune ronde à côté). Il perd. Très " +
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
            "text": ("TRÊVE (0 point). Quand plus AUCUN joueur n'a de carrée qui " +
                     "peut bouger (peu importe à qui c'est de jouer), la partie est " +
                     "nulle : sans carrée mobile, plus aucune poussée n'est " +
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
            "text": ("NULLE PAR ACCORD (0 point). Pendant une partie, tu peux " +
                     "proposer la nulle avec le bouton « ½ » (entouré) ; si " +
                     "l'adversaire accepte, la partie est nulle. RÉPÉTITION : si la " +
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
            "text": ("ABANDON / TEMPS / DÉCONNEXION (+2 points chacun). Trois façons " +
                     "de gagner sans jouer : si l'adversaire ABANDONNE (le bouton " +
                     "« X »), si son TEMPS tombe à 0:00 (la pendule), ou s'il se " +
                     "DÉCONNECTE. Dans les trois cas, tu gagnes +2 " +
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
            self.text_box.text = T(step.get("text", ""))
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
                self.text_box.text = T(step.get("text_select", ""))
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
                self.text_box.text = T(step.get("text_group", ""))
                nxt = step["_group_internal"][self._grp_idx]
                self.tuto_annotations = {"framed_sel": [nxt], "arrows": []}
            elif ph == "mmove":
                self.text_box.text = T(step.get("text_move", ""))
                self.tuto_annotations = {
                    "framed": [],
                    "arrows": [(leader, step["_moveto_internal"])],
                }
            elif ph == "validate":
                self.text_box.text = T(step.get("text_validate", ""))
                self.tuto_annotations = {"framed_sel": [self._moved_to], "arrows": []}
            else:  # done
                self.text_box.text = T(step.get("text_done", ""))
                dframe = step.get("_doneframe_internal")
                self.tuto_annotations = ({"framed": [dframe], "arrows": []}
                                         if dframe else None)
            return
        # Poussée : phases select -> move -> push -> validate -> done
        if step.get("push"):
            leader = step["_leader_internal"]
            ph = self._phase
            if ph == "select":
                self.text_box.text = T(step.get("text_select", ""))
                self.tuto_annotations = {"framed_sel": [leader], "arrows": []}
            elif ph == "move":
                self.text_box.text = T(step.get("text_move", ""))
                self.tuto_annotations = {
                    "framed": [],
                    "arrows": [(leader, step["_moveto_internal"])],
                }
            elif ph == "push":
                pushes = step.get("_pushes_internal")
                if pushes is not None:
                    cur = pushes[self._push_idx]
                    self.text_box.text = T(cur.get("text", step.get("text_push", "")))
                    self.tuto_annotations = {
                        "framed": [],
                        "arrows": [(step["_moveto_internal"], cur["push_to"])],
                    }
                else:
                    self.text_box.text = T(step.get("text_push", ""))
                    self.tuto_annotations = {
                        "framed": [],
                        "arrows": [(step["_moveto_internal"], step["_pushto_internal"])],
                    }
            elif ph == "validate":
                self.text_box.text = T(step.get("text_validate", ""))
                self.tuto_annotations = {"framed_sel": [self._moved_to], "arrows": []}
            else:  # done
                self.text_box.text = T(step.get("text_done", ""))
                dframe = step.get("_doneframe_internal")
                self.tuto_annotations = ({"framed": [dframe], "arrows": []}
                                         if dframe else None)
            return
        ph = self._phase
        mp = step["_move_internal"]
        seq = step.get("_sequence_internal")
        if ph == "select":
            self.text_box.text = T(step.get("text_select", ""))
            self.tuto_annotations = {"framed_sel": [mp], "arrows": []}
        elif ph == "move":
            if seq is not None:
                # Multisaut : flèche du saut courant (de la pièce vers l'arrivée)
                cur = seq[self._seq_idx]
                self.text_box.text = T(cur.get("text", step.get("text_move", "")))
                self.tuto_annotations = {"framed": [], "arrows": [(mp, cur["dest"])]}
            else:
                self.text_box.text = T(step.get("text_move", ""))
                self.tuto_annotations = {
                    "framed": [],
                    "arrows": [(self._conv_cell(*p0), self._conv_cell(*p1))
                               for (p0, p1) in step.get("arrows", [])],
                }
        elif ph == "validate":
            self.text_box.text = T(step.get("text_validate", ""))
            self.tuto_annotations = {"framed_sel": [self._moved_to], "arrows": []}
        else:  # done
            self.text_box.text = T(step.get("text_done", ""))
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
        self.pause_btn = RoundButton(text=T("Pause"), font_size=SF("13sp"), bold=True,
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
        self.prev_btn = RoundButton(text=T("< Précédent"), font_size=SF("15sp"),
                                    bold=True, bg_color=COL_BTN_GREY,
                                    color=(1, 1, 1, 1))
        self.prev_btn.bind(on_release=lambda *a: self._prev())
        self.next_btn = RoundButton(text=T("Suivant >"), font_size=SF("15sp"),
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
            self.banner_lbl.text = T(step["banner"])
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
        self.text_box.text = T(stop.get("text", ""))
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
        self.next_btn.text = T("Le menu >") if last else T("Suivant >")

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
        popup = Popup(title=T("Pause"), content=content, size_hint=(0.8, 0.42))

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

        content.add_widget(mk(T("Réglages"), lambda: open_settings_popup(None)))
        content.add_widget(mk(T("Fermer le tuto"), _close, bg=COL_ORANGE))
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

        # Zones de ralliement : couleurs du thème PLATEAU (axe "plateau"),
        # indépendamment des couleurs générales.
        _bt = THEMES.get(THEME_BOARD, THEMES["original"])
        _b_clair, _b_fonce = _bt["clair"], _bt["fonce"]
        top_color = _b_clair if self.gs.flipped else _b_fonce
        bot_color = _b_fonce if self.gs.flipped else _b_clair

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
            medieval_tex = (_theme_bg_texture("plateau.png", theme=THEME_BOARD)
                            if _theme_bg_dir(THEME_BOARD) else None)
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
                # Petits carrés sur le chemin d'un multisaut reconstruit (même
                # couleur que les cadres du dernier coup ; le carré rappelle les
                # cadres et ne se confond pas avec les pièces rondes).
                for (pc, pr) in hl.get("jump_path", []):
                    if 0 <= pc < COLS and 0 <= pr < ROWS:
                        px = self._col_to_x(pc, cs, ox)
                        py = self._row_to_y(pr, cs, oy)
                        d = cs * 0.16
                        Rectangle(pos=(px + cs * 0.5 - d * 0.5,
                                       py + cs * 0.5 - d * 0.5), size=(d, d))

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
                cl = _CoreLabel(text=T(el.get("text", "")),
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
    title_lbl = Label(text=T("Pause"), font_size=SF("20sp"), bold=True,
                      color=(1, 1, 1, 1), size_hint=(1, 0.14),
                      halign="center", valign="middle")
    title_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(title_lbl)
    info_lbl = Label(
        text=T("Le chrono du joueur au trait continue à s'écouler."),
        font_size=SF("13sp"), italic=True, color=(0.8, 0.8, 0.8, 1),
        size_hint=(1, 0.20), halign="center", valign="middle")
    info_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(info_lbl)
    btn_resume = RoundButton(text=T("Reprendre"), bg_color=COL_ORANGE,
                             color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                             size_hint=(1, 0.18))
    btn_settings = RoundButton(text=T("Réglages"), bg_color=COL_BTN_GREY,
                               color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                               size_hint=(1, 0.18))
    # En correspondance : pas de "match" (partie unique), donc le bouton ne
    # propose pas d'annuler/abandonner mais simplement de revenir au menu (la
    # partie reste en cours sur le serveur, on y reviendra plus tard).
    # EN LIGNE (matchmaking/défi) : pas de bouton T("Annuler le match") ici, on
    # abandonne la PARTIE via le bouton [×], et on met fin au MATCH entre deux
    # parties via "Quitter le match". Inutile de dupliquer dans la pause.
    _is_corr_pause = getattr(game, "corr_mode", False)
    _is_online_pause = getattr(game, "online_mode", False)
    btn_quit = None
    if not _is_online_pause:
        btn_quit = RoundButton(text=(T("Revenir au menu") if _is_corr_pause
                                     else T("Annuler le match")),
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
    t = Label(text=T("Annuler le match ?"), font_size=SF("18sp"), bold=True,
              color=(1, 1, 1, 1), size_hint=(1, 0.3),
              halign="center", valign="middle")
    t.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(t)
    if is_online:
        msg = T("Abandonner compte comme une DÉFAITE.\nVotre adversaire gagne les points.")
    elif is_corr:
        msg = T("Abandonner compte comme une défaite\ndans cette partie de correspondance.")
    else:
        msg = T("La partie en cours sera perdue.")
    info = Label(text=msg, font_size=SF("13sp"), color=(0.85, 0.85, 0.85, 1),
                 size_hint=(1, 0.25), halign="center", valign="middle")
    info.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(info)
    row = BoxLayout(orientation="horizontal", size_hint=(1, 0.32), spacing=S(8))
    b_no  = RoundButton(text=T("Continuer"), bg_color=COL_BTN_GREY,
                        color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                        size_hint=(0.5, 1))
    b_yes = RoundButton(text=T("Abandonner") if (is_online or is_corr) else T("Annuler le match"),
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
    t = Label(text=T("Abandonner ?"), font_size=SF("18sp"), bold=True,
              color=(1, 1, 1, 1), size_hint=(1, 0.18),
              halign="center", valign="middle")
    t.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(t)
    info = Label(
        text=T("{name} confirme abandonner. L'adversaire marquera 2 points.").format(name=abandoning),
        font_size=SF("13sp"), color=(0.85, 0.85, 0.85, 1),
        size_hint=(1, 0.26), halign="center", valign="middle")
    info.bind(size=lambda w, s: setattr(w, "text_size", s))
    content.add_widget(info)
    btn_no  = RoundButton(text="Annuler", bg_color=COL_BTN_GREY,
                          color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True,
                          size_hint=(1, 0.22))
    btn_yes = RoundButton(text=T("Oui, abandonner"), bg_color=(0.7, 0.15, 0.15, 1),
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
        # Bouton T("Analyser") visible uniquement en mode replay
        self.analyse_btn = RoundButton(text=T("Analyser"), font_size=SF("14sp"), bold=True,
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
        self.ai_mode_btn = RoundButton(text=T("Rapide"), font_size=SF("15sp"), bold=True,
                                       bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                       size_hint=(None, 1), width=S(108),
                                       radius=S(14))
        self.ai_mode_btn.bind(on_release=self._toggle_ai_mode)
        self.ai_mode_btn.opacity = 0
        self.ai_mode_btn.disabled = True
        # Bouton T("Chat") visible uniquement en partie en ligne
        self.chat_btn = RoundButton(text=T("Chat"), font_size=SF("14sp"), bold=True,
                                    bg_color=(0.15, 0.15, 0.15, 1), color=(1, 1, 1, 1),
                                    size_hint=(None, 1), width=S(88),
                                    radius=S(14))
        self.chat_btn.bind(on_release=lambda *a: self._open_chat())
        self.chat_btn.opacity = 0
        self.chat_btn.disabled = True
        # Bouton "Retour au menu" : caché par défaut (largeur 0), affiché quand la
        # partie est terminée, pour toujours pouvoir revenir au menu même après
        # avoir fermé le popup de fin. Placé à GAUCHE (toujours visible).
        self.menu_btn = RoundButton(text=T("Retour au menu"), font_size=SF("11sp"),
                                    bold=True, bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                                    size_hint=(None, 1), width=0, radius=S(14))
        self.menu_btn.bind(on_release=self._back_to_menu)
        self.menu_btn.opacity = 0
        self.menu_btn.disabled = True
        self.top_bar.add_widget(self.flip_btn)
        self.top_bar.add_widget(self.menu_btn)
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
        self.top_info = BoxLayout(orientation="horizontal",
                                  size_hint=(1, 0.12),
                                  padding=(S(10), S(4)), spacing=S(8))
        with self.top_info.canvas.before:
            self._top_info_col = Color(*COL_BG_MENU)
            self._top_info_rect = RoundedRectangle(pos=self.top_info.pos,
                                                   size=self.top_info.size,
                                                   radius=[S(14)])
        self.top_info.bind(
            pos=lambda *a: setattr(self._top_info_rect, "pos", self.top_info.pos),
            size=lambda *a: setattr(self._top_info_rect, "size", self.top_info.size))

        # Avatar (grand : occupe toute la hauteur du bandeau, à gauche)
        self.top_avatar = PiecePhoto(photo="", size_hint=(None, 1), width=S(58))
        # Carré : remplit toute la hauteur du bandeau (largeur suit la hauteur).
        self.top_avatar.bind(height=lambda w, h: setattr(w, "width", h))
        self.top_info.add_widget(self.top_avatar)
        top_col = BoxLayout(orientation="vertical", size_hint=(1, 1), spacing=S(2))

        # Ligne 1 : nom + horloge + score
        top_row1 = BoxLayout(size_hint=(1, 0.5), spacing=S(6))
        self.top_name = Label(text=T("Joueur 2"), font_size=SF("16sp"), bold=True,
                              color=(0.05, 0.05, 0.05, 1),
                              size_hint=(0.42, 1),
                              halign="left", valign="middle", shorten=True)
        self.top_name.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        self.top_name.bind(on_touch_down=lambda lbl, t: self._on_name_click(lbl, "top", t))
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
        top_col.add_widget(top_row1)

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
        top_col.add_widget(top_row2)
        self.top_info.add_widget(top_col)
        stack.add_widget(self.top_info)

        # ── Emplacement du plateau (placeholder qui réserve la place) ──
        # Le vrai plateau (board_w) est ajouté à root APRÈS, par-dessus tout.
        self._board_slot = Widget(size_hint=(1, 0.66))
        stack.add_widget(self._board_slot)

        # ── Cadre info BAS (côté blanc) : miroir du haut ──
        # Ligne haut (près du plateau) : captures + abandon
        # Ligne bas : nom + horloge + score
        self.bot_info = BoxLayout(orientation="horizontal",
                                  size_hint=(1, 0.12),
                                  padding=(S(10), S(4)), spacing=S(8))
        with self.bot_info.canvas.before:
            self._bot_info_col = Color(*COL_BG_MENU)
            self._bot_info_rect = RoundedRectangle(pos=self.bot_info.pos,
                                                   size=self.bot_info.size,
                                                   radius=[S(14)])
        self.bot_info.bind(
            pos=lambda *a: setattr(self._bot_info_rect, "pos", self.bot_info.pos),
            size=lambda *a: setattr(self._bot_info_rect, "size", self.bot_info.size))

        # Avatar (grand : occupe toute la hauteur du bandeau, à gauche)
        self.bot_avatar = PiecePhoto(photo="", size_hint=(None, 1), width=S(58))
        self.bot_avatar.bind(height=lambda w, h: setattr(w, "width", h))
        self.bot_info.add_widget(self.bot_avatar)
        bot_col = BoxLayout(orientation="vertical", size_hint=(1, 1), spacing=S(2))

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
        bot_col.add_widget(bot_row1)

        # Ligne 2 : avatar + nom + horloge + score
        bot_row2 = BoxLayout(size_hint=(1, 0.5), spacing=S(6))
        self.bot_name = Label(text=T("Joueur 1"), font_size=SF("16sp"), bold=True,
                              color=(0.05, 0.05, 0.05, 1),
                              size_hint=(0.42, 1),
                              halign="left", valign="middle", shorten=True)
        self.bot_name.bind(size=lambda lbl, sz: setattr(lbl, "text_size", sz))
        self.bot_name.bind(on_touch_down=lambda lbl, t: self._on_name_click(lbl, "bot", t))
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
        bot_col.add_widget(bot_row2)
        self.bot_info.add_widget(bot_col)
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
        # Mettre à jour le BON mélo selon le mode de la partie (random ou standard).
        is_random = getattr(self, "current_random_code", None) is not None
        if is_random:
            ONLINE.melo_random = nouveau
        else:
            ONLINE.melo = nouveau
        try:
            save_online_session(ONLINE.token, ONLINE.pseudo, ONLINE.melo,
                                ONLINE.melo_random)
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
            title, body = T("Partie terminée"), ""
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
        title = pf[0] if pf else T("Match terminé")
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
                body = T("Score final\n%s : %d    %s : %d") % (bn, sb, nn, sn)
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
                    self._next_status_lbl.text = (T("L'adversaire est prêt !\n")
                        + T("Clique sur « Partie suivante »."))
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
        my_name = ONLINE.pseudo or T("Moi")
        if gagnant == my_name:
            titre = T("Match gagné")
            corps = (T("Votre adversaire n'a pas rejoint la partie suivante.\n")
                     + T("Vous remportez le match.\n\n(Aucun point Mélo : pas de partie en cours.)"))
        else:
            titre = T("Match terminé")
            corps = (T("Vous n'avez pas rejoint la partie suivante à temps.\n")
                     + T("Le match est perdu.\n\n(Aucun point Mélo : pas de partie en cours.)"))
        # Popup simple d'information puis retour menu
        c = BoxLayout(orientation="vertical", spacing=S(12), padding=S(16))
        lbl = Label(text=corps, color=(1, 1, 1, 1), halign="center",
                    valign="middle", font_size=SF("14sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        c.add_widget(lbl)
        ok = RoundButton(text=T("OK"), bg_color=COL_BLUE, color=(1, 1, 1, 1),
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
        self._dc_opp_name = self.online_opponent or T("Adversaire")
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
                    self.top_name.text = T("%s (déco %ds)") % (self._dc_opp_name,
                                                            self._dc_remaining)
                else:
                    self.top_name.text = T("%s (abandon…)") % self._dc_opp_name
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
        lbl = Label(text=T("%s propose la nulle.") % (self.online_opponent or T("L'adversaire")),
                    color=(1, 1, 1, 1), halign="center", valign="middle",
                    font_size=SF("15sp"))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        row = BoxLayout(orientation="horizontal", spacing=S(10), size_hint=(1, 0.4))
        acc = RoundButton(text=T("Accepter"), bg_color=COL_BLUE, color=(1, 1, 1, 1),
                          font_size=SF("14sp"), bold=True)
        ref = RoundButton(text=T("Refuser"), bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
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
        my_name = ONLINE.pseudo or T("Moi")
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
        my_name = ONLINE.pseudo or T("Moi")
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
            self.chat_btn.text = (T("Chat (%d)") % self._chat_unread
                                  if self._chat_unread > 0 else T("Chat"))
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
        proposeur = gd.get("nulle_proposeur") or self.corr_opponent or T("L'adversaire")
        content = BoxLayout(orientation="vertical", spacing=S(12), padding=S(16))
        lbl = Label(text=T("%s propose une partie nulle.") % proposeur,
                    font_size=SF("15sp"), color=(1, 1, 1, 1),
                    halign="center", valign="middle", size_hint=(1, 0.5))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        row = BoxLayout(orientation="horizontal", spacing=S(10),
                        size_hint=(1, 0.5))
        acc = RoundButton(text=T("Accepter"), bg_color=(0.20, 0.60, 0.25, 1),
                          color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True)
        ref = RoundButton(text=T("Refuser"), bg_color=COL_BTN_GREY,
                          color=(1, 1, 1, 1), font_size=SF("15sp"), bold=True)
        row.add_widget(acc)
        row.add_widget(ref)
        content.add_widget(row)
        popup = Popup(title=T("Proposition de nulle"), content=content,
                      size_hint=(0.82, 0.4), auto_dismiss=False)

        def _accept(*a):
            popup.dismiss()
            def _done(result, err):
                if err or not (result and result.get("ok")):
                    self._popup_simple(T("Nulle"), err or T("Échec."))
                    return
                # La partie est désormais nulle côté serveur.
                self._game_over = True
                self._popup_finish(T("Partie nulle"),
                                   T("Vous avez accepté la nulle."), None)
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
        lbl = Label(text=T("Jouer contre Deep Grey depuis cette position.\n")
                         + T("Choisissez votre camp :"),
                    font_size=SF("15sp"), color=(0.1, 0.1, 0.1, 1),
                    halign="center", valign="middle", size_hint=(1, None),
                    height=S(60))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(lbl)
        popup = Popup(title="Deep Grey", content=content, size_hint=(0.8, 0.42))
        row = BoxLayout(orientation="horizontal", spacing=S(12),
                        size_hint=(1, None), height=S(56))
        b_blanc = RoundButton(text=T("Blancs"), font_size=SF("16sp"), bold=True,
                              bg_color=(0.92, 0.92, 0.92, 1), color=(0, 0, 0, 1))
        b_noir = RoundButton(text=T("Noirs"), font_size=SF("16sp"), bold=True,
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
        #    choisi Blanc, c'est lui (T("Joueur 1")) ; sinon c'est deep grey.
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
                self.chat_btn.text = T("Chat (%d)") % self._chat_unread
        # Rafraîchir la fenêtre de chat si elle est ouverte
        if getattr(self, "_chat_open", False) and hasattr(self, "_chat_log_box"):
            self._refresh_chat_log()

    def _refresh_chat_log(self):
        """Reconstruit la liste des messages dans la fenêtre de chat."""
        if not hasattr(self, "_chat_log_box"):
            return
        self._chat_log_box.clear_widgets()
        for auteur, texte in getattr(self, "_chat_messages", []):
            is_me = (auteur == (ONLINE.pseudo or T("Moi")))
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
        auteur = (data or {}).get("auteur", self.online_opponent or T("Adversaire"))
        texte = (data or {}).get("texte", "")
        if texte:
            self._add_chat_message(auteur, texte)

    def _is_real_player(self, pseudo):
        """True si le pseudo est un VRAI joueur en ligne (pas un placeholder local
        'Joueur 1/2', pas l'IA Deep Grey)."""
        if not pseudo:
            return False
        ph = {"Joueur 1", "Joueur 2", T("Joueur 1"), T("Joueur 2"),
              "deep grey", "Deep Grey", "IA", T("IA")}
        return pseudo not in ph

    def _refresh_avatars(self):
        """Met à jour les deux vignettes avatar selon les joueurs affichés."""
        if not hasattr(self, "top_avatar"):
            return
        self._set_one_avatar(self.top_avatar, getattr(self, "_top_pseudo", ""))
        self._set_one_avatar(self.bot_avatar, getattr(self, "_bot_pseudo", ""))

    def _set_one_avatar(self, avatar, pseudo):
        p = pseudo if isinstance(pseudo, str) else ""
        pl = p.strip().lower()
        if pl in ("deep grey", "deepgrey"):
            avatar.set_photo(DEEPGREY_PHOTO)
            return
        # Est-ce MOI ? En ligne : mon pseudo. Contre l'IA : le côté qui n'est pas
        # Deep Grey (donc l'humain = moi si je suis connecté).
        is_me = False
        if ONLINE.is_logged_in():
            if p == ONLINE.pseudo:
                is_me = True
            elif getattr(self, "vs_ai", False) and not self._is_real_player(p):
                is_me = True
        if is_me:
            def on_ready(photo, av=avatar):
                try:
                    av.set_photo(avatar_photo_for(ONLINE.pseudo, photo))
                except Exception:
                    pass
            photo = resolve_avatar_photo(ONLINE.pseudo, on_ready=on_ready)
            avatar.set_photo(avatar_photo_for(ONLINE.pseudo, photo))
            return
        if not p or not self._is_real_player(p):
            avatar.set_photo("")   # placeholder local -> logo par défaut
            return
        def on_ready2(photo, av=avatar, ps=p):
            try:
                av.set_photo(avatar_photo_for(ps, photo))
            except Exception:
                pass
        photo = resolve_avatar_photo(p, on_ready=on_ready2)
        avatar.set_photo(avatar_photo_for(p, photo))

    def _on_name_click(self, label, which, touch):
        """Clic sur un nom -> menu déroulant (Profil / Favori / Bloquer / Message)."""
        try:
            if not label.collide_point(*touch.pos):
                return False
        except Exception:
            return False
        pseudo = self._top_pseudo if which == "top" else self._bot_pseudo
        pseudo = pseudo if isinstance(pseudo, str) else ""
        if not self._is_real_player(pseudo):
            return False
        self._show_name_menu(pseudo)
        return True

    def _show_name_menu(self, pseudo):
        """Petit menu déroulant sur un nom de joueur."""
        if not ONLINE.is_logged_in():
            return
        is_me = (pseudo == (ONLINE.pseudo or ""))
        content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(14))
        content.add_widget(Label(text="[b]%s[/b]" % pseudo, markup=True,
                                 font_size=SF("18sp"), color=(1, 1, 1, 1),
                                 size_hint=(1, None), height=S(32)))
        pop = Popup(title="", content=content, size_hint=(0.8, None),
                    height=S(120 + 58 * (1 if is_me else 4) + 46),
                    separator_height=0)

        def mk(txt, cb, bg=COL_BTN_GREY):
            b = RoundButton(text=txt, bg_color=bg, color=(1, 1, 1, 1),
                            font_size=SF("14sp"), bold=True,
                            size_hint=(1, None), height=S(48))
            b.bind(on_release=lambda *a: (pop.dismiss(), cb()))
            content.add_widget(b)

        mk(T("Profil"), lambda: self._name_profile(pseudo))
        if not is_me:
            mk(T("Favori"), lambda: self._name_favorite(pseudo))
            mk(T("Message"), lambda: self._name_message(pseudo))
            mk(T("Bloquer"), lambda: self._name_block(pseudo), bg=(0.72, 0.26, 0.26, 1))
        close = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
                            color=(1, 1, 1, 1), font_size=SF("12sp"),
                            size_hint=(1, None), height=S(40))
        close.bind(on_release=lambda *a: pop.dismiss())
        content.add_widget(close)
        pop.open()

    def _gs_popup(self, title, message):
        """Petit popup d'information (GameScreen)."""
        c = BoxLayout(orientation="vertical", padding=S(16), spacing=S(10))
        lbl = Label(text=message, color=(1, 1, 1, 1), font_size=SF("14sp"),
                    halign="center", valign="middle")
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        c.add_widget(lbl)
        p = Popup(title=title, content=c, size_hint=(0.82, 0.35))
        btn = RoundButton(text=T("OK"), bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                          font_size=SF("14sp"), bold=True,
                          size_hint=(1, None), height=S(44))
        btn.bind(on_release=lambda *a: p.dismiss())
        c.add_widget(btn)
        p.open()

    def _name_profile(self, pseudo):
        try:
            scr = self.manager.get_screen("account")
            scr.target_pseudo = None if pseudo == (ONLINE.pseudo or "") else pseudo
            self.manager.current = "account"
        except Exception:
            pass

    def _name_favorite(self, pseudo):
        ONLINE.add_favorite(pseudo, lambda ok, e: self._gs_popup(
            T("Favori"), T("%s ajouté aux favoris.") % pseudo if ok
            else T("Erreur : %s") % e))

    def _name_block(self, pseudo):
        def on_done(ok, err):
            if ok:
                if not self.replay_mode:
                    msg = (T("%s bloqué. La partie en cours continue ; le blocage "
                             "prendra effet à la fin.") % pseudo)
                else:
                    msg = T("%s bloqué.") % pseudo
                self._gs_popup(T("Blocage"), msg)
            else:
                self._gs_popup(T("Blocage"), T("Erreur : %s") % err)
        ONLINE.block_user(pseudo, on_done)

    def _name_message(self, pseudo):
        # La messagerie unifiée arrive au chantier suivant ; on ouvre la
        # conversation dédiée dès qu'elle existe.
        self._open_conversation(pseudo)

    def _open_conversation(self, pseudo):
        """Ouvre la boîte de messages UNIFIÉE avec un joueur (la même partout)."""
        if not pseudo or not self._is_real_player(pseudo):
            return
        try:
            conv = self.manager.get_screen("conversation")
            conv.target_pseudo = pseudo
            conv.return_screen = self.manager.current
            self.manager.current = "conversation"
        except Exception:
            pass

    def _set_chat_badge(self, count):
        """Affiche une pastille de messages non lus sur le bouton chat en partie."""
        try:
            if hasattr(self, "chat_btn"):
                self.chat_btn.text = (T("Chat (%d)") % count
                                      if count and count > 0 else T("Chat"))
        except Exception:
            pass

    def _open_chat(self):
        """Ouvre la boîte de messages UNIFIÉE avec l'adversaire : LA MÊME
        conversation partout (parties directes, correspondance, hors partie)."""
        if not (getattr(self, "online_mode", False)
                or getattr(self, "corr_mode", False)):
            return
        # Adversaire = le joueur affiché qui n'est pas moi
        me = ONLINE.pseudo or ""
        opp = None
        for p in (getattr(self, "_top_pseudo", None),
                  getattr(self, "_bot_pseudo", None)):
            if isinstance(p, str) and p and p != me and self._is_real_player(p):
                opp = p
                break
        if not opp:
            return
        self._chat_open = True
        self._chat_unread = 0
        if hasattr(self, "chat_btn"):
            self.chat_btn.text = T("Chat")
        self._open_conversation(opp)
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
        # Restaurer le snapshot de la position où on était quand on a cliqué T("Analyser")
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
        # Nouvelle partie : cacher le bouton "Menu" du bandeau (réservé à la fin).
        if hasattr(self, "menu_btn"):
            self._hide_menu_button()
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
            self.chat_btn.text = T("Chat")
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

    def _reconstruct_jump_path(self, start, end, board_before):
        """Reconstruit le chemin d'un MULTISAUT (une pièce ronde sautant par-dessus
        des rondes) avec le MOINS de sauts possible, entre start et end, à partir
        du plateau AVANT le coup. Renvoie la liste des cases d'atterrissage
        INTERMÉDIAIRES (sans le départ ni l'arrivée) pour les afficher en petits
        points. Renvoie [] si ce n'est pas un multisaut (déplacement simple, saut
        unique, ou chemin introuvable). Si plusieurs chemins sont aussi courts,
        on en renvoie un seul (peu importe lequel)."""
        if start is None or end is None or board_before is None:
            return []
        sc, sr = start
        if not _dg_on_board(sc, sr):
            return []
        mover = board_before[sc][sr]
        if not _dg_is_round(mover):
            return []   # seules les pièces rondes enchaînent des sauts
        # Plateau d'obstacles = plateau avant le coup, sans le sauteur lui-même
        obst = _dg_clone(board_before)
        obst[sc][sr] = None
        from collections import deque
        q = deque([(sc, sr, (start,))])
        seen = {start}
        best = None
        while q:
            cc, cr, path = q.popleft()
            if (cc, cr) == end:
                best = path
                break
            for dc in (-1, 0, 1):
                for dr in (-1, 0, 1):
                    if dc == 0 and dr == 0:
                        continue
                    mc, mr = cc + dc, cr + dr          # case sautée
                    nc, nr = cc + 2 * dc, cr + 2 * dr  # case d'atterrissage
                    if not (_dg_on_board(mc, mr) and _dg_on_board(nc, nr)):
                        continue
                    if not _dg_is_round(obst[mc][mr]):
                        continue   # on ne saute QUE par-dessus une pièce ronde
                    if (nc, nr) != end and obst[nc][nr] is not None:
                        continue   # atterrissage intermédiaire doit être vide
                    if (nc, nr) in seen:
                        continue
                    seen.add((nc, nr))
                    q.append((nc, nr, path + ((nc, nr),)))
        # best est None (introuvable) ou un tuple de cases. 2 cases = saut unique.
        if not best or len(best) < 3:
            return []
        return list(best[1:-1])   # on retire départ et arrivée

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

        # Chemin d'un multisaut : petits points intermédiaires (pas pour les
        # poussées, qui contiennent ">"). Renvoie [] si ce n'est pas un multisaut.
        if end is not None and ">" not in n:
            result["jump_path"] = self._reconstruct_jump_path(
                start, end, board_before)

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
        title = T("Match nul par répétition")
        players = self._players()
        pA, pB = players[0], players[1]
        body  = (T("La même position s'est répétée 4 fois.\n\n")
                 + f"{pA} : {self.scores[pA]}    "
                 + f"{pB} : {self.scores[pB]}")
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
        self.ai_mode_btn.text = T("Profond") if deep else T("Rapide")

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
            # Mélo du mode de CETTE partie (random ou standard).
            _is_rnd = getattr(self, "current_random_code", None) is not None
            my_melo = ONLINE.melo_random if _is_rnd else ONLINE.melo
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
        # Mémoriser les pseudos réels de chaque côté (pour le menu sur les noms).
        self._top_pseudo = ptop
        self._bot_pseudo = pbot
        # Mettre à jour les avatars (Deep Grey a son image ; joueurs réels leur
        # pièce ; placeholders locaux une pièce par défaut).
        self._refresh_avatars()
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
                    # Le coup de mat (éjection de l'Héritier) doit être ENREGISTRÉ
                    # avant la fin, sinon il manque dans l'historique/replay. On
                    # marque donc le mat et on laisse _end_turn enregistrer le coup
                    # PUIS terminer la partie — en local, en ligne ET en
                    # correspondance. Seul un coup DISTANT (déjà enregistré par la
                    # logique d'application distante) termine immédiatement.
                    if getattr(self, "_applying_remote", False):
                        self._end_game_by_color(loser_color=loser, method="mat")
                        return
                    else:
                        self._mat_pending = loser
                        self._move_had_ejection = True
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
        mover = self.turn   # le joueur qui vient de jouer ce coup
        self.sel       = None
        self.group_sel = set()
        self.moved     = False
        self.push_on   = False
        self.jumping   = False
        if mover == "Noir":
            # Noir a fait fuguer l'Héritier BLANC sur SON propre tour (il a poussé
            # l'Héritier adverse dans son ralliement) : Blanc gagne TOUT DE SUITE,
            # sans tour de rattrapage (Noir a déjà joué).
            self.turn = "Blanc"
            if notation is not None:
                if getattr(self, "corr_mode", False):
                    self._corr_pending_method = "fugue"
                self._record_move(notation, push_targets=captured_push_targets)
            self._end_game_by_color(loser_color="Noir", method="fugue")
            return
        # Cas normal : Blanc a fugué son propre Héritier → Noir a un tour de
        # rattrapage (il peut fuguer aussi pour une nulle).
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
        mover = self.turn   # le joueur qui vient de jouer ce coup
        self.sel       = None
        self.group_sel = set()
        self.moved     = False
        self.push_on   = False
        self.jumping   = False
        if mover == "Blanc" and not self.blanc_fugued:
            # Blanc a fait fuguer l'Héritier NOIR sur SON propre tour (il a poussé
            # l'Héritier adverse dans son ralliement) : Noir gagne TOUT DE SUITE,
            # sans tour de rattrapage (Blanc a déjà joué). Symétrique de _fugue_blanc.
            self.turn = "Blanc"
            if notation is not None:
                if getattr(self, "corr_mode", False):
                    self._corr_pending_method = "fugue"
                self._record_move(notation, push_targets=captured_push_targets)
            self._end_game_by_color(loser_color="Blanc", method="fugue")
            return
        # Le tour bascule à Blanc pour le snapshot (fin de partie)
        self.turn = "Blanc"
        if notation is not None:
            if getattr(self, "corr_mode", False):
                self._corr_pending_method = "nulle" if self.blanc_fugued else "fugue"
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
                        T("Nulle proposée"),
                        T("Proposition de nulle envoyée.\nVotre adversaire la verra en ouvrant la partie."))
                else:
                    self._popup_simple(T("Nulle"), err or T("Échec de la proposition."))
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
            Popup(title=T("Nulle proposée"),
                  content=Label(text=T("Proposition de nulle envoyée\nà votre adversaire."),
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
            title = T("Partie nulle")
            if method == "nulle_accord":
                body = T("Nulle par accord mutuel.\nAucun point accordé.")
            elif method == "nulle_pat":
                body = (T("Trêve : plus aucune pièce carrée ne peut bouger.\n") +
                        T("Aucun point accordé."))
            else:
                body = T("Les deux Héritiers ont fugué.\nAucun point accordé.")
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
            verbe = {"fugue":  T("fugue"),
                     "mat":    T("mat"),
                     "temps":  T("temps écoulé"),
                     "abandon": T("abandon"),
                     "papatte": T("papatte (adversaire bloqué)")}[method]
            title = T("{winner} gagne la partie").format(winner=_disp_player(winner_player))
            players = self._players()
            pA, pB = players[0], players[1]
            body  = (T("Victoire par {v} (+{pts} pt)").format(v=verbe, pts=pts)
                     + "\n\n"
                     + f"{_disp_player(pA)} : {self.scores[pA]}    "
                     + f"{_disp_player(pB)} : {self.scores[pB]}")

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
            # CLASSEMENT / SYNCHRO : si CONNECTÉ, TOUTES les parties (en ligne ET
            # locales) vont au serveur pour être synchronisées entre appareils.
            # L'identifiant (préfixe "online_" / "local_") distingue les deux
            # historiques. Si NON connecté, la partie locale va dans un .nmc local.
            if ONLINE.is_logged_in():
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
                # Pas connecté : partie locale / vs IA → fichier .nmc local
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
        # Orienter le plateau du POINT DE VUE du joueur connecté (lui en bas).
        # load_replay ne le faisait pas : le plateau gardait alors une orientation
        # résiduelle, ce qui pouvait inverser les noms/côtés. Si mon pseudo est le
        # joueur des Noirs -> Noirs en bas (flipped=False) ; sinon (je suis les
        # Blancs, ou partie locale sans pseudo) -> Blancs en bas (flipped=True).
        _my_pseudo = getattr(ONLINE, "pseudo", "") or ""
        _noir_player = self._other_player(blanc_player)
        self.flipped = not (_my_pseudo and _my_pseudo == _noir_player)
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

    def _reveal_menu_button(self):
        """Affiche le bouton 'Retour au menu' du bandeau (partie terminée)."""
        try:
            self.menu_btn.width = S(155)
            self.menu_btn.opacity = 1
            self.menu_btn.disabled = False
        except Exception:
            pass

    def _hide_menu_button(self):
        """Cache le bouton 'Menu' du bandeau (partie en cours)."""
        try:
            self.menu_btn.width = 0
            self.menu_btn.opacity = 0
            self.menu_btn.disabled = True
        except Exception:
            pass

    def _decide_next(self, title, body, winner_player):
        # La partie est terminée : afficher le bouton "Menu" du bandeau, pour
        # pouvoir revenir au menu même après avoir fermé le popup de fin.
        self._reveal_menu_button()
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
        # (match_continue → popup T("Partie suivante"), ou match_over → popup final).
        if getattr(self, "online_mode", False):
            self._pending_finish = (title, body, winner_player)
            return

        # Mode "Partie" : on s'arrête après une seule partie
        if self.target == "partie":
            self._popup_finish(title, body, winner_player=winner_player)
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
                self._popup_finish(T("Match nul !"),
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
            self._popup_continue(
                title + T("  •  Ultime partie pour {loser}").format(loser=loser),
                body, next_first_blanc=loser)
            return

        self._popup_finish(title, body, winner_player=leader)

    def _first_blanc_of_round1(self):
        players = self._players()
        pA, pB = players[0], players[1]
        return pA if self.played_blanc[pA] >= self.played_blanc[pB] else pB

    def _popup_continue(self, title, body, next_first_blanc):
        # EN LIGNE : le bouton T("Partie suivante") ne relance pas localement. Il
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
        info = Label(text=T("Prochaine partie : {name} joue les Blancs").format(name=_disp_player(next_first_blanc)),
                     font_size=SF("12sp"), italic=True,
                     color=(0.8, 0.8, 0.8, 1),
                     size_hint=(1, None), height=S(24))
        content.add_widget(info)
        btn = RoundButton(text=T("Partie suivante"), bg_color=COL_ORANGE,
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
            text=T("Clique sur « Partie suivante » pour continuer le match."),
            font_size=SF("12sp"), italic=True, color=(0.85, 0.85, 0.85, 1),
            size_hint=(1, None), height=S(40), halign="center")
        self._next_status_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        content.add_widget(self._next_status_lbl)
        btn = RoundButton(text=T("Partie suivante"), bg_color=COL_ORANGE,
                          color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                          size_hint=(1, None), height=S(50))
        content.add_widget(btn)
        quit_btn = RoundButton(text=T("Quitter le match"), bg_color=COL_BTN_GREY,
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
            btn.text = T("En attente de l'adversaire…")
            btn.disabled = True
            try:
                ONLINE.sio_emit("pret_partie_suivante",
                                {"game_id": self.online_game_id})
            except Exception:
                pass
            # Démarrer un compte à rebours d'1 min (affichage informatif côté
            # joueur prêt : c'est l'adversaire qui risque l'abandon).
            self._next_remaining = 60
            self._next_status_lbl.text = (T("En attente de l'adversaire…  (%ds)")
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
                    self._next_status_lbl.text = (T("En attente de l'adversaire…  (%ds)")
                                                  % self._next_remaining)
                else:
                    self._next_status_lbl.text = T("Temps écoulé…")
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
        # Partie/match terminé : révéler le bouton "Retour au menu" du bandeau.
        # ESSENTIEL : ce popup est auto-dismiss (on peut le fermer en tapant à
        # côté pour regarder la position finale). Le bouton du bandeau reste alors
        # le seul moyen de revenir au menu — il doit donc être là, indépendamment
        # du popup.
        self._reveal_menu_button()
        content = BoxLayout(orientation="vertical", spacing=10, padding=10)
        content.add_widget(Label(text=body, font_size=SF("14sp"), color=(1, 1, 1, 1)))
        if winner_player:
            big = Label(text=T("Victoire de {name} !").format(name=_disp_player(winner_player)),
                        font_size=SF("18sp"), bold=True,
                        color=COL_ORANGE,
                        size_hint=(1, None), height=S(40))
        else:
            big = Label(text=T("Match nul"),
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
                melo_lbl = Label(text=T("Mélo : %d  (%s%d)") % (melo_val, sign, delta),
                                 font_size=SF("15sp"), bold=True, color=dcol,
                                 size_hint=(1, None), height=S(34))
                content.add_widget(melo_lbl)
            else:
                # Le mélo peut arriver juste après : message d'attente neutre
                wait_lbl = Label(text=T("Mise à jour du mélo…"),
                                 font_size=SF("13sp"), italic=True,
                                 color=(0.6, 0.6, 0.6, 1),
                                 size_hint=(1, None), height=S(28))
                content.add_widget(wait_lbl)
        btn = RoundButton(text=T("Retour au menu"), bg_color=COL_BLUE,
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
            lbl = Label(text=T("Connectez-vous à un compte\npour voir vos parties en ligne."),
                        color=(1, 1, 1, 1), halign="center", valign="middle",
                        font_size=SF("15sp"))
            lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            content.add_widget(lbl)
            btn = RoundButton(text=T("OK"), bg_color=COL_BLUE, color=(1, 1, 1, 1),
                              font_size=SF("15sp"), bold=True, size_hint=(1, 0.4))
            content.add_widget(btn)
            p = Popup(title="", content=content, size_hint=(0.8, 0.4),
                      separator_height=0)
            btn.bind(on_release=lambda *a: p.dismiss())
            p.open()
            return
        try:
            scr = self.manager.get_screen("history_online")
            scr._return_screen = "parties_menu"; scr._return_pseudo = None
        except Exception:
            pass
        self.manager.current = "history_online"

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        header = BoxLayout(size_hint=(1, 0.08), padding=(S(8), S(6)))
        back = RoundButton(text=T("< Menu"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        title = Label(text=T("Historique"), font_size=SF("32sp"), italic=True,
                      color=(0, 0, 0, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(110)))
        root.add_widget(header)

        body = FloatLayout()

        b_online = RoundButton(text=T("Historique en ligne"), font_size=SF("17sp"), bold=True,
                               bg_color=COL_BLUE, color=(1, 1, 1, 1),
                               size_hint=(0.8, 0.1),
                               pos_hint={"center_x": 0.5, "top": 0.85})
        b_online.bind(on_release=lambda *a: self._open_online_history())
        body.add_widget(b_online)
        self._b_online = b_online

        b_local = RoundButton(text=T("Historique en local"), font_size=SF("17sp"), bold=True,
                              bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                              size_hint=(0.8, 0.1),
                              pos_hint={"center_x": 0.5, "top": 0.70})
        def _open_local_hist(*a):
            try:
                scr = self.manager.get_screen("history_local")
                scr._return_screen = "parties_menu"; scr._return_pseudo = None
            except Exception:
                pass
            self.manager.current = "history_local"
        b_local.bind(on_release=_open_local_hist)
        body.add_widget(b_local)
        self._b_local = b_local

        b_reader = RoundButton(text=T("Lecteur nmc"), font_size=SF("17sp"), bold=True,
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


# ── Écran T("Historique en ligne") (placeholder) ───────────────────────────────

def open_account_party(screen, game_uid):
    """Récupère le .nmc d'une partie du compte (serveur) puis l'ouvre en lecture."""
    def on_nmc(nmc_text, err):
        if err or not nmc_text:
            Popup(title=T("Erreur"),
                  content=Label(text=T("Impossible de charger la partie."),
                                color=(1, 1, 1, 1)),
                  size_hint=(0.7, 0.3)).open()
            return
        meta, moves = parse_nmc_content(nmc_text)
        if not meta:
            return
        g = screen.manager.get_screen("game")
        if g.load_replay(meta, moves):
            screen.manager.current = "game"
    ONLINE.get_account_game(game_uid, on_nmc)


def render_account_entry(screen, g):
    """Ajoute dans screen.list_box une ligne d'historique pour une partie DU
    COMPTE (métadonnées serveur). Le .nmc complet est récupéré au tap. Partagé
    entre l'historique en ligne et l'historique local (parties synchronisées)."""
    method = g.get("methode", "?")
    result = g.get("resultat", "?")
    date = ""
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
        cad_str = T("Corresp")
    elif cadence == "zen":
        cad_str = T("Zen")
    elif cadence in ("?", None, ""):
        cad_str = "?"
    else:
        cad_str = f"{cadence}min"
    player1 = g.get("joueur1", "Joueur 1")
    player2 = g.get("joueur2", "Joueur 2")
    game_uid = g.get("game_uid", "")

    my_pseudo = getattr(ONLINE, "pseudo", "") or ""
    if result not in ("1-0", "0-1"):
        sym_col = (0.75, 0.75, 0.75, 1); sym = "\u00bd"
    else:
        if my_pseudo and my_pseudo == player2:
            i_won = (result == "0-1")
        else:
            i_won = (result == "1-0")
        sym_col = (0.30, 0.85, 0.30, 1) if i_won else (1.0, 0.33, 0.33, 1)
        sym = "#"

    wrap = BoxLayout(orientation="horizontal", size_hint=(1, None),
                     height=S(90), spacing=S(8))
    row = ClickableRow(on_press_cb=lambda u=game_uid: open_account_party(screen, u),
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
    # Ligne des noms encadrée par les deux avatars (Deep Grey a son image dédiée,
    # les joueurs réels leur pièce ; photos fournies par le serveur).
    names_row = BoxLayout(orientation="horizontal", size_hint=(1, 0.4), spacing=S(4))
    av1 = PiecePhoto(photo="", size_hint=(None, 1), width=S(22))
    _p1 = resolve_avatar_photo(
        player1,
        on_ready=lambda ph, w=av1, ps=player1: w.set_photo(avatar_photo_for(ps, ph)))
    av1.set_photo(avatar_photo_for(player1, _p1 or g.get("joueur1_photo", "")))
    names_lbl = Label(text=f"{player1}  vs  {player2}", font_size=SF("14sp"),
                      bold=True, color=(1, 1, 1, 1), size_hint=(1, 1),
                      halign="left", valign="middle", shorten=True)
    names_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    av2 = PiecePhoto(photo="", size_hint=(None, 1), width=S(22))
    _p2 = resolve_avatar_photo(
        player2,
        on_ready=lambda ph, w=av2, ps=player2: w.set_photo(avatar_photo_for(ps, ph)))
    av2.set_photo(avatar_photo_for(player2, _p2 or g.get("joueur2_photo", "")))
    names_row.add_widget(av1)
    names_row.add_widget(names_lbl)
    names_row.add_widget(av2)
    date_lbl = Label(text=date, font_size=SF("11sp"), color=(0.85, 0.85, 0.85, 1),
                     size_hint=(1, 0.3), halign="left", valign="middle")
    date_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    info_lbl = Label(text=f"{cad_str}  \u2022  {verbe}", font_size=SF("11sp"),
                     italic=True, color=(0.85, 0.85, 0.85, 1),
                     size_hint=(1, 0.3), halign="left", valign="middle")
    info_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    txt_box.add_widget(names_row)
    txt_box.add_widget(date_lbl)
    txt_box.add_widget(info_lbl)
    row.add_widget(txt_box)
    wrap.add_widget(row)
    screen.list_box.add_widget(wrap)


def _history_go_back(screen):
    """Retour depuis un écran d'historique : vers le PROFIL si on y est venu depuis
    un profil, sinon vers le menu des parties."""
    sm = screen.manager
    if sm is None:
        return
    if getattr(screen, "_return_screen", "parties_menu") == "account":
        try:
            sm.get_screen("account").target_pseudo = getattr(screen, "_return_pseudo", None)
        except Exception:
            pass
        sm.current = "account"
    else:
        sm.current = "parties_menu"


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
        back = RoundButton(text=T("< Historique"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a, s=self: _history_go_back(s))
        title = Label(text=T("En ligne"), font_size=SF("28sp"), italic=True,
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
        # Cible : None = mon historique ; sinon celui d'un autre joueur (profil).
        target = getattr(self, "target_pseudo", None)
        self.target_pseudo = None   # consommé une seule fois
        if not ONLINE.is_logged_in():
            msg = Label(text=T("Connectez-vous pour voir vos parties en ligne."),
                        font_size=SF("15sp"), color=(0.3, 0.3, 0.3, 1), italic=True,
                        size_hint=(1, None), height=S(80), halign="center")
            msg.bind(size=lambda w, s: setattr(w, "text_size", (s[0], None)))
            self.list_box.add_widget(msg)
            return
        loading = Label(text=T("Chargement des parties en ligne…"),
                        font_size=SF("14sp"), color=(0.3, 0.3, 0.3, 1),
                        italic=True, size_hint=(1, None), height=S(80),
                        halign="center")
        self.list_box.add_widget(loading)

        def on_games(games, err):
            self.list_box.clear_widgets()
            if err:
                self.list_box.add_widget(Label(
                    text=T("Impossible de charger l'historique\n(%s)") % err,
                    font_size=SF("14sp"), color=(0.6, 0.2, 0.2, 1), italic=True,
                    size_hint=(1, None), height=S(80), halign="center"))
                return
            games = [g for g in (games or [])
                     if str(g.get("game_uid", "")).startswith("online_")]
            if not games:
                self.list_box.add_widget(Label(
                    text=T("Aucune partie en ligne.\nJouez une partie en ligne pour la voir ici !"),
                    font_size=SF("15sp"), color=(0.3, 0.3, 0.3, 1), italic=True,
                    size_hint=(1, None), height=S(80), halign="center"))
                return
            for g in games:
                render_account_entry(self, g)
        ONLINE.list_games(target, on_games)


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
        back = RoundButton(text=T("< Historique"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a, s=self: _history_go_back(s))
        title = Label(text=T("En local"), font_size=SF("28sp"), italic=True,
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
        target = getattr(self, "target_pseudo", None)
        self.target_pseudo = None   # consommé une seule fois
        # CONNECTÉ : les parties LOCALES du compte (préfixe local_) viennent du
        # SERVEUR (synchronisées entre appareils). NON connecté : fichiers .nmc.
        if ONLINE.is_logged_in():
            loading = Label(text=T("Chargement…"), font_size=SF("14sp"),
                            color=(0.3, 0.3, 0.3, 1), italic=True,
                            size_hint=(1, None), height=S(80), halign="center")
            self.list_box.add_widget(loading)

            def on_games(games, err):
                self.list_box.clear_widgets()
                if err:
                    self.list_box.add_widget(Label(
                        text=T("Impossible de charger l'historique\n(%s)") % err,
                        font_size=SF("14sp"), color=(0.6, 0.2, 0.2, 1), italic=True,
                        size_hint=(1, None), height=S(80), halign="center"))
                    return
                games = [g for g in (games or [])
                         if str(g.get("game_uid", "")).startswith("local_")]
                if not games:
                    self.list_box.add_widget(Label(
                        text=T("Aucune partie locale.\nJouez en local ou contre l'IA pour la voir ici !"),
                        font_size=SF("15sp"), color=(0.3, 0.3, 0.3, 1), italic=True,
                        size_hint=(1, None), height=S(80), halign="center"))
                    return
                for g in games:
                    render_account_entry(self, g)
            ONLINE.list_games(target, on_games)
            return

        # NON connecté : fichiers .nmc locaux de l'appareil
        files = list_local_parties()
        if not files:
            empty = Label(text=T("Aucune partie locale.\nJouez en local ou contre l'IA pour la voir ici !"),
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
            cad_str = T("Corresp")
        elif cadence == "zen":
            cad_str = T("Zen")
        elif cadence in ("?", None, ""):
            cad_str = "?"
        else:
            cad_str = f"{cadence}min"
        player1 = g.get("joueur1", "Joueur 1")
        player2 = g.get("joueur2", "Joueur 2")
        game_uid = g.get("game_uid", "")

        # Symbole de résultat DU POINT DE VUE DU JOUEUR CONNECTÉ : vert = gagné,
        # rouge = perdu, gris = nulle. joueur1 = Blancs, joueur2 = Noirs ;
        # "1-0" = Blancs gagnent, "0-1" = Noirs gagnent.
        my_pseudo = getattr(ONLINE, "pseudo", "") or ""
        if result not in ("1-0", "0-1"):
            sym_col = (0.75, 0.75, 0.75, 1); sym = "½"
        else:
            if my_pseudo and my_pseudo == player2:
                i_won = (result == "0-1")      # je suis les Noirs
            else:
                i_won = (result == "1-0")      # je suis les Blancs (ou inconnu)
            sym_col = (0.30, 0.85, 0.30, 1) if i_won else (1.0, 0.33, 0.33, 1)
            sym = "#"

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
                Popup(title=T("Erreur"),
                      content=Label(text=T("Impossible de charger la partie."),
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

        cad_str = f"{cadence}min" if cadence != "zen" else T("Zen")
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
        b_copy = RoundButton(text=T("Copier"), font_size=SF("11sp"), bold=True,
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
        content_box.add_widget(Label(text=T("Sélectionnez tout le texte ci-dessous,\npuis copiez-le."),
                                     font_size=SF("13sp"), color=(1, 1, 1, 1),
                                     size_hint=(1, None), height=S(40), halign="center"))
        ti = TextInput(text=content, multiline=True, readonly=False,
                       font_size=SF("13sp"), size_hint=(1, 1))
        content_box.add_widget(ti)
        close_btn = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
                                color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                                size_hint=(1, None), height=S(44))
        content_box.add_widget(close_btn)
        p = Popup(title=T("Contenu .nmc"), content=content_box,
                  size_hint=(0.95, 0.85), auto_dismiss=True)
        close_btn.bind(on_release=lambda *a: p.dismiss())
        p.open()

    def _share_nmc(self, filepath):
        """Tente d'utiliser le partage natif Android via plyer. Sinon affiche un popup."""
        try:
            from plyer import share
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            share.share(title=T("Partie La Fuga"), text=content)
        except Exception:
            # Fallback : ouvre la popup de copie
            self._copy_nmc(filepath)

    def _show_error(self):
        p = Popup(title=T("Erreur"),
                  content=Label(text=T("désolé, le fichier nmc est invalide,\nla lecture ne peut pas s effectuer"),
                                color=(1, 1, 1, 1), font_size=SF("13sp")),
                  size_hint=(0.85, 0.3))
        p.open()


# OnlineHistoryScreen réutilise la présentation/ouverture des parties du compte
# définies dans HistoryScreen (assigné ici car HistoryScreen est défini après).
OnlineHistoryScreen._add_account_entry = HistoryScreen._add_account_entry
OnlineHistoryScreen._open_account_party = HistoryScreen._open_account_party


# ── Écran Lecteur nmc ──────────────────────────────────────────────────────

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
        back = RoundButton(text=T("< Historique"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(110))
        back.bind(on_release=lambda *a, s=self: _history_go_back(s))
        title = Label(text=T("Lecteur nmc"), font_size=SF("26sp"), italic=True,
                      color=(0, 0, 0, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(110)))
        root.add_widget(header)

        # Zone de saisie
        from kivy.uix.textinput import TextInput
        instruct = Label(text=T("Collez le contenu d'un fichier .nmc ci-dessous :"),
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
        play_btn = RoundButton(text=T("Lire"), bg_color=COL_ORANGE,
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
                  content=Label(text=T("désolé, le fichier nmc est invalide,\nla lecture ne peut pas s effectuer"),
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
                                  board_col=t["board"], theme=self.theme_name)


def draw_piece_themed(canvas, x, y, sz, piece, accent_clair, accent_fonce, board_col=None, theme=None):
    """Comme draw_piece mais avec des accents de couleur fournis (pour l'aperçu).
    'theme' est transmis en preview_theme pour que les rendus spéciaux (deepgrey)
    s'appliquent au bon thème, indépendamment du thème courant."""
    global COL_ORANGE, COL_BLUE, COL_BG_BOARD
    save_o, save_b, save_bg = COL_ORANGE, COL_BLUE, COL_BG_BOARD
    COL_ORANGE = accent_clair
    COL_BLUE = accent_fonce
    if board_col is not None:
        COL_BG_BOARD = board_col
    try:
        draw_piece(canvas, x, y, sz, piece, force_normal=True, preview_theme=theme)
    finally:
        COL_ORANGE = save_o
        COL_BLUE = save_b
        COL_BG_BOARD = save_bg


# ── Photo de profil = une PIÈCE (type + thème), image jamais stockée au serveur ──
PROFILE_PIECES = ["Héritier", "Nurse", "Garde", "Soldat", "Chevalier"]


def parse_photo(photo):
    """'theme|Type' ou 'theme|Type|Noir' -> (theme, type, camp).
    Vide/invalide -> ('original', 'Héritier', 'Blanc')."""
    theme = "original"
    piece_type = "Héritier"
    camp = "Blanc"
    if photo and "|" in photo:
        parts = photo.split("|")
        t, p = parts[0], parts[1] if len(parts) > 1 else ""
        if t in THEMES:
            theme = t
        if p in PROFILE_PIECES:
            piece_type = p
        if len(parts) >= 3 and parts[2] in ("Blanc", "Noir"):
            camp = parts[2]
    return theme, piece_type, camp


def draw_profile_piece(canvas, x, y, sz, theme, piece_type, camp="Blanc"):
    """Dessine une pièce (type + camp) dans les couleurs/images du thème DONNÉ,
    indépendamment du thème courant (pour la photo de profil)."""
    piece = {"type": piece_type, "camp": camp}
    th = THEMES.get(theme, THEMES["original"])
    if _theme_image_dir(theme) is not None:
        draw_piece(canvas, x, y, sz, piece, preview_theme=theme)
    else:
        draw_piece_themed(canvas, x, y, sz, piece,
                          th["clair"], th["fonce"], th.get("board"), theme=theme)


DEEPGREY_PHOTO = "deepgrey"   # marqueur : photo spéciale de l'IA (deepgrey.png)
_DEEPGREY_CACHE = {}


def _deepgrey_texture():
    """Charge (une fois) l'image de profil de Deep Grey (deepgrey.png à la racine,
    à côté de main.py). Renvoie la texture ou None si le fichier est absent."""
    if "tex" in _DEEPGREY_CACHE:
        return _DEEPGREY_CACHE["tex"]
    tex = None
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base, "deepgrey.png")
        if os.path.exists(path):
            from kivy.core.image import Image as CoreImage
            tex = CoreImage(path).texture
    except Exception:
        tex = None
    _DEEPGREY_CACHE["tex"] = tex
    return tex


# Photo par défaut de TOUT LE MONDE : le logo du thème "original" (fixe : ne suit
# PAS le thème courant). Les photos sont modifiables uniquement depuis le profil.
DEFAULT_PHOTO = "logo|original"
_LOGO_SPECIAL = {"medieval": "bataille", "fleur": "fleurs", "insectes": "foret"}
_LOGO_CACHE = {}


def _logo_texture(theme):
    """Charge (et met en cache) le logo d'un thème (logos/logo_<nom>.png)."""
    if theme in _LOGO_CACHE:
        return _LOGO_CACHE[theme]
    tex = None
    try:
        base = os.path.dirname(os.path.abspath(__file__))
        name = _LOGO_SPECIAL.get(theme, theme)
        path = os.path.join(base, "logos", "logo_%s.png" % name)
        if os.path.exists(path):
            from kivy.core.image import Image as CoreImage
            tex = CoreImage(path).texture
    except Exception:
        tex = None
    _LOGO_CACHE[theme] = tex
    return tex


def avatar_photo_for(pseudo, photo=""):
    """Photo à utiliser pour l'avatar d'un joueur : marqueur Deep Grey si c'est
    l'IA, sinon la photo fournie (vide -> pièce par défaut au rendu)."""
    if pseudo and pseudo.strip().lower() in ("deep grey", "deepgrey"):
        return DEEPGREY_PHOTO
    return photo or ""


_AVATAR_PHOTO_CACHE = {}   # pseudo (minuscule) -> photo connue


def resolve_avatar_photo(pseudo, on_ready=None):
    """Renvoie IMMÉDIATEMENT la photo connue d'un pseudo (Deep Grey, ma photo,
    cache, ou '' par défaut). Si inconnue et que c'est un joueur réel, la récupère
    en arrière-plan puis appelle on_ready(photo) pour rafraîchir l'affichage."""
    if not pseudo:
        return ""
    pl = pseudo.strip().lower()
    if pl in ("deep grey", "deepgrey"):
        return DEEPGREY_PHOTO
    if pseudo == (ONLINE.pseudo or ""):
        # Ma photo : self.photo si connue, sinon la récupérer du serveur (le login
        # ne la renvoie pas toujours, donc elle peut être vide au démarrage).
        if ONLINE.photo:
            _AVATAR_PHOTO_CACHE[pl] = ONLINE.photo
            return ONLINE.photo
        if ONLINE.is_logged_in():
            def on_prof(prof, err):
                photo = (prof or {}).get("photo", "") if not err else ""
                ONLINE.photo = photo or ""
                _AVATAR_PHOTO_CACHE[pl] = photo or ""
                if on_ready:
                    on_ready(photo or "")
            ONLINE.get_profile(pseudo, on_prof)
        return ""
    if pl in _AVATAR_PHOTO_CACHE:
        return _AVATAR_PHOTO_CACHE[pl]
    if ONLINE.is_logged_in():
        def on_prof(prof, err):
            photo = (prof or {}).get("photo", "") if not err else ""
            _AVATAR_PHOTO_CACHE[pl] = photo or ""
            if on_ready:
                on_ready(photo or "")
        ONLINE.get_profile(pseudo, on_prof)
    return ""


def _refresh_chat_badges(widget):
    """Met à jour les pastilles de messages non lus (bouton Chat du menu ET bouton
    chat en partie) en récupérant le total côté serveur."""
    sm = getattr(widget, "manager", None)
    if sm is None or not ONLINE.is_logged_in():
        return

    def on_list(convos, total, err):
        if err:
            return
        for name in ("menu", "game"):
            try:
                scr = sm.get_screen(name)
                if hasattr(scr, "_set_chat_badge"):
                    scr._set_chat_badge(total)
            except Exception:
                pass
    ONLINE.list_conversations(on_list)


class PiecePhoto(Widget):
    """Affiche une pièce comme photo de profil (type + thème). 'photo' est un mot
    'theme|Type' ; vide => thème courant + Héritier. Cas spécial : 'deepgrey'
    affiche l'image dédiée de l'IA (deepgrey.png)."""

    def __init__(self, photo="", **kw):
        super().__init__(**kw)
        self._photo_raw = photo or ""
        self._theme, self._piece, self._camp = parse_photo(photo)
        self.bind(pos=lambda *a: self._redraw(), size=lambda *a: self._redraw())

    def set_photo(self, photo):
        self._photo_raw = photo or ""
        self._theme, self._piece, self._camp = parse_photo(photo)
        self._redraw()

    def _redraw(self, *a):
        self.canvas.clear()
        sz = min(self.width, self.height)
        if sz <= 0:
            return
        x = self.x + (self.width - sz) / 2.0
        y = self.y + (self.height - sz) / 2.0
        raw = self._photo_raw or DEFAULT_PHOTO   # vide -> logo original (fixe)
        # Cas spécial Deep Grey : vraie image dédiée (deepgrey.png).
        if raw == DEEPGREY_PHOTO:
            tex = _deepgrey_texture()
            with self.canvas:
                if tex is not None:
                    Color(1, 1, 1, 1)   # sinon l'image prend la couleur ambiante
                    Rectangle(texture=tex, pos=(x, y), size=(sz, sz))
                else:
                    Color(0.30, 0.30, 0.34, 1)   # repli si image absente
                    RoundedRectangle(pos=(x, y), size=(sz, sz), radius=[sz * 0.12])
            return
        # Logo d'un thème : "logo|<theme>".
        if raw.startswith("logo|"):
            theme = raw.split("|", 1)[1]
            tex = _logo_texture(theme)
            th = THEMES.get(theme, THEMES["original"])
            with self.canvas:
                Color(*th.get("menu", (0.75, 0.75, 0.75, 1)))
                RoundedRectangle(pos=(x, y), size=(sz, sz), radius=[sz * 0.12])
                if tex is not None:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex, pos=(x, y), size=(sz, sz))
            return
        # Sinon : une pièce (theme|Type).
        th = THEMES.get(self._theme, THEMES["original"])
        with self.canvas:
            Color(*th.get("board", (0.5, 0.5, 0.5, 1)))
            RoundedRectangle(pos=(x, y), size=(sz, sz), radius=[sz * 0.12])
        draw_profile_piece(self.canvas, x, y, sz, self._theme, self._piece, self._camp)


def open_settings_popup(app_or_game):
    """Ouvre la popup de réglages (son + thème).
    app_or_game : soit le GameScreen (pour rafraîchir en direct), soit None."""
    # Trouver le ScreenManager
    from kivy.app import App
    app = App.get_running_app()
    sm = app.sm if hasattr(app, "sm") else None

    cfg = load_config()

    root = BoxLayout(orientation="vertical", spacing=S(6), padding=S(16))

    # ── Sélecteur de langue (UNIQUEMENT depuis le menu, pour éviter de
    # détruire l'écran courant pendant le tuto ou une partie/analyse) ──
    _lang_from_menu = (sm is not None and getattr(sm, "current", None) == "menu")
    if _lang_from_menu:
        # ── Sélecteur de langue ──
        root.add_widget(Label(text=T("Langue"), font_size=SF("15sp"), bold=True,
                              color=(1, 1, 1, 1), size_hint=(1, 0.05)))
        lang_row = BoxLayout(orientation="horizontal", size_hint=(1, 0.10),
                             spacing=S(6))
        lang_state = {"idx": LANG_ORDER.index(LANG) if LANG in LANG_ORDER else 0}
        lang_prev = RoundButton(text="<", font_size=SF("16sp"), bold=True,
                                bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                                size_hint=(0.16, 1))
        lang_lbl = Label(text=LANG_LABELS[LANG_ORDER[lang_state["idx"]]],
                         font_size=SF("15sp"), bold=True, color=(1, 1, 1, 1),
                         halign="center", valign="middle", size_hint=(0.68, 1))
        lang_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        lang_next = RoundButton(text=">", font_size=SF("16sp"), bold=True,
                                bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                                size_hint=(0.16, 1))
        lang_row.add_widget(lang_prev)
        lang_row.add_widget(lang_lbl)
        lang_row.add_widget(lang_next)
        root.add_widget(lang_row)

        def _lang_update():
            lang_lbl.text = LANG_LABELS[LANG_ORDER[lang_state["idx"]]]

        def _lang_prev(*a):
            lang_state["idx"] = (lang_state["idx"] - 1) % len(LANG_ORDER)
            _lang_update()

        def _lang_next(*a):
            lang_state["idx"] = (lang_state["idx"] + 1) % len(LANG_ORDER)
            _lang_update()
        lang_prev.bind(on_release=_lang_prev)
        lang_next.bind(on_release=_lang_next)

        lang_apply_btn = RoundButton(text=T("Valider la langue"), bg_color=COL_ORANGE,
                                     color=(1, 1, 1, 1), font_size=SF("12sp"),
                                     bold=True, size_hint=(1, 0.07))

        def _apply_lang(*a):
            code = LANG_ORDER[lang_state["idx"]]
            set_language(code)
            popup.dismiss()
            try:
                app.rebuild_screens()
            except Exception:
                pass
        lang_apply_btn.bind(on_release=_apply_lang)
        root.add_widget(lang_apply_btn)

    # ── Section Son ──
    root.add_widget(Label(text=T("Volume"), font_size=SF("17sp"), bold=True,
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
    inst_lbl = Label(text=T(INSTRUMENT_LABELS[INSTRUMENT_ORDER[inst_state["idx"]]]),
                     font_size=SF("14sp"), bold=True, color=(1, 1, 1, 1),
                     halign="center", valign="middle", size_hint=(0.68, 1))
    inst_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
    inst_next = RoundButton(text=">", font_size=SF("16sp"), bold=True,
                            bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                            size_hint=(0.16, 1))
    def _set_instrument(*a):
        name = INSTRUMENT_ORDER[inst_state["idx"]]
        inst_lbl.text = T(INSTRUMENT_LABELS[name])
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
    root.add_widget(Label(text=T("Vitesse de glissée des pièces"), font_size=SF("17sp"),
                          bold=True, color=(1, 1, 1, 1), size_hint=(1, 0.07)))
    # Valeur stockée = durée de l'animation en secondes (0 = instantané).
    # Curseur : gauche = instantané (0s), droite = lent (0.6s).
    try:
        cur_speed = float(cfg.get("slide_speed", "0.18"))
    except (ValueError, TypeError):
        cur_speed = 0.18
    speed_slider = Slider(min=0.0, max=0.6, value=cur_speed, size_hint=(1, 0.08))
    def speed_text(v):
        if v < 0.02: return T("Instantané")
        if v < 0.20: return T("Rapide")
        if v < 0.40: return T("Moyen")
        return T("Lent")
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
    root.add_widget(Label(text=T("Thème"), font_size=SF("17sp"), bold=True,
                          color=(1, 1, 1, 1), size_hint=(1, 0.07)))

    # État local de l'index de thème affiché
    state = {"idx": THEME_ORDER.index(CURRENT_THEME) if CURRENT_THEME in THEME_ORDER else 0}

    # Ligne : < nom_thème >  +  aperçu  (boutons réduits)
    theme_row = BoxLayout(orientation="horizontal", size_hint=(1, 0.14), spacing=S(6))
    btn_prev = RoundButton(text="<", font_size=SF("16sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(0.14, 1))
    name_box = BoxLayout(orientation="vertical", size_hint=(0.32, 1))
    theme_name_lbl = Label(text=T(THEME_LABELS[THEME_ORDER[state["idx"]]]),
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

    # ── Bouton « Composer le thème » (juste sous le thème, menu uniquement) ──
    if _lang_from_menu:
        compose_btn = RoundButton(text=T("Composer le thème"), bg_color=COL_BLUE,
                                  color=(1, 1, 1, 1), bold=True,
                                  font_size=SF("12sp"), size_hint=(1, 0.07))

        def _open_composer(*a):
            try:
                popup.dismiss()
            except Exception:
                pass
            if sm is not None:
                sm.current = "theme_composer"
        compose_btn.bind(on_release=_open_composer)
        root.add_widget(compose_btn)

    def update_preview():
        name = THEME_ORDER[state["idx"]]
        theme_name_lbl.text = T(THEME_LABELS[name])
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
    btn_apply = RoundButton(text=T("Appliquer ce thème"), bg_color=COL_ORANGE,
                            color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True,
                            size_hint=(0.72, 1))
    btn_close = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
                            color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True,
                            size_hint=(0.28, 1))
    btn_box.add_widget(btn_apply)
    btn_box.add_widget(btn_close)
    root.add_widget(btn_box)

    popup = Popup(title=T("Réglages"), content=root, size_hint=(0.92, 0.88),
                  auto_dismiss=True)

    def apply_theme_now(*a):
        name = THEME_ORDER[state["idx"]]
        apply_theme(name)
        save_config(theme=name)
        # Enregistrer aussi le thème côté serveur (si connecté), pour le retrouver
        # à la prochaine connexion, même depuis un autre appareil.
        try:
            if ONLINE.is_logged_in():
                ONLINE.set_theme(name)
        except Exception:
            pass
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
        # Fond IMAGE des thèmes spéciaux (médiéval / fleur / insectes) : il faut
        # remplacer le texture, sinon l'ancien fond reste jusqu'à ce qu'on ferme
        # et rouvre l'appli.
        if hasattr(screen, "_bg_stone"):
            try:
                tex = (_theme_bg_texture("fond.png", theme=THEME_MENU_BG)
                       if _theme_bg_dir(THEME_MENU_BG) else None)
                screen._bg_stone.texture = tex
                if tex:
                    p, s = _fit_menu_bg(tex, Window.width, Window.height)
                    screen._bg_stone.pos = p
                    screen._bg_stone.size = s
                    screen._bg_stone_col.a = 1
                else:
                    screen._bg_stone_col.a = 0
                if hasattr(screen, "_bg_veil_col"):
                    screen._bg_veil_col.rgba = ((1, 1, 1, 0.45)
                                                if (THEME_MENU_BG == "fleur"
                                                    and tex) else (1, 1, 1, 0))
            except Exception:
                pass
        # Logo du menu : recharger avec le logo du thème courant (ici, sur le
        # chemin FIABLE, car dans apply_theme_colors ça pouvait être avalé).
        if hasattr(screen, "_logo_widget") and hasattr(screen, "_theme_logo_path"):
            try:
                lp = screen._theme_logo_path()
                # "source vide puis source" force Kivy à vraiment recharger.
                screen._logo_widget.source = ""
                screen._logo_widget.source = lp
                screen._logo_widget.reload()
                try:
                    from kivy.core.image import Image as _CImg
                    screen._logo_widget.texture = _CImg(lp, nocache=True).texture
                except Exception:
                    pass
            except Exception:
                pass
        # Tuto : redessiner le plateau pour qu'il prenne le nouveau thème.
        if hasattr(screen, "board_w") and hasattr(screen, "steps"):
            try:
                screen.board_w._redraw()
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


def show_first_launch_language(app, after):
    """Popup de choix de la langue au tout premier lancement (avant le tuto).
    Affiche les 10 langues (noms natifs) ; au clic, applique la langue et appelle
    `after()`. Titre bilingue car on ne connaît pas encore la langue du joueur."""
    root = BoxLayout(orientation="vertical", spacing=S(10), padding=S(16))
    title = Label(text="Langue / Language", font_size=SF("20sp"), bold=True,
                  color=(1, 1, 1, 1), size_hint=(1, 0.16),
                  halign="center", valign="middle")
    title.bind(size=lambda w, s: setattr(w, "text_size", s))
    root.add_widget(title)
    grid = GridLayout(cols=2, spacing=S(8), size_hint=(1, 0.84))
    popup = Popup(title="", separator_height=0, content=root,
                  size_hint=(0.9, 0.9), auto_dismiss=False)

    def _make(code):
        b = RoundButton(text=LANG_LABELS[code], bg_color=COL_BTN_GREY,
                        color=(1, 1, 1, 1), font_size=SF("17sp"), bold=True)

        def _pick(*a):
            set_language(code)
            try:
                popup.dismiss()
            except Exception:
                pass
            try:
                after()
            except Exception:
                pass
        b.bind(on_release=_pick)
        return b
    for code in LANG_ORDER:
        grid.add_widget(_make(code))
    root.add_widget(grid)
    popup.open()


def _register_unicode_font():
    """Enregistre une police couvrant latin + cyrillique + CJK (chinois, japonais,
    coréen) comme police PAR DÉFAUT de l'appli, pour que toutes les langues
    s'affichent (sinon Kivy utilise Roboto, qui ne connaît que le latin, et les
    autres alphabets apparaissent en carrés □).

    On l'enregistre sous le nom "Roboto" : c'est le nom de la police par défaut de
    Kivy, donc TOUS les Label/Button l'utilisent automatiquement, sans avoir à
    changer chaque widget.

    Robustesse : on cherche à plusieurs endroits (dossier du script, dossier
    courant, chemins Android), via resource_find de Kivy, et en dernier recours on
    prend N'IMPORTE QUEL fichier .otf/.ttf/.ttc trouvé dans polices/ (le nom exact
    n'a donc pas d'importance). S'il n'y a rien, on garde la police par défaut
    (le latin marche toujours)."""
    try:
        from kivy.core.text import LabelBase
        from kivy.resources import resource_find, resource_add_path
    except Exception as e:
        print("[police] Kivy indisponible :", e)
        return False
    import glob
    # 1) Dossiers-racines où chercher (PC de dev ET APK Android compilé)
    roots = []
    try:
        roots.append(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass
    try:
        roots.append(os.getcwd())
    except Exception:
        pass
    for env in ("ANDROID_APP_PATH", "ANDROID_PRIVATE", "ANDROID_ARGUMENT"):
        v = os.environ.get(env)
        if v:
            roots.append(v)
    seen = set()
    roots = [r for r in roots if r and not (r in seen or seen.add(r))]
    subs = ["polices", "fonts", "police", "font", "assets", "."]
    # Déclarer ces dossiers à Kivy pour que resource_find les explore
    for r in roots:
        for s in subs:
            d = os.path.join(r, s)
            if os.path.isdir(d):
                try:
                    resource_add_path(d)
                except Exception:
                    pass
    # 2) Noms de fichiers préférés (essayés d'abord)
    preferred = [
        "NotoSansCJKsc-Regular.otf", "NotoSansCJKsc-Regular.ttf",
        "NotoSansCJK-Regular.ttc", "NotoSansSC-Regular.otf",
        "NotoSansSC-Regular.ttf", "NotoSansCJKjp-Regular.otf",
        "NotoSansCJKkr-Regular.otf", "DroidSansFallbackFull.ttf",
        "DroidSansFallback.ttf", "GoNotoCurrent-Regular.ttf",
        "unifont.ttf", "arialuni.ttf",
    ]
    found = None
    for name in preferred:
        try:
            p = resource_find(name)
        except Exception:
            p = None
        if p and os.path.exists(p):
            found = p
            break
    # 3) Sinon : prendre n'importe quel fichier de police dans les dossiers
    if not found:
        def score(fp):
            n = os.path.basename(fp).lower()
            return sum(kw in n for kw in
                       ("noto", "cjk", "droid", "unifont", "arialuni", "sans"))
        for r in roots:
            for s in subs:
                d = os.path.join(r, s)
                if not os.path.isdir(d):
                    continue
                cand = []
                for ext in ("*.otf", "*.ttf", "*.ttc"):
                    cand += glob.glob(os.path.join(d, ext))
                cand.sort(key=score, reverse=True)
                if cand:
                    found = cand[0]
                    break
            if found:
                break
    if not found:
        print("[police] aucune police trouvée (mettez un .otf/.ttf dans polices/) "
              "— les alphabets non-latins resteront en carrés")
        return False
    # 4) Enregistrer sous 'Roboto' (police par défaut) -> tous les widgets
    try:
        LabelBase.register(name="Roboto", fn_regular=found)
        print("[police] police Unicode par défaut :", found)
        return True
    except Exception as e:
        print("[police] échec de l'enregistrement :", e, "->", found)
        return False


def _disp_player(name):
    """Nom de joueur pour l'AFFICHAGE uniquement : traduit les identifiants locaux
    ('Joueur 1'/'Joueur 2'), affiche 'Deep Grey' pour l'IA, laisse les vrais pseudos
    inchangés. NE JAMAIS utiliser comme clé de dictionnaire ni identifiant logique
    (la logique doit rester en français)."""
    if name in ("Joueur 1", "Joueur 2"):
        return T(name)
    if name == "deep grey":
        return "Deep Grey"
    return name


class ConversationScreen(Screen):
    """Boîte de messages UNIFIÉE avec un joueur : LA MÊME conversation partout
    (correspondance, parties directes, hors partie), liée à la paire de joueurs.
    target_pseudo = l'autre joueur ; return_screen = l'écran où revenir."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self.target_pseudo = None
        self.return_screen = "menu"
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))

        header = BoxLayout(size_hint=(1, 0.09), padding=(S(8), S(6)), spacing=S(8))
        back = RoundButton(text=T("< Retour"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(100))
        back.bind(on_release=lambda *a: setattr(self.manager, "current",
                                                self.return_screen))
        self.title_lbl = Label(text="", font_size=SF("18sp"), bold=True,
                               color=(0, 0, 0, 1), halign="center", valign="middle")
        self.title_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        header.add_widget(back)
        header.add_widget(self.title_lbl)
        header.add_widget(Widget(size_hint=(None, 1), width=S(100)))
        root.add_widget(header)

        self.scroll = ScrollView(size_hint=(1, 1), do_scroll_x=False, bar_width=6)
        self.msg_box = GridLayout(cols=1, spacing=S(4), padding=(S(10), S(8)),
                                  size_hint_y=None)
        self.msg_box.bind(minimum_height=self.msg_box.setter("height"))
        self.scroll.add_widget(self.msg_box)
        root.add_widget(self.scroll)

        bar = BoxLayout(size_hint=(1, 0.1), padding=(S(8), S(6)), spacing=S(8))
        self.input = TextInput(multiline=False, hint_text=T("Votre message…"),
                               font_size=SF("15sp"), size_hint=(1, 1))
        send = RoundButton(text=T("Envoyer"), bg_color=COL_ORANGE, color=(1, 1, 1, 1),
                           font_size=SF("14sp"), bold=True,
                           size_hint=(None, 1), width=S(100))
        send.bind(on_release=lambda *a: self._send())
        bar.add_widget(self.input)
        bar.add_widget(send)
        root.add_widget(bar)
        self.add_widget(root)

    def on_pre_enter(self, *a):
        self.title_lbl.text = self.target_pseudo or "?"
        # Marquer comme lus les messages reçus de cet interlocuteur.
        if self.target_pseudo:
            ONLINE.mark_read(self.target_pseudo,
                             lambda ok, e: _refresh_chat_badges(self))
        # Photo de l'interlocuteur (pour les avatars des bulles).
        self._target_photo = resolve_avatar_photo(
            self.target_pseudo,
            on_ready=lambda p: setattr(self, "_target_photo", p))
        self.msg_box.clear_widgets()
        self.msg_box.add_widget(Label(
            text=T("Chargement…"), font_size=SF("13sp"), color=(0.4, 0.4, 0.4, 1),
            italic=True, size_hint_y=None, height=S(40)))

        def on_conv(msgs, err):
            self.msg_box.clear_widgets()
            if err:
                self.msg_box.add_widget(Label(
                    text=T("Conversation indisponible."), font_size=SF("13sp"),
                    color=(0.6, 0.3, 0.3, 1), size_hint_y=None, height=S(40)))
                return
            if not msgs:
                self.msg_box.add_widget(Label(
                    text=T("Aucun message. Écrivez le premier !"),
                    font_size=SF("13sp"), color=(0.4, 0.4, 0.4, 1), italic=True,
                    size_hint_y=None, height=S(40)))
                return
            for m in msgs:
                self._add_bubble(m.get("texte", ""), m.get("de_moi", False))
            self._scroll_bottom()
        ONLINE.list_conversation(self.target_pseudo, on_conv)

    def _add_bubble(self, text, de_moi):
        row = BoxLayout(orientation="horizontal", size_hint_y=None,
                        spacing=S(6), padding=(S(2), S(2)))
        av = PiecePhoto(size_hint=(None, 1), width=S(34))
        if de_moi:
            av.set_photo(avatar_photo_for(ONLINE.pseudo, ONLINE.photo))
        else:
            av.set_photo(avatar_photo_for(self.target_pseudo,
                                          getattr(self, "_target_photo", "")))
        lbl = Label(text=text, font_size=SF("16sp"),
                    color=(1, 0.82, 0.4, 1) if de_moi else (0.95, 0.95, 0.95, 1),
                    halign="right" if de_moi else "left", valign="middle",
                    size_hint=(1, None))

        def _resize(w, s):
            h = max(S(38), s[1] + S(12))
            w.height = h
            row.height = h
        lbl.bind(width=lambda w, *a: setattr(w, "text_size", (w.width - S(10), None)),
                 texture_size=_resize)
        if de_moi:
            row.add_widget(lbl)
            row.add_widget(av)
        else:
            row.add_widget(av)
            row.add_widget(lbl)
        self.msg_box.add_widget(row)

    def _scroll_bottom(self):
        try:
            Clock.schedule_once(lambda dt: setattr(self.scroll, "scroll_y", 0), 0.05)
        except Exception:
            pass

    def _send(self):
        txt = self.input.text.strip()
        if not txt or not self.target_pseudo:
            return
        self.input.text = ""
        self._add_bubble(txt, True)      # affichage optimiste
        self._scroll_bottom()

        def on_done(ok, err):
            if not ok:
                self._add_bubble(T("(non envoyé : %s)") % err, False)
        ONLINE.send_message(self.target_pseudo, txt, on_done)

    def add_incoming(self, de, texte):
        """Message reçu en temps réel : l'ajoute si c'est cette conversation."""
        if de and de == self.target_pseudo:
            self._add_bubble(texte, False)
            self._scroll_bottom()


class ConversationsListScreen(Screen):
    """Liste de TOUTES mes conversations (messagerie), avec pastille de non-lus."""

    def __init__(self, **kw):
        super().__init__(**kw)
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg_col = Color(*COL_BG_MENU)
            self._bg = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bg, "size", Window.size))
        header = BoxLayout(size_hint=(1, 0.09), padding=(S(8), S(6)), spacing=S(8))
        back = RoundButton(text=T("< Retour"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(100))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        title = Label(text=T("Messages"), font_size=SF("18sp"), bold=True,
                      color=(0, 0, 0, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(100)))
        root.add_widget(header)
        self.scroll = ScrollView(size_hint=(1, 1))
        self.list_box = GridLayout(cols=1, spacing=S(8), padding=(S(10), S(8)),
                                   size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        self.scroll.add_widget(self.list_box)
        root.add_widget(self.scroll)
        self.add_widget(root)

    def on_pre_enter(self, *a):
        self.list_box.clear_widgets()
        self.list_box.add_widget(Label(
            text=T("Chargement…"), font_size=SF("13sp"), italic=True,
            color=(0.4, 0.4, 0.4, 1), size_hint_y=None, height=S(40)))

        def on_list(convos, total, err):
            self.list_box.clear_widgets()
            if err:
                self.list_box.add_widget(Label(
                    text=T("Messagerie indisponible."), font_size=SF("13sp"),
                    color=(0.6, 0.3, 0.3, 1), size_hint_y=None, height=S(40)))
                return
            if not convos:
                self.list_box.add_widget(Label(
                    text=T("Aucune conversation pour le moment."),
                    font_size=SF("13sp"), italic=True, color=(0.4, 0.4, 0.4, 1),
                    size_hint_y=None, height=S(40)))
                return
            for c in convos:
                self.list_box.add_widget(self._make_row(c))
        ONLINE.list_conversations(on_list)

    def _make_row(self, c):
        pseudo = c.get("pseudo", "?")
        last = c.get("last_text", "") or ""
        unread = c.get("unread", 0)
        de_moi = c.get("last_de_moi", False)
        card = BoxLayout(orientation="horizontal", size_hint=(1, None),
                         height=S(64), spacing=S(10), padding=(S(10), S(6)))
        with card.canvas.before:
            Color(*COL_BTN_GREY)
            card._r = RoundedRectangle(pos=card.pos, size=card.size, radius=[S(10)])
        card.bind(pos=lambda b, *a: setattr(b._r, "pos", b.pos),
                  size=lambda b, *a: setattr(b._r, "size", b.size))
        av = PiecePhoto(photo=avatar_photo_for(pseudo, c.get("photo", "")),
                        size_hint=(None, 1), width=S(46))
        card.add_widget(av)
        col = BoxLayout(orientation="vertical", size_hint=(1, 1))
        name_lbl = Label(text=pseudo, font_size=SF("15sp"), bold=True,
                         color=(1, 1, 1, 1), halign="left", valign="middle",
                         size_hint=(1, 0.5), shorten=True)
        name_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        preview = (T("Vous : ") + last) if de_moi else last
        prev_lbl = Label(text=preview, font_size=SF("12sp"),
                         color=(0.82, 0.82, 0.82, 1), halign="left",
                         valign="middle", size_hint=(1, 0.5), shorten=True)
        prev_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        col.add_widget(name_lbl)
        col.add_widget(prev_lbl)
        card.add_widget(col)
        if unread > 0:
            badge = Label(text=str(unread), font_size=SF("13sp"), bold=True,
                          color=(1, 1, 1, 1), size_hint=(None, 1), width=S(30))
            with badge.canvas.before:
                badge._bc = Color(0.85, 0.2, 0.2, 1)
                badge._br = RoundedRectangle(radius=[S(12)])

            def _upd(w, *a):
                s = min(S(26), w.height)
                w._br.size = (s, s)
                w._br.pos = (w.x + (w.width - s) / 2.0,
                             w.y + (w.height - s) / 2.0)
            badge.bind(pos=_upd, size=_upd)
            card.add_widget(badge)
        card.bind(on_touch_down=lambda w, t, ps=pseudo:
                  self._open_convo(ps) if w.collide_point(*t.pos) else None)
        return card

    def _open_convo(self, pseudo):
        try:
            conv = self.manager.get_screen("conversation")
            conv.target_pseudo = pseudo
            conv.return_screen = "conversations_list"
            self.manager.current = "conversation"
        except Exception:
            pass


class AxisPreview(Widget):
    """Aperçu d'un thème pour un axe donné : 'general' (couleurs), 'menu' ou
    'board' (fonds). Les axes 'pieces' et 'logo' passent par PiecePhoto."""

    def __init__(self, axis, theme, **kw):
        super().__init__(**kw)
        self._axis = axis
        self._theme = theme
        self.bind(pos=lambda *a: self._redraw(), size=lambda *a: self._redraw())

    def _redraw(self, *a):
        self.canvas.clear()
        sz = min(self.width, self.height)
        if sz <= 0:
            return
        x = self.x + (self.width - sz) / 2.0
        y = self.y + (self.height - sz) / 2.0
        th = THEMES.get(self._theme, THEMES["original"])
        r = sz * 0.14
        with self.canvas:
            if self._axis == "general":
                Color(*th["fonce"])
                RoundedRectangle(pos=(x, y), size=(sz, sz), radius=[r])
                m = sz * 0.24
                Color(*th["clair"])
                RoundedRectangle(pos=(x + m, y + m),
                                 size=(sz - 2 * m, sz - 2 * m), radius=[r * 0.7])
            else:  # menu / board
                fname = "fond.png" if self._axis == "menu" else "plateau.png"
                tex = _theme_bg_texture(fname, theme=self._theme)
                if tex is not None:
                    Color(1, 1, 1, 1)
                    Rectangle(texture=tex, pos=(x, y), size=(sz, sz))
                else:
                    col = th["menu"] if self._axis == "menu" else th["board"]
                    Color(*col)
                    RoundedRectangle(pos=(x, y), size=(sz, sz), radius=[r])


def _make_axis_preview(axis, theme, size):
    """Widget d'aperçu d'un thème pour un axe."""
    if axis == "pieces":
        return PiecePhoto(photo=theme + "|Héritier",
                          size_hint=(None, None), size=size)
    if axis == "logo":
        return PiecePhoto(photo="logo|" + theme,
                          size_hint=(None, None), size=size)
    return AxisPreview(axis, theme, size_hint=(None, None), size=size)


class ThemeComposerScreen(Screen):
    """Composition de thème : 5 axes indépendants, chacun avec un défilement
    horizontal d'aperçus à choisir."""

    AXES = [
        ("general", "Général"),
        ("pieces",  "Pièces"),
        ("logo",    "Logo"),
        ("menu",    "Fond du menu"),
        ("board",   "Plateau"),
    ]

    def __init__(self, **kw):
        super().__init__(**kw)
        self._sel = {}      # axe -> thème choisi
        self._cells = {}    # axe -> {thème: cellule}
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical")
        with root.canvas.before:
            self._bg = Color(*COL_BG_MENU)
            self._bgr = Rectangle(pos=(0, 0), size=Window.size)
        Window.bind(size=lambda *a: setattr(self._bgr, "size", Window.size))
        header = BoxLayout(size_hint=(1, 0.09), padding=(S(8), S(6)), spacing=S(8))
        back = RoundButton(text=T("< Retour"), font_size=SF("14sp"), bold=True,
                           bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                           size_hint=(None, 1), width=S(100))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        title = Label(text=T("Composer le thème"), font_size=SF("17sp"),
                      bold=True, color=(1, 1, 1, 1))
        header.add_widget(back)
        header.add_widget(title)
        header.add_widget(Widget(size_hint=(None, 1), width=S(100)))
        root.add_widget(header)
        scroll = ScrollView(size_hint=(1, 1))
        self._sections = BoxLayout(orientation="vertical", size_hint_y=None,
                                   spacing=S(10), padding=(S(8), S(8)))
        self._sections.bind(minimum_height=self._sections.setter("height"))
        scroll.add_widget(self._sections)
        root.add_widget(scroll)
        applyrow = BoxLayout(size_hint=(1, 0.10), padding=(S(10), S(6)),
                             spacing=S(8))
        self._apply_btn = RoundButton(text=T("Appliquer"), bg_color=COL_ORANGE,
                                      color=(1, 1, 1, 1), bold=True,
                                      font_size=SF("15sp"))
        self._apply_btn.bind(on_release=self._apply)
        applyrow.add_widget(self._apply_btn)
        root.add_widget(applyrow)
        self.add_widget(root)

    def on_pre_enter(self, *a):
        try:
            self._bg.rgba = COL_BG_MENU
        except Exception:
            pass
        self._sel = {"general": THEME_GENERAL, "pieces": THEME_PIECES,
                     "logo": THEME_LOGO, "menu": THEME_MENU_BG,
                     "board": THEME_BOARD}
        self._build_sections()

    def _build_sections(self):
        self._sections.clear_widgets()
        self._cells = {}
        for axis, label in self.AXES:
            self._sections.add_widget(self._make_section(axis, label))

    def _make_section(self, axis, label):
        box = BoxLayout(orientation="vertical", size_hint_y=None,
                        height=S(120), spacing=S(4))
        lbl = Label(text=T(label), font_size=SF("14sp"), bold=True,
                    color=(1, 1, 1, 1), halign="left", valign="middle",
                    size_hint=(1, None), height=S(24))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        box.add_widget(lbl)
        row_scroll = ScrollView(size_hint=(1, None), height=S(90),
                                do_scroll_y=False)
        row = BoxLayout(orientation="horizontal", size_hint=(None, 1),
                        spacing=S(8), padding=(S(4), 0))
        row.bind(minimum_width=row.setter("width"))
        self._cells[axis] = {}
        for theme in THEME_ORDER:
            cell = self._make_cell(axis, theme)
            self._cells[axis][theme] = cell
            row.add_widget(cell)
        row_scroll.add_widget(row)
        box.add_widget(row_scroll)
        return box

    def _make_cell(self, axis, theme):
        cell = BoxLayout(orientation="vertical", size_hint=(None, 1),
                         width=S(74), padding=S(3), spacing=S(2))
        with cell.canvas.before:
            cell._sel_col = Color(*(COL_ORANGE if self._sel.get(axis) == theme
                                    else (0, 0, 0, 0)))
            cell._sel_r = RoundedRectangle(pos=cell.pos, size=cell.size,
                                           radius=[S(10)])
        cell.bind(pos=lambda b, *a: setattr(b._sel_r, "pos", b.pos),
                  size=lambda b, *a: setattr(b._sel_r, "size", b.size))
        anchor = AnchorLayout(size_hint=(1, None), height=S(58))
        anchor.add_widget(_make_axis_preview(axis, theme, (S(54), S(54))))
        cell.add_widget(anchor)
        name = Label(text=T(THEME_LABELS.get(theme, theme)), font_size=SF("9sp"),
                     color=(1, 1, 1, 1), size_hint=(1, None), height=S(18),
                     halign="center", valign="middle", shorten=True)
        name.bind(size=lambda w, s: setattr(w, "text_size", s))
        cell.add_widget(name)
        cell.bind(on_touch_down=lambda b, t, ax=axis, th=theme:
                  self._pick(ax, th) if b.collide_point(*t.pos) else None)
        return cell

    def _pick(self, axis, theme):
        self._sel[axis] = theme
        for th, cell in self._cells.get(axis, {}).items():
            cell._sel_col.rgba = COL_ORANGE if th == theme else (0, 0, 0, 0)

    def _apply(self, *a):
        apply_composite_theme(self._sel.get("general", "original"),
                              self._sel.get("pieces", "original"),
                              self._sel.get("logo", "original"),
                              self._sel.get("menu", "original"),
                              self._sel.get("board", "original"))
        s = current_theme_str()
        save_config(theme=s)
        try:
            if ONLINE.is_logged_in():
                ONLINE.set_theme(s)
        except Exception:
            pass
        if self.manager:
            refresh_all_screens(self.manager)
            self.manager.current = "menu"


class AccountScreen(Screen):
    """Profil d'un joueur : photo (pièce), pseudo, Mélo, description, tableaux
    qui-me-suit / qui-je-suis / (bloqués). IDENTIQUE pour soi et pour les autres.
    Sur SON propre profil : photo, description, email et notifications éditables,
    et la liste des bloqués (avec Débloquer). target_pseudo = None => mon profil."""

    _SUB = [
        ("turn",        "quand c'est à moi de jouer (corresp.)"),
        ("msg",         "quand je reçois un message (corresp.)"),
        ("defi_corr",   "quand quelqu'un me défie (corresp.)"),
        ("defi_direct", "quand quelqu'un me défie (en direct)"),
    ]

    def __init__(self, **kw):
        super().__init__(**kw)
        self.target_pseudo = None
        self._notif = {"mail": False, "turn": True, "msg": True,
                       "defi_corr": True, "defi_direct": True}
        self._email = ""
        self._photo = ""
        self._desc = ""
        self._boxes = {}
        self._build()

    def _build(self):
        root = BoxLayout(orientation="vertical", spacing=S(6), padding=S(10))
        self._scroll = ScrollView(size_hint=(1, 0.9))
        self._content = GridLayout(cols=1, size_hint_y=None, spacing=S(8),
                                   padding=(0, 0, S(4), S(4)))
        self._content.bind(minimum_height=self._content.setter("height"))
        self._scroll.add_widget(self._content)
        root.add_widget(self._scroll)
        self._bottom = BoxLayout(orientation="horizontal", size_hint=(1, 0.09),
                                 spacing=S(8))
        root.add_widget(self._bottom)
        self.add_widget(root)

    # ── Petits helpers de mise en page ──
    def _section_title(self, text):
        lbl = Label(text=text, font_size=SF("15sp"), bold=True, color=(1, 1, 1, 1),
                    halign="left", valign="middle", size_hint_y=None, height=S(30))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        return lbl

    def _person_row(self, f, blocked=False):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=S(38),
                        spacing=S(6))
        dot = "●" if f.get("online") else "○"
        col = (0.35, 0.8, 0.35, 1) if f.get("online") else (0.5, 0.5, 0.5, 1)
        row.add_widget(Label(text=dot, color=col, font_size=SF("14sp"),
                             size_hint=(None, 1), width=S(22)))
        name = Label(text=f.get("pseudo", "?"), color=(1, 1, 1, 1),
                     font_size=SF("13sp"), halign="left", valign="middle",
                     size_hint=(1, 1))
        name.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(name)
        melo = Label(text=T("Mélo : %d") % f.get("melo", 1500),
                     color=(0.8, 0.8, 0.6, 1), font_size=SF("11sp"),
                     halign="right", valign="middle", size_hint=(None, 1),
                     width=S(96))
        melo.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(melo)
        if blocked:
            unblock = RoundButton(text=T("Débloquer"), bg_color=COL_BTN_GREY,
                                  color=(1, 1, 1, 1), font_size=SF("10sp"), bold=True,
                                  size_hint=(None, 1), width=S(92))
            pseudo = f.get("pseudo", "")
            unblock.bind(on_release=lambda *a, p=pseudo, r=row: self._do_unblock(p, r))
            row.add_widget(unblock)
        return row

    def _add_person_list(self, people, empty_text, blocked=False):
        if not people:
            lbl = Label(text=empty_text, font_size=SF("12sp"),
                        color=(0.6, 0.6, 0.6, 1), halign="left", valign="middle",
                        size_hint_y=None, height=S(32))
            lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            self._content.add_widget(lbl)
            return
        for f in people:
            self._content.add_widget(self._person_row(f, blocked=blocked))

    def _do_unblock(self, pseudo, row):
        def on_done(ok, err):
            if ok:
                try: self._content.remove_widget(row)
                except Exception: pass
        ONLINE.unblock_user(pseudo, on_done)

    # ── Chargement du profil ──
    def on_pre_enter(self, *a):
        self._content.clear_widgets()
        self._bottom.clear_widgets()
        self._content.add_widget(Label(
            text=T("Chargement…"), font_size=SF("14sp"), color=(0.8, 0.8, 0.8, 1),
            size_hint_y=None, height=S(40)))
        back = RoundButton(text=T("Revenir au menu"), bg_color=COL_ORANGE,
                           color=(1, 1, 1, 1), font_size=SF("13sp"), bold=True)
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        self._bottom.add_widget(back)

        def on_prof(prof, err):
            if err or not prof:
                self._content.clear_widgets()
                self._content.add_widget(Label(
                    text=T("Profil indisponible."), font_size=SF("14sp"),
                    color=(0.85, 0.6, 0.6, 1), size_hint_y=None, height=S(40)))
                return
            self._populate(prof)
        ONLINE.get_profile(self.target_pseudo, on_prof)

    def _populate(self, prof):
        is_self = prof.get("is_self", False)
        self._is_self = is_self
        self._prof_pseudo = prof.get("pseudo", "?")
        self._email = prof.get("email", "") or ""
        self._photo = prof.get("photo", "") or ""
        self._desc = prof.get("description", "") or ""
        C = self._content
        C.clear_widgets()

        # Identité : photo + pseudo + Mélo
        idrow = BoxLayout(orientation="horizontal", size_hint_y=None,
                          height=S(140), spacing=S(12))
        self._photo_w = PiecePhoto(
            photo=self._photo,   # vide => logo original (DEFAULT_PHOTO)
            size_hint=(None, 1), width=S(140))
        idrow.add_widget(self._photo_w)
        idbox = BoxLayout(orientation="vertical", size_hint=(1, 1))
        p_lbl = Label(text="[b]%s[/b]" % self._prof_pseudo, markup=True,
                      font_size=SF("20sp"), color=(1, 1, 1, 1),
                      halign="left", valign="middle")
        p_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        m_lbl = Label(
            text=T("Standard : %d") % prof.get("melo", 1500) + "    "
                 + T("Random : %d") % prof.get("melo_random", 1500),
            font_size=SF("12sp"), bold=True, color=(0.85, 0.85, 0.55, 1),
            halign="left", valign="middle")
        m_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        idbox.add_widget(p_lbl)
        idbox.add_widget(m_lbl)
        idrow.add_widget(idbox)
        C.add_widget(idrow)

        if is_self:
            btn = RoundButton(text=T("Changer la photo"), bg_color=COL_BTN_GREY,
                              color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True,
                              size_hint_y=None, height=S(40))
            btn.bind(on_release=self._open_photo_picker)
            C.add_widget(btn)

        # Description
        C.add_widget(self._section_title(T("Description")))
        self._desc_lbl = Label(
            text=self._desc or T("(Aucune description)"),
            font_size=SF("13sp"),
            color=(0.9, 0.9, 0.9, 1) if self._desc else (0.55, 0.55, 0.55, 1),
            halign="left", valign="top", size_hint_y=None)
        self._desc_lbl.bind(
            width=lambda w, *a: setattr(w, "text_size", (w.width, None)),
            texture_size=lambda w, s: setattr(w, "height", max(S(28), s[1] + S(4))))
        C.add_widget(self._desc_lbl)
        if is_self:
            btn = RoundButton(text=T("Modifier la description"),
                              bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                              font_size=SF("12sp"), bold=True,
                              size_hint_y=None, height=S(40))
            btn.bind(on_release=self._open_desc_popup)
            C.add_widget(btn)

        # Réglages (mon profil seulement) : email + notifications
        if is_self:
            C.add_widget(self._section_title(T("Adresse mail")))
            self.email_lbl = Label(
                text=self._email or T("Aucune adresse mail"), font_size=SF("13sp"),
                color=(1, 1, 1, 1), halign="left", valign="middle",
                size_hint_y=None, height=S(26))
            self.email_lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
            C.add_widget(self.email_lbl)
            btn = RoundButton(text=T("Renseigner ou changer l'adresse mail"),
                              bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                              font_size=SF("12sp"), bold=True,
                              size_hint_y=None, height=S(40))
            btn.bind(on_release=self._open_email_popup)
            C.add_widget(btn)
            self._boxes = {}
            C.add_widget(self._mk_check(
                "mail", T("Recevoir des mails (aucune notification push)"), False))
            for key, label in self._SUB:
                C.add_widget(self._mk_check(key, T(label), True))
            self._refresh_boxes()
            ONLINE.account_info(self._on_notif_info)

        # Tableaux
        C.add_widget(self._section_title(
            T("Personnes qui me suivent") if is_self else T("Le suivent")))
        self._add_person_list(prof.get("followers", []),
                              T("Personne ne le suit encore."))
        C.add_widget(self._section_title(
            T("Personnes que je suis") if is_self else T("Il suit")))
        self._add_person_list(prof.get("following", []), T("Ne suit personne."))
        if is_self:
            C.add_widget(self._section_title(T("Joueurs bloqués")))
            self._add_person_list(prof.get("blocked", []),
                                  T("Aucun joueur bloqué."), blocked=True)

        # Historique
        C.add_widget(self._section_title(T("Historique")))
        hrow = BoxLayout(orientation="horizontal", size_hint_y=None, height=S(46),
                         spacing=S(8))
        loc = RoundButton(text=T("Historique local"), bg_color=COL_BTN_GREY,
                          color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True)
        onl = RoundButton(text=T("Historique en ligne"), bg_color=COL_BTN_GREY,
                          color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True)
        loc.bind(on_release=lambda *a: self._open_history(False))
        onl.bind(on_release=lambda *a: self._open_history(True))
        hrow.add_widget(loc)
        hrow.add_widget(onl)
        C.add_widget(hrow)

        # Barre du bas : retour (+ déconnexion sur mon profil)
        self._bottom.clear_widgets()
        back = RoundButton(text=T("Revenir au menu"), bg_color=COL_ORANGE,
                           color=(1, 1, 1, 1), font_size=SF("13sp"), bold=True,
                           size_hint=(0.6, 1) if is_self else (1, 1))
        back.bind(on_release=lambda *a: setattr(self.manager, "current", "menu"))
        self._bottom.add_widget(back)
        if is_self:
            lo = RoundButton(text=T("Se déconnecter"), bg_color=COL_BTN_GREY,
                             color=(1, 1, 1, 1), font_size=SF("12sp"), bold=True,
                             size_hint=(0.4, 1))
            lo.bind(on_release=self._logout)
            self._bottom.add_widget(lo)

    def _on_notif_info(self, info, err):
        if err or not info:
            return
        n = info.get("notif", {}) or {}
        self._notif = {
            "mail": bool(n.get("mail", False)),
            "turn": bool(n.get("turn", True)),
            "msg": bool(n.get("msg", True)),
            "defi_corr": bool(n.get("defi_corr", True)),
            "defi_direct": bool(n.get("defi_direct", True)),
        }
        self._refresh_boxes()

    # ── Cases de notification ──
    def _mk_check(self, key, label_text, sub):
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=S(38),
                        spacing=S(8), padding=(S(34) if sub else 0, 0, 0, 0))
        box = RoundButton(text="", bg_color=COL_BTN_GREY, color=(1, 1, 1, 1),
                          font_size=SF("15sp"), bold=True,
                          size_hint=(None, 1), width=S(38))
        box.bind(on_release=lambda *a, k=key: self._toggle(k))
        lbl = Label(text=label_text, color=(1, 1, 1, 1), font_size=SF("12sp"),
                    halign="left", valign="middle", size_hint=(1, 1))
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))
        row.add_widget(box)
        row.add_widget(lbl)
        self._boxes[key] = box
        return row

    def _toggle(self, key):
        if key != "mail" and not self._notif["mail"]:
            return
        self._notif[key] = not self._notif[key]
        self._refresh_boxes()
        ONLINE.set_notif_prefs(dict(self._notif))

    def _refresh_boxes(self):
        master = self._notif["mail"]
        for key, box in self._boxes.items():
            checked = self._notif[key]
            active = (key == "mail") or master
            box.text = "✓" if (checked and active) else ""
            try:
                box.set_bg(COL_ORANGE if (checked and active) else COL_BTN_GREY)
            except Exception:
                pass

    # ── Popups d'édition (mon profil) ──
    def _open_email_popup(self, *a):
        content = BoxLayout(orientation="vertical", spacing=S(10), padding=S(16))
        inp = TextInput(text=self._email, multiline=False,
                        hint_text=T("Nouvelle adresse mail"), font_size=SF("15sp"),
                        size_hint=(1, None), height=S(48))
        content.add_widget(inp)
        save = RoundButton(text=T("Enregistrer"), bg_color=COL_ORANGE,
                           color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                           size_hint=(1, None), height=S(46))
        content.add_widget(save)
        popup = Popup(title=T("Adresse mail"), content=content,
                      size_hint=(0.9, 0.35), pos_hint={"center_x": 0.5, "top": 0.98})

        def do_save(*_):
            new_email = inp.text.strip()

            def on_done(ok, err):
                if ok:
                    self._email = new_email
                    self.email_lbl.text = new_email or T("Aucune adresse mail")
            ONLINE.set_email(new_email, on_done)
            popup.dismiss()
        save.bind(on_release=do_save)
        popup.open()

    def _open_desc_popup(self, *a):
        content = BoxLayout(orientation="vertical", spacing=S(10), padding=S(16))
        inp = TextInput(text=self._desc, multiline=True,
                        hint_text=T("Écris ta description…"), font_size=SF("14sp"),
                        size_hint=(1, 1))
        content.add_widget(inp)
        save = RoundButton(text=T("Enregistrer"), bg_color=COL_ORANGE,
                           color=(1, 1, 1, 1), font_size=SF("14sp"), bold=True,
                           size_hint=(1, None), height=S(46))
        content.add_widget(save)
        popup = Popup(title=T("Description"), content=content,
                      size_hint=(0.92, 0.6), pos_hint={"center_x": 0.5, "top": 0.98})

        def do_save(*_):
            new_desc = inp.text.strip()[:500]

            def on_done(ok, err):
                if ok:
                    self._desc = new_desc
                    self._desc_lbl.text = new_desc or T("(Aucune description)")
                    self._desc_lbl.color = ((0.9, 0.9, 0.9, 1) if new_desc
                                            else (0.55, 0.55, 0.55, 1))
            ONLINE.set_description(new_desc, on_done)
            popup.dismiss()
        save.bind(on_release=do_save)
        popup.open()

    def _open_photo_picker(self, *a):
        """Galerie de photos de profil : tout est rangé (Deep Grey, logos de chaque
        thème, puis toutes les pièces par thème), on tape celle qu'on veut."""
        content = BoxLayout(orientation="vertical", spacing=S(8), padding=S(10))
        content.add_widget(Label(
            text=T("Choisis ta photo de profil"), font_size=SF("16sp"), bold=True,
            color=(1, 1, 1, 1), size_hint=(1, None), height=S(32)))
        scroll = ScrollView(size_hint=(1, 1))
        grid = GridLayout(cols=4, spacing=S(10), padding=(S(4), S(4)),
                          size_hint_y=None, row_default_height=S(70),
                          row_force_default=True)
        grid.bind(minimum_height=grid.setter("height"))
        scroll.add_widget(grid)
        content.add_widget(scroll)
        close = RoundButton(text=T("Fermer"), bg_color=COL_BTN_GREY,
                            color=(1, 1, 1, 1), font_size=SF("13sp"),
                            size_hint=(1, None), height=S(44))
        content.add_widget(close)
        popup = Popup(title="", content=content, size_hint=(0.96, 0.9),
                      separator_height=0)
        close.bind(on_release=lambda *a: popup.dismiss())

        def pick(photo_str):
            self._photo = photo_str
            self._photo_w.set_photo(photo_str)
            ONLINE.set_photo(photo_str)
            popup.dismiss()

        def add_option(photo_str):
            cell = AnchorLayout(size_hint=(1, None), height=S(70))
            pp = PiecePhoto(photo=photo_str, size_hint=(None, None),
                            size=(S(64), S(64)))
            pp.bind(on_touch_down=lambda w, t, ps=photo_str:
                    pick(ps) if w.collide_point(*t.pos) else None)
            cell.add_widget(pp)
            grid.add_widget(cell)

        add_option(DEEPGREY_PHOTO)                    # Deep Grey
        for th in THEME_ORDER:                         # logos de chaque thème
            add_option("logo|" + th)
        for th in THEME_ORDER:                         # pièces : blanches PUIS noires
            for pc in PROFILE_PIECES:
                add_option(th + "|" + pc)              # blanche
                add_option(th + "|" + pc + "|Noir")    # noire
        popup.open()
    def _open_history(self, online):
        """Ouvre l'historique (local ou en ligne) du profil affiché."""
        target = None if getattr(self, "_is_self", True) else self._prof_pseudo
        try:
            name = "history_online" if online else "history_local"
            scr = self.manager.get_screen(name)
            scr.target_pseudo = target
            scr._return_screen = "account"
            scr._return_pseudo = target
            self.manager.current = name
        except Exception:
            pass

    def _logout(self, *a):
        ONLINE.logout()
        clear_online_session()
        try:
            menu = self.manager.get_screen("menu")
            menu._refresh_online_ui()
        except Exception:
            pass
        self.manager.current = "menu"


class _DummyDismiss:
    """Objet factice avec une méthode dismiss() sans effet. Sert à réutiliser
    _confirm_cancel_match depuis le bouton retour Android, où aucun popup de
    pause n'est ouvert à refermer."""
    def dismiss(self, *a, **k):
        pass


def restart_app():
    """Relance PROPREMENT l'application (Android uniquement). Utile quand un long
    passage en arrière-plan a détruit le contexte graphique et laissé un écran
    figé : plutôt que de rester bloqué, on redémarre l'appli.

    Méthode fiable : on programme le redémarrage via AlarmManager JUSTE AVANT de
    tuer le processus, pour que l'appli reparte même si le processus meurt."""
    try:
        from jnius import autoclass
        Intent = autoclass("android.content.Intent")
        PythonActivity = autoclass("org.kivy.android.PythonActivity")
        System = autoclass("java.lang.System")
        Process = autoclass("android.os.Process")
        activity = PythonActivity.mActivity
        context = activity.getApplicationContext()
        pm = context.getPackageManager()
        intent = pm.getLaunchIntentForPackage(context.getPackageName())
        intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK
                        | Intent.FLAG_ACTIVITY_CLEAR_TASK)
        scheduled = False
        try:
            PendingIntent = autoclass("android.app.PendingIntent")
            AlarmManager = autoclass("android.app.AlarmManager")
            Context = autoclass("android.content.Context")
            SystemClock = autoclass("android.os.SystemClock")
            # FLAG_CANCEL_CURRENT (0x10000000) | FLAG_IMMUTABLE (0x04000000)
            flags = 0x10000000 | 0x04000000
            pending = PendingIntent.getActivity(context, 0, intent, flags)
            am = context.getSystemService(Context.ALARM_SERVICE)
            am.set(AlarmManager.ELAPSED_REALTIME,
                   SystemClock.elapsedRealtime() + 300, pending)
            scheduled = True
        except Exception:
            scheduled = False
        if not scheduled:
            # Repli : relancer l'activité directement
            try:
                activity.startActivity(intent)
            except Exception:
                pass
        Process.killProcess(Process.myPid())
        System.exit(0)
    except Exception:
        # Hors Android (ou si l'API échoue) : ne rien faire.
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
        # Clavier virtuel : la vue remonte JUSTE assez pour que le champ saisi
        # reste visible au-dessus du clavier (sans décaler tout l'écran).
        try:
            Window.softinput_mode = "below_target"
        except Exception:
            pass
        # Police Unicode (latin + cyrillique + CJK) pour toutes les langues.
        _register_unicode_font()
        # Charger la config (thème + volume + en ligne)
        cfg = load_config()
        apply_theme(cfg["theme"])
        # Langue de l'appli (multilingue). Par défaut : français.
        global LANG
        _lang = cfg.get("lang", "fr")
        LANG = _lang if _lang in LANG_LABELS else "fr"
        # Sécurité : on force l'adresse du serveur en ligne sur celle par défaut
        # (le vrai serveur) et on efface toute vieille adresse de test qui aurait
        # pu rester dans config.txt (sinon l'appli tenterait un PC injoignable).
        ONLINE.server_url = SERVER_URL_DEFAULT
        if cfg.get("server_url"):
            try:
                c = load_config()
                c.pop("server_url", None)
                save_config(c)
            except Exception:
                pass
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
        # (L'adresse du serveur est fixée par SERVER_URL_DEFAULT ; on n'utilise
        # plus config.txt pour ça, afin d'éviter qu'une vieille valeur —  ex.
        # localhost enregistré par erreur — empêche la connexion au vrai serveur.)
        # Reconnexion automatique si un token est sauvegardé (rester connecté
        # entre deux ouvertures de l'appli).
        token = cfg.get("online_token")
        if token:
            ONLINE.token = token
            ONLINE.pseudo = cfg.get("online_pseudo")
            try:
                ONLINE.melo = int(cfg.get("online_melo", "1500"))
                ONLINE.melo_random = int(cfg.get("online_melo_random", "1500"))
            except (ValueError, TypeError):
                ONLINE.melo = 1500
            def on_auto_login(ok):
                if not ok:
                    ONLINE.logout()
                    clear_online_session()
                else:
                    # Réappliquer le thème enregistré sur le serveur.
                    try:
                        apply_theme(ONLINE.theme)
                        save_config(theme=ONLINE.theme)
                        refresh_all_screens(self.sm)
                    except Exception:
                        pass
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
        sm.add_widget(AccountScreen(name="account"))
        sm.add_widget(ConversationScreen(name="conversation"))
        sm.add_widget(ConversationsListScreen(name="conversations_list"))
        sm.add_widget(ThemeComposerScreen(name="theme_composer"))
        self.sm = sm
        # Premier lancement de l'appli : ouvrir directement le tutoriel (une
        # seule fois). Le joueur peut le quitter quand il veut. Ensuite on va au
        # menu comme d'habitude.
        # Au tout premier lancement, on ouvre le tuto automatiquement. On le fait
        # APRÈS l'affichage de l'appli (Clock) pour ne pas basculer d'écran
        # pendant la construction.
        # Au tout premier lancement : d'abord choisir la langue, PUIS le tuto.
        first_lang = str(cfg.get("lang_chosen", "0")) not in ("1", "True", "true")
        need_tuto = str(cfg.get("tuto_seen", "0")) not in ("1", "True", "true")

        def _go_tuto(dt=None):
            try:
                setattr(self.sm, "current", "tuto")
            except Exception:
                pass

        if first_lang:
            def _after_lang():
                save_config(lang_chosen="1")
                # Reconstruire les écrans dans la langue choisie
                try:
                    self.rebuild_screens()
                except Exception:
                    pass
                if need_tuto:
                    save_config(tuto_seen="1")
                    Clock.schedule_once(_go_tuto, 0.2)
            Clock.schedule_once(
                lambda dt: show_first_launch_language(self, _after_lang), 0.4)
        elif need_tuto:
            try:
                Clock.schedule_once(_go_tuto, 0.4)
                save_config(tuto_seen="1")
            except Exception:
                pass
        # Gestion du bouton RETOUR Android (touche 27). Par défaut Android
        # quitterait l'app ; on intercepte pour naviguer dans l'app à la place.
        Window.bind(on_keyboard=self._on_key)
        return sm

    def rebuild_screens(self):
        """Recrée tous les écrans : au changement de langue, chaque écran relit
        ses textes via T() avec la nouvelle langue. On revient au menu."""
        sm = getattr(self, "sm", None)
        if sm is None:
            return
        for s in list(sm.screens):
            sm.remove_widget(s)
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(LoginScreen(name="login"))
        try:
            sm.add_widget(TutoScreen(name="tuto"))
        except Exception:
            pass
        sm.add_widget(GameScreen(name="game"))
        sm.add_widget(PartiesMenuScreen(name="parties_menu"))
        sm.add_widget(HistoryScreen(name="history_local"))
        sm.add_widget(OnlineHistoryScreen(name="history_online"))
        sm.add_widget(ReaderScreen(name="reader"))
        sm.add_widget(AccountScreen(name="account"))
        sm.add_widget(ConversationScreen(name="conversation"))
        sm.add_widget(ConversationsListScreen(name="conversations_list"))
        sm.add_widget(ThemeComposerScreen(name="theme_composer"))
        try:
            sm.current = "menu"
        except Exception:
            pass

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
            # T("Annuler le match").
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
        """Au retour de veille / d'arrière-plan : réactiver le plein écran et
        FORCER un redessin complet (sinon le contexte graphique perdu laisse un
        écran où l'on ne voit que le fond du thème), puis rétablir la connexion."""
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
        la connexion et l'état le plus longtemps possible. Au retour, on_resume
        force un redessin complet."""
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
