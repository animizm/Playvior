"""
Playvior GUI — CustomTkinter front end for export_playlists.py / import_playlists.py.

Requires: pip install customtkinter plexapi

This file does not duplicate any Plex logic. It imports the same
functions the CLI scripts use (export_separate_files, export_combined_file,
get_video_playlists, load_playlist_docs, build_library_index, import_playlist)
so the GUI and CLI always behave identically — this is just a different
front end onto the same tested code.
"""

import math
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter
import tkinter.filedialog as filedialog
import tkinter.messagebox as messagebox

import customtkinter as ctk
from customtkinter.windows.widgets.core_rendering.draw_engine import DrawEngine
from plexapi.myplex import MyPlexAccount, MyPlexPinLogin

from export_playlists import (
    get_video_playlists,
    export_separate_files,
    export_combined_file,
)
from import_playlists import (
    load_playlist_docs,
    build_library_index,
    import_playlist,
)

# --- Windows DPI awareness ------------------------------------------------
# Must happen before Tk creates any window. CustomTkinter tries to set this
# itself, but on some setups (notably launching via a plain python.exe from
# PowerShell/cmd, which is exactly how this app is normally started) that
# call happens too late or silently no-ops, leaving Tk convinced the screen
# is lower-resolution than it is. The visible symptom is small canvas-drawn
# icons (dropdown chevrons, checkmarks) rendering as a blurry cluster of
# dots instead of a clean shape, since they're drawn at the wrong pixel
# density and then stretched. Setting this explicitly, early, fixes it.
if sys.platform == "win32":
    try:
        from ctypes import windll, c_void_p
        # Per-Monitor-v2 (Windows 10 1703+) is the modern, complete awareness
        # level. Plain "system aware" (the old fallback below) still lets
        # customtkinter's own scaling tracker apply a second, fractional
        # scale factor on top of what Windows reports, which is what turns
        # anti-aliased lines (dropdown chevrons, rounded corners) into a
        # scatter of dots instead of a clean shape.
        windll.user32.SetProcessDpiAwarenessContext(c_void_p(-4))
    except Exception:
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                from ctypes import windll
                windll.user32.SetProcessDPIAware()
            except Exception:
                pass

# --- icon rendering method -------------------------------------------------
# CustomTkinter draws small icons (dropdown chevrons, checkmarks) one of two
# ways: as a glyph from its private bundled font, or as a raw vector line on
# the Tk canvas. The font-glyph path looks smoother in principle (real OS
# antialiasing), but its antialiasing collapses into disconnected dots at
# these widget sizes regardless of how large we make them — that's not a
# small-size-only artifact after all. The vector-line path is the one that
# actually rendered a solid, connected chevron, so that's what stays on,
# even though Tk's canvas draws it without antialiasing (a flatter, more
# aliased look, but a correct shape).
DrawEngine.preferred_drawing_method = "polygon_shapes"

# The setting above is one global switch, and it affects the checkbox's
# checkmark exactly the same way it affects the dropdown chevron — but the
# checkmark looked worse on the vector-line path, not better (its glyph
# apparently isn't subject to the same hinting breakup the chevron's is).
# So the checkmark is pinned back to the font-glyph path specifically,
# regardless of the global setting above, by replacing just that one draw
# method with a version that always takes the font-glyph branch.


def _font_checkmark(self, width, height, size):
    size = round(size)
    requires_recoloring = False
    if not self._canvas.find_withtag("checkmark"):
        self._canvas.create_text(
            0, 0, text="Z", font=("CustomTkinter_shapes_font", -size),
            tags=("checkmark", "create_text"), anchor="center",
        )
        self._canvas.tag_raise("checkmark")
        requires_recoloring = True
    self._canvas.coords("checkmark", round(width / 2), round(height / 2))
    return requires_recoloring


DrawEngine.draw_checkmark = _font_checkmark

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# --- brand colors -----------------------------------------------------------
# Swap the built-in "blue" theme's accent and background colors for the
# app's own palette: Gamboge/Amber for anything interactive (buttons,
# checkmarks, the progress bar, selected states) and Shark/Dark Grey for
# backgrounds. This edits the theme dict customtkinter just loaded, in
# place, rather than shipping a separate theme file — every widget still
# reads corner radii, border widths, etc. from the "blue" theme's
# structure, just with these colors substituted in. Each value is a
# (light-mode, dark-mode) pair; both are set the same since this app always
# forces dark mode.
_AMBER = "#E5A00D"
_AMBER_HOVER = "#C3880B"
_AMBER_PRESSED = "#A6740A"
_GLOW_BLUE = "#5AA9E6"       # bright end of the action-button pulse outline
_GLOW_BLUE_DIM = "#2C4A5E"   # dim end — a dark, desaturated blue rather than off
_BG = "#282A2D"          # Shark — window background
_PANEL = "#303236"       # one step lighter than _BG, for "card" frames
_PANEL_HOVER = "#3A3C40"
_INSET = "#1F2023"       # darker than _BG, for input fields and log boxes
_BORDER = "#45474B"
_TEXT_ON_AMBER = "#1A1A1A"   # dark text for contrast against the amber fill
_TEXT = "#DCE4EE"            # ordinary light body text


def _themed(color):
    return [color, color]


_theme = ctk.ThemeManager.theme

_theme["CTk"]["fg_color"] = _themed(_BG)
_theme["CTkToplevel"]["fg_color"] = _themed(_BG)

