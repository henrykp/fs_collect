import traceback
import logging
from typing import Optional

import wmi
import win32gui
import win32process

c = wmi.WMI()


def get_app_name(hwnd) -> Optional[str]:
    """Get application filename given hwnd."""
    name = None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    for p in c.query('SELECT Name FROM Win32_Process WHERE ProcessId = %s' % str(pid)):
        name = p.Name
        break
    return name


def get_window_title(hwnd) -> str:
    return win32gui.GetWindowText(hwnd)


def get_active_window_handle():
    hwnd = win32gui.GetForegroundWindow()
    return hwnd


def get_current_active_window() -> dict:
    app, title = None, None
    try:
        window_handle = get_active_window_handle()
        app = get_app_name(window_handle)
        title = get_window_title(window_handle)
    except Exception as e:
        logging.warning(e)
        traceback.print_exc()

    if app is None:
        app = "unknown"
    if title is None:
        title = "unknown"

    return {"app_name": app, "title": title}
