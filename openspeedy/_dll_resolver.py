"""
Locate the speedpatch DLLs on disk.

Resolution order:
1. ``OPENSPEEDY_DLL_DIR`` environment variable (directory containing the DLLs)
2. Package data directory ``openspeedy/data/``
3. Current working directory
"""

import os
import struct
from pathlib import Path
from typing import Optional

from ._exceptions import DLLNotFoundError


def _get_data_dir() -> Path:
    """Return the absolute path to ``openspeedy/data/``."""
    return Path(__file__).resolve().parent / "data"


def _is_python_64bit() -> bool:
    """Return ``True`` if the running Python interpreter is 64-bit."""
    return struct.calcsize("P") == 8


def _get_own_dll_path() -> Path:
    """Return the path to the speedpatch DLL matching the Python
    interpreter's own architecture."""
    dll_name = "speedpatch64.dll" if _is_python_64bit() else "speedpatch32.dll"
    return _resolve_dll_path(dll_name)


def _get_target_dll_path(is_64bit: bool) -> Path:
    """Return the path to the speedpatch DLL for a target of the given
    architecture."""
    dll_name = "speedpatch64.dll" if is_64bit else "speedpatch32.dll"
    return _resolve_dll_path(dll_name)


def _resolve_dll_path(dll_name: str) -> Path:
    """Resolve a DLL by name using the standard search order.

    Raises:
        DLLNotFoundError: If the DLL cannot be found at any search location.
    """
    # 1. Environment variable override
    env_dir = os.environ.get("OPENSPEEDY_DLL_DIR")
    if env_dir:
        candidate = Path(env_dir) / dll_name
        if candidate.is_file():
            return candidate

    # 2. Package data directory
    candidate = _get_data_dir() / dll_name
    if candidate.is_file():
        return candidate

    # 3. Current working directory
    candidate = Path.cwd() / dll_name
    if candidate.is_file():
        return candidate

    raise DLLNotFoundError(str(candidate))


def _find_all_dll_paths() -> dict:
    """Find paths for both DLLs if available.

    Returns:
        Dict mapping arch name to Path, e.g.
        ``{"x64": Path(...), "x86": Path(...)}``.
        Missing entries are simply omitted.
    """
    result: dict = {}
    for arch, dll_name in [("x64", "speedpatch64.dll"), ("x86", "speedpatch32.dll")]:
        try:
            result[arch] = _resolve_dll_path(dll_name)
        except DLLNotFoundError:
            pass
    return result
