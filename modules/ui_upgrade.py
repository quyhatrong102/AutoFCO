"""
ui_upgrade.py - UI cho tab Auto Đập Thẻ
"""
import os
import threading
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk

from config import SAMPLE_DIR
from ui_helpers import add_hover_effect, prevent_typing, configure_log_tags
from bot import FCOnlineBot


class UpgradeUI:
    """
    Mixin cung cấp toàn bộ UI và logic điều khiển cho tab Auto Đập Thẻ.
    Kế thừa bởi App.
    """

    def build_upgrade_ui(self):
        self.btn_back_upgrade = tk.Button(
            self.upgrade_frame, text="< Menu",
            font=("Consolas", 8, "bold"), bg="#21262d", fg="#c9d1d9",
            bd=0, command=self.show_menu
        )
        self.btn_back_upgrade.place(x=5, y=5)
        add_hover_effect(self.btn_back_upgrade, "#30363d", "#21262d")

        tk.Label(self.upgrade_frame, text="Auto Đập Thẻ",
                 font=("Consolas", 14, "bold"), fg="#ff79c6", bg="#0d1117").pack(pady=(15, 0))
        tk.Label(self.upgrade_frame, text="By Quybodoivodichvutru",
                 font=("Consolas", 10, "bold"), fg="#58a6ff", bg="#0d1117").pack(pady=(2, 10))

        self.btn_target = tk.Button(
            self.upgrade_frame, text="Cấp thẻ đích",
            bg="#21262d", fg="#c9d1d9", font=("Consolas", 9, "bold"),
            width=20, bd=0, activebackground="#30363d", activeforeground="white",
            command=self.toggle_dropdown
        )
        self.btn_target.pack(pady=5)
        add_hover_effect(self.btn_target, "#30363d", "#21262d")

        self.drop_frame = tk.Frame(
            self.upgrade_frame, bg="#161b22",
            highlightthickness=2, highlightbackground="#58a6ff",
            padx=5, pady=5
        )
        self.load_dropdown_items()

        info_f = tk.Frame(self.upgrade_frame, bg="#0d1117")
        info_f.pack(pady=5)

        tk.Label(info_f, text="Cấp thẻ đích:", font=("Consolas", 9), fg="#8b949e",
                 bg="#0d1117", width=14, anchor="e").grid(row=0, column=0, sticky="e", padx=(0, 5), pady=2)
        self.lbl_target_icon = tk.Label(info_f, bg="#0d1117")
        self.lbl_target_icon.grid(row=0, column=1, sticky="w")

        tk.Label(info_f, text="Cấp hiện tại:", font=("Consolas", 9), fg="#8b949e",
                 bg="#0d1117", width=14, anchor="e").grid(row=1, column=0, sticky="e", padx=(0, 5), pady=2)
        self.lbl_current_icon = tk.Label(info_f, bg="#0d1117")
        self.lbl_current_icon.grid(row=1, column=1, sticky="w")

        self.fodder_container = tk.Frame(self.upgrade_frame, bg="#0d1117")
        self.fodder_container.pack(fill="x", padx=10, pady=5)

        log_wrapper = tk.Frame(self.upgrade_frame, bg="#0d1117")
        log_wrapper.pack(padx=10, pady=5, fill="both", expand=True)

        self.log_b = scrolledtext.ScrolledText(
            log_wrapper, bg="#161b22", fg="#7ee787",
            font=("Consolas", 10), height=6, bd=0
        )
        self.log_b.bind("<Key>", prevent_typing)
        self.log_b.pack(fill="both", expand=True)
        configure_log_tags(self.log_b)

        self.bottom_wrapper = tk.Frame(self.upgrade_frame, bg="#0d1117")
        self.bottom_wrapper.pack(side="bottom", fill="x", padx=10, pady=(5, 15))

        self.ctrl_f = tk.Frame(self.bottom_wrapper, bg="#0d1117")
        self.ctrl_f.pack(fill="x", pady=(0, 5))
        btn_container = tk.Frame(self.ctrl_f, bg="#0d1117")
        btn_container.pack(side="left")

        self.b_s = tk.Button(
            btn_container, text="START", bg="#238636", fg="white",
            font=("Consolas", 10, "bold"), width=10, bd=0,
            activebackground="#2ea043", command=self.start
        )
        self.b_s.pack(anchor="w")
        add_hover_effect(self.b_s, "#2ea043", "#238636")

        self.lbl_esc_hint = tk.Label(
            btn_container, text="ESC để Dừng",
            font=("Consolas", 7, "bold"), fg="#ff5555", bg="#0d1117"
        )
        self.lbl_esc_hint.pack(anchor="w", pady=(2, 0))
        self.lbl_esc_hint.pack_forget()

        self.chk_bp = tk.Checkbutton(
            self.ctrl_f, text="Bảo vệ BP",
            variable=self.bp_protection_var,
            bg="#0d1117", fg="#c9d1d9", selectcolor="#0d1117",
            activebackground="#0d1117", font=("Consolas", 9), bd=0, highlightthickness=0
        )
        self.chk_bp.pack(side="right", padx=0)
        add_hover_effect(self.chk_bp, None, None, "#58a6ff", "#c9d1d9")

        self.chk_auto_buy = tk.Checkbutton(
            self.ctrl_f, text="Auto mua phôi",
            variable=self.auto_buy_fodder_var,
            bg="#0d1117", fg="#c9d1d9", selectcolor="#0d1117",
            activebackground="#0d1117", font=("Consolas", 9), bd=0, highlightthickness=0,
            command=self.toggle_auto_buy_ext
        )
        self.chk_auto_buy.pack(side="right", padx=5)
        add_hover_effect(self.chk_auto_buy, None, None, "#58a6ff", "#c9d1d9")

        self.ext_buy_container = tk.Frame(
            self.bottom_wrapper, bg="#161b22",
            highlightthickness=1, highlightbackground="#58a6ff"
        )
        self.ext_buy_rows_container = tk.Frame(self.ext_buy_container, bg="#161b22")
        self.ext_buy_rows_container.pack(fill="both", expand=True, padx=5, pady=5)

    def toggle_auto_buy_ext(self):
        if self.auto_buy_fodder_var.get():
            self.root.geometry(f"320x800+{self.sw - 320}+0")
            self.ext_buy_container.pack(fill="x", pady=(10, 0))
            self.update_ext_buy_ui()
        else:
            self.root.geometry(f"320x600+{self.sw - 320}+0")
            self.ext_buy_container.pack_forget()

    def update_ext_buy_ui(self, *args):
        if not self.auto_buy_fodder_var.get():
            return

        unique_ovrs = set()
        for i in self.fodder_rows:
            for ent in self.fodder_rows[i]:
                val = ent.get().strip()
                if val.isdigit():
                    unique_ovrs.add(val)

        unique_ovrs = sorted(list(unique_ovrs), key=lambda x: int(x))

        old_data = {}
        for ovr, vars_dict in self.ext_buy_data.items():
            old_data[ovr] = {"price": vars_dict["price"].get(), "qty": vars_dict["qty"].get()}

        for widget in self.ext_buy_rows_container.winfo_children():
            widget.destroy()

        self.ext_buy_data.clear()

        if not unique_ovrs:
            tk.Label(
                self.ext_buy_rows_container,
                text="Hãy điền OVR phôi ở trên trước.",
                bg="#161b22", fg="#8b949e", font=("Consolas", 8)
            ).pack(pady=10)
            return

        wrapper = tk.Frame(self.ext_buy_rows_container, bg="#161b22")
        wrapper.pack(anchor="center", pady=5)

        ext_header = tk.Frame(wrapper, bg="#161b22")
        ext_header.pack(fill="x", pady=(0, 5))
        tk.Label(ext_header, text="OVR", font=("Consolas", 8, "bold"), fg="#8b949e", bg="#161b22", width=5).pack(side="left", padx=2)
        tk.Label(ext_header, text="Giá (B)", font=("Consolas", 8, "bold"), fg="#8b949e", bg="#161b22", width=12).pack(side="left", padx=2)
        tk.Label(ext_header, text="SL/lần", font=("Consolas", 8, "bold"), fg="#8b949e", bg="#161b22", width=6).pack(side="left", padx=2)

        vcmd_price = (self.root.register(self.validate_price), '%P')
        vcmd_short = (self.root.register(self.validate_input), '%P')

        for ovr in unique_ovrs:
            row_f = tk.Frame(wrapper, bg="#161b22")
            row_f.pack(fill="x", pady=2)

            tk.Entry(
                row_f, textvariable=tk.StringVar(value=ovr),
                bg="#30363d", fg="#8b949e", font=("Consolas", 9, "bold"),
                width=5, justify="center", state="readonly"
            ).pack(side="left", padx=2)

            p_val = old_data.get(ovr, {}).get("price", "") if isinstance(old_data.get(ovr), dict) else ""
            q_val = old_data.get(ovr, {}).get("qty", "10") if isinstance(old_data.get(ovr), dict) else "10"

            p_var = tk.StringVar(value=p_val)
            tk.Entry(
                row_f, textvariable=p_var, bg="#21262d", fg="white",
                font=("Consolas", 9), width=12, justify="center",
                insertbackground="white", validate='key', validatecommand=vcmd_price
            ).pack(side="left", padx=2)

            q_var = tk.StringVar(value=q_val)
            tk.Entry(
                row_f, textvariable=q_var, bg="#21262d", fg="white",
                font=("Consolas", 9), width=6, justify="center",
                insertbackground="white", validate='key', validatecommand=vcmd_short
            ).pack(side="left", padx=2)

            self.ext_buy_data[ovr] = {"price": p_var, "qty": q_var}

    def load_dropdown_items(self):
        for i in range(2, 14):
            icon = self.load_icon(i, (30, 30))
            if icon:
                btn = tk.Button(
                    self.drop_frame, image=icon, bg="#21262d", relief="flat",
                    command=lambda g=i: self.set_target(g)
                )
                btn.image = icon
                btn.grid(row=(i - 2) // 3, column=(i - 2) % 3, padx=2, pady=2)
                add_hover_effect(btn, "#30363d", "#21262d")

    def toggle_dropdown(self):
        if not self.is_running:
            if self.drop_frame.winfo_ismapped():
                self.drop_frame.place_forget()
            else:
                self.drop_frame.place(relx=0.5, y=110, anchor="n")
                self.drop_frame.lift()

    def set_target(self, grade):
        self.lbl_current_icon.config(image='')
        self.lbl_current_icon.image = None
        self.target_grade = grade
        icon = self.load_icon(grade, (25, 25))
        if icon:
            self.lbl_target_icon.config(image=icon)
            self.lbl_target_icon.image = icon
        self.drop_frame.place_forget()
        self.refresh_fodder_inputs()

    def load_icon(self, grade, size=(22, 22)):
        p = os.path.join(SAMPLE_DIR, f"{grade}.png")
        if os.path.exists(p):
            img = Image.open(p).resize(size, Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        return None

    def refresh_fodder_inputs(self):
        # Luu lai gia tri cu truoc khi xoa
        old_fodder = {}
        for i, entries in self.fodder_rows.items():
            old_fodder[i] = [ent.get() for ent in entries]

        for widget in self.fodder_container.winfo_children():
            widget.destroy()
        self.fodder_rows.clear()
        vcmd = (self.root.register(self.validate_input), '%P')
        if self.target_grade and self.target_grade > 1:
            for i in range(1, self.target_grade):
                row_f = tk.Frame(self.fodder_container, bg="#0d1117")
                row_f.pack(pady=2, anchor="center")

                tk.Label(
                    row_f, text=f"Phôi {i}->{i+1}:",
                    font=("Consolas", 8), fg="#c9d1d9", bg="#0d1117",
                    width=13, anchor="e"
                ).pack(side="left", padx=(0, 5))

                entries = []
                saved = old_fodder.get(i, [])
                for j in range(5):
                    ent = tk.Entry(
                        row_f, bg="#21262d", fg="white", font=("Consolas", 8),
                        bd=1, width=4, justify='center', insertbackground="white",
                        validate='key', validatecommand=vcmd
                    )
                    ent.pack(side="left", padx=1)
                    # Restore gia tri cu neu co
                    if j < len(saved) and saved[j]:
                        ent.insert(0, saved[j])
                    entries.append(ent)
                    ent.bind("<Return>", lambda e, r=i: self.nav_focus(r + 1, 0))
                    ent.bind("<KeyRelease>", lambda e: self.root.after(100, self.update_ext_buy_ui))
                    for k, key in enumerate(["Up", "Down", "Left", "Right"]):
                        dr = [(-1, 0), (1, 0), (0, -1), (0, 1)][k]
                        ent.bind(f"<{key}>", lambda e, r=i + dr[0], c=j + dr[1]: self.nav_focus(r, c))
                self.fodder_rows[i] = entries
        self.update_ext_buy_ui()

    def nav_focus(self, r, c):
        if r in self.fodder_rows and 0 <= c < len(self.fodder_rows[r]):
            self.fodder_rows[r][c].focus_set()

    # ===================== LOG - THREAD SAFE =====================

    def log_upgrade(self, msg, tag=None, return_pos=False):
        """
        Log thread-safe cho tab Đập Thẻ.
        QUAN TRỌNG: Đọc pos trước khi schedule để tránh race condition.
        """
        if return_pos:
            # Phải lấy pos TRƯỚC khi insert để dùng làm vị trí cập nhật sau
            # Lấy pos bằng cách đếm ký tự hiện tại (thread-safe hơn dùng index)
            # Dùng biến mutable để truyền qua callback
            pos_holder = [None]

            def _insert_and_get_pos():
                pos_holder[0] = self.log_b.index("end-1c")
                self.log_b.insert("end", msg + "\n", tag)
                self.log_b.see("end")

            self.root.after(0, _insert_and_get_pos)
            # Trả về một "proxy" - thực ra pos sẽ được dùng sau
            # Vì log_update cũng chạy qua root.after, thứ tự được đảm bảo
            return pos_holder
        else:
            self.root.after(0, lambda: self._insert_log(self.log_b, msg, tag))
            return None

    def update_log_line(self, pos_holder, status_text, tag):
        """Cập nhật dòng log sau khi đã insert - dùng pos_holder từ log_upgrade."""
        if pos_holder is None:
            return
        self.root.after(0, lambda: self._update_log_line_safe(pos_holder, status_text, tag))

    def _update_log_line_safe(self, pos_holder, status_text, tag):
        if pos_holder[0] is not None:
            self.log_b.insert(f"{pos_holder[0]} lineend", status_text, tag)

    # ===================== START / STOP =====================

    def start(self):
        if self.drop_frame.winfo_ismapped():
            self.drop_frame.place_forget()

        if self.target_grade is None:
            self.log_upgrade("Hãy chọn cấp thẻ đích", "orange")
            return
        if self.bp_protection_var.get() and self.target_grade < 9:
            self.log_upgrade("\n❌ Cấp thẻ đích <9 !!!", tag="header")
            return

        if self.auto_buy_fodder_var.get():
            for ovr, vars_dict in self.ext_buy_data.items():
                if not vars_dict["price"].get().strip():
                    self.log_upgrade(f"❌ Vui lòng điền Giá tiền mua phôi {ovr}!", "orange")
                    return

        self.show_confirm_popup()

    def execute_start(self):
        self.log_b.delete('1.0', tk.END)
        self.is_running = True
        self.b_s.config(state="disabled", bg="#484f58")
        self.chk_bp.config(state="disabled", fg="#484f58")
        self.chk_auto_buy.config(state="disabled", fg="#484f58")
        self.lock_ui()

        self.lbl_esc_hint.pack(anchor="w", pady=(2, 0))
        f_map = {g: [e.get().strip() for e in r if e.get().strip()] for g, r in self.fodder_rows.items()}

        auto_buy_config = None
        if self.auto_buy_fodder_var.get():
            auto_buy_config = {}
            for ovr, vars_dict in self.ext_buy_data.items():
                auto_buy_config[ovr] = {
                    "price": vars_dict["price"].get().strip(),
                    "qty": vars_dict["qty"].get().strip()
                }

        self.bot = FCOnlineBot(
            self.log_upgrade,
            self.update_current_grade_ui,
            self.on_finished_callback,
            f_map,
            self.target_grade,
            lambda ovr: self.show_alarm(ovr, False),
            lambda ovr, msg=None, custom_msg=None: self.show_alarm(ovr, True, custom_msg or msg),
            self.update_log_line,
            self.bp_protection_var.get(),
            auto_buy_config
        )
        threading.Thread(target=self.bot.run, daemon=True).start()

    def show_summary(self, data):
        if data is None:
            return
        total, successes, fails, fodder = data
        self.log_upgrade("\n=========================", "cyan")
        self.log_upgrade("📊 BẢNG TỔNG KẾT", "gold")
        self.log_upgrade(f"Số lượt đập thẻ: {total}", "white")
        self.log_upgrade("\n📍 Chi tiết:", "green")
        for grade in sorted(set(successes.keys()) | set(fails.keys())):
            s, f = successes[grade], fails[grade]
            self.log_upgrade(f" + Lên +{grade}: {s + f} lần", "white")
            self.log_upgrade(f"   - Thành công: {s}", "success")
            self.log_upgrade(f"   - Thất bại: {f}", "fail")
        self.log_upgrade("\n💎 Phôi tiêu tốn:", "orange")
        if not fodder:
            self.log_upgrade(" Chưa tiêu tốn phôi nào.", "white")
        else:
            for ovr, count in sorted(fodder.items(), key=lambda x: int(x[0])):
                self.log_upgrade(f" + {count}x{ovr}", "white")
        self.log_upgrade("=========================", "cyan")

    def update_current_grade_ui(self, g):
        self.root.after(0, self._update_current_grade_ui_safe, g)

    def _update_current_grade_ui_safe(self, g):
        icon = self.load_icon(g, (25, 25))
        if icon:
            self.lbl_current_icon.config(image=icon)
            self.lbl_current_icon.image = icon