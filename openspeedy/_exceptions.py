"""
Custom exception hierarchy for the openspeedy package.

All exceptions derive from ``OpenSpeedyError``. Each exception carries the
original Windows error code (if applicable) and a human-readable message
formatted via ``ctypes.FormatError()``.
"""

import ctypes
from typing import Optional


class OpenSpeedyError(Exception):
    """Base exception for all openspeedy errors."""

    def __init__(self, message: str, win_error: Optional[int] = None) -> None:
        if win_error is not None:
            message = f"{message} (Win32 error {win_error}: {ctypes.FormatError(win_error)})"
        super().__init__(message)
        self.win_error = win_error


class PlatformNotSupportedError(OpenSpeedyError):
    """Raised when attempting to use openspeedy on a non-Windows platform."""

    def __init__(self) -> None:
        import sys

        super().__init__(
            f"openspeedy is Windows-only. Current platform: {sys.platform}"
        )


class DLLNotFoundError(OpenSpeedyError):
    """Raised when the speedpatch DLL cannot be found."""

    def __init__(self, path: str) -> None:
        super().__init__(f"Speedpatch DLL not found at: {path}")


class ProcessAccessDeniedError(OpenSpeedyError):
    """Raised when OpenProcess fails (e.g. protected system process)."""

    def __init__(self, pid: int, win_error: Optional[int] = None) -> None:
        super().__init__(
            f"Cannot access process {pid}. "
            f"It may be a protected/system process, or you may need administrator privileges.",
            win_error=win_error,
        )


class ProcessNotFoundError(OpenSpeedyError):
    """Raised when a PID does not correspond to a running process."""

    def __init__(self, pid: int) -> None:
        super().__init__(f"Process not found: PID {pid}")


class ProcessArchitectureMismatch(OpenSpeedyError):
    """Raised when trying to inject a DLL whose architecture does not match
    the target process (v1 limitation — same-arch injection only)."""

    def __init__(self, python_arch: str, target_arch: str, pid: int) -> None:
        super().__init__(
            f"Architecture mismatch: Python is {python_arch} but target process "
            f"(PID {pid}) is {target_arch}. "
            f"Use a {target_arch} Python interpreter to inject into {target_arch} processes."
        )


class InjectionError(OpenSpeedyError):
    """Raised when DLL injection fails."""

    def __init__(
        self, pid: int, reason: str, win_error: Optional[int] = None
    ) -> None:
        super().__init__(
            f"Failed to inject into process {pid}: {reason}", win_error=win_error
        )


class EjectionError(OpenSpeedyError):
    """Raised when DLL ejection fails."""

    def __init__(
        self, pid: int, reason: str, win_error: Optional[int] = None
    ) -> None:
        super().__init__(
            f"Failed to eject from process {pid}: {reason}", win_error=win_error
        )


class SpeedRangeError(OpenSpeedyError):
    """Raised when the speed factor is out of valid range."""

    def __init__(self, factor: float) -> None:
        from ._constants import SPEED_MIN, SPEED_MAX

        super().__init__(
            f"Speed factor must be between {SPEED_MIN} and {SPEED_MAX}, got {factor}"
        )


class SpeedControlError(OpenSpeedyError):
    """Raised when a speedpatch DLL operation fails at runtime."""

    def __init__(self, operation: str, reason: str = "") -> None:
        msg = f"Speed control operation '{operation}' failed"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
