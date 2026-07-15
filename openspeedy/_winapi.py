"""
Low-level Windows API definitions via ctypes.

All kernel32 / user32 / psapi / advapi32 function prototypes, structure
definitions, and helper utilities are defined here.  Every function uses
``use_last_error=True`` so that ``ctypes.get_last_error()`` returns the
thread-local Win32 error code after a failed call.

.. note::

    Windows ``BOOL`` is a 4-byte ``int``.  We use ``ctypes.c_int`` as the
    restype for BOOL-returning functions — **never** ``ctypes.c_bool`` (which
    is 1 byte), as that would cause a stack-read underflow on x86.
"""

import ctypes
import struct
from ctypes import wintypes
from typing import Optional

# ---------------------------------------------------------------------------
# DLL handles (use_last_error=True for automatic GetLastError capture)
# ---------------------------------------------------------------------------
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
user32 = ctypes.WinDLL("user32", use_last_error=True)
psapi = ctypes.WinDLL("psapi", use_last_error=True)
advapi32 = ctypes.WinDLL("advapi32", use_last_error=True)

# ---------------------------------------------------------------------------
# Common Win32 types
# ---------------------------------------------------------------------------
LPVOID = wintypes.LPVOID
HANDLE = wintypes.HANDLE
HMODULE = wintypes.HMODULE
HICON = wintypes.HICON
HDC = wintypes.HDC
HWND = wintypes.HWND
DWORD = wintypes.DWORD
BOOL = wintypes.BOOL
UINT = wintypes.UINT
LONG = wintypes.LONG
ULONGLONG = ctypes.c_ulonglong
LARGE_INTEGER = ctypes.c_longlong
ULARGE_INTEGER = ctypes.c_ulonglong
SIZE_T = ctypes.c_size_t
LPCWSTR = wintypes.LPCWSTR
LPWSTR = wintypes.LPWSTR
LPCSTR = wintypes.LPCSTR
ATOM = wintypes.ATOM

# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _check_handle(result: int, operation: str) -> int:
    """Raise ``OpenSpeedyError`` if *result* is NULL or INVALID_HANDLE_VALUE."""
    from ._constants import INVALID_HANDLE_VALUE_SIGNED
    from ._exceptions import OpenSpeedyError

    if not result or result == INVALID_HANDLE_VALUE_SIGNED:
        err = ctypes.get_last_error()
        raise OpenSpeedyError(
            f"{operation} failed: {ctypes.FormatError(err)} (code {err})",
            win_error=err,
        )
    return result


def _check_bool(result: int, operation: str) -> None:
    """Raise ``OpenSpeedyError`` if a BOOL-returning call returned 0."""
    from ._exceptions import OpenSpeedyError

    if not result:
        err = ctypes.get_last_error()
        raise OpenSpeedyError(
            f"{operation} failed: {ctypes.FormatError(err)} (code {err})",
            win_error=err,
        )


def _is_python_64bit() -> bool:
    """Return ``True`` if the running Python interpreter is 64-bit."""
    return struct.calcsize("P") == 8


# Import constants lazily to avoid circular imports at module level.
# We use a private function so the constants are available inside helpers
# without polluting the module namespace with a star-import.
def _constants():
    from . import _constants as _c

    return _c


# ---------------------------------------------------------------------------
# FILETIME
# ---------------------------------------------------------------------------
class FILETIME(ctypes.Structure):
    _fields_ = [
        ("dwLowDateTime",  wintypes.DWORD),
        ("dwHighDateTime", wintypes.DWORD),
    ]


# ---------------------------------------------------------------------------
# SYSTEM_INFO (for processor architecture)
# ---------------------------------------------------------------------------
class SYSTEM_INFO(ctypes.Structure):
    _fields_ = [
        ("wProcessorArchitecture",      wintypes.WORD),
        ("wReserved",                    wintypes.WORD),
        ("dwPageSize",                   wintypes.DWORD),
        ("lpMinimumApplicationAddress",  wintypes.LPVOID),
        ("lpMaximumApplicationAddress",  wintypes.LPVOID),
        ("dwActiveProcessorMask",        ctypes.POINTER(ctypes.c_ulonglong)),
        ("dwNumberOfProcessors",         wintypes.DWORD),
        ("dwProcessorType",              wintypes.DWORD),
        ("dwAllocationGranularity",      wintypes.DWORD),
        ("wProcessorLevel",              wintypes.WORD),
        ("wProcessorRevision",           wintypes.WORD),
    ]


PROCESSOR_ARCHITECTURE_INTEL = 0
PROCESSOR_ARCHITECTURE_AMD64 = 9
PROCESSOR_ARCHITECTURE_ARM64 = 12


