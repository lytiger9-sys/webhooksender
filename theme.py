from __future__ import annotations

import customtkinter as ctk


FONT_FAMILY = "Malgun Gothic"
MONO_FAMILY = "Consolas"

APP_BG = "#0b0d12"
PANEL_BG = "#131722"
PANEL_ALT = "#181d2a"
INPUT_BG = "#0f131c"
DISCORD_BG = "#313338"
DISCORD_PANEL = "#2b2d31"
TEXT_PRIMARY = "#f5f7fb"
TEXT_MUTED = "#98a1b3"
TEXT_SOFT = "#6f7788"
ACCENT = "#4de1b2"
ACCENT_HOVER = "#32c89a"
WARNING = "#f2c94c"
DANGER = "#ff657d"
BORDER = "#232838"
SUCCESS = "#4de1b2"


def apply_theme(root: ctk.CTk) -> None:
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root.option_add("*Font", "{Malgun Gothic} 11")
