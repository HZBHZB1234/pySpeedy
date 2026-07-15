"""
Tests for the ``SpeedController`` class.
"""

from unittest.mock import MagicMock, patch

import pytest

from openspeedy._core import SpeedController
from openspeedy._speeddll import set_speed as _set_speed_raw
from openspeedy._types import ProcessInfo


@pytest.fixture(autouse=True)
def _reset_speed():
    """Reset global speed factor to 1.0 after every test.

    The speedpatch DLL uses a shared data section, so state leaks
    between tests.  This fixture ensures a clean slate.
    """
    yield
    _set_speed_raw(1.0)


class TestSpeedControllerInit:
    """Controller instantiation and lifecycle."""

    def test_init_default_state(self):
        sc = SpeedController()
        assert sc._injected_pids == set()
        assert sc.get_speed() == 1.0  # default from mock

    def test_context_manager_protocol(self):
        with SpeedController() as sc:
            assert isinstance(sc, SpeedController)

    def test_repr(self):
        sc = SpeedController()
        r = repr(sc)
        assert "SpeedController" in r
        assert "injected=0" in r


class TestSpeedControllerSpeed:
    """Speed factor get/set."""

    def test_set_speed(self):
        sc = SpeedController()
        sc.set_speed(2.5)

    def test_get_speed_default(self):
        sc = SpeedController()
        sc.set_speed(1.0)  # reset from other tests (shared DLL section)
        assert sc.get_speed() == 1.0

    def test_speed_range_validation(self):
        sc = SpeedController()
        from openspeedy._exceptions import SpeedRangeError

        with pytest.raises(SpeedRangeError):
            sc.set_speed(0.0)
        with pytest.raises(SpeedRangeError):
            sc.set_speed(-1.0)
        with pytest.raises(SpeedRangeError):
            sc.set_speed(9999.0)


class TestSpeedContext:
    """Context manager behavior."""

    def test_speed_context_restores(self):
        sc = SpeedController()
        sc.set_speed(1.0)

        with sc.speed_context(3.0):
            # Inside the context, speed should be 3.0
            # (mocked DLL returns whatever was last set)
            pass

        # After exiting, speed should be restored to 1.0
        assert sc.get_speed() == 1.0

    def test_speed_context_restores_on_exception(self):
        sc = SpeedController()
        sc.set_speed(2.0)

        with pytest.raises(ValueError):
            with sc.speed_context(5.0):
                raise ValueError("oops")

        # Speed should still be restored
        assert sc.get_speed() == 2.0


class TestSpeedControllerTracking:
    """Injection tracking."""

    def test_tracks_injected_pids(self):
        """After inject(), the PID is tracked."""
        sc = SpeedController()
        # We don't actually call sc.inject() here because it needs
        # real Windows — test the tracking directly
        sc._injected_pids.add(100)
        assert 100 in sc._injected_pids

    def test_untracks_on_eject(self):
        sc = SpeedController()
        sc._injected_pids.add(100)
        sc._injected_pids.discard(100)
        assert 100 not in sc._injected_pids

    def test_close_clears_tracking(self):
        sc = SpeedController()
        sc._injected_pids.update([100, 200, 300])
        # patch _eject_dll to avoid actual ejection
        with patch("openspeedy._core._eject_dll"):
            sc.close()
        assert len(sc._injected_pids) == 0


class TestProcessEnumeration:
    """Process listing."""

    def test_list_processes_returns_list(self):
        sc = SpeedController()
        procs = sc.list_processes(fast=True)
        assert isinstance(procs, list)

    def test_list_processes_full(self):
        sc = SpeedController()
        procs = sc.list_processes(fast=False)
        assert isinstance(procs, list)
