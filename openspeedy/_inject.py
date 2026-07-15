"""
DLL injection into a target Windows process.

Re-implements the Rust ``do_inject()`` / ``try_inject_impl()`` functions from
``src-bridge/src/main.rs`` in pure Python via ``ctypes``.

Injection flow
--------------

1. ``OpenProcess`` with required access rights
2. ``IsWow64Process`` to detect target architecture
3. Verify architecture compatibility (v1: same-arch only)
4. ``VirtualAllocEx`` to allocate remote memory for the DLL path
5. ``WriteProcessMemory`` to write the path string into the target
6. Get ``LoadLibraryW`` address from local ``kernel32.dll``
7. ``CreateRemoteThread`` with ``LoadLibraryW`` as entry point
8. ``WaitForSingleObject`` (5 s timeout)
9. ``GetExitCodeThread`` — non-zero means success
10. On failure, retry with ``LoadLibraryA`` (ANSI path fallback)
11. ``VirtualFreeEx`` to clean up remote memory
"""

import ctypes
from typing import Optional

from ._constants import (
    INFINITE,
    MEM_COMMIT,
    MEM_RELEASE,
    MEM_RESERVE,
    PAGE_READWRITE,
    PROCESS_INJECT_ACCESS,
    PROCESS_QUERY_INFORMATION,
    WAIT_OBJECT_0,
)
from ._dll_resolver import _get_target_dll_path
from ._exceptions import (
    InjectionError,
    ProcessAccessDeniedError,
    ProcessArchitectureMismatch,
    ProcessNotFoundError,
)
from ._winapi import (
    kernel32,
    wintypes,
    _is_python_64bit,
    get_loadlibrarya_address,
    get_loadlibraryw_address,
)


def inject_dll(pid: int) -> None:
    """Inject the speedpatch DLL into the target process via
    ``CreateRemoteThread`` + ``LoadLibraryW`` (with ``LoadLibraryA``
    fallback).

    Args:
        pid: Target process ID.

    Raises:
        ProcessNotFoundError: The PID does not exist.
        ProcessAccessDeniedError: Cannot open the process.
        ProcessArchitectureMismatch: The Python and target architectures
            differ (v1 limitation).
        InjectionError: Injection failed for another reason.
    """
    # 1. Detect target architecture
    is64 = _detect_target_arch(pid)
    python_is64 = _is_python_64bit()

    # 2. Architecture compatibility check (v1)
    if is64 != python_is64:
        python_arch = "x64" if python_is64 else "x86"
        target_arch = "x64" if is64 else "x86"
        raise ProcessArchitectureMismatch(python_arch, target_arch, pid)

    # 3. Resolve DLL path
    dll_path = _get_target_dll_path(is64)
    dll_path_str = str(dll_path)

    # 4. Open the target process
    h_proc = kernel32.OpenProcess(PROCESS_INJECT_ACCESS, False, pid)
    if not h_proc:
        err = ctypes.get_last_error()
        if err == 87:  # ERROR_INVALID_PARAMETER — likely invalid PID
            raise ProcessNotFoundError(pid)
        raise ProcessAccessDeniedError(pid, win_error=err)

    try:
        # 5. Try LoadLibraryW injection
        if _try_inject(h_proc, dll_path_str, wide=True):
            return

        # 6. Fallback: LoadLibraryA
        if _try_inject(h_proc, dll_path_str, wide=False):
            return

        raise InjectionError(
            pid, "both LoadLibraryW and LoadLibraryA injection failed"
        )
    finally:
        kernel32.CloseHandle(h_proc)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _detect_target_arch(pid: int) -> bool:
    """Return ``True`` if the target process is 64-bit.

    Opens the process briefly to call ``IsWow64Process``.
    """
    h_proc = kernel32.OpenProcess(PROCESS_QUERY_INFORMATION, False, pid)
    if not h_proc:
        err = ctypes.get_last_error()
        raise ProcessAccessDeniedError(pid, win_error=err)

    try:
        wow64 = wintypes.BOOL(False)
        try:
            kernel32.IsWow64Process(h_proc, ctypes.byref(wow64))
        except AttributeError:
            # Pure 32-bit Windows
            return False
        # wow64=True means 32-bit process on 64-bit OS → is64=False
        return not wow64.value
    finally:
        kernel32.CloseHandle(h_proc)


def _try_inject(h_proc: int, dll_path: str, wide: bool = True) -> bool:
    """Attempt a single injection using the given path encoding.

    Args:
        h_proc: Open process handle.
        dll_path: Filesystem path to the DLL.
        wide: If ``True``, encode as UTF-16 (for ``LoadLibraryW``).
            If ``False``, encode as ANSI/MBCS (for ``LoadLibraryA``).

    Returns:
        ``True`` if the injection appears successful (remote thread exit
        code was non-zero).
    """
    # Encode path
    if wide:
        path_bytes = dll_path.encode("utf-16-le") + b"\x00\x00"
    else:
        path_bytes = dll_path.encode("mbcs") + b"\x00"

    path_len = len(path_bytes)

    # Allocate remote memory
    remote_mem = kernel32.VirtualAllocEx(
        h_proc, None, path_len, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE
    )
    if not remote_mem:
        return False

    try:
        # Write DLL path into the target
        written = ctypes.c_size_t(0)
        if not kernel32.WriteProcessMemory(
            h_proc, remote_mem, path_bytes, path_len, ctypes.byref(written)
        ):
            return False

        # Get the address of LoadLibraryW / LoadLibraryA
        if wide:
            lp_start = get_loadlibraryw_address()
        else:
            lp_start = get_loadlibrarya_address()

        if not lp_start:
            return False

        # Create the remote thread
        thread_id = wintypes.DWORD(0)
        h_thread = kernel32.CreateRemoteThread(
            h_proc,
            None,            # default security
            0,                # default stack size
            lp_start,         # LoadLibraryW/A
            remote_mem,       # parameter: DLL path
            0,                # run immediately
            ctypes.byref(thread_id),
        )
        if not h_thread:
            return False

        try:
            # Wait for LoadLibrary to finish
            ret = kernel32.WaitForSingleObject(h_thread, 5000)
            if ret != WAIT_OBJECT_0:
                return False

            # Check the thread exit code (LoadLibrary returns HMODULE on success,
            # NULL on failure)
            exit_code = wintypes.DWORD(0)
            if not kernel32.GetExitCodeThread(h_thread, ctypes.byref(exit_code)):
                return False

            return exit_code.value != 0
        finally:
            kernel32.CloseHandle(h_thread)

    finally:
        kernel32.VirtualFreeEx(h_proc, remote_mem, 0, MEM_RELEASE)
