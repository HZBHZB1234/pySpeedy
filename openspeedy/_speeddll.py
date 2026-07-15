"""
ctypes wrapper around the speedpatch DLL.

Loads the DLL matching the Python interpreter's architecture and provides
typed wrappers for all exported ``SP_*`` functions.

The DLL is loaded lazily on first use (thread-safe singleton) so that
importing the package does not immediately require the native DLL to be
present.
"""

import ctypes
import threading
from typing import Optional

from ._constants import SPEED_DEFAULT, SPEED_MAX, SPEED_MIN
from ._dll_resolver import _get_own_dll_path
from ._exceptions import DLLNotFoundError, SpeedControlError, SpeedRangeError

# ---------------------------------------------------------------------------
# Lazy singleton
# ---------------------------------------------------------------------------

_SPEED_DLL: Optional[ctypes.CDLL] = None
_SPEED_DLL_LOCK = threading.Lock()


def _get_speed_dll() -> ctypes.CDLL:
    """Load (if needed) and return the speedpatch DLL.

    Thread-safe.  Uses double-checked locking.
    """
    global _SPEED_DLL
    if _SPEED_DLL is None:
        with _SPEED_DLL_LOCK:
            if _SPEED_DLL is None:
                dll_path = _get_own_dll_path()
                # CDLL is correct here — the exports use __cdecl (x86) or
                # the unified x64 convention.  WinDLL would assume __stdcall.
                dll = ctypes.CDLL(str(dll_path))
                _setup_dll_exports(dll)
                _SPEED_DLL = dll
    return _SPEED_DLL


def _setup_dll_exports(dll: ctypes.CDLL) -> None:
    """Define argtypes and restype for every exported ``SP_*`` function."""

    # SP_SetSpeed(double factor)
    dll.SP_SetSpeed.argtypes = [ctypes.c_double]
    dll.SP_SetSpeed.restype = None

    # SP_GetSpeed() -> double
    dll.SP_GetSpeed.argtypes = []
    dll.SP_GetSpeed.restype = ctypes.c_double

    # SP_Enable(DWORD processId)
    dll.SP_Enable.argtypes = [ctypes.c_uint32]
    dll.SP_Enable.restype = None

    # SP_Disable(DWORD processId)
    dll.SP_Disable.argtypes = [ctypes.c_uint32]
    dll.SP_Disable.restype = None

    # SP_IsEnabledById(DWORD processId) -> BOOL
    # BOOL is a 4-byte int, NOT c_bool (1 byte)!
    dll.SP_IsEnabledById.argtypes = [ctypes.c_uint32]
    dll.SP_IsEnabledById.restype = ctypes.c_int

    # SP_IsEnabled() -> BOOL
    dll.SP_IsEnabled.argtypes = []
    dll.SP_IsEnabled.restype = ctypes.c_int


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_factor(factor: float) -> None:
    """Raise :exc:`SpeedRangeError` if *factor* is out of bounds."""
    if factor <= 0 or factor < SPEED_MIN or factor > SPEED_MAX:
        raise SpeedRangeError(factor)


# ---------------------------------------------------------------------------
# Public convenience wrappers
# ---------------------------------------------------------------------------


def set_speed(factor: float) -> None:
    """Set the global speed multiplier.

    Written to the DLL's shared data section; all injected processes
    see the update immediately.

    Args:
        factor: Speed multiplier.  1.0 = normal, 2.0 = double,
            0.5 = half.  Must be in ``[0.001, 1000.0]``.
    """
    _validate_factor(factor)
    dll = _get_speed_dll()
    dll.SP_SetSpeed(factor)


def get_speed() -> float:
    """Read the current global speed factor from the DLL's shared section.

    Returns:
        The current speed multiplier (default 1.0).
    """
    dll = _get_speed_dll()
    return dll.SP_GetSpeed()


def enable(pid: int) -> None:
    """Enable speed hooks for a specific process.

    The process must already have the speedpatch DLL injected.

    Args:
        pid: Target process ID.
    """
    dll = _get_speed_dll()
    dll.SP_Enable(pid)


def disable(pid: int) -> None:
    """Disable speed hooks for a specific process.

    When disabled, the injected DLL still intercepts calls, but
    ``SpeedFactor()`` returns 1.0 (no speed modification).

    Args:
        pid: Target process ID.
    """
    dll = _get_speed_dll()
    dll.SP_Disable(pid)


def is_enabled(pid: int) -> bool:
    """Check whether speed hooks are enabled for a process.

    Args:
        pid: Target process ID.

    Returns:
        ``True`` if speed control is enabled for the process.
    """
    dll = _get_speed_dll()
    return dll.SP_IsEnabledById(pid) != 0


def is_dll_loaded() -> bool:
    """Return ``True`` if the speedpatch DLL has been loaded into the
    current Python process."""
    return _SPEED_DLL is not None
