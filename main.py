from __future__ import annotations

import customtkinter as ctk

import auth
import database
from gui.admin_page import AdminPage
from gui.login_page import LoginPage
from gui.user_page import UserPage
from theme import APP_BG, apply_theme


class HSApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        database.init_db()
        apply_theme(self)

        self.title("HS 웹훅 전송기 v1.2")
        self.geometry("1480x920")
        self.minsize(1240, 760)
        self.configure(fg_color=APP_BG)

        self.current_page = None
        self.show_login(allow_auto=True)

    def show_login(self, allow_auto: bool = True) -> None:
        if self.current_page:
            self.current_page.destroy()
            self.current_page = None

        if allow_auto:
            auto_info = auth.try_auto_login()
            if auto_info:
                self._show_page(auto_info)
                return

        self.current_page = LoginPage(self, self._show_page)
        self.current_page.pack(fill="both", expand=True)

    def _show_page(self, auth_info: dict) -> None:
        if self.current_page:
            self.current_page.destroy()
            self.current_page = None

        if auth_info.get("type") == "admin":
            self.current_page = AdminPage(self, self.handle_logout)
        else:
            self.current_page = UserPage(self, auth_info, self.handle_logout)
        self.current_page.pack(fill="both", expand=True)

    def handle_logout(self) -> None:
        auth.logout()
        self.show_login(allow_auto=False)


if __name__ == "__main__":
    app = HSApp()
    app.mainloop()
