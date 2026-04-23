from __future__ import annotations

import customtkinter as ctk

import auth
from theme import (
    ACCENT,
    ACCENT_HOVER,
    APP_BG,
    BORDER,
    FONT_FAMILY,
    INPUT_BG,
    PANEL_ALT,
    PANEL_BG,
    TEXT_MUTED,
    TEXT_PRIMARY,
)


class LoginPage(ctk.CTkFrame):
    def __init__(self, parent, login_callback):
        super().__init__(parent, fg_color=APP_BG)
        self.login_callback = login_callback
        self.auto_login_var = ctk.BooleanVar(value=False)
        self._build_ui()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=6)
        self.grid_columnconfigure(1, weight=5)
        self.grid_rowconfigure(0, weight=1)

        left = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=0)
        left.grid(row=0, column=0, sticky="nsew")

        right = ctk.CTkFrame(self, fg_color=APP_BG, corner_radius=0)
        right.grid(row=0, column=1, sticky="nsew", padx=28, pady=28)

        self._build_intro(left)
        self._build_form(right)

    def _build_intro(self, parent) -> None:
        wrap = ctk.CTkFrame(parent, fg_color="transparent")
        wrap.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            wrap,
            text="HS 웹훅 전송기 v1.2",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 30, "bold"),
        ).pack(anchor="w")

        ctk.CTkLabel(
            wrap,
            text="디스코드 웹훅 메시지를 라이선스 기반으로 관리하고,\n검은 테마의 라이브 미리보기로 바로 확인할 수 있는 전송기입니다.",
            justify="left",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 13),
        ).pack(anchor="w", pady=(14, 24))

        for badge in (
            "실시간 Discord 스타일 미리보기",
            "자동 저장 + 만료 후 재등록 데이터 유지",
            "라이선스 첫 로그인 시점부터 사용 시간 시작",
        ):
            card = ctk.CTkFrame(wrap, fg_color=PANEL_ALT, corner_radius=16, border_width=1, border_color=BORDER)
            card.pack(fill="x", pady=6)
            ctk.CTkLabel(
                card,
                text=badge,
                text_color=TEXT_PRIMARY,
                font=(FONT_FAMILY, 12),
                anchor="w",
            ).pack(fill="x", padx=16, pady=14)

    def _build_form(self, parent) -> None:
        card = ctk.CTkFrame(parent, fg_color=PANEL_BG, corner_radius=24, border_width=1, border_color=BORDER)
        card.place(relx=0.5, rely=0.5, anchor="center", relwidth=0.92, relheight=0.72)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="로그인",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(28, 8))

        ctk.CTkLabel(
            card,
            text="발급받은 라이선스를 입력하세요.",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 12),
        ).grid(row=1, column=0, sticky="w", padx=28)

        self.entry = ctk.CTkEntry(
            card,
            height=46,
            fg_color=INPUT_BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            placeholder_text="라이선스 코드를 입력하세요",
            font=(FONT_FAMILY, 14),
        )
        self.entry.grid(row=2, column=0, sticky="ew", padx=28, pady=(28, 12))
        self.entry.bind("<Return>", lambda _event: self.attempt_login())
        self.entry.insert(0, auth.get_last_license_key())

        self.auto_login_box = ctk.CTkCheckBox(
            card,
            text="자동 로그인",
            variable=self.auto_login_var,
            checkbox_width=20,
            checkbox_height=20,
            corner_radius=6,
            text_color=TEXT_PRIMARY,
            border_color=BORDER,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            font=(FONT_FAMILY, 12),
        )
        self.auto_login_box.grid(row=3, column=0, sticky="w", padx=28)

        self.error_label = ctk.CTkLabel(
            card,
            text="",
            text_color="#ff7389",
            font=(FONT_FAMILY, 11),
        )
        self.error_label.grid(row=4, column=0, sticky="w", padx=28, pady=(10, 0))

        login_button = ctk.CTkButton(
            card,
            text="로그인",
            height=48,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#07110d",
            font=(FONT_FAMILY, 14, "bold"),
            command=self.attempt_login,
        )
        login_button.grid(row=5, column=0, sticky="ew", padx=28, pady=(22, 18))

        ctk.CTkLabel(
            card,
            text="첫 로그인 후부터 라이선스 사용 기간이 계산됩니다.",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        ).grid(row=6, column=0, sticky="w", padx=28)

    def attempt_login(self) -> None:
        key = self.entry.get().strip()
        info = auth.login(key, auto_login=self.auto_login_var.get())
        if info.get("ok"):
            self.error_label.configure(text="")
            self.login_callback(info)
            return

        self.error_label.configure(text=info.get("error", "로그인에 실패했습니다."))
