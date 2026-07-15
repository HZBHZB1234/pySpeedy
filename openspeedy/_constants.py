"""
Win32 API constants used across the openspeedy package.

Grouped by API surface for readability. All values are from the Windows SDK.
"""

# ---------------------------------------------------------------------------
# Process access rights
# ---------------------------------------------------------------------------
PROCESS_TERMINATE = 0x0001
PROCESS_CREATE_THREAD = 0x0002
PROCESS_SET_SESSIONID = 0x0004
PROCESS_VM_OPERATION = 0x0008
PROCESS_VM_READ = 0x0010
PROCESS_VM_WRITE = 0x0020
PROCESS_DUP_HANDLE = 0x0040
PROCESS_CREATE_PROCESS = 0x0080
PROCESS_SET_QUOTA = 0x0100
PROCESS_SET_INFORMATION = 0x0200
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_SUSPEND_RESUME = 0x0800
PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
PROCESS_ALL_ACCESS = 0x1FFFFF

# Commonly needed combination for DLL injection
PROCESS_INJECT_ACCESS = (
    PROCESS_CREATE_THREAD
    | PROCESS_QUERY_INFORMATION
    | PROCESS_VM_OPERATION
    | PROCESS_VM_WRITE
    | PROCESS_VM_READ
)

PROCESS_EJECT_ACCESS = (
    PROCESS_CREATE_THREAD
    | PROCESS_QUERY_INFORMATION
    | PROCESS_VM_OPERATION
)

# ---------------------------------------------------------------------------
# Memory allocation
# ---------------------------------------------------------------------------
MEM_COMMIT = 0x00001000
MEM_RESERVE = 0x00002000
MEM_RELEASE = 0x00008000
MEM_DECOMMIT = 0x00004000
PAGE_READWRITE = 0x04
PAGE_EXECUTE_READWRITE = 0x40

# ---------------------------------------------------------------------------
# ToolHelp snapshots
# ---------------------------------------------------------------------------
TH32CS_SNAPPROCESS = 0x00000002
TH32CS_SNAPMODULE = 0x00000008
TH32CS_SNAPTHREAD = 0x00000004

# ---------------------------------------------------------------------------
# File mapping
# ---------------------------------------------------------------------------
FILE_MAP_ALL_ACCESS = 0x000F001F
FILE_MAP_READ = 0x00000004
FILE_MAP_WRITE = 0x00000002
SECTION_QUERY = 0x0001
SECTION_MAP_WRITE = 0x0002
SECTION_MAP_READ = 0x0004
SECTION_MAP_EXECUTE = 0x0008
SECTION_EXTEND_SIZE = 0x0010
SECTION_ALL_ACCESS = 0x000F001F
STANDARD_RIGHTS_REQUIRED = 0x000F0000
INVALID_HANDLE_VALUE_SIGNED = -1

# ---------------------------------------------------------------------------
# Wait / synchronization
# ---------------------------------------------------------------------------
INFINITE = 0xFFFFFFFF
WAIT_OBJECT_0 = 0x00000000
WAIT_TIMEOUT = 0x00000102
WAIT_FAILED = 0xFFFFFFFF
WAIT_ABANDONED_0 = 0x00000080

# ---------------------------------------------------------------------------
# Token / security
# ---------------------------------------------------------------------------
TOKEN_QUERY = 0x0008
TOKEN_ADJUST_PRIVILEGES = 0x0020
TokenElevation = 20  # TOKEN_INFORMATION_CLASS

# ---------------------------------------------------------------------------
# Process name format
# ---------------------------------------------------------------------------
PROCESS_NAME_WIN32 = 0
PROCESS_NAME_NATIVE = 1

# ---------------------------------------------------------------------------
# Module filter flags for EnumProcessModulesEx
# ---------------------------------------------------------------------------
LIST_MODULES_DEFAULT = 0x00
LIST_MODULES_32BIT = 0x01
LIST_MODULES_64BIT = 0x02
LIST_MODULES_ALL = 0x03

# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------
ERROR_SUCCESS = 0
ERROR_ACCESS_DENIED = 5
ERROR_INVALID_PARAMETER = 87
ERROR_PIPE_CONNECTED = 535
ERROR_BROKEN_PIPE = 109
ERROR_NO_DATA = 232
ERROR_PIPE_NOT_CONNECTED = 233
ERROR_MORE_DATA = 234

# ---------------------------------------------------------------------------
# Window enumeration
# ---------------------------------------------------------------------------
GW_OWNER = 4
GW_HWNDFIRST = 0
GW_HWNDLAST = 1
GW_HWNDNEXT = 2
GW_HWNDPREV = 3
GW_CHILD = 5
GW_ENABLEDPOPUP = 6

# ---------------------------------------------------------------------------
# Speed factor limits
# ---------------------------------------------------------------------------
SPEED_MIN = 0.001
SPEED_MAX = 1000.0
SPEED_DEFAULT = 1.0
