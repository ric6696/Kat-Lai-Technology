import secrets, string, pytest
from fastapi.testclient import TestClient
from ..main import app
from ..internal.Authentication import register_user_with_unhashed_password
from ..database import get_user_db
from ..database import DeviceDataManager, get_device_db
from ..models.Device import ScheduleData, DeviceParamters
from datetime import datetime, timedelta, timezone

from .Utils.registration import (
    read_serial_number,
    get_test_access_token,
    delete_manager,
)


@pytest.fixture(scope="session")
def device_db():
    return get_device_db()


@pytest.fixture(scope="session")
def test_client():
    return TestClient(app)


@pytest.fixture(scope="session")
def get_username():
    # TODO: Handle FileNotFound Exception!!!
    with open("./app/tests/TestParameters.txt") as f:
        username = f.readline().replace("username = ", "").strip()
        if not (username):
            raise RuntimeError("Username is not provided! Provide a valid information")
        print(f"Base Username: {username}")
        return username


@pytest.fixture(scope="session")
def get_serial_number():
    return read_serial_number()


@pytest.fixture(scope="session")
def get_password():
    password = "".join(
        secrets.choice(string.ascii_letters + string.digits) for i in range(20)
    )
    print(f"Password: {password}")
    return password


@pytest.fixture(scope="session")
def get_root_token(test_client: TestClient, get_username: str, get_password: str):
    user_data = {
        "username": get_username,
        "email": "string",
        "full_name": "string",
        "disabled": False,
        "unhashed_password": get_password,
        "scopes": ["Admin"],
    }
    # TODO: Handle Exceptions
    register_user_with_unhashed_password(user_data, get_user_db())
    token = get_test_access_token(test_client, get_username, get_password)
    yield token
    delete_manager(test_client, get_username, token)


@pytest.fixture(scope="session")
def register_testing_device(device_db: DeviceDataManager, get_serial_number: str):
    try:
        print("Registering Device")
        yield device_db._register_testing_device(get_serial_number[4:])
    except RuntimeError as err:
        pytest.fail(f"Failed to register device, {err}")

    try:
        print("Deregistering Device")
        device_db._deregister_testing_device(get_serial_number[4:])
    except RuntimeError as err:
        pytest.fail(
            f"Failed to deregister device, {err}. Please clean database manually"
        )


@pytest.fixture(scope="session")
def v_schedule_data():
    return ScheduleData(
        start_time=datetime.fromisoformat(
            str(datetime.now(timezone.utc) + timedelta(minutes=20))
        ),
        end_time=datetime.fromisoformat(
            str(datetime.now(timezone.utc) + timedelta(minutes=40))
        ),
        scheduled_paramters=DeviceParamters(element="Wood", intensity=50),
    )


@pytest.fixture()
def get_schedule_data(
    get_serial_number: str,
    v_schedule_data: ScheduleData,
    register_testing_device: str,
):
    db: DeviceDataManager = get_device_db()
    try:
        print("Putting Schedule")
        db.put_schedule(get_serial_number, v_schedule_data)
    except (RuntimeError, ValueError) as err:
        pytest.fail(f"Failed to put schedule, {err}")

    yield v_schedule_data

    try:
        print("Removing Schedule")
        db.remove_schedule(get_serial_number, v_schedule_data.start_time)
    except (
        RuntimeError,
        ValueError,
        TypeError,
    ) as err:
        pytest.fail(f"Failed to remove schedule {err}")
