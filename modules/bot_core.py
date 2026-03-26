"""
bot_core.py - Logic Bot chính: detect, click, scan phôi, nâng cấp (Color-Tracking Edition)
"""
import os
import time
import threading
import pyautogui
import cv2
import numpy as np
import win32gui
import win32con
import pytesseract
from PIL import ImageGrab
from collections import Counter

from config import SAMPLE_DIR


class FCOnlineBot:
    def __init__(self, log_func=None, ui_update_func=None, on_finished_func=None,
                 fodder_map=None, target_grade=1, alarm_func=None, success_alarm_func=None,
                 log_update_func=None, bp_enabled=False, auto_buy_config=None):
        
        self.log = log_func if log_func else (lambda msg, tag="": print(msg))
        self.log_update = log_update_func if log_update_func else (lambda pos, msg, tag="": None)
        self.update_ui_icon = ui_update_func if ui_update_func else (lambda grade: None)
        self.on_finished = on_finished_func if on_finished_func else (lambda *args, **kwargs: None)
        self.trigger_error_alarm = alarm_func if alarm_func else (lambda msg=None: None)
        self.trigger_success_alarm = success_alarm_func if success_alarm_func else (lambda grade, msg=None: None)
        
        self.fodder_map = fodder_map if fodder_map else {}
        self.target_grade = target_grade
        self.bp_enabled = bp_enabled
        self.auto_buy_config = auto_buy_config
        self.running = False
        self.rect = None
        self.has_used_bp_in_cycle = False

        self.total_cycles = 0
        self.fodder_consumed = Counter()
        self.grade_success = Counter()
        self.grade_fail = Counter()
        self.last_target_grade = None
        self.last_log_pos = None

    def arrange_game(self, hidden=False):
        hwnd = win32gui.FindWindow(None, "FC ONLINE")
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            x_pos = -1280 if hidden else 0
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, x_pos, 0, 1280, 720, win32con.SWP_SHOWWINDOW)
            time.sleep(1.0)
            self.rect = win32gui.GetWindowRect(hwnd)
            return True
        return False

    # ===================== COLOR TRACKING ENGINE =====================
    def is_color_match(self, hex_color, x, y, tolerance=15):
        hex_color = hex_color.lstrip('#')
        tr, tg, tb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        try:
            screen = ImageGrab.grab(bbox=(x, y, x+1, y+1))
            r, g, b = screen.getpixel((0, 0))
            return (abs(r - tr) <= tolerance and abs(g - tg) <= tolerance and abs(b - tb) <= tolerance)
        except Exception:
            return False

    def hover_and_wait_color(self, rel_x, rel_y, hex_color, timeout=5.0, click_if_match=True):
        if not self.running or not self.rect: return False
        x, y = self.rect[0] + rel_x, self.rect[1] + rel_y
        pyautogui.moveTo(x, y)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.running: return False
            if self.is_color_match(hex_color, x, y):
                if click_if_match:
                    time.sleep(0.1) 
                    pyautogui.click(x, y)
                return True
            time.sleep(0.1)
        return False

    # ===================== IMAGE MATCHING CẤP THẺ MỚI (TỐI ƯU SIÊU CHUẨN) =====================
    def detect_grade_PRECISION(self):
        """Scan vung lon, multi-scale, threshold 0.75 - logic goc."""
        x1, y1, x2, y2 = self.rect
        scan_area = (x1 + 430, y1 + 150, x1 + 680, y1 + 400)
        shot = ImageGrab.grab(bbox=scan_area)
        img_gray = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
        best_grade, highest_val = -1, 0
        scales = np.linspace(0.8, 1.2, 5)
        for g in range(1, 14):
            p = os.path.join(SAMPLE_DIR, f"{g}.png")
            if not os.path.exists(p):
                continue
            template = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            for scale in scales:
                res = cv2.matchTemplate(
                    img_gray,
                    cv2.resize(template, None, fx=scale, fy=scale),
                    cv2.TM_CCOEFF_NORMED
                )
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > highest_val and max_val > 0.75:
                    highest_val = max_val
                    best_grade = g
        return best_grade

    def check_and_close_popup(self):
        """Quet btn_close.png trong vung co dinh goc duoi phai."""
        if not self.rect: return
        x1, y1, _, _ = self.rect
        br_region = (x1 + 1072, y1 + 524, x1 + 1150, y1 + 588)
        p = os.path.join(SAMPLE_DIR, "btn_close.png")
        if not os.path.exists(p): return
        template = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        shot = ImageGrab.grab(bbox=br_region)
        screen_gray = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= 0.75:
            h, w = template.shape
            cx = br_region[0] + max_loc[0] + w // 2
            cy = br_region[1] + max_loc[1] + h // 2
            pyautogui.click(cx, cy)
            time.sleep(0.2)

    def _start_popup_watcher(self):
        """Background thread: cu 1s check va dong popup neu xuat hien."""
        def _watch():
            while self.running:
                self.check_and_close_popup()
                time.sleep(1.0)
        t = threading.Thread(target=_watch, daemon=True)
        t.start()



    def _start_popup_watcher(self):
        """Chay background thread, cu 1s quet btn_close 1 lan."""
        def _watch():
            while self.running:
                try:
                    self.check_and_close_popup()
                except Exception:
                    pass
                time.sleep(1.0)
        t = threading.Thread(target=_watch, daemon=True)
        t.start()

    # ===================== GAME INTERACTIONS =====================
    def handle_bp_protection(self):
        if not self.running: return False
        x1, y1, _, _ = self.rect
        
        # Click nút bảo vệ BP
        pyautogui.click(x1 + 697, y1 + 668)
        time.sleep(0.5)
        
        # Kéo thanh trượt đến Max (chuẩn xác click 614, 442 và kéo chậm 1s)
        pyautogui.moveTo(x1 + 614, y1 + 442)
        time.sleep(0.1)
        pyautogui.mouseDown()
        time.sleep(0.05)
        pyautogui.moveTo(x1 + 870, y1 + 442, duration=1.0) 
        time.sleep(0.1)
        pyautogui.mouseUp()
        time.sleep(0.2)
        
        # Click Xác nhận
        pyautogui.click(x1 + 743, y1 + 597)
        time.sleep(0.5)
        return True

    # Vung tick check moi dong (relative to window topleft):
    # Dong i (0-based): x=1029..1110, y=(281 + i*39)..(281 + (i+1)*39), max 9 dong
    _TICK_X1      = 1029
    _TICK_X2      = 1110
    _TICK_Y0      = 281   # y tren cua dong 0
    _TICK_ROW_H   = 39    # chieu cao moi dong
    _TICK_MAX_ROW = 9
    _TICK_TEMPLATE = None

    def _get_tick_template(self):
        if self._TICK_TEMPLATE is not None:
            return self._TICK_TEMPLATE
        p = os.path.join(SAMPLE_DIR, "ticked.png")
        if os.path.exists(p):
            FCOnlineBot._TICK_TEMPLATE = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        return FCOnlineBot._TICK_TEMPLATE

    def _cy_to_row(self, cy):
        """Chuyen cy (screen absolute) → row index (0-based), hoac -1 neu ngoai vung."""
        if not self.rect: return -1
        y1 = self.rect[1]
        rel_y = cy - y1
        row_i = int((rel_y - self._TICK_Y0) / self._TICK_ROW_H)
        if 0 <= row_i < self._TICK_MAX_ROW:
            return row_i
        return -1

    def _is_ticked(self, cy):
        """
        Kiem tra dong co cy (screen absolute) da tick chua.
        Chup dung vung tick cua dong do, so khop voi ticked.png.
        """
        if not self.rect: return False
        tmpl = self._get_tick_template()
        if tmpl is None: return False
        row_i = self._cy_to_row(cy)
        if row_i < 0: return False
        x1, y1 = self.rect[0], self.rect[1]
        bbox = (
            x1 + self._TICK_X1,
            y1 + self._TICK_Y0 + row_i * self._TICK_ROW_H,
            x1 + self._TICK_X2,
            y1 + self._TICK_Y0 + (row_i + 1) * self._TICK_ROW_H,
        )
        try:
            shot = ImageGrab.grab(bbox=bbox)
            gray = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
            th, tw = tmpl.shape
            if gray.shape[0] < th or gray.shape[1] < tw:
                return False
            res = cv2.matchTemplate(gray, tmpl, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, _ = cv2.minMaxLoc(res)
            return max_val >= 0.75
        except Exception:
            return False

    def _count_ticked_all(self, needed_ovrs, fodder_region):
        """
        Scroll xuong toan bo danh sach, dem tat ca phoi da tick xanh.
        Goi sau khi da scroll len dinh.
        """
        result = Counter()
        needed_set = set(str(o) for o in needed_ovrs)
        last_hash = None
        for _ in range(50):
            if not self.running: break
            ticked_now = self._count_ticked(needed_ovrs, fodder_region)
            for k, v in ticked_now.items():
                result[k] = max(result[k], result.get(k, 0) + v)
            img_check = ImageGrab.grab(bbox=fodder_region)
            curr_hash = cv2.resize(cv2.cvtColor(np.array(img_check), cv2.COLOR_RGB2GRAY), (60, 60))
            if last_hash is not None and np.mean(cv2.absdiff(last_hash, curr_hash)) < 1.0:
                break
            last_hash = curr_hash
            for _ in range(9): __import__('pyautogui').scroll(-100)
            time.sleep(0.3)
        return result

    def _count_ticked(self, needed_ovrs, fodder_region):
        """
        Scan OCR vung phoi, dem so phoi da tick xanh theo OVR.
        Tra ve Counter {ovr_str: so_da_tick}.
        Dung de tru vao target_counts truoc khi bat dau scan, tranh click lai phoi da chon.
        """
        result = Counter()
        if not self.rect: return result
        try:
            shot = ImageGrab.grab(bbox=fodder_region)
            img  = cv2.resize(cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR),
                              None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, thresh = cv2.threshold(gray, 165, 255, cv2.THRESH_BINARY_INV)
            data = pytesseract.image_to_data(
                thresh, config='--psm 11 -c tessedit_char_whitelist=0123456789',
                output_type=pytesseract.Output.DICT
            )
            seen_cy = set()
            needed_set = set(str(o) for o in needed_ovrs)
            for i, text in enumerate(data['text']):
                if text in needed_set:
                    cx = fodder_region[0] + (data['left'][i] + data['width'][i] // 2) // 2
                    cy = fodder_region[1] + (data['top'][i] + data['height'][i] // 2) // 2
                    row_key = self._cy_to_row(cy)
                    key = row_key if row_key >= 0 else round(cy / 5) * 5
                    if key in seen_cy:
                        continue
                    seen_cy.add(key)
                    if self._is_ticked(cy):
                        result[text] += 1
        except Exception:
            pass
        return result

    def _scan_fodder_with_threshold(self, thresh_img, fodder_region, target_counts, current_cycle_fodder,
                                       processed_cy=None):
        """
        Scan OCR tim phoi theo OVR.
        - processed_cy: set cac cy da xu ly (chia se giua 3 threshold, tranh double-count).
        - Neu phoi da tick xanh → giam count, KHONG click (tranh uncheck).
        - Chua tick → click.
        """
        if processed_cy is None:
            processed_cy = set()

        data = pytesseract.image_to_data(
            thresh_img, config='--psm 11 -c tessedit_char_whitelist=0123456789',
            output_type=pytesseract.Output.DICT
        )
        acted_any = False
        for i, text in enumerate(data['text']):
            if text in target_counts and target_counts[text] > 0:
                cx = fodder_region[0] + (data['left'][i] + data['width'][i] // 2) // 2
                cy = fodder_region[1] + (data['top'][i] + data['height'][i] // 2) // 2

                # Tranh double-count: cung cy da xu ly boi threshold khac trong cung scan
                row_key = self._cy_to_row(cy)
                cy_key  = row_key if row_key >= 0 else round(cy / 5) * 5
                if cy_key in processed_cy:
                    continue
                processed_cy.add(cy_key)

                if self._is_ticked(cy):
                    # Da tick → skip, KHONG click, KHONG giam count
                    # (target_counts da duoc tru boi current_cycle_fodder truoc khi scan)
                    continue
                else:
                    # Chua tick → click
                    pyautogui.click(cx, cy)
                    target_counts[text] -= 1
                    current_cycle_fodder[text] += 1
                    acted_any = True
                    time.sleep(0.15)
                    if not any(target_counts.values()):
                        return acted_any
        return acted_any
    def _fill_input(self, cx, cy, val):
        if not self.running: return
        pyautogui.click(cx, cy)
        time.sleep(0.15)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        pyautogui.write(str(val), interval=0.04)
        time.sleep(0.15)
        pyautogui.press('enter')

    def _read_total_price(self):
        """
        OCR vung tong tien (918,569 → 1100,599).
        Chu mau do tren nen toi → dung THRESH_BINARY_INV.
        Bo ky tu cuoi (B/8 bi nham) va dau phay phan cach hang nghin.
        Vi du: "260B" → 260, "1,750B" → 1750.
        """
        if not self.rect: return None
        x1, y1 = self.rect[0], self.rect[1]
        bbox = (x1 + 918, y1 + 569, x1 + 1100, y1 + 599)
        try:
            from PIL import Image as _PILImg
            import re as _re
            shot = ImageGrab.grab(bbox=bbox)
            iw, ih = shot.size
            img_big = shot.resize((iw * 4, ih * 4), _PILImg.LANCZOS)
            arr = np.array(img_big.convert("L"))
            _, bw = cv2.threshold(arr, 100, 255, cv2.THRESH_BINARY_INV)
            bw = cv2.copyMakeBorder(bw, 8, 8, 8, 8, cv2.BORDER_CONSTANT, value=255)
            pil = _PILImg.fromarray(bw)
            text = pytesseract.image_to_string(
                pil, config="--psm 7 -c tessedit_char_whitelist=0123456789BM,."
            ).strip()
            if len(text) > 1:
                text = text[:-1]  # bo ky tu cuoi (B hoac 8 bi nham)
            digits = _re.sub(r"[^0-9]", "", text)
            return int(digits) if digits else None
        except Exception:
            return None
    def _fill_price_and_qty_verified(self, price_cx, price_cy, price_val,
                                      qty_cx, qty_cy, qty_val,
                                      price_input, max_retry=5):
        """
        Dien gia + so luong roi verify bang OCR vung tong tien.
        expected = price_input * qty_val.
        Neu sai → dien lai, toi da max_retry lan.
        """
        expected = int(price_input) * int(qty_val)
        for attempt in range(max_retry):
            if not self.running: return
            self._fill_input(price_cx, price_cy, price_val)
            time.sleep(0.5)
            self._fill_input(qty_cx, qty_cy, qty_val)
            time.sleep(0.3)
            displayed = self._read_total_price()
            if displayed == expected:
                return
            time.sleep(0.2)
    def _do_buy_loop(self, target_ovr, target_price, remaining_qty, log_fail_once=False):
        has_logged_fail = False
        actual_bought = 0
        x1, y1, _, _ = self.rect

        while self.running:
            # Buoc 1: Click nut Mua hang loat
            pyautogui.click(x1 + 1039, y1 + 671)

            # Buoc 2: Di chuot den 755,603, doi 0.15s roi poll color 09D95E → click xac nhan
            pyautogui.moveTo(x1 + 755, y1 + 603)
            time.sleep(0.15)
            deadline = time.time() + 10.0
            while time.time() < deadline:
                if not self.running: return 0, False, False
                if self.is_color_match("09D95E", x1 + 755, y1 + 603):
                    pyautogui.click(x1 + 755, y1 + 603)
                    break
                time.sleep(0.1)
            else:
                continue  # timeout → click lai tu dau

            # Buoc 3: Poll song song 2 nut ket qua (20s cho game lag)
            outcome = None
            deadline = time.time() + 20.0
            while time.time() < deadline:
                if not self.running: return 0, False, False

                # Check that bai: 770,457
                pyautogui.moveTo(x1 + 770, y1 + 457)
                time.sleep(0.15)
                if self.is_color_match("09D95E", x1 + 770, y1 + 457):
                    outcome = "fail"
                    break

                # Check thanh cong: 739,671
                pyautogui.moveTo(x1 + 739, y1 + 671)
                time.sleep(0.15)
                if self.is_color_match("09D95E", x1 + 739, y1 + 671):
                    outcome = "success"
                    break

            if outcome == "fail":
                if log_fail_once and not has_logged_fail:
                    self.log("❌ Mua thất bại! Đang spam ...", "fail")
                    has_logged_fail = True
                pyautogui.click(x1 + 770, y1 + 457)
                continue

            elif outcome == "success":
                pyautogui.click(x1 + 739, y1 + 671)
            else:
                return 0, False, True  # timeout → stop

            # Buoc 4: Doi button 860,672 hien (09D95E) - UI da cap nhat → scan OCR → click
            pyautogui.moveTo(x1 + 860, y1 + 672)
            time.sleep(0.15)
            deadline = time.time() + 5.0
            while time.time() < deadline:
                if not self.running: return 0, False, False
                if self.is_color_match("09D95E", x1 + 860, y1 + 672):
                    break
                time.sleep(0.1)

            # Buoc 5: Scan dong "Ban da mua duoc tong cong X cau thu"
            # Lay so nam giua chu "cong" va chu "cau"
            import re as _re
            scan_qty_region = (x1 + 541, y1 + 615, x1 + 753, y1 + 635)
            actual_bought = None
            while actual_bought is None and self.running:
                shot = ImageGrab.grab(bbox=scan_qty_region)
                img_np = cv2.resize(np.array(shot), None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC)
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                text = pytesseract.image_to_string(thresh, config='--psm 7 -l vie').strip()
                m = _re.search(r'\d+', text)
                if m:
                    try:
                        v = int(m.group())
                        if 1 <= v <= 10:
                            actual_bought = v
                    except ValueError:
                        pass
                if actual_bought is None:
                    time.sleep(0.1)
            if not self.running:
                return 0, False, False

            # Buoc 6: Click nut Nhan
            pyautogui.click(x1 + 860, y1 + 672)

            return actual_bought, True, False

        return 0, False, False