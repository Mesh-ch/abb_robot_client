import pytest
import time
from abb_robot_client.rws2 import RWS2, EventLogEntry, JointTarget, RAPIDExecutionState, RobTarget

@pytest.fixture(scope="module")
def client():
    return RWS2()
  
### Test POST methods
    
# def test_ipc_message(client):
#     messages = client.read_ipc_message("MY_QUEUE", timeout=5)
#     assert isinstance(messages, list)
#     for msg in messages:
#         print("IPC Message:", msg)

def test_resetpp(client):
    client.resetpp()
    print("Program pointer reset.")

def test_set_speedratio(client):
    original_speedratio = client.get_speedratio()
    new_speedratio = 50 if original_speedratio != 50 else 60
    client.set_speedratio(new_speedratio)
    updated_speedratio = client.get_speedratio()
    assert updated_speedratio == new_speedratio
    # Restore original speed ratio
    client.set_speedratio(100)
    assert client.get_speedratio() == 100
    
def test_set_digital_io(client):
    io_state = client.get_digital_io("motion_program_error")
    new_state = '1' if io_state == '0' else '0'
    client.set_digital_io("motion_program_error", new_state)
    updated_state = client.get_digital_io("motion_program_error")
    assert updated_state == int(new_state)
    time.sleep(0.5)
    # Restore original state
    client.set_digital_io("motion_program_error", io_state)
    assert client.get_digital_io("motion_program_error") == int(io_state)

def test_start(client):
    client.set_motors_on()
    time.sleep(0.5)  # Wait for motors to turn on
    client.start()
    print("Robot started.")
    
def test_upload_delete_file(client):
    test_content = "Test file content"
    client.upload_file("test_upload.txt", test_content)
    uploaded_content = client.read_file("test_upload.txt")
    if isinstance(uploaded_content, bytes):
        uploaded_content = uploaded_content.decode("utf-8")
    assert uploaded_content == test_content
    client.delete_file("test_upload.txt")
    contents = client.read_file_str("test_upload.txt")  # Should raise an error if file is deleted
    assert "Path does not exist" in contents
    
def test_set_rapid_variable(client):
    variable = client.get_rapid_variable_num("test_num")  # Ensure variable exists
    assert isinstance(variable, (int, float))
    client.set_rapid_variable("test_num", '42')
    assert client.get_rapid_variable("test_num") == '42'
    client.set_rapid_variable("test_num", 0)  # Reset to original value

def test_set_rapid_variable_num(client):
    variable = client.get_rapid_variable_num("test_num")  # Ensure variable exists
    assert isinstance(variable, (int, float))
    client.set_rapid_variable_num("test_num", 42)
    assert client.get_rapid_variable("test_num") == '42'
    client.set_rapid_variable("test_num", 0)  # Reset to original value
    
def test_toggle_motors(client):
    motor_state = client.get_controller_state()
    if motor_state == 'motoron':
        client.set_controller_state('motoroff')
        assert client.get_controller_state() == 'motoroff'
        client.set_controller_state('motoron')
    elif motor_state == 'motoroff':
        client.set_controller_state('motoron')
        assert client.get_controller_state() == 'motoron'
        client.set_controller_state('motoroff')
    else:
        raise Exception(f"Controller in unexpected state: {motor_state}")
        
def test_request_mastership(client):
    client.request_mastership()

def test_release_mastership(client):
    result = client.request_mastership()
    time.sleep(1)  # Simulate some operations while holding mastership
    result = client.release_mastership()
    print(result)
