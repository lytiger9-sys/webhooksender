from __future__ import annotations

import re
import tkinter as tk
from tkinter import font as tkfont

import customtkinter as ctk

import api_handler
from theme import (
    ACCENT,
    BORDER,
    DANGER,
    DISCORD_BG,
    DISCORD_PANEL,
    FONT_FAMILY,
    INPUT_BG,
    MONO_FAMILY,
    PANEL_ALT,
    PANEL_BG,
    TEXT_MUTED,
    TEXT_PRIMARY,
    TEXT_SOFT,
    WARNING,
)


EMOJI_ALIASES = {
    "smile": "😄",
    "grin": "😁",
    "joy": "😂",
    "rofl": "🤣",
    "wink": "😉",
    "heart_eyes": "😍",
    "thinking": "🤔",
    "fire": "🔥",
    "sparkles": "✨",
    "rocket": "🚀",
    "wave": "👋",
    "sob": "😭",
    "thumbsup": "👍",
    "thumbsdown": "👎",
    "eyes": "👀",
    "warning": "⚠️",
    "white_check_mark": "✅",
    "x": "❌",
    "star": "⭐",
    "zap": "⚡",
    "clap": "👏",
    "pray": "🙏",
    "100": "💯",
    "tada": "🎉",
    "party": "🥳",
    "skull": "💀",
    "wave": "👋",
}

TOKEN_PATTERN = re.compile(
    r"(<a?:[A-Za-z0-9_]+:\d+>)|(`[^`\n]+`)|(\*\*[^*\n]+\*\*)|(~~[^~\n]+~~)|(__[^_\n]+__)|(\*[^*\n]+\*)|(@everyone|@here)|(:[a-z0-9_+\-]+:)|(https?://\S+)",
    re.IGNORECASE,
)


