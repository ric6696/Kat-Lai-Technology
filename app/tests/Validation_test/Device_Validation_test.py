from fastapi.testclient import TestClient
from ..Utils.registration import (
    put_master_order,
    remove_master_order,
    remove_master_history,
)
from ...database import DeviceDataManager, get_device_db
from ...models.Device import MasterData, DeviceParamters
import pytest


class TestDeviceModelValidation:
    ScheduleDataInvalidFormat = [
        {
            "start_time": "2044-09-07T10:53:37.178721",
            "end_time": "2044-09-07T11:53:37.178721",
            "scheduled_paramters": {"element": "Fire", "intensity": 50},
        },
        {
            "start_time": "2024-08-14T08",
            "end_time": "2024-08-14T09",
            "scheduled_paramters": {"element": "Fire", "intensity": 50},
        },
        {
            "start_time": "2024-08-14",
            "end_time": "2024-08-15",
            "scheduled_paramters": {"element": "Fire", "intensity": 50},
        },
    ]

    ScheduleDataInvalidOrder = [
        {
            # start_time is greater than end_time
            "start_time": "2024-09-07T12:53:37.178721Z",
            "end_time": "2024-09-07T11:53:37.178721Z",
            "scheduled_paramters": {"element": "Fire", "intensity": 50},
        },
        {
            # Start time and end time are the same
            "start_time": "2024-09-07T11:53:37.178721Z",
            "end_time": "2024-09-07T11:53:37.178721Z",
            "scheduled_paramters": {"element": "Fire", "intensity": 50},
        },
        {
            # End time is in the past
            "start_time": "2020-09-07T10:53:37.178721Z",
            "end_time": "2020-09-07T11:53:37.178721Z",
            "scheduled_paramters": {"element": "Fire", "intensity": 50},
        },
    ]

    @pytest.mark.parametrize("ScheduleDataInvalidFormat", ScheduleDataInvalidFormat)
    def test_invalid_time_format(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        ScheduleDataInvalidFormat: dict,
    ):
        response = test_client.put(
            f"/mobile/put-schedule?{get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=ScheduleDataInvalidFormat,
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"

        response = test_client.put(
            f"/mobile/put-schedule?{get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=ScheduleDataInvalidFormat,
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"

        response = test_client.put(
            f"/mobile/put-schedule?{get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=ScheduleDataInvalidFormat,
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"

    @pytest.mark.parametrize("ScheduleDataInvalidOrder", ScheduleDataInvalidOrder)
    def test_invalid_time_order(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        ScheduleDataInvalidOrder: dict,
    ):
        response = test_client.put(
            f"/mobile/put-schedule?{get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=ScheduleDataInvalidOrder,
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"

        response = test_client.put(
            f"/mobile/put-schedule?{get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=ScheduleDataInvalidOrder,
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"

        response = test_client.put(
            f"/mobile/put-schedule?{get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=ScheduleDataInvalidOrder,
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"

    @pytest.mark.parametrize(
        "element", ["metal", "wood", "fire", "earth", "Water", "Air"]
    )
    def test_update_state_element(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        element,
    ):
        data = {"updates": {"element": element, "intensity": 50}}
        response = test_client.post(
            f"/mobile/update-state?serial={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=data,
        )
        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"

    @pytest.mark.parametrize("intensity", [-5, 10.5, 101])
    def test_update_state_intensity_range(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        intensity,
    ):
        data = {"updates": {"element": "Wood", "intensity": intensity}}
        response = test_client.post(
            f"/mobile/update-state?serial={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=data,
        )

        assert (
            response.status_code == 422
        ), f"Expected 422 Unprocessable Entity, got {response.json()}"


class TestDeviceRoutersValidation:
    def test_invalid_timezone(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
    ):
        deviceData = MasterData(
            updates=DeviceParamters(element="Wood", intensity=50),
            user_touch_allowed=True,
        )
        invalid_timezone = "hfkjashfkdsfh"
        put_master_order(get_serial_number, deviceData)
        response = test_client.post(
            f"/device/fetch-control?serial={get_serial_number}&refresh=false&timezone_id={invalid_timezone}",
            headers={"Authorization": f"Bearer {get_root_token}"},
        )
        assert (
            response.status_code == 400
        ), f"Expected 400 Unprocessable Entity, got {response.json()}"

        remove_master_order(get_serial_number)
        remove_master_history(get_serial_number)

    def test_fetch_control_RuntimeError(self, test_client, get_root_token):
        """
        Test case for fetch control when RuntimeError occurs:
        Master Tables are not loaded
        """
        db: DeviceDataManager = get_device_db()
        temp = db.master_history_table
        db.master_history_table = None
        response = test_client.post(
            "/device/fetch-control?serial=HKSW001&refresh=false",
            headers={"Authorization": f"Bearer {get_root_token}"},
        )
        db.master_history_table = temp
        assert (
            response.status_code == 500
        ), f"Expected 500 Internal Server Error, got {response.json()}"
