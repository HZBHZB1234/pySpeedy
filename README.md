# OpenSpeedy · Python 游戏变速库

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/Platform-Windows%2010%2B-lightblue)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-GPL%20v3-green.svg)](LICENSE)

OpenSpeedy 的 Python 绑定库 —— 将 [OpenSpeedy](https://github.com/game1024/OpenSpeedy) 游戏变速器的核心加速功能封装为纯 Python 第三方库。通过向目标 Windows 进程注入 speedpatch DLL 并 Hook 时间相关 API，实现进程时间的加速与减速控制。

**仅限 Windows。** 使用。

---

## 目录

- [安装](#安装)
- [快速开始](#快速开始)
- [核心概念](#核心概念)
- [API 参考](#api-参考)
  - [SpeedController](#speedcontroller)
  - [ProcessInfo](#processinfo)
  - [异常体系](#异常体系)
- [使用示例](#使用示例)
- [技术原理](#技术原理)
- [从源码构建](#从源码构建)
- [要求与限制](#要求与限制)
- [常见问题](#常见问题)
- [许可证](#许可证)

---

## 安装

### 从 PyPI 安装（推荐）

```bash
pip install openspeedy
```

### 从源码安装

```bash
git clone https://github.com/game1024/OpenSpeedy.git
cd OpenSpeedy
pip install -e ".[dev]"
```

安装后会在包目录下包含预编译的 `speedpatch64.dll` 和 `speedpatch32.dll`。

---

## 快速开始

```python
from openspeedy import SpeedController

# 创建控制器（自动加载 speedpatch DLL）
sc = SpeedController()

# 枚举所有运行中的进程
for proc in sc.list_processes():
    if "game" in proc.name.lower():
        print(f"发现游戏进程: PID={proc.pid} 架构={proc.arch}")

# 注入 DLL 到目标进程
sc.inject(1234)

# 设置全局速度倍率（对所有已注入进程生效）
sc.set_speed(2.0)   # 2 倍速
sc.set_speed(0.5)   # 0.5 倍速（慢放）
sc.set_speed(1.0)   # 恢复正常速度

# 使用上下文管理器临时变速
with sc.speed_context(5.0):
    # 此代码块内以 5 倍速运行
    ...
# 退出后自动恢复之前的速度

# 查看状态
print(f"当前速度: {sc.get_speed()}x")
print(f"进程 1234 已启用: {sc.is_enabled(1234)}")

# 清理（弹出所有已注入的进程）
sc.close()
```

---

## 核心概念

### 全局速度因子

速度因子是一个 **全局共享** 的值，写入 DLL 的共享 PE 数据段后，**所有**已注入 speedpatch DLL 的进程都会立即感知变化。这意味着：

- 调用 `sc.set_speed(2.0)` 一次，所有游戏进程同时加速
- 不需要针对每个进程单独设置速度
- 如果需要对不同进程使用不同速度，使用 `enable(pid)` / `disable(pid)` 控制每个进程的开关状态

### 注入 vs 启用

| 操作 | 含义 |
|------|------|
| `inject(pid)` | 将 speedpatch DLL 加载到目标进程中，**并自动启用** |
| `eject(pid)` | 将 DLL 从目标进程中卸载 |
| `enable(pid)` | 对已注入的进程**恢复**变速效果 |
| `disable(pid)` | 对已注入的进程**暂停**变速效果（DLL 仍在进程中，但不修改时间） |

### 快速枚举 vs 完整枚举

```python
# 快速模式（默认）：只返回 PID、名称、架构
procs = sc.list_processes(fast=True)

# 完整模式：额外获取窗口标题、内存、路径、管理员状态
procs = sc.list_processes(fast=False)
```

完整模式需要为每个进程调用 `OpenProcess`，速度较慢。建议先用快速模式筛选，再对关注的进程使用完整模式。

---

## API 参考

### SpeedController

| 方法 | 签名 | 说明 |
|------|------|------|
| `list_processes` | `(fast: bool = True) -> list[ProcessInfo]` | 枚举所有运行中的 Windows 进程 |
| `inject` | `(pid: int) -> None` | 注入 speedpatch DLL 到目标进程并启用 |
| `eject` | `(pid: int) -> None` | 从目标进程卸载 speedpatch DLL |
| `set_speed` | `(factor: float) -> None` | 设置全局速度倍率（0.001 ~ 1000.0） |
| `get_speed` | `() -> float` | 获取当前全局速度倍率 |
| `enable` | `(pid: int) -> None` | 启用指定进程的变速效果 |
| `disable` | `(pid: int) -> None` | 暂停指定进程的变速效果 |
| `is_enabled` | `(pid: int) -> bool` | 检查指定进程是否已启用变速 |
| `speed_context` | `(factor: float) -> Iterator[None]` | 上下文管理器，临时变速后自动恢复 |
| `close` | `() -> None` | 弹出所有由此控制器实例注入的进程 |

`SpeedController` 支持上下文管理器协议：

```python
with SpeedController() as sc:
    sc.inject(pid)
    sc.set_speed(2.0)
# 退出时自动调用 close()
```

### ProcessInfo

```python
@dataclass
class ProcessInfo:
    pid: int              # 进程 ID
    name: str             # 可执行文件名（如 "notepad.exe"）
    arch: str             # "x64" 或 "x86"
    window_title: str | None  # 主窗口标题，无可见窗口时为 None
    memory_kb: int            # 工作集大小（KB），快速模式下为 0
    exe_path: str | None      # 可执行文件完整路径
    is_admin: bool            # 是否以管理员权限运行
```

### ModuleInfo

```python
@dataclass
class ModuleInfo:
    name: str             # 模块文件名（如 "speedpatch64.dll"）
    path: str             # 模块文件完整路径
    base_address: int     # 加载基址
    size: int             # 镜像大小（字节）
```

### 异常体系

所有异常继承自 `OpenSpeedyError`：

```
OpenSpeedyError
├── PlatformNotSupportedError    # 非 Windows 平台
├── DLLNotFoundError             # speedpatch DLL 未找到
├── ProcessAccessDeniedError     # 无法打开进程（权限不足 / 受保护进程）
├── ProcessNotFoundError         # PID 不存在
├── ProcessArchitectureMismatch  # 跨架构注入（v1 限制）
├── InjectionError               # DLL 注入失败
├── EjectionError                # DLL 卸载失败
├── SpeedRangeError              # 速度因子超出范围
└── SpeedControlError            # DLL 操作运行时错误
```

每个异常都携带 Windows 错误码（`e.win_error`）和格式化消息：

```python
from openspeedy import SpeedController, ProcessAccessDeniedError

sc = SpeedController()
try:
    sc.inject(4)  # System 进程 (PID 4)，无法注入
except ProcessAccessDeniedError as e:
    print(f"访问被拒绝: {e}")
    print(f"Win32 错误码: {e.win_error}")
```

---

## 使用示例

### 示例 1：变速指定名称的进程

```python
from openspeedy import SpeedController

def speed_up_game(game_name: str, factor: float):
    """查找并加速指定名称的游戏进程。"""
    sc = SpeedController()
    for proc in sc.list_processes(fast=True):
        if game_name.lower() in proc.name.lower():
            print(f"找到 {proc.name} (PID={proc.pid}, {proc.arch})")
            sc.inject(proc.pid)
    sc.set_speed(factor)
    print(f"已设置 {factor}x 速度")
    return sc  # 调用方负责调用 sc.close()

# 使用
ctrl = speed_up_game("game.exe", 2.0)
# ... 游戏运行中 ...
ctrl.close()
```

### 示例 2：监控进程启动并自动注入

```python
import time
from openspeedy import SpeedController

def watch_and_inject(target_name: str, speed: float):
    """持续监控，发现目标进程后自动注入并变速。"""
    sc = SpeedController()
    sc.set_speed(speed)
    injected = set()

    try:
        while True:
            for proc in sc.list_processes(fast=True):
                if proc.name.lower() == target_name.lower():
                    if proc.pid not in injected:
                        try:
                            sc.inject(proc.pid)
                            injected.add(proc.pid)
                            print(f"已注入 {proc.name} (PID={proc.pid})")
                        except Exception as e:
                            print(f"注入失败 PID={proc.pid}: {e}")
            time.sleep(3)
    except KeyboardInterrupt:
        print("\n正在清理...")
        sc.close()

# 监控 notepad.exe，一旦启动就以 3 倍速运行
watch_and_inject("notepad.exe", 3.0)
```

### 示例 3：使用上下文管理器实现临时加速

```python
from openspeedy import SpeedController

sc = SpeedController()
sc.inject(1234)

# 正常情况下 1 倍速
sc.set_speed(1.0)

def boss_fight():
    """Boss 战时临时加速到 3 倍。"""
    with sc.speed_context(3.0):
        # Boss 战逻辑...
        pass
    # 自动恢复 1 倍速

def grinding():
    """刷材料时 10 倍速。"""
    with sc.speed_context(10.0):
        # 刷材料逻辑...
        pass
```

### 示例 4：按进程分别控制开关

```python
from openspeedy import SpeedController

sc = SpeedController()

# 注入两个游戏进程
sc.inject(1000)  # Game A
sc.inject(2000)  # Game B

sc.set_speed(5.0)  # 全局 5 倍速

# 暂停 Game B 的变速，Game A 保持 5 倍速
sc.disable(2000)

print(sc.is_enabled(1000))  # True
print(sc.is_enabled(2000))  # False

# 恢复 Game B
sc.enable(2000)
```

### 示例 5：获取进程详细信息

```python
from openspeedy import SpeedController

sc = SpeedController()

# 完整枚举，获取所有信息
for proc in sc.list_processes(fast=False):
    if proc.window_title and proc.memory_kb > 100_000:
        print(f"[{proc.pid}] {proc.name}")
        print(f"  窗口: {proc.window_title}")
        print(f"  架构: {proc.arch}")
        print(f"  内存: {proc.memory_kb:,} KB")
        print(f"  路径: {proc.exe_path}")
        print(f"  管理员: {'是' if proc.is_admin else '否'}")
        print()
```

---

## 技术原理

### 架构概览

```
┌─────────────────────────────────────────┐
│  Python 进程                             │
│  ┌───────────────────────────────────┐  │
│  │  SpeedController                  │  │
│  │  ├─ list_processes()  ToolHelp   │  │
│  │  ├─ inject()          CreateRemoteThread
│  │  ├─ set_speed()       SP_SetSpeed │  │
│  │  └─ enable/disable    SP_Enable   │  │
│  └──────────────┬────────────────────┘  │
│                 │ ctypes                  │
│     ┌───────────▼───────────┐            │
│     │  speedpatch64.dll     │ (本地加载) │
│     │  - 共享数据段 (factor) │            │
│     │  - SP_* 导出函数       │            │
│     └───────────────────────┘            │
└─────────────────────────────────────────┘
         │ CreateRemoteThread
         │ + LoadLibraryW
         ▼
┌─────────────────────────────────────────┐
│  目标进程 (游戏)                         │
│  ┌───────────────────────────────────┐  │
│  │  speedpatch64.dll (MinHook)       │  │
│  │  ├─ Sleep              → ÷factor  │  │
│  │  ├─ GetTickCount       → ×factor  │  │
│  │  ├─ QueryPerformanceCounter       │  │
│  │  ├─ timeGetTime                   │  │
│  │  ├─ SetWaitableTimer              │  │
│  │  └─ ... (共 10 个时间 API)         │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
```

### Hook 的时间 API

| 函数 | 所属 DLL | 变速策略 |
|------|----------|----------|
| `Sleep` | kernel32.dll | 睡眠时间 ÷ 速度因子 |
| `SleepEx` | kernel32.dll | 同上 |
| `SetTimer` | user32.dll | 定时器间隔 ÷ 速度因子 |
| `SetWaitableTimer` | kernel32.dll | 到期时间 ÷ 速度因子 |
| `SetWaitableTimerEx` | kernel32.dll | 同上 |
| `timeSetEvent` | winmm.dll | 延迟 ÷ 速度因子 |
| `timeGetTime` | winmm.dll | 基线增量 × 速度因子 |
| `GetTickCount` | kernel32.dll | 同上 |
| `GetTickCount64` | kernel32.dll | 同上 |
| `GetMessageTime` | user32.dll | 同上 |
| `QueryPerformanceCounter` | kernel32.dll | 同上 |
| `GetSystemTimeAsFileTime` | kernel32.dll | 同上 |
| `GetSystemTimePreciseAsFileTime` | kernel32.dll | 同上 |

两种变速策略：

- **除法型**（Sleep / SetTimer / SetWaitableTimer）：将时间参数除以速度因子。例如 2 倍速时 `Sleep(100)` 实际只睡 50ms。
- **增量缩放型**（GetTickCount / QPC / timeGetTime）：维护一个基线快照，每次调用时计算 `baselineDetour + factor * (now - baselineKernel)`。速度因子变化时自动重新基线，保证时间单调递增不会回退。

### 共享数据段

速度因子 `factor` 存储在 DLL 的**共享 PE 数据段**中：

```c
#pragma data_seg("shared")
static std::atomic<double> factor = 1.0;
#pragma data_seg()
#pragma comment(linker, "/section:shared,RWS")
```

Windows 加载器将此段的同一物理内存页映射到每个加载该 DLL 的进程。任何进程写入后，所有进程立即可见。Python 端只需在本地加载 DLL 并调用 `SP_SetSpeed()` 即可全局生效。

### 按进程开关（命名文件映射）

每个注入进程在 `DllMain` 中创建 `CreateFileMapping("OpenSpeedy.<PID>")`，内含一个 bool 标志。Python 通过加载本地 DLL 调用 `SP_Enable(pid)` / `SP_Disable(pid)` 来操作该标志。当进程被禁用时，Hook 函数仍被调用，但 `SpeedFactor()` 返回 1.0（即不做任何修改）。

---

## 从源码构建

### 前提条件

- [Python](https://www.python.org/) 3.8+
- [CMake](https://cmake.org/) 3.16+
- [Visual Studio](https://visualstudio.microsoft.com/) 2019+（含 C++ 桌面开发工作负载）
- [Rust](https://www.rust-lang.org/)（可选，仅构建 bridge EXE 时需要）

### 构建步骤

```bash
# 克隆仓库
git clone https://github.com/game1024/OpenSpeedy.git
cd OpenSpeedy

# 构建 64 位 speedpatch DLL
cmake -S src-bridge/speedpatch -B build64 -A x64
cmake --build build64 --config Release

# 构建 32 位 speedpatch DLL
cmake -S src-bridge/speedpatch -B build32 -A Win32
cmake --build build32 --config Release

# 复制 DLL 到包数据目录
cp build64/Release/speedpatch64.dll openspeedy/data/
cp build32/Release/speedpatch32.dll openspeedy/data/

# 安装开发模式
pip install -e ".[dev]"

# 运行测试
pytest openspeedy/tests/ -v
```

---

## 要求与限制

### 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 或更高版本 |
| Python | 3.8 - 3.12 |
| 架构 | x64 和 x86 均支持 |
| 权限 | 注入管理员进程需要以管理员身份运行 Python |

### v1 架构限制

**同名架构注入**：64 位 Python 解释器只能向 64 位目标进程注入；32 位 Python 只能向 32 位目标注入。这是因为 `LoadLibraryW` 在调用进程 `kernel32.dll` 中的地址必须与目标进程中的地址匹配。这与原始 OpenSpeedy 使用两个独立桥接进程的原因相同。如需向不同架构注入，请使用对应架构的 Python 解释器。

### 安全注意事项

- **杀毒软件**：DLL 注入行为可能被安全软件标记。请将 `openspeedy/data/` 目录添加到白名单。
- **反作弊系统**：带有内核级反作弊的游戏（EAC、BattlEye、Vanguard、Ricochet 等）**会检测并阻止**此工具。在这些游戏中使用可能导致账号被封禁。
- **在线竞技游戏**：不建议在竞技类在线游戏中使用本工具。这违反大多数游戏的服务条款。
- **仅供学习研究**：本工具的设计目的是学习 Windows API Hook 和进程注入技术。

---

## 常见问题

<details>
<summary><strong>Q: 注入失败，提示"访问被拒绝"？</strong></summary>

以管理员身份运行 Python。某些进程（特别是系统服务和以管理员身份运行的程序）需要管理员权限才能打开。
</details>

<details>
<summary><strong>Q: 变速后游戏崩溃？</strong></summary>

过高的速度倍率（如 100x 以上）可能导致游戏物理引擎计算异常或除零错误。建议在 0.1x ~ 10x 范围内使用。
</details>

<details>
<summary><strong>Q: 注入成功但没有加速效果？</strong></summary>

确认：
1. `sc.is_enabled(pid)` 返回 `True`
2. `sc.get_speed()` 返回预期值
3. 目标进程确实是 32 位游戏运行在 64 位系统上（检查 `arch` 字段）
</details>

<details>
<summary><strong>Q: 如何在 macOS / Linux 上使用？</strong></summary>

无法使用。此库依赖 Windows 特有的 API（`CreateRemoteThread`、`LoadLibrary`、共享 PE 数据段等），仅在 Windows 上可用。
</details>

---

## 许可证

- `openspeedy` Python 库：[GPL v3](LICENSE)
- 内置 `speedpatch*.dll` 包含 [MinHook](https://github.com/TsudaKageyu/minhook)，使用 BSD 2-Clause 许可证

---

## 相关链接

- [OpenSpeedy 原始项目](https://github.com/game1024/OpenSpeedy) — Tauri + Rust + React 桌面应用
- [MinHook](https://github.com/TsudaKageyu/minhook) — API Hook 库
