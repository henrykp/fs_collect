import ctypes
from ctypes import Structure, POINTER, WINFUNCTYPE, windll  # type: ignore
from ctypes.wintypes import BOOL, UINT, DWORD  # type: ignore

import traceback
import logging
from typing import Optional

import wmi
import win32gui
import win32process


def get_app_name(hwnd) -> Optional[str]:
    """Get application filename given hwnd."""
    name = None
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    c = wmi.WMI()
    q = 'SELECT Name FROM Win32_Process WHERE ProcessId = %s' % str(pid)
    print(f'Query: {q}')
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


class LastInputInfo(Structure):
    _fields_ = [
        ("cbSize", UINT),
        ("dwTime", DWORD)
    ]


def _getLastInputTick() -> int:
    prototype = WINFUNCTYPE(BOOL, POINTER(LastInputInfo))
    paramflags = ((1, "lastinputinfo"), )
    c_GetLastInputInfo = prototype(("GetLastInputInfo", ctypes.windll.user32), paramflags)  # type: ignore

    l = LastInputInfo()
    l.cbSize = ctypes.sizeof(LastInputInfo)
    assert 0 != c_GetLastInputInfo(l)
    return l.dwTime


def _getTickCount() -> int:
    prototype = WINFUNCTYPE(DWORD)
    paramflags = ()
    c_GetTickCount = prototype(("GetTickCount", ctypes.windll.kernel32), paramflags)  # type: ignore
    return c_GetTickCount()


def seconds_since_last_input():
    seconds_since_input = (_getTickCount() - _getLastInputTick()) / 1000
    return seconds_since_input
