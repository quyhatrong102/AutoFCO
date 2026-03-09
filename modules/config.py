"""
config.py - Cấu hình toàn cục cho AUTO FCO
"""
import os
import warnings
import pyautogui
import pytesseract

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
warnings.filterwarnings("ignore", category=UserWarning)

# BASE_DIR là thư mục cha (chứa auto.py và thư mục lib/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAMPLE_DIR = os.path.join(BASE_DIR, "lib", "sample")

TESS_PATH = os.path.join(BASE_DIR, "lib", "Tesseract-OCR", "tesseract.exe")
if os.path.exists(TESS_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESS_PATH

pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True

# ── Dùng riêng cho bot_insert.py ──────────────────────────────────────
try:
    import mss as _mss_lib
    import threading as _threading
    import cv2 as _cv2
    from PIL import Image as _PIL_Image

    _mss_local = _threading.local()

    def mss_grab(bbox):
        if not hasattr(_mss_local, "sct"):
            _mss_local.sct = _mss_lib.mss()
        x1, y1, x2, y2 = bbox
        mon = {"left": x1, "top": y1, "width": x2 - x1, "height": y2 - y1}
        shot = _mss_local.sct.grab(mon)
        return _PIL_Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")

    _tmpl_cache: dict = {}

    def load_template(path: str):
        if path not in _tmpl_cache:
            _tmpl_cache[path] = _cv2.imread(path, _cv2.IMREAD_GRAYSCALE)
        return _tmpl_cache[path]

except ImportError:
    pass
