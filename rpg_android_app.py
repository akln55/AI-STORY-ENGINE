from __future__ import annotations

from pathlib import Path
from threading import Thread

from kivy.app import App
from kivy.animation import Animation
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp, sp
from kivy.properties import ColorProperty, NumericProperty
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.progressbar import ProgressBar
from kivy.uix.screenmanager import Screen, ScreenManager, SlideTransition
from kivy.uix.spinner import Spinner
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, RoundedRectangle, Line

from engine import __version__
from engine.app.controller import AppController
from engine.ai.model_manager import ModelSpec


# Adapted from the supplied "Void Panel Utilitarian" reference:
# near-black canvas, quiet charcoal panels, white primary actions, restrained status green.
BG = (0.0, 0.0, 0.0, 1)                    # #000000
SURFACE = (17 / 255, 17 / 255, 17 / 255, 1) # #111111
SURFACE_2 = (26 / 255, 26 / 255, 26 / 255, 1) # #1A1A1A
BORDER = (1.0, 1.0, 1.0, 0.10)
TEXT = (0.98, 0.98, 0.98, 1)                # near-white
MUTED = (0.61, 0.64, 0.69, 1)               # muted gray
ACCENT = (22 / 255, 163 / 255, 74 / 255, 1) # status/active only
DANGER = (0.86, 0.15, 0.15, 1)
FOOTER_SURFACE = (10 / 255, 10 / 255, 10 / 255, 1)


def _aligned_label(text="", **kwargs):
    """Consistent wrapping and alignment for fixed-size mobile labels."""
    kwargs.setdefault("halign", "left")
    kwargs.setdefault("valign", "middle")
    label = Label(text=text, **kwargs)
    label.bind(size=lambda widget, *_: setattr(widget, "text_size", widget.size))
    return label


def _field_group(caption, control, *, height=dp(70)):
    """A labelled, compact form field; prevents unlabeled tall text boxes."""
    group = BoxLayout(orientation="vertical", spacing=dp(5), size_hint_y=None, height=height)
    group.add_widget(_aligned_label(
        text=caption.upper(), color=MUTED, font_size=sp(10), bold=True,
        size_hint_y=None, height=dp(18),
    ))
    control.size_hint_y = None
    control.height = dp(44)
    group.add_widget(control)
    return group


class RoundedPanel(BoxLayout):
    radius = NumericProperty(dp(18))
    fill = ColorProperty(SURFACE)
    outline = ColorProperty(BORDER)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(rgba=self.fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
            self._line_color = Color(rgba=self.outline)
            self._line = Line(rounded_rectangle=(self.x, self.y, self.width, self.height, self.radius), width=0.7)
        self.bind(pos=self._sync, size=self._sync, fill=self._sync, outline=self._sync, radius=self._sync)

    def _sync(self, *_):
        self._color.rgba = self.fill
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self.radius]
        self._line_color.rgba = self.outline
        self._line.rounded_rectangle = (self.x, self.y, self.width, self.height, self.radius)


class SoftButton(Button):
    fill = ColorProperty(SURFACE_2)
    pressed_fill = ColorProperty((0.22, 0.22, 0.22, 1))
    radius = NumericProperty(dp(22))

    def __init__(self, **kwargs):
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("font_size", sp(14))
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(rgba=self.fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(pos=self._sync, size=self._sync, fill=self._sync, radius=self._sync)

    def _sync(self, *_):
        self._color.rgba = self.pressed_fill if self.state == "down" else self.fill
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self.radius]


class AccentButton(SoftButton):
    # The reference uses a near-white pill as the primary action.
    fill = ColorProperty(TEXT)
    pressed_fill = ColorProperty((0.82, 0.82, 0.82, 1))
    color = ColorProperty((0.03, 0.03, 0.03, 1))


class GhostButton(SoftButton):
    fill = ColorProperty((0, 0, 0, 0))
    pressed_fill = ColorProperty(SURFACE_2)
    color = ColorProperty(TEXT)


class PillInput(TextInput):
    background_color = ColorProperty(SURFACE_2)
    foreground_color = ColorProperty(TEXT)
    hint_text_color = ColorProperty(MUTED)
    cursor_color = ColorProperty(ACCENT)

    def __init__(self, **kwargs):
        # Inherited Kivy properties must be set on instances, not replaced by
        # plain class attributes. Replacing font_size/multiline here breaks
        # Kivy's Property metaclass during app startup on Android.
        kwargs.setdefault("padding", [dp(15), dp(12)])
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(rgba=self.background_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(16)])
        self.bind(pos=self._sync, size=self._sync, background_color=self._sync)

    def _sync(self, *_):
        self._color.rgba = self.background_color
        self._rect.pos = self.pos
        self._rect.size = self.size


class BodyLabel(Label):
    color = ColorProperty(TEXT)

    def __init__(self, **kwargs):
        # These are inherited Kivy properties, so keep defaults per instance.
        kwargs.setdefault("font_size", sp(15))
        kwargs.setdefault("halign", "left")
        kwargs.setdefault("valign", "middle")
        kwargs.setdefault("text_size", (None, None))
        super().__init__(**kwargs)


class BaseScreen(Screen):
    def __init__(self, app, **kwargs):
        super().__init__(**kwargs)
        self.app_ref = app
        self.background_color = BG

    def show(self):
        self.opacity = 0
        Animation(opacity=1, duration=0.18, t="out_quad").start(self)


class HomeScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="home", **kwargs)
        root = ScrollView(do_scroll_x=False, bar_width=0)
        content = BoxLayout(
            orientation="vertical",
            padding=[dp(22), dp(26), dp(22), dp(24)],
            spacing=dp(14),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(_aligned_label(
            text="RPG ENGINE  /  YEREL DÜNYA SİMÜLASYONU",
            color=ACCENT, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(20),
        ))
        content.add_widget(_aligned_label(
            text="RPG Engine", color=TEXT, font_size=sp(32), bold=True,
            size_hint_y=None, height=dp(46),
        ))
        content.add_widget(_aligned_label(
            text="Kendi dünyanı kur. Kararların hikâyeyi şekillendirsin.",
            color=MUTED, font_size=sp(14), valign="top",
            size_hint_y=None, height=dp(44),
        ))

        card = RoundedPanel(
            orientation="vertical", padding=[dp(18), dp(16)], spacing=dp(10),
            size_hint_y=None, height=dp(222), fill=SURFACE, radius=dp(24),
        )
        card.add_widget(_aligned_label(
            text="KALDIĞIN YER", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(20),
        ))
        self.status = _aligned_label(
            text="Demo dünyası hazır", color=TEXT, font_size=sp(21), bold=True,
            size_hint_y=None, height=dp(34),
        )
        card.add_widget(self.status)
        self.meta = _aligned_label(
            text="Demo / AI kapalı · Tur 0", color=MUTED, font_size=sp(12),
            size_hint_y=None, height=dp(24),
        )
        card.add_widget(self.meta)
        start = AccentButton(text="Dünyayı aç", size_hint_y=None, height=dp(48))
        start.bind(on_release=lambda *_: self.app_ref.open_gameplay())
        card.add_widget(start)
        content.add_widget(card)

        content.add_widget(_aligned_label(
            text="HIZLI ERİŞİM", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(22),
        ))
        shortcuts = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(54))
        games = SoftButton(text="Oyunlar")
        games.bind(on_release=lambda *_: self.app_ref.open_game())
        ai = SoftButton(text="AI ve API")
        ai.bind(on_release=lambda *_: self.app_ref.open_ai())
        shortcuts.add_widget(games)
        shortcuts.add_widget(ai)
        content.add_widget(shortcuts)

        content.add_widget(_aligned_label(
            text="Senaryolar Oyun bölümünde; model ve API seçenekleri Ayarlar bölümünde.",
            color=MUTED, font_size=sp(12), valign="top",
            size_hint_y=None, height=dp(42),
        ))
        root.add_widget(content)
        self.add_widget(root)

    def refresh(self):
        self.meta.text = f"{self.app_ref.controller.provider_name} · Tur {self.app_ref.controller.turn}"


