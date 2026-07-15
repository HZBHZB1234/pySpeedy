"""
OpenSpeedy — Python bindings for the OpenSpeedy game speed controller.

This library wraps the OpenSpeedy speedpatch DLL injection mechanism,
allowing Python scripts to accelerate or decelerate Windows games by
intercepting time-related API functions in target processes.

**Windows only.**  On any other platform, importing this package raises
``ImportError`` immediately.

Quick start
-----------

::

    from openspeedy import SpeedController

    sc = SpeedController()

    # List running processes
    for proc in sc.list_processes():
        print(f"PID {proc.pid}: {proc.name} ({proc.arch})")

    # Inject into a process and set 2x speed
    sc.inject(1234)
    sc.set_speed(2.0)

    # Check status
    print(f"Speed: {sc.get_speed()}x, enabled: {sc.is_enabled(1234)}")

    # Clean up
    sc.close()

License
-------

GPL v3.  See the LICENSE file for full text.

The bundled ``speedpatch*.dll`` files incorporate MinHook, which is
licensed under the BSD 2-Clause License.
"""

import sys

if sys.platform != "win32":
    raise ImportError(
        "openspeedy is Windows-only. "
        "It requires Windows APIs for DLL injection, process manipulation, "
        "and shared memory. "
        f"Current platform: {sys.platform}"
    )

from openspeedy._core import SpeedController
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
from openspeedy._types import ModuleInfo, ProcessInfo

__version__ = "0.1.0"

__all__ = [
    # Main class
    "SpeedController",
    # Data types
    "ProcessInfo",
    "ModuleInfo",
    # Exceptions
    "OpenSpeedyError",
    "PlatformNotSupportedError",
    "DLLNotFoundError",
    "ProcessAccessDeniedError",
    "ProcessNotFoundError",
    "ProcessArchitectureMismatch",
    "InjectionError",
    "EjectionError",
    "SpeedRangeError",
    "SpeedControlError",
]
