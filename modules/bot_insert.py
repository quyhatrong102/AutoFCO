"""
bot_insert.py - Logic Auto Chèn / Săn Cầu Thủ Đỉnh Cao (Mù Ảnh)
"""
import time
import pyautogui
import cv2
import numpy as np
import pytesseract
from PIL import ImageGrab

class InsertMixin:

    def run_insert(self):
        self.running = True
        if not self.arrange_game():
            self.log("❌ Không tìm thấy cửa sổ game!")
            self.running = False
            self.on_finished()
            return

        self.log(f"🚀 Bắt đầu spam chèn Slot {self.target_slot} (Mua {'Max' if self.is_max else 'Min'})", "header")
        x1, y1, _, _ = self.rect

        # Tọa độ Slot 1-11
        idx = max(1, min(self.target_slot, 11)) - 1
        slot_x = 1000
        slot_y = 214 + (idx * 40)

        while self.running:
            # 1. Click thẳng vào Slot
            pyautogui.click(x1 + slot_x, y1 + slot_y)
            
            # 2. Chờ popup hiện ra (Check nút Hủy đổi màu)
            popup_opened = self.hover_and_wait_color(997, 587, "353838", timeout=2.0, click_if_match=False)
            
            if popup_opened:
                # 3. Đọc giá Min/Max hiện tại trên popup
                if self.is_max:
                    scan_reg = (x1 + 906, y1 + 311, x1 + 1041, y1 + 331)
                else:
                    scan_reg = (x1 + 908, y1 + 319, x1 + 1043, y1 + 340)
                    
                shot = ImageGrab.grab(bbox=scan_reg)
                img_np = cv2.resize(np.array(shot), None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
                gray = cv2.cvtColor(img_np, cv2.COLOR_RGB2GRAY)
                _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
                val_str = pytesseract.image_to_string(thresh, config='--psm 7 -c tessedit_char_whitelist=0123456789').strip()
                
                try:
                    current_price = int(val_str)
                except ValueError:
                    current_price = -1
                    
                # 4. Kiểm tra và Chớp thời cơ
                if current_price > 0 and current_price == int(self.target_price):
                    self.log(f"⚡ Đã thấy giá {current_price}! Đang xúc...", "green")
                    
                    if self.is_max:
                        # Click Chèn Max
                        self.hover_and_wait_color(875, 588, "D03C23", timeout=1.0, click_if_match=True)
                    else:
                        # Click Chèn Min
                        self.hover_and_wait_color(876, 618, "0C8FF3", timeout=1.0, click_if_match=True)
                        
                    # Ấn Xác Nhận đơn mua
                    time.sleep(0.5)
                    pyautogui.press('enter')
                    time.sleep(1.0)
                else:
                    # Giá chưa đúng -> Click Hủy để đóng popup (Đây cũng chính là F5 tự nhiên)
                    pyautogui.click(x1 + 997, y1 + 587)
                    
            # Tốc độ Spam (Có thể chỉnh thấp hơn nếu mạng khỏe)
            time.sleep(0.2)

        self.on_finished()