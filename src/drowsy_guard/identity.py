"""Local account-name suggestion, only requested when the user clicks autofill."""
import ctypes
from ctypes import wintypes
import os
import sys
from pathlib import Path


def clean_name(value):
    return ' '.join(''.join(c for c in value if c.isalnum() or c in " '-").split())[:24]


def device_name():
    if sys.platform == 'win32':
        buffer = ctypes.create_unicode_buffer(257)
        size = wintypes.DWORD(len(buffer))
        function = ctypes.windll.advapi32.GetUserNameW
        function.argtypes = [wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
        function.restype = wintypes.BOOL
        if function(buffer, ctypes.byref(size)):
            return clean_name(buffer.value)
    return clean_name(os.environ.get('USERNAME') or os.environ.get('USER') or Path.home().name)


def name_context(settings):
    name = clean_name(settings.get('user_name', ''))
    return {'name': name} if settings.get('personalization_enabled', False) and name else {}
