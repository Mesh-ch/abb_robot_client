import inspect

from abb_robot_client import RWS, RWS2, RWSMock
from abb_robot_client.rws_interface import RWSLike
import abb_robot_client.rws as rws1_mod
import abb_robot_client.rws2 as rws2_mod


COMMON_METHODS = [
    # Execution / state
    "start",
    "stop",
    "resetpp",
    "get_execution_state",
    "get_controller_state",
    "set_controller_state",
    "set_motors_on",
    "set_motors_off",
    "get_operation_mode",
    "get_speedratio",
    "set_speedratio",
    "is_mastered",
    # Tasks
    "get_tasks",
    "activate_task",
    "deactivate_task",
    # IO
    "get_digital_io",
    "set_digital_io",
    "get_analog_io",
    "set_analog_io",
    # RAPID variables
    "get_rapid_variable",
    "get_rapid_variable_num",
    "set_rapid_variable",
    "set_rapid_variable_num",
    # Files
    "get_ramdisk_path",
    "read_file",
    "read_file_str",
    "upload_file",
    "delete_file",
    # Misc
    "read_event_log",
    "get_mechunits",
    # Geometry
    "get_jointtarget",
    "get_robtarget",
]


def test_common_methods_present_on_all():
    for cls in (RWS, RWS2, RWSMock):
        for name in COMMON_METHODS:
            assert hasattr(cls, name), f"{cls.__name__} missing method: {name}"
            attr = getattr(cls, name)
            assert callable(attr), f"{cls.__name__}.{name} is not callable"


def test_mock_conforms_to_protocol():
    mock = RWSMock()
    assert isinstance(mock, RWSLike), "RWSMock must conform to RWSLike Protocol"


def test_taskstate_type_field_naming():
    # RWS1 TaskState uses `type_` (to avoid keyword); RWS2 uses `type`
    assert hasattr(rws1_mod.TaskState, "type_"), "RWS.TaskState should expose type_"
    assert hasattr(rws2_mod.TaskState, "type"), "RWS2.TaskState should expose type"


def test_mock_geometry_return_types():
    from abb_robot_client.rws import JointTarget, RobTarget

    mock = RWSMock()
    jt = mock.get_jointtarget()
    rt = mock.get_robtarget()
    assert isinstance(jt, JointTarget)
    assert isinstance(rt, RobTarget)