# ---------------------------------------------------------------------------
# PROCESSENTRY32W — for CreateToolhelp32Snapshot / Process32First / Process32Next
# ---------------------------------------------------------------------------
class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize",              wintypes.DWORD),
        ("cntUsage",            wintypes.DWORD),
        ("th32ProcessID",       wintypes.DWORD),
        ("th32DefaultHeapID",   ctypes.POINTER(ctypes.c_ulong)),
        ("th32ModuleID",        wintypes.DWORD),
        ("cntThreads",          wintypes.DWORD),
        ("th32ParentProcessID", wintypes.DWORD),
        ("pcPriClassBase",      wintypes.LONG),
        ("dwFlags",             wintypes.DWORD),
        ("szExeFile",           ctypes.c_wchar * 260),
    ]


# ---------------------------------------------------------------------------
# MODULEENTRY32W — for Module32First / Module32Next
# ---------------------------------------------------------------------------
class MODULEENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize",          wintypes.DWORD),
        ("th32ModuleID",    wintypes.DWORD),
        ("th32ProcessID",   wintypes.DWORD),
        ("GlblcntUsage",    wintypes.DWORD),
        ("ProccntUsage",    wintypes.DWORD),
        ("modBaseAddr",     ctypes.POINTER(ctypes.c_byte)),  # LPBYTE
        ("modBaseSize",     wintypes.DWORD),
        ("hModule",         wintypes.HMODULE),
        ("szModule",        ctypes.c_wchar * 256),
        ("szExePath",       ctypes.c_wchar * 260),
    ]


# ---------------------------------------------------------------------------
# MEMORYSTATUSEX — for GlobalMemoryStatusEx
# ---------------------------------------------------------------------------
class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ("dwLength",                wintypes.DWORD),
        ("dwMemoryLoad",            wintypes.DWORD),
        ("ullTotalPhys",            wintypes.ULARGE_INTEGER),
        ("ullAvailPhys",            wintypes.ULARGE_INTEGER),
        ("ullTotalPageFile",        wintypes.ULARGE_INTEGER),
        ("ullAvailPageFile",        wintypes.ULARGE_INTEGER),
        ("ullTotalVirtual",         wintypes.ULARGE_INTEGER),
        ("ullAvailVirtual",         wintypes.ULARGE_INTEGER),
        ("ullAvailExtendedVirtual", wintypes.ULARGE_INTEGER),
    ]


# ---------------------------------------------------------------------------
# PROCESS_MEMORY_COUNTERS — for GetProcessMemoryInfo
# ---------------------------------------------------------------------------
class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("cb",                          wintypes.DWORD),
        ("PageFaultCount",              wintypes.DWORD),
        ("PeakWorkingSetSize",          ctypes.c_size_t),
        ("WorkingSetSize",              ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage",     ctypes.c_size_t),
        ("QuotaPagedPoolUsage",         ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage",  ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage",      ctypes.c_size_t),
        ("PagefileUsage",               ctypes.c_size_t),
        ("PeakPagefileUsage",           ctypes.c_size_t),
    ]


# ---------------------------------------------------------------------------
# TOKEN_ELEVATION — for GetTokenInformation(TokenElevation)
# ---------------------------------------------------------------------------
class TOKEN_ELEVATION(ctypes.Structure):
    _fields_ = [
        ("TokenIsElevated", wintypes.DWORD),
    ]


# ---------------------------------------------------------------------------
# REASON_CONTEXT — for SetWaitableTimerEx (placeholder)
# ---------------------------------------------------------------------------
class REASON_CONTEXT(ctypes.Structure):
    _fields_ = [
        ("Version", wintypes.DWORD),
        ("Flags",   wintypes.DWORD),
        ("Reason",  ctypes.c_char * 128),  # simplified
    ]


# ===================================================================
# kernel32.dll function prototypes
# ===================================================================

# --- Process / thread -------------------------------------------------------

kernel32.OpenProcess.restype = wintypes.HANDLE
kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]

kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]

kernel32.GetCurrentProcess.restype = wintypes.HANDLE
kernel32.GetCurrentProcess.argtypes = []

kernel32.GetCurrentProcessId.restype = wintypes.DWORD
kernel32.GetCurrentProcessId.argtypes = []

kernel32.GetExitCodeThread.restype = wintypes.BOOL
kernel32.GetExitCodeThread.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.DWORD),
]

kernel32.TerminateProcess.restype = wintypes.BOOL
kernel32.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]

kernel32.GetProcessId.restype = wintypes.DWORD
kernel32.GetProcessId.argtypes = [wintypes.HANDLE]

# --- Memory -----------------------------------------------------------------

kernel32.VirtualAllocEx.restype = wintypes.LPVOID
kernel32.VirtualAllocEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.DWORD,
    wintypes.DWORD,
]

kernel32.VirtualFreeEx.restype = wintypes.BOOL
kernel32.VirtualFreeEx.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    ctypes.c_size_t,
    wintypes.DWORD,
]

kernel32.WriteProcessMemory.restype = wintypes.BOOL
kernel32.WriteProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,
    wintypes.LPCVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]

kernel32.ReadProcessMemory.restype = wintypes.BOOL
kernel32.ReadProcessMemory.argtypes = [
    wintypes.HANDLE,
    wintypes.LPCVOID,
    wintypes.LPVOID,
    ctypes.c_size_t,
    ctypes.POINTER(ctypes.c_size_t),
]

# --- Thread -----------------------------------------------------------------

kernel32.CreateRemoteThread.restype = wintypes.HANDLE
kernel32.CreateRemoteThread.argtypes = [
    wintypes.HANDLE,
    wintypes.LPVOID,       # LPSECURITY_ATTRIBUTES
    ctypes.c_size_t,         # dwStackSize
    wintypes.LPVOID,       # LPTHREAD_START_ROUTINE
    wintypes.LPVOID,       # lpParameter
    wintypes.DWORD,         # dwCreationFlags
    ctypes.POINTER(wintypes.DWORD),  # lpThreadId
]

kernel32.WaitForSingleObject.restype = wintypes.DWORD
kernel32.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]

# --- ToolHelp snapshot -------------------------------------------------------

kernel32.CreateToolhelp32Snapshot.restype = wintypes.HANDLE
kernel32.CreateToolhelp32Snapshot.argtypes = [wintypes.DWORD, wintypes.DWORD]

kernel32.Process32FirstW.restype = wintypes.BOOL
kernel32.Process32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]

kernel32.Process32NextW.restype = wintypes.BOOL
kernel32.Process32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]

kernel32.Module32FirstW.restype = wintypes.BOOL
kernel32.Module32FirstW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]

kernel32.Module32NextW.restype = wintypes.BOOL
kernel32.Module32NextW.argtypes = [wintypes.HANDLE, ctypes.POINTER(MODULEENTRY32W)]

# --- Architecture detection --------------------------------------------------

kernel32.IsWow64Process.restype = wintypes.BOOL
kernel32.IsWow64Process.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.BOOL)]

kernel32.GetNativeSystemInfo.restype = None
kernel32.GetNativeSystemInfo.argtypes = [ctypes.POINTER(SYSTEM_INFO)]

# --- Process image name ------------------------------------------------------

kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
kernel32.QueryFullProcessImageNameW.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.LPWSTR,
    ctypes.POINTER(wintypes.DWORD),
]

# --- Module / library --------------------------------------------------------

kernel32.GetModuleHandleW.restype = wintypes.HMODULE
kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]

kernel32.GetProcAddress.restype = wintypes.LPVOID
kernel32.GetProcAddress.argtypes = [wintypes.HMODULE, wintypes.LPCSTR]

kernel32.LoadLibraryW.restype = wintypes.HMODULE
kernel32.LoadLibraryW.argtypes = [wintypes.LPCWSTR]

kernel32.FreeLibrary.restype = wintypes.BOOL
kernel32.FreeLibrary.argtypes = [wintypes.HMODULE]

kernel32.GetModuleFileNameW.restype = wintypes.DWORD
kernel32.GetModuleFileNameW.argtypes = [
    wintypes.HMODULE,
    wintypes.LPWSTR,
    wintypes.DWORD,
]

# --- File mapping ------------------------------------------------------------

kernel32.CreateFileMappingW.restype = wintypes.HANDLE
kernel32.CreateFileMappingW.argtypes = [
    wintypes.HANDLE,       # hFile (INVALID_HANDLE_VALUE for pagefile-backed)
    wintypes.LPVOID,       # lpFileMappingAttributes
    wintypes.DWORD,         # flProtect
    wintypes.DWORD,         # dwMaximumSizeHigh
    wintypes.DWORD,         # dwMaximumSizeLow
    wintypes.LPCWSTR,       # lpName
]

kernel32.OpenFileMappingW.restype = wintypes.HANDLE
kernel32.OpenFileMappingW.argtypes = [
    wintypes.DWORD,         # dwDesiredAccess
    wintypes.BOOL,          # bInheritHandle
    wintypes.LPCWSTR,       # lpName
]

