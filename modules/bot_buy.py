"""
bot_buy.py - Logic Auto Mua Phôi độc lập
"""
import time
import pyautogui


class BuyFodderMixin:
    """
    Mixin chứa logic run_buy_fodder() cho chức năng Auto Mua Phôi độc lập.
    Kế thừa bởi FCOnlineBot.
    """

    def run_buy_fodder(self, buy_data):
        """Luồng chính: Auto Mua Phôi (độc lập, không đập thẻ)."""
        self.running = True
        if not self.arrange_game():
            self.log("❌ Ko thấy game FC Online!", "fail")
            self.running = False
            self.on_finished()
            return

        self.log("\n=========================", "cyan")
        self.log(" BẮT ĐẦU", "gold")

        x1, y1, x2, y2 = self.rect
        w, h = x2 - x1, y2 - y1

        top_right_region = (x1 + w // 2, y1, x2, y1 + h // 2)
        bottom_right_region = (x1 + int(w * 0.7), y1 + int(h * 0.7), x2, y2)
        popup_region = (x1 + int(w * 0.2), y1 + int(h * 0.2), x1 + int(w * 0.8), y2 - int(h * 0.05))

        for row_idx, row in enumerate(buy_data):
            if not self.running:
                break

            target_ovr = int(row["ovr"])
            target_price = str(int(row["price"]) * 10)
            original_qty = int(row["qty"])
            remaining_qty = original_qty

            self.log(f"\n----- MUA PHÔI {target_ovr} -----", "header")

            # Tìm và click tab "Mua hàng loạt"
            btn_buy_coords = self.find_template_coords("btn_mua_hang_loat.png", region=top_right_region)
            if btn_buy_coords:
                pyautogui.click(btn_buy_coords)
                time.sleep(5.0)
            else:
                self.log("❌ Không tìm thấy tab 'Mua hàng loạt'. Bỏ qua dòng này.", "fail")
                continue

            # Tìm anchor vị trí OVR min/max
            anchor1_coords = self.find_template_coords("anchor1.png", region=top_right_region)
            anchor2_coords = self.find_template_coords("anchor2.png", region=top_right_region)

            if anchor1_coords:
                ovr_min_pos = (anchor1_coords[0], anchor1_coords[1] + 45)
            else:
                ovr_min_pos = (x1 + int(w * 0.73), y1 + int(h * 0.46))

            if anchor2_coords:
                ovr_max_pos = (anchor2_coords[0], anchor2_coords[1] + 45)
            else:
                ovr_max_pos = (x1 + int(w * 0.88), y1 + int(h * 0.46))

            # Điền OVR: max → min → max để tránh lỗi validate
            self._fill_input(ovr_max_pos[0], ovr_max_pos[1], target_ovr)
            if not self.running:
                return
            time.sleep(4.0)
            self._fill_input(ovr_min_pos[0], ovr_min_pos[1], target_ovr)
            if not self.running:
                return
            time.sleep(4.0)
            self._fill_input(ovr_max_pos[0], ovr_max_pos[1], target_ovr)
            if not self.running:
                return
            time.sleep(4.0)

            price_pos = (x1 + int(w * 0.82), y1 + int(h * 0.58))
            qty_pos = (x1 + int(w * 0.915), y1 + int(h * 0.66))

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

                if should_stop or not self.running:
                    break

                remaining_qty -= actual_bought
                if remaining_qty > 0 and self.running:
                    self.log(
                        f"🔄 Đã mua được {actual_bought}. Còn thiếu {remaining_qty} phôi. Đang mua tiếp...",
                        "orange"
                    )

            if self.running and remaining_qty <= 0:
                bought_amount = original_qty - max(0, remaining_qty)
                self.log(f"✅ Đã mua đủ: {bought_amount}/{original_qty} phôi OVR {target_ovr}.", "success")

        if self.running:
            self.log("\n=========================", "cyan")
            self.log(" KẾT THÚC", "gold")

        self.running = False
        # Alarm thông báo trước (schedule qua root.after)
        self.trigger_success_alarm(0, custom_msg="Mua phôi hoàn tất !!!")
        # Reset UI sau (cũng schedule qua root.after → chạy SAU alarm)
        self.on_finished()
