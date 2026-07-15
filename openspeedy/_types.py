"""
Public data types for the openspeedy package.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(eq=True, unsafe_hash=True)
class ProcessInfo:
    """Information about a running Windows process.

    Attributes:
        pid: Process identifier.
        name: Executable file name (e.g. ``"notepad.exe"``).
        arch: CPU architecture — ``"x64"`` or ``"x86"``.
        window_title: Title of the process's main visible window, or ``None``.
        memory_kb: Working set size in kilobytes (0 in fast-enumeration mode).
        exe_path: Full path to the executable, or ``None`` if unavailable.
        is_admin: Whether the process is running with elevated privileges.
    """

    pid: int
    name: str
    arch: str = "x64"
    window_title: Optional[str] = None
    memory_kb: int = 0
    exe_path: Optional[str] = None
    is_admin: bool = False


@dataclass
class ModuleInfo:
    """Information about a loaded module (DLL) in a process.

    Attributes:
        name: Base file name of the module (e.g. ``"speedpatch64.dll"``).
        path: Full filesystem path to the module file.
        base_address: Memory address where the module is loaded.
        size: Size of the module image in bytes.
    """

    name: str
    path: str
    base_address: int
    size: int
