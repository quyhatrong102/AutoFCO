"""
auto.py - Entry point chính cho AUTO FCO
AUTO FCO by Quybodoivodichvutru

Cấu trúc thư mục:
  auto.py              → File chạy chính (file này)
  modules/
    admin_deps.py      → Kiểm tra quyền Admin, cài thư viện
    config.py          → Cấu hình đường dẫn, pyautogui
    bot_core.py        → FCOnlineBotBase: helpers dùng chung
    bot_upgrade.py     → UpgradeMixin: logic Auto Đập Thẻ
    bot_buy.py         → BuyFodderMixin: logic Auto Mua Phôi
    bot.py             → FCOnlineBot: tổng hợp các Mixin
    ui_helpers.py      → Tiện ích UI dùng chung
    ui_upgrade.py      → UI + logic tab Đập Thẻ
    ui_buy.py          → UI + logic tab Mua Phôi
    ui_app.py          → App chính: menu, alarm, callbacks
"""
import sys
import os

# Đảm bảo import được từ thư mục modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules"))

from admin_deps import ensure_admin, install_deps

ensure_admin()
install_deps()

import tkinter as tk
from ui_app import App

if __name__ == "__main__":
    root = tk.Tk()
    App(root)
    root.mainloop()
