from ...models.Device import MasterData
from fastapi.testclient import TestClient
from ...database import DeviceDataManager, get_device_db
from ...internal.Authentication import validate_scopes


def read_serial_number():
    # TODO: Handle FileNotFound Exception!!!
    with open("./app/tests/TestParameters.txt") as f:
        _ = f.readline()
        serial_number = f.readline().replace("serial-number = ", "").strip()
        if not (serial_number):
            raise RuntimeError(
                "Serial-number is not provided! Provide a valid information"
            )
        if serial_number[:4] != "TEST":
            raise RuntimeError("Serial-number should start with 'TEST'")
        return serial_number


def register_user_with_scopes(
    client: TestClient, username: str, password: str, token: str, scopes: str
) -> None:
    response = client.put(
        "/users/register",
        headers={"Authorization": f"Bearer {token}"},
        data={
            "username": username,
            "password": password,
            "scope": scopes,
        },
    )
    assert (
        response.status_code == 200
    ), f"Failed to register user with scopes{response.json()}"
    return None


def get_test_access_token(
    client: TestClient, username: str, password: str, scopes: list[str] | None = None
) -> str:
    if not scopes:
        scopes = ["Admin"]

    try:
        scopes_str = validate_scopes(scopes)
    except ValueError as err:
        raise AssertionError("Invalid scope provided!") from err

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "charset": "UTF-8",
    }

    response = client.post(
        "/token",
        headers=headers,
        data={
            "username": username,
            "password": password,
            "scope": scopes_str,
        },
    )
    assert response.status_code == 200, f"Token generation failed!{response.json()}"
    return response.json()["access_token"]


def delete_manager(client: TestClient, username: str, token: str) -> None:
    response = client.delete(
        f"/users/delete?username={username}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 200, "User deletion failed!"


def put_master_order(
    serial_number: str, data: MasterData, db: DeviceDataManager = get_device_db()
):
    try:
        db.put_master_order(serial_number, data)
    except (ValueError, RuntimeError) as err:
        print(err)
        raise AssertionError("Failed to put master order") from err


def remove_master_order(serial_number: str, db: DeviceDataManager = get_device_db()):
    try:
        db._remove_master_order(serial_number)
    except (ValueError, RuntimeError) as err:
        print(err)
        raise AssertionError("Failed to remove master order") from err


def remove_master_history(serial_number: str, db: DeviceDataManager = get_device_db()):
    try:
        db._remove_master_history(serial_number)
    except (ValueError, RuntimeError) as err:
        print(err)
        raise AssertionError("Failed to remove master history") from err
