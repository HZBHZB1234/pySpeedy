"""
Tests for data types.
"""

from openspeedy._types import ModuleInfo, ProcessInfo


class TestProcessInfo:
    def test_defaults(self):
        pi = ProcessInfo(pid=100, name="test.exe")
        assert pi.pid == 100
        assert pi.name == "test.exe"
        assert pi.arch == "x64"
        assert pi.window_title is None
        assert pi.memory_kb == 0
        assert pi.exe_path is None
        assert pi.is_admin is False

    def test_full(self):
        pi = ProcessInfo(
            pid=200,
            name="game.exe",
            arch="x86",
            window_title="Game Window",
            memory_kb=102400,
            exe_path="C:\\Games\\game.exe",
            is_admin=True,
        )
        assert pi.pid == 200
        assert pi.arch == "x86"
        assert pi.window_title == "Game Window"
        assert pi.memory_kb == 102400
        assert pi.exe_path == "C:\\Games\\game.exe"
        assert pi.is_admin is True

    def test_equality(self):
        a = ProcessInfo(pid=1, name="a.exe")
        b = ProcessInfo(pid=1, name="a.exe")
        assert a == b

    def test_hashable(self):
        # dataclass instances are hashable (unsafe_hash=False default
        # but they compare by value)
        pi = ProcessInfo(pid=1, name="a.exe")
        _ = {pi: "value"}  # should not raise


class TestModuleInfo:
    def test_fields(self):
        mi = ModuleInfo(
            name="speedpatch64.dll",
            path="C:\\tools\\speedpatch64.dll",
            base_address=0x7FFE0000,
            size=65536,
        )
        assert mi.name == "speedpatch64.dll"
        assert mi.base_address == 0x7FFE0000
        assert mi.size == 65536
