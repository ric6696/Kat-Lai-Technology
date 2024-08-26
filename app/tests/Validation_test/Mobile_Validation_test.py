from fastapi.testclient import TestClient
from ..Utils.fake_serials import reserved_serial
from datetime import datetime, timezone, timedelta
from ...models.Device import MasterData, DeviceParamters


class TestMobileValidation:
    deviceData = MasterData(
        updates=DeviceParamters(element="Wood", intensity=50),
        user_touch_allowed=True,
    )

    def test_put_schedules_invalid_time_order(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        register_testing_device: str,
    ):
        # Invalid time order: start_time cannot be in the past
        Invalid_schedule_data = {
            "start_time": str(datetime.now(timezone.utc) - timedelta(days=10)),
            "end_time": str(datetime.now(timezone.utc) + timedelta(minutes=10)),
            "scheduled_paramters": {"element": "Fire", "intensity": 50},
        }
        response = test_client.put(
            f"/mobile/put-schedule?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=Invalid_schedule_data,
        )
        assert response.status_code == 400, f"Expected 400, got {response.json()}"
        assert "Start time cannot be in the past" in response.json()["detail"]

    def test_get_schedules_not_found(
        self,
        test_client: TestClient,
        get_root_token: str,
        register_testing_device: str,
    ):
        invalid_serial_number = reserved_serial()
        response = test_client.get(
            f"/mobile/get-schedules?serial_number={invalid_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
        )
        assert response.status_code == 400, f"Expected 400, got {response.json()}"
