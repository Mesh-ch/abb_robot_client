import pytest
from abb_robot_client.rws2 import RWS2, EventLogEntry, JointTarget, RAPIDExecutionState, RobTarget

@pytest.fixture(scope="module")
def client():
    return RWS2()

## Test GET methods
def test_get_tasks(client):
    tasks = client.get_tasks()
    assert isinstance(tasks, dict)
    assert "T_ROB1" in tasks

def test_get_jointtargets(client):
    jointtargets = client.get_jointtarget()
    assert isinstance(jointtargets, JointTarget)
    
def test_get_execution_state(client):
    state = client.get_execution_state()
    assert isinstance(state, RAPIDExecutionState)

def test_get_ramdisk_paths(client):
    paths = client.get_ramdisk_path()
    assert paths == '/TEMP/', f"Unexpected RAM disk path: {paths}"
    
def test_get_controller_state(client):
    state = client.get_controller_state()
    assert state in ['init','motoron', 'motoroff', 'guardstop', 'emergencystop', 'emergencystopreset', 'sysfail'], f"Unexpected controller state: {state}"

def test_get_operation_mode(client):
    mode = client.get_operation_mode()
    assert mode in ['AUTO', 'MAN', 'MANFS'], f"Unexpected operation mode: {mode}"
    
def test_get_digital_io(client):
    signal_value = client.get_digital_io("Auto", network="IntBus", unit="IoPanel")
    assert isinstance(signal_value, int)
    assert signal_value == 1, {"Expected 'Auto' signal to be 1 (True)"}
    signal_value = client.get_digital_io("motion_program_error")
    assert isinstance(signal_value, int)
    assert signal_value == 0, {"Expected 'motion_program_error' signal to be 0 (False)"}
    
def test_get_analog_io(client):
    signal_value = client.get_analog_io("motion_program_preempt")
    assert isinstance(signal_value, float)
    
def test_get_rapid_variable(client):
    var_value = client.get_rapid_variable("MOTION_PROGRAM_CMD_MOVEL", "T_ROB1")
    assert int(var_value) == 3, f"Unexpected RAPID Variable 'MOTION_PROGRAM_CMD_MOVEL' in 'T_ROB1': {var_value}"

def test_get_rapid_variable_num(client):
    var_value = client.get_rapid_variable_num("MOTION_PROGRAM_CMD_MOVEL", "T_ROB1")
    assert var_value == 3, f"Unexpected RAPID Variable 'MOTION_PROGRAM_CMD_MOVEL' in 'T_ROB1': {var_value}"
    
def test_read_file(client):
    file_contents = client.read_file("motion_program_exec.mod", directory="$HOME")
    # assert isinstance(file_contents, dict)  # Assuming the API returns JSON content
    assert isinstance(file_contents, bytes), f"Unexpected file content type: {type(file_contents)}"
    assert file_contents.startswith(b"MODULE motion_program_exec"), f"Unexpected file content: {file_contents}"

def test_read_event_log(client):
    elog = client.read_event_log()
    assert isinstance(elog[0], EventLogEntry), f"Unexpected event log entry type: {type(elog[0])}"

def test_get_robtarget(client):
    robtarget = client.get_robtarget()
    assert isinstance(robtarget, RobTarget), f"Unexpected robtarget type: {type(robtarget)}"
    print(robtarget)

def test_get_speedratio(client):
    speedratio = client.get_speedratio()
    assert 0<=speedratio<=100
    
    
# def test_get_ipc_queue(client):
#     messages = client.get_ipc_queue("testq")
#     assert isinstance(messages, dict)
#     assert "messages" in messages
#     assert isinstance(messages["messages"], list)
    
# def test_ipc_message(client):
#     messages = client.read_ipc_message("MY_QUEUE", timeout=5)
#     assert isinstance(messages, list)
#     for msg in messages:
#         print("IPC Message:", msg)
        
        
if __name__ == "__main__":
    rws = RWS2()
    #### GET REQUESTS ####
    # test_get_tasks(rws)
    test_get_jointtargets(rws)
    # test_get_execution_state(rws)
    # test_get_ramdisk_paths(rws)
    # test_get_controller_state(rws)
    # test_get_operation_mode(rws)
    # test_get_digital_io(rws)
    # test_get_analog_io(rws)
    # test_get_rapid_variable(rws)
    # test_get_rapid_variable_num(rws)
    # test_read_file(rws)
    # test_read_event_log(rws)
    # test_read_event_log(rws)
    test_get_robtarget(rws)
    # test_get_speedratio(rws)
    # test_get_ipc_queue(rws)
    # test_ipc_message(rws)
