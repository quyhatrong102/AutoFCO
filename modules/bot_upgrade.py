"""
bot_upgrade.py - Logic Auto Đập Thẻ (nâng cấp cầu thủ) (Tọa độ tuyệt đối)
"""
import time
import pyautogui
import cv2
import numpy as np
import pytesseract
from PIL import ImageGrab
from collections import Counter


class UpgradeMixin:

    def _run_single_buy_for_upgrade(self, target_ovr, config):
        target_ovr = int(target_ovr)
        target_price = str(int(config["price"]) * 10)
        target_qty = min(max(int(config["qty"]), 1), 10)
        x1, y1, _, _ = self.rect

        # Click Tab Mua hàng loạt
        pyautogui.click(x1 + 914, y1 + 140)
        time.sleep(4.0)

        # Điền Input bằng tọa độ tĩnh
        self._fill_input(x1 + 1068, y1 + 327, target_ovr) # Max
        if not self.running: return False
        time.sleep(1.0)
        self._fill_input(x1 + 976, y1 + 327, target_ovr) # Min
        if not self.running: return False
        time.sleep(1.0)
        self._fill_input(x1 + 1068, y1 + 327, target_ovr) # Gõ lại max cho chắc
        if not self.running: return False
        time.sleep(1.0)

        original_qty  = target_qty
        remaining_qty = target_qty

        self.log(f"\n----- MUA PHÔI {target_ovr} -----", "header")

        while remaining_qty > 0 and self.running:
            current_buy_qty = min(remaining_qty, 10)

            self._fill_input(x1 + 946, y1 + 448, target_price)
            time.sleep(0.5)
            self._fill_input(x1 + 1050, y1 + 508, current_buy_qty)
            time.sleep(0.5)

            actual_bought, success, should_stop = self._do_buy_loop(
                target_ovr, target_price, current_buy_qty, log_fail_once=True
            )
            
            if should_stop or not self.running: return False
            remaining_qty -= actual_bought
            if remaining_qty > 0 and self.running:
                self.log(f"🔄 Đã mua được {actual_bought}. Còn thiếu {remaining_qty} phôi. Đang mua tiếp...", "orange")

        if self.running and remaining_qty <= 0:
            bought = original_qty - max(0, remaining_qty)
            self.log(f"✅ Đã mua đủ: {bought}/{original_qty} phôi OVR {target_ovr}.", "success")

        return remaining_qty <= 0 and self.running

    def run(self):
        self.running = True
        if not self.arrange_game():
            self.log("❌ Ko thấy game!")
            self.running = False
            self.on_finished()
            return

        while self.running:
            current_cycle_fodder = Counter()
            current_grade = -1
            self.has_used_bp_in_cycle = False

            for _ in range(15):
                if not self.running: break
                current_grade = self.detect_grade_PRECISION()
                if current_grade != -1: break
                time.sleep(0.5)

            if current_grade == -1:
                # Click mù Tiếp Tục nếu bị kẹt ở màn kết quả
                x1, y1, _, _ = self.rect
                pyautogui.click(x1 + 1063, y1 + 718)
                time.sleep(1.0)
                continue

            self.update_ui_icon(current_grade)

            if current_grade >= self.target_grade:
                if self.total_cycles == 0:
                    msg = f"Cấp thẻ đang là +{current_grade} rồi." if current_grade == self.target_grade else f"Cấp thẻ hiện tại > +{self.target_grade} rồi."
                    self.log(f"\n📢 {msg}", tag="header")
                    self.on_finished(summary_data=None)
                    return
                else:
                    self.log(f"\n🎉 Đạt mục tiêu +{current_grade}!", tag="header")
                    self.trigger_success_alarm(current_grade, custom_msg=f"Thành công +{current_grade}")
                    break

            if self.bp_enabled and current_grade >= 8:
                if self.handle_bp_protection():
                    self.has_used_bp_in_cycle = True

            self.total_cycles += 1
            self.log(f"\n----- Lần {self.total_cycles} -----", tag="header")
            target_next = current_grade + 1
            self.last_target_grade = target_next
            attempt_no = self.grade_success[target_next] + self.grade_fail[target_next] + 1
            log_msg = f"Đập {current_grade} lên {target_next} (lần {attempt_no})"
            if self.has_used_bp_in_cycle: log_msg += " (Bảo vệ BP)"
            self.last_log_pos = self.log(log_msg, return_pos=True)

            needed_ovrs = self.fodder_map.get(current_grade, [])
            if not needed_ovrs: break

            x1, y1, _, _ = self.rect
            
            # Click chuột phải Reset phôi
            pyautogui.click(x1 + 834, y1 + 423, button='right')
            time.sleep(0.5)

            # Khung chữ nhật thu nhỏ cho Phôi
            fodder_region = (x1 + 869, y1 + 281, x1 + 905, y1 + 641)

            target_counts = Counter(needed_ovrs)
            shot = ImageGrab.grab(bbox=fodder_region)
            img_res = cv2.resize(cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR), None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            gray = cv2.cvtColor(img_res, cv2.COLOR_BGR2GRAY)
            _, t_bin = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            self._scan_fodder_with_threshold(t_bin, fodder_region, target_counts, current_cycle_fodder)

            if self.running and any(target_counts.values()):
                # Cuộn lên 9 nấc
                for _ in range(9): pyautogui.scroll(100)
                time.sleep(0.4)

                last_hash = None
                for scroll_attempt in range(30):
                    if not self.running or not any(target_counts.values()): break

                    s_loop = ImageGrab.grab(bbox=fodder_region)
                    i_loop = cv2.resize(cv2.cvtColor(np.array(s_loop), cv2.COLOR_RGB2BGR), None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
                    g_loop = cv2.cvtColor(i_loop, cv2.COLOR_BGR2GRAY)
                    _, t_loop = cv2.threshold(g_loop, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                    self._scan_fodder_with_threshold(t_loop, fodder_region, target_counts, current_cycle_fodder)

                    if not any(target_counts.values()): break

                    img_check = ImageGrab.grab(bbox=fodder_region)
                    curr_hash = cv2.resize(cv2.cvtColor(np.array(img_check), cv2.COLOR_RGB2GRAY), (60, 60))
                    if last_hash is not None and np.mean(cv2.absdiff(last_hash, curr_hash)) < 1.0: break
                    last_hash = curr_hash
                    
                    # Cuộn xuống 9 nấc
                    for _ in range(9): pyautogui.scroll(-100)
                    time.sleep(0.8)

            if not self.running: break

            if any(target_counts.values()):
                missing_ovr = list(target_counts.keys())[0]
                if self.auto_buy_config and missing_ovr in self.auto_buy_config:
                    self.log(f"🔄 Hết phôi {missing_ovr}. Kích hoạt Auto Mua...", "orange")
                    success = self._run_single_buy_for_upgrade(missing_ovr, self.auto_buy_config[missing_ovr])
                    if not self.running: break

                    if success:
                        self.log(f"✅ Đã mua xong phôi {missing_ovr}, quay lại đập thẻ...", "green")
                        # Quay lại trang Nâng cấp
                        pyautogui.click(x1 + 690, y1 + 143)
                        time.sleep(1.5)
                        continue
                    else:
                        self.log("❌ Auto Mua thất bại, dừng đập thẻ.", "fail")
                        self.trigger_error_alarm(missing_ovr)
                        break
                else:
                    self.log(f"❌ HẾT PHÔI {missing_ovr} !!!", tag="fail")
                    self.trigger_error_alarm(missing_ovr)
                    break

            # --- NÂNG CẤP ---
            # Click Tiếp theo
            pyautogui.click(x1 + 1028, y1 + 667)
            time.sleep(1.5)
            
            # Click Tiến hành (nếu thấy màu xanh)
            self.hover_and_wait_color(720, 522, "09D95E", timeout=1.5, click_if_match=True)

            # Click Nâng cấp
            time.sleep(1.0)
            pyautogui.click(x1 + 1027, y1 + 543)
            time.sleep(0.5)

            if self.running:
                self.upgrade_triggered = True
                self.fodder_consumed.update(current_cycle_fodder)

                # Skip Animation HCN
                skip_reg = (x1 + 1037, y1 + 666, x1 + 1123, y1 + 740)
                max_skips = 2 if self.has_used_bp_in_cycle else 1
                for s_count in range(max_skips):
                    if not self.running: break
                    for skip_idx in range(15):
                        if not self.running: break
                        s_shot = ImageGrab.grab(bbox=skip_reg)
                        s_gray = cv2.cvtColor(np.array(s_shot), cv2.COLOR_RGB2GRAY)
                        _, s_thresh = cv2.threshold(s_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                        txt_s = pytesseract.image_to_string(s_thresh, config='--psm 7').lower()
                        
                        if any(k in txt_s for k in ["qua", "skip", "bo"]):
                            pyautogui.press('space')
                            time.sleep(1.0)
                            break
                        time.sleep(0.5)

                # Chờ màn hình kết quả
                btn_found = False
                for wait_idx in range(15):
                    if not self.running: break
                    
                    # Click mù vào Tiếp tục
                    pyautogui.click(x1 + 1063, y1 + 718)
                    time.sleep(0.5)
                    
                    # Quét xem đã về màn hình thẻ chính chưa
                    res_grade = self.detect_grade_PRECISION()
                    if res_grade != -1:
                        btn_found = True
                        if res_grade == self.last_target_grade:
                            self.grade_success[res_grade] += 1
                            self.log_update(self.last_log_pos, ": THÀNH CÔNG", "success")
                        else:
                            self.grade_fail[self.last_target_grade] += 1
                            self.log_update(self.last_log_pos, f": THẤT BẠI VỀ +{res_grade}", "fail")
                        break
                    
                if not btn_found and self.running: 
                    self.log("LỖI: Hết thời gian chờ kết quả đập thẻ", "fail")
                    break

        self.on_finished(summary_data=(self.total_cycles, self.grade_success, self.grade_fail, self.fodder_consumed))