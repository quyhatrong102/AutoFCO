"""
admin_deps.py - Kiểm tra quyền Admin và cài đặt thư viện phụ thuộc
"""
import os
import subprocess
import sys
import ctypes


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def ensure_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()


def install_deps():
    pkgs = {
        "pyautogui": "pyautogui",
        "cv2": "opencv-python",
        "numpy": "numpy",
        "pygetwindow": "pygetwindow",
        "PIL": "Pillow",
        "win32gui": "pywin32",
        "pytesseract": "pytesseract",
        "pygame": "pygame",
        "keyboard": "keyboard",
        "mss": "mss"
    }
    for mod, pkg in pkgs.items():
        try:
            __import__(mod)
        except ImportError:
            subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "--user", "-q"])
