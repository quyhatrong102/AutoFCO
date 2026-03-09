"""
bot_upgrade.py - Logic Auto Đập Thẻ (nâng cấp cầu thủ) (BẢN CẤP ĐỘ 1)
"""
import time
import pyautogui
import cv2
import numpy as np
import pytesseract
from PIL import ImageGrab
from collections import Counter


class UpgradeMixin:
    """
    Mixin chứa logic run() cho Auto Đập Thẻ.
    """

    def _run_single_buy_for_upgrade(self, target_ovr, config):
        """Mua phôi tự động khi hết phôi trong lúc đập thẻ."""
        target_ovr = int(target_ovr)
        target_price = str(int(config["price"]) * 10)
        target_qty = min(max(int(config["qty"]), 1), 10)

        x1, y1, x2, y2 = self.rect
        w, h = x2 - x1, y2 - y1
        top_right_region    = (x1 + w // 2, y1, x2, y1 + h // 2)
        bottom_right_region = (x1 + int(w * 0.7), y1 + int(h * 0.7), x2, y2)
        popup_region        = (x1 + int(w * 0.2), y1 + int(h * 0.2), x1 + int(w * 0.8), y2 - int(h * 0.05))

        btn_buy_coords = self.find_template_coords("btn_mua_hang_loat.png", region=top_right_region)
        if not btn_buy_coords:
            self.log("❌ Không tìm thấy tab 'Mua hàng loạt'.", "fail")
            return False

        pyautogui.click(btn_buy_coords)
        time.sleep(4.0)

        anchor1_coords = self.find_template_coords("anchor1.png", region=top_right_region)
        anchor2_coords = self.find_template_coords("anchor2.png", region=top_right_region)
        ovr_min_pos = (anchor1_coords[0], anchor1_coords[1] + int(h * 0.04)) if anchor1_coords else (x1 + int(w * 0.73), y1 + int(h * 0.46))
        ovr_max_pos = (anchor2_coords[0], anchor2_coords[1] + int(h * 0.04)) if anchor2_coords else (x1 + int(w * 0.88), y1 + int(h * 0.46))

        self._fill_input(ovr_max_pos[0], ovr_max_pos[1], target_ovr)
        if not self.running: return False
        time.sleep(4.0)
        self._fill_input(ovr_min_pos[0], ovr_min_pos[1], target_ovr)
        if not self.running: return False
        time.sleep(4.0)
        self._fill_input(ovr_max_pos[0], ovr_max_pos[1], target_ovr)
        if not self.running: return False
        time.sleep(4.0)

        price_pos = (x1 + int(w * 0.82),  y1 + int(h * 0.58))
        qty_pos   = (x1 + int(w * 0.915), y1 + int(h * 0.66))

        original_qty  = target_qty
        remaining_qty = target_qty

        self.log(f"\n----- MUA PHÔI {target_ovr} -----", "header")

        while remaining_qty > 0 and self.running:
            current_buy_qty = min(remaining_qty, 10)

            self._fill_input(price_pos[0], price_pos[1], target_price)
            time.sleep(0.5)
            self._fill_input(qty_pos[0], qty_pos[1], current_buy_qty)
            time.sleep(0.5)

            actual_bought, success, should_stop = self._do_buy_loop(
                target_ovr, target_price, current_buy_qty,
                price_pos, qty_pos, popup_region, bottom_right_region,
                log_fail_once=True
            )
            if should_stop: return False
            if not self.running: return False
            remaining_qty -= actual_bought
            if remaining_qty > 0 and self.running:
                self.log(f"🔄 Đã mua được {actual_bought}. Còn thiếu {remaining_qty} phôi. Đang mua tiếp...", "orange")

        if self.running and remaining_qty <= 0:
            bought = original_qty - max(0, remaining_qty)
            self.log(f"✅ Đã mua đủ: {bought}/{original_qty} phôi OVR {target_ovr}.", "success")

        return remaining_qty <= 0 and self.running

    # ================= LOGIC AUTO ĐẬP THẺ CHÍNH =================
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
                if self.find_and_click_green_button(region_type="continue"):
                    time.sleep(1.0)
                    continue
                break

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

            self.clear_achievement_popup()
            x1, y1, x2, y2 = self.rect
            w, h = x2 - x1, y2 - y1
            
            # CẤP ĐỘ 1: Chuyển Vùng Phôi thành tỷ lệ tương đối tuyệt đối
            fodder_region = (x1 + int(w * 0.48) - 15, y1 + int(h * 0.14) - 15, x2 - 5, y2 - int(h * 0.08))

            pyautogui.moveTo(x1 + int(w * 0.75), y1 + int(h * 0.5))
            pyautogui.rightClick()
            time.sleep(0.5)

            target_counts = Counter(needed_ovrs)
            shot    = ImageGrab.grab(bbox=fodder_region)
            img_res = cv2.resize(cv2.cvtColor(np.array(shot), cv2.COLOR_RGB2BGR), None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            gray    = cv2.cvtColor(img_res, cv2.COLOR_BGR2GRAY)

            _, t_bin = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
            self._scan_fodder_with_threshold(t_bin, fodder_region, target_counts, current_cycle_fodder)

            if self.running and any(target_counts.values()):
                last_hash_up = None
                for _ in range(20):
                    if not self.running: break
                    self.clear_achievement_popup()
                    img_check    = ImageGrab.grab(bbox=fodder_region)
                    curr_hash_up = cv2.resize(cv2.cvtColor(np.array(img_check), cv2.COLOR_RGB2GRAY), (60, 60))
                    if last_hash_up is not None and np.mean(cv2.absdiff(last_hash_up, curr_hash_up)) < 1.0: break
                    last_hash_up = curr_hash_up
                    for _ in range(10): pyautogui.scroll(100)
                    time.sleep(0.15)
                time.sleep(0.3)

                last_hash = None
                for scroll_attempt in range(30):
                    if not self.running or not any(target_counts.values()): break
                    self.clear_achievement_popup()

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
                    for _ in range(10): pyautogui.scroll(-100)
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
                        top_half = (x1, y1, x2, y1 + int(h * 0.5))
                        tab_nk = self.find_template_coords("trang_nang_cap.png", region=top_half)
                        if tab_nk:
                            pyautogui.click(tab_nk)
                            time.sleep(1.5)
                        else:
                            self.log("⚠️ Không tìm thấy tab Nâng cấp, thử rightClick...", "orange")
                            pyautogui.moveTo(x1 + int(w * 0.75), y1 + int(h * 0.5))
                            pyautogui.rightClick()
                            time.sleep(1.0)
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
            if self.find_and_click_green_button(region_type="next"):
                time.sleep(1.5)
                tien_hanh_btn = self.find_template_coords("btn_tien_hanh.png")
                if tien_hanh_btn:
                    pyautogui.click(tien_hanh_btn)
                    time.sleep(1.0)

                confirmed = False
                upgrade_clicked = False

                for i in range(15):
                    if not self.running: break
                    if self.find_and_click_green_button(region_type="confirm"):
                        confirmed = True
                        break
                    if self.find_and_click_green_button(region_type="upgrade"):
                        upgrade_clicked = True
                        break
                    time.sleep(0.5)

                if confirmed and not upgrade_clicked:
                    time.sleep(1.0)
                    for i in range(40):
                        if not self.running: break
                        if self.find_and_click_green_button(region_type="upgrade"):
                            upgrade_clicked = True
                            break
                        time.sleep(0.5)

                if upgrade_clicked:
                    popup_region = (x1 + int(w * 0.2), y1 + int(h * 0.2), x1 + int(w * 0.8), y2 - int(h * 0.05))
                    dismiss_btn = None
                    for _pc in range(6):
                        if not self.running: break
                        dismiss_btn = self.find_template_coords("btn_xac_nhan2.png", region=popup_region, threshold=0.7)
                        if dismiss_btn: break
                        time.sleep(0.4)
                    if dismiss_btn:
                        pyautogui.click(dismiss_btn)
                        self.log("⚠️ Popup chặn → Đã đóng, chọn lại phôi...", "orange")
                        time.sleep(0.5)
                        continue

                if upgrade_clicked:
                    self.upgrade_triggered = True
                    self.fodder_consumed.update(current_cycle_fodder)

# Bỏ qua animation
                    skip_reg = (x1 + int(w * 0.5), y1 + int(h * 6 / 7), x2, y2)
                    max_skips = 2 if self.has_used_bp_in_cycle else 1
                    for s_count in range(max_skips):
                        if not self.running: break
                        for skip_idx in range(15):
                            if not self.running: break
                            
                            # --- CHÈN CODE DEBUG VÀO ĐÂY ---
                            s_shot = ImageGrab.grab(bbox=skip_reg)
                            s_shot.save("debug_skip_region.png") # Ảnh sẽ lưu ở thư mục chứa tool
                            # -------------------------------
                            
                            s_gray = cv2.cvtColor(np.array(s_shot), cv2.COLOR_RGB2GRAY)
                            _, s_thresh = cv2.threshold(s_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                            txt_s = pytesseract.image_to_string(s_thresh, config='--psm 7').lower()
                            
                            if any(k in txt_s for k in ["qua", "skip", "bo"]):
                                pyautogui.press('space')
                                time.sleep(1.0)
                                break
                            time.sleep(0.5)

                    max_continues = 2 if self.has_used_bp_in_cycle else 1
                    for c_count in range(max_continues):
                        if not self.running: break
                        btn_found = False
                        for wait_idx in range(15):
                            if not self.running: break
                            if self.find_and_click_green_button(region_type="continue"):
                                btn_found = True
                                if c_count == 0:
                                    time.sleep(1.2)
                                    res_grade = self.detect_grade_PRECISION()
                                    if res_grade == self.last_target_grade:
                                        self.grade_success[res_grade] += 1
                                        self.log_update(self.last_log_pos, ": THÀNH CÔNG", "success")
                                    else:
                                        self.grade_fail[self.last_target_grade] += 1
                                        self.log_update(self.last_log_pos, f": THẤT BẠI VỀ +{res_grade}", "fail")
                                else:
                                    time.sleep(0.2)
                                break
                            time.sleep(0.3)

                        if not btn_found:
                            if self.running: self.log("LỖI: Hết thời gian chờ kết quả đập thẻ", "fail")
                            break
                else:
                    self.log("LỖI: Không tìm thấy nút Nâng cấp để click.", "fail")
                    break
            else:
                self.log("LỖI: Không tìm thấy nút Tiếp theo.", "fail")
                break

        self.on_finished(summary_data=(self.total_cycles, self.grade_success, self.grade_fail, self.fodder_consumed))