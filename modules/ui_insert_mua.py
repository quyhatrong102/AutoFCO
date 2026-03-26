"""
ui_insert_mua.py - UI cho tab Auto Chèn DS Mua
"""
import threading
import tkinter as tk
from tkinter import scrolledtext

from ui_helpers import add_hover_effect, prevent_typing, configure_log_tags


# ── Kích thước cố định từng cột (px) ────────────────────────────────
_W_SLOT  = 44    # ô slot
_W_MB    = 72    # ô Mua/Bán
_W_DEL   = 20    # ô nút X
_PAD_L   = 8     # padding trái cả dòng
_PAD_MID = 8     # khoảng cách giữa các cột
_ROW_TOT = _PAD_L + _W_SLOT + _PAD_MID + _W_MB + _PAD_MID + _W_DEL

# ── Hằng số cửa sổ ───────────────────────────────────────────────────
_WIN_W      = 320
_WIN_H_BASE = 570
_ROW_H      = 30
_MAX_ROWS   = 14


def _fetch_internet_time():
    import datetime
    try:
        import urllib.request, json
        with urllib.request.urlopen(
            "http://worldtimeapi.org/api/timezone/Asia/Ho_Chi_Minh", timeout=3
        ) as resp:
            data = json.loads(resp.read().decode())
            return datetime.datetime.strptime(data["datetime"][:19], "%Y-%m-%dT%H:%M:%S")
    except Exception:
        pass
    try:
        import urllib.request, email.utils
        with urllib.request.urlopen("http://time.is/", timeout=3) as resp:
            raw = resp.info().get("Date", "")
            if raw:
                return datetime.datetime(*email.utils.parsedate(raw)[:6])
    except Exception:
        pass
    return datetime.datetime.now()


