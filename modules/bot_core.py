"""
bot_core.py - Logic Bot chính: detect, click, scan phôi, nâng cấp (Color-Tracking Edition)
"""
import os
import time
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
    # Đã cấp giá trị mặc định (=None) cho toàn bộ tham số để fix lỗi sập ngầm của Auto Chèn/Mua
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

    def arrange_game(self):
        hwnd = win32gui.FindWindow(None, "FC ONLINE")
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, 0, 0, 1280, 720, win32con.SWP_SHOWWINDOW)
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
        x1, y1, _, _ = self.rect
        
        # 1. Thu hẹp vùng quét chính xác vào tọa độ chữ số tĩnh đã đo: (537,184) đến (567,203)
        scan_area = (x1 + 537, y1 + 184, x1 + 567, y1 + 203)
        shot = ImageGrab.grab(bbox=scan_area)
        img_gray = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)

        # 2. Sử dụng Canny Edge Detection: Lấy "Khung xương" của chữ số, chống mù lòa do hiệu ứng Glow
        img_edges = cv2.Canny(img_gray, 50, 150)

        best_grade, highest_val = -1, 0
        scales = [0.8, 0.9, 1.0, 1.1, 1.2] # Nới rộng dải scale một chút do khung đã rất chật

        for g in range(1, 14):
            p = os.path.join(SAMPLE_DIR, f"{g}.png")
            if not os.path.exists(p): continue
            template = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            template_edges = cv2.Canny(template, 50, 150) # Cũng lấy khung xương mẫu

            for scale in scales:
                w_t = int(template_edges.shape[1] * scale)
                h_t = int(template_edges.shape[0] * scale)
                if w_t == 0 or h_t == 0 or w_t > img_edges.shape[1] or h_t > img_edges.shape[0]:
                    continue

                resized_template = cv2.resize(template_edges, (w_t, h_t), interpolation=cv2.INTER_NEAREST)
                res = cv2.matchTemplate(img_edges, resized_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)

                if max_val > highest_val:
                    highest_val = max_val
                    best_grade = g

        # Threshold của Edge Match thường thấp hơn Gray (Lớn hơn 0.15 là đã khớp xương chữ)
        if highest_val > 0.15:
            return best_grade

        # 3. FALLBACK: Cứu cánh bằng thuật toán GrayScale cũ nhưng khắt khe hơn
        best_grade_gray, highest_val_gray = -1, 0
        for g in range(1, 14):
            p = os.path.join(SAMPLE_DIR, f"{g}.png")
            if not os.path.exists(p): continue
            template = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            for scale in scales:
                w_t = int(template.shape[1] * scale)
                h_t = int(template.shape[0] * scale)
                if w_t == 0 or h_t == 0 or w_t > img_gray.shape[1] or h_t > img_gray.shape[0]:
                    continue
                resized_template = cv2.resize(template, (w_t, h_t), interpolation=cv2.INTER_AREA)
                res = cv2.matchTemplate(img_gray, resized_template, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > highest_val_gray and max_val > 0.70:
                    highest_val_gray = max_val
                    best_grade_gray = g

        return best_grade_gray

    # ===================== GAME INTERACTIONS =====================
    def handle_bp_protection(self):
        if not self.running: return False
        x1, y1, _, _ = self.rect
        
        # Click nút bảo vệ BP
        pyautogui.click(x1 + 697, y1 + 668)
        time.sleep(0.5)
        
        # Kéo thanh trượt đến Max (Tốc độ kéo cực nhanh: 0.15s)
        pyautogui.moveTo(x1 + 614, y1 + 442)
        time.sleep(0.1)
        pyautogui.mouseDown()
        time.sleep(0.05)
        pyautogui.moveTo(x1 + 870, y1 + 442, duration=0.15) 
        time.sleep(0.1)
        pyautogui.mouseUp()
        time.sleep(0.2)
        
        # Click Xác nhận
        pyautogui.click(x1 + 743, y1 + 597)
        time.sleep(0.5)
        return True

    def _scan_fodder_with_threshold(self, thresh_img, fodder_region, target_counts, current_cycle_fodder):
        data = pytesseract.image_to_data(
            thresh_img, config='--psm 11 -c tessedit_char_whitelist=0123456789', output_type=pytesseract.Output.DICT
        )
        for i, text in enumerate(data['text']):
            if text in target_counts and target_counts[text] > 0:
                cx = fodder_region[0] + (data['left'][i] + data['width'][i] // 2) // 2
                cy = fodder_region[1] + (data['top'][i] + data['height'][i] // 2) // 2
                pyautogui.click(cx, cy)
                target_counts[text] -= 1
                current_cycle_fodder[text] += 1
                time.sleep(0.15)
                if not any(target_counts.values()):
                    return True
        return False

    def _fill_input(self, cx, cy, val):
        if not self.running: return
        pyautogui.click(cx, cy)
        time.sleep(0.1)
        pyautogui.click(cx, cy)
        time.sleep(0.15)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.15)
        pyautogui.press('backspace')
        time.sleep(0.1)
        pyautogui.write(str(val), interval=0.03)
        time.sleep(0.15)
        pyautogui.press('enter')

    def _do_buy_loop(self, target_ovr, target_price, remaining_qty, log_fail_once=False):
        buy_success = False
        has_logged_fail = False
        actual_bought = 0
        x1, y1, _, _ = self.rect

        while not buy_success and self.running:
            pyautogui.click(x1 + 1039, y1 + 671)
            time.sleep(0.5)

            confirm_success = self.hover_and_wait_color(750, 602, "09D95E", timeout=3.0, click_if_match=True)
            if not confirm_success:
                continue

            outcome = None
            deadline = time.time() + 8.0
            while time.time() < deadline:
                if not self.running: break
                pyautogui.moveTo(x1 + 737, y1 + 671)
                time.sleep(0.05)
                if self.is_color_match("09D95E", x1 + 737, y1 + 671):
                    outcome = "success"
                    break
                    
                pyautogui.moveTo(x1 + 768, y1 + 460)
                time.sleep(0.05)
                if self.is_color_match("09D95E", x1 + 768, y1 + 460):
                    outcome = "fail"
                    break

            if outcome == "fail":
                if log_fail_once and not has_logged_fail:
                    self.log("❌ Mua thất bại! Đang spam ...", "fail")
                    has_logged_fail = True
                pyautogui.click(x1 + 768, y1 + 460) 
                time.sleep(0.2)
                continue

            elif outcome == "success":
                pyautogui.click(x1 + 737, y1 + 671)
                buy_success = True
                time.sleep(1.0)
            else:
                return 0, False, True

        if not self.running: return 0, False, False

        scan_qty_region = (x1 + 695, y1 + 618, x1 + 706, y1 + 633)
        shot = ImageGrab.grab(bbox=scan_qty_region)
        img_np = cv2.resize(np.array(shot), None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC) 
        gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
        _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        text = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()
        
        try: actual_bought = int(text)
        except ValueError:
            self.log("❌ Lỗi OCR. DỪNG!", "fail")
            self.running = False
            return 0, False, True

        # Click Nhận ngay cuối cùng
        self.hover_and_wait_color(857, 673, "09D95E", timeout=3.0, click_if_match=True)
        time.sleep(1.0)

        return actual_bought, True, False