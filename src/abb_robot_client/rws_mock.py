from __future__ import annotations

from typing import Any, Dict, List, Optional
from dataclasses import dataclass
import numpy as np

from .rws_interface import RWSLike, TaskStateLike, RAPIDExecutionStateLike, EventLogEntryLike

# Reuse common geometry types from RWS 1.0
from .rws import JointTarget, RobTarget


@dataclass
class _ExecState:
    ctrlexecstate: Any
    cycle: Any


class _TaskState:
    def __init__(
        self,
        name: str,
        type_val: str,
        taskstate: str = "ready",
        excstate: str = "stopped",
        active: bool = True,
        motiontask: bool = True,
    ) -> None:
        self.name = name
        self._type_val = type_val
        self.taskstate = taskstate
        self.excstate = excstate
        self.active = active
        self.motiontask = motiontask

    @property
    def type_(self) -> str:  # alias for unified interface
        return self._type_val


@dataclass
class _EventLogEntry:
    seqnum: int
    msgtype: int
    code: int
    title: str
    desc: str
    # Extra fields for completeness
    tstamp: Optional[str] = None
    args: Optional[List[Any]] = None
    conseqs: Optional[str] = None
    causes: Optional[str] = None
    actions: Optional[str] = None


class RWSMock(RWSLike):
    """Mock Robot Web Services client returning hardcoded data.

    This mock mirrors the shared API defined in `rws_interface.RWSLike` so
    it can stand in for `rws.RWS` or `rws2.RWS2` in tests or local runs.
    """

    def __init__(self) -> None:
        self._exec_state = "stopped"
        self._speedratio = 100
        self._controller_state = "motoroff"
        self._opmode = "AUTO"
        self._tasks: Dict[str, _TaskState] = {
            "T_ROB1": _TaskState(
                "T_ROB1", type_val="NORMAL", taskstate="ready", excstate=self._exec_state, active=True, motiontask=True
            )
        }
        # IO state
        self._dio: Dict[str, int] = {
            "Auto": 1,
            "motion_program_error": 0,
            "motion_program_log_motion": 0,
        }
        self._aio: Dict[str, float] = {
            "motion_program_preempt": 0.0,
        }
        # RAPID variables (all stored as strings, like controller encoding)
        self._rapid: Dict[str, str] = {
            "T_ROB1/MOTION_PROGRAM_CMD_MOVEL": "3",
            "T_ROB1/test_num": "0",
        }
        # Filesystem (simple virtual store keyed by path)
        self._files: Dict[str, bytes] = {
            "$HOME/motion_program_exec.mod": b"MODULE motion_program_exec\nENDMODULE\n",
            "/TEMP/motion_program_exec.mod": b"MODULE motion_program_exec\nENDMODULE\n",
        }

    # Execution / state
    def start(self, cycle: str = "asis", tasks: Optional[List[str]] = None) -> None:  # noqa: D401
        # No-op; change execution state to simulate run
        if self._controller_state != "motoron":
            raise RuntimeError("Cannot start execution: controller is not in 'motoron' state")
        self._exec_state = "running"

    def stop(self) -> None:
        self._exec_state = "stopped"

    def resetpp(self) -> None:
        pass

    def get_execution_state(self) -> RAPIDExecutionStateLike:
        return _ExecState(ctrlexecstate=self._exec_state, cycle="forever")

    def get_controller_state(self) -> str:
        return self._controller_state

    def set_controller_state(self, ctrl_state: str) -> None:
        if ctrl_state not in {"motoron", "motoroff"}:
            raise ValueError("ctrl_state must be 'motoron' or 'motoroff'")
        self._controller_state = ctrl_state

    def set_motors_on(self) -> None:
        self._controller_state = "motoron"

    def set_motors_off(self) -> None:
        self._controller_state = "motoroff"

    def get_operation_mode(self) -> str:
        return self._opmode

    def get_speedratio(self) -> int:
        return int(self._speedratio)

    def set_speedratio(self, speedratio: int) -> None:
        sr = int(speedratio)
        if not 0 <= sr <= 100:
            raise ValueError("speedratio must be 0..100")
        self._speedratio = sr

    def is_mastered(self) -> bool:
        return False

    # Tasks
    def get_tasks(self) -> Dict[str, TaskStateLike]:
        return dict(self._tasks)

    def activate_task(self, task: str) -> None:
        if task in self._tasks:
            self._tasks[task].active = True

    def deactivate_task(self, task: str) -> None:
        if task in self._tasks:
            self._tasks[task].active = False

    # IO
    def get_digital_io(self, signal: str, network: str = "", unit: str = "") -> int:
        return int(self._dio.get(signal, 0))

    def set_digital_io(self, signal: str, value: bool | int, network: str = "", unit: str = "") -> None:
        self._dio[signal] = 1 if bool(value) else 0

    def get_analog_io(self, signal: str, network: str = "", unit: str = "") -> float:
        return float(self._aio.get(signal, 0.0))

    def set_analog_io(self, signal: str, value: int | float, network: str = "", unit: str = "") -> None:
        self._aio[signal] = float(value)

    # RAPID variables
    def _qualify_var(self, var: str, task: str) -> str:
        return f"{task}/{var}" if task else var

    def get_rapid_variable(self, var: str, task: str = "T_ROB1") -> str:
        key = self._qualify_var(var, task)
        return self._rapid.get(key, "0")

    def get_rapid_variable_num(self, var: str, task: str = "T_ROB1") -> float:
        return float(self.get_rapid_variable(var, task))

    def get_rapid_variable_num_array(self, var: str, task: str = "T_ROB1") -> np.ndarray:
        val_str = self.get_rapid_variable(var, task)
        try:
            # Assume comma-separated values
            return np.array([float(v.strip()) for v in val_str.split(",")])
        except ValueError:
            return np.array([])

    def set_rapid_variable(self, var: str, value: str | int | float, task: str = "T_ROB1") -> None:
        key = self._qualify_var(var, task)
        self._rapid[key] = str(value)

    def set_rapid_variable_num(self, var: str, val: float, task: str = "T_ROB1") -> None:
        self.set_rapid_variable(var, str(val), task)

    # Files
    def get_ramdisk_path(self) -> str:
        return "/TEMP/"

    def _resolve_path(self, filename: str, directory: Optional[str]) -> str:
        if directory:
            return f"{directory.rstrip('/')}/{filename.lstrip('/')}"
        return filename

    def read_file(self, filename: str, directory: str | None = None) -> bytes:
        path = self._resolve_path(filename, directory)
        data = self._files.get(path)
        if data is None:
            raise FileNotFoundError(f"Path does not exist: {path}")
        return data

    def read_file_str(self, filename: str, directory: str | None = None) -> str:
        try:
            return self.read_file(filename, directory).decode("utf-8")
        except FileNotFoundError as e:
            return str(e)

    def upload_file(self, filename: str, content: str | bytes, directory: str | None = None) -> None:
        path = self._resolve_path(filename, directory)
        if isinstance(content, str):
            content = content.encode("utf-8")
        self._files[path] = content

    def delete_file(self, filename: str, directory: str | None = None) -> None:
        path = self._resolve_path(filename, directory)
        if path in self._files:
            del self._files[path]

    # Event log
    def read_event_log(self) -> List[EventLogEntryLike]:
        return [
            _EventLogEntry(
                seqnum=1,
                msgtype=1,
                code=0,
                title="Mock event",
                desc="This is a mock event log entry",
            )
        ]

    # Misc
    def get_mechunits(self) -> List[str]:
        return ["ROB_1"]

    # Geometry helpers
    def get_jointtarget(self, mechunit: str = "ROB_1") -> JointTarget:
        return JointTarget(robax=np.zeros(6), extax=np.zeros(6))

    def get_robtarget(
        self, mechunit: str = "ROB_1", tool: str = "tool0", wobj: str = "wobj0", coordinate: str = "Base"
    ) -> RobTarget:
        return RobTarget(
            trans=np.zeros(3),
            rot=np.array([1.0, 0.0, 0.0, 0.0]),
            robconf=np.array([0, 0, 0, 0]),
            extax=np.zeros(6),
        )