class InsertMuaUI:

    def build_insert_mua_ui(self):
        # ── Nút back ──────────────────────────────────────────────
        self.btn_back_insert_mua = tk.Button(
            self.insert_mua_frame, text="< Menu",
            font=("Consolas", 8, "bold"), bg="#21262d", fg="#c9d1d9",
            bd=0, command=self.show_menu
        )
        self.btn_back_insert_mua.place(x=5, y=5)
        add_hover_effect(self.btn_back_insert_mua, "#30363d", "#21262d")

        # ── Tiêu đề ───────────────────────────────────────────────
        tk.Label(self.insert_mua_frame, text="Auto Chèn (DS Mua)",
                 font=("Consolas", 14, "bold"), fg="#ff79c6", bg="#0d1117"
                 ).pack(pady=(22, 0))
        tk.Label(self.insert_mua_frame, text="By Quybodoivodichvutru",
                 font=("Consolas", 10, "bold"), fg="#58a6ff", bg="#0d1117"
                 ).pack(pady=(2, 6))

        # ── Khung thời gian ───────────────────────────────────────
        time_frame = tk.Frame(self.insert_mua_frame, bg="#161b22",
                              highlightthickness=1, highlightbackground="#30363d")
        time_frame.pack(pady=(4, 0), padx=20, fill="x")

        self.lbl_clock = tk.Label(time_frame, text="--:--:--",
                                  font=("Consolas", 22, "bold"), fg="#f1c40f", bg="#161b22")
        self.lbl_clock.pack(pady=(8, 2))

        self.lbl_chan_le = tk.Label(time_frame, text="",
                                    font=("Consolas", 9), fg="#8b949e", bg="#161b22")
        self.lbl_chan_le.pack(pady=(0, 8))

        # ── Khu vực cấu hình slot ─────────────────────────────────
        self.insert_mua_rows_data = []

        # Wrapper căn giữa — dùng outer frame expand để center
        outer_wrap = tk.Frame(self.insert_mua_frame, bg="#0d1117")
        outer_wrap.pack(pady=(10, 0), fill="x")

        table_wrap = tk.Frame(outer_wrap, bg="#0d1117")
        table_wrap.pack(anchor="center")

        # Header
        hdr = tk.Frame(table_wrap, bg="#0d1117")
        hdr.pack(anchor="w")

        def _hdr_cell(parent, text, w, padx_left=0):
            f = tk.Frame(parent, bg="#0d1117", width=w, height=18)
            f.pack_propagate(False)
            f.pack(side="left", padx=(padx_left, 0))
            tk.Label(f, text=text, font=("Consolas", 8, "bold"),
                     fg="#58a6ff", bg="#0d1117").pack(anchor="center")

        _hdr_cell(hdr, "Slot",      _W_SLOT, padx_left=_PAD_L)
        _hdr_cell(hdr, "Mua / Bán", _W_MB,   padx_left=_PAD_MID)

        # Container rows
        self.insert_rows_container = tk.Frame(table_wrap, bg="#0d1117")
        self.insert_rows_container.pack(anchor="w", pady=(2, 0))

        self._add_insert_row(is_first=True)

        # Nút Thêm
        btn_add = tk.Button(self.insert_mua_frame, text="+ THÊM",
                            font=("Consolas", 9, "bold"), bg="#21262d", fg="#c9d1d9",
                            width=10, bd=0, command=self._add_insert_row_auto)
        btn_add.pack(pady=(6, 2))
        add_hover_effect(btn_add, "#30363d", "#21262d")

        # ── Log output ────────────────────────────────────────────
        log_f = tk.Frame(self.insert_mua_frame, bg="#0d1117")
        log_f.pack(fill="both", expand=True, padx=10, pady=(6, 0))

        self.insert_mua_log_b = scrolledtext.ScrolledText(
            log_f, bg="#161b22", fg="#7ee787",
            font=("Consolas", 10), height=4, bd=0)
        self.insert_mua_log_b.bind("<Key>", prevent_typing)
        self.insert_mua_log_b.pack(fill="both", expand=True)
        configure_log_tags(self.insert_mua_log_b)

        # ── Bottom: START + checkbox ──────────────────────────────
        ctrl_f = tk.Frame(self.insert_mua_frame, bg="#0d1117")
        ctrl_f.pack(side="bottom", fill="x", padx=10, pady=(5, 15))

        btn_row = tk.Frame(ctrl_f, bg="#0d1117")
        btn_row.pack(fill="x")

        self.btn_start_insert_mua = tk.Button(
            btn_row, text="START", bg="#238636", fg="white",
            font=("Consolas", 10, "bold"), width=10, bd=0,
            activebackground="#2ea043", command=self.start_insert)
        self.btn_start_insert_mua.pack(side="left")
        add_hover_effect(self.btn_start_insert_mua, "#2ea043", "#238636")

        right_f = tk.Frame(btn_row, bg="#0d1117")
        right_f.pack(side="right")

        # ESC hint — hàng riêng bên dưới START, căn trái tuyệt đối
        esc_row = tk.Frame(ctrl_f, bg="#0d1117")
        esc_row.pack(fill="x")
        self.lbl_esc_hint_insert_mua = tk.Label(
            esc_row, text="ESC để Dừng",
            font=("Consolas", 7, "bold"), fg="#ff5555", bg="#0d1117")
        self.lbl_esc_hint_insert_mua.pack(side="left", pady=(2, 0))
        self.lbl_esc_hint_insert_mua.pack_forget()

        self.insert_mua_time_limit_var = tk.BooleanVar(value=False)

        # Màu sắc các trạng thái
        _C_ACTIVE  = "#c9d1d9"   # đã tích
        _C_DIMMED  = "#484f58"   # chưa tích
        _C_HOVER   = "#58a6ff"   # hover khi đã tích

        chk = tk.Checkbutton(
            right_f, text="Chỉ chạy trong",
            variable=self.insert_mua_time_limit_var,
            bg="#0d1117", fg=_C_DIMMED, selectcolor="#0d1117",
            activebackground="#0d1117", activeforeground=_C_ACTIVE,
            font=("Consolas", 9), bd=0, highlightthickness=0)
        chk.pack(side="left")

        vcmd2 = (self.root.register(
            lambda P: P == "" or (P.isdigit() and len(P) <= 2)), '%P')
        self.insert_mua_time_limit_entry = tk.Entry(
            right_f, width=3, font=("Consolas", 9),
            bg="#161b22", fg=_C_DIMMED, insertbackground="white",
            bd=1, justify="center", state="disabled",
            validate='key', validatecommand=vcmd2)
        self.insert_mua_time_limit_entry.pack(side="left", padx=3)

        lbl_phut = tk.Label(right_f, text="phút",
                            font=("Consolas", 9), fg=_C_DIMMED, bg="#0d1117")
        lbl_phut.pack(side="left")

        def _on_toggle(*args):
            enabled = self.insert_mua_time_limit_var.get()
            if enabled:
                chk.config(fg=_C_ACTIVE)
                lbl_phut.config(fg=_C_ACTIVE)
                self.insert_mua_time_limit_entry.config(
                    state="normal", bg="#21262d", fg="white")
            else:
                chk.config(fg=_C_DIMMED)
                lbl_phut.config(fg=_C_DIMMED)
                self.insert_mua_time_limit_entry.config(
                    state="disabled", bg="#161b22", fg=_C_DIMMED)

        self.insert_mua_time_limit_var.trace_add("write", _on_toggle)

        # Hover đồng bộ: chỉ sáng khi đã tích
        def _hover_enter(e):
            if self.insert_mua_time_limit_var.get():
                chk.config(fg=_C_HOVER)
                lbl_phut.config(fg=_C_HOVER)
        def _hover_leave(e):
            if self.insert_mua_time_limit_var.get():
                chk.config(fg=_C_ACTIVE)
                lbl_phut.config(fg=_C_ACTIVE)
        for w in (right_f, chk, lbl_phut):
            w.bind("<Enter>", _hover_enter)
            w.bind("<Leave>", _hover_leave)

        # ── Đồng hồ ───────────────────────────────────────────────
        self._insert_clock_running = False
        self._insert_time_offset   = None
        self._insert_log_queue     = []   # queue log de tranh flood main thread
        self._fetch_time_offset_async()
        self.root.after(100, self._drain_insert_log)  # bat dau drain loop

    # ===================== DÒNG SLOT =====================

    def _add_insert_mua_row(self, is_first=False, slot_num=None, mua_ban_init="Mua"):
        if len(self.insert_mua_rows_data) >= _MAX_ROWS:
            return

        row_f = tk.Frame(self.insert_rows_container, bg="#0d1117")
        row_f.pack(anchor="w", pady=2)

        # ── Slot: button mở custom dropdown ───────────────────────
        # Tính slot nhỏ nhất chưa có nếu không truyền vào
        if slot_num is None:
            used = {int(r["slot"].get()) for r in self.insert_mua_rows_data}
            slot_num = next((i for i in range(1, _MAX_ROWS + 1) if i not in used), 1)
        slot_var = tk.StringVar(value=str(slot_num))

        slot_f = tk.Frame(row_f, bg="#0d1117", width=_W_SLOT, height=22)
        slot_f.pack_propagate(False)
        slot_f.pack(side="left", padx=(_PAD_L, 0))

        slot_btn = tk.Button(slot_f, textvariable=slot_var,
                             bg="#21262d", fg="white", font=("Consolas", 9),
                             bd=1, relief="flat", anchor="center")
        slot_btn.pack(fill="both", expand=True)
        add_hover_effect(slot_btn, "#30363d", "#21262d")

        def _open_slot_popup(b=slot_btn, v=slot_var):
            """Custom dropdown: mỗi số là 1 Button riêng, hover effect, căn giữa."""
            pop = tk.Toplevel(self.root)
            pop.overrideredirect(True)
            pop.attributes("-topmost", True)
            pop.configure(bg="#30363d", highlightthickness=0)

            bx  = b.winfo_rootx()
            by  = b.winfo_rooty() + b.winfo_height() - 1
            bw  = b.winfo_width()
            bh  = 22   # chiều cao mỗi item
            pop.geometry(f"{bw}x{14 * bh}+{bx}+{by}")

            def _pick(val, p=pop, sv=v):
                sv.set(str(val))
                p.destroy()

            for i in range(1, _MAX_ROWS + 1):
                btn = tk.Button(
                    pop, text=str(i),
                    font=("Consolas", 9), bg="#21262d", fg="white",
                    bd=0, relief="flat", anchor="center",
                    activebackground="#388bfd", activeforeground="white",
                    command=lambda val=i: _pick(val)
                )
                btn.place(x=0, y=(i - 1) * bh, width=bw, height=bh)
                add_hover_effect(btn, "#30363d", "#21262d")

            # Đóng khi click ra ngoài
            pop.bind("<FocusOut>", lambda e: pop.destroy())
            pop.after(50, pop.focus_set)

        slot_btn.config(command=_open_slot_popup)

        # ── Mua / Bán toggle ──────────────────────────────────────
        mua_ban_var = tk.StringVar(value=mua_ban_init)

        mb_f = tk.Frame(row_f, bg="#21262d",
                        highlightthickness=1, highlightbackground="#484f58",
                        width=_W_MB, height=22)
        mb_f.pack_propagate(False)
        mb_f.pack(side="left", padx=(_PAD_MID, 0))

        C_MUA_ON = "#da3633"; C_MUA_OFF = "#21262d"
        C_BAN_ON = "#1f6feb"; C_BAN_OFF = "#21262d"

        _init_mua = (mua_ban_init == "Mua")
        btn_mua = tk.Button(mb_f, text="Mua", font=("Consolas", 8, "bold"),
                             bg=C_MUA_ON if _init_mua else C_MUA_OFF,
                             fg="white" if _init_mua else "#8b949e", bd=0, relief="flat")
        btn_ban = tk.Button(mb_f, text="Bán", font=("Consolas", 8, "bold"),
                             bg=C_BAN_OFF if _init_mua else C_BAN_ON,
                             fg="#8b949e" if _init_mua else "white", bd=0, relief="flat")
        btn_mua.place(relx=0,   rely=0, relwidth=0.5, relheight=1)
        btn_ban.place(relx=0.5, rely=0, relwidth=0.5, relheight=1)

        def _sel_mua(bm=btn_mua, bb=btn_ban, v=mua_ban_var):
            v.set("Mua"); bm.config(bg=C_MUA_ON, fg="white"); bb.config(bg=C_BAN_OFF, fg="#8b949e")

        def _sel_ban(bm=btn_mua, bb=btn_ban, v=mua_ban_var):
            v.set("Bán"); bm.config(bg=C_MUA_OFF, fg="#8b949e"); bb.config(bg=C_BAN_ON, fg="white")

        btn_mua.config(command=_sel_mua)
        btn_ban.config(command=_sel_ban)

        # ── Nút X ─────────────────────────────────────────────────
        pos_var = tk.StringVar(value="")   # giữ lại để tương thích bot
        row_data = {"frame": row_f, "slot": slot_var,
                    "mua_ban": mua_ban_var, "pos": pos_var}

        del_f = tk.Frame(row_f, bg="#0d1117", width=_W_DEL, height=22)
        del_f.pack_propagate(False)
        del_f.pack(side="left", padx=(_PAD_MID, 0))

        if not is_first:
            btn_del = tk.Button(del_f, text="X", font=("Consolas", 9, "bold"),
                                bg="#da3633", fg="white", bd=0,
                                command=lambda rd=row_data: self._remove_insert_row(rd),
                                takefocus=0)
            btn_del.pack(fill="both", expand=True)
            add_hover_effect(btn_del, "#f85149", "#da3633")

        self.insert_mua_rows_data.append(row_data)
        if not is_first:
            self._update_insert_mua_window_height()

    def _add_insert_mua_row_auto(self):
        """Bấm + THÊM: thêm row với slot nhỏ nhất chưa dùng, mặc định Mua."""
        if len(self.insert_mua_rows_data) >= _MAX_ROWS:
            return
        used = {int(r["slot"].get()) for r in self.insert_mua_rows_data}
        next_slot = next((i for i in range(1, _MAX_ROWS + 1) if i not in used), 1)
        self._add_insert_row(is_first=False, slot_num=next_slot, mua_ban_init="Mua")
    def _remove_insert_mua_row(self, row_data):
        if row_data in self.insert_mua_rows_data:
            row_data["frame"].destroy()
            self.insert_mua_rows_data.remove(row_data)
            self._update_insert_mua_window_height()

    def _update_insert_mua_window_height(self):
        n = len(self.insert_mua_rows_data)
        h = _WIN_H_BASE + max(0, n - 1) * _ROW_H
        self.root.geometry(f"{_WIN_W}x{h}+{self.sw - _WIN_W}+0")

    # ===================== ĐỒNG HỒ =====================

    def _fetch_time_offset_async(self):
        def _worker():
            import datetime
            try:
                inet = _fetch_internet_time()
                self._insert_time_offset = inet - datetime.datetime.now()
            except Exception:
                self._insert_time_offset = None
            self.root.after(0, self._start_insert_clock)
        threading.Thread(target=_worker, daemon=True).start()

    def _start_insert_clock(self):
        self._insert_clock_running = True
        self._tick_insert_clock()

    def _tick_insert_clock(self):
        if not self._insert_clock_running:
            return
        if not self.insert_mua_frame.winfo_ismapped():
            self.root.after(500, self._tick_insert_clock)
            return
        import datetime
        now = datetime.datetime.now()
        if self._insert_time_offset is not None:
            now = now + self._insert_time_offset
        h, m, s = now.hour, now.minute, now.second
        self.lbl_clock.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        chan_le = "Chẵn" if h % 2 == 0 else "Lẻ"
        self.lbl_chan_le.config(text=f"{chan_le}  {h}",
                                fg="#50fa7b" if h % 2 == 0 else "#ff79c6")
        self.root.after(1000, self._tick_insert_clock)

    # ===================== LOG =====================

    def log_insert_mua(self, msg, tag=None):
        self._insert_log_queue.append((msg, tag))

    def _drain_insert_log(self):
        """Drain log queue moi 100ms thay vi moi lan bot log → tranh flood main thread."""
        if self._insert_log_queue:
            # Lay toi da 20 dong moi lan drain de tranh block
            batch = self._insert_log_queue[:20]
            del self._insert_log_queue[:20]
            for msg, tag in batch:
                self._insert_log(self.insert_mua_log_b, msg, tag)
        self.root.after(100, self._drain_insert_log)

    # ===================== START / STOP =====================

    def start_insert_mua(self):
        if self.is_running:
            return
        if not self.insert_mua_rows_data:
            self.log_insert("❌ Chưa có dòng slot nào.", "orange")
            return

        # Thu thập config từ UI
        slot_configs = []
        for row in self.insert_mua_rows_data:
            slot_configs.append({
                "slot":    row["slot"].get(),
                "mua_ban": row["mua_ban"].get(),
                "pos_var": row["pos"],
            })

        # Reset ô vị trí
        for row in self.insert_mua_rows_data:
            row["pos"].set("")

        self.insert_mua_log_b.delete("1.0", "end")
        self.is_running = True
        self.btn_start_insert_mua.config(state="disabled", bg="#484f58")
        self.lock_ui()
        self.lbl_esc_hint_insert_mua.pack(side="left", pady=(2, 0))

        from bot import FCOnlineBot
        import threading

        self.bot = FCOnlineBot(
            self.log_insert,
            lambda *a: None,          # ui_update (unused)
            self.on_finished_callback,
            {}, None,
            lambda ovr: None,         # error alarm (unused)
            lambda *a, **kw: None,    # success alarm (unused)
            lambda *a: None,          # log_update (unused)
            False
        )
        # Inject root ref vào bot để gọi root.after cho pos_var
        self.bot.root = self.root

        # Lấy time_limit nếu checkbox được tích
        time_limit = None
        if self.insert_mua_time_limit_var.get():
            try:
                time_limit = float(self.insert_mua_time_limit_entry.get())
            except ValueError:
                time_limit = None

        threading.Thread(
            target=self.bot.run_insert_mua,
            args=(slot_configs,),
            kwargs={"time_limit_minutes": time_limit},
            daemon=True
        ).start()

    def stop_insert(self):
        pass
