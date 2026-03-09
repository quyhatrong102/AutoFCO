"""
bot_core.py - Logic Bot chính: detect, click, scan phôi, nâng cấp
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

    # ===================== GAME WINDOW =====================

    def arrange_game(self):
        hwnd = win32gui.FindWindow(None, "FC ONLINE")
        if hwnd:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.SetWindowPos(hwnd, win32con.HWND_TOP, -7, 0, 1350, 1050, win32con.SWP_SHOWWINDOW)
            time.sleep(1.0)
            self.rect = win32gui.GetWindowRect(hwnd)
            return True
        return False

    # ===================== IMAGE MATCHING =====================

    def find_template_coords(self, template_name, region=None, threshold=0.75):
        p = os.path.join(SAMPLE_DIR, template_name)
        if not os.path.exists(p):
            return None
        template = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        bbox = region if region else self.rect
        screen = np.array(ImageGrab.grab(bbox=bbox))
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            h, w = template.shape
            return (bbox[0] + max_loc[0] + w // 2, bbox[1] + max_loc[1] + h // 2)
        return None

    def get_template_box(self, template_name, region=None, threshold=0.75):
        p = os.path.join(SAMPLE_DIR, template_name)
        if not os.path.exists(p):
            return None
        template = cv2.imread(p, cv2.IMREAD_GRAYSCALE)
        bbox = region if region else self.rect
        screen = np.array(ImageGrab.grab(bbox=bbox))
        screen_gray = cv2.cvtColor(screen, cv2.COLOR_RGB2GRAY)
        res = cv2.matchTemplate(screen_gray, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(res)
        if max_val >= threshold:
            h, w = template.shape
            return (bbox[0] + max_loc[0], bbox[1] + max_loc[1], w, h)
        return None

    # ===================== GAME INTERACTIONS =====================

    def clear_achievement_popup(self):
        if not self.rect:
            return False
        x1, y1, x2, y2 = self.rect
        w, h = x2 - x1, y2 - y1
        br_region = (x1 + w // 2, y1 + h // 2, x2, y2)
        close_coords = self.find_template_coords("close_btn.png", region=br_region)
        if close_coords:
            pyautogui.click(close_coords)
            time.sleep(0.2)
            return True
        return False

    def detect_grade_PRECISION(self):
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

    def handle_bp_protection(self):
        if not self.running:
            return False
        btn_coords = self.find_template_coords("bp_btn.png")
        if not btn_coords:
            return False
        pyautogui.click(btn_coords)
        time.sleep(0.5)
        slider_coords = self.find_template_coords("bp_slider.png")
        if slider_coords:
            pyautogui.moveTo(slider_coords)
            pyautogui.dragRel(500, 0, duration=0.2, button='left')
            time.sleep(0.3)
            confirm_coords = self.find_template_coords("bp_confirm.png")
            if confirm_coords:
                pyautogui.click(confirm_coords)
                time.sleep(0.5)
                return True
        return False

    def find_and_click_green_button(self, region_type="next"):
        self.clear_achievement_popup()
        x1, y1, x2, y2 = self.rect
        w, h = x2 - x1, y2 - y1
        if region_type in ["next", "continue"]:
            search_region = (x1 + int(w * 0.7), y1 + int(h * 0.85), x2, y2)
        elif region_type == "confirm":
            search_region = (x1 + int(w * 0.3), y1 + int(h * 0.5), x1 + int(w * 0.7), y1 + int(h * 0.8))
        else:
            search_region = (x1 + int(w * 0.7), y1 + int(h * 0.65), x2, y2)

        shot = ImageGrab.grab(bbox=search_region)
        shot_cv = np.array(shot)
        hsv = cv2.cvtColor(shot_cv, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, np.array([40, 150, 150]), np.array([80, 255, 255]))

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for cnt in contours:
            if cv2.contourArea(cnt) > 800:
                M = cv2.moments(cnt)
                if M["m00"] != 0:
                    cX = int(M["m10"] / M["m00"]) + search_region[0]
                    cY = int(M["m01"] / M["m00"]) + search_region[1]
                    pyautogui.click(cX, cY, clicks=3 if region_type == "upgrade" else 1, interval=0.1)
                    return True
        return False

    # ===================== FODDER SCAN =====================

    def _scan_fodder_with_threshold(self, thresh_img, fodder_region, target_counts, current_cycle_fodder):
        data = pytesseract.image_to_data(
            thresh_img,
            config='--psm 11 -c tessedit_char_whitelist=0123456789',
            output_type=pytesseract.Output.DICT
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

    # ===================== BUY HELPER (dùng trong cả 2 luồng) =====================

    def _fill_input(self, cx, cy, val):
        if not self.running:
            return
        pyautogui.click(cx, cy)
        time.sleep(0.15)
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.1)
        pyautogui.write(str(val), interval=0.04)
        time.sleep(0.15)
        pyautogui.press('enter')

    def _do_buy_loop(self, target_ovr, target_price, remaining_qty,
                     price_pos, qty_pos, popup_region, bottom_right_region,
                     log_fail_once=False):
        """
        Vòng lặp mua hàng loạt. Trả về (actual_bought, success, should_stop).
        """
        buy_success = False
        has_logged_fail = False
        actual_bought = 0

        def _find_confirm():
            c = self.find_template_coords("btn_xac_nhan.png", region=popup_region, threshold=0.7)
            return c or self.find_template_coords("bp_confirm.png", region=popup_region, threshold=0.7)

        def _wait_confirm(timeout=2.0):
            """Chờ nút xác nhận hiện ra, trả về coords hoặc None."""
            deadline = time.time() + timeout
            while time.time() < deadline:
                if not self.running:
                    return None
                c = _find_confirm()
                if c:
                    return c
                time.sleep(0.05)
            return None

        def _wait_confirm_gone(timeout=2.0):
            """Chờ nút xác nhận biến mất."""
            deadline = time.time() + timeout
            while time.time() < deadline:
                if not self.running:
                    return
                if not _find_confirm():
                    return
                time.sleep(0.05)

        while not buy_success and self.running:
            green_buy_btn = self.find_template_coords("btn_mua_hang_loat_green.png", region=bottom_right_region)
            if green_buy_btn:
                pyautogui.click(green_buy_btn)
            else:
                time.sleep(0.1)
                continue

            # Chờ popup xác nhận lần 1 hiện ra
            confirm_btn1 = _wait_confirm(timeout=2.0)
            if not confirm_btn1:
                continue

            pyautogui.click(confirm_btn1)
            _wait_confirm_gone(timeout=2.0)

            # Chờ kết quả: btn_nhan_ngay (thành công) hoặc btn_xac_nhan (thất bại)
            outcome = None
            deadline = time.time() + 8.0
            while time.time() < deadline:
                if not self.running:
                    break
                if self.find_template_coords("btn_nhan_ngay.png", region=popup_region):
                    outcome = "success"
                    break
                if _find_confirm():
                    outcome = "fail"
                    break
                time.sleep(0.05)

            if outcome == "fail":
                if log_fail_once and not has_logged_fail:
                    self.log("❌ Mua thất bại! Đang spam ...", "fail")
                    has_logged_fail = True
                # Click ngay nút xác nhận thất bại (đã detect ở trên → không cần tìm lại)
                fail_btn = _find_confirm()
                if fail_btn:
                    pyautogui.click(fail_btn)
                    _wait_confirm_gone(timeout=2.0)
                continue

            elif outcome == "success":
                nhan_ngay_btn = self.find_template_coords("btn_nhan_ngay.png", region=popup_region)
                if nhan_ngay_btn:
                    pyautogui.click(nhan_ngay_btn)
                buy_success = True
                time.sleep(1.0)
            else:
                return 0, False, True

        if not self.running:
            return 0, False, False

        # Đọc số lượng đã mua bằng OCR
        anchor_box = None
        for _ in range(20):
            if not self.running:
                break
            anchor_box = self.get_template_box("amount_anchor.png", region=popup_region)
            if anchor_box:
                break
            time.sleep(0.1)

        if anchor_box:
            ax, ay, aw, ah = anchor_box
            scan_qty_region = (ax + aw - 5, ay - 8, ax + aw + 60, ay + ah + 8)
            shot = ImageGrab.grab(bbox=scan_qty_region)
            img_np = cv2.resize(np.array(shot), None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            text = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()
            try:
                actual_bought = int(text)
            except ValueError:
                self.log("❌ Lỗi OCR. DỪNG!", "fail")
                self.running = False
                return 0, False, True
        else:
            self.log("❌ Lỗi Anchor. DỪNG!", "fail")
            self.running = False
            return 0, False, True

        final_confirm = _find_confirm()
        if final_confirm:
            pyautogui.click(final_confirm)
            time.sleep(1.0)

        return actual_bought, True, False