class MessageBubble(RoundedPanel):
    """Lightweight chat bubble; text reveal is presentation-only and never touches game state."""

    def __init__(self, text="", role="npc", **kwargs):
        kwargs.setdefault("orientation", "vertical")
        kwargs.setdefault("padding", [dp(14), dp(10), dp(14), dp(10)])
        kwargs.setdefault("size_hint_y", None)
        kwargs.setdefault("radius", dp(18))
        kwargs.setdefault("fill", SURFACE if role == "npc" else SURFACE_2)
        kwargs.setdefault("outline", BORDER)
        super().__init__(**kwargs)
        self.role = role
        self._label = Label(
            text=text,
            color=TEXT,
            font_size=sp(15),
            halign="left",
            valign="top",
            size_hint_y=None,
            markup=False,
        )
        self._label.bind(texture_size=self._sync_height)
        self.add_widget(self._label)
        self.bind(width=lambda *_: self._sync_width())
        Clock.schedule_once(lambda *_: self._sync_width(), 0)

    @property
    def text(self):
        return self._label.text

    @text.setter
    def text(self, value):
        self._label.text = value
        self._sync_width()

    def _sync_width(self):
        width = max(dp(40), self.width - dp(28))
        self._label.text_size = (width, None)

    def _sync_height(self, *_):
        self.height = max(dp(44), self._label.texture_size[1] + dp(20))


class GameplayScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="gameplay", **kwargs)
        root = BoxLayout(orientation="vertical", padding=[dp(12), dp(10), dp(12), dp(10)], spacing=dp(8))
        top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        back = GhostButton(text="Geri", size_hint_x=None, width=dp(62), font_size=sp(12))
        back.bind(on_release=lambda *_: self.app_ref.open_home())
        top.add_widget(back)
        self.title = Label(text="Oyun", color=TEXT, font_size=sp(18), bold=True, halign="left")
        self.title.bind(size=lambda *_: setattr(self.title, "text_size", self.title.size))
        top.add_widget(self.title)
        self.turn = _aligned_label(text="Tur 0", color=MUTED, font_size=sp(11), size_hint_x=None, width=dp(58))
        top.add_widget(self.turn)
        root.add_widget(top)

        self.scroll = ScrollView(do_scroll_x=False, bar_width=0)
        self.message_box = BoxLayout(orientation="vertical", spacing=dp(10), padding=[dp(4), dp(6), dp(4), dp(90)], size_hint_y=None)
        self.message_box.bind(minimum_height=self.message_box.setter("height"))
        self.scroll.add_widget(self.message_box)
        root.add_widget(self.scroll)

        composer = RoundedPanel(orientation="horizontal", padding=[dp(6), dp(6)], spacing=dp(6), size_hint_y=None, height=dp(60), fill=(0.12, 0.12, 0.12, 1))
        self.input = PillInput(hint_text="Ne yapmak istiyorsun?", size_hint_x=1)
        self.input.bind(on_text_validate=lambda *_: self.submit())
        composer.add_widget(self.input)
        send = AccentButton(text="Gönder", size_hint_x=None, width=dp(86), font_size=sp(11))
        send.bind(on_release=lambda *_: self.submit())
        composer.add_widget(send)
        root.add_widget(composer)
        self.add_widget(root)
        self._typing_bubble = None
        self._animation_events = set()

    def show(self):
        super().show()
        self.refresh()
        # Keep the Android keyboard closed on entry. The player taps the composer
        # when ready; forcing focus during a screen transition can cause unstable
        # soft-keyboard behavior on some Android builds.

    def refresh(self):
        self.turn.text = f"Tur {self.app_ref.controller.turn}"
        self.title.text = self.app_ref.current_campaign_name()

    def _scroll_bottom(self, *_):
        self.scroll.scroll_y = 0

    def clear_messages(self):
        for event in list(self._animation_events):
            try:
                event.cancel()
            except Exception:
                pass
        self._animation_events.clear()
        self._typing_bubble = None
        self.message_box.clear_widgets()

    def add_message(self, text, role="npc", animate=False):
        if not text:
            return None
        bubble = MessageBubble(text="" if animate else text, role=role)
        bubble.size_hint_x = 0.88
        bubble.pos_hint = {"right": 1} if role == "player" else {"x": 0}
        self.message_box.add_widget(bubble)
        if animate:
            source = str(text)
            index = 0

            def reveal(_dt):
                nonlocal index
                index = min(len(source), index + 3)
                bubble.text = source[:index]
                self._scroll_bottom()
                if index >= len(source):
                    event = events.pop()
                    self._animation_events.discard(event)
                    return False
                return True

            events = []
            event = Clock.schedule_interval(reveal, 0.018)
            events.append(event)
            self._animation_events.add(event)
        Clock.schedule_once(self._scroll_bottom, 0)
        return bubble

    def set_log(self, text):
        self.clear_messages()
        self.add_message(text, role="npc", animate=False)

    def append(self, text):
        return self.add_message(text, role="npc", animate=True)

    def show_typing(self):
        self.remove_typing()
        self._typing_bubble = MessageBubble(text="İşleniyor…", role="npc")
        self._typing_bubble.size_hint_x = 0.38
        self._typing_bubble.pos_hint = {"x": 0}
        self.message_box.add_widget(self._typing_bubble)
        Clock.schedule_once(self._scroll_bottom, 0)

    def remove_typing(self):
        if self._typing_bubble is not None:
            try:
                self.message_box.remove_widget(self._typing_bubble)
            except Exception:
                pass
            self._typing_bubble = None

    def submit(self):
        text = self.input.text.strip()
        if not text or self.app_ref.busy or getattr(self.app_ref, "_lifecycle_stopping", False):
            return
        self.input.text = ""
        self.app_ref.busy = True
        self.add_message(text, role="player")
        self.show_typing()
        Thread(target=self.app_ref._submit_worker, args=(text,), daemon=True).start()


