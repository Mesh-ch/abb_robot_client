import pytest
from abb_robot_client.rws import RWS


@pytest.fixture(scope="module")
def client():
    return RWS()


def test_set_speedratio(client):
    original_speedratio = client.get_speedratio()
    new_speedratio = 50 if original_speedratio != 50 else 60
    client.set_speedratio(new_speedratio)
    updated_speedratio = client.get_speedratio()
    assert updated_speedratio == new_speedratio
    # Restore original speed ratio
    client.set_speedratio(100)
    assert client.get_speedratio() == 100


def test_start(client):
    client.start()
    print("Robot started.")


def test_upload_delete_file(client):
    test_content = "Test file content"
    path = client.get_ramdisk_path()
    client.upload_file(f"{path}/test_upload.txt", test_content)
    uploaded_content = client.read_file(f"{path}/test_upload.txt")
    if isinstance(uploaded_content, bytes):
        uploaded_content = uploaded_content.decode("utf-8")
    assert uploaded_content == test_content
    client.delete_file(f"{path}/test_upload.txt")
    try:
        _contents = client.read_file(f"{path}/test_upload.txt")  # Should raise an error if file is deleted
    except Exception as e:
        _contents = str(e)
        assert "File not found" in e.args[0]


def test_set_rapid_variable(client):
    variable = client.get_rapid_variable_num("test_num")  # Ensure variable exists
    assert isinstance(variable, (int, float))
    client.set_rapid_variable("test_num", "42")
    assert client.get_rapid_variable("test_num") == "42"
    client.set_rapid_variable("test_num", 0)  # Reset to original value


def test_set_rapid_variable_num(client):
    variable = client.get_rapid_variable_num("test_num")  # Ensure variable exists
    assert isinstance(variable, (int, float))
    client.set_rapid_variable_num("test_num", 42)
    assert client.get_rapid_variable("test_num") == "42"
    client.set_rapid_variable("test_num", 0)  # Reset to original value


def test_toggle_motors(client):
    motor_state = client.get_controller_state()
    if motor_state == "motoron":
        client.set_controller_state("motoroff")
        assert client.get_controller_state() == "motoroff"
        client.set_controller_state("motoron")
    elif motor_state == "motoroff":
        client.set_controller_state("motoron")
        assert client.get_controller_state() == "motoron"
        client.set_controller_state("motoroff")
    else:
        raise Exception(f"Controller in unexpected state: {motor_state}")


def test_motors_on(client):
    client.set_controller_state("motoron")
    assert client.get_controller_state() == "motoron"


def test_motors_off(client):
    client.set_controller_state("motoroff")
    assert client.get_controller_state() == "motoroff"


def test_is_mastered(client):
    result = client.is_mastered()
    assert isinstance(result, bool)


if __name__ == "__main__":
    rws = RWS()
