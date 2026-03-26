"""
bot_insert_mua.py - Logic Auto Chen DS Mua
Flow:
  1. arrange_game
  2. Loop slot: click dong tai (1000, 214+(slot-1)*40)
  3. Doi popup FCFCF7 → OCR gia → chen neu gia doi
"""
import os
import re
import time
import datetime
import numpy as np
import pyautogui
import pytesseract
import cv2
from PIL import ImageGrab, Image as PILImage

_PROOF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "chen_proof")

_SLOT_X   = 1000
_SLOT_Y0  = 214
_SLOT_DY  = 40   # spacing giua cac dong

def _ensure_proof_dir():
    os.makedirs(_PROOF_DIR, exist_ok=True)


class InsertMuaMixin:

    def _ocr_mua_from_img(self, img):
        iw, ih = img.size
        img_big = img.resize((iw * 4, ih * 4), PILImage.LANCZOS)
        arr = np.array(img_big.convert("L"))
        _, bw = cv2.threshold(arr, 180, 255, cv2.THRESH_BINARY)
        bw = cv2.copyMakeBorder(bw, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
        pil = PILImage.fromarray(bw)
        text = pytesseract.image_to_string(
            pil, config="--psm 7 -c tessedit_char_whitelist=0123456789"
        ).strip()
        if len(text) > 1:
            text = text[:-1]
        digits = re.sub(r"[^\d]", "", text)
        return digits if len(digits) >= 4 else None

    def _wait_popup_close_mua(self, timeout=3.0):
        if not self.rect: return
        x1, y1 = self.rect[0], self.rect[1]
        deadline = time.time() + timeout
        while time.time() < deadline:
            if not self.running: return
            if not self.is_color_match("FCFCF7", x1 + 679, y1 + 595):
                return
            time.sleep(0.05)

    def _get_clock_now_mua(self):
        now = datetime.datetime.now()
        if getattr(self, "_insert_time_offset", None) is not None:
            now = now + self._insert_time_offset
        return now

    def _in_active_window_mua(self):
        s = self._get_clock_now_mua().second
        return s >= 50 or s <= 25

    def run_insert_mua(self, slot_configs, time_limit_minutes=None):
        self.running = True
        _ensure_proof_dir()

        if not self.arrange_game():
            self.log("❌ Không tìm thấy cửa sổ game!")
            self.running = False
            self.on_finished()
            return

        x1, y1, _, _ = self.rect
        start_time = time.time()

        self.log(f"🚀 Bắt đầu Auto Chèn DS Mua - {len(slot_configs)} slot", "header")
        for cfg in slot_configs:
            slot_num = int(cfg["slot"])
            is_max   = (cfg["mua_ban"] == "Mua")
            self.log(f"  Slot {slot_num}: {'Chèn Max' if is_max else 'Chèn Min'}", "white")
        self.log("", "white")

        slot_states = {int(cfg["slot"]): {"init_price": None, "done": False}
                       for cfg in slot_configs}
        all_seen_prices = set()

        if not self._in_active_window_mua():
            s_now = self._get_clock_now_mua().second
            self.log(f"⏳ Chờ đến giây :50... (hiện tại :{s_now:02d})", "white")
            while self.running:
                if self._get_clock_now_mua().second >= 50:
                    break
                time.sleep(0.05)

        while self.running:
            if time_limit_minutes is not None:
                if (time.time() - start_time) / 60.0 >= time_limit_minutes:
                    self.log(f"⏰ Hết thời gian {time_limit_minutes} phút. Dừng.", "orange")
                    break

            if not self._in_active_window_mua():
                _wait_count = getattr(self, "_insert_mua_wait_count", 0) + 1
                self._insert_mua_wait_count = _wait_count
                if _wait_count == 1:
                    self.log("⏸ Qua :25 — chờ đến :50...", "orange")
                while self.running:
                    if self._get_clock_now_mua().second >= 50:
                        break
                    time.sleep(0.05)
                continue

            active_slots = [cfg for cfg in slot_configs
                            if not slot_states[int(cfg["slot"])]["done"]]
            if not active_slots:
                break

            for cfg in active_slots:
                if not self.running:
                    break

                slot_num = int(cfg["slot"])
                is_max   = (cfg["mua_ban"] == "Mua")
                st       = slot_states[slot_num]

                # Toa do dong trong DS Mua
                slot_y = _SLOT_Y0 + (slot_num - 1) * _SLOT_DY

                if is_max:
                    huy_x, huy_y   = 997, 587
                    chen_x, chen_y = 875, 588
                    chen_color     = "D03C23"
                    price_x, price_y = 973, 321
                    bbox_price     = (x1 + 906, y1 + 311, x1 + 1041, y1 + 331)
                else:
                    huy_x, huy_y   = 1004, 617
                    chen_x, chen_y = 882, 616
                    chen_color     = "0C8FF3"
                    price_x, price_y = 975, 329
                    bbox_price     = (x1 + 908, y1 + 319, x1 + 1063, y1 + 340)

                # Buoc 1: Click dong
                pyautogui.click(x1 + _SLOT_X, y1 + slot_y)
                time.sleep(0.3)

                # Buoc 2: Doi popup cu dong, detect popup moi
                self._wait_popup_close_mua()
                popup_opened = self.hover_and_wait_color(
                    679, 595, "FCFCF7", timeout=5.0, click_if_match=False
                )
                if not popup_opened:
                    self.log(f"⚠️ Slot {slot_num}: popup không hiện, thử lại...", "orange")
                    continue

                time.sleep(0.1)

                # Buoc 3: OCR gia
                price_img = ImageGrab.grab(bbox=bbox_price)
                price_now = self._ocr_mua_from_img(price_img)

                # Contamination check
                own_init = slot_states[slot_num]["init_price"]
                suspicious = all_seen_prices - ({own_init} if own_init else set())
                if price_now and price_now in suspicious:
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()
                    continue
                if price_now:
                    all_seen_prices.add(price_now)

                # Lan dau: luu gia goc
                if st["init_price"] is None:
                    if price_now is None:
                        pyautogui.click(x1 + huy_x, y1 + huy_y)
                        self._wait_popup_close_mua()
                        continue
                    st["init_price"] = price_now
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"📌 Slot {slot_num} ({mb_label}): giá gốc = {price_now}B", "white")
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()
                    continue

                # Gia chua thay doi
                if price_now == st["init_price"]:
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()
                    continue

                # Buoc 4: Gia thay doi → chup proof NGAY LAP TUC roi chen
                if price_now and price_now != st["init_price"]:
                    old_price = st["init_price"]
                    now_ts   = self._get_clock_now_mua()
                    ts_str   = f"{now_ts.hour}:{now_ts.minute:02d}:{now_ts.second:02d}"
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"✅ Đã chèn Slot {slot_num} ({mb_label}) lúc {ts_str}", "success")
                    self.log(f"   Giá: {old_price}B → {price_now}B", "success")

                    # Chup proof ngay luc phat hien gia doi (popup dang hien)
                    try:
                        ts_fname = f"{now_ts.hour}h{now_ts.minute:02d}p{now_ts.second:02d}s"
                        label_f  = "max" if is_max else "min"
                        fname    = f"Mua_Slot{slot_num}_{label_f}_{ts_fname}.png"
                        ImageGrab.grab(bbox=(x1, y1, x1+1280, y1+720)).save(
                            os.path.join(_PROOF_DIR, fname))
                    except Exception:
                        pass

                    pyautogui.click(x1 + price_x, y1 + price_y)
                    time.sleep(0.1)

                    clicked = self.hover_and_wait_color(
                        chen_x, chen_y, chen_color, timeout=1.0, click_if_match=True
                    )

                    if not clicked:
                        pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()

                    st["done"] = True

                else:
                    pyautogui.click(x1 + huy_x, y1 + huy_y)
                    self._wait_popup_close_mua()

        self.running = False
        self.on_finished()
