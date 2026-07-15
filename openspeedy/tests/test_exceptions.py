"""
Tests for the exception hierarchy.
"""

from openspeedy._exceptions import (
    DLLNotFoundError,
    EjectionError,
    InjectionError,
    OpenSpeedyError,
    PlatformNotSupportedError,
    ProcessAccessDeniedError,
    ProcessArchitectureMismatch,
    ProcessNotFoundError,
    SpeedControlError,
    SpeedRangeError,
)


class TestExceptionHierarchy:
    """Verify exception inheritance."""

    def test_all_inherit_from_base(self):
        for cls in [
            PlatformNotSupportedError,
            DLLNotFoundError,
            ProcessAccessDeniedError,
            ProcessNotFoundError,
            ProcessArchitectureMismatch,
            InjectionError,
            EjectionError,
            SpeedRangeError,
            SpeedControlError,
        ]:
            assert issubclass(cls, OpenSpeedyError)

    def test_base_inherits_from_exception(self):
        assert issubclass(OpenSpeedyError, Exception)


class TestExceptionMessages:
    """Verify exception messages contain useful information."""

    def test_dll_not_found(self):
        e = DLLNotFoundError("C:\\some\\path\\speedpatch64.dll")
        assert "C:\\some\\path" in str(e)

    def test_process_access_denied(self):
        e = ProcessAccessDeniedError(1234, win_error=5)
        assert "1234" in str(e)
        assert e.win_error == 5

    def test_process_not_found(self):
        e = ProcessNotFoundError(9999)
        assert "9999" in str(e)

    def test_arch_mismatch(self):
        e = ProcessArchitectureMismatch("x64", "x86", 100)
        msg = str(e)
        assert "x64" in msg
        assert "x86" in msg
        assert "100" in msg

    def test_injection_error(self):
        e = InjectionError(500, "VirtualAllocEx failed", win_error=8)
        assert "500" in str(e)
        assert e.win_error == 8

    def test_ejection_error(self):
        e = EjectionError(500, "module not found")
        assert "500" in str(e)

    def test_speed_range_error(self):
        e = SpeedRangeError(0.0)
        assert "0.0" in str(e)

    def test_speed_control_error(self):
        e = SpeedControlError("SP_SetSpeed", "DLL not loaded")
        assert "SP_SetSpeed" in str(e)
        assert "DLL not loaded" in str(e)
