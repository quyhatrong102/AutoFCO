"""
bot_buy.py - Mua phôi hàng loạt độc lập (Tọa độ tĩnh)
"""
import time
import pyautogui

class BuyFodderMixin:

    def run_buy_fodder(self, buy_data):
        self.running = True
        if not self.arrange_game():
            self.log("❌ Ko thấy game!")
            self.running = False
            self.on_finished()
            return

        x1, y1, _, _ = self.rect

        for item in buy_data:
            if not self.running:
                break

            target_ovr   = int(item["ovr"])
            target_price = str(int(item["price"]) * 10)
            target_qty   = int(item["qty"])

            self._fill_input(x1 + 1068, y1 + 327, target_ovr)
            if not self.running: break
            time.sleep(2.0)
            self._fill_input(x1 + 976, y1 + 327, target_ovr)
            if not self.running: break
            time.sleep(2.0)
            self._fill_input(x1 + 1068, y1 + 327, target_ovr)
            if not self.running: break
            time.sleep(2.0)

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
                if should_stop or not self.running:
                    break

                remaining_qty -= actual_bought
                if remaining_qty > 0 and self.running:
                    self.log(f"🔄 Đã mua được {actual_bought}. Còn thiếu {remaining_qty} phôi. Đang mua tiếp...", "orange")

            if self.running:
                bought = original_qty - max(0, remaining_qty)
                if bought >= original_qty:
                    self.log(f"✅ Đã mua đủ: {bought}/{original_qty} phôi OVR {target_ovr}.", "success")
                else:
                    self.log(f"⚠️ Dừng mua. Thực tế mua được: {bought}/{original_qty} phôi.", "orange")

        self.running = False
        self.on_finished()