class RecentGamesScreen(BaseScreen):
    """The Oyun tab: resume the active campaign or launch a recent scenario."""

    def __init__(self, app, **kwargs):
        super().__init__(app, name="games", **kwargs)
        root = BoxLayout(
            orientation="vertical", padding=[dp(22), dp(20), dp(22), dp(12)],
            spacing=dp(12),
        )
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(54), spacing=dp(8))
        title = _aligned_label(text="Oyun", color=TEXT, font_size=sp(29), bold=True)
        header.add_widget(title)
        add = AccentButton(text="+ Senaryo", size_hint_x=None, width=dp(128),
                           size_hint_y=None, height=dp(44))
        add.bind(on_release=lambda *_: self.app_ref.import_scenario())
        header.add_widget(add)
        root.add_widget(header)
        root.add_widget(_aligned_label(
            text="Dünyaların ve en son oynadığın maceralar.",
            color=MUTED, font_size=sp(13), size_hint_y=None, height=dp(30),
        ))

        self.list_box = BoxLayout(orientation="vertical", spacing=dp(12), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        scroll.add_widget(self.list_box)
        root.add_widget(scroll)
        self.add_widget(root)

    def show(self):
        super().show()
        self.refresh()

    def refresh(self):
        self.list_box.clear_widgets()
        active = RoundedPanel(
            orientation="vertical", padding=[dp(16), dp(14)], spacing=dp(8),
            size_hint_y=None, height=dp(166), fill=SURFACE, radius=dp(24),
        )
        active.add_widget(_aligned_label(
            text="AKTİF DÜNYA", color=ACCENT, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(20),
        ))
        active.add_widget(_aligned_label(
            text=self.app_ref.current_campaign_name(), color=TEXT, font_size=sp(19), bold=True,
            size_hint_y=None, height=dp(30),
        ))
        active.add_widget(_aligned_label(
            text=f"Tur {self.app_ref.controller.turn}  ·  {self.app_ref.controller.provider_name}",
            color=MUTED, font_size=sp(12), size_hint_y=None, height=dp(22),
        ))
        resume = AccentButton(text="Dünyayı aç", size_hint_y=None, height=dp(44))
        resume.bind(on_release=lambda *_: self.app_ref.open_gameplay())
        active.add_widget(resume)
        self.list_box.add_widget(active)

        self.list_box.add_widget(_aligned_label(
            text="SON OYNANANLAR", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(24),
        ))
        recent = list(self.app_ref.recent_scenarios)
        if not recent:
            empty = RoundedPanel(
                orientation="vertical", padding=dp(16), spacing=dp(8),
                size_hint_y=None, height=dp(132), fill=SURFACE,
            )
            empty.add_widget(_aligned_label(
                text="Henüz senaryo yok", color=TEXT, font_size=sp(16), bold=True,
                size_hint_y=None, height=dp(28),
            ))
            empty.add_widget(_aligned_label(
                text="Sağ üstteki + Senaryo ile ilk dünyanı içe aktar.",
                color=MUTED, font_size=sp(12), valign="top",
                size_hint_y=None, height=dp(42),
            ))
            self.list_box.add_widget(empty)
            return

        installed_ids = {item.scenario_id for item in self.app_ref.controller.installed_scenarios()}
        for item in recent:
            sid = item.get("scenario_id", "")
            name = item.get("name", sid or "Senaryo")
            card = RoundedPanel(
                orientation="horizontal", padding=dp(12), spacing=dp(10),
                size_hint_y=None, height=dp(82), fill=SURFACE,
            )
            info = BoxLayout(orientation="vertical", spacing=dp(4))
            label = _aligned_label(
                text=name, color=TEXT, font_size=sp(14), bold=True,
                size_hint_y=None, height=dp(28),
            )
            info.add_widget(label)
            info.add_widget(_aligned_label(
                text="Demo dünya" if sid == "demo-bootstrap" else
                     ("Kurulu senaryo" if sid in installed_ids else "Son oynanan"),
                color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(22),
            ))
            card.add_widget(info)
            launch = SoftButton(text="Aç", size_hint_x=None, width=dp(72))
            if sid == "demo-bootstrap":
                launch.bind(on_release=lambda *_: self.app_ref.open_gameplay())
            else:
                launch.bind(on_release=lambda *_a, scenario_id=sid: self.app_ref.open_scenario(scenario_id))
            card.add_widget(launch)
            self.list_box.add_widget(card)


class ScenariosScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="scenarios", **kwargs)
        root = BoxLayout(
            orientation="vertical", padding=[dp(20), dp(20), dp(20), dp(12)],
            spacing=dp(12),
        )
        root.add_widget(self._heading(
            "Senaryolar",
            "Kurulu dünyalar ve içe aktarabileceğin .rpgscenario paketleri.",
        ))
        import_btn = AccentButton(
            text="+ Senaryo içe aktar", size_hint_y=None, height=dp(46),
        )
        import_btn.bind(on_release=lambda *_: self.app_ref.import_scenario())
        root.add_widget(import_btn)

        self.list_box = BoxLayout(orientation="vertical", spacing=dp(10), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        scroll.add_widget(self.list_box)
        root.add_widget(scroll)
        self.add_widget(root)

    def _heading(self, title, subtitle):
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(74), spacing=dp(5))
        box.add_widget(_aligned_label(
            text=title, color=TEXT, font_size=sp(28), bold=True,
            size_hint_y=None, height=dp(40),
        ))
        box.add_widget(_aligned_label(
            text=subtitle, color=MUTED, font_size=sp(12), valign="top",
            size_hint_y=None, height=dp(30),
        ))
        return box

    def show(self):
        super().show()
        self.refresh()

    def refresh(self):
        self.list_box.clear_widgets()
        installed = self.app_ref.controller.installed_scenarios()
        if not installed:
            empty = RoundedPanel(
                orientation="vertical", padding=dp(16), spacing=dp(8),
                size_hint_y=None, height=dp(132), fill=SURFACE, radius=dp(20),
            )
            empty.add_widget(_aligned_label(
                text="Henüz senaryo yok", color=TEXT, font_size=sp(16), bold=True,
                size_hint_y=None, height=dp(28),
            ))
            empty.add_widget(_aligned_label(
                text="İlk dünyanı eklemek için yukarıdaki “Senaryo içe aktar” düğmesini kullan.",
                color=MUTED, font_size=sp(12), valign="top",
                size_hint_y=None, height=dp(48),
            ))
            self.list_box.add_widget(empty)
            return
        for item in installed:
            card = RoundedPanel(
                orientation="horizontal", padding=dp(12), spacing=dp(10),
                size_hint_y=None, height=dp(84), fill=SURFACE, radius=dp(18),
            )
            info = BoxLayout(orientation="vertical", spacing=dp(4))
            info.add_widget(_aligned_label(
                text=item.name, color=TEXT, font_size=sp(14), bold=True,
                size_hint_y=None, height=dp(28),
            ))
            info.add_widget(_aligned_label(
                text=f"v{item.version} · {item.chapter_count} bölüm",
                color=MUTED, font_size=sp(11), size_hint_y=None, height=dp(20),
            ))
            card.add_widget(info)
            btn = AccentButton(
                text="Başlat", size_hint_x=None, width=dp(88),
                font_size=sp(12),
            )
            btn.bind(on_release=lambda *_a, sid=item.scenario_id: self.app_ref.open_scenario(sid))
            card.add_widget(btn)
            self.list_box.add_widget(card)


class AIScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="ai", **kwargs)
        root = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(
            orientation="vertical", padding=[dp(20), dp(20), dp(20), dp(28)],
            spacing=dp(12), size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(self._heading(
            "Yapay zekâ",
            "Yerel model veya API sağlayıcısı seç. Model adlarını bilmen gerekmiyor; kataloğu kullanabilirsin.",
        ))

        provider_panel = RoundedPanel(
            orientation="horizontal", padding=dp(14), spacing=dp(10),
            size_hint_y=None, height=dp(68), fill=SURFACE, radius=dp(18),
        )
        status_dot = RoundedPanel(
            orientation="vertical", size_hint=(None, None), size=(dp(10), dp(10)),
            fill=ACCENT, outline=ACCENT, radius=dp(6),
        )
        provider_panel.add_widget(status_dot)
        provider_info = BoxLayout(orientation="vertical", spacing=dp(3))
        provider_info.add_widget(_aligned_label(
            text="AKTİF SAĞLAYICI", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(18),
        ))
        self.provider = _aligned_label(
            text="Demo / AI kapalı", color=TEXT, font_size=sp(14), bold=True,
            size_hint_y=None, height=dp(24),
        )
        provider_info.add_widget(self.provider)
        provider_panel.add_widget(provider_info)
        content.add_widget(provider_panel)

        local = RoundedPanel(
            orientation="vertical", padding=dp(14), spacing=dp(8),
            size_hint_y=None, height=dp(264), fill=SURFACE, radius=dp(22),
        )
        local.add_widget(_aligned_label(
            text="Yerel modeller · Local GGUF", color=TEXT, font_size=sp(17), bold=True,
            size_hint_y=None, height=dp(26),
        ))
        local.add_widget(_aligned_label(
            text="GGUF dosyaları telefonda, uygulamanın özel alanında tutulur.",
            color=MUTED, font_size=sp(12), valign="top",
            size_hint_y=None, height=dp(34),
        ))
        local_actions = BoxLayout(orientation="horizontal", spacing=dp(8),
                                  size_hint_y=None, height=dp(44))
        pick = SoftButton(text="GGUF içe aktar")
        pick.bind(on_release=lambda *_: self.app_ref.import_model())
        local_actions.add_widget(pick)
        advanced = SoftButton(text="Elle indir")
        advanced.bind(on_release=lambda *_: self.open_model_download_dialog())
        local_actions.add_widget(advanced)
        local.add_widget(local_actions)
        self.local_models = BoxLayout(
            orientation="vertical", spacing=dp(5), size_hint_y=None, height=dp(94),
        )
        local.add_widget(self.local_models)
        content.add_widget(local)

        self.hf_catalog = RoundedPanel(
            orientation="vertical", padding=dp(14), spacing=dp(8),
            size_hint_y=None, height=dp(316), fill=SURFACE, radius=dp(22),
        )
        self.hf_catalog.add_widget(_aligned_label(
            text="Hugging Face model kataloğu", color=TEXT, font_size=sp(17), bold=True,
            size_hint_y=None, height=dp(26),
        ))
        self.hf_catalog.add_widget(_aligned_label(
            text="Bir model ailesi seç veya arama yap. Dosya seçmeden hiçbir şey indirilmez.",
            color=MUTED, font_size=sp(11), valign="top",
            size_hint_y=None, height=dp(34),
        ))
        search_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8),
        )
        self.hf_search = PillInput(hint_text="Model veya aile ara")
        self.hf_search.bind(on_text_validate=lambda *_: self.search_remote_models())
        search_row.add_widget(self.hf_search)
        search_button = AccentButton(text="Ara", size_hint_x=None, width=dp(76))
        search_button.bind(on_release=lambda *_: self.search_remote_models())
        search_row.add_widget(search_button)
        self.hf_catalog.add_widget(search_row)

        for presets in (("Qwen", "Llama"), ("Phi", "Gemma")):
            preset_row = BoxLayout(
                orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(34),
            )
            for query in presets:
                preset = SoftButton(text=query, font_size=sp(12))
                preset.bind(on_release=lambda *_a, value=query: self._search_preset(value))
                preset_row.add_widget(preset)
            self.hf_catalog.add_widget(preset_row)

        self.hf_results = BoxLayout(
            orientation="vertical", spacing=dp(6), size_hint_y=None,
        )
        self.hf_results.bind(minimum_height=self.hf_results.setter("height"))
        self.hf_results.add_widget(_aligned_label(
            text="Önerilen ailelerden birini seçerek başla.",
            color=MUTED, font_size=sp(11), valign="top",
            size_hint_y=None, height=dp(28),
        ))
        self.hf_catalog.add_widget(self.hf_results)
        content.add_widget(self.hf_catalog)

        api = RoundedPanel(
            orientation="vertical", padding=dp(14), spacing=dp(8),
            size_hint_y=None, height=dp(424), fill=SURFACE, radius=dp(22),
        )
        api.add_widget(_aligned_label(
            text="API sağlayıcısı", color=TEXT, font_size=sp(17), bold=True,
            size_hint_y=None, height=dp(26),
        ))
        self.api_provider = Spinner(
            text="OpenAI", values=("OpenAI", "Gemini"),
            size_hint_y=None, height=dp(44), font_size=sp(14),
            background_normal="", background_down="",
            background_color=SURFACE_2, color=TEXT,
        )
        self.api_provider.bind(text=lambda *_: self._provider_changed())
        api.add_widget(_field_group("Sağlayıcı", self.api_provider, height=dp(68)))

        self.api_endpoint = PillInput(
            text="https://api.openai.com/v1", hint_text="https://api.openai.com/v1",
        )
        self.api_model = PillInput(
            text="gpt-4.1-mini", hint_text="Örn. gpt-4.1-mini",
        )
        self.api_key = PillInput(
            hint_text="API anahtarını buraya yapıştır", password=True,
        )
        self.api_endpoint_field = _field_group("API endpoint", self.api_endpoint)
        api.add_widget(self.api_endpoint_field)
        api.add_widget(_field_group("Model adı", self.api_model))
        api.add_widget(_field_group("API anahtarı", self.api_key))
        connect = AccentButton(
            text="API ayarlarını uygula", size_hint_y=None, height=dp(46),
        )
        connect.bind(on_release=lambda *_: self.connect_api())
        api.add_widget(connect)
        content.add_widget(api)
        content.add_widget(_aligned_label(
            text="API anahtarı cihazda kalıcı olarak saklanmaz; yalnızca bu oturumda kullanılır. "
                 "Bağlantı, oyun içinde ilk istek gönderildiğinde doğrulanır.",
            color=MUTED, font_size=sp(11), valign="top",
            size_hint_y=None, height=dp(44),
        ))
        self._provider_changed()
        root.add_widget(content)
        self.add_widget(root)

    def _heading(self, title, subtitle):
        box = BoxLayout(orientation="vertical", size_hint_y=None, height=dp(82), spacing=dp(5))
        box.add_widget(_aligned_label(
            text=title, color=TEXT, font_size=sp(28), bold=True,
            size_hint_y=None, height=dp(40),
        ))
        box.add_widget(_aligned_label(
            text=subtitle, color=MUTED, font_size=sp(12), valign="top",
            size_hint_y=None, height=dp(36),
        ))
        return box

    def show(self):
        super().show(); self.refresh()

    def _provider_changed(self):
        gemini = self.api_provider.text == "Gemini"
        self.api_endpoint.disabled = gemini
        self.api_endpoint.opacity = 0.4 if gemini else 1.0
        self.api_endpoint_field.opacity = 0.55 if gemini else 1.0
        if gemini and self.api_model.text.strip() in {"", "gpt-4.1-mini"}:
            self.api_model.text = "gemini-3.6-flash"
        elif not gemini and self.api_model.text.strip() == "gemini-3.6-flash":
            self.api_model.text = "gpt-4.1-mini"

    def refresh(self):
        self.provider.text = self.app_ref.controller.provider_name
        self.local_models.clear_widgets()
        self.local_models.add_widget(_aligned_label(
            text="Modeller kontrol ediliyor…", color=MUTED, font_size=sp(11),
            size_hint_y=None, height=dp(28),
        ))
        token = getattr(self, "_model_refresh_token", 0) + 1
        self._model_refresh_token = token

        def worker():
            try:
                models = self.app_ref.controller.installed_local_models(verify_integrity=False)
                error = None
            except Exception as exc:
                models = []
                error = exc

            def finish(*_):
                if token != self._model_refresh_token:
                    return
                self.local_models.clear_widgets()
                if error is not None:
                    self.local_models.add_widget(_aligned_label(
                        text="Model listesi okunamadı.", color=MUTED, font_size=sp(11),
                        size_hint_y=None, height=dp(28),
                    ))
                    return
                if not models:
                    self.local_models.add_widget(_aligned_label(
                        text="Henüz yerel model yok.", color=MUTED, font_size=sp(11),
                        size_hint_y=None, height=dp(28),
                    ))
                    return
                for model in models[:3]:
                    row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(32))
                    label = _aligned_label(
                        text=f"{model.name} · {model.size_gib:.2f} GiB",
                        color=TEXT, font_size=sp(10), size_hint_y=None, height=dp(32),
                    )
                    row.add_widget(label)
                    button = SoftButton(text="Etkinleştir", size_hint_x=None, width=dp(106),
                                        size_hint_y=None, height=dp(32), font_size=sp(11))
                    button.bind(on_release=lambda *_a, path=str(model.path): self.activate_local_model(path))
                    row.add_widget(button)
                    self.local_models.add_widget(row)

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()

    def _search_preset(self, query):
        self.hf_search.text = query
        self.search_remote_models()

    def _friendly_catalog_error(self, error):
        raw = str(error).lower()
        if any(value in raw for value in (
            "no address associated", "name or service not known",
            "temporary failure in name resolution", "nodename nor servname",
            "urlopen error", "network is unreachable",
        )):
            return "Hugging Face'e ulaşılamadı. İnternet veya DNS bağlantını kontrol edip yeniden dene."
        if "timed out" in raw or "timeout" in raw:
            return "İstek zaman aşımına uğradı. Bağlantını kontrol edip tekrar dene."
        if "401" in raw or "403" in raw:
            return "Bu depoya erişilemiyor olabilir. Herkese açık bir model seçmeyi dene."
        return "Model kataloğu şu anda açılamadı. Biraz sonra tekrar deneyebilirsin."

    def search_remote_models(self):
        query = self.hf_search.text.strip()
        if not query:
            self.app_ref.notify("Bir model ailesi seç veya arama alanına bir kelime yaz.")
            return
        token = getattr(self, "_hf_search_token", 0) + 1
        self._hf_search_token = token
        self.hf_results.clear_widgets()
        self.hf_results.add_widget(_aligned_label(
            text=f"“{query}” aranıyor…", color=MUTED, font_size=sp(12),
            size_hint_y=None, height=dp(30),
        ))
        self.hf_catalog.height = dp(316)

        def worker():
            try:
                models = self.app_ref.controller.search_remote_models(query, limit=8)
                error = None
            except Exception as exc:
                models = []
                error = exc

            def finish(*_):
                if token != self._hf_search_token:
                    return
                self.hf_results.clear_widgets()
                if error is not None:
                    panel = RoundedPanel(
                        orientation="vertical", padding=dp(10), spacing=dp(6),
                        size_hint_y=None, height=dp(100), fill=SURFACE_2, radius=dp(14),
                    )
                    panel.add_widget(_aligned_label(
                        text="Kataloğa bağlanılamadı", color=TEXT, font_size=sp(13), bold=True,
                        size_hint_y=None, height=dp(24),
                    ))
                    panel.add_widget(_aligned_label(
                        text=self._friendly_catalog_error(error), color=MUTED, font_size=sp(11),
                        valign="top", size_hint_y=None, height=dp(40),
                    ))
                    retry = SoftButton(text="Tekrar dene", size_hint_y=None, height=dp(34),
                                       font_size=sp(11))
                    retry.bind(on_release=lambda *_: self.search_remote_models())
                    panel.add_widget(retry)
                    self.hf_results.add_widget(panel)
                    self.hf_catalog.height = dp(378)
                    return
                if not models:
                    panel = RoundedPanel(
                        orientation="vertical", padding=dp(10), spacing=dp(4),
                        size_hint_y=None, height=dp(78), fill=SURFACE_2, radius=dp(14),
                    )
                    panel.add_widget(_aligned_label(
                        text="Eşleşme bulunamadı", color=TEXT, font_size=sp(13), bold=True,
                        size_hint_y=None, height=dp(24),
                    ))
                    panel.add_widget(_aligned_label(
                        text="Qwen, Llama, Phi veya Gemma aramalarını deneyebilirsin.",
                        color=MUTED, font_size=sp(11), valign="top",
                        size_hint_y=None, height=dp(34),
                    ))
                    self.hf_results.add_widget(panel)
                    self.hf_catalog.height = dp(354)
                    return
                visible = models[:6]
                for model in visible:
                    card = RoundedPanel(
                        orientation="horizontal", padding=dp(9), spacing=dp(8),
                        size_hint_y=None, height=dp(64), fill=SURFACE_2, radius=dp(14),
                    )
                    info = BoxLayout(orientation="vertical", spacing=dp(2))
                    name = _aligned_label(
                        text=model.repo_id, color=TEXT, font_size=sp(11), bold=True,
                        size_hint_y=None, height=dp(34),
                    )
                    info.add_widget(name)
                    info.add_widget(_aligned_label(
                        text=f"{model.downloads:,} indirme · {model.likes:,} beğeni",
                        color=MUTED, font_size=sp(10), size_hint_y=None, height=dp(16),
                    ))
                    card.add_widget(info)
                    files_button = SoftButton(
                        text="GGUF seç", size_hint_x=None, width=dp(88),
                        font_size=sp(11),
                    )
                    files_button.bind(
                        on_release=lambda *_a, repo=model.repo_id: self.show_remote_model_files(repo)
                    )
                    card.add_widget(files_button)
                    self.hf_results.add_widget(card)
                self.hf_catalog.height = dp(270 + len(visible) * 70)

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()


    def show_remote_model_files(self, repo_id):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        status = _aligned_label(
            text="GGUF dosyaları yükleniyor…", color=MUTED, font_size=sp(12),
            valign="top", size_hint_y=None, height=dp(62),
        )
        box.add_widget(status)
        files_box = BoxLayout(orientation="vertical", spacing=dp(6), size_hint_y=None)
        files_box.bind(minimum_height=files_box.setter("height"))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        scroll.add_widget(files_box)
        box.add_widget(scroll)
        close = SoftButton(text="Kapat", size_hint_y=None, height=dp(42))
        box.add_widget(close)
        popup = Popup(title=repo_id, content=box, size_hint=(0.96, 0.78),
                      background_color=SURFACE)
        close.bind(on_release=lambda *_: popup.dismiss())
        popup.open()

        def worker():
            try:
                files = self.app_ref.controller.remote_model_files(repo_id)
                error = None
            except Exception as exc:
                files = []
                error = exc

            def finish(*_):
                files_box.clear_widgets()
                if error is not None:
                    status.text = self._friendly_catalog_error(error)
                    return
                if not files:
                    status.text = "Uygun GGUF dosyası bulunamadı. Bu depoda dosya olmayabilir veya dosyalar indirme sınırını aşıyor olabilir."
                    return
                status.text = "İndirmek istediğin dosyayı seç. Dosya boyutu indirme öncesinde kontrol edilir."
                for item in files:
                    size = f"{item.size_gib:.2f} GiB" if item.size_gib is not None else "Boyut doğrulanacak"
                    row = BoxLayout(orientation="horizontal", spacing=dp(8),
                                    size_hint_y=None, height=dp(56))
                    info = _aligned_label(
                        text=f"{item.filename}\n{size}", color=TEXT, font_size=sp(11),
                        size_hint_y=None, height=dp(50),
                    )
                    row.add_widget(info)
                    choose = AccentButton(text="Seç", size_hint_x=None, width=dp(68))
                    choose.bind(on_release=lambda *_a, file=item: (
                        popup.dismiss(),
                        self.open_model_download_dialog(repo_id, file.filename, file.size_bytes)
                    ))
                    row.add_widget(choose)
                    files_box.add_widget(row)

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()

    def open_model_download_dialog(self, repo_id="", filename="", expected_size_bytes=None):
        if getattr(self.app_ref, "_model_download_in_progress", False):
            self.app_ref.notify("Model indirme zaten devam ediyor.")
            return
        box = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(8))
        box.add_widget(_aligned_label(
            text="Yalnızca seçtiğin GGUF dosyası indirilir. Dosya boyutu ve bütünlüğü kontrol edilir.",
            color=MUTED, font_size=sp(11), valign="top",
            size_hint_y=None, height=dp(42),
        ))
        repo = PillInput(text=repo_id, hint_text="Örn. organization/model")
        filename = PillInput(text=filename, hint_text="Örn. model.Q4_K_M.gguf")
        revision = PillInput(text="main", hint_text="main veya commit etiketi")
        sha = PillInput(hint_text="İsteğe bağlı SHA-256")
        for caption, widget in (
            ("Hugging Face deposu", repo),
            ("GGUF dosya adı", filename),
            ("Sürüm", revision),
            ("Bütünlük doğrulaması", sha),
        ):
            box.add_widget(_field_group(caption, widget))
        progress = ProgressBar(max=100, value=0, size_hint_y=None, height=dp(8))
        status = _aligned_label(
            text="İndirmeye hazır.", color=MUTED, font_size=sp(11), valign="top",
            size_hint_y=None, height=dp(34),
        )
        box.add_widget(progress)
        box.add_widget(status)
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = SoftButton(text="İptal")
        start = AccentButton(text="İndir")
        actions.add_widget(cancel)
        actions.add_widget(start)
        box.add_widget(actions)
        popup = Popup(
            title="Model indir", content=box, size_hint=(0.94, 0.80),
            background_color=SURFACE, separator_color=ACCENT, auto_dismiss=False,
        )
        cancel.bind(on_release=lambda *_: popup.dismiss())

        def worker():
            try:
                spec = ModelSpec(
                    repo.text.strip(),
                    filename.text.strip(),
                    revision=revision.text.strip() or "main",
                    expected_size_bytes=expected_size_bytes,
                    expected_sha256=sha.text.strip() or None,
                )
                spec.validate()

                def progress_callback(written, total):
                    def update(*_):
                        if total:
                            progress.value = min(100, (written / total) * 100)
                            status.text = f"{written / (1024 ** 3):.2f} / {total / (1024 ** 3):.2f} GiB"
                        else:
                            status.text = f"{written / (1024 ** 3):.2f} GiB indirildi"
                    Clock.schedule_once(update, 0)

                installed = self.app_ref.controller.download_local_model(
                    spec, progress_callback=progress_callback
                )
                message = f"Model indirildi: {installed.name}"
            except Exception as exc:
                message = f"Model indirilemedi: {exc}"

            def finish(*_):
                self.app_ref._model_download_in_progress = False
                popup.dismiss()
                self.app_ref.notify(message)
                self.refresh()

            Clock.schedule_once(finish, 0)

        def start_download(*_):
            if not repo.text.strip() or not filename.text.strip():
                status.text = "Repository ve GGUF dosya adı zorunlu."
                return
            self.app_ref._model_download_in_progress = True
            start.disabled = True
            cancel.disabled = True
            status.text = "Model doğrulanıyor ve indiriliyor…"
            Thread(target=worker, daemon=True).start()

        start.bind(on_release=start_download)
        popup.open()

    def activate_local_model(self, path):
        if getattr(self.app_ref, "_model_activation_in_progress", False):
            return
        self.app_ref._model_activation_in_progress = True
        self.app_ref.notify("Local model doğrulanıyor ve başlatılıyor…")

        def worker():
            try:
                self.app_ref.controller.set_local_model(path)
                message = "Local model etkinleştirildi."
            except Exception as exc:
                message = f"Local model başlatılamadı: {exc}"

            def finish(*_):
                self.app_ref._model_activation_in_progress = False
                self.app_ref.notify(message)
                self.refresh()

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()

    def connect_api(self):
        api_key = self.api_key.text.strip()
        model_name = self.api_model.text.strip()
        if not api_key:
            self.app_ref.notify("API anahtarı gerekli.")
            return
        if not model_name:
            self.app_ref.notify("Model adı gerekli.")
            return
        try:
            if self.api_provider.text == "Gemini":
                self.app_ref.controller.set_gemini(api_key, model_name)
                message = "Gemini ayarları uygulandı. Bağlantı ilk istek gönderildiğinde kontrol edilir."
            else:
                self.app_ref.controller.set_openai_compatible(
                    self.api_endpoint.text.strip(), api_key, model_name
                )
                message = "API ayarları uygulandı. Bağlantı ilk istek gönderildiğinde kontrol edilir."
            self.api_key.text = ""
            self.app_ref.notify(message)
            self.refresh()
        except Exception as exc:
            self.app_ref.notify(f"API ayarı başarısız: {exc}")


class SettingsScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="settings", **kwargs)
        root = ScrollView(do_scroll_x=False, bar_width=dp(3))
        content = BoxLayout(
            orientation="vertical", padding=[dp(22), dp(22), dp(22), dp(26)],
            spacing=dp(12), size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))
        content.add_widget(_aligned_label(
            text="Ayarlar", color=TEXT, font_size=sp(29), bold=True,
            size_hint_y=None, height=dp(42),
        ))
        content.add_widget(_aligned_label(
            text="Kayıt, dünya ve yapay zekâ tercihlerini buradan yönet.",
            color=MUTED, font_size=sp(13), valign="top",
            size_hint_y=None, height=dp(42),
        ))

        saves = RoundedPanel(
            orientation="vertical", padding=dp(14), spacing=dp(10),
            size_hint_y=None, height=dp(128), fill=SURFACE, radius=dp(20),
        )
        saves.add_widget(_aligned_label(
            text="KAMPANYA KAYDI", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(20),
        ))
        save_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(48))
        save_btn = SoftButton(text="Kaydet")
        save_btn.bind(on_release=lambda *_: app.save())
        load_btn = SoftButton(text="Kayıt yükle")
        load_btn.bind(on_release=lambda *_: app.load())
        save_row.add_widget(save_btn)
        save_row.add_widget(load_btn)
        saves.add_widget(save_row)
        content.add_widget(saves)

        worlds = RoundedPanel(
            orientation="vertical", padding=dp(14), spacing=dp(8),
            size_hint_y=None, height=dp(112), fill=SURFACE, radius=dp(20),
        )
        worlds.add_widget(_aligned_label(
            text="SENARYOLAR", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(18),
        ))
        world_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(44))
        world_row.add_widget(_aligned_label(
            text="Kurulu dünyaları ve senaryo paketlerini yönet.",
            color=TEXT, font_size=sp(12),
        ))
        world_btn = AccentButton(text="Aç", size_hint_x=None, width=dp(78))
        world_btn.bind(on_release=lambda *_: app.open_scenarios())
        world_row.add_widget(world_btn)
        worlds.add_widget(world_row)
        content.add_widget(worlds)

        ai = RoundedPanel(
            orientation="vertical", padding=dp(14), spacing=dp(8),
            size_hint_y=None, height=dp(112), fill=SURFACE, radius=dp(20),
        )
        ai.add_widget(_aligned_label(
            text="YAPAY ZEKÂ", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(18),
        ))
        ai_row = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(44))
        ai_row.add_widget(_aligned_label(
            text="Yerel GGUF modelleri ve API sağlayıcıları.",
            color=TEXT, font_size=sp(12),
        ))
        ai_btn = AccentButton(text="Yapılandır", size_hint_x=None, width=dp(116))
        ai_btn.bind(on_release=lambda *_: app.open_ai())
        ai_row.add_widget(ai_btn)
        ai.add_widget(ai_row)
        content.add_widget(ai)

        content.add_widget(_aligned_label(
            text=f"RPG Engine v{__version__}  ·  Android API 36  ·  Kivy 2.3.1",
            color=MUTED, font_size=sp(11), valign="top",
            size_hint_y=None, height=dp(40),
        ))
        root.add_widget(content)
        self.add_widget(root)


class RPGEngineApp(App):
    title = "RPG Engine"

    def build(self):
        Window.clearcolor = BG
        Window.softinput_mode = "below_target"
        self.busy = False
        self._lifecycle_stopping = False
        self._gameplay_initialized = False
        self._autosave_pending = False
        self._saf_import_in_progress = False
        self._model_import_in_progress = False
        self._model_activation_in_progress = False
        self._model_download_in_progress = False

        try:
            self.controller = AppController.demo()
            self.recent_scenarios = []
            try:
                recent_path = Path(self.user_data_dir) / "recent_scenarios.json"
                recent_path.parent.mkdir(parents=True, exist_ok=True)
                self._recent_store = JsonStore(str(recent_path))
                if self._recent_store.exists("recent"):
                    self.recent_scenarios = list(self._recent_store.get("recent").get("items", []))
            except Exception:
                self._recent_store = None
            self.manager = ScreenManager(transition=SlideTransition(duration=0.16))
            self.home = HomeScreen(self)
            self.games = RecentGamesScreen(self)
            self.game = GameplayScreen(self)
            self.scenarios = ScenariosScreen(self)
            self.ai = AIScreen(self)
            self.settings = SettingsScreen(self)
            for screen in (self.home, self.games, self.game, self.scenarios, self.ai, self.settings):
                self.manager.add_widget(screen)

            root = BoxLayout(orientation="vertical", spacing=0)
            root.add_widget(self.manager)
            root.add_widget(self._bottom_nav())
            self.manager.current = "home"
            self._update_nav_state()
            self._record_recent_scenario("demo-bootstrap", "Demo dünyası")
            Clock.schedule_once(lambda *_: self.home.refresh(), 0)
            return root
        except Exception as exc:
            # Do not let a first-launch initialization exception immediately
            # terminate the app with no visible diagnostic. main.py also logs
            # failures that happen before this module can be imported.
            from pathlib import Path
            import traceback
            try:
                diagnostics = Path.cwd() / "diagnostics"
                diagnostics.mkdir(parents=True, exist_ok=True)
                (diagnostics / "build_error.log").write_text(
                    "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                    encoding="utf-8",
                )
                diagnostic_path = str(diagnostics / "build_error.log")
            except Exception:
                diagnostic_path = "diagnostics/build_error.log"

            root = BoxLayout(orientation="vertical", padding=dp(24), spacing=dp(18))
            root.add_widget(Label(
                text="RPG Engine başlatılamadı",
                color=TEXT,
                font_size=sp(24),
                halign="left",
                valign="middle",
                size_hint_y=None,
                height=dp(52),
            ))
            detail = Label(
                text=(
                    "İlk açılışta uygulama kurulumu başarısız oldu.\n\n"
                    f"{type(exc).__name__}: {exc}\n\n"
                    f"Tanı kaydı: {diagnostic_path}"
                ),
                color=TEXT,
                halign="left",
                valign="top",
            )
            detail.bind(size=lambda *_: setattr(detail, "text_size", detail.size))
            root.add_widget(detail)
            return root

    def _bottom_nav(self):
        # Text-first labels are reliable with the fonts packaged by Android.
        nav = RoundedPanel(
            orientation="horizontal", padding=[dp(8), dp(6)], spacing=dp(6),
            size_hint=(1, None), height=dp(62),
            fill=FOOTER_SURFACE, radius=dp(24),
        )
        self.nav_buttons = {}
        for label, target in (("Oyun", "games"), ("Ana", "home"), ("Ayarlar", "settings")):
            button = GhostButton(text=label, font_size=sp(13), radius=dp(20))
            button.bind(on_release=lambda *_a, t=target: self.go(t))
            nav.add_widget(button)
            self.nav_buttons[target] = button
        return nav

    def _update_nav_state(self):
        current = self.manager.current
        active = (
            "games" if current in {"games", "gameplay", "scenarios"}
            else "settings" if current == "ai"
            else current
        )
        for target, button in getattr(self, "nav_buttons", {}).items():
            selected = target == active
            button.fill = SURFACE_2 if selected else (0, 0, 0, 0)
            button.color = TEXT if selected else MUTED

    def go(self, screen):
        self.manager.transition.direction = "right" if screen in {"home", "games"} else "left"
        self.manager.current = screen
        target = self.manager.get_screen(screen)
        self._update_nav_state()
        if hasattr(target, "show"):
            target.show()

    def open_home(self): self.go("home")
    def open_game(self): self.go("games")
    def open_gameplay(self):
        # The home screen can be opened before any scenario has ever been played.
        # Initialize the deterministic look/status log once instead of presenting
        # an empty chat surface or relying on an implicit previous game.
        if not getattr(self, "_gameplay_initialized", False):
            self._initial_game()
        self.go("gameplay")
    def open_scenarios(self): self.go("scenarios")
    def open_ai(self): self.go("ai")

    def current_campaign_name(self):
        pack = getattr(self.controller, "scenario_pack", None)
        if pack is not None:
            return getattr(pack, "name", self.controller.scenario_id)
        return "Demo dünyası" if self.controller.scenario_id == "demo-bootstrap" else self.controller.scenario_id

    def _record_recent_scenario(self, scenario_id, name):
        item = {"scenario_id": str(scenario_id), "name": str(name)}
        self.recent_scenarios = [old for old in self.recent_scenarios
                                 if old.get("scenario_id") != item["scenario_id"]]
        self.recent_scenarios.insert(0, item)
        self.recent_scenarios = self.recent_scenarios[:8]
        try:
            if self._recent_store is not None:
                self._recent_store.put("recent", items=self.recent_scenarios)
        except Exception:
            pass
        if hasattr(self, "games"):
            self.games.refresh()

    def notify(self, text):
        body = BoxLayout(
            orientation="vertical", padding=[dp(16), dp(12)], spacing=dp(10),
        )
        message = _aligned_label(
            text=str(text), color=TEXT, font_size=sp(14), valign="middle",
        )
        body.add_widget(message)
        dismiss = AccentButton(text="Tamam", size_hint_y=None, height=dp(42))
        body.add_widget(dismiss)
        popup = Popup(
            title="RPG Engine", content=body, size_hint=(0.90, None), height=dp(178),
            background_color=SURFACE, separator_color=ACCENT, auto_dismiss=True,
        )
        dismiss.bind(on_release=lambda *_: popup.dismiss())
        popup.open()
        Clock.schedule_once(lambda *_: popup.dismiss(), 5.0)

    def _append(self, text):
        self.game.append(text)

    def _submit_worker(self, text):
        try:
            result = self.controller.submit(text)
        except Exception as exc:
            result = f"[İşlem başarısız: {exc}]"
        Clock.schedule_once(lambda *_: self._finish_submit(result), 0)

    def _finish_submit(self, result):
        self.busy = False
        # Persistence is deliberately independent from presentation animation.
        if self.controller.dirty:
            self._autosave("turn")
        if self._autosave_pending:
            self._autosave_pending = False
            if self.controller.dirty:
                self._autosave("deferred")
        self.game.remove_typing()
        self.game.append(result)
        self.game.refresh()
        self.home.refresh()
        if self._lifecycle_stopping:
            try:
                self.controller.shutdown()
            except Exception:
                pass

    def _initial_game(self):
        try:
            opening = self.controller.submit("look")
        except Exception as exc:
            self._record_gameplay_error("initial_world_view", exc)
            opening = (
                "Dünya görünümü yüklenemedi. Ana menüye dönüp yeniden deneyebilirsin.\n"
                f"Tanı: {type(exc).__name__}"
            )
            self._gameplay_initialized = False
        else:
            self._gameplay_initialized = True
        self.game.set_log("RPG Engine\n" + opening)
        self.game.refresh()
        return self._gameplay_initialized

    def _record_gameplay_error(self, stage, exc):
        try:
            target = self._diagnostic_dir() / "gameplay_error.log"
            import traceback
            target.write_text(
                f"stage={stage}\nerror={type(exc).__name__}: {exc}\n\n"
                + "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                encoding="utf-8",
            )
        except Exception:
            pass

    def save(self):
        try:
            self.controller.save()
            self.notify("Oyun kaydedildi.")
        except Exception as exc:
            self.notify(f"Kaydetme başarısız: {exc}")

    def load(self):
        try:
            self.controller.load()
            self.game.set_log("Kayıt yüklendi.\n" + self.controller.submit("status"))
            self._gameplay_initialized = True
            self.game.refresh(); self.home.refresh()
        except Exception as exc:
            self.notify(f"Kayıt yüklenemedi: {exc}")

    def import_scenario(self):
        if self._saf_import():
            return
        chooser = FileChooserListView(filters=["*.zip", "*.rpgscenario.zip"], path=str(Path.home()))
        box = BoxLayout(orientation="vertical")
        box.add_widget(chooser)
        popup = Popup(title="Senaryo içe aktar", content=box, size_hint=(0.96, 0.88), background_color=SURFACE)
        actions = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        actions.add_widget(SoftButton(text="İptal", on_release=popup.dismiss))
        def do_import(*_):
            if not chooser.selection: return
            try:
                pack = self.controller.install_scenario(chooser.selection[0])
                popup.dismiss(); self.notify(f"{pack.name} yüklendi."); self.open_scenarios()
            except Exception as exc: self.notify(f"Import başarısız: {exc}")
        actions.add_widget(AccentButton(text="İçe aktar", on_release=do_import))
        box.add_widget(actions); popup.open()

    def _saf_import(self):
        if self._saf_import_in_progress: return True
        try:
            from rpg_android_file_picker import open_scenario_document
        except ImportError:
            return False
        self._saf_import_in_progress = True
        try:
            launched = open_scenario_document(self._on_saf_import)
        except Exception as exc:
            self._saf_import_in_progress = False; self.notify(str(exc)); return False
        if not launched: self._saf_import_in_progress = False
        return launched

    def _on_saf_import(self, path):
        Clock.schedule_once(lambda *_: self._finish_saf_import(path), 0)

    def _finish_saf_import(self, path):
        self._saf_import_in_progress = False
        try:
            pack = self.controller.install_scenario(path)
            self.notify(f"Senaryo yüklendi: {pack.name}"); self.open_scenarios()
        except Exception as exc:
            self.notify(f"Import başarısız: {exc}")

    def open_scenario(self, scenario_id):
        try:
            pack = self.controller.load_installed_scenario(scenario_id)
            self.controller.start_scenario(pack)
            self._gameplay_initialized = False
            self._record_recent_scenario(pack.scenario_id, pack.name)
            self.open_gameplay()
        except Exception as exc:
            self.notify(f"Senaryo başlatılamadı: {exc}")

    def import_model(self):
        if self._model_import_in_progress: return
        try:
            from rpg_android_file_picker import open_model_document
        except ImportError:
            self._desktop_model_picker(); return
        self._model_import_in_progress = True
        try:
            launched = open_model_document(self._on_model_import)
        except Exception as exc:
            self._model_import_in_progress = False; self.notify(str(exc)); return
        if not launched:
            self._model_import_in_progress = False; self._desktop_model_picker()

    def _desktop_model_picker(self):
        chooser = FileChooserListView(filters=["*.gguf"], path=str(Path.home()))
        box = BoxLayout(orientation="vertical"); box.add_widget(chooser)
        popup = Popup(title="GGUF model seç", content=box, size_hint=(0.96, 0.88), background_color=SURFACE)
        actions = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(8))
        actions.add_widget(SoftButton(text="İptal", on_release=popup.dismiss))
        def choose(*_):
            if not chooser.selection: return
            popup.dismiss(); self._activate_local_model(chooser.selection[0], cleanup_source=False)
        actions.add_widget(AccentButton(text="Modeli seç", on_release=choose))
        box.add_widget(actions); popup.open()

    def _on_model_import(self, path):
        Clock.schedule_once(lambda *_: self._finish_model_import(path), 0)

    def _finish_model_import(self, path):
        self._model_import_in_progress = False
        self._activate_local_model(path, cleanup_source=True)

    def _activate_local_model(self, path, *, cleanup_source=False):
        if self._model_activation_in_progress:
            return
        self._model_activation_in_progress = True
        self.notify("Local model içe aktarılıyor…")

        def worker():
            try:
                installed = self.controller.install_local_model(path)
                if cleanup_source:
                    Path(path).unlink(missing_ok=True)
                message = f"Local model içe aktarıldı: {installed.name}"
            except Exception as exc:
                message = f"Local model içe aktarılamadı: {exc}"

            def finish(*_):
                self._model_activation_in_progress = False
                self.notify(message)
                self.ai.refresh()

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()

    def on_start(self):
        self._show_autosave_diagnostic_if_present()

    def on_pause(self):
        self._autosave("pause")
        return True

    def on_stop(self):
        self._lifecycle_stopping = True
        self._autosave("stop")
        # Do not intentionally tear down a live native AI runtime while a
        # gameplay worker is still completing its transaction. The worker's
        # completion path performs the final shutdown when possible.
        if not self.busy:
            try:
                self.controller.shutdown()
            except Exception:
                pass

    def _diagnostic_dir(self):
        try:
            from engine.persistence.saves import default_save_dir
            path = default_save_dir().parent / "diagnostics"
        except Exception:
            path = Path.home() / ".rpg_engine" / "diagnostics"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _record_autosave_error(self, reason, exc):
        try:
            target = self._diagnostic_dir() / "autosave_error.log"
            target.write_text(
                f"reason={reason}\nerror={type(exc).__name__}: {exc}\n",
                encoding="utf-8",
            )
        except Exception:
            pass

    def _show_autosave_diagnostic_if_present(self):
        try:
            target = self._diagnostic_dir() / "autosave_error.log"
            if not target.exists():
                return
            detail = target.read_text(encoding="utf-8", errors="replace").strip()
            self.notify(f"Önceki otomatik kayıt sırasında hata oluştu.\n{detail}")
            target.unlink(missing_ok=True)
        except Exception:
            pass

    def _autosave(self, reason):
        if not self.controller.dirty:
            return
        if self.busy:
            self._autosave_pending = True
            return
        try:
            self.controller.save()
        except Exception as exc:
            self._record_autosave_error(reason, exc)


if __name__ == "__main__":
    RPGEngineApp().run()