_theme["CTkFrame"]["fg_color"] = _themed(_PANEL)
_theme["CTkFrame"]["top_fg_color"] = _themed(_PANEL_HOVER)
_theme["CTkFrame"]["border_color"] = _themed(_BORDER)

_theme["CTkButton"]["fg_color"] = _themed(_AMBER)
_theme["CTkButton"]["hover_color"] = _themed(_AMBER_HOVER)
_theme["CTkButton"]["border_color"] = _themed(_BORDER)
_theme["CTkButton"]["text_color"] = _themed(_TEXT_ON_AMBER)

_theme["CTkLabel"]["text_color"] = _themed(_TEXT)

_theme["CTkEntry"]["fg_color"] = _themed(_INSET)
_theme["CTkEntry"]["border_color"] = _themed(_BORDER)
_theme["CTkEntry"]["text_color"] = _themed(_TEXT)

_theme["CTkCheckBox"]["fg_color"] = _themed(_AMBER)
_theme["CTkCheckBox"]["hover_color"] = _themed(_AMBER_HOVER)
_theme["CTkCheckBox"]["border_color"] = _themed(_BORDER)
_theme["CTkCheckBox"]["checkmark_color"] = _themed(_TEXT_ON_AMBER)
_theme["CTkCheckBox"]["text_color"] = _themed(_TEXT)

_theme["CTkProgressBar"]["fg_color"] = _themed(_PANEL_HOVER)
_theme["CTkProgressBar"]["progress_color"] = _themed(_AMBER)

_theme["CTkOptionMenu"]["fg_color"] = _themed(_AMBER)
_theme["CTkOptionMenu"]["button_color"] = _themed(_AMBER_HOVER)
_theme["CTkOptionMenu"]["button_hover_color"] = _themed(_AMBER_PRESSED)
_theme["CTkOptionMenu"]["text_color"] = _themed(_TEXT_ON_AMBER)

_theme["CTkSegmentedButton"]["fg_color"] = _themed(_PANEL_HOVER)
_theme["CTkSegmentedButton"]["selected_color"] = _themed(_AMBER)
_theme["CTkSegmentedButton"]["selected_hover_color"] = _themed(_AMBER_HOVER)
_theme["CTkSegmentedButton"]["unselected_color"] = _themed(_PANEL_HOVER)
_theme["CTkSegmentedButton"]["unselected_hover_color"] = _themed(_BORDER)
_theme["CTkSegmentedButton"]["text_color"] = _themed(_TEXT)

_theme["CTkTextbox"]["fg_color"] = _themed(_INSET)
_theme["CTkTextbox"]["border_color"] = _themed(_BORDER)
_theme["CTkTextbox"]["text_color"] = _themed(_TEXT)

_theme["CTkScrollableFrame"]["label_fg_color"] = _themed(_PANEL)

_theme["DropdownMenu"]["fg_color"] = _themed(_PANEL)
_theme["DropdownMenu"]["hover_color"] = _themed(_PANEL_HOVER)
_theme["DropdownMenu"]["text_color"] = _themed(_TEXT)

_theme["CTkSwitch"]["progress_color"] = _themed(_AMBER)
_theme["CTkRadioButton"]["fg_color"] = _themed(_AMBER)
_theme["CTkRadioButton"]["hover_color"] = _themed(_AMBER_HOVER)
_theme["CTkSlider"]["button_color"] = _themed(_AMBER)
_theme["CTkSlider"]["button_hover_color"] = _themed(_AMBER_HOVER)

# Force a flat 1.0 scale rather than letting customtkinter compute its own
# factor from the (now correctly reported) OS DPI. Two multiplying scale
# factors compounding into a fractional value is the other half of the
# "dotted icon" symptom — this keeps geometry on clean pixel boundaries.
ctk.set_widget_scaling(1.0)
ctk.set_window_scaling(1.0)

MUTED = "#9aa5b1"
DIM = "#6f7a86"
BAD = "#e06c6c"

# Cap for the Server dropdown's displayed name, so a long Plex server name
# truncates with an ellipsis instead of growing the dropdown without bound.
SERVER_NAME_MAX_CHARS = 22


def _truncate_server_name(name):
    if len(name) <= SERVER_NAME_MAX_CHARS:
        return name
    return name[: SERVER_NAME_MAX_CHARS - 1].rstrip() + "…"


_GLOW_BORDER_WIDTH = 2  # thickness of the pulsing outline traced on the button itself


