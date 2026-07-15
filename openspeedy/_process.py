"""
Process enumeration and detail gathering via Windows ToolHelp API.

Maps to the Rust ``process_enumerator.rs`` module.  Provides both a fast
snapshot-only enumeration and a full enumeration that opens each process
for detail collection.
"""

import ctypes
from typing import List, Optional

from ._constants import (
    PROCESS_QUERY_INFORMATION,
    PROCESS_QUERY_LIMITED_INFORMATION,
    PROCESS_VM_READ,
    PROCESS_NAME_WIN32,
    TH32CS_SNAPPROCESS,
    TOKEN_QUERY,
    TokenElevation,
)
from ._types import ProcessInfo
from ._winapi import (
    PROCESSENTRY32W,
    PROCESS_MEMORY_COUNTERS,
    TOKEN_ELEVATION,
    advapi32,
    kernel32,
    psapi,
    user32,
    wintypes,
    _check_bool,
    _check_handle,
    _is_python_64bit,
)

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def list_processes(fast: bool = True) -> List[ProcessInfo]:
    """Enumerate all running Windows processes.

    Args:
        fast: If ``True`` (default), only snapshot data is returned.
            ``window_title`` will be ``None`` and ``memory_kb`` will be 0.
            If ``False``, each process is opened to collect window title,
            memory usage, executable path, and admin status.

    Returns:
        List of :class:`ProcessInfo` objects, sorted by PID.
    """
    procs: List[ProcessInfo] = []
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return procs

    try:
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)

        if kernel32.Process32FirstW(snapshot, ctypes.byref(entry)):
            while True:
                pid = entry.th32ProcessID
                name = entry.szExeFile.rstrip("\x00")

                if pid != 0 and name:
                    if fast:
                        # Snapshot-only: just PID, name, and arch detection
                        # (arch detection requires opening the process)
                        arch = _detect_arch_for_pid(pid)
                        procs.append(
                            ProcessInfo(pid=pid, name=name, arch=arch)
                        )
                    else:
                        procs.append(_collect_process_details(pid, name))

                if not kernel32.Process32NextW(snapshot, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)

    procs.sort(key=lambda p: p.pid)
    return procs


def get_process_arch(pid: int) -> str:
    """Detect the CPU architecture of a process.

    Returns:
        ``"x86"`` if the process is 32-bit (running under WOW64 on 64-bit
        Windows), ``"x64"`` otherwise.
    """
    return _detect_arch_for_pid(pid)


# ---------------------------------------------------------------------------
# Internal: process detail collection
# ---------------------------------------------------------------------------


def _collect_process_details(pid: int, name: str) -> ProcessInfo:
    """Open a process and gather all available details."""
    arch = _detect_arch_for_pid(pid)
    window_title = _find_window_title(pid)
    memory_kb = _get_memory_kb(pid)
    exe_path = _get_exe_path(pid)
    admin = _is_admin(pid)
    return ProcessInfo(
        pid=pid,
        name=name,
        arch=arch,
        window_title=window_title,
        memory_kb=memory_kb,
        exe_path=exe_path,
        is_admin=admin,
    )


# ---------------------------------------------------------------------------
# Internal: architecture detection
# ---------------------------------------------------------------------------


def _detect_arch_for_pid(pid: int) -> str:
    """Determine whether a process is 32-bit (WOW64) or 64-bit.

    Must open the process to call ``IsWow64Process``.
    """
    if pid == 0:
        return "x64" if _is_python_64bit() else "x86"

    h_proc = _open_process(pid, PROCESS_QUERY_INFORMATION)
    if h_proc is None:
        # Can't query — assume same arch as Python
        return "x64" if _is_python_64bit() else "x86"

    try:
        wow64 = wintypes.BOOL(False)
        # IsWow64Process may not exist on true 32-bit Windows, but it's
        # always available on 64-bit Windows (which is the dominant case).
        try:
            kernel32.IsWow64Process(h_proc, ctypes.byref(wow64))
        except AttributeError:
            # Pure 32-bit Windows — everything is 32-bit
            return "x86"

        return "x86" if wow64.value else "x64"
    finally:
        kernel32.CloseHandle(h_proc)


# ---------------------------------------------------------------------------
# Internal: window title
# ---------------------------------------------------------------------------


