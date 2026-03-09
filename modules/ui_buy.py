"""
ui_buy.py - UI cho tab Auto Mua Phôi
"""
import threading
import tkinter as tk
from tkinter import scrolledtext

from ui_helpers import add_hover_effect, prevent_typing, configure_log_tags
from bot import FCOnlineBot

# Hằng số kích thước cửa sổ Auto Mua Phôi
_BUY_W      = 340
_BUY_H_BASE = 600   # chiều cao khi chỉ có 1 dòng
_BUY_ROW_H  = 32    # mỗi dòng slot thêm bao nhiêu px
_BUY_MAX    = 11    # số dòng tối đa


class BuyFodderUI:
    """
    Mixin cung cấp toàn bộ UI và logic điều khiển cho tab Auto Mua Phôi.
    Kế thừa bởi App.
    """

    def build_buy_fodder_ui(self):
        self.btn_back_buy = tk.Button(
            self.buy_fodder_frame, text="< Menu",
            font=("Consolas", 8, "bold"), bg="#21262d", fg="#c9d1d9",
            bd=0, command=self.show_menu
        )
        self.btn_back_buy.place(x=5, y=5)
        add_hover_effect(self.btn_back_buy, "#30363d", "#21262d")

        tk.Label(
            self.buy_fodder_frame, text="Auto Mua Phôi",
            font=("Consolas", 14, "bold"), fg="#ff79c6", bg="#0d1117"
        ).pack(pady=(25, 10))

        table_container = tk.Frame(self.buy_fodder_frame, bg="#0d1117")
        table_container.pack(anchor="center", pady=5)

        header_f = tk.Frame(table_container, bg="#0d1117")
        header_f.pack(fill="x", pady=(0, 5))

        def make_header(parent, text, w):
            f = tk.Frame(parent, bg="#0d1117", width=w, height=20)
            f.pack_propagate(False)
            f.pack(side="left", padx=2)
            tk.Label(f, text=text, font=("Consolas", 9, "bold"), fg="#58a6ff", bg="#0d1117").pack(anchor="center")

        make_header(header_f, "OVR", 45)
        make_header(header_f, "Giá tiền (B)", 100)
        make_header(header_f, "Số lượng", 85)

        self.buy_rows_container = tk.Frame(table_container, bg="#0d1117")
        self.buy_rows_container.pack(fill="x")

        self.add_buy_row(is_first=True)

        btn_add_row = tk.Button(
            self.buy_fodder_frame, text="+ THÊM",
            font=("Consolas", 9, "bold"), bg="#21262d", fg="#c9d1d9",
            width=12, bd=0, command=self.add_buy_row
        )
        btn_add_row.pack(pady=(10, 10))
        add_hover_effect(btn_add_row, "#30363d", "#21262d")

        log_f = tk.Frame(self.buy_fodder_frame, bg="#0d1117")
        log_f.pack(fill="both", expand=True, padx=15, pady=5)

        self.buy_log_b = scrolledtext.ScrolledText(
            log_f, bg="#161b22", fg="#7ee787",
            font=("Consolas", 10), height=8, bd=0
        )
        self.buy_log_b.bind("<Key>", prevent_typing)
        self.buy_log_b.pack(fill="both", expand=True)
        configure_log_tags(self.buy_log_b)

        ctrl_f = tk.Frame(self.buy_fodder_frame, bg="#0d1117")
        ctrl_f.pack(side="bottom", fill="x", pady=(5, 15))

        self.btn_start_buy = tk.Button(
            ctrl_f, text="START", bg="#238636", fg="white",
            font=("Consolas", 10, "bold"), width=15, bd=0,
            activebackground="#2ea043", command=self.start_buy_fodder
        )
        self.btn_start_buy.pack(anchor="center")
        add_hover_effect(self.btn_start_buy, "#2ea043", "#238636")

        self.lbl_esc_hint_buy = tk.Label(
            ctrl_f, text="ESC để Dừng",
            font=("Consolas", 7, "bold"), fg="#ff5555", bg="#0d1117"
        )
        self.lbl_esc_hint_buy.pack(anchor="center", pady=(2, 0))
        self.lbl_esc_hint_buy.pack_forget()

    def add_buy_row(self, is_first=False):
        if len(self.buy_fodder_rows_data) >= _BUY_MAX:
            return

        vcmd_short = (self.root.register(self.validate_input), '%P')
        vcmd_price = (self.root.register(self.validate_price), '%P')

        row_f = tk.Frame(self.buy_rows_container, bg="#0d1117")
        row_f.pack(fill="x", pady=3)

        f_ovr = tk.Frame(row_f, bg="#0d1117", width=45, height=22)
        f_ovr.pack_propagate(False)
        f_ovr.pack(side="left", padx=2)
        ovr_var = tk.StringVar()
        ent_ovr = tk.Entry(
            f_ovr, textvariable=ovr_var, bg="#21262d", fg="white",
            font=("Consolas", 9), bd=1, justify='center',
            insertbackground="white", validate='key', validatecommand=vcmd_short
        )
        ent_ovr.pack(fill="both", expand=True)

        f_price = tk.Frame(row_f, bg="#0d1117", width=100, height=22)
        f_price.pack_propagate(False)
        f_price.pack(side="left", padx=2)
        price_var = tk.StringVar()
        ent_price = tk.Entry(
            f_price, textvariable=price_var, bg="#21262d", fg="white",
            font=("Consolas", 9), bd=1, justify='center',
            insertbackground="white", validate='key', validatecommand=vcmd_price
        )
        ent_price.pack(fill="both", expand=True)

        f_qty = tk.Frame(row_f, bg="#0d1117", width=85, height=22)
        f_qty.pack_propagate(False)
        f_qty.pack(side="left", padx=2)

        qty_var = tk.StringVar(value="1")

        def dec(var=qty_var):
            try:
                v = int(var.get())
                if v > 1:
                    var.set(str(v - 1))
            except:
                var.set("1")

        def inc(var=qty_var):
            try:
                v = int(var.get())
                if v < 999:
                    var.set(str(v + 1))
            except:
                var.set("1")

        btn_minus = tk.Button(
            f_qty, text="-", font=("Consolas", 9, "bold"),
            bg="#21262d", fg="white", bd=0, width=2, command=dec, takefocus=0
        )
        btn_minus.pack(side="left")
        add_hover_effect(btn_minus, "#30363d", "#21262d")

        ent_qty = tk.Entry(
            f_qty, textvariable=qty_var, bg="#21262d", fg="white",
            font=("Consolas", 9), bd=1, width=3, justify='center',
            insertbackground="white", validate='key', validatecommand=vcmd_short
        )
        ent_qty.pack(side="left", padx=2, fill="both", expand=True)

        btn_plus = tk.Button(
            f_qty, text="+", font=("Consolas", 9, "bold"),
            bg="#21262d", fg="white", bd=0, width=2, command=inc, takefocus=0
        )
        btn_plus.pack(side="left")
        add_hover_effect(btn_plus, "#30363d", "#21262d")

        row_data = {"frame": row_f, "ovr": ovr_var, "qty": qty_var, "price": price_var}

        f_del = tk.Frame(row_f, bg="#0d1117", width=20, height=22)
        f_del.pack_propagate(False)
        f_del.pack(side="left", padx=(2, 0))
        if not is_first:
            btn_del = tk.Button(
                f_del, text="X", font=("Consolas", 9, "bold"),
                bg="#da3633", fg="white", bd=0,
                command=lambda: self.remove_buy_row(row_data), takefocus=0
            )
            btn_del.pack(fill="both", expand=True)
            add_hover_effect(btn_del, "#f85149", "#da3633")

        self.buy_fodder_rows_data.append(row_data)
        if not is_first:
            self._update_buy_window_height()

    def remove_buy_row(self, row_data):
        if row_data in self.buy_fodder_rows_data:
            row_data["frame"].destroy()
            self.buy_fodder_rows_data.remove(row_data)
            self._update_buy_window_height()

    def _update_buy_window_height(self):
        """Kéo dài / thu ngắn cửa sổ theo số dòng."""
        n = len(self.buy_fodder_rows_data)
        h = _BUY_H_BASE + max(0, n - 1) * _BUY_ROW_H
        self.root.geometry(f"{_BUY_W}x{h}+{self.sw - _BUY_W}+0")

    def start_buy_fodder(self):
        raw_data = []
        for row in list(self.buy_fodder_rows_data):
            ovr = row["ovr"].get().strip()
            price = row["price"].get().strip()
            qty = row["qty"].get().strip()

            if not ovr or not price or not qty:
                self.remove_buy_row(row)
            else:
                raw_data.append({"ovr": int(ovr), "price": int(price), "qty": int(qty)})

        if not raw_data:
            self.log_buy("❌ Không có dữ liệu hợp lệ để chạy.", "orange")
            return

        # Gộp các dòng cùng OVR
        merged_dict = {}
        for item in raw_data:
            ovr = item["ovr"]
            if ovr in merged_dict:
                merged_dict[ovr]["qty"] += item["qty"]
                merged_dict[ovr]["price"] = min(merged_dict[ovr]["price"], item["price"])
            else:
                merged_dict[ovr] = {"ovr": ovr, "price": item["price"], "qty": item["qty"]}

        buy_data = list(merged_dict.values())

        # Cập nhật lại UI
        for row in list(self.buy_fodder_rows_data):
            self.remove_buy_row(row)
        for idx, item in enumerate(buy_data):
            self.add_buy_row(is_first=(idx == 0))
            last_row = self.buy_fodder_rows_data[-1]
            last_row["ovr"].set(str(item["ovr"]))
            last_row["price"].set(str(item["price"]))
            last_row["qty"].set(str(item["qty"]))

        self.buy_log_b.delete('1.0', tk.END)
        self.is_running = True
        self.btn_start_buy.config(state="disabled", bg="#484f58")
        self.lock_ui()
        self.lbl_esc_hint_buy.pack(anchor="center", pady=(2, 0))

        self.bot = FCOnlineBot(
            self.log_buy,
            self.update_current_grade_ui,
            self.on_buy_finished_callback,
            {}, None,
            lambda ovr: self.show_alarm(ovr, False),
            lambda ovr, msg=None, custom_msg=None: self.show_alarm(ovr, True, custom_msg or msg),
            self.update_log_line,
            False
        )
        threading.Thread(target=self.bot.run_buy_fodder, args=(buy_data,), daemon=True).start()

    def on_buy_finished_callback(self, summary_data=None):
        self.root.after(0, self._on_finished_safe, summary_data)

    def log_buy(self, msg, tag=None, return_pos=False):
        pos = None
        if return_pos:
            pos_holder = [None]

            def _insert_and_get_pos():
                pos_holder[0] = self.buy_log_b.index("end-1c")
                self.buy_log_b.insert("end", msg + "\n", tag)
                self.buy_log_b.see("end")

            self.root.after(0, _insert_and_get_pos)
            return pos_holder
        else:
            self.root.after(0, lambda: self._insert_log(self.buy_log_b, msg, tag))
            return None
