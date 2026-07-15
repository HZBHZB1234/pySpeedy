"""
High-level ``SpeedController`` — the main entry point for the openspeedy
library.

Aggregates process enumeration, DLL injection/ejection, speed factor
control, and per-process enable/disable into a single, easy-to-use class.
"""

import threading
from contextlib import contextmanager
from typing import Iterator, List, Set

from ._constants import SPEED_DEFAULT
from ._eject import eject_dll as _eject_dll
from ._inject import inject_dll as _inject_dll
from ._process import list_processes as _list_processes
from ._speeddll import (
    disable as _disable,
    enable as _enable,
    get_speed as _get_speed,
    is_enabled as _is_enabled,
    set_speed as _set_speed,
)
from ._types import ProcessInfo


class SpeedController:
    """Control game speed by injecting OpenSpeedy's speedpatch DLL into
    target Windows processes.

    Usage::

        from openspeedy import SpeedController

        sc = SpeedController()
        processes = sc.list_processes()

        # Inject into a game
        sc.inject(pid)

        # Set 2x speed
        sc.set_speed(2.0)

        # Temporarily boost to 5x
        with sc.speed_context(5.0):
            ...  # game runs at 5x

        # Clean up
        sc.close()

    Thread safety
    -------------

    Injection/ejection operations are serialized with an internal lock.
    Speed factor read/write is inherently atomic (the DLL uses
    ``std::atomic<double>`` in a shared PE section) and requires no
    additional synchronization at the Python level.

    .. note::

        **v1 architecture limitation**: A 64-bit Python interpreter can
        only inject into 64-bit processes; a 32-bit interpreter can only
        inject into 32-bit processes.  This is because ``LoadLibraryW``
        must be at the same virtual address in both the calling and target
        processes.
    """

    def __init__(self) -> None:
        self._injected_pids: Set[int] = set()
        self._lock = threading.Lock()

    # ── Process enumeration ─────────────────────────────────────────────

    def list_processes(self, fast: bool = True) -> List[ProcessInfo]:
        """Enumerate all running Windows processes.

        Args:
            fast: If ``True`` (default), use snapshot-only enumeration
                (faster but less detail).  If ``False``, open each process
                to collect window title, memory, path, and admin status.

        Returns:
            List of :class:`ProcessInfo` objects.
        """
        return _list_processes(fast=fast)

    # ── Injection / ejection ────────────────────────────────────────────

    def inject(self, pid: int) -> None:
        """Inject the speedpatch DLL into a target process and enable
        speed control for it.

        Args:
            pid: Target process ID.

        Raises:
            ProcessNotFoundError: The PID does not exist.
            ProcessAccessDeniedError: Cannot open the process (protected
                or insufficient privileges).
            ProcessArchitectureMismatch: Python and target architectures
                differ.
            InjectionError: The injection itself failed.
        """
        with self._lock:
            _inject_dll(pid)
            _enable(pid)
            self._injected_pids.add(pid)

    def eject(self, pid: int) -> None:
        """Unload the speedpatch DLL from a target process.

        Args:
            pid: Target process ID.

        Raises:
            EjectionError: The DLL was not found or ``FreeLibrary`` failed.
        """
        with self._lock:
            _eject_dll(pid)
            self._injected_pids.discard(pid)

    # ── Global speed factor ─────────────────────────────────────────────

    def set_speed(self, factor: float) -> None:
        """Set the global speed multiplier.

        Applies to **all** processes that have the speedpatch DLL injected
        (via the shared PE data section).

        Args:
            factor: Speed multiplier (1.0 = normal, 2.0 = double,
                0.5 = half).  Must be in ``[0.001, 1000.0]``.

        Raises:
            SpeedRangeError: The factor is out of the valid range.
        """
        _set_speed(factor)

    def get_speed(self) -> float:
        """Get the current global speed multiplier.

        Returns:
            The speed factor (defaults to 1.0).
        """
        return _get_speed()

    # ── Per-process enable / disable ────────────────────────────────────

    def enable(self, pid: int) -> None:
        """Enable (or re-enable) speed control for a previously injected
        process.

        When a process is disabled, the injected DLL still intercepts time
        API calls but returns unmodified values (factor = 1.0).  Calling
        ``enable()`` restores speed modification.

        Args:
            pid: Target process ID.
        """
        _enable(pid)

    def disable(self, pid: int) -> None:
        """Temporarily disable speed control for a process.

        The process still has the DLL loaded, but time APIs are not
        affected.  Call :meth:`enable` to re-apply speed control.

        Args:
            pid: Target process ID.
        """
        _disable(pid)

    def is_enabled(self, pid: int) -> bool:
        """Check whether speed control is currently active for a process.

        Args:
            pid: Target process ID.

        Returns:
            ``True`` if speed control is enabled for the process.
        """
        return _is_enabled(pid)

    # ── Context manager ─────────────────────────────────────────────────

    @contextmanager
    def speed_context(self, factor: float) -> Iterator[None]:
        """Temporarily set a speed factor, restoring the previous value on
        exit.

        Usage::

            with sc.speed_context(3.0):
                # everything runs at 3x
                ...
            # speed restored

        Args:
            factor: Temporary speed multiplier.
        """
        old = _get_speed()
        _set_speed(factor)
        try:
            yield
        finally:
            _set_speed(old)

    # ── Cleanup ─────────────────────────────────────────────────────────

    def close(self) -> None:
        """Eject from all processes that were injected by this controller
        instance.

        This is a best-effort operation — some ejections may fail
        (e.g. if the target process has already exited).  Failures are
        logged but do not prevent ejecting the remaining processes.

        The controller can still be used after ``close()``; the tracking
        set is simply cleared.
        """
        with self._lock:
            pids = list(self._injected_pids)
            for pid in pids:
                try:
                    _eject_dll(pid)
                except Exception:
                    pass  # best-effort
            self._injected_pids.clear()

    def __enter__(self) -> "SpeedController":
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def __repr__(self) -> str:
        return (
            f"<SpeedController injected={len(self._injected_pids)} "
            f"speed={_get_speed():.2f}>"
        )
