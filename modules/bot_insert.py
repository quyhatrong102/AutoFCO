"""
bot_insert.py - Logic Auto Chen (DS của bạn)

Flow:
1. arrange_game, tim anchor_trang_thai, OCR cot Trang thai
2. Voi moi slot: hover → click dang_ki_lai → ghi nho btn_coords
3. Doc gia (OCR) tu max.png/min.png sang phai
4. Click btn_huy
5. Loop: hover → click dang_ki_lai nhanh → doc gia → click huy
   → den khi gia thay doi
6. Khi gia thay doi: chup screenshot → click chen_max/chen_min
7. Toan bo loop chi chay tu giay :50 den giay :25 phut sau
8. Nhieu slot: check lan luot, slot xong roi skip
"""
import os
import re
import time
import datetime
import threading
import cv2
import numpy as np
import pyautogui
import pytesseract
from PIL import ImageGrab

from config import SAMPLE_DIR

_HOVER_RETRIES = 5
_MAX_ROWS      = 11

# Thu muc luu proof screenshot
_PROOF_DIR = os.path.join(os.path.dirname(SAMPLE_DIR), "chen_proof")


def _ensure_proof_dir():
    os.makedirs(_PROOF_DIR, exist_ok=True)


class InsertMixin:

    # ─────────────────── HELPERS ───────────────────

    def _find_scored(self, template_name, region, threshold=0.65):
        p = os.path.join(SAMPLE_DIR, template_name)
        if not os.path.exists(p):
            self.log(f"   Khong co file: {template_name}", "orange")
            return None
        tmpl   = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        screen = np.array(ImageGrab.grab(bbox=region))
        gray   = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        res    = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        th, tw = tmpl.shape
        if max_val >= threshold:
            return (region[0] + max_loc[0] + tw // 2,
                    region[1] + max_loc[1] + th // 2)
        return None

    def _find_silent(self, template_name, region, threshold=0.72):
        """Tim template khong log."""
        p = os.path.join(SAMPLE_DIR, template_name)
        if not os.path.exists(p):
            return None
        tmpl   = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        screen = np.array(ImageGrab.grab(bbox=region))
        gray   = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        res    = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        th, tw = tmpl.shape
        if max_val >= threshold:
            return (region[0] + max_loc[0] + tw // 2,
                    region[1] + max_loc[1] + th // 2)
        return None

    def _wait_for(self, template_name, region=None, threshold=0.72, timeout=5.0):
        """
        Poll moi 0.1s cho den khi tim thay template hoac het timeout.
        Tra ve coords hoac None.
        """
        region = region or self.rect
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.running:
                return None
            coords = self._find_silent(template_name, region, threshold)
            if coords:
                return coords
            time.sleep(0.1)
        return None

    def _scan_status_rows(self, scan_region):
        """
        OCR cot Trang thai, tra ve list of dict:
          { row_idx, status("Mua"|"Ban"), cx, cy }
        """
        rx1, ry1, rx2, ry2 = scan_region
        cx_center = (rx1 + rx2) // 2

        img = ImageGrab.grab(bbox=scan_region)
        iw, ih = img.size
        img_big = img.resize((iw * 3, ih * 3))
        arr = np.array(img_big.convert("L"))
        _, bw = cv2.threshold(arr, 100, 255, cv2.THRESH_BINARY)
        from PIL import Image as PILImage
        pil = PILImage.fromarray(bw)

        data = pytesseract.image_to_data(
            pil, lang="vie", config="--psm 6",
            output_type=pytesseract.Output.DICT
        )

        line_map = {}
        for i, text in enumerate(data["text"]):
            if not text.strip():
                continue
            key = (data["block_num"][i], data["line_num"][i])
            line_map.setdefault(key, []).append(
                (data["top"][i], data["height"][i], text.strip().lower())
            )

        sorted_lines = sorted(line_map.items(), key=lambda x: x[1][0][0])

        rows = []
        for _, words in sorted_lines:
            full = " ".join(w for _, _, w in words)
            if "mua" in full:
                status = "Mua"
            elif "bán" in full or "ban" in full:
                status = "Ban"
            else:
                continue

            top_scaled = words[0][0]
            h_scaled   = words[0][1]
            row_y_rel  = (top_scaled + h_scaled // 2) // 3
            cy_abs     = ry1 + row_y_rel

            row_idx = len(rows) + 1
            rows.append({
                "row_idx": row_idx,
                "status":  status,
                "cx":      cx_center,
                "cy":      cy_abs,
            })
    
        return rows

    def _ocr_price(self, anchor_tmpl, rect):
        """
        Tim anchor (max.png hoac min.png) o nua phai man hinh,
        OCR tu diem do sang phai de lay gia.
        Doc 3 lan tren cung 1 anh, lay ket qua xuat hien nhieu nhat.
        Tra ve (digits_str, click_x, click_y) hoac (None, None, None).
        """
        x1, y1, x2, y2 = rect
        w = x2 - x1

        right_half = (x1 + w // 2, y1, x2, y2)
        anchor = self._find_silent(anchor_tmpl, right_half, threshold=0.65)
        if not anchor:
            return None, None, None

        ax, ay = anchor

        # Vung doc gia: bat dau sau anchor ~30px, ±18px theo Y
        price_region = (ax + 30, ay - 18, x2 - 5, ay + 18)
        img = ImageGrab.grab(bbox=price_region)

        from PIL import Image as PILImage, ImageEnhance
        # Crop bo 20px ben phai (o den goc phai bi OCR doc nham)
        img_crop = img.crop((0, 0, img.width - 20, img.height))
        iw, ih = img_crop.size
        img_big = img_crop.resize((iw * 4, ih * 4), PILImage.LANCZOS)
        gray = ImageEnhance.Contrast(img_big).enhance(3.0).convert("L")
        arr  = np.array(gray)
        # Nguong cung 150: nen xam sang → trang, chu den → den
        _, bw = cv2.threshold(arr, 150, 255, cv2.THRESH_BINARY)
        # Padding trang 6px de Tesseract khong bi nham canh
        bw = cv2.copyMakeBorder(bw, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=255)
        pil = PILImage.fromarray(bw)

        # OCR 1 lan - anh da xu ly ro nen doc chinh xac
        cfg = "--psm 7 -c tessedit_char_whitelist=0123456789,B"
        text = pytesseract.image_to_string(pil, config=cfg).strip()
        text_clean = re.sub(r"[Bb]\s*$", "", text).strip()
        digits = re.sub(r"[^\d]", "", text_clean)
        return (digits if digits else None), ax, ay


    def _get_clock_now(self):
        """Lay thoi gian hien tai tu dong ho insert (co offset internet)."""
        import datetime as dt
        now = dt.datetime.now()
        if getattr(self, "_insert_time_offset", None) is not None:
            now = now + self._insert_time_offset
        return now

    def _in_active_window(self, now=None):
        """
        Tra ve True neu dang trong cua so active (:50 den :25 phut sau).
        :50 <= giay < 60  HOAC  0 <= giay <= 25
        """
        if now is None:
            now = self._get_clock_now()
        s = now.second
        return s >= 50 or s <= 25

    def _seconds_until_active(self):
        """So giay cho den khi cua so :50 mo ra."""
        now = self._get_clock_now()
        s = now.second
        if s >= 50 or s <= 25:
            return 0
        return 50 - s   # so giay con lai den :50

    # ─────────────────── HOVER + CLICK DKL ───────────────────

    def _hover_and_click_dkl(self, cx, cy, fast=False):
        """
        Di chuot vao (cx, cy), cho btn_dang_ki_lai hien thi DUNG DONG (cy ± 40px) roi click.
        fast=True: di chuot nhanh hon.
        Tra ve toa do btn_dang_ki_lai hoac None.
        """
        dur = 0.05 if fast else 0.25
        pyautogui.moveTo(cx, cy, duration=dur)

        # Poll: tim btn_dang_ki_lai nhung chi chap nhan neu Y gan cy (tranh nham dong khac)
        deadline = time.time() + 3.0
        while time.time() < deadline:
            if not self.running:
                return None
            btn = self._find_silent("btn_dang_ki_lai.png", self.rect, threshold=0.72)
            if btn:
                bx, by = btn
                if abs(by - cy) <= 40:   # dung dong can hover
                    pyautogui.click(btn)
                    return btn
                # btn hien nhung sai dong → di chuot lai vao dung vi tri
                pyautogui.moveTo(cx, cy, duration=0.05)
            time.sleep(0.1)
        return None

    # ─────────────────── RUN INSERT ───────────────────

    def run_insert(self, slot_configs, time_limit_minutes=None):
        self.running = True
        _ensure_proof_dir()

        # 1. Resize game
        if not self.arrange_game():
            self.log("❌ Khong tim thay cua so FC ONLINE!", "fail")
            self.running = False
            self.on_finished()
            return

        x1, y1, x2, y2 = self.rect
        w, h = x2 - x1, y2 - y1

        self.log("🔍 Đang tìm DS...", "white")

        # 2. Tim anchor_trang_thai
        anchor_coords = None
        for attempt in range(5):
            if not self.running:
                break
            anchor_coords = self._find_scored(
                "anchor_trang_thai.png", self.rect, threshold=0.65
            )
            if anchor_coords:
                break
            time.sleep(0.5)

        if not anchor_coords:
            self.log("❌ Khong tim thay anchor Trang thai.", "fail")
            self.running = False
            self.on_finished()
            return

        anchor_x, anchor_y = anchor_coords

        # 3. OCR cot Trang thai
        col_x1 = anchor_x - 120
        col_x2 = anchor_x + 120
        scan_region = (col_x1, anchor_y + 5, col_x2, y2 - int(h * 0.08))
        ds_rows = self._scan_status_rows(scan_region)

        if not ds_rows:
            self.log("❌ Khong tim thay dong nao.", "fail")
            self.running = False
            self.on_finished()
            return

        self.log(f"✅ Tìm được {len(ds_rows)} dòng. Đang quét giá...", "white")

        # ── Chuẩn bị trạng thái từng slot ──────────────────────
        # slot_state: dict slot_num → {
        #   "cfg": cfg,
        #   "ds_row": matched ds_row,
        #   "done": bool,
        #   "dkl_coords": (cx, cy) btn_dang_ki_lai da biet,
        #   "init_price": str gia goc,
        #   "anchor_tmpl": "max.png" | "min.png",
        #   "chen_tmpl":   "chen_max.png" | "chen_min.png",
        #   "proof_label": "max" | "min",
        # }
        slot_states = {}

        for cfg in slot_configs:
            slot_num = int(cfg["slot"])
            mua_ban  = cfg["mua_ban"]
            matched  = next((r for r in ds_rows if r["row_idx"] == slot_num), None)

            if not matched:
                self.log(f"⚠️ Slot {slot_num}: khong co trong DS", "orange")
                continue

            anchor_tmpl = "max.png"  if mua_ban == "Mua" else "min.png"
            chen_tmpl   = "chen_max.png" if mua_ban == "Mua" else "chen_min.png"
            proof_label = "max"      if mua_ban == "Mua" else "min"

            slot_states[slot_num] = {
                "cfg":          cfg,
                "ds_row":       matched,
                "done":         False,
                "dkl_coords":   None,
                "init_price":   None,
                "price_anchor": None,   # (ax, ay) toa do anchor gia de click
                "price_click":  None,   # toa do click dong gia (ax+60, ay) - luu tu lan dau
                "chen_coords":  None,   # toa do chen_max/chen_min - luu tu lan dau
                "anchor_tmpl":  anchor_tmpl,
                "chen_tmpl":    chen_tmpl,
                "proof_label":  proof_label,
            }

        if not slot_states:
            self.log("❌ Khong co slot hop le nao.", "fail")
            self.running = False
            self.on_finished()
            return

        # ── Buoc dau: hover, click dang_ki_lai, doc gia goc, click huy ──
        # Thuc hien LAN DAU cho tat ca slot (ghi nho btn_dang_ki_lai coords)
        for slot_num, st in slot_states.items():
            if not self.running:
                break

            cx = st["ds_row"]["cx"]
            cy = st["ds_row"]["cy"]
            mua_ban = st["cfg"]["mua_ban"]

            btn = self._hover_and_click_dkl(cx, cy, fast=False)
            if not btn:
                st["done"] = True
                continue

            st["dkl_coords"] = btn   # ghi nho toa do btn_dang_ki_lai thuc te

            # Cho popup mo hoan toan (max.png/min.png hien ra) roi moi OCR
            x1r, y1r, x2r, y2r = self.rect
            right_half = (x1r + (x2r - x1r) // 2, y1r, x2r, y2r)
            self._wait_for(st["anchor_tmpl"], right_half, threshold=0.65, timeout=5.0)

            # Doc gia goc
            price, _ax, _ay = self._ocr_price(st["anchor_tmpl"], self.rect)
            st["init_price"]   = price
            st["price_anchor"] = (_ax, _ay)
            if _ax:
                st["price_click"] = (_ax + 60, _ay)   # toa do click dong gia

            # Luu toa do chen_tmpl lan dau (de dung lai trong loop)
            chen_first = self._wait_for(st["chen_tmpl"], self.rect, threshold=0.72, timeout=3.0)
            if chen_first:
                st["chen_coords"] = chen_first

            self.log(f"📌 Slot {slot_num} ({mua_ban}): giá gốc {price}B", "white")

            # Click huy
            btn_huy = self._wait_for("btn_huy.png", self.rect, threshold=0.72, timeout=3.0)
            if btn_huy:
                pyautogui.click(btn_huy)
                # Cho popup dong lai (btn_huy bien mat)
                deadline = time.time() + 2.0
                while time.time() < deadline:
                    if not self._find_silent("btn_huy.png", self.rect, 0.72):
                        break
                    time.sleep(0.1)

        # ── Cho den cua so active (:50) ────────────────────────
        s_now = self._get_clock_now().second
        if 26 <= s_now <= 49:
            self.log("⏳ Chờ đến giây :50...", "white")
            while self.running:
                s = self._get_clock_now().second
                if s >= 50:
                    break
                time.sleep(0.2)
        elif s_now > 25 and s_now < 50:
            pass  # fallback (khong can)

        # ── LOOP chinh ──────────────────────────────────────────

        # Deadline tong (neu co gioi han thoi gian)
        total_deadline = (time.time() + time_limit_minutes * 60) if time_limit_minutes else None

        while self.running:
            # Kiem tra gioi han thoi gian tong
            if total_deadline and time.time() >= total_deadline:
                self.log("⏹ Hết thời gian — dừng.", "orange")
                break

            now = self._get_clock_now()

            # Kiem tra con trong cua so active khong
            if not self._in_active_window(now):
                self.log("⏸ Qua :25 — chờ đến :50...", "orange")
                # Cho den giay :50 (khong phai :00)
                while self.running:
                    s = self._get_clock_now().second
                    if s >= 50:
                        break
                    time.sleep(0.2)
                if not self.running:
                    break
                self.log("▶ Bắt đầu lại...", "white")
                continue

            # Tat ca slot da xong?
            active_slots = [s for s in slot_states.values() if not s["done"]]
            if not active_slots:
                    break

            for st in active_slots:
                if not self.running:
                    break

                slot_num = int(st["cfg"]["slot"])
                bx, by   = st["dkl_coords"]   # toa do btn_dkl da biet

                # Di chuot thang vao vi tri btn cu, doi hien roi click
                btn = self._hover_and_click_dkl(bx, by, fast=True)
                if not btn:
                    continue

                # Cho anchor gia hien ra roi moi OCR
                x1r, y1r, x2r, y2r = self.rect
                right_half = (x1r + (x2r - x1r) // 2, y1r, x2r, y2r)
                self._wait_for(st["anchor_tmpl"], right_half, threshold=0.65, timeout=4.0)

                # Doc gia hien tai
                price_now, ax_now, ay_now = self._ocr_price(st["anchor_tmpl"], self.rect)
                if ax_now:
                    st["price_anchor"] = (ax_now, ay_now)
                    st["price_click"]  = (ax_now + 60, ay_now)
                # Cap nhat toa do chen_tmpl neu tim thay
                chen_found = self._find_silent(st["chen_tmpl"], self.rect, threshold=0.72)
                if chen_found:
                    st["chen_coords"] = chen_found

                # Kiem tra gia da thay doi chua
                changed = (
                    price_now is not None
                    and st["init_price"] is not None
                    and price_now != st["init_price"]
                )

                if changed:
                    now_ts2 = self._get_clock_now()
                    ts2_str = f"{now_ts2.hour}:{now_ts2.minute:02d}:{now_ts2.second:02d}"
                    mb_label = "Mua" if st["proof_label"] == "max" else "Bán"
                    self.log(f"✅ Đã chèn Slot {slot_num} ({mb_label}) lúc {ts2_str}", "success")
                    self.log(f"   Giá: {st['init_price']}B → {price_now}B", "success")

                    # Chup screenshot NGAY LAP TUC (truoc click chen)
                    now_ts  = self._get_clock_now()
                    ts_str  = f"{now_ts.hour}h{now_ts.minute:02d}p{now_ts.second:02d}s"
                    fname   = f"Slot{slot_num}_{st['proof_label']}_{ts_str}.png"
                    fpath   = os.path.join(_PROOF_DIR, fname)
                    try:
                        ImageGrab.grab(bbox=self.rect).save(fpath)
                    except Exception:
                        pass

                    # Click vao dong gia (dung toa do da luu)
                    if st.get("price_click"):
                        pyautogui.click(st["price_click"])
                    elif st.get("price_anchor"):
                        pax, pay = st["price_anchor"]
                        pyautogui.click(pax + 60, pay)

                    # Click chen_tmpl: dung cached coords truoc, fallback wait_for
                    chen_btn = st.get("chen_coords")
                    if not chen_btn:
                        chen_btn = self._wait_for(st["chen_tmpl"], self.rect, threshold=0.72, timeout=3.0)
                    if chen_btn:
                        pyautogui.click(chen_btn)
                        # Cap nhat lai coords moi nhat
                        st["chen_coords"] = chen_btn

                    # Cap nhat UI pos_var
                    pos_var = st["cfg"].get("pos_var")
                    if pos_var:
                        self.root.after(0, lambda v=pos_var, s=slot_num: v.set(str(s)))

                    st["done"] = True
                    continue

                # Gia chua thay doi → click huy de dong popup
                # Kiem tra lan cuoi cua so active truoc khi huy
                now_check = self._get_clock_now()
                if not self._in_active_window(now_check):
                    # Het cua so: click huy de ket thuc loop hien tai
                    btn_huy = self._wait_for("btn_huy.png", self.rect, 0.72, timeout=2.0)
                    if btn_huy:
                        pyautogui.click(btn_huy)
                        deadline2 = time.time() + 2.0
                        while time.time() < deadline2:
                            if not self._find_silent("btn_huy.png", self.rect, 0.72):
                                break
                            time.sleep(0.05)
                    break  # break for-slot, vong while se xu ly cho den :50

                btn_huy = self._wait_for("btn_huy.png", self.rect, threshold=0.72, timeout=3.0)
                if btn_huy:
                    pyautogui.click(btn_huy)
                    # Cho popup dong (btn_huy bien mat)
                    deadline = time.time() + 2.0
                    while time.time() < deadline:
                        if not self._find_silent("btn_huy.png", self.rect, 0.72):
                            break
                        time.sleep(0.05)

        self.log("✅ Hoàn thành.", "success")
        self.running = False
        self.on_finished()