def _find_window_title(pid: int) -> Optional[str]:
    """Find the title of the first visible top-level window owned by *pid*."""
    result: List[str] = []  # mutable container for callback communication

    WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)

    @WNDENUMPROC
    def _callback(hwnd: int, lparam: int) -> bool:
        # Check if this window belongs to the target PID
        window_pid = wintypes.DWORD(0)
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value != pid:
            return True  # continue enumeration

        # Must be visible
        if not user32.IsWindowVisible(hwnd):
            return True

        # Get title text
        text_len = user32.GetWindowTextLengthW(hwnd)
        if text_len == 0:
            return True

        buf = ctypes.create_unicode_buffer(text_len + 1)
        user32.GetWindowTextW(hwnd, buf, text_len + 1)
        title = buf.value
        if title:
            result.append(title)
            return False  # Found — stop enumeration

        return True

    user32.EnumWindows(_callback, 0)
    return result[0] if result else None


# ---------------------------------------------------------------------------
# Internal: memory
# ---------------------------------------------------------------------------


def _get_memory_kb(pid: int) -> int:
    """Get the working set size of a process in kilobytes."""
    h_proc = _open_process(pid, PROCESS_QUERY_INFORMATION | PROCESS_VM_READ)
    if h_proc is None:
        return 0

    try:
        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        if psapi.GetProcessMemoryInfo(
            h_proc, ctypes.byref(pmc), ctypes.sizeof(PROCESS_MEMORY_COUNTERS)
        ):
            return pmc.WorkingSetSize // 1024
        return 0
    finally:
        kernel32.CloseHandle(h_proc)


# ---------------------------------------------------------------------------
# Internal: executable path
# ---------------------------------------------------------------------------


def _get_exe_path(pid: int) -> Optional[str]:
    """Get the full executable path for a process."""
    h_proc = _open_process(
        pid, PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    )
    if h_proc is None:
        # Retry with limited access (works for some protected processes)
        h_proc = _open_process(pid, PROCESS_QUERY_LIMITED_INFORMATION)
    if h_proc is None:
        return None

    try:
        buf = ctypes.create_unicode_buffer(260)
        size = wintypes.DWORD(260)
        if kernel32.QueryFullProcessImageNameW(
            h_proc, PROCESS_NAME_WIN32, buf, ctypes.byref(size)
        ):
            return buf.value
        return None
    finally:
        kernel32.CloseHandle(h_proc)


# ---------------------------------------------------------------------------
# Internal: admin / elevation
# ---------------------------------------------------------------------------


def _is_admin(pid: int) -> bool:
    """Check whether a process is running with elevated (admin) privileges."""
    if pid == 0:
        return False

    h_proc = _open_process(pid, PROCESS_QUERY_INFORMATION)
    if h_proc is None:
        h_proc = _open_process(pid, PROCESS_QUERY_LIMITED_INFORMATION)
    if h_proc is None:
        return False

    try:
        token = wintypes.HANDLE(0)
        if not advapi32.OpenProcessToken(
            h_proc, TOKEN_QUERY, ctypes.byref(token)
        ):
            return False

        try:
            elevation = TOKEN_ELEVATION()
            ret_len = wintypes.DWORD(0)
            if advapi32.GetTokenInformation(
                token,
                TokenElevation,
                ctypes.byref(elevation),
                ctypes.sizeof(TOKEN_ELEVATION),
                ctypes.byref(ret_len),
            ):
                return elevation.TokenIsElevated != 0
            return False
        finally:
            kernel32.CloseHandle(token)
    finally:
        kernel32.CloseHandle(h_proc)


# ---------------------------------------------------------------------------
# Internal: process handle helper
# ---------------------------------------------------------------------------


def _open_process(pid: int, desired_access: int) -> Optional[int]:
    """Open a process handle with the given access rights.

    Returns:
        The handle value as an int, or ``None`` if ``OpenProcess`` failed.
    """
    if pid == 0:
        return None
    h = kernel32.OpenProcess(desired_access, False, pid)
    if not h:
        return None
    return h


# ---------------------------------------------------------------------------
# Internal: enumerate modules in a process
# ---------------------------------------------------------------------------


def _find_module_base(pid: int, dll_name_lower: str) -> Optional[int]:
    """Find the base address (HMODULE) of a loaded DLL in a target process.

    Args:
        pid: Target process ID.
        dll_name_lower: DLL name in lower-case (e.g. ``"speedpatch64.dll"``).

    Returns:
        The module handle (base address) as an int, or ``None`` if not found.
    """
    from ._constants import TH32CS_SNAPMODULE
    from ._winapi import MODULEENTRY32W as _MODULEENTRY32W

    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return None

    try:
        entry = _MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(_MODULEENTRY32W)

        if kernel32.Module32FirstW(snapshot, ctypes.byref(entry)):
            while True:
                mod_name = entry.szModule.rstrip("\x00").lower()
                if mod_name == dll_name_lower:
                    # hModule in MODULEENTRY32W is the base address (HMODULE)
                    return entry.hModule

                if not kernel32.Module32NextW(snapshot, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)

    return None