class HoverTooltip:
    def __init__(self, widget, text_provider):
        self.widget = widget
        self.text_provider = text_provider
        self.tooltip = None
        widget.bind("<Enter>", self.show_tooltip, add="+")
        widget.bind("<Leave>", self.hide_tooltip, add="+")
        widget.bind("<ButtonPress>", self.hide_tooltip, add="+")

    def show_tooltip(self, _event=None):
        text = self.text_provider() if callable(self.text_provider) else str(self.text_provider)
        if not text:
            return

        self.hide_tooltip()
        self.tooltip = tk.Toplevel(self.widget)
        self.tooltip.wm_overrideredirect(True)
        self.tooltip.attributes("-topmost", True)

        x = self.widget.winfo_rootx() + 12
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 8
        self.tooltip.wm_geometry(f"+{x}+{y}")

        label = tk.Label(
            self.tooltip,
            text=text,
            justify="left",
            bg="#151922",
            fg=TEXT_PRIMARY,
            bd=0,
            padx=10,
            pady=7,
            font=(FONT_FAMILY, 10),
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        label.pack()

    def hide_tooltip(self, _event=None):
        if self.tooltip is not None:
            self.tooltip.destroy()
            self.tooltip = None


class WebhookInputRow(ctk.CTkFrame):
    def __init__(self, master, index: int, on_change):
        super().__init__(master, fg_color="transparent")
        self.index = index
        self.on_change = on_change
        self.locked = False
        self.status_mode = "normal"

        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        self.label = ctk.CTkLabel(
            header,
            text=f"웹훅 {index + 1}",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
        )
        self.label.grid(row=0, column=0, sticky="w")

        self.entry = ctk.CTkEntry(
            self,
            height=42,
            fg_color=INPUT_BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text="https://discord.com/api/webhooks/...",
            font=(FONT_FAMILY, 11),
        )
        self.entry.grid(row=1, column=0, sticky="ew", pady=(6, 4))
        self.entry.bind("<KeyRelease>", self._handle_change)

        self.status_label = ctk.CTkLabel(
            self,
            text="",
            anchor="w",
            text_color=TEXT_SOFT,
            font=(FONT_FAMILY, 10),
        )
        self.status_label.grid(row=2, column=0, sticky="w")

    def _handle_change(self, _event=None):
        self.refresh_validation()
        if callable(self.on_change):
            self.on_change()

    def get(self) -> str:
        return self.entry.get().strip()

    def set(self, value: str) -> None:
        self.entry.configure(state="normal")
        self.entry.delete(0, "end")
        self.entry.insert(0, value or "")
        self.refresh_validation()

    def clear_status(self) -> None:
        self.status_mode = "normal"
        self.status_label.configure(text="", text_color=TEXT_SOFT)
        if self.locked:
            self.entry.configure(
                fg_color=PANEL_ALT,
                border_color=BORDER,
                text_color=TEXT_MUTED,
                state="disabled",
            )
            return

        self.entry.configure(
            fg_color=INPUT_BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            state="normal",
        )

    def refresh_validation(self) -> bool:
        if self.locked:
            return False

        value = self.get()
        self.clear_status()
        if not value:
            return False

        is_valid, message = api_handler.validate_discord_webhook(value)
        if not is_valid:
            self.status_mode = "invalid"
            self.entry.configure(
                fg_color="#171a21",
                border_color="#3c4354",
                text_color=TEXT_MUTED,
            )
            self.status_label.configure(text=message, text_color=WARNING)
            return False
        return True

    def set_locked(self, locked: bool) -> None:
        self.locked = locked
        self.entry.configure(state="normal")
        self.refresh_validation()
        if locked:
            self.status_mode = "locked"
            self.entry.configure(
                state="disabled",
                fg_color=PANEL_ALT,
                border_color=BORDER,
                text_color=TEXT_MUTED,
            )
            self.status_label.configure(
                text="현재 라이선스로는 수정할 수 없습니다",
                text_color=TEXT_SOFT,
            )

    def mark_send_result(self, success: bool, message: str = "") -> None:
        if self.locked:
            return

        if success:
            self.status_mode = "success"
            self.entry.configure(border_color=ACCENT)
            self.status_label.configure(text="전송 성공", text_color=ACCENT)
        else:
            self.status_mode = "failure"
            self.entry.configure(
                fg_color="#22151a",
                border_color=DANGER,
                text_color=TEXT_PRIMARY,
            )
            self.status_label.configure(
                text=message or "웹훅 실행 실패",
                text_color=DANGER,
            )


class DiscordPreview(ctk.CTkFrame):
    def __init__(self, master):
        super().__init__(master, fg_color=DISCORD_PANEL, corner_radius=18, border_width=1, border_color=BORDER)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(
            self,
            text="Live Preview",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 16, "bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(18, 10))

        self.avatar = ctk.CTkLabel(
            self,
            text="HS",
            width=42,
            height=42,
            fg_color=ACCENT,
            text_color="#0d1317",
            font=(FONT_FAMILY, 16, "bold"),
            corner_radius=21,
        )
        self.avatar.grid(row=1, column=0, sticky="n", padx=(18, 12), pady=(2, 18))

        body = ctk.CTkFrame(self, fg_color=DISCORD_BG, corner_radius=16)
        body.grid(row=1, column=1, sticky="nsew", padx=(0, 18), pady=(2, 18))
        body.grid_rowconfigure(0, weight=1)
        body.grid_columnconfigure(0, weight=1)

        self.text = tk.Text(
            body,
            wrap="word",
            bg=DISCORD_BG,
            fg=TEXT_PRIMARY,
            bd=0,
            relief="flat",
            padx=18,
            pady=16,
            insertbackground=TEXT_PRIMARY,
            selectbackground="#4b5365",
            highlightthickness=0,
        )
        self.text.grid(row=0, column=0, sticky="nsew")
        self.text.configure(state="disabled")

        self._setup_tags()
        self.render("")

    def _setup_tags(self) -> None:
        base_font = tkfont.Font(family=FONT_FAMILY, size=12)
        bold_font = tkfont.Font(family=FONT_FAMILY, size=12, weight="bold")
        italic_font = tkfont.Font(family=FONT_FAMILY, size=12, slant="italic")
        h1_font = tkfont.Font(family=FONT_FAMILY, size=19, weight="bold")
        h2_font = tkfont.Font(family=FONT_FAMILY, size=16, weight="bold")
        h3_font = tkfont.Font(family=FONT_FAMILY, size=14, weight="bold")
        code_font = tkfont.Font(family=MONO_FAMILY, size=11)
        username_font = tkfont.Font(family=FONT_FAMILY, size=12, weight="bold")

        self.text.tag_configure("username", font=username_font, foreground=TEXT_PRIMARY)
        self.text.tag_configure("timestamp", font=(FONT_FAMILY, 10), foreground=TEXT_MUTED)
        self.text.tag_configure("body", font=base_font, foreground=TEXT_PRIMARY, spacing1=1, spacing3=3)
        self.text.tag_configure("bold", font=bold_font)
        self.text.tag_configure("italic", font=italic_font)
        self.text.tag_configure("underline", underline=True)
        self.text.tag_configure("strike", overstrike=True)
        self.text.tag_configure("code", font=code_font, background="#1d2029", foreground="#d7e3ff")
        self.text.tag_configure("codeblock", font=code_font, background="#1d2029", foreground="#d7e3ff", lmargin1=12, lmargin2=12)
        self.text.tag_configure("quote", foreground="#c9d2e3", lmargin1=18, lmargin2=18)
        self.text.tag_configure("h1", font=h1_font, foreground=TEXT_PRIMARY, spacing1=8, spacing3=5)
        self.text.tag_configure("h2", font=h2_font, foreground=TEXT_PRIMARY, spacing1=7, spacing3=4)
        self.text.tag_configure("h3", font=h3_font, foreground=TEXT_PRIMARY, spacing1=6, spacing3=4)
        self.text.tag_configure("mention", background="#243a62", foreground="#a8c7ff")
        self.text.tag_configure("link", foreground="#7ac7ff", underline=True)
        self.text.tag_configure("emoji", foreground="#ffd166")

    def render(self, content: str) -> None:
        preview_text = (content or "").strip("\n")
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.insert("end", "HS Webhook ", ("username",))
        self.text.insert("end", "오늘  ", ("timestamp",))
        self.text.insert("end", "\n")

        if not preview_text:
            self.text.insert(
                "end",
                "메시지를 입력하면 이곳에 디스코드에서 보일 형태로 바로 미리보기가 표시됩니다.",
                ("body",),
            )
            self.text.configure(state="disabled")
            return

        code_block_mode = False
        multiline_quote = False

        for raw_line in preview_text.splitlines():
            line = raw_line.rstrip("\r")
            stripped = line.strip()

            if stripped.startswith("```"):
                code_block_mode = not code_block_mode
                continue

            if code_block_mode:
                self.text.insert("end", f"{line}\n", ("codeblock",))
                continue

            if line.startswith(">>> "):
                multiline_quote = True
                self.text.insert("end", "▎ ", ("quote",))
                self._insert_inline(line[4:], "quote")
                self.text.insert("end", "\n")
                continue

            if multiline_quote:
                self.text.insert("end", "▎ ", ("quote",))
                self._insert_inline(line, "quote")
                self.text.insert("end", "\n")
                continue

            if line.startswith("> "):
                self.text.insert("end", "▎ ", ("quote",))
                self._insert_inline(line[2:], "quote")
                self.text.insert("end", "\n")
                continue

            if line.startswith("# "):
                self.text.insert("end", f"{line[2:]}\n", ("h1",))
                continue

            if line.startswith("## "):
                self.text.insert("end", f"{line[3:]}\n", ("h2",))
                continue

            if line.startswith("### "):
                self.text.insert("end", f"{line[4:]}\n", ("h3",))
                continue

            self._insert_inline(line, "body")
            self.text.insert("end", "\n")

        self.text.configure(state="disabled")

    def _insert_inline(self, line: str, base_tag: str) -> None:
        cursor = 0
        for match in TOKEN_PATTERN.finditer(line):
            start, end = match.span()
            if start > cursor:
                self.text.insert("end", line[cursor:start], (base_tag,))

            token = match.group(0)
            if token.startswith("<") and token.endswith(">"):
                name = token.split(":")[1]
                self.text.insert("end", f":{name}:", ("emoji",))
            elif token.startswith("`"):
                self.text.insert("end", token[1:-1], ("code",))
            elif token.startswith("**"):
                self.text.insert("end", token[2:-2], ("bold",))
            elif token.startswith("~~"):
                self.text.insert("end", token[2:-2], ("strike",))
            elif token.startswith("__"):
                self.text.insert("end", token[2:-2], ("underline",))
            elif token.startswith("*") and token.endswith("*"):
                self.text.insert("end", token[1:-1], ("italic",))
            elif token in {"@everyone", "@here"}:
                self.text.insert("end", token, ("mention",))
            elif token.startswith("http://") or token.startswith("https://"):
                self.text.insert("end", token, ("link",))
            elif token.startswith(":") and token.endswith(":"):
                alias = token[1:-1].lower()
                self.text.insert("end", EMOJI_ALIASES.get(alias, token), ("body",))
            else:
                self.text.insert("end", token, (base_tag,))

            cursor = end

        if cursor < len(line):
            self.text.insert("end", line[cursor:], (base_tag,))
