from __future__ import annotations

import customtkinter as ctk

import auth
from theme import (
    ACCENT,
    ACCENT_HOVER,
    APP_BG,
    BORDER,
    DANGER,
    FONT_FAMILY,
    INPUT_BG,
    PANEL_ALT,
    PANEL_BG,
    TEXT_MUTED,
    TEXT_PRIMARY,
)
from utils import format_timestamp, normalize_positive_int


class AdminPage(ctk.CTkFrame):
    def __init__(self, parent, logout_callback):
        super().__init__(parent, fg_color=APP_BG)
        self.logout_callback = logout_callback
        self.current_view = "generate"
        self.result_key = ""
        self.status_filter = ctk.StringVar(value="사용중")
        self._build_ui()
        self.show_view("generate")

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=0, width=240)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(5, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="HS 관리자",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(26, 4))

        ctk.CTkLabel(
            self.sidebar,
            text="라이선스 생성과 상태 관리를 한 곳에서 처리합니다.",
            justify="left",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        ).grid(row=1, column=0, sticky="w", padx=22, pady=(0, 20))

        self.nav_buttons = {}
        for row, (key, label) in enumerate((("generate", "라이선스 생성"), ("status", "상태"))):
            button = ctk.CTkButton(
                self.sidebar,
                text=label,
                height=42,
                anchor="w",
                fg_color="transparent",
                hover_color=PANEL_ALT,
                border_width=1,
                border_color=BORDER,
                text_color=TEXT_PRIMARY,
                font=(FONT_FAMILY, 13, "bold"),
                command=lambda value=key: self.show_view(value),
            )
            button.grid(row=row + 2, column=0, sticky="ew", padx=18, pady=6)
            self.nav_buttons[key] = button

        logout_button = ctk.CTkButton(
            self.sidebar,
            text="로그아웃",
            height=42,
            fg_color="#1a202c",
            hover_color="#20293a",
            border_width=1,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13, "bold"),
            command=self.logout_callback,
        )
        logout_button.grid(row=6, column=0, sticky="ew", padx=18, pady=18)

        self.content = ctk.CTkFrame(self, fg_color=APP_BG)
        self.content.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)
        self.content.grid_rowconfigure(0, weight=1)
        self.content.grid_columnconfigure(0, weight=1)

    def show_view(self, view_name: str) -> None:
        self.current_view = view_name
        for key, button in self.nav_buttons.items():
            if key == view_name:
                button.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#07110d", border_color=ACCENT)
            else:
                button.configure(fg_color="transparent", hover_color=PANEL_ALT, text_color=TEXT_PRIMARY, border_color=BORDER)

        for widget in self.content.winfo_children():
            widget.destroy()

        if view_name == "generate":
            self._build_generate_view()
        else:
            self._build_status_view()

    def _build_generate_view(self) -> None:
        card = ctk.CTkFrame(self.content, fg_color=PANEL_BG, corner_radius=24, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="라이선스 생성",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(26, 8))

        ctk.CTkLabel(
            card,
            text="며칠 동안 사용할지, 메시지 종류 수, 메시지당 웹훅 수를 정한 뒤 새 라이선스를 발급하세요.",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 12),
        ).grid(row=1, column=0, sticky="w", padx=28)

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.grid(row=2, column=0, sticky="ew", padx=28, pady=(26, 18))
        form.grid_columnconfigure(1, weight=1)

        self.days_entry = self._create_input(form, 0, "사용 일수", "30")
        self.webhook_entry = self._create_input(form, 1, "메시지당 웹훅 수", "3")
        self.message_entry = self._create_input(form, 2, "메시지 종류 수", "5")

        action = ctk.CTkButton(
            card,
            text="라이선스 생성",
            height=48,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#07110d",
            font=(FONT_FAMILY, 14, "bold"),
            command=self.generate_key,
        )
        action.grid(row=3, column=0, sticky="ew", padx=28)

        self.generate_error = ctk.CTkLabel(
            card,
            text="",
            text_color="#ff7389",
            font=(FONT_FAMILY, 11),
        )
        self.generate_error.grid(row=4, column=0, sticky="w", padx=28, pady=(10, 0))

        result_card = ctk.CTkFrame(card, fg_color=PANEL_ALT, corner_radius=18, border_width=1, border_color=BORDER)
        result_card.grid(row=5, column=0, sticky="ew", padx=28, pady=(18, 28))
        result_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            result_card,
            text="생성된 라이선스",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 14, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 8))

        self.result_entry = ctk.CTkEntry(
            result_card,
            height=46,
            fg_color=INPUT_BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 15, "bold"),
        )
        self.result_entry.grid(row=1, column=0, sticky="ew", padx=18)

        copy_button = ctk.CTkButton(
            result_card,
            text="클립보드에 복사",
            height=42,
            fg_color="#202a3a",
            hover_color="#29354b",
            border_width=1,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
            command=self.copy_to_clipboard,
        )
        copy_button.grid(row=2, column=0, sticky="ew", padx=18, pady=(14, 18))

    def _create_input(self, master, row: int, label: str, default: str):
        ctk.CTkLabel(
            master,
            text=label,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
        ).grid(row=row, column=0, sticky="w", pady=10)

        entry = ctk.CTkEntry(
            master,
            height=42,
            fg_color=INPUT_BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13),
        )
        entry.insert(0, default)
        entry.grid(row=row, column=1, sticky="ew", pady=10)
        return entry

    def generate_key(self) -> None:
        days = normalize_positive_int(self.days_entry.get(), 30)
        webhook_limit = normalize_positive_int(self.webhook_entry.get(), 3)
        message_limit = normalize_positive_int(self.message_entry.get(), 5)

        license_data = auth.create_license(days, message_limit, webhook_limit)
        if not license_data.get("ok"):
            self.generate_error.configure(text=license_data.get("error", "라이선스 생성에 실패했습니다."))
            return

        self.result_key = license_data["key"]
        self.result_entry.delete(0, "end")
        self.result_entry.insert(0, self.result_key)
        self.generate_error.configure(text="")

    def copy_to_clipboard(self) -> None:
        key = self.result_entry.get().strip()
        if not key:
            self.generate_error.configure(text="복사할 라이선스가 없습니다.")
            return

        self.clipboard_clear()
        self.clipboard_append(key)
        self.generate_error.configure(text="클립보드에 복사했습니다.", text_color=ACCENT)
        self.after(1800, lambda: self.generate_error.configure(text="", text_color="#ff7389"))

    def _build_status_view(self) -> None:
        card = ctk.CTkFrame(self.content, fg_color=PANEL_BG, corner_radius=24, border_width=1, border_color=BORDER)
        card.grid(row=0, column=0, sticky="nsew")
        card.grid_rowconfigure(2, weight=1)
        card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            card,
            text="라이선스 상태",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 24, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=28, pady=(26, 8))

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.grid(row=1, column=0, sticky="ew", padx=28)
        top.grid_columnconfigure(0, weight=1)

        segmented = ctk.CTkSegmentedButton(
            top,
            values=["사용중", "만료", "미사용"],
            variable=self.status_filter,
            command=lambda _value: self.refresh_status_list(),
            fg_color=PANEL_ALT,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=PANEL_ALT,
            unselected_hover_color="#20263a",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
        )
        segmented.set("사용중")
        segmented.grid(row=0, column=0, sticky="w")

        self.bulk_button = ctk.CTkButton(
            top,
            text="",
            height=36,
            width=140,
            fg_color="#202a3a",
            hover_color="#29354b",
            border_width=1,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
            command=self.bulk_delete,
        )
        self.bulk_button.grid(row=0, column=1, sticky="e")

        self.status_hint = ctk.CTkLabel(
            card,
            text="",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        )
        self.status_hint.grid(row=3, column=0, sticky="w", padx=28, pady=(8, 24))

        self.status_list = ctk.CTkScrollableFrame(card, fg_color="transparent")
        self.status_list.grid(row=2, column=0, sticky="nsew", padx=28, pady=(18, 0))
        self.status_list.grid_columnconfigure(0, weight=1)

        self.refresh_status_list()

    def refresh_status_list(self) -> None:
        if not hasattr(self, "status_list"):
            return

        for widget in self.status_list.winfo_children():
            widget.destroy()

        filter_map = {"사용중": "active", "만료": "expired", "미사용": "unused"}
        state = filter_map[self.status_filter.get()]
        records = auth.get_license_overview(state)

        if state == "active":
            self.bulk_button.grid_remove()
            self.status_hint.configure(text="현재 사용중인 라이선스 목록입니다.")
        elif state == "expired":
            self.bulk_button.grid()
            self.bulk_button.configure(text="만료 내역 일괄 삭제", fg_color=DANGER, hover_color="#d04b62")
            self.status_hint.configure(text="만료된 라이선스는 한 번에 삭제할 수 있습니다.")
        else:
            self.bulk_button.grid()
            self.bulk_button.configure(text="미사용 전체 삭제", fg_color="#202a3a", hover_color="#29354b")
            self.status_hint.configure(text="아직 로그인되지 않은 발급 라이선스입니다.")

        if not records:
            empty = ctk.CTkFrame(self.status_list, fg_color=PANEL_ALT, corner_radius=18, border_width=1, border_color=BORDER)
            empty.grid(row=0, column=0, sticky="ew")
            ctk.CTkLabel(
                empty,
                text="표시할 라이선스가 없거나 서버 연결에 실패했습니다.",
                text_color=TEXT_MUTED,
                font=(FONT_FAMILY, 12),
            ).pack(padx=18, pady=18)
            return

        for row, record in enumerate(records):
            item = ctk.CTkFrame(self.status_list, fg_color=PANEL_ALT, corner_radius=18, border_width=1, border_color=BORDER)
            item.grid(row=row, column=0, sticky="ew", pady=6)
            item.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                item,
                text=record["key"],
                text_color=TEXT_PRIMARY,
                font=(FONT_FAMILY, 14, "bold"),
            ).grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))

            if state == "active":
                detail = (
                    f"남은 기간 {record['remaining_text']} | "
                    f"메시지 {record['message_limit']}개 | "
                    f"웹훅 {record['webhook_limit']}개"
                )
            elif state == "expired":
                detail = (
                    f"만료일 {format_timestamp(record['expires_at']) or '-'} | "
                    f"메시지 {record['message_limit']}개 | 웹훅 {record['webhook_limit']}개"
                )
            else:
                detail = (
                    f"발급일 {format_timestamp(record['created_at']) or '-'} | "
                    f"사용 예정 {record['days']}일"
                )

            ctk.CTkLabel(
                item,
                text=detail,
                text_color=TEXT_MUTED,
                font=(FONT_FAMILY, 11),
            ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 14))

            if state == "unused":
                delete_button = ctk.CTkButton(
                    item,
                    text="삭제",
                    width=90,
                    height=34,
                    fg_color=DANGER,
                    hover_color="#d04b62",
                    text_color=TEXT_PRIMARY,
                    font=(FONT_FAMILY, 11, "bold"),
                    command=lambda key=record["key"]: self.delete_one_license(key),
                )
                delete_button.grid(row=0, column=1, rowspan=2, padx=18, pady=14)

    def delete_one_license(self, key: str) -> None:
        auth.delete_license(key)
        self.refresh_status_list()

    def bulk_delete(self) -> None:
        filter_map = {"사용중": "active", "만료": "expired", "미사용": "unused"}
        state = filter_map[self.status_filter.get()]
        if state == "active":
            return
        auth.delete_licenses_by_state(state)
        self.refresh_status_list()
