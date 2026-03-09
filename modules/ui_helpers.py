"""
ui_helpers.py - Các hàm tiện ích UI dùng chung cho App
"""
import tkinter as tk


def add_hover_effect(widget, hover_bg, normal_bg, hover_fg=None, normal_fg=None):
    def on_enter(e):
        if str(widget['state']) == 'normal':
            if hover_bg:
                widget.config(bg=hover_bg)
            if hover_fg:
                widget.config(fg=hover_fg)

    def on_leave(e):
        if str(widget['state']) == 'normal':
            if normal_bg:
                widget.config(bg=normal_bg)
            if normal_fg:
                widget.config(fg=normal_fg)

    widget.bind("<Enter>", on_enter)
    widget.bind("<Leave>", on_leave)


def prevent_typing(event):
    """Ngăn gõ chữ vào log, nhưng vẫn cho phép Copy (Ctrl+C) và cuộn."""
    if event.state & 0x4:
        return None
    if event.keysym in ('Up', 'Down', 'Left', 'Right', 'Prior', 'Next', 'Home', 'End'):
        return None
    return "break"


def configure_log_tags(widget):
    """Cấu hình màu sắc tag cho ScrolledText log."""
    tag_colors = [
        ("header", "#ff79c6"),
        ("cyan", "#58a6ff"),
        ("gold", "#f1c40f"),
        ("green", "#2ecc71"),
        ("orange", "#e67e22"),
        ("success", "#50fa7b"),
        ("fail", "#ff5555"),
        ("white", "#ffffff"),
    ]
    bold_tags = {"header", "success", "fail", "gold"}
    for tag, color in tag_colors:
        f_size = 11 if tag == "header" else 10
        font = ("Consolas", f_size, "bold") if tag in bold_tags else ("Consolas", f_size)
        widget.tag_config(tag, foreground=color, font=font)