kernel32.MapViewOfFile.restype = wintypes.LPVOID
kernel32.MapViewOfFile.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    wintypes.DWORD,
    wintypes.DWORD,
    ctypes.c_size_t,
]

kernel32.UnmapViewOfFile.restype = wintypes.BOOL
kernel32.UnmapViewOfFile.argtypes = [wintypes.LPCVOID]

# --- Error handling ----------------------------------------------------------

kernel32.GetLastError.restype = wintypes.DWORD
kernel32.GetLastError.argtypes = []

kernel32.SetLastError.restype = None
kernel32.SetLastError.argtypes = [wintypes.DWORD]

# --- Global memory -----------------------------------------------------------

kernel32.GlobalMemoryStatusEx.restype = wintypes.BOOL
kernel32.GlobalMemoryStatusEx.argtypes = [
    ctypes.POINTER(MEMORYSTATUSEX),
]

# ===================================================================
# psapi.dll function prototypes
# ===================================================================

psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
psapi.GetProcessMemoryInfo.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(PROCESS_MEMORY_COUNTERS),
    wintypes.DWORD,
]

psapi.EnumProcessModulesEx.restype = wintypes.BOOL
psapi.EnumProcessModulesEx.argtypes = [
    wintypes.HANDLE,
    ctypes.POINTER(wintypes.HMODULE),
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
    wintypes.DWORD,
]

psapi.GetModuleInformation.restype = wintypes.BOOL
# Skip full argtypes — used sparingly; define on-demand if needed.

psapi.GetModuleFileNameExW.restype = wintypes.DWORD
psapi.GetModuleFileNameExW.argtypes = [
    wintypes.HANDLE,
    wintypes.HMODULE,
    wintypes.LPWSTR,
    wintypes.DWORD,
]

# ===================================================================
# advapi32.dll function prototypes
# ===================================================================

advapi32.OpenProcessToken.restype = wintypes.BOOL
advapi32.OpenProcessToken.argtypes = [
    wintypes.HANDLE,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.HANDLE),
]

advapi32.GetTokenInformation.restype = wintypes.BOOL
advapi32.GetTokenInformation.argtypes = [
    wintypes.HANDLE,
    ctypes.c_int,                 # TOKEN_INFORMATION_CLASS
    wintypes.LPVOID,
    wintypes.DWORD,
    ctypes.POINTER(wintypes.DWORD),
]

# ===================================================================
# user32.dll function prototypes
# ===================================================================

user32.EnumWindows.restype = wintypes.BOOL
user32.EnumWindows.argtypes = [
    ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM),
    wintypes.LPARAM,
]

user32.IsWindowVisible.restype = wintypes.BOOL
user32.IsWindowVisible.argtypes = [wintypes.HWND]

user32.GetWindowTextW.restype = ctypes.c_int
user32.GetWindowTextW.argtypes = [
    wintypes.HWND,
    wintypes.LPWSTR,
    ctypes.c_int,
]

user32.GetWindowTextLengthW.restype = ctypes.c_int
user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]

user32.GetWindowThreadProcessId.restype = wintypes.DWORD
user32.GetWindowThreadProcessId.argtypes = [
    wintypes.HWND,
    ctypes.POINTER(wintypes.DWORD),
]

user32.GetForegroundWindow.restype = wintypes.HWND
user32.GetForegroundWindow.argtypes = []

user32.GetParent.restype = wintypes.HWND
user32.GetParent.argtypes = [wintypes.HWND]


# ===================================================================
# Convenience: kernel32 LoadLibraryW address for remote threads
# ===================================================================

def get_loadlibraryw_address() -> int:
    """Return the address of ``LoadLibraryW`` in the local ``kernel32.dll``.

    Because ``kernel32.dll`` is loaded at the same base address in every
    process of the same architecture, this address is also valid as a
    remote-thread start routine in a target process of the same bitness.
    """
    # We must use ctypes.cast on the function pointer to get a generic address.
    # ctypes.c_void_p from the function gives us the raw pointer value.
    return ctypes.cast(kernel32.LoadLibraryW, ctypes.c_void_p).value  # type: ignore[attr-defined]


def get_loadlibrarya_address() -> int:
    """Return the address of ``LoadLibraryA`` in the local ``kernel32.dll``."""
    return ctypes.cast(kernel32.LoadLibraryA, ctypes.c_void_p).value  # type: ignore[attr-defined]


def get_freelibrary_address() -> int:
    """Return the address of ``FreeLibrary`` in the local ``kernel32.dll``."""
    return ctypes.cast(kernel32.FreeLibrary, ctypes.c_void_p).value  # type: ignore[attr-defined]
