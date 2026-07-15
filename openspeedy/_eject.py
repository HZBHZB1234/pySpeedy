"""
DLL ejection from a target Windows process.

Re-implements the Rust ``do_eject()`` function from ``src-bridge/src/main.rs``
in pure Python via ``ctypes``.

Ejection flow
-------------

1. Determine the DLL name from the target architecture
2. ``CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)``
3. ``Module32FirstW`` / ``Module32NextW`` loop to find the speedpatch DLL
4. Extract ``hModule`` (the module base address)
5. ``OpenProcess`` on the target
6. Get ``FreeLibrary`` address from local ``kernel32.dll``
7. ``CreateRemoteThread`` with ``FreeLibrary(hModule)`` as entry point
8. ``WaitForSingleObject``
9. Cleanup handles
"""

import ctypes

from ._constants import (
    PROCESS_EJECT_ACCESS,
    PROCESS_QUERY_INFORMATION,
    TH32CS_SNAPMODULE,
    WAIT_OBJECT_0,
)
from ._exceptions import (
    EjectionError,
    ProcessAccessDeniedError,
)
from ._process import _detect_arch_for_pid
from ._winapi import (
    MODULEENTRY32W,
    kernel32,
    wintypes,
    get_freelibrary_address,
)


def eject_dll(pid: int) -> None:
    """Unload the speedpatch DLL from a target process.

    Args:
        pid: Target process ID.

    Raises:
        EjectionError: The DLL was not found in the target or
            ``FreeLibrary`` failed.
        ProcessAccessDeniedError: Cannot open the process.
    """
    # 1. Determine DLL name from target architecture
    arch = _detect_arch_for_pid(pid)
    dll_name = "speedpatch64.dll" if arch == "x64" else "speedpatch32.dll"
    dll_name_lower = dll_name.lower()

    # 2. Enumerate modules in the target
    h_module = _find_dll_module(pid, dll_name_lower)
    if h_module is None:
        raise EjectionError(pid, f"module '{dll_name}' not found in process")

    # 3. Open the target process
    h_proc = kernel32.OpenProcess(PROCESS_EJECT_ACCESS, False, pid)
    if not h_proc:
        err = ctypes.get_last_error()
        raise ProcessAccessDeniedError(pid, win_error=err)

    try:
        # 4. Get FreeLibrary address
        lp_free = get_freelibrary_address()
        if not lp_free:
            raise EjectionError(pid, "cannot get FreeLibrary address")

        # 5. Create remote thread calling FreeLibrary(h_module)
        thread_id = wintypes.DWORD(0)
        h_thread = kernel32.CreateRemoteThread(
            h_proc,
            None,
            0,
            lp_free,
            h_module,
            0,
            ctypes.byref(thread_id),
        )
        if not h_thread:
            err = ctypes.get_last_error()
            raise EjectionError(
                pid, "CreateRemoteThread for FreeLibrary failed", win_error=err
            )

        try:
            ret = kernel32.WaitForSingleObject(h_thread, 5000)
            if ret != WAIT_OBJECT_0:
                raise EjectionError(
                    pid, "WaitForSingleObject timed out or failed"
                )
        finally:
            kernel32.CloseHandle(h_thread)

    finally:
        kernel32.CloseHandle(h_proc)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _find_dll_module(pid: int, dll_name_lower: str) -> int | None:
    """Find the HMODULE (base address) of a DLL loaded in a target process.

    Args:
        pid: Target process ID.
        dll_name_lower: Lower-cased DLL name to search for.

    Returns:
        Module handle value, or ``None`` if not found.
    """
    snapshot = kernel32.CreateToolhelp32Snapshot(TH32CS_SNAPMODULE, pid)
    if not snapshot or snapshot == ctypes.c_void_p(-1).value:
        return None

    try:
        entry = MODULEENTRY32W()
        entry.dwSize = ctypes.sizeof(MODULEENTRY32W)

        if kernel32.Module32FirstW(snapshot, ctypes.byref(entry)):
            while True:
                mod_name = entry.szModule.rstrip("\x00").lower()
                if mod_name == dll_name_lower:
                    return entry.hModule

                if not kernel32.Module32NextW(snapshot, ctypes.byref(entry)):
                    break
    finally:
        kernel32.CloseHandle(snapshot)

    return None
