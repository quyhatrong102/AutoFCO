"""
bot_insert.py - Logic Auto Chen (toa do tinh, check gia thay doi bang OCR)
"""
import os
import re
import time
import datetime
import numpy as np
import pyautogui
import pytesseract
import cv2
from PIL import ImageGrab, Image as PILImage, ImageEnhance

_PROOF_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "lib", "chen_proof")

def _ensure_proof_dir():
    os.makedirs(_PROOF_DIR, exist_ok=True)


class InsertMixin:

    def _ocr_from_img(self, img):
        """
        OCR lay digits tu anh PIL.
        - resize x4 LANCZOS → Contrast x3 → THRESH_BINARY
        - whitelist 0123456789,B
        - LUON bo ky tu cuoi cung (du la chu hay so) de loai B/8 bi nham
        """
        iw, ih = img.size
        img_big = img.resize((iw * 4, ih * 4), PILImage.LANCZOS)
        gray = ImageEnhance.Contrast(img_big).enhance(3.0).convert("L")
        arr  = np.array(gray)
        _, bw = cv2.threshold(arr, 150, 255, cv2.THRESH_BINARY)
        bw = cv2.copyMakeBorder(bw, 6, 6, 6, 6, cv2.BORDER_CONSTANT, value=255)
        pil = PILImage.fromarray(bw)
        text = pytesseract.image_to_string(
            pil, config="--psm 7 -c tessedit_char_whitelist=0123456789B"
        ).strip()
        # Game LUON hien thi B sau gia (36000B)
        # OCR co the doc dung B hoac nham thanh 8 → luon bo ky tu cuoi
        if len(text) > 1:
            text = text[:-1]
        digits = re.sub(r"[^\d]", "", text)
        return digits if digits else None

    def _grab_price(self, x1, y1, is_max):
        """Chup vung gia co dinh. Tra ve (img_PIL, bbox)."""
        if is_max:
            bbox = (x1 + 906, y1 + 311, x1 + 1041, y1 + 331)
        else:
            bbox = (x1 + 908, y1 + 319, x1 + 1043, y1 + 340)
        return ImageGrab.grab(bbox=bbox), bbox

    def _get_text_click_coords(self, x1, y1, is_max):
        """OCR lay toa do chinh xac cua vung text gia tren man hinh."""
        img, bbox = self._grab_price(x1, y1, is_max)
        scale = 3
        iw, ih = img.size
        img_big = img.resize((iw * scale, ih * scale))
        arr = np.array(img_big.convert("L"))
        _, bw = cv2.threshold(arr, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        pil = PILImage.fromarray(bw)
        try:
            data = pytesseract.image_to_data(
                pil,
                config="--psm 7 -c tessedit_char_whitelist=0123456789",
                output_type=pytesseract.Output.DICT
            )
            boxes = [
                (data["left"][i], data["top"][i], data["width"][i], data["height"][i])
                for i, txt in enumerate(data["text"])
                if txt.strip().isdigit()
            ]
            if boxes:
                lx = min(b[0] for b in boxes)
                ty = min(b[1] for b in boxes)
                rx = max(b[0] + b[2] for b in boxes)
                by = max(b[1] + b[3] for b in boxes)
                cx = bbox[0] + (lx + rx) // 2 // scale
                cy = bbox[1] + (ty + by) // 2 // scale
                return cx, cy
        except Exception:
            pass
        return (bbox[0] + bbox[2]) // 2, (bbox[1] + bbox[3]) // 2

    def _get_clock_now(self):
        now = datetime.datetime.now()
        if getattr(self, "_insert_time_offset", None) is not None:
            now = now + self._insert_time_offset
        return now

    def _in_active_window(self):
        s = self._get_clock_now().second
        return s >= 50 or s <= 25

    def run_insert(self, slot_configs, time_limit_minutes=None):
        self.running = True
        _ensure_proof_dir()
        if not self.arrange_game():
            self.log("❌ Không tìm thấy cửa sổ game!")
            self.running = False
            self.on_finished()
            return

        x1, y1, _, _ = self.rect
        start_time = time.time()
        SLOT_X = 1000

        self.log(f"🚀 Bắt đầu Auto Chèn - {len(slot_configs)} slot", "header")
        for cfg in slot_configs:
            slot_num = int(cfg["slot"])
            is_max   = (cfg["mua_ban"] == "Mua")
            self.log(f"  Slot {slot_num}: {'Chèn Max' if is_max else 'Chèn Min'}", "white")
        self.log("", "white")

        # Trang thai tung slot: init_price + done flag
        slot_states = {}  # slot_num -> {"init_price": str|None, "done": bool}
        for cfg in slot_configs:
            slot_states[int(cfg["slot"])] = {"init_price": None, "done": False}

        # Cho den cua so active (:50)
        if not self._in_active_window():
            s_now = self._get_clock_now().second
            self.log(f"⏳ Chờ đến giây :50... (hiện tại :{s_now:02d})", "white")
            while self.running:
                if self._get_clock_now().second >= 50:
                    break
                time.sleep(0.05)

        while self.running:
            # Kiem tra time limit
            if time_limit_minutes is not None:
                if (time.time() - start_time) / 60.0 >= time_limit_minutes:
                    self.log(f"⏰ Hết thời gian {time_limit_minutes} phút. Dừng.", "orange")
                    break

            # Kiem tra cua so thoi gian :50 -> :25
            if not self._in_active_window():
                self.log("⏸ Qua :25 — chờ đến :50...", "orange")
                while self.running:
                    if self._get_clock_now().second >= 50:
                        break
                    time.sleep(0.05)
                self.log("▶ Bắt đầu lại...", "white")
                continue

            # Tat ca slot da xong?
            active_slots = [cfg for cfg in slot_configs
                            if not slot_states[int(cfg["slot"])]["done"]]
            if not active_slots:
                break

            for cfg in active_slots:
                if not self.running:
                    break

                slot_num = int(cfg["slot"])
                is_max   = (cfg["mua_ban"] == "Mua")
                slot_y   = 214 + ((slot_num - 1) * 40)
                st       = slot_states[slot_num]

                # 1. Di chuot vao slot, doi 0.15s roi click
                pyautogui.moveTo(x1 + SLOT_X, y1 + slot_y)
                time.sleep(0.15)
                pyautogui.click()

                # Toa do theo loai Mua/Ban
                if is_max:
                    huy_x, huy_y   = 997, 587
                    chen_x, chen_y = 875, 588
                    chen_color     = "D03C23"
                else:
                    huy_x, huy_y   = 1004, 617
                    chen_x, chen_y = 882, 616
                    chen_color     = "0C8FF3"

                # 2. Doi popup hien (mau 353838 tai nut Huy)
                _t0 = time.time()
                popup_opened = self.hover_and_wait_color(
                    huy_x, huy_y, "353838", timeout=2.0, click_if_match=False
                )
                self.log(f"   [DBG] popup wait: {time.time()-_t0:.3f}s slot{slot_num}", "white")

                if not popup_opened:
                    continue

                # Doi popup render xong
                time.sleep(0.5)

                # 3. Chup va OCR gia hien tai
                price_img, price_bbox = self._grab_price(x1, y1, is_max)
                price_now = self._ocr_from_img(price_img)



                if st["init_price"] is None:
                    # Lan dau: luu gia goc, log ra, dong popup
                    st["init_price"] = price_now
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"📌 Slot {slot_num} ({mb_label}): giá gốc = {price_now}B", "white")
                    pyautogui.click(self.rect[0] + huy_x, self.rect[1] + huy_y)
                    continue

                # So sanh gia: chi chen khi gia thay doi
                if price_now and price_now != st["init_price"]:
                    old_price = st["init_price"]

                    # Chup screenshot proof NGAY LAP TUC truoc khi click
                    try:
                        now_ts   = self._get_clock_now()
                        ts_fname = f"{now_ts.hour}h{now_ts.minute:02d}p{now_ts.second:02d}s"
                        label_f  = "max" if is_max else "min"
                        fname    = f"Slot{slot_num}_{label_f}_{ts_fname}.png"
                        ImageGrab.grab(bbox=(x1, y1, x1 + 1280, y1 + 720)).save(
                            os.path.join(_PROOF_DIR, fname)
                        )
                    except Exception:
                        pass

                    # Log
                    now_ts   = self._get_clock_now()
                    ts_str   = f"{now_ts.hour}:{now_ts.minute:02d}:{now_ts.second:02d}"
                    mb_label = "Mua" if is_max else "Bán"
                    self.log(f"✅ Đã chèn Slot {slot_num} ({mb_label}) lúc {ts_str}", "success")
                    self.log(f"   Giá: {old_price}B → {price_now}B", "success")

                    # Click vao vung text gia
                    tx, ty = self._get_text_click_coords(x1, y1, is_max)
                    pyautogui.click(tx, ty)
                    time.sleep(0.1)

                    # Click nut chen (logic y chang Mua, chi khac toa do va mau)
                    clicked = self.hover_and_wait_color(
                        chen_x, chen_y, chen_color, timeout=1.0, click_if_match=True
                    )

                    if clicked:
                        time.sleep(0.5)
                        pyautogui.press('enter')
                        time.sleep(1.0)
                    else:
                        pyautogui.click(self.rect[0] + huy_x, self.rect[1] + huy_y)

                    st["done"] = True

                else:
                    # Gia chua thay doi → dong popup, F5 lai
                    pyautogui.click(self.rect[0] + huy_x, self.rect[1] + huy_y)

            # Delay giua moi vong lap
            time.sleep(0.2)

        self.running = False
        self.on_finished()
