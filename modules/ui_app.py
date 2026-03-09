"""
ui_app.py - Class App chính: gộp tất cả UI Mixin và xử lý menu, alarm, shared callbacks
"""
import tkinter as tk
from tkinter import Toplevel
import pygame
import keyboard
import os

from ui_helpers import add_hover_effect
from ui_upgrade import UpgradeUI
from ui_buy import BuyFodderUI
from ui_insert import InsertUI
from config import SAMPLE_DIR


class App(UpgradeUI, BuyFodderUI, InsertUI):
    def __init__(self, root):
        self.root = root
        self.sw = root.winfo_screenwidth()

        self.target_grade = None
        self.is_running = False
        self.fodder_rows = {}

        self.buy_fodder_rows_data = []
        self.ext_buy_data = {}

        self.alarm_window = None
        pygame.mixer.init()

        self.bp_protection_var = tk.BooleanVar(value=False)
        self.auto_buy_fodder_var = tk.BooleanVar(value=False)

        keyboard.add_hotkey('esc', self.stop)

        self.root.title("AUTO FCO")
        self.root.configure(bg="#0d1117")
        self.root.attributes("-topmost", True)

        self.menu_frame = tk.Frame(self.root, bg="#0d1117")
        self.upgrade_frame = tk.Frame(self.root, bg="#0d1117")
        self.insert_frame = tk.Frame(self.root, bg="#0d1117")
        self.buy_fodder_frame = tk.Frame(self.root, bg="#0d1117")

        self.btn_back_upgrade = None
        self.btn_back_buy = None
        self.btn_back_insert = None
        self.ctrl_f = None

        self.bot = None

        self.build_menu_ui()
        self.build_upgrade_ui()
        self.build_insert_ui()
        self.build_buy_fodder_ui()

        self.show_menu()

    # ===================== MENU UI =====================

    def build_menu_ui(self):
        tk.Label(
            self.menu_frame, text="AUTO FCO",
            font=("Consolas", 20, "bold"), fg="#ff79c6", bg="#0d1117"
        ).pack(pady=(40, 5))
        tk.Label(
            self.menu_frame, text="By Quybodoivodichvutru",
            font=("Consolas", 10), fg="#58a6ff", bg="#0d1117"
        ).pack(pady=(0, 25))

        btn_upgrade = tk.Button(
            self.menu_frame, text="Auto Đập Thẻ",
            bg="#238636", fg="white", font=("Consolas", 11, "bold"),
            width=18, bd=0, command=self.show_upgrade
        )
        btn_upgrade.pack(pady=6)
        add_hover_effect(btn_upgrade, "#2ea043", "#238636")

        btn_buy_fodder = tk.Button(
            self.menu_frame, text="Auto Mua Phôi",
            bg="#da3633", fg="white", font=("Consolas", 11, "bold"),
            width=18, bd=0, command=self.show_buy_fodder
        )
        btn_buy_fodder.pack(pady=6)
        add_hover_effect(btn_buy_fodder, "#f85149", "#da3633")

        btn_insert = tk.Button(
            self.menu_frame, text="Auto Chèn",
            bg="#1f6feb", fg="white", font=("Consolas", 11, "bold"),
            width=18, bd=0, command=self.show_insert
        )
        btn_insert.pack(pady=6)
        add_hover_effect(btn_insert, "#388bfd", "#1f6feb")

    # ===================== NAVIGATION =====================

    def show_menu(self):
        if self.is_running:
            return
        self.upgrade_frame.pack_forget()
        self.insert_frame.pack_forget()
        self.buy_fodder_frame.pack_forget()
        self.root.geometry(f"220x330+{self.sw - 220}+0")
        self.menu_frame.pack(fill="both", expand=True)

    def show_upgrade(self):
        if self.is_running:
            return
        self.menu_frame.pack_forget()
        self.insert_frame.pack_forget()
        self.buy_fodder_frame.pack_forget()
        h = 800 if self.auto_buy_fodder_var.get() else 600
        self.root.geometry(f"320x{h}+{self.sw - 320}+0")
        self.upgrade_frame.pack(fill="both", expand=True)

    def show_insert(self):
        if self.is_running:
            return
        self.menu_frame.pack_forget()
        self.upgrade_frame.pack_forget()
        self.buy_fodder_frame.pack_forget()
        self.insert_frame.pack(fill="both", expand=True)
        self._update_insert_window_height()

    def show_buy_fodder(self):
        if self.is_running:
            return
        self.menu_frame.pack_forget()
        self.upgrade_frame.pack_forget()
        self.insert_frame.pack_forget()
        self.buy_fodder_frame.pack(fill="both", expand=True)
        self._update_buy_window_height()

    # ===================== SHARED UI UTILS =====================

    def add_hover_effect(self, widget, hover_bg, normal_bg, hover_fg=None, normal_fg=None):
        add_hover_effect(widget, hover_bg, normal_bg, hover_fg, normal_fg)

    def lock_ui(self):
        if self.btn_back_upgrade:
            self.btn_back_upgrade.config(state="disabled", fg="#484f58")
        if hasattr(self, 'btn_start_buy'):
            self.btn_start_buy.config(state="disabled", bg="#484f58")
        if self.btn_back_buy:
            self.btn_back_buy.config(state="disabled", fg="#484f58")
        if self.btn_back_insert:
            self.btn_back_insert.config(state="disabled", fg="#484f58")

    def unlock_ui(self):
        if self.btn_back_upgrade:
            self.btn_back_upgrade.config(state="normal", fg="#c9d1d9")
        if hasattr(self, 'btn_start_buy'):
            self.btn_start_buy.config(state="normal", bg="#238636")
        if self.btn_back_buy:
            self.btn_back_buy.config(state="normal", fg="#c9d1d9")
        if self.btn_back_insert:
            self.btn_back_insert.config(state="normal", fg="#c9d1d9")

    def validate_input(self, P):
        return P == "" or (P.isdigit() and len(P) <= 3)

    def validate_price(self, P):
        return P == "" or (P.isdigit() and len(P) <= 12)

    # ===================== LOG SHARED =====================

    def _insert_log(self, widget, msg, tag):
        widget.insert("end", msg + "\n", tag)
        widget.see("end")

    # ===================== STOP =====================

    def stop(self):
        """Dừng bot (ESC hoặc tự động). Reset toàn bộ UI ngay lập tức."""
        if self.alarm_window:
            self.stop_alarm()
        if not self.is_running:
            return
        if self.bot:
            self.bot.running = False
        if self.buy_fodder_frame.winfo_ismapped():
            self.log_buy("\n🛑 ĐANG DỪNG...", "orange")
        elif self.insert_frame.winfo_ismapped():
            self.log_insert("\n🛑 ĐANG DỪNG...", "orange")
        else:
            self.log_upgrade("\n🛑 ĐANG DỪNG...", "orange")
        self._reset_ui()

    # ===================== CALLBACKS =====================

    def on_finished_callback(self, summary_data=None):
        self.root.after(0, self._on_finished_safe, summary_data)

    def _on_finished_safe(self, summary_data):
        """Callback từ bot thread khi kết thúc bình thường (không phải ESC)."""
        self._reset_ui()
        if summary_data:
            self.show_summary(summary_data)

    def _reset_ui(self):
        """Reset toàn bộ trạng thái UI về idle. Idempotent - gọi nhiều lần vẫn an toàn."""
        if not self.is_running:
            return  # Guard chống double-call
        self.is_running = False
        try:
            self.lbl_current_icon.config(image='')
            self.lbl_current_icon.image = None
        except Exception:
            pass
        try:
            if self.upgrade_frame.winfo_ismapped():
                self.b_s.config(state="normal", bg="#238636")
                self.chk_bp.config(state="normal", fg="#c9d1d9")
                self.chk_auto_buy.config(state="normal", fg="#c9d1d9")
                self.lbl_esc_hint.pack_forget()
            elif self.buy_fodder_frame.winfo_ismapped():
                self.btn_start_buy.config(state="normal", bg="#238636")
                self.lbl_esc_hint_buy.pack_forget()
            elif self.insert_frame.winfo_ismapped():
                self.btn_start_insert.config(state="normal", bg="#238636")
                self.lbl_esc_hint_insert.pack_forget()
        except Exception:
            pass
        try:
            self.unlock_ui()
        except Exception:
            pass

    # ===================== CONFIRM POPUP =====================

    def show_confirm_popup(self):
        popup = Toplevel(self.root)
        popup.overrideredirect(True)
        popup.configure(bg="#161b22", highlightthickness=1, highlightbackground="#58a6ff")
        popup.attributes("-topmost", True)
        w, h = 220, 220
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (w // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (h // 2)
        popup.geometry(f"{w}x{h}+{x}+{y}")
        tk.Label(popup, text="XÁC NHẬN", font=("Consolas", 10, "bold"), fg="#58a6ff", bg="#161b22").pack(pady=10)
        tk.Label(popup, text="Cất hết cầu thủ\nquan trọng chưa?",
                 font=("Consolas", 9), fg="#ffffff", bg="#161b22", justify="center").pack(pady=5)
        btn_f = tk.Frame(popup, bg="#161b22")
        btn_f.pack(pady=15)

        def on_ok():
            popup.destroy()
            self.execute_start()

        def on_cancel():
            popup.destroy()

        b_ok = tk.Button(btn_f, text="Ok rồi", font=("Consolas", 9, "bold"),
                         bg="#238636", fg="white", width=18, bd=0, command=on_ok)
        b_ok.pack(pady=5)
        add_hover_effect(b_ok, "#2ea043", "#238636")
        b_ca = tk.Button(btn_f, text="Quên mất đợi tí", font=("Consolas", 9),
                         bg="#484f58", fg="white", width=18, bd=0, command=on_cancel)
        b_ca.pack(pady=5)
        add_hover_effect(b_ca, "#5d6671", "#484f58")

    # ===================== ALARM =====================

    def show_alarm(self, ovr, is_success=False, custom_msg=None):
        self.root.after(0, self._show_alarm_safe, ovr, is_success, custom_msg)

    def _show_alarm_safe(self, ovr, is_success, custom_msg):
        sf, color = ("Done.mp3", "#238636") if is_success else ("hetPhoi.mp3", "#da3633")
        sp = os.path.join(SAMPLE_DIR, sf)
        if os.path.exists(sp):
            pygame.mixer.music.load(sp)
            pygame.mixer.music.play(-1)

        self.alarm_window = Toplevel(self.root)
        self.alarm_window.title("RESULT")
        self.alarm_window.configure(bg=color)
        self.alarm_window.attributes("-topmost", True)
        w, h = 400, 200
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.alarm_window.geometry(f"{w}x{h}+{(sw - w) // 2}+{(sh - h) // 2}")

        display_text = custom_msg if custom_msg else (
            f"Thành công +{ovr}" if is_success else f"Hết phôi {ovr} !!!"
        )
        tk.Label(
            self.alarm_window, text=display_text,
            font=("Consolas", 16, "bold"), fg="white", bg=color
        ).pack(pady=40)
        tk.Button(
            self.alarm_window, text="OK",
            font=("Consolas", 12, "bold"), bg="white", fg=color,
            width=15, command=self.stop_alarm
        ).pack(pady=10)

    def stop_alarm(self):
        pygame.mixer.music.stop()
        if self.alarm_window:
            self.alarm_window.destroy()
            self.alarm_window = None
