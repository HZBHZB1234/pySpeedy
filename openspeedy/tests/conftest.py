"""
Shared test fixtures and mocks for openspeedy tests.

All tests can run on any platform — Windows API calls are mocked via
``unittest.mock`` so that we can verify logic without requiring a real
Windows environment.
"""

import sys
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Platform guard override — allow importing openspeedy on non-Windows
# for test purposes
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _mock_platform_win32():
    """Make ``sys.platform`` report ``"win32"`` so that the package-level
    platform guard does not block imports during testing."""
    with patch.object(sys, "platform", "win32"):
        yield


# ---------------------------------------------------------------------------
# Mock ctypes DLL handles
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_kernel32():
    """Return a ``MagicMock`` standing in for ``kernel32.dll``."""
    mock = MagicMock()
    mock.OpenProcess.return_value = 0x1000  # fake handle
    mock.CloseHandle.return_value = True
    mock.VirtualAllocEx.return_value = 0x20000000
    mock.VirtualFreeEx.return_value = True
    mock.WriteProcessMemory.return_value = True
    mock.CreateRemoteThread.return_value = 0x3000
    mock.WaitForSingleObject.return_value = 0  # WAIT_OBJECT_0
    mock.GetExitCodeThread.return_value = True
    mock.CreateToolhelp32Snapshot.return_value = 0x4000
    mock.IsWow64Process.return_value = True
    mock.QueryFullProcessImageNameW.return_value = True
    mock.GetModuleHandleW.return_value = 0x5000
    mock.LoadLibraryW.return_value = 0x6000
    mock.GetProcAddress.return_value = 0x7000
    mock.CreateFileMappingW.return_value = 0x8000
    mock.OpenFileMappingW.return_value = 0x9000
    mock.MapViewOfFile.return_value = 0xA0000000
    mock.UnmapViewOfFile.return_value = True
    return mock


@pytest.fixture
def mock_user32():
    """Return a ``MagicMock`` standing in for ``user32.dll``."""
    mock = MagicMock()
    mock.EnumWindows.return_value = True
    mock.IsWindowVisible.return_value = True
    mock.GetWindowThreadProcessId.return_value = 42
    mock.GetWindowTextLengthW.return_value = 5
    mock.GetWindowTextW.return_value = 5
    mock.GetParent.return_value = 0
    return mock


@pytest.fixture
def mock_psapi():
    """Return a ``MagicMock`` standing in for ``psapi.dll``."""
    mock = MagicMock()
    mock.GetProcessMemoryInfo.return_value = True
    return mock


@pytest.fixture
def mock_advapi32():
    """Return a ``MagicMock`` standing in for ``advapi32.dll``."""
    mock = MagicMock()
    mock.OpenProcessToken.return_value = True
    mock.GetTokenInformation.return_value = True
    return mock


@pytest.fixture
def mock_speedpatch_dll():
    """Return a ``MagicMock`` standing in for the speedpatch DLL."""
    mock = MagicMock()
    mock.SP_GetSpeed.return_value = 1.0
    mock.SP_SetSpeed.return_value = None
    mock.SP_Enable.return_value = None
    mock.SP_Disable.return_value = None
    mock.SP_IsEnabledById.return_value = 1  # TRUE
    mock.SP_IsEnabled.return_value = 1  # TRUE
    return mock


@pytest.fixture
def sample_processes():
    """Sample ``ProcessInfo`` list for testing."""
    from openspeedy._types import ProcessInfo

    return [
        ProcessInfo(pid=4, name="System", arch="x64"),
        ProcessInfo(pid=100, name="notepad.exe", arch="x64",
                    window_title="Untitled - Notepad", memory_kb=8192,
                    exe_path="C:\\Windows\\System32\\notepad.exe"),
        ProcessInfo(pid=200, name="game.exe", arch="x86",
                    window_title="My Game", memory_kb=524288,
                    exe_path="C:\\Games\\game.exe", is_admin=True),
    ]
