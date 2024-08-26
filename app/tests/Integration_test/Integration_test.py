import pytest
from fastapi.testclient import TestClient
from ...models.Device import ScheduleData, DeviceParamters, MasterData
from ...database import DeviceDataManager, get_device_db
from datetime import datetime
from ..Utils.registration import (
    remove_master_history,
    remove_master_order,
    put_master_order,
)


def test_user_touch_allowed_false(
    test_client: TestClient,
    get_root_token: str,
    get_serial_number: str,
    register_testing_device: str,
) -> None:
    data = {
        "updates": {"element": "Fire", "intensity": 99},
        "user_touch_allowed": False,
    }
    response = test_client.post(
        f"/manager/put-master-order?serial_number={get_serial_number}",
        headers={"Authorization": f"Bearer {get_root_token}"},
        json=data,
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    response = test_client.post(
        f"/device/fetch-control?serial={get_serial_number}&refresh=false",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    data = {"updates": {"element": "Wood", "intensity": 66}}
    response = test_client.post(
        f"/mobile/update-state?serial_number={get_serial_number}",
        headers={"Authorization": f"Bearer {get_root_token}"},
        json=data,
    )
    assert response.status_code == 403, f"Expected 403 Forbidden, got {response.json()}"

    remove_master_history(get_serial_number)


def test_user_touch_allowed_true(
    test_client: TestClient,
    get_root_token: str,
    get_serial_number: str,
    register_testing_device: str,
) -> None:
    response = test_client.post(
        f"/manager/put-master-order?serial_number={get_serial_number}",
        headers={"Authorization": f"Bearer {get_root_token}"},
        json={
            "updates": {"element": "Wood", "intensity": 50},
            "user_touch_allowed": True,
        },
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    response = test_client.post(
        f"/device/fetch-control?serial={get_serial_number}&refresh=false",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    response = test_client.get(
        f"/mobile/get-device-state?serial_number={get_serial_number}",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    data = {"updates": {"element": "Fire", "intensity": 40}}
    response = test_client.post(
        f"mobile/update-state?serial_number={get_serial_number}",
        headers={"Authorization": f"Bearer {get_root_token}"},
        json=data,
    )
    assert response.status_code == 202, f"Expected 200 OK, got {response.json()}"

    response = test_client.post(
        f"/device/fetch-control?serial={get_serial_number}&refresh=false",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    response = test_client.get(
        f"/mobile/get-device-state?serial_number={get_serial_number}",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    remove_master_history(get_serial_number)


def test_schedule(get_serial_number) -> None:
    db: DeviceDataManager = get_device_db()
    data = ScheduleData(
        start_time=datetime.fromisoformat("2068-07-11 09:17:24.049946+00:00"),
        end_time=datetime.fromisoformat("2068-07-11 10:17:24.049946+00:00"),
        scheduled_paramters=DeviceParamters(
            element="Fire",
            intensity=0,
        ),
    )
    try:
        db.put_schedule(get_serial_number, data)
    except (RuntimeError, ValueError):
        pytest.fail("Unexpected error occurred, failed to put schedule!")

    try:
        db.get_schedules(get_serial_number)
    except (RuntimeError, ValueError):
        pytest.fail("Unexpected error occurred, failed to get schedules!")

    try:
        db.remove_schedule(get_serial_number, data.start_time)
    except (RuntimeError, ValueError, TypeError):
        pytest.fail("Unexpected error occurred, failed to remove schedule!")


def test_fetch_control_refresh(
    test_client,
    get_serial_number,
    get_root_token,
) -> None:
    putData = MasterData(
        updates=DeviceParamters(element="Wood", intensity=50),
        user_touch_allowed=False,
    )
    put_master_order(get_serial_number, putData)

    response = test_client.post(
        f"/device/fetch-control?serial={get_serial_number}&refresh=false",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    response = test_client.post(
        f"/device/fetch-control?serial={get_serial_number}&refresh=false",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 404, f"Expected 404 Not Found, got {response.json()}"

    remove_master_order(get_serial_number)
    remove_master_history(get_serial_number)


def test_fetch_control_interrupt(
    test_client: TestClient,
    get_serial_number: str,
    get_root_token: str,
    register_testing_device: str,
) -> None:
    putData = MasterData(
        updates=DeviceParamters(element="Fire", intensity=100),
        user_touch_allowed=False,
    )
    put_master_order(get_serial_number, putData)

    response = test_client.post(
        f"/device/fetch-control?serial={get_serial_number}&refresh=true",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

    updateData = {
        "element": "Wood",
        "intensity": 50,
    }

    response = test_client.post(
        f"/device/fetch-control?serial={get_serial_number}&refresh=true",
        headers={"Authorization": f"Bearer {get_root_token}"},
        json=updateData,
    )
    assert response.status_code == 404, f"Expected 404 OK, got {response.json()}"

    response = test_client.get(
        f"/mobile/get-device-state?serial_number={get_serial_number}",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
    assert response.json()["updates"] == updateData, "Failed to interrupt fetch control"