def _blend_hex(c1, c2, t):
    """Linear-interpolate between two '#rrggbb' colors at t in [0, 1]."""
    r1, g1, b1 = int(c1[1:3], 16), int(c1[3:5], 16), int(c1[5:7], 16)
    r2, g2, b2 = int(c2[1:3], 16), int(c2[3:5], 16), int(c2[5:7], 16)
    r = round(r1 + (r2 - r1) * t)
    g = round(g1 + (g2 - g1) * t)
    b = round(b1 + (b2 - b1) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


class PlayviorApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Playvior")
        self._set_app_icon()
        self.geometry("860x780")
        self.minsize(760, 700)

        # --- connection state, shared by both tabs ---------------------
        self.account = None            # MyPlexAccount once signed in
        self.server = None             # PlexServer currently connected
        self.resources = []            # available server resources
        self._server_name_by_display = {}   # truncated dropdown label -> real server name

        # --- export tab state --------------------------------------------
        self.export_playlists_cache = []   # plexapi Playlist objects
        self.export_checkboxes = {}        # title -> CTkCheckBox

        # --- import tab state --------------------------------------------
        self.import_docs = []              # loaded playlist docs (dicts)
        self.import_checkboxes = {}        # title -> CTkCheckBox

        # --- busy indicator (sign-in / server connect) --------------------
        self._busy_active = False

        # --- pulsing-glow animation state (bottom Export/Import buttons,
        # active + populated with playlists) --------------------------------
        self._glow_jobs = {}    # button -> scheduled `after` id, while pulsing

        self._build_layout()

    # Sizes Windows/X11/macOS actually pick between for a window icon. Below
    # ~40px the full ribbon-badge mark turns to mush (the scalloped border
    # and ribbon tails are too fine), so the small sizes use a simplified
    # ring + play-triangle version instead -- see assets/playvior_<n>.png,
    # which the icon-generation script bakes with the matching design per
    # size, and playvior.ico bundles the same per-size images for Windows.
    _ICON_PNG_SIZES = (16, 20, 24, 32, 48, 64, 128, 256)

    def _set_app_icon(self):
        """Best-effort: use the .ico on Windows (title bar + taskbar) and the
        per-size .png files everywhere else (and as an iconphoto fallback on
        Windows too), so every size Tk/the OS might pick gets a crisp image
        rather than one shrunk from a single detailed source. Never let a
        missing/unsupported icon stop the app from starting."""
        assets_dir = Path(__file__).resolve().parent / "assets"
        icon_ico = assets_dir / "playvior.ico"
        try:
            if sys.platform.startswith("win") and icon_ico.exists():
                self.iconbitmap(default=str(icon_ico))
        except Exception:
            pass
        try:
            images = []
            for size in self._ICON_PNG_SIZES:
                png_path = assets_dir / f"playvior_{size}.png"
                if png_path.exists():
                    images.append(tkinter.PhotoImage(file=str(png_path)))
            if images:
                # Keep references on self -- Tk drops an image (blanking the
                # icon) once nothing still refers to it.
                self._app_icon_images = images
                self.iconphoto(True, *images)
        except Exception:
            pass

    # ------------------------------------------------------------ layout --

    def _build_layout(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=24, pady=(20, 8))
        title_row = ctk.CTkFrame(header, fg_color="transparent")
        title_row.pack(anchor="w")
        title_font = ctk.CTkFont(size=22, weight="bold")
        # Two-tone wordmark: "Play" in the regular text color, "vior" in the
        # brand amber, packed with no gap so it reads as one word.
        ctk.CTkLabel(title_row, text="Play", font=title_font, text_color=_TEXT).pack(side="left")
        ctk.CTkLabel(title_row, text="vior", font=title_font, text_color=_AMBER).pack(side="left")
        ctk.CTkLabel(header, text="Export and import Plex video playlists", text_color=MUTED).pack(anchor="w")

        conn = ctk.CTkFrame(self, corner_radius=10)
        conn.pack(fill="x", padx=24, pady=8)
        conn.grid_columnconfigure(1, weight=1)

        self.signin_button = ctk.CTkButton(conn, text="Sign in with Plex", command=self.start_login)
        self.signin_button.grid(row=0, column=0, padx=14, pady=14, sticky="w")

        status_row = ctk.CTkFrame(conn, fg_color="transparent")
        status_row.grid(row=0, column=1, padx=8, pady=14, sticky="w")
        self.status_label = ctk.CTkLabel(status_row, text="Not signed in", text_color=MUTED)
        self.status_label.pack(side="left")
        # Green dot shown after the server name once actually connected;
        # hidden the rest of the time (pack_forget'd immediately below, and
        # again whenever a new sign-in/connect cycle starts).
        self.status_dot = ctk.CTkLabel(
            status_row, text="●", text_color="#3CCB5A", font=ctk.CTkFont(size=13)
        )
        self.status_dot.pack(side="left", padx=(6, 0))
        self.status_dot.pack_forget()

        ctk.CTkLabel(conn, text="Server:").grid(row=0, column=2, padx=(20, 6), pady=14, sticky="e")
        self.server_menu = ctk.CTkOptionMenu(
            conn,
            values=["(sign in first)"],
            command=self._on_server_menu_selected,
            height=36,
            width=220,
            dynamic_resizing=False,
        )
        self.server_menu.grid(row=0, column=3, padx=(0, 14), pady=14, sticky="e")
        self._set_optionmenu_active(self.server_menu, False)

        self.busy_bar = ctk.CTkProgressBar(conn, mode="indeterminate")
        self.busy_bar.grid(row=1, column=0, columnspan=4, padx=14, pady=(0, 12), sticky="ew")
        self.busy_bar.grid_remove()

        # --- tab switcher ---------------------------------------------------
        # CTkTabview's built-in tab selector renders each button's outer
        # corners by blending two *different* background colors together
        # (the window behind it above, the panel behind it below) — a
        # computation that turned out to depend on exact pixel geometry
        # and kept coming out wrong on certain DPI/scaling combinations no
        # matter how it was patched. A plain, standalone CTkButton doesn't
        # have that problem: every one of its corners sits against a
        # single flat background color, the same way the Sign in/Export/
        # Import buttons elsewhere in this window already render cleanly
        # everywhere. So instead of patching CTkTabview further, the tab
        # switcher here is just two ordinary buttons that toggle which
        # content frame is packed — no internal corner-blending involved.
        tab_bar = ctk.CTkFrame(self, fg_color="transparent")
        tab_bar.pack(fill="x", padx=24, pady=(8, 0))

        self.tab_export_btn = ctk.CTkButton(
            tab_bar, text="Export", width=80, command=lambda: self._select_tab("Export")
        )
        self.tab_export_btn.pack(side="left", padx=(14, 8))
        self.tab_import_btn = ctk.CTkButton(
            tab_bar, text="Import", width=80, command=lambda: self._select_tab("Import")
        )
        self.tab_import_btn.pack(side="left")

        self.tab_content = ctk.CTkFrame(self, fg_color="transparent")
        self.tab_content.pack(fill="both", expand=True, padx=24, pady=(8, 20))

        self.export_tab_frame = ctk.CTkFrame(self.tab_content, fg_color="transparent")
        self.import_tab_frame = ctk.CTkFrame(self.tab_content, fg_color="transparent")

        self._build_export_tab(self.export_tab_frame)
        self._build_import_tab(self.import_tab_frame)

        self._current_tab = None
        self._select_tab("Export")

        self.bind("<Configure>", self._on_resize)

    def _select_tab(self, name):
        if name == self._current_tab:
            return
        self._current_tab = name
        if name == "Export":
            self.import_tab_frame.pack_forget()
            self.export_tab_frame.pack(fill="both", expand=True)
        else:
            self.export_tab_frame.pack_forget()
            self.import_tab_frame.pack(fill="both", expand=True)
        self._style_toggle_button(self.tab_export_btn, name == "Export")
        self._style_toggle_button(self.tab_import_btn, name == "Import")

    @staticmethod
    def _style_toggle_button(button, selected):
        if selected:
            # Back to each CTkButton's own default (theme accent) styling.
            button.configure(
                fg_color=ctk.ThemeManager.theme["CTkButton"]["fg_color"],
                hover_color=ctk.ThemeManager.theme["CTkButton"]["hover_color"],
                text_color=ctk.ThemeManager.theme["CTkButton"]["text_color"],
                border_width=0,
            )
        else:
            button.configure(
                fg_color="transparent",
                hover_color=("gray85", "gray25"),
                text_color=MUTED,
                border_width=1,
                border_color=("gray70", "gray35"),
            )

    @staticmethod
    def _set_button_active(button, active):
        """Enable/disable a CTkButton, and swap it to a neutral grey while
        disabled instead of leaving it filled amber with faint grey text —
        amber is bright enough that disabled-state text on top of it reads
        too light to be comfortable."""
        if active:
            button.configure(
                state="normal", fg_color=_AMBER, hover_color=_AMBER_HOVER, text_color=_TEXT_ON_AMBER
            )
        else:
            button.configure(
                state="disabled",
                fg_color=_PANEL_HOVER,
                hover_color=_PANEL_HOVER,
                text_color=_TEXT,
                text_color_disabled=_TEXT,
            )

    @staticmethod
    def _set_optionmenu_active(menu, active):
        """Same idea as _set_button_active, for the Server dropdown."""
        if active:
            menu.configure(
                state="normal",
                fg_color=_AMBER,
                button_color=_AMBER_HOVER,
                button_hover_color=_AMBER_PRESSED,
                text_color=_TEXT_ON_AMBER,
            )
        else:
            menu.configure(
                state="disabled",
                fg_color=_PANEL_HOVER,
                button_color=_PANEL_HOVER,
                button_hover_color=_PANEL_HOVER,
                text_color=_TEXT,
                text_color_disabled=_TEXT,
            )

    # ---------------------------------------------------- pulsing glow --
    # A subtle "ready to go" cue on the bottom Export/Import buttons: once a
    # button is active *and* has playlists loaded (and at least one is
    # checked), a sharp blue outline pulses right on the button's own edge —
    # its border_color breathes between a dim and a bright blue. This is
    # drawn by the button itself (border_width/border_color), so the line is
    # crisp, not a separate overlapping widget, and border_width doesn't
    # change customtkinter's overall button footprint, so it never affects
    # this button's own size/position/alignment with anything else in the row.

    _GLOW_STEPS = 60          # steps per full pulse cycle
    _GLOW_INTERVAL_MS = 40    # ms between steps (~2.4s per cycle)

    def _start_glow(self, button):
        if button in self._glow_jobs:
            return  # already pulsing
        self._glow_tick(button, 0)

    def _stop_glow(self, button):
        job = self._glow_jobs.pop(button, None)
        if job is not None:
            self.after_cancel(job)
        try:
            button.configure(border_width=0)
        except Exception:
            pass  # button may have been destroyed

    def _glow_tick(self, button, step):
        try:
            if not button.winfo_exists():
                self._glow_jobs.pop(button, None)
                return
        except Exception:
            self._glow_jobs.pop(button, None)
            return
        t = (step % self._GLOW_STEPS) / self._GLOW_STEPS
        intensity = (math.sin(t * 2 * math.pi) + 1) / 2  # smooth 0..1..0
        button.configure(
            border_width=_GLOW_BORDER_WIDTH, border_color=_blend_hex(_GLOW_BLUE_DIM, _GLOW_BLUE, intensity)
        )
        self._glow_jobs[button] = self.after(
            self._GLOW_INTERVAL_MS, lambda: self._glow_tick(button, step + 1)
        )

    def _update_export_glow(self):
        active = str(self.export_button.cget("state")) == "normal"
        populated = bool(self.export_playlists_cache)
        if active and populated:
            self._start_glow(self.export_button)
        else:
            self._stop_glow(self.export_button)

    def _update_import_glow(self):
        active = str(self.import_button.cget("state")) == "normal"
        populated = bool(self.import_docs)
        if active and populated:
            self._start_glow(self.import_button)
        else:
            self._stop_glow(self.import_button)

    # ------------------------------------------------- action-button state --
    # Whether the bottom Export/Import buttons are enabled depends on more
    # than just "connected"/"file loaded": if the user has unchecked every
    # playlist in the list, there is nothing to act on, so the button goes
    # grey (inactive) even though the underlying data is still there.

    def _update_export_button_state(self):
        any_checked = any(cb.get() for cb in self.export_checkboxes.values())
        self._set_button_active(self.export_button, bool(self.server) and any_checked)
        self._update_export_glow()

    def _update_import_button_state(self):
        any_checked = any(cb.get() for cb in self.import_checkboxes.values())
        self._set_button_active(
            self.import_button, bool(self.server) and bool(self.import_docs) and any_checked
        )
        self._update_import_glow()

    def _select_export_mode(self, mode):
        if mode == self.export_mode:
            return
        self.export_mode = mode
        self._style_toggle_button(self.mode_separate_btn, mode == "separate")
        self._style_toggle_button(self.mode_combined_btn, mode == "combined")

    def _build_export_tab(self, parent):
        list_frame = ctk.CTkFrame(parent, corner_radius=10)
        list_frame.pack(fill="x", padx=4, pady=(4, 8))
        ctk.CTkLabel(
            list_frame, text="VIDEO PLAYLISTS", font=ctk.CTkFont(size=11, weight="bold"), text_color=MUTED
        ).pack(anchor="w", padx=16, pady=(10, 4))

        self.export_list_container = ctk.CTkScrollableFrame(list_frame, fg_color="transparent", height=130)
        self.export_list_container.pack(fill="both", padx=10, pady=(0, 10))
        ctk.CTkLabel(
            self.export_list_container,
            text="Sign in and choose a server to see its video playlists.",
            text_color=DIM,
        ).pack(anchor="w", pady=20, padx=6)

        options = ctk.CTkFrame(parent, corner_radius=10)
        options.pack(fill="x", padx=4, pady=8)
        options.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            options, text="EXPORT MODE", font=ctk.CTkFont(size=11, weight="bold"), text_color=MUTED
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))
        mode_row = ctk.CTkFrame(options, fg_color="transparent")
        mode_row.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 14))
        # Same reasoning as the Export/Import tab switcher above: two plain
        # buttons instead of a CTkSegmentedButton, so corner rendering never
        # depends on blending backgrounds between adjacent segments.
        self.mode_separate_btn = ctk.CTkButton(
            mode_row, text="One file per playlist", command=lambda: self._select_export_mode("separate")
        )
        self.mode_separate_btn.pack(side="left", padx=(0, 8))
        self.mode_combined_btn = ctk.CTkButton(
            mode_row, text="Single combined file", command=lambda: self._select_export_mode("combined")
        )
        self.mode_combined_btn.pack(side="left")
        self.export_mode = None
        self._select_export_mode("separate")

        ctk.CTkLabel(
            options, text="OUTPUT FOLDER", font=ctk.CTkFont(size=11, weight="bold"), text_color=MUTED
        ).grid(row=0, column=1, sticky="w", padx=14, pady=(10, 4))
        folder_row = ctk.CTkFrame(options, fg_color="transparent")
        folder_row.grid(row=1, column=1, sticky="ew", padx=14, pady=(0, 14))

        self.output_folder_var = ctk.StringVar(value=str(Path.cwd() / "exported_playlists"))
        self.output_entry = ctk.CTkEntry(folder_row, textvariable=self.output_folder_var)
        self.output_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(folder_row, text="Browse", width=80, command=self.browse_output_folder).pack(
            side="left", padx=(8, 0)
        )

        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        action_row.pack(fill="x", padx=4, pady=(0, 8))
        # Packed exactly like the Browse button above (same width, same
        # side="right"/padx) so their edges line up — the pulsing outline
        # (see _start_glow/_glow_tick) is drawn via this button's own
        # border_width/border_color and never changes its footprint.
        self.export_button = ctk.CTkButton(action_row, text="Export", width=80, command=self.start_export)
        self.export_button.pack(side="right", padx=(0, 14))
        self._set_button_active(self.export_button, False)

        self.export_log = ctk.CTkTextbox(parent, height=90, font=ctk.CTkFont(family="Consolas", size=12))
        self.export_log.pack(fill="x", padx=4, pady=(0, 4))
        self.export_log.configure(state="disabled")

    def _build_import_tab(self, parent):
        file_row = ctk.CTkFrame(parent, corner_radius=10)
        file_row.pack(fill="x", padx=4, pady=(4, 8))
        file_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            file_row,
            text="EXPORTED JSON FILE",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MUTED,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))

        entry_row = ctk.CTkFrame(file_row, fg_color="transparent")
        entry_row.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 14))
        self.import_file_var = ctk.StringVar(value="")
        # If the user hand-clears this field (rather than picking a new file
        # via Browse), the previously loaded playlist list no longer refers
        # to anything on screen, so drop it rather than leaving stale
        # checkboxes checked against a file path that's no longer shown.
        self.import_file_var.trace_add("write", self._on_import_file_var_changed)
        self.import_file_entry = ctk.CTkEntry(
            entry_row, textvariable=self.import_file_var, placeholder_text="Choose an exported .json file..."
        )
        self.import_file_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(entry_row, text="Browse", width=80, command=self.browse_import_file).pack(
            side="left", padx=(8, 0)
        )

        list_frame = ctk.CTkFrame(parent, corner_radius=10)
        list_frame.pack(fill="x", padx=4, pady=8)
        ctk.CTkLabel(
            list_frame, text="PLAYLISTS IN FILE", font=ctk.CTkFont(size=11, weight="bold"), text_color=MUTED
        ).pack(anchor="w", padx=16, pady=(10, 4))
        self.import_list_container = ctk.CTkScrollableFrame(list_frame, fg_color="transparent", height=130)
        self.import_list_container.pack(fill="both", padx=10, pady=(0, 10))
        ctk.CTkLabel(
            self.import_list_container, text="Choose a file to see the playlists inside it.", text_color=DIM
        ).pack(anchor="w", pady=20, padx=6)

        options = ctk.CTkFrame(parent, corner_radius=10)
        options.pack(fill="x", padx=4, pady=8)
        ctk.CTkLabel(
            options,
            text="IF A PLAYLIST ALREADY EXISTS",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=MUTED,
        ).grid(row=0, column=0, sticky="w", padx=14, pady=(10, 4))
        self.conflict_menu = ctk.CTkOptionMenu(options, values=["Skip", "Replace", "Duplicate"], height=36)
        self.conflict_menu.set("Skip")
        self.conflict_menu.grid(row=1, column=0, sticky="w", padx=14, pady=(0, 14))

        action_row = ctk.CTkFrame(parent, fg_color="transparent")
        action_row.pack(fill="x", padx=4, pady=(0, 8))
        self.import_button = ctk.CTkButton(action_row, text="Import", width=80, command=self.start_import)
        self.import_button.pack(side="right", padx=(0, 14))
        self._set_button_active(self.import_button, False)

        self.import_log = ctk.CTkTextbox(parent, height=90, font=ctk.CTkFont(family="Consolas", size=12))
        self.import_log.pack(fill="x", padx=4, pady=(0, 4))
        self.import_log.configure(state="disabled")

    # ----------------------------------------------------------- helpers --

    def log(self, box, message):
        box.configure(state="normal")
        box.insert("end", message + "\n")
        box.see("end")
        box.configure(state="disabled")

    def _hide_widget(self, widget):
        """Hide a widget under whichever geometry manager placed it, and
        remember how, so _show_widget can restore it exactly."""
        manager = widget.winfo_manager()
        if manager == "grid":
            widget._playvior_saved_geo = ("grid", widget.grid_info())
            widget.grid_remove()
        elif manager == "pack":
            widget._playvior_saved_geo = ("pack", widget.pack_info())
            widget.pack_forget()
        elif manager == "place":
            widget._playvior_saved_geo = ("place", widget.place_info())
            widget.place_forget()

    def _show_widget(self, widget):
        saved = getattr(widget, "_playvior_saved_geo", None)
        if widget.winfo_manager():
            return  # already shown
        if not saved:
            return  # was never hidden by us
        manager, info = saved
        if manager == "grid":
            widget.grid(**info)
        elif manager == "pack":
            widget.pack(**info)
        elif manager == "place":
            widget.place(**info)

    def _sync_scrollbar(self, frame):
        """
        CTkScrollableFrame always allocates a scrollbar track, even when
        every row fits without scrolling. Show it only when the content
        actually overflows the visible area, and hide it otherwise.

        This reaches into customtkinter's internal _parent_canvas /
        _scrollbar attributes, since there's no public API for this. It
        also re-checks a couple of times shortly after, since right after
        populating the list Tk may not have finished laying it out yet
        (winfo_height() can still read a stale/placeholder value), which
        would otherwise make this decide wrong and never correct itself.
        """

        def attempt():
            canvas = getattr(frame, "_parent_canvas", None)
            scrollbar = getattr(frame, "_scrollbar", None)
            if canvas is None or scrollbar is None:
                return
            try:
                frame.update_idletasks()
                bbox = canvas.bbox("all")
                content_height = (bbox[3] - bbox[1]) if bbox else 0
                visible_height = canvas.winfo_height()
                if visible_height <= 1:
                    return  # not laid out yet; a later retry will catch it
                if content_height > visible_height:
                    self._show_widget(scrollbar)
                else:
                    self._hide_widget(scrollbar)
            except Exception:
                pass

        attempt()
        self.after(60, attempt)
        self.after(250, attempt)

    def _on_resize(self, event=None):
        self._sync_scrollbar(self.export_list_container)
        self._sync_scrollbar(self.import_list_container)

    # -------------------------------------------------------- busy state --
    # Sign-in and server-connect both wait on real network round trips
    # (the browser approval, then plexapi probing possible connection
    # routes to the server) that we can't meaningfully shortcut — so
    # instead we make the wait itself legible: an indeterminate progress
    # bar plus a "Just a moment..." status message, so it's clear the app
    # is still working rather than frozen.

    def _start_busy(self, label):
        self._busy_active = True
        self.status_label.configure(text=f"{label} Just a moment...")
        self.busy_bar.grid()
        self.busy_bar.start()

    def _stop_busy(self, final_text):
        self._busy_active = False
        self.busy_bar.stop()
        self.busy_bar.grid_remove()
        self.status_label.configure(text=final_text)

    def browse_output_folder(self):
        chosen = filedialog.askdirectory(title="Choose output folder")
        if chosen:
            self.output_folder_var.set(chosen)

    def browse_import_file(self):
        chosen = filedialog.askopenfilename(
            title="Choose an exported playlist file", filetypes=[("JSON files", "*.json")]
        )
        if chosen:
            self.import_file_var.set(chosen)
            self.load_import_file(chosen)

    # ------------------------------------------------------------ sign-in --
    # Runs plexapi's real PIN/OAuth flow (MyPlexPinLogin) in a background
    # thread so the window never freezes while waiting on the browser
    # approval. UI updates are marshalled back via self.after(...).

    def start_login(self):
        self.status_dot.pack_forget()
        self.signin_button.configure(
            text="Signing in...", state="disabled", text_color_disabled=_TEXT_ON_AMBER
        )
        self._start_busy("Waiting for approval in your browser...")
        threading.Thread(target=self._login_worker, daemon=True).start()

    def _login_worker(self):
        try:
            pinlogin = MyPlexPinLogin(oauth=True)
            webbrowser.open(pinlogin.oauthUrl())
            pinlogin.run(timeout=120)
            pinlogin.waitForLogin()
            if not pinlogin.token:
                self.after(0, self._login_failed, "Sign-in timed out or was not approved.")
                return
            account = MyPlexAccount(token=pinlogin.token)
            resources = [r for r in account.resources() if r.provides == "server"]
            self.after(0, self._login_succeeded, account, resources)
        except Exception as exc:
            self.after(0, self._login_failed, str(exc))

    def _login_succeeded(self, account, resources):
        self.account = account
        self.resources = resources
        names = [r.name for r in resources] or ["(no servers found)"]
        self._stop_busy(f"Signed in as {account.username}")
        display_names = [_truncate_server_name(n) for n in names]
        self._server_name_by_display = dict(zip(display_names, names))
        self.server_menu.configure(values=display_names)
        self._set_optionmenu_active(self.server_menu, bool(resources))
        self.server_menu.set(display_names[0])
        if resources:
            # A server connection attempt starts immediately below (and its
            # own status message will replace "Signed in as ..." right
            # away), so the button stays "Connecting..." rather than
            # jumping to "Signed in" early -- on_server_selected takes it
            # from here and _connect_succeeded/_connect_failed settle it.
            self.on_server_selected(names[0])
        else:
            self.signin_button.configure(
                text="Signed in", state="disabled", text_color_disabled=_TEXT_ON_AMBER
            )

    def _login_failed(self, message):
        self._stop_busy(f"Sign-in failed: {message}")
        self.signin_button.configure(text="Sign in with Plex", state="normal")

    def _on_server_menu_selected(self, display_value):
        """The dropdown shows a possibly-truncated label; translate it back
        to the real server name before handing it to on_server_selected."""
        self.on_server_selected(self._server_name_by_display.get(display_value, display_value))

    def on_server_selected(self, name):
        self.status_dot.pack_forget()
        self._start_busy(f"Connecting to {name}...")
        self.signin_button.configure(
            text="Connecting...", state="disabled", text_color_disabled=_TEXT_ON_AMBER
        )
        self._set_button_active(self.export_button, False)
        self._set_button_active(self.import_button, False)
        self._update_export_glow()
        self._update_import_glow()
        threading.Thread(target=self._connect_worker, args=(name,), daemon=True).start()

    def _connect_worker(self, name):
        try:
            resource = next(r for r in self.resources if r.name == name)
            server = resource.connect()
            self.after(0, self._connect_succeeded, server, name)
        except Exception as exc:
            self.after(0, self._connect_failed, str(exc))

    def _connect_succeeded(self, server, name):
        self.server = server
        self._stop_busy(f"Connected to {name}")
        self.status_dot.pack(side="left", padx=(6, 0))
        self.signin_button.configure(
            text="Signed in", state="disabled", text_color_disabled=_TEXT_ON_AMBER
        )
        self.refresh_export_playlists()
        self._update_import_button_state()

    def _connect_failed(self, message):
        self._stop_busy(f"Connection failed: {message}")
        self.signin_button.configure(
            text="Signed in", state="disabled", text_color_disabled=_TEXT_ON_AMBER
        )

    # ------------------------------------------------------------ export --

    def refresh_export_playlists(self):
        for child in self.export_list_container.winfo_children():
            child.destroy()
        self.export_checkboxes = {}

        playlists = get_video_playlists(self.server)
        self.export_playlists_cache = playlists

        if not playlists:
            ctk.CTkLabel(
                self.export_list_container, text="No video playlists found on this server.", text_color=DIM
            ).pack(anchor="w", pady=20, padx=6)
            self._sync_scrollbar(self.export_list_container)
            self._update_export_button_state()
            return

        for pl in playlists:
            row = ctk.CTkFrame(self.export_list_container, fg_color="transparent")
            row.pack(fill="x", pady=3)
            cb = ctk.CTkCheckBox(row, text=pl.title, command=self._update_export_button_state)
            cb.select()
            cb.pack(side="left")
            ctk.CTkLabel(row, text=f"{len(pl.items())} items", text_color=DIM).pack(side="right", padx=8)
            self.export_checkboxes[pl.title] = cb

        self._sync_scrollbar(self.export_list_container)
        self._update_export_button_state()

    def start_export(self):
        selected_titles = {t for t, cb in self.export_checkboxes.items() if cb.get()}
        selected = [p for p in self.export_playlists_cache if p.title in selected_titles]
        if not selected:
            messagebox.showwarning("Playvior", "Select at least one playlist to export.")
            return

        mode = self.export_mode
        output_dir = Path(self.output_folder_var.get())

        self._set_button_active(self.export_button, False)
        self._update_export_glow()
        self.log(self.export_log, f"Exporting {len(selected)} playlist(s)...")
        threading.Thread(target=self._export_worker, args=(selected, mode, output_dir), daemon=True).start()

    def _export_worker(self, playlists, mode, output_dir):
        try:
            if mode == "separate":
                written = export_separate_files(playlists, self.server, output_dir)
                for path in written:
                    self.after(0, self.log, self.export_log, f"Wrote {path.name}")
            else:
                path = export_combined_file(playlists, self.server, output_dir)
                self.after(0, self.log, self.export_log, f"Wrote {path.name}")
            self.after(0, self.log, self.export_log, "Done.")
        except Exception as exc:
            self.after(0, self.log, self.export_log, f"Export failed: {exc}")
        finally:
            self.after(0, self._update_export_button_state)

    # ------------------------------------------------------------ import --

    def _on_import_file_var_changed(self, *_args):
        if not self.import_file_var.get().strip():
            self._clear_import_playlists()

    def _clear_import_playlists(self):
        for child in self.import_list_container.winfo_children():
            child.destroy()
        self.import_checkboxes = {}
        self.import_docs = []
        ctk.CTkLabel(
            self.import_list_container, text="Choose a file to see the playlists inside it.", text_color=DIM
        ).pack(anchor="w", pady=20, padx=6)
        self._sync_scrollbar(self.import_list_container)
        self._update_import_button_state()

    def load_import_file(self, path):
        for child in self.import_list_container.winfo_children():
            child.destroy()
        self.import_checkboxes = {}

        try:
            docs = load_playlist_docs(Path(path))
        except Exception as exc:
            ctk.CTkLabel(
                self.import_list_container, text=f"Couldn't read file: {exc}", text_color=BAD
            ).pack(anchor="w", pady=20, padx=6)
            self.import_docs = []
            self._sync_scrollbar(self.import_list_container)
            self._update_import_button_state()
            return

        self.import_docs = docs
        for doc in docs:
            row = ctk.CTkFrame(self.import_list_container, fg_color="transparent")
            row.pack(fill="x", pady=3)
            cb = ctk.CTkCheckBox(row, text=doc["playlist_title"], command=self._update_import_button_state)
            cb.select()
            cb.pack(side="left")
            ctk.CTkLabel(row, text=f"{doc['item_count']} items", text_color=DIM).pack(side="right", padx=8)
            self.import_checkboxes[doc["playlist_title"]] = cb

        self._sync_scrollbar(self.import_list_container)
        self._update_import_button_state()

    def start_import(self):
        selected_titles = {t for t, cb in self.import_checkboxes.items() if cb.get()}
        selected_docs = [d for d in self.import_docs if d["playlist_title"] in selected_titles]
        if not selected_docs:
            messagebox.showwarning("Playvior", "Select at least one playlist to import.")
            return
        if not self.server:
            messagebox.showwarning("Playvior", "Sign in and choose a target server first.")
            return

        conflict_map = {"Skip": "skip", "Replace": "replace", "Duplicate": "rename"}
        on_conflict = conflict_map[self.conflict_menu.get()]

        self._set_button_active(self.import_button, False)
        self._update_import_glow()
        self.log(self.import_log, "Indexing target server library...")
        threading.Thread(target=self._import_worker, args=(selected_docs, on_conflict), daemon=True).start()

    def _import_worker(self, docs, on_conflict):
        try:
            idx = build_library_index(self.server)
            self.after(0, self.log, self.import_log, "Importing...")
            for doc in docs:
                result = import_playlist(self.server, doc, idx, on_conflict=on_conflict)
                if result.skipped_reason:
                    self.after(0, self.log, self.import_log, f"⚠️ {result.playlist_title}: {result.skipped_reason}")
                    continue
                self.after(
                    0,
                    self.log,
                    self.import_log,
                    f"✅ {result.playlist_title}: {len(result.matched)} matched, {len(result.unmatched)} unmatched",
                )
                for entry in result.unmatched:
                    label = (
                        entry["title"]
                        if entry["type"] == "movie"
                        else f"{entry.get('show_title')} S{entry.get('season_number')}E{entry.get('episode_number')} - {entry['title']}"
                    )
                    self.after(0, self.log, self.import_log, f"    - {label}")
            self.after(0, self.log, self.import_log, "Done.")
        except Exception as exc:
            self.after(0, self.log, self.import_log, f"Import failed: {exc}")
        finally:
            self.after(0, self._update_import_button_state)


if __name__ == "__main__":
    app = PlayviorApp()
    app.mainloop()
