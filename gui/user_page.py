from __future__ import annotations

from datetime import timedelta

import customtkinter as ctk

import api_handler
import auth
import database
from gui.components import DiscordPreview, HoverTooltip, WebhookInputRow
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
    TEXT_SOFT,
    WARNING,
)
from utils import add_days, format_remaining, format_timestamp, normalize_positive_int, now_local, parse_iso, to_iso


class UserPage(ctk.CTkFrame):
    def __init__(self, parent, info, logout_callback):
        super().__init__(parent, fg_color=APP_BG)
        self.logout_callback = logout_callback
        self.info = dict(info)
        self.loading_slot = False
        self.current_idx = 0
        self.sidebar_buttons = []
        self.webhook_rows = []
        self.scheduler_after_id = None
        self.license_after_id = None

        self.db = database.load_db()
        database.ensure_profile_capacity(
            self.db,
            int(self.info.get("message_limit", 1) or 1),
            int(self.info.get("webhook_limit", 1) or 1),
        )
        database.save_all(self.db)
        self.profile = self.db["profile"]

        self.active_message_limit = int(self.info.get("message_limit", 1) or 1)
        self.active_webhook_limit = int(self.info.get("webhook_limit", 1) or 1)
        self.max_webhook_slots = max(
            self.active_webhook_limit,
            max(len(slot.get("webhooks", [])) or 1 for slot in self.profile.get("slots", [])),
        )

        self._build_ui()
        self._refresh_sidebar()
        self.switch_slot(0)
        self._refresh_license_info()
        self._start_scheduler()

    def destroy(self):
        if self.scheduler_after_id:
            self.after_cancel(self.scheduler_after_id)
            self.scheduler_after_id = None
        if self.license_after_id:
            self.after_cancel(self.license_after_id)
            self.license_after_id = None
        super().destroy()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, fg_color=PANEL_BG, corner_radius=0, width=260)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="HS 웹훅 전송기",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 22, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(24, 6))

        ctk.CTkLabel(
            self.sidebar,
            text="메시지 제목은 왼쪽 사이드바에만 표시되고 실제 전송에는 포함되지 않습니다.",
            justify="left",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 16))

        self.slot_list = ctk.CTkScrollableFrame(self.sidebar, fg_color="transparent")
        self.slot_list.grid(row=2, column=0, sticky="nsew", padx=12)
        self.slot_list.grid_columnconfigure(0, weight=1)

        footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=18, pady=18)
        footer.grid_columnconfigure(0, weight=1)

        self.license_card = ctk.CTkFrame(footer, fg_color=PANEL_ALT, corner_radius=18, border_width=1, border_color=BORDER)
        self.license_card.grid(row=0, column=0, sticky="ew")

        ctk.CTkLabel(
            self.license_card,
            text="라이선스 정보",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13, "bold"),
        ).pack(anchor="w", padx=16, pady=(16, 8))

        self.license_info_label = ctk.CTkLabel(
            self.license_card,
            text="",
            justify="left",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        )
        self.license_info_label.pack(anchor="w", padx=16, pady=(0, 16))

        logout_button = ctk.CTkButton(
            footer,
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
        logout_button.grid(row=1, column=0, sticky="ew", pady=(14, 0))

        workspace = ctk.CTkFrame(self, fg_color=APP_BG)
        workspace.grid(row=0, column=1, sticky="nsew", padx=24, pady=24)
        workspace.grid_columnconfigure(0, weight=6)
        workspace.grid_columnconfigure(1, weight=5)
        workspace.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(workspace, fg_color="transparent")
        header.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        header.grid_columnconfigure(0, weight=1)

        self.page_title = ctk.CTkLabel(
            header,
            text="메시지 1",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 24, "bold"),
        )
        self.page_title.grid(row=0, column=0, sticky="w")

        self.page_subtitle = ctk.CTkLabel(
            header,
            text="제목과 내용을 편집하면 자동 저장되고 오른쪽에서 바로 라이브 프리뷰가 갱신됩니다.",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 12),
        )
        self.page_subtitle.grid(row=1, column=0, sticky="w", pady=(6, 0))

        editor = ctk.CTkFrame(workspace, fg_color=PANEL_BG, corner_radius=22, border_width=1, border_color=BORDER)
        editor.grid(row=1, column=0, sticky="nsew", padx=(0, 12))
        editor.grid_rowconfigure(4, weight=1)
        editor.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            editor,
            text="메시지 편집",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 18, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(22, 10))

        self.lock_note = ctk.CTkLabel(
            editor,
            text="",
            text_color=WARNING,
            font=(FONT_FAMILY, 11),
        )
        self.lock_note.grid(row=1, column=0, sticky="w", padx=22)

        title_wrap = ctk.CTkFrame(editor, fg_color="transparent")
        title_wrap.grid(row=2, column=0, sticky="ew", padx=22, pady=(14, 12))
        title_wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            title_wrap,
            text="제목",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.title_entry = ctk.CTkEntry(
            title_wrap,
            height=42,
            fg_color=INPUT_BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 13),
        )
        self.title_entry.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.title_entry.bind("<KeyRelease>", self._handle_form_change)

        content_wrap = ctk.CTkFrame(editor, fg_color="transparent")
        content_wrap.grid(row=3, column=0, sticky="nsew", padx=22, pady=(0, 10))
        content_wrap.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            content_wrap,
            text="내용",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.counter_label = ctk.CTkLabel(
            content_wrap,
            text="0 / 2000",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        )
        self.counter_label.grid(row=0, column=1, sticky="e")

        self.content_box = ctk.CTkTextbox(
            content_wrap,
            height=280,
            fg_color=INPUT_BG,
            border_width=1,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12),
            wrap="word",
        )
        self.content_box.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        self.content_box.bind("<KeyRelease>", self._handle_form_change)

        controls = ctk.CTkFrame(editor, fg_color="transparent")
        controls.grid(row=4, column=0, sticky="ew", padx=22, pady=(0, 0))
        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            controls,
            text="주기(일)",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12, "bold"),
        ).grid(row=0, column=0, sticky="w")

        self.interval_entry = ctk.CTkEntry(
            controls,
            width=86,
            height=40,
            fg_color=INPUT_BG,
            border_color=BORDER,
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 12),
        )
        self.interval_entry.grid(row=0, column=1, sticky="w", padx=(12, 0))
        self.interval_entry.bind("<FocusOut>", self._commit_interval)
        self.interval_entry.bind("<Return>", self._commit_interval)

        self.send_button = ctk.CTkButton(
            controls,
            text="메시지 전송",
            height=44,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#07110d",
            font=(FONT_FAMILY, 13, "bold"),
            command=self.send_current_message,
        )
        self.send_button.grid(row=0, column=2, sticky="e")
        HoverTooltip(self.send_button, self._build_send_tooltip)

        self.send_state_label = ctk.CTkLabel(
            editor,
            text="",
            text_color=TEXT_SOFT,
            font=(FONT_FAMILY, 11),
        )
        self.send_state_label.grid(row=5, column=0, sticky="w", padx=22, pady=(14, 4))

        self.last_sent_label = ctk.CTkLabel(
            editor,
            text="메시지 전송 버튼을 통해 메시지 전송을 시작하세요",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        )
        self.last_sent_label.grid(row=6, column=0, sticky="w", padx=22, pady=(0, 22))

        self.preview = DiscordPreview(workspace)
        self.preview.grid(row=1, column=1, sticky="nsew")

        webhook_card = ctk.CTkFrame(workspace, fg_color=PANEL_BG, corner_radius=22, border_width=1, border_color=BORDER)
        webhook_card.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(16, 0))
        webhook_card.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            webhook_card,
            text="웹훅 입력",
            text_color=TEXT_PRIMARY,
            font=(FONT_FAMILY, 18, "bold"),
        ).grid(row=0, column=0, sticky="w", padx=22, pady=(20, 6))

        self.webhook_hint = ctk.CTkLabel(
            webhook_card,
            text="웹훅 링크는 discord.com 기반 주소만 허용됩니다.",
            text_color=TEXT_MUTED,
            font=(FONT_FAMILY, 11),
        )
        self.webhook_hint.grid(row=1, column=0, sticky="w", padx=22)

        self.webhook_list = ctk.CTkScrollableFrame(webhook_card, fg_color="transparent", height=220)
        self.webhook_list.grid(row=2, column=0, sticky="ew", padx=18, pady=(14, 18))
        self.webhook_list.grid_columnconfigure(0, weight=1)

        for index in range(self.max_webhook_slots):
            row = WebhookInputRow(self.webhook_list, index, self._handle_form_change)
            row.grid(row=index, column=0, sticky="ew", pady=8, padx=4)
            self.webhook_rows.append(row)

    def _refresh_sidebar(self) -> None:
        for widget in self.slot_list.winfo_children():
            widget.destroy()

        self.sidebar_buttons.clear()
        for index, slot in enumerate(self.profile.get("slots", [])):
            locked = index >= self.active_message_limit
            title = (slot.get("title") or f"메시지 {index + 1}").strip() or f"메시지 {index + 1}"
            label = title if not locked else f"잠김 · {title}"

            button = ctk.CTkButton(
                self.slot_list,
                text=label,
                height=44,
                anchor="w",
                fg_color="transparent",
                hover_color=PANEL_ALT,
                border_width=1,
                border_color=BORDER,
                text_color=TEXT_MUTED if locked else TEXT_PRIMARY,
                font=(FONT_FAMILY, 12, "bold"),
                command=lambda idx=index: self.switch_slot(idx),
            )
            button.grid(row=index, column=0, sticky="ew", pady=5)
            self.sidebar_buttons.append(button)

        self._refresh_sidebar_selection()

    def _refresh_sidebar_selection(self) -> None:
        for index, button in enumerate(self.sidebar_buttons):
            locked = index >= self.active_message_limit
            if index == self.current_idx:
                if locked:
                    button.configure(fg_color="#403326", border_color=WARNING, text_color=TEXT_PRIMARY)
                else:
                    button.configure(fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=ACCENT, text_color="#07110d")
            else:
                button.configure(
                    fg_color="transparent",
                    hover_color=PANEL_ALT,
                    border_color=BORDER,
                    text_color=TEXT_MUTED if locked else TEXT_PRIMARY,
                )

    def switch_slot(self, idx: int) -> None:
        if idx < 0 or idx >= len(self.profile.get("slots", [])):
            return

        self.current_idx = idx
        slot = self.profile["slots"][idx]
        slot_locked = idx >= self.active_message_limit
        self.loading_slot = True

        self.page_title.configure(text=(slot.get("title") or f"메시지 {idx + 1}").strip() or f"메시지 {idx + 1}")
        self.title_entry.configure(state="normal")
        self.title_entry.delete(0, "end")
        self.title_entry.insert(0, slot.get("title") or f"메시지 {idx + 1}")

        self.content_box.configure(state="normal")
        self.content_box.delete("1.0", "end")
        self.content_box.insert("1.0", slot.get("content", ""))

        self.interval_entry.configure(state="normal")
        self.interval_entry.delete(0, "end")
        self.interval_entry.insert(0, str(max(1, int(slot.get("interval_days", 1) or 1))))

        webhooks = list(slot.get("webhooks", []))
        for row_index, row in enumerate(self.webhook_rows):
            row.set(webhooks[row_index] if row_index < len(webhooks) else "")
            row.set_locked(slot_locked or row_index >= self.active_webhook_limit)

        self._apply_lock_state(slot_locked)
        self._update_counter()
        self._update_preview()
        self._update_send_labels()
        self._refresh_sidebar_selection()
        self.loading_slot = False

    def _apply_lock_state(self, slot_locked: bool) -> None:
        self.title_entry.configure(state="disabled" if slot_locked else "normal")
        self.content_box.configure(state="disabled" if slot_locked else "normal")
        self.interval_entry.configure(state="disabled" if slot_locked else "normal")
        self.send_button.configure(state="disabled" if slot_locked else "normal")

        if slot_locked:
            self.lock_note.configure(text="이 메시지는 현재 라이선스 범위를 넘어 잠겨 있습니다. 저장된 데이터는 유지되지만 수정할 수 없습니다.")
            self.send_state_label.configure(text="현재 라이선스로는 이 메시지를 전송할 수 없습니다.", text_color=WARNING)
        else:
            self.lock_note.configure(text="")
            self.send_state_label.configure(text="", text_color=TEXT_SOFT)

        if self.active_webhook_limit <= 0:
            self.webhook_hint.configure(text="현재 라이선스가 만료되어 웹훅을 사용할 수 없습니다.")
        elif self.max_webhook_slots > self.active_webhook_limit:
            self.webhook_hint.configure(
                text=(
                    f"현재 라이선스로는 메시지당 웹훅 {self.active_webhook_limit}개까지 수정할 수 있습니다. "
                    "초과 칸은 잠긴 상태로 보관됩니다."
                )
            )
        else:
            self.webhook_hint.configure(text="웹훅 링크는 discord.com 기반 주소만 허용됩니다.")

    def _handle_form_change(self, _event=None) -> None:
        if self.loading_slot:
            return
        self._save_current_slot()

    def _commit_interval(self, _event=None) -> None:
        if self.loading_slot:
            return
        value = normalize_positive_int(self.interval_entry.get(), 1)
        self.interval_entry.delete(0, "end")
        self.interval_entry.insert(0, str(value))
        self._save_current_slot()

    def _save_current_slot(self) -> None:
        if self.current_idx >= len(self.profile.get("slots", [])):
            return

        slot = self.profile["slots"][self.current_idx]
        content = self.content_box.get("1.0", "end-1c")
        if len(content) > 2000:
            content = content[:2000]
            self.content_box.delete("1.0", "end")
            self.content_box.insert("1.0", content)

        slot["title"] = self.title_entry.get().strip() or f"메시지 {self.current_idx + 1}"
        slot["content"] = content
        slot["interval_days"] = normalize_positive_int(self.interval_entry.get(), slot.get("interval_days", 1))
        slot["webhooks"] = [row.get() for row in self.webhook_rows]

        database.save_all(self.db)
        self.page_title.configure(text=slot["title"])
        self._update_counter()
        self._update_preview()
        self._refresh_sidebar()

    def _update_counter(self) -> None:
        count = len(self.content_box.get("1.0", "end-1c"))
        self.counter_label.configure(text=f"{count} / 2000")

    def _update_preview(self) -> None:
        self.preview.render(self.content_box.get("1.0", "end-1c"))

    def _build_send_tooltip(self) -> str:
        interval = normalize_positive_int(self.interval_entry.get(), 1)
        return f"메시지를 전송합니다. 이제부터 {interval}일마다 메시지가 전송됩니다."

    def _update_send_labels(self) -> None:
        slot = self.profile["slots"][self.current_idx]
        if slot.get("last_sent_at"):
            self.last_sent_label.configure(text=f"{format_timestamp(slot['last_sent_at'])}에 마지막으로 보냈습니다.")
        else:
            self.last_sent_label.configure(text="메시지 전송 버튼을 통해 메시지 전송을 시작하세요")

        if self.current_idx >= self.active_message_limit:
            self.send_state_label.configure(text="현재 라이선스로는 이 메시지를 전송할 수 없습니다.", text_color=WARNING)
            return

        last_result = slot.get("last_result")
        if last_result == "failure" and slot.get("last_error"):
            self.send_state_label.configure(text=slot["last_error"], text_color=DANGER)
        elif last_result == "partial":
            self.send_state_label.configure(text="일부 웹훅 전송에 실패했습니다.", text_color=WARNING)
        elif last_result == "success" and slot.get("sending_enabled"):
            self.send_state_label.configure(
                text=f"{slot.get('interval_days', 1)}일 주기 자동 전송이 활성화되어 있습니다.",
                text_color=ACCENT,
            )
        elif self.current_idx < self.active_message_limit:
            self.send_state_label.configure(text="", text_color=TEXT_SOFT)

    def send_current_message(self) -> None:
        if self.current_idx >= self.active_message_limit:
            return
        self._commit_interval()
        success = self._dispatch_slot(self.current_idx, manual=True)
        if success:
            self._refresh_sidebar()

    def _dispatch_slot(self, slot_index: int, manual: bool) -> bool:
        slot = self.profile["slots"][slot_index]
        if slot_index >= self.active_message_limit:
            return False

        content = (slot.get("content") or "").strip()
        now = now_local()

        if not content:
            slot["last_result"] = "failure"
            slot["last_error"] = "메시지 내용을 입력하세요."
            if not slot.get("last_sent_at"):
                slot["sending_enabled"] = False
                slot["next_attempt_at"] = None
            elif slot.get("sending_enabled"):
                slot["next_attempt_at"] = to_iso(now + timedelta(hours=1))
            database.save_all(self.db)
            if self.current_idx == slot_index:
                self._update_send_labels()
            return False

        valid_targets = []
        for webhook_index, url in enumerate(slot.get("webhooks", [])[: self.active_webhook_limit]):
            clean_url = (url or "").strip()
            if not clean_url:
                if self.current_idx == slot_index and webhook_index < len(self.webhook_rows):
                    self.webhook_rows[webhook_index].clear_status()
                continue

            is_valid, message = api_handler.validate_discord_webhook(clean_url)
            if not is_valid:
                if self.current_idx == slot_index and webhook_index < len(self.webhook_rows):
                    self.webhook_rows[webhook_index].mark_send_result(False, message)
                continue
            valid_targets.append((webhook_index, clean_url))

        if not valid_targets:
            slot["last_result"] = "failure"
            slot["last_error"] = "전송 가능한 디스코드 웹훅을 하나 이상 입력하세요."
            if not slot.get("last_sent_at"):
                slot["sending_enabled"] = False
                slot["next_attempt_at"] = None
            elif slot.get("sending_enabled"):
                slot["next_attempt_at"] = to_iso(now + timedelta(hours=1))
            database.save_all(self.db)
            if self.current_idx == slot_index:
                self._update_send_labels()
            return False

        success_count = 0
        failure_count = 0
        last_error = ""

        for webhook_index, clean_url in valid_targets:
            success, message = api_handler.send_to_discord(clean_url, content)
            if self.current_idx == slot_index and webhook_index < len(self.webhook_rows):
                self.webhook_rows[webhook_index].mark_send_result(success, message)

            if success:
                success_count += 1
            else:
                failure_count += 1
                last_error = message or "웹훅 실행 실패"

        if success_count:
            slot["last_sent_at"] = to_iso(now)
            slot["sending_enabled"] = True
            slot["next_attempt_at"] = to_iso(add_days(now, slot.get("interval_days", 1)))
            slot["last_result"] = "success" if failure_count == 0 else "partial"
            slot["last_error"] = last_error if failure_count else ""
            if self.current_idx == slot_index:
                if failure_count:
                    self.send_state_label.configure(
                        text=f"{success_count}개 성공, {failure_count}개 실패. 자동 전송은 유지됩니다.",
                        text_color=WARNING,
                    )
                elif manual:
                    self.send_state_label.configure(
                        text=f"메시지를 전송했습니다. 이제부터 {slot.get('interval_days', 1)}일마다 메시지가 전송됩니다.",
                        text_color=ACCENT,
                    )
                else:
                    self.send_state_label.configure(text="예약된 자동 전송이 완료되었습니다.", text_color=ACCENT)
        else:
            slot["last_result"] = "failure"
            slot["last_error"] = last_error or "웹훅 실행 실패"
            if slot.get("sending_enabled"):
                slot["next_attempt_at"] = to_iso(now + timedelta(hours=1))
            else:
                slot["next_attempt_at"] = None
            if self.current_idx == slot_index:
                self.send_state_label.configure(text=slot["last_error"], text_color=DANGER)

        database.save_all(self.db)
        if self.current_idx == slot_index:
            self._update_send_labels()
        return success_count > 0

    def _start_scheduler(self) -> None:
        self.scheduler_after_id = self.after(1200, self._process_scheduled_messages)

    def _process_scheduled_messages(self) -> None:
        self.scheduler_after_id = None
        if self.active_message_limit > 0:
            now = now_local()
            changed = False
            for index, slot in enumerate(self.profile.get("slots", [])):
                if index >= self.active_message_limit or not slot.get("sending_enabled"):
                    continue

                next_attempt = parse_iso(slot.get("next_attempt_at"))
                if next_attempt is None:
                    last_sent = parse_iso(slot.get("last_sent_at"))
                    if last_sent:
                        slot["next_attempt_at"] = to_iso(add_days(last_sent, slot.get("interval_days", 1)))
                        changed = True
                        next_attempt = parse_iso(slot.get("next_attempt_at"))
                    else:
                        slot["sending_enabled"] = False
                        changed = True
                        continue

                if next_attempt and next_attempt <= now:
                    if self._dispatch_slot(index, manual=False):
                        changed = True

            if changed:
                database.save_all(self.db)

        self.scheduler_after_id = self.after(60000, self._process_scheduled_messages)

    def _refresh_license_info(self) -> None:
        previous_limits = (self.active_message_limit, self.active_webhook_limit)
        refreshed = auth.refresh_user_info(self.info.get("license_key", ""))

        if refreshed:
            self.info.update(refreshed)
            self.active_message_limit = int(self.info.get("message_limit", 1) or 1)
            self.active_webhook_limit = int(self.info.get("webhook_limit", 1) or 1)
        else:
            self.info["remaining_text"] = "만료됨"
            self.active_message_limit = 0
            self.active_webhook_limit = 0

        remaining_text = format_remaining(self.info.get("expires_at"))
        info_text = (
            f"보낼 수 있는 메시지 종류 수: {self.active_message_limit}개\n"
            f"메시지당 사용할 수 있는 웹훅 수: {self.active_webhook_limit}개\n"
            f"남은 기간: {remaining_text}"
        )
        self.license_info_label.configure(text=info_text)

        if previous_limits != (self.active_message_limit, self.active_webhook_limit):
            self._refresh_sidebar()
            self.switch_slot(min(self.current_idx, len(self.profile.get("slots", [])) - 1))

        self.license_after_id = self.after(60000, self._refresh_license_info)
