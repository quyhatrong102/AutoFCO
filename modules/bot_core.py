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
    def __init__(self, log_func, ui_update_func, on_finished_func,
                 fodder_map, target_grade, alarm_func, success_alarm_func,
                 log_update_func, bp_enabled, auto_buy_config=None):
        self.log = log_func
        self.log_update = log_update_func
        self.update_ui_icon = ui_update_func
        self.on_finished = on_finished_func
        self.trigger_error_alarm = alarm_func
        self.trigger_success_alarm = success_alarm_func
        self.fodder_map = fodder_map
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
        """Đọc đúng 1 Pixel tại tọa độ và so sánh mã màu Hex (Chống lag siêu nhẹ)"""
        hex_color = hex_color.lstrip('#')
        tr, tg, tb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        try:
            screen = ImageGrab.grab(bbox=(x, y, x+1, y+1))
            r, g, b = screen.getpixel((0, 0))
            return (abs(r - tr) <= tolerance and abs(g - tg) <= tolerance and abs(b - tb) <= tolerance)
        except Exception:
            return False

    def hover_and_wait_color(self, rel_x, rel_y, hex_color, timeout=5.0, click_if_match=True):
        """Di chuột vào tọa độ, chờ nó đổi màu thì click"""
        if not self.running or not self.rect: return False
        x, y = self.rect[0] + rel_x, self.rect[1] + rel_y
        pyautogui.moveTo(x, y)
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            if not self.running: return False
            if self.is_color_match(hex_color, x, y):
                if click_if_match:
                    time.sleep(0.1) # Dừng một nhịp để game nhận click
                    pyautogui.click(x, y)
                return True
            time.sleep(0.1)
        return False

    # ===================== IMAGE MATCHING CẤP THẺ =====================

    def _multi_scale_match(self, template, screen_gray, threshold):
        best_val = 0
        best_loc = None
        best_w, best_h = 0, 0
        scales = [1.0, 1.25, 1.5, 0.8, 1.1]
        for scale in scales:
            w = int(template.shape[1] * scale)
            h = int(template.shape[0] * scale)
            if w > screen_gray.shape[1] or h > screen_gray.shape[0] or w == 0 or h == 0: continue
            resized_template = cv2.resize(template, (w, h), interpolation=cv2.INTER_AREA)
            res = cv2.matchTemplate(screen_gray, resized_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(res)
            if max_val > best_val:
                best_val, best_loc, best_w, best_h = max_val, max_loc, w, h
        if best_val >= threshold: return best_loc, best_w, best_h
        return None, 0, 0

    def detect_grade_PRECISION(self):
        x1, y1, x2, y2 = self.rect
        w, h = x2 - x1, y2 - y1
        scan_area = (x1 + int(w * 0.31), y1 + int(h * 0.14), x1 + int(w * 0.51), y1 + int(h * 0.39))
        shot = ImageGrab.grab(bbox=scan_area)
        img_gray = cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2GRAY)
        best_grade, highest_val = -1, 0
        scales = np.linspace(0.8, 1.2, 5)
        for g in range(1, 14):
            p = os.path.join(SAMPLE_DIR, f"{g}.png")
            if not os.path.exists(p): continue
            template = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
            for scale in scales:
                res = cv2.matchTemplate(img_gray, cv2.resize(template, None, fx=scale, fy=scale), cv2.TM_CCOEFF_NORMED)
                _, max_val, _, _ = cv2.minMaxLoc(res)
                if max_val > highest_val and max_val > 0.75:
                    highest_val = max_val
                    best_grade = g
        return best_grade

    # ===================== GAME INTERACTIONS =====================

    def handle_bp_protection(self):
        if not self.running: return False
        x1, y1, _, _ = self.rect
        
        # Click nút bảo vệ BP
        pyautogui.click(x1 + 697, y1 + 668)
        time.sleep(0.5)
        
        # Kéo thanh trượt đến Max
        pyautogui.moveTo(x1 + 613, y1 + 442)
        pyautogui.dragTo(x1 + 834, y1 + 442, duration=0.3, button='left')
        time.sleep(0.3)
        
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
            # Click Mua hàng loạt
            pyautogui.click(x1 + 1039, y1 + 671)
            time.sleep(0.5)

            # Chờ popup mở và ấn Xác nhận (Màu xanh 09D95E)
            confirm_success = self.hover_and_wait_color(750, 602, "09D95E", timeout=3.0, click_if_match=True)
            if not confirm_success:
                continue

            # Chờ kết quả Thất bại hoặc Thành công (Luân phiên đưa chuột check màu)
            outcome = None
            deadline = time.time() + 8.0
            while time.time() < deadline:
                if not self.running: break
                
                # Check Nhận Ngay (Thành công)
                pyautogui.moveTo(x1 + 737, y1 + 671)
                time.sleep(0.05)
                if self.is_color_match("09D95E", x1 + 737, y1 + 671):
                    outcome = "success"
                    break
                    
                # Check Xác Nhận (Thất bại)
                pyautogui.moveTo(x1 + 768, y1 + 460)
                time.sleep(0.05)
                if self.is_color_match("09D95E", x1 + 768, y1 + 460):
                    outcome = "fail"
                    break

            if outcome == "fail":
                if log_fail_once and not has_logged_fail:
                    self.log("❌ Mua thất bại! Đang spam ...", "fail")
                    has_logged_fail = True
                pyautogui.click(x1 + 768, y1 + 460) # Click tắt popup
                time.sleep(0.2)
                continue

            elif outcome == "success":
                pyautogui.click(x1 + 737, y1 + 671)
                buy_success = True
                time.sleep(1.0)
            else:
                return 0, False, True # Timeout

        if not self.running: return 0, False, False

        # Vùng check Số lượng mua được (Gọn cực kì, không cần OCR cả bảng)
        scan_qty_region = (x1 + 695, y1 + 618, x1 + 706, y1 + 633)
        shot = ImageGrab.grab(bbox=scan_qty_region)
        img_np = cv2.resize(np.array(shot), None, fx=4, fy=4, interpolation=cv2.INTER_CUBIC) # Resize to lên để đọc
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