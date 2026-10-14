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
from kivy.uix.widget import Widget
from kivy.storage.jsonstore import JsonStore
from kivy.graphics import Color, RoundedRectangle, Line

from engine import __version__
from engine.app.controller import AppController
from engine.ai.model_manager import ModelSpec, check_huggingface_connection
from engine.ai.connectivity import APIConnectionError, check_api_connection


# Semantic dark-theme tokens: one source of truth for surfaces, text and actions.
# Keep the canvas near-black, panels charcoal, and green reserved for active/status states.
BG = (0.0, 0.0, 0.0, 1)                       # #000000
SURFACE = (17 / 255, 17 / 255, 17 / 255, 1)   # #111111
SURFACE_2 = (26 / 255, 26 / 255, 26 / 255, 1) # #1A1A1A
SURFACE_PRESSED = (43 / 255, 43 / 255, 43 / 255, 1) # #2B2B2B
BORDER = (1.0, 1.0, 1.0, 0.10)
TEXT = (0.98, 0.98, 0.98, 1)                  # primary text
TEXT_MUTED = (0.61, 0.64, 0.69, 1)            # secondary text
PRIMARY_ACTION = (0.98, 0.98, 0.98, 1)        # light primary action surface
PRIMARY_ACTION_TEXT = (0.035, 0.035, 0.035, 1) # dark text on light action
ACCENT = (22 / 255, 163 / 255, 74 / 255, 1)   # status/active only
DANGER = (0.86, 0.15, 0.15, 1)
FOOTER_SURFACE = (10 / 255, 10 / 255, 10 / 255, 1)

# Backwards-compatible alias while screens migrate to semantic names.
MUTED = TEXT_MUTED


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
    pressed_fill = ColorProperty(SURFACE_PRESSED)
    disabled_fill = ColorProperty(SURFACE_2)
    radius = NumericProperty(dp(22))

    def __init__(self, **kwargs):
        # Set visual defaults on the instance. This keeps subclass overrides
        # predictable under Kivy's property system and Android rendering.
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_down", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        kwargs.setdefault("color", TEXT)
        kwargs.setdefault("disabled_color", MUTED)
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("bold", False)
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(rgba=self.fill)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[self.radius])
        self.bind(
            pos=self._sync,
            size=self._sync,
            fill=self._sync,
            pressed_fill=self._sync,
            disabled_fill=self._sync,
            radius=self._sync,
            state=self._sync,
            disabled=self._sync,
        )
        self._sync()

    def _sync(self, *_):
        self._color.rgba = (
            self.disabled_fill if self.disabled
            else self.pressed_fill if self.state == "down"
            else self.fill
        )
        self._rect.pos = self.pos
        self._rect.size = self.size
        self._rect.radius = [self.radius]


class AccentButton(SoftButton):
    # Primary actions use a light surface and explicitly dark, readable text.
    fill = ColorProperty(PRIMARY_ACTION)
    pressed_fill = ColorProperty((0.82, 0.82, 0.82, 1))
    disabled_fill = ColorProperty((0.32, 0.32, 0.32, 1))
    color = ColorProperty(PRIMARY_ACTION_TEXT)

    def __init__(self, **kwargs):
        kwargs.setdefault("color", PRIMARY_ACTION_TEXT)
        kwargs.setdefault("disabled_color", (0.25, 0.25, 0.25, 1))
        kwargs.setdefault("font_size", sp(14))
        super().__init__(**kwargs)

class GhostButton(SoftButton):
    fill = ColorProperty((0, 0, 0, 0))
    pressed_fill = ColorProperty(SURFACE_2)
    color = ColorProperty(TEXT)


class PillInput(TextInput):
    # Draw the rounded surface ourselves; Kivy's built-in rectangular
    # TextInput background must remain transparent or it covers the pill.
    background_color = ColorProperty((0, 0, 0, 0))
    fill_color = ColorProperty(SURFACE_2)
    foreground_color = ColorProperty(TEXT)
    hint_text_color = ColorProperty(MUTED)
    cursor_color = ColorProperty(ACCENT)

    def __init__(self, **kwargs):
        # Keep the native TextInput background transparent so its rectangular
        # canvas does not paint over the rounded surface.
        kwargs.setdefault("padding", [dp(15), dp(10)])
        kwargs.setdefault("font_size", sp(14))
        kwargs.setdefault("multiline", False)
        kwargs.setdefault("background_normal", "")
        kwargs.setdefault("background_active", "")
        kwargs.setdefault("background_color", (0, 0, 0, 0))
        super().__init__(**kwargs)
        with self.canvas.before:
            self._color = Color(rgba=self.fill_color)
            self._rect = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(18)])
        self.bind(pos=self._sync, size=self._sync, fill_color=self._sync)

    def _sync(self, *_):
        self._color.rgba = self.fill_color
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
            text="Henüz dünya seçilmedi", color=TEXT, font_size=sp(21), bold=True,
            size_hint_y=None, height=dp(34),
        )
        card.add_widget(self.status)
        self.meta = _aligned_label(
            text="Bir senaryo içe aktar veya Senaryo Atölyesi'nden oluştur.",
            color=MUTED, font_size=sp(12), size_hint_y=None, height=dp(24),
        )
        card.add_widget(self.meta)
        start = AccentButton(text="Senaryoları aç", size_hint_y=None, height=dp(48))
        start.bind(on_release=lambda *_: self.app_ref.open_current_campaign_or_scenarios())
        self.start_button = start
        card.add_widget(start)
        content.add_widget(card)

        content.add_widget(_aligned_label(
            text="HIZLI ERİŞİM", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(22),
        ))
        shortcuts = BoxLayout(orientation="horizontal", spacing=dp(10), size_hint_y=None, height=dp(54))
        games = SoftButton(text="Oyunlar")
        games.bind(on_release=lambda *_: self.app_ref.open_game())
        settings = SoftButton(text="Ayarlar")
        settings.bind(on_release=lambda *_: self.app_ref.go("settings"))
        shortcuts.add_widget(games)
        shortcuts.add_widget(settings)
        content.add_widget(shortcuts)

        content.add_widget(_aligned_label(
            text="Senaryolar Oyun bölümünde. Model, Hugging Face ve API seçenekleri Ayarlar > Yapay zekâ bölümünde.",
            color=MUTED, font_size=sp(12), valign="top",
            size_hint_y=None, height=dp(42),
        ))
        root.add_widget(content)
        self.add_widget(root)

    def refresh(self):
        pack = getattr(self.app_ref.controller, "scenario_pack", None)
        if pack is None:
            self.status.text = "Henüz dünya seçilmedi"
            self.meta.text = "Senaryoları açıp dünya seç veya yeni senaryo oluştur."
            self.start_button.text = "Senaryoları aç"
        else:
            self.status.text = pack.name
            self.meta.text = f"{self.app_ref.controller.provider_name} · Tur {self.app_ref.controller.turn}"
            self.start_button.text = "Dünyayı aç"


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
        self.fill = SURFACE_2 if role == "player" else SURFACE
        self.outline = (
            (ACCENT[0], ACCENT[1], ACCENT[2], 0.35)
            if role == "player" else DANGER if role == "error" else BORDER
        )
        role_caption = {
            "player": ("SEN", ACCENT),
            "error": ("HATA", DANGER),
        }
        caption, caption_color = role_caption.get(role, ("ANLATI", MUTED))
        self._role_label = Label(
            text=caption,
            color=caption_color,
            font_size=sp(9),
            bold=True,
            halign="left",
            valign="middle",
            size_hint_y=None,
            height=dp(14),
        )
        self._role_label.bind(
            size=lambda widget, *_: setattr(widget, "text_size", widget.size)
        )
        self.add_widget(self._role_label)
        self._label = Label(
            text=text,
            color=TEXT,
            font_size=sp(16),
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
        # Account for the role caption as well as the body and panel padding.
        self._label.height = max(dp(24), self._label.texture_size[1])
        self.height = self._label.height + dp(34)


class GameplayScreen(BaseScreen):
    def __init__(self, app, **kwargs):
        super().__init__(app, name="gameplay", **kwargs)
        root = BoxLayout(orientation="vertical", padding=[dp(12), dp(10), dp(12), dp(10)], spacing=dp(8))
        top = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
        back = GhostButton(text="‹  Geri", size_hint_x=None, width=dp(72), font_size=sp(12))
        back.bind(on_release=lambda *_: self.app_ref.open_home())
        top.add_widget(back)
        self.title = Label(text="Oyun", color=TEXT, font_size=sp(18), bold=True, halign="left")
        self.title.bind(size=lambda *_: setattr(self.title, "text_size", self.title.size))
        top.add_widget(self.title)
        self.turn = _aligned_label(text="Tur 0", color=MUTED, font_size=sp(11), size_hint_x=None, width=dp(66))
        top.add_widget(self.turn)
        root.add_widget(top)

        self.scroll = ScrollView(do_scroll_x=False, bar_width=dp(2), scroll_type=["bars", "content"])
        self.message_box = BoxLayout(orientation="vertical", spacing=dp(12), padding=[dp(4), dp(8), dp(4), dp(18)], size_hint_y=None)
        self.message_box.bind(minimum_height=self.message_box.setter("height"))
        self.scroll.bind(size=lambda *_: setattr(self.message_box, "width", self.scroll.width))
        self.scroll.add_widget(self.message_box)
        root.add_widget(self.scroll)

        composer = RoundedPanel(
            orientation="horizontal", padding=[dp(6), dp(6)], spacing=dp(6),
            size_hint_y=None, height=dp(60), fill=(0.12, 0.12, 0.12, 1),
            radius=dp(28),
        )
        self.composer = composer
        self.input = PillInput(
            hint_text="Ne yapmak istiyorsun?", size_hint_x=1, size_hint_y=1,
            multiline=True, padding=[dp(14), dp(8)], font_size=sp(15),
            fill_color=(0.12, 0.12, 0.12, 1),
        )
        self.input.bind(text=self._resize_composer, width=self._resize_composer)
        composer.add_widget(self.input)
        self.send_button = AccentButton(
            text="Gönder", size_hint_x=None, width=dp(76), font_size=sp(11)
        )
        self.send_button.bind(on_release=lambda *_: self.submit())
        composer.add_widget(self.send_button)
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

    def _resize_composer(self, *_):
        """Grow the rounded composer for multi-line input without filling the screen."""
        text = self.input.text or ""
        width = max(dp(120), self.input.width)
        chars_per_line = max(18, int(width / max(1, sp(15) * 0.52)))
        visual_lines = 0
        for line in text.split("\n"):
            visual_lines += max(1, (len(line) + chars_per_line - 1) // chars_per_line)
        visual_lines = min(4, max(1, visual_lines))
        self.composer.height = dp(60) + dp(18) * (visual_lines - 1)

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
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), padding=[dp(2), 0, dp(2), 0])
        bubble = MessageBubble(text="" if animate else text, role=role)
        bubble.size_hint = (0.88, None)
        bubble.height = dp(48)
        if role == "player":
            row.add_widget(Widget())
            row.add_widget(bubble)
        else:
            row.add_widget(bubble)
            row.add_widget(Widget())
        bubble.bind(height=lambda widget, *_: setattr(row, "height", max(dp(48), widget.height)))
        self.message_box.add_widget(row)
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

    def append(self, text, role="npc"):
        return self.add_message(text, role=role, animate=True)

    def show_typing(self):
        self.remove_typing()
        row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(48), padding=[dp(2), 0, dp(2), 0])
        self._typing_bubble = MessageBubble(text="İşleniyor…", role="npc")
        self._typing_bubble.size_hint = (0.55, None)
        self._typing_bubble.height = dp(48)
        row.add_widget(self._typing_bubble)
        row.add_widget(Widget())
        self._typing_bubble.bind(height=lambda widget, *_: setattr(row, "height", max(dp(48), widget.height)))
        self.message_box.add_widget(row)
        Clock.schedule_once(self._scroll_bottom, 0)

    def remove_typing(self):
        if self._typing_bubble is not None:
            try:
                parent = self._typing_bubble.parent
                if parent is not None:
                    self.message_box.remove_widget(parent)
            except Exception:
                pass
            self._typing_bubble = None

    def set_busy(self, busy):
        self.send_button.disabled = bool(busy)
        self.send_button.text = "Bekle…" if busy else "Gönder"
        self.input.disabled = bool(busy)
        self.input.hint_text = "Yanıt hazırlanıyor…" if busy else "Ne yapmak istiyorsun?"

    def submit(self):
        text = self.input.text.strip()
        if not text or self.app_ref.busy or getattr(self.app_ref, "_lifecycle_stopping", False):
            return
        self.input.text = ""
        self.app_ref.busy = True
        self.set_busy(True)
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
        has_campaign = getattr(self.app_ref.controller, "scenario_pack", None) is not None
        active.add_widget(_aligned_label(
            text=self.app_ref.current_campaign_name(), color=TEXT, font_size=sp(19), bold=True,
            size_hint_y=None, height=dp(30),
        ))
        active.add_widget(_aligned_label(
            text=(
                f"Tur {self.app_ref.controller.turn}  ·  {self.app_ref.controller.provider_name}"
                if has_campaign else "Bir senaryo seç veya Senaryo Atölyesi'nde yeni bir dünya oluştur."
            ),
            color=MUTED, font_size=sp(12), size_hint_y=None, height=dp(22),
        ))
        resume = AccentButton(
            text="Dünyayı aç" if has_campaign else "Senaryoları aç",
            size_hint_y=None, height=dp(44),
        )
        resume.bind(on_release=lambda *_: self.app_ref.open_current_campaign_or_scenarios())
        active.add_widget(resume)
        self.list_box.add_widget(active)

        self.list_box.add_widget(_aligned_label(
            text="SON OYNANANLAR", color=MUTED, font_size=sp(10), bold=True,
            size_hint_y=None, height=dp(24),
        ))
        recent = [
            item for item in self.app_ref.recent_scenarios
            if item.get("scenario_id") != "demo-bootstrap"
        ]
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
        actions = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(46))
        workshop_btn = SoftButton(text="Senaryo Atölyesi", font_size=sp(11))
        workshop_btn.bind(on_release=lambda *_: self.app_ref.open_source_workspace())
        import_btn = AccentButton(text="+ Senaryo içe aktar", font_size=sp(11))
        import_btn.bind(on_release=lambda *_: self.app_ref.import_scenario())
        actions.add_widget(workshop_btn)
        actions.add_widget(import_btn)
        root.add_widget(actions)

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
            remove = GhostButton(
                text="Kaldır", size_hint_x=None, width=dp(64), font_size=sp(10),
            )
            remove.bind(on_release=lambda *_a, selected=item: self.app_ref.confirm_remove_scenario(selected))
            card.add_widget(remove)
            self.list_box.add_widget(card)


class SourceWorkspaceScreen(BaseScreen):
    """Persistent source queue and extraction-candidate viewer for scenario creation."""

    def __init__(self, app, **kwargs):
        super().__init__(app, name="source_workspace", **kwargs)
        root = BoxLayout(
            orientation="vertical", padding=[dp(16), dp(12), dp(16), dp(10)],
            spacing=dp(8),
        )
        header = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(46), spacing=dp(8))
        back = GhostButton(text="‹ Geri", size_hint_x=None, width=dp(72), font_size=sp(12))
        back.bind(on_release=lambda *_: self.app_ref.open_scenarios())
        header.add_widget(back)
        header.add_widget(_aligned_label(text="Senaryo Atölyesi", color=TEXT, font_size=sp(22), bold=True))
        root.add_widget(header)
        root.add_widget(_aligned_label(
            text="Kaynakları sırala, bölümler halinde işle ve ilerlemeyi kalıcı olarak sakla.",
            color=MUTED, font_size=sp(11), valign="top", size_hint_y=None, height=dp(34),
        ))

        workspace_row = BoxLayout(orientation="horizontal", spacing=dp(8), size_hint_y=None, height=dp(44))
        self.workspace_picker = Spinner(
            text="Çalışma alanı seç", values=(), size_hint_x=1,
            background_normal="", background_color=SURFACE_2,
            color=TEXT, font_size=sp(12),
        )
        self.workspace_picker.bind(text=self._select_workspace)
        workspace_row.add_widget(self.workspace_picker)
        create = AccentButton(text="+ Yeni", size_hint_x=None, width=dp(82), font_size=sp(12))
        create.bind(on_release=lambda *_: self._create_workspace_dialog())
        workspace_row.add_widget(create)
        root.add_widget(workspace_row)

        self.status_label = _aligned_label(
            text="Önce bir çalışma alanı oluştur.", color=MUTED, font_size=sp(11),
            valign="top", size_hint_y=None, height=dp(42),
        )
        root.add_widget(self.status_label)

        actions = BoxLayout(orientation="horizontal", spacing=dp(6), size_hint_y=None, height=dp(44))
        self.add_source_button = SoftButton(text="Kaynak ekle", font_size=sp(11))
        self.add_source_button.bind(on_release=lambda *_: self._choose_source())
        actions.add_widget(self.add_source_button)
        self.process_button = AccentButton(text="İşlemeyi başlat / devam et", font_size=sp(10))
        self.process_button.bind(on_release=lambda *_: self._process_queue())
        actions.add_widget(self.process_button)
        root.add_widget(actions)

        candidate_button = GhostButton(text="Çıkarılan adayları incele", size_hint_y=None, height=dp(34), font_size=sp(11))
        candidate_button.bind(on_release=lambda *_: self._show_candidates())
        root.add_widget(candidate_button)

        self._export_running = False
        self.export_button = AccentButton(
            text="İncelenmiş veriden senaryo ZIP'i oluştur",
            size_hint_y=None, height=dp(42), font_size=sp(11),
        )
        self.export_button.bind(on_release=lambda *_: self._create_export_dialog())
        root.add_widget(self.export_button)

        self.list_box = BoxLayout(orientation="vertical", spacing=dp(8), size_hint_y=None)
        self.list_box.bind(minimum_height=self.list_box.setter("height"))
        scroll = ScrollView(do_scroll_x=False, bar_width=dp(3))
        scroll.add_widget(self.list_box)
        root.add_widget(scroll)
        self.add_widget(root)

        self.active_workspace_id = None
        self._workspace_labels = {}
        self._refreshing_picker = False
        self._queue_running = False
        self._saf_workspace_id = None

    def show(self):
        super().show()
        self.refresh()

    def refresh(self):
        try:
            workspaces = self.app_ref.controller.list_source_workspaces()
        except Exception as exc:
            self.status_label.text = f"Çalışma alanları okunamadı ({type(exc).__name__})."
            return
        old_id = self.active_workspace_id
        self._workspace_labels = {
            f"{item['name']} · {item['source_count']} kaynak": item["workspace_id"]
            for item in workspaces
        }
        self._refreshing_picker = True
        self.workspace_picker.values = tuple(self._workspace_labels)
        if old_id and old_id in {item["workspace_id"] for item in workspaces}:
            self.active_workspace_id = old_id
            self.workspace_picker.text = next(label for label, wid in self._workspace_labels.items() if wid == old_id)
        elif workspaces:
            self.active_workspace_id = workspaces[0]["workspace_id"]
            self.workspace_picker.text = next(label for label, wid in self._workspace_labels.items() if wid == self.active_workspace_id)
        else:
            self.active_workspace_id = None
            self.workspace_picker.text = "Çalışma alanı seç"
        self._refreshing_picker = False

        self.list_box.clear_widgets()
        self.add_source_button.disabled = self.active_workspace_id is None or self._queue_running or self._export_running
        self.process_button.disabled = self.active_workspace_id is None or self._queue_running or self._export_running
        self.export_button.disabled = self.active_workspace_id is None or self._queue_running or self._export_running
        if self.active_workspace_id is None:
            self.status_label.text = "Henüz çalışma alanı yok. + Yeni ile başla."
            empty = RoundedPanel(
                orientation="vertical", padding=dp(14), size_hint_y=None,
                height=dp(96), fill=SURFACE, radius=dp(16),
            )
            empty.add_widget(_aligned_label(
                text="Kaynak dosyaların ayrı ve değişmeden saklanır. İlk sürüm .txt ve .md kabul eder.",
                color=MUTED, font_size=sp(12), valign="top",
            ))
            self.list_box.add_widget(empty)
            return

        try:
            meta = self.app_ref.controller.source_workspace_manager().get_workspace(self.active_workspace_id)
            statuses = self.app_ref.controller.source_workspace_manager().status(self.active_workspace_id)
        except Exception as exc:
            self.status_label.text = f"Durum okunamadı ({type(exc).__name__})."
            return
        total_done = sum(item.chunks_completed for item in statuses)
        total_chunks = sum(item.chunks_total for item in statuses)
        failed = sum(item.status == "failed" for item in statuses)
        self.status_label.text = (
            f"{meta['name']} · {len(statuses)} kaynak · {total_done}/{total_chunks} parça tamamlandı"
            + (f" · {failed} hata/yeniden deneme" if failed else "")
        )
        if not statuses:
            self.list_box.add_widget(_aligned_label(
                text="Henüz kaynak eklenmedi.", color=MUTED, font_size=sp(12),
                size_hint_y=None, height=dp(44),
            ))
            return
        for status in statuses:
            card = RoundedPanel(
                orientation="horizontal", padding=dp(9), spacing=dp(7),
                size_hint_y=None, height=dp(88), fill=SURFACE, radius=dp(16),
            )
            info = BoxLayout(orientation="vertical", spacing=dp(4))
            info.add_widget(_aligned_label(
                text=f"{status.sequence}. {status.name}", color=TEXT, font_size=sp(12), bold=True,
                size_hint_y=None, height=dp(25),
            ))
            progress = f"{status.chunks_completed}/{status.chunks_total} parça" if status.chunks_total else "henüz işlenmedi"
            state_text = {
                "pending": "Bekliyor", "processing": "İşleniyor", "completed": "Tamamlandı",
                "failed": "Hata · tekrar denenebilir",
            }.get(status.status, status.status)
            if status.last_error:
                state_text += f" · {status.last_error[:70]}"
            info.add_widget(_aligned_label(
                text=f"{state_text} · {progress}", color=DANGER if status.status == "failed" else MUTED,
                font_size=sp(9), valign="top",
            ))
            card.add_widget(info)
            left = GhostButton(text="↑", size_hint_x=None, width=dp(32), font_size=sp(13))
            left.disabled = self._queue_running or status.sequence == 1
            left.bind(on_release=lambda *_a, sid=status.source_id: self._reorder_source(sid, -1))
            card.add_widget(left)
            right = GhostButton(text="↓", size_hint_x=None, width=dp(32), font_size=sp(13))
            right.disabled = self._queue_running or status.sequence == len(statuses)
            right.bind(on_release=lambda *_a, sid=status.source_id: self._reorder_source(sid, 1))
            card.add_widget(right)
            remove = GhostButton(text="×", size_hint_x=None, width=dp(32), font_size=sp(14))
            remove.disabled = self._queue_running
            remove.bind(on_release=lambda *_a, sid=status.source_id, name=status.name: self._confirm_remove_source(sid, name))
            card.add_widget(remove)
            self.list_box.add_widget(card)

    def _select_workspace(self, _spinner, label):
        if self._refreshing_picker:
            return
        self.active_workspace_id = self._workspace_labels.get(label)
        self.refresh()

    def _create_workspace_dialog(self):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(9))
        name = PillInput(hint_text="Senaryo adı", multiline=False)
        description = PillInput(hint_text="Açıklama (isteğe bağlı)", multiline=False)
        box.add_widget(_field_group("Senaryo", name))
        box.add_widget(_field_group("Açıklama", description))
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Yeni senaryo çalışma alanı", content=box, size_hint=(0.92, None), height=dp(260), background_color=SURFACE)
        actions.add_widget(SoftButton(text="İptal", on_release=popup.dismiss))
        def create_workspace(*_):
            try:
                workspace_id = self.app_ref.controller.create_source_workspace(name.text, description.text)
            except Exception as exc:
                self.status_label.text = f"Çalışma alanı oluşturulamadı: {exc}"
                return
            self.active_workspace_id = workspace_id
            popup.dismiss()
            self.refresh()
        actions.add_widget(AccentButton(text="Oluştur", on_release=create_workspace))
        box.add_widget(actions)
        popup.open()

    def _choose_source(self):
        if self.active_workspace_id is None:
            self.status_label.text = "Önce çalışma alanı oluştur."
            return
        if self.app_ref._saf_source_import(self.active_workspace_id):
            return
        chooser = FileChooserListView(filters=["*.txt", "*.md"], path=str(Path.home()))
        box = BoxLayout(orientation="vertical", spacing=dp(8), padding=dp(10))
        box.add_widget(chooser)
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Kaynak metni seç (.txt / .md)", content=box, size_hint=(0.96, 0.88), background_color=SURFACE)
        actions.add_widget(SoftButton(text="İptal", on_release=popup.dismiss))
        def add_selected(*_):
            if not chooser.selection:
                return
            selected = chooser.selection[0]
            popup.dismiss()
            self._attach_source(self.active_workspace_id, selected, cleanup_temp=False)
        actions.add_widget(AccentButton(text="Kaynağı ekle", on_release=add_selected))
        box.add_widget(actions)
        popup.open()

    def _attach_source(self, workspace_id, path, *, cleanup_temp):
        try:
            added = self.app_ref.controller.add_source_to_workspace(workspace_id, path)
            if cleanup_temp:
                Path(path).unlink(missing_ok=True)
            self.active_workspace_id = workspace_id
            self.status_label.text = f"Kaynak eklendi: {added.name}"
        except Exception as exc:
            self.status_label.text = f"Kaynak eklenemedi: {exc}"
        self.refresh()

    def _reorder_source(self, source_id, delta):
        try:
            self.app_ref.controller.reorder_workspace_source(self.active_workspace_id, source_id, delta)
        except Exception as exc:
            self.status_label.text = f"Sıralama değiştirilemedi: {exc}"
        self.refresh()

    def _confirm_remove_source(self, source_id, name):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(_aligned_label(
            text=f"{name} kaynak listesinden çıkarılsın mı? Tamamlanmış çıkarım kayıtları denetim için korunur.",
            color=TEXT, font_size=sp(12), valign="top",
        ))
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(title="Kaynağı listeden çıkar", content=box, size_hint=(0.92, None), height=dp(220), background_color=SURFACE)
        actions.add_widget(SoftButton(text="İptal", on_release=popup.dismiss))
        def remove(*_):
            try:
                self.app_ref.controller.remove_workspace_source(self.active_workspace_id, source_id)
                self.status_label.text = "Kaynak listeden çıkarıldı; önceki çıkarım partileri korundu."
            except Exception as exc:
                self.status_label.text = f"Kaynak çıkarılamadı: {exc}"
            popup.dismiss()
            self.refresh()
        actions.add_widget(AccentButton(text="Çıkar", on_release=remove))
        box.add_widget(actions)
        popup.open()

    def _process_queue(self):
        if self.active_workspace_id is None or self._queue_running:
            return
        workspace_id = self.active_workspace_id
        self._queue_running = True
        self.process_button.disabled = True
        self.add_source_button.disabled = True
        self.status_label.text = "Kaynak parçaları AI ile işleniyor. Her tamamlanan parça ayrı kaydedilir…"

        def progress(batch, error):
            def update(*_):
                if error:
                    self.status_label.text = (
                        f"{batch.source_name} · parça {batch.chunk_index + 1}: hata ({error}); "
                        "checkpoint korunuyor, devam ederek tekrar deneyebilirsin."
                    )
                else:
                    self.status_label.text = (
                        f"{batch.source_name} · parça {batch.chunk_index + 1}/{batch.chunk_count} kaydedildi."
                    )
            Clock.schedule_once(update, 0)

        def worker():
            try:
                count = self.app_ref.controller.process_source_queue(workspace_id, progress_callback=progress)
                message = f"İşlem tamamlandı. {count} yeni parça kaydedildi."
            except Exception as exc:
                message = str(exc)
            def finish(*_):
                self._queue_running = False
                self.status_label.text = message
                self.refresh()
            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()

    def _create_export_dialog(self):
        if self.active_workspace_id is None or self._queue_running or self._export_running:
            self.status_label.text = "Önce bir çalışma alanı seç ve işleme tamamlanmasını bekle."
            return
        manager = self.app_ref.controller.source_workspace_manager()
        try:
            index = manager.candidate_index(self.active_workspace_id)
        except Exception as exc:
            self.status_label.text = f"Adaylar okunamadı: {type(exc).__name__}"
            return
        locations = [entity for entity in index["entities"] if entity.get("category") == "locations"]
        if not locations:
            self.status_label.text = "Henüz mekân adayı yok. Kaynakları işle ve en az bir mekân çıkar."
            return

        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(8))
        title = PillInput(hint_text="Senaryo adı", text="Yeni Senaryo", multiline=False)
        scenario_id = PillInput(hint_text="Sabit senaryo ID'si", text="new-scenario", multiline=False)
        player = PillInput(hint_text="Oyuncu karakterinin adı", text="Oyuncu", multiline=False)
        start_options = {
            f"{entity['name']} · {entity['id_candidate']}": entity["id_candidate"]
            for entity in locations
        }
        start_picker = Spinner(
            text=next(iter(start_options)), values=tuple(start_options),
            background_normal="", background_color=SURFACE_2, color=TEXT, font_size=sp(11),
        )
        box.add_widget(_field_group("Senaryo adı", title))
        box.add_widget(_field_group("Senaryo ID", scenario_id))
        box.add_widget(_field_group("Oyuncu adı", player))
        box.add_widget(_field_group("Başlangıç mekânı", start_picker))
        box.add_widget(_aligned_label(
            text="Yalnızca açıkça desteklenen, izin verilen alanlar kanonik JSON'a aktarılır. "
                 "Çelişkili veya belirsiz iddialar inceleme dosyasında kalır.",
            color=MUTED, font_size=sp(10), valign="top", size_hint_y=None, height=dp(42),
        ))
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(
            title="Senaryo paketini oluştur", content=box,
            size_hint=(0.94, None), height=dp(420), background_color=SURFACE,
        )
        actions.add_widget(SoftButton(text="İptal", on_release=popup.dismiss))

        def start_export(*_):
            chosen_location = start_options.get(start_picker.text)
            if not chosen_location:
                self.status_label.text = "Başlangıç mekânı seç."
                return
            if not title.text.strip() or not scenario_id.text.strip() or not player.text.strip():
                self.status_label.text = "Senaryo adı, ID ve oyuncu adı zorunlu."
                return
            workspace_id = self.active_workspace_id
            output = manager.root / workspace_id / "exports" / (scenario_id.text.strip() + ".rpgscenario.zip")
            scenario_title = title.text.strip()
            scenario_key = scenario_id.text.strip()
            player_name = player.text.strip()
            self._export_running = True
            self.refresh()
            self.status_label.text = "Kanonik kayıtlar hazırlanıyor, paket doğrulanıp yazılıyor…"
            popup.dismiss()

            def worker():
                try:
                    exported = manager.export_scenario_archive(
                        workspace_id, output,
                        scenario_id=scenario_key,
                        scenario_name=scenario_title,
                        player_name=player_name,
                        start_location_id=chosen_location,
                    )
                    message = f"Senaryo paketi oluşturuldu: {exported}"
                    path_value = str(exported)
                    succeeded = True
                except Exception as exc:
                    message = f"Paket oluşturulamadı: {exc}"
                    path_value = ""
                    succeeded = False

                def finish(*_a):
                    self._export_running = False
                    self.refresh()
                    self.status_label.text = message
                    if succeeded:
                        if not self.app_ref.save_generated_scenario_archive(path_value):
                            self.app_ref.notify(message)
                    else:
                        self.app_ref.notify(message)
                Clock.schedule_once(finish, 0)

            Thread(target=worker, daemon=True).start()

        actions.add_widget(AccentButton(text="ZIP oluştur", on_release=start_export))
        box.add_widget(actions)
        popup.open()

    def _show_candidates(self):
        if self.active_workspace_id is None:
            self.status_label.text = "Önce bir çalışma alanı seç."
            return
        try:
            records = self.app_ref.controller.source_workspace_manager().candidate_index(self.active_workspace_id)
            text = __import__("json").dumps(records, ensure_ascii=False, indent=2) if records.get("source_batch_count") else "Henüz işlenmiş parça yok."
        except Exception as exc:
            text = f"Adaylar okunamadı: {type(exc).__name__}"
        viewer = TextInput(
            text=text, readonly=True, multiline=True, font_size=sp(11),
            background_color=SURFACE, foreground_color=TEXT,
        )
        popup = Popup(title="Çıkarılan adaylar (ara veri)", content=viewer, size_hint=(0.96, 0.88), background_color=SURFACE)
        popup.open()


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
            "Ayarlar · Yapay zekâ",
            "Yerel GGUF, Hugging Face model kataloğu ve API sağlayıcılarını buradan yönet.",
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
            text="◇  Yerel modeller · Local GGUF", color=TEXT, font_size=sp(17), bold=True,
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
            size_hint_y=None, height=dp(354), fill=SURFACE, radius=dp(22),
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
        self.hf_sort = Spinner(
            text="İndirme", values=("İndirme", "Beğeni", "Güncel"),
            size_hint_x=None, width=dp(92), font_size=sp(10),
            background_normal="", background_down="",
            background_color=SURFACE_2, color=TEXT,
        )
        search_row.add_widget(self.hf_sort)
        search_button = AccentButton(text="Ara", size_hint_x=None, width=dp(56))
        search_button.bind(on_release=lambda *_: self.search_remote_models())
        search_row.add_widget(search_button)
        self.hf_catalog.add_widget(search_row)

        connection_row = BoxLayout(
            orientation="horizontal", size_hint_y=None, height=dp(38), spacing=dp(8),
        )
        self.hf_connection_button = SoftButton(
            text="↻  Bağlantıyı test et", size_hint_x=None, width=dp(142), font_size=sp(11),
        )
        self.hf_connection_button.bind(on_release=lambda *_: self.test_huggingface_connection())
        connection_row.add_widget(self.hf_connection_button)
        self.hf_connection_status = _aligned_label(
            text="İnternet/DNS erişimini kontrol et.", color=MUTED, font_size=sp(10),
            size_hint_y=None, height=dp(38),
        )
        connection_row.add_widget(self.hf_connection_status)
        self.hf_catalog.add_widget(connection_row)

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
            size_hint_y=None, height=dp(520), fill=SURFACE, radius=dp(22),
        )
        api.add_widget(_aligned_label(
            text="API sağlayıcısı", color=TEXT, font_size=sp(17), bold=True,
            size_hint_y=None, height=dp(26),
        ))
        self.api_provider = Spinner(
            text="OpenAI", values=("OpenAI", "Gemini", "OpenAI-compatible"),
            size_hint_y=None, height=dp(44), font_size=sp(14),
            background_normal="", background_down="",
            background_color=SURFACE_2, color=TEXT,
        )
        self.api_provider.bind(text=lambda *_: self._provider_changed())
        api.add_widget(_field_group("Sağlayıcı", self.api_provider, height=dp(68)))

        self.api_endpoint = PillInput(
            text="https://api.openai.com/v1", hint_text="https://api.openai.com/v1",
        )
        self._last_api_provider = "OpenAI"
        self.api_advanced_open = False
        self.api_model = PillInput(
            text="gpt-4.1-mini", hint_text="Örn. gpt-4.1-mini",
        )
        self.api_key = PillInput(
            hint_text="API anahtarını buraya yapıştır", password=True,
        )
        self.api_key_field = _field_group("API anahtarı", self.api_key)
        api.add_widget(self.api_key_field)
        self.api_advanced_button = SoftButton(
            text="Gelişmiş ayarlar", size_hint_y=None, height=dp(38), font_size=sp(12),
        )
        self.api_advanced_button.bind(on_release=lambda *_: self._toggle_api_advanced())
        api.add_widget(self.api_advanced_button)
        self.api_endpoint_field = _field_group("API endpoint", self.api_endpoint)
        self.api_model_field = _field_group("Model adı", self.api_model)
        api.add_widget(self.api_endpoint_field)
        api.add_widget(self.api_model_field)
        self.api_status = _aligned_label(
            text="API bağlantısını test ederek modeli doğrula.", color=MUTED, font_size=sp(11),
            valign="top", size_hint_y=None, height=dp(32),
        )
        api.add_widget(self.api_status)
        self.api_models_picker = Spinner(
            text="Bağlantı testinden sonra model seç", values=(),
            size_hint_y=None, height=0, font_size=sp(12),
            background_normal="", background_down="",
            background_color=SURFACE_2, color=TEXT,
        )
        self.api_models_picker.bind(text=self._choose_api_model)
        api.add_widget(self.api_models_picker)
        self.api_model_filter = PillInput(
            hint_text="Model listesinde filtrele…", size_hint_y=None, height=0,
        )
        self.api_model_filter.bind(text=lambda *_: self._filter_api_models())
        api.add_widget(self.api_model_filter)
        self._api_all_model_ids = ()
        self.api_connect_button = AccentButton(
            text="✓  Ayarları uygula ve test et", size_hint_y=None, height=dp(46),
        )
        self.api_connect_button.bind(on_release=lambda *_: self.connect_api())
        api.add_widget(self.api_connect_button)
        self.api_generation_test_button = SoftButton(
            text="Gerçek AI yanıtını test et", size_hint_y=None, height=dp(42),
            disabled=True,
        )
        self.api_generation_test_button.bind(
            on_release=lambda *_: self.test_api_generation()
        )
        api.add_widget(self.api_generation_test_button)
        self.api_panel = api
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
        provider = self.api_provider.text
        previous_provider = getattr(self, "_last_api_provider", "OpenAI")
        gemini = provider == "Gemini"
        compatible = provider == "OpenAI-compatible"
        if compatible and previous_provider != "OpenAI-compatible":
            self.api_endpoint.text = ""
            self.api_endpoint.hint_text = "Örn. https://api.provider.com/v1"
            self.api_advanced_open = True
        elif provider == "OpenAI" and previous_provider == "OpenAI-compatible":
            self.api_endpoint.text = "https://api.openai.com/v1"
            self.api_endpoint.hint_text = "https://api.openai.com/v1"
            self.api_model.text = "gpt-4.1-mini"
            self.api_model.hint_text = "Örn. gpt-4.1-mini"
            self.api_advanced_open = False
        elif gemini and previous_provider == "OpenAI-compatible":
            self.api_model.text = "gemini-2.5-flash"
            self.api_advanced_open = False
        self._last_api_provider = provider
        self.api_endpoint.disabled = gemini
        self.api_endpoint.opacity = 0.4 if gemini else 1.0
        if gemini and self.api_model.text.strip() in {"", "gpt-4.1-mini", "gemini-3.6-flash"}:
            self.api_model.text = "gemini-2.5-flash"
        elif provider == "OpenAI" and self.api_model.text.strip() in {"", "gemini-3.6-flash", "gemini-2.5-flash"}:
            self.api_model.text = "gpt-4.1-mini"
        elif compatible and self.api_model.text.strip() in {"", "gpt-4.1-mini", "gemini-3.6-flash", "gemini-2.5-flash"}:
            self.api_model.text = ""
            self.api_model.hint_text = "Sağlayıcının model kimliği"
        elif not compatible:
            self.api_model.hint_text = "Örn. gpt-4.1-mini"
        if hasattr(self, "api_models_picker"):
            self._api_all_model_ids = ()
            self.api_models_picker.values = ()
            self.api_models_picker.text = "Model listesi gelişmiş ayarlarda görünür"
            self.api_models_picker.height = 0
        if hasattr(self, "api_model_filter"):
            self.api_model_filter.height = 0
        self._update_api_advanced_visibility()
        if hasattr(self, "api_status"):
            self.api_status.text = "Sağlayıcı değişti; model listesini görmek için bağlantıyı test et."
            self.api_status.color = MUTED
        if hasattr(self, "api_generation_test_button"):
            self.api_generation_test_button.disabled = True

    def _toggle_api_advanced(self):
        if self.api_provider.text == "OpenAI-compatible":
            self.api_advanced_open = True
        else:
            self.api_advanced_open = not self.api_advanced_open
        self._update_api_advanced_visibility()

    def _update_api_advanced_visibility(self):
        """Keep routine providers simple; reveal endpoint/model only when useful."""
        provider = self.api_provider.text
        compatible = provider == "OpenAI-compatible"
        show_model = compatible or self.api_advanced_open
        show_endpoint = compatible or (self.api_advanced_open and provider == "OpenAI")
        self.api_endpoint_field.height = dp(70) if show_endpoint else 0
        self.api_endpoint_field.opacity = 1 if show_endpoint else 0
        self.api_endpoint_field.disabled = not show_endpoint or provider == "Gemini"
        self.api_model_field.height = dp(70) if show_model else 0
        self.api_model_field.opacity = 1 if show_model else 0
        has_models = bool(getattr(self, "_api_all_model_ids", ()))
        show_model_picker = show_model and has_models
        self.api_model_filter.height = dp(42) if show_model_picker else 0
        self.api_models_picker.height = dp(42) if show_model_picker else 0
        if compatible:
            self.api_advanced_button.text = "Özel sağlayıcı bağlantı alanları"
            self.api_advanced_button.disabled = True
        else:
            self.api_advanced_button.text = (
                "Gelişmiş ayarları gizle" if self.api_advanced_open else "Gelişmiş ayarlar"
            )
            self.api_advanced_button.disabled = False
        if hasattr(self, "api_panel"):
            self._update_api_panel_height()

    def _update_api_panel_height(self):
        if not hasattr(self, "api_panel"):
            return
        fixed = dp(416)
        self.api_panel.height = (
            fixed + self.api_endpoint_field.height + self.api_model_field.height
            + self.api_model_filter.height + self.api_models_picker.height
        )

    def _filter_api_models(self):
        all_models = getattr(self, "_api_all_model_ids", ())
        query = self.api_model_filter.text.strip().casefold()
        filtered = tuple(model for model in all_models if query in model.casefold())[:30]
        current = self.api_models_picker.text
        self.api_models_picker.values = filtered
        if current not in filtered:
            self.api_models_picker.text = "Filtrelenen modelleri seç" if filtered else "Eşleşen model yok"
        if not filtered and all_models:
            self.api_status.text = "Filtreyle eşleşen model yok. Filtreyi kısalt veya model adını elle gir."
            self.api_status.color = MUTED

    def _choose_api_model(self, _spinner, selected):
        if not selected or selected not in self.api_models_picker.values:
            return
        self.api_model.text = selected
        adapter = getattr(self.app_ref.controller.session, "adapter", None)
        if adapter is not None and hasattr(adapter, "model"):
            adapter.model = selected
            self.api_status.text = f"Model seçildi: {selected}"
            self.api_status.color = ACCENT

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
            "dns resolution failed", "no address associated", "name or service not known",
            "temporary failure in name resolution", "nodename nor servname",
            "getaddrinfo failed",
        )):
            return (
                "DNS hatası: huggingface.co adresi çözümlenemedi. Wi-Fi/mobil veriyi, "
                "Özel DNS ayarını ve VPN/reklam engelleyiciyi kontrol et; sonra tekrar dene."
            )
        if "network is unreachable" in raw or "no route to host" in raw:
            return "Ağa erişilemiyor. Uçak modunu kapatıp Wi-Fi veya mobil veriyi kontrol et."
        if "ssl" in raw or "certificate" in raw or "tls" in raw:
            return "Güvenli bağlantı kurulamadı. Cihazın tarih/saatini ve ağ filtrelerini kontrol et."
        if "timed out" in raw or "timeout" in raw:
            return "İstek zaman aşımına uğradı. Bağlantıyı kontrol edip tekrar dene."
        if "401" in raw or "403" in raw:
            return "Bu depoya erişilemiyor olabilir. Herkese açık bir model seçmeyi dene."
        if "429" in raw:
            return "Hugging Face geçici istek sınırına ulaştı. Biraz bekleyip tekrar dene."
        return "Hugging Face kataloğu açılamadı. Bağlantıyı test et; sonra aramayı yeniden dene."

    def test_huggingface_connection(self):
        if getattr(self, "_hf_probe_running", False):
            return
        self._hf_probe_running = True
        self.hf_connection_button.disabled = True
        self.hf_connection_status.text = "Hugging Face bağlantısı kontrol ediliyor…"
        self.hf_connection_status.color = MUTED

        def worker():
            try:
                check_huggingface_connection(timeout=8.0)
                message = "Bağlantı başarılı."
                success = True
            except Exception as exc:
                message = self._friendly_catalog_error(exc)
                success = False

            def finish(*_):
                self._hf_probe_running = False
                self.hf_connection_button.disabled = False
                self.hf_connection_status.text = message
                self.hf_connection_status.color = ACCENT if success else DANGER

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()

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
        self.hf_catalog.height = dp(354)

        def worker():
            try:
                sort_by = {"İndirme": "downloads", "Beğeni": "likes", "Güncel": "lastModified"}.get(
                    self.hf_sort.text, "downloads"
                )
                models = self.app_ref.controller.search_remote_models(query, limit=8, sort_by=sort_by)
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
                    self.hf_catalog.height = dp(416)
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
                    self.hf_catalog.height = dp(392)
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
            text="Yalnızca seçtiğin GGUF dosyası indirilir. Kesilen indirmeler tekrar denendiğinde devam edebilir.",
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
        status = _aligned_label(text="İndirmeye hazır.", color=MUTED, font_size=sp(11),
                                valign="top", size_hint_y=None, height=dp(34))
        box.add_widget(progress)
        box.add_widget(status)
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        cancel = SoftButton(text="Kapat")
        start = AccentButton(text="İndir / devam et")
        actions.add_widget(cancel)
        actions.add_widget(start)
        box.add_widget(actions)
        popup = Popup(title="Model indir", content=box, size_hint=(0.94, 0.80),
                      background_color=SURFACE, separator_color=ACCENT, auto_dismiss=False)
        cancel.bind(on_release=lambda *_: popup.dismiss())

        def worker(spec):
            try:
                def progress_callback(written, total):
                    def update(*_):
                        if total:
                            progress.value = min(100, written * 100 / total)
                            status.text = f"{written / (1024 ** 3):.2f} / {total / (1024 ** 3):.2f} GiB"
                        else:
                            status.text = f"{written / (1024 ** 3):.2f} GiB indirildi"
                    Clock.schedule_once(update, 0)
                installed = self.app_ref.controller.download_local_model(
                    spec, progress_callback=progress_callback
                )
                message = f"Model indirildi ve doğrulandı: {installed.name}"
            except Exception as exc:
                message = f"İndirme tamamlanmadı; tekrar deneyerek devam edebilirsin. {exc}"

            def finish(*_):
                self.app_ref._model_download_in_progress = False
                start.disabled = False
                cancel.disabled = False
                status.text = message
                start.text = "Tekrar dene / devam et"
                self.app_ref.notify(message)
                self.refresh()
            Clock.schedule_once(finish, 0)

        def start_download(*_):
            # Snapshot every Kivy widget value on the UI thread before starting the worker.
            selected_repo = repo.text.strip()
            selected_filename = filename.text.strip()
            selected_revision = revision.text.strip() or "main"
            selected_sha = sha.text.strip() or None
            if not selected_repo or not selected_filename:
                status.text = "Repository ve GGUF dosya adı zorunlu."
                return
            spec = ModelSpec(
                selected_repo, selected_filename, revision=selected_revision,
                expected_size_bytes=expected_size_bytes, expected_sha256=selected_sha,
            )
            try:
                spec.validate()
            except Exception as exc:
                status.text = f"Model bilgisi geçersiz: {exc}"
                return
            self.app_ref._model_download_in_progress = True
            start.disabled = True
            cancel.disabled = True
            status.text = "İndirme başlatılıyor…"
            Thread(target=worker, args=(spec,), daemon=True).start()

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
        provider = self.api_provider.text
        endpoint = self.api_endpoint.text.strip()
        if not api_key:
            self.api_status.text = "API anahtarı gerekli."
            self.api_status.color = DANGER
            return
        if not model_name:
            self.api_status.text = "Model adı gerekli."
            self.api_status.color = DANGER
            return
        # Do not replace a working provider until the new credentials and
        # endpoint have passed the connection probe below. This preserves the
        # current adapter if the user mistypes a key or endpoint.
        self.api_key.text = ""
        self.api_status.text = "Bağlantı kontrol ediliyor…"
        self.api_status.color = MUTED
        self.api_connect_button.disabled = True
        self.api_provider.disabled = True
        token = getattr(self, "_api_probe_token", 0) + 1
        self._api_probe_token = token

        def worker():
            model_ids = ()
            try:
                result = check_api_connection(
                    provider,
                    endpoint=endpoint,
                    api_key=api_key,
                    timeout=12.0,
                )
                message = result.message
                model_ids = result.model_ids
                success = True
            except APIConnectionError as exc:
                message = str(exc)
                success = False
            except Exception:
                message = "Bağlantı kontrolü başarısız oldu. Endpoint ve ağ bağlantısını kontrol et."
                success = False

            def finish(*_):
                if token != self._api_probe_token:
                    return
                apply_success = success
                final_message = message
                if apply_success:
                    try:
                        if provider == "Gemini":
                            self.app_ref.controller.set_gemini(api_key, model_name)
                        else:
                            self.app_ref.controller.set_openai_compatible(endpoint, api_key, model_name)
                        self.provider.text = self.app_ref.controller.provider_name
                    except Exception as exc:
                        apply_success = False
                        final_message = f"Ayarlar uygulanamadı: {exc}"
                self.api_status.text = final_message
                self.api_status.color = ACCENT if apply_success else DANGER
                self.api_connect_button.disabled = False
                self.api_provider.disabled = False
                self.api_generation_test_button.disabled = not apply_success
                if apply_success and model_ids:
                    self._api_all_model_ids = tuple(model_ids)
                    self.api_model_filter.text = ""
                    self.api_models_picker.values = model_ids[:30]
                    self.api_models_picker.text = "Bulunan modelleri seç"
                else:
                    self._api_all_model_ids = ()
                    self.api_model_filter.text = ""
                    self.api_models_picker.values = ()
                    self.api_models_picker.text = "Model listesi bulunamadı"
                self._update_api_advanced_visibility()
                if apply_success and model_ids:
                    self.api_status.text = final_message + " Model listesini filtreleyebilir veya adını elle yazabilirsin."

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()

    def test_api_generation(self):
        """Exercise the selected provider's real generation endpoint, not just model listing."""
        if getattr(self, "_api_generation_test_running", False):
            return
        adapter = getattr(self.app_ref.controller.session, "adapter", None)
        if adapter is None or not hasattr(adapter, "generate"):
            self.api_status.text = "Etkin bir AI sağlayıcısı bulunamadı."
            self.api_status.color = DANGER
            return

        self._api_generation_test_running = True
        self.api_generation_test_button.disabled = True
        self.api_status.text = "Gerçek AI isteği gönderiliyor…"
        self.api_status.color = MUTED

        def worker():
            try:
                result = adapter.generate(
                    "PLAYER ACTION: look. Return a valid response using the required "
                    "structured RPG response schema. Keep the narrative to one short sentence."
                )
                narrative = getattr(result, "narrative", "")
                if not isinstance(narrative, str) or not narrative.strip():
                    raise RuntimeError("Provider returned no narrative.")
                message = "Gerçek AI üretimi başarılı. Sağlayıcı yanıt verdi."
                success = True
            except Exception as exc:
                # Do not expose API keys, request bodies, or arbitrary provider response bodies.
                error_name = type(exc).__name__
                message = f"Gerçek AI isteği başarısız ({error_name}). Bağlantı, model ve API erişimini kontrol et."
                success = False

            def finish(*_):
                self._api_generation_test_running = False
                self.api_generation_test_button.disabled = False
                self.api_status.text = message
                self.api_status.color = ACCENT if success else DANGER

            Clock.schedule_once(finish, 0)

        Thread(target=worker, daemon=True).start()


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
            self.source_workspace = SourceWorkspaceScreen(self)
            self.ai = AIScreen(self)
            self.settings = SettingsScreen(self)
            for screen in (self.home, self.games, self.game, self.scenarios, self.source_workspace, self.ai, self.settings):
                self.manager.add_widget(screen)

            root = BoxLayout(orientation="vertical", spacing=0)
            root.add_widget(self.manager)
            root.add_widget(self._bottom_nav())
            self.manager.current = "home"
            self._update_nav_state()
            # The demo runtime remains available internally, but is not pinned as an
            # active world or injected into the user's recent-scenarios list.
            self.recent_scenarios = [
                item for item in self.recent_scenarios
                if item.get("scenario_id") != "demo-bootstrap"
            ]
            try:
                if self._recent_store is not None:
                    self._recent_store.put("recent", items=self.recent_scenarios)
            except Exception:
                pass
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
            "games" if current in {"games", "gameplay", "scenarios", "source_workspace"}
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
    def open_source_workspace(self): self.go("source_workspace")
    def open_ai(self): self.go("ai")
    def save_generated_scenario_archive(self, path):
        try:
            from rpg_android_file_picker import save_scenario_document
        except ImportError:
            return False
        self._saf_scenario_export_in_progress = True
        try:
            launched = save_scenario_document(
                path, Path(path).name,
                on_saved=lambda uri: Clock.schedule_once(
                    lambda *_: self._finish_scenario_export(uri, None), 0
                ),
                on_error=lambda error: Clock.schedule_once(
                    lambda *_: self._finish_scenario_export(None, error), 0
                ),
                on_cancel=lambda: Clock.schedule_once(
                    lambda *_: self._finish_scenario_export(None, None), 0
                ),
            )
        except Exception as exc:
            self._saf_scenario_export_in_progress = False
            self.notify(f"ZIP kaydedilemedi: {type(exc).__name__}")
            return True
        if not launched:
            self._saf_scenario_export_in_progress = False
        return launched

    def _finish_scenario_export(self, uri, error):
        self._saf_scenario_export_in_progress = False
        if error:
            self.notify(f"ZIP dışa aktarılamadı ({error}). Atölyedeki paket korunuyor.")
        elif uri:
            self.notify("Senaryo ZIP'i seçtiğin konuma kaydedildi.")


    def open_current_campaign_or_scenarios(self):
        if getattr(self.controller, "scenario_pack", None) is None:
            self.open_scenarios()
        else:
            self.open_gameplay()

    def current_campaign_name(self):
        pack = getattr(self.controller, "scenario_pack", None)
        if pack is not None:
            return getattr(pack, "name", self.controller.scenario_id)
        return "Henüz dünya seçilmedi"

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
            error = False
        except Exception as exc:
            # Keep provider details and credentials out of the visible chat.
            result = "İstek tamamlanamadı. API ayarlarını ve bağlantını kontrol edip tekrar dene."
            error = True
            self._record_gameplay_error("turn_submission", exc)
        Clock.schedule_once(lambda *_: self._finish_submit(result, error=error), 0)

    def _finish_submit(self, result, error=False):
        self.busy = False
        self.game.set_busy(False)
        # Persistence is deliberately independent from presentation animation.
        if self.controller.dirty:
            self._autosave("turn")
        if self._autosave_pending:
            self._autosave_pending = False
            if self.controller.dirty:
                self._autosave("deferred")
        self.game.remove_typing()
        self.game.append(result, role="error" if error else "npc")
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
            opening = "Dünya görünümü yüklenemedi. Ana menüye dönüp yeniden deneyebilirsin."
            self._gameplay_initialized = False
        else:
            self._gameplay_initialized = True
        if self._gameplay_initialized:
            self.game.set_log("RPG Engine\n" + opening)
        else:
            # Keep operational failures separate from in-world narration and
            # avoid exposing implementation-specific exception names to players.
            self.game.set_log("RPG Engine")
            self.game.append(opening, role="error")
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

    def _saf_source_import(self, workspace_id):
        if getattr(self, "_saf_source_import_in_progress", False):
            return True
        try:
            from rpg_android_file_picker import open_source_document
        except ImportError:
            return False
        self._saf_source_import_in_progress = True
        self._saf_source_workspace_id = workspace_id
        try:
            launched = open_source_document(self._on_saf_source_import)
        except Exception as exc:
            self._saf_source_import_in_progress = False
            self.notify(f"Kaynak seçici açılamadı: {type(exc).__name__}")
            return False
        if not launched:
            self._saf_source_import_in_progress = False
        return launched

    def _on_saf_source_import(self, path):
        Clock.schedule_once(lambda *_: self._finish_saf_source_import(path), 0)

    def _finish_saf_source_import(self, path):
        self._saf_source_import_in_progress = False
        workspace_id = getattr(self, "_saf_source_workspace_id", None)
        try:
            if workspace_id is None:
                raise RuntimeError("Kaynak için çalışma alanı seçilmedi.")
            self.source_workspace._attach_source(workspace_id, path, cleanup_temp=True)
        except Exception as exc:
            self.notify(f"Kaynak eklenemedi: {type(exc).__name__}")
        self.source_workspace.refresh()

    def confirm_remove_scenario(self, item):
        box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(10))
        box.add_widget(_aligned_label(
            text=(
                f"'{item.name}' kurulu senaryo paketini kaldırmak istiyor musun? "
                "Oyun kayıtları silinmez; ancak bu senaryoyu tekrar açmak için yeniden içe aktarman gerekir."
            ),
            color=TEXT, font_size=sp(12), valign="top",
        ))
        actions = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        popup = Popup(
            title="Senaryoyu kaldır", content=box, size_hint=(0.92, None),
            height=dp(245), background_color=SURFACE,
        )
        actions.add_widget(SoftButton(text="İptal", on_release=popup.dismiss))

        def remove(*_):
            try:
                self.controller.remove_installed_scenario(item.scenario_id)
                self.recent_scenarios = [
                    recent for recent in self.recent_scenarios
                    if recent.get("scenario_id") != item.scenario_id
                ]
                if self._recent_store is not None:
                    self._recent_store.put("recent", items=self.recent_scenarios)
                self.notify(f"'{item.name}' kaldırıldı. Oyun kayıtları korundu.")
            except Exception as exc:
                self.notify(f"Senaryo kaldırılamadı: {exc}")
            popup.dismiss()
            self.scenarios.refresh()
            self.games.refresh()

        actions.add_widget(AccentButton(text="Kaldır", on_release=remove))
        box.add_widget(actions)
        popup.open()

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
