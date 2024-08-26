from ...database import DeviceDataManager, get_device_db
from ...models.Device import (
    ClientData,
    MasterData,
    ScheduleData,
    DeviceParamters,
)
from ..Utils.fake_serials import reserved_serial
import pytest
from fastapi.testclient import TestClient
import urllib


@pytest.fixture
def device_data_with_user_touch_allowed(scope="class"):
    return MasterData(
        updates=DeviceParamters(element="Wood", intensity=50),
        user_touch_allowed=True,
    )


@pytest.fixture
def device_data_with_user_touch_not_allowed(scope="class"):
    return MasterData(
        updates=DeviceParamters(element="Wood", intensity=50),
        user_touch_allowed=False,
    )


class TestMobile:
    def test_put_schedule_device_not_found(
        self,
        test_client: TestClient,
        get_root_token: str,
        v_schedule_data: ScheduleData,
        register_testing_device: str,
    ) -> None:
        invalid_serial_number = reserved_serial()
        response = test_client.put(
            f"/mobile/put-schedule?serial_number={invalid_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=v_schedule_data.model_dump(),
        )
        assert (
            response.status_code == 400
        ), f"Expected 400 Bad Request, got {response.json()}"

    def test_put_schedule(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        v_schedule_data: ScheduleData,
        register_testing_device: str,
    ) -> None:
        db: DeviceDataManager = get_device_db()

        response = test_client.put(
            f"/mobile/put-schedule?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=v_schedule_data.model_dump(),
        )
        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
        putData = v_schedule_data
        try:
            rcvData = db.get_schedules(get_serial_number)[0]
        except RuntimeError as err:
            pytest.fail(f"Failed to get schedule, {err}")

        assert putData == rcvData, "Failed to put schedule"
        try:
            db.remove_schedule(
                get_serial_number,
                v_schedule_data.start_time,
            )
        except ValueError as err:
            print(err)
            pytest.fail("Unexpected error occurred!, failed to remove schedule")

    def test_put_schedule_conflict(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        get_schedule_data: ScheduleData,
    ) -> None:
        response = test_client.put(
            f"/mobile/put-schedule?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=get_schedule_data.model_dump(),
        )
        assert (
            response.status_code == 409
        ), f"Expected 409 Conflict, got {response.json()}"

    def test_put_schedule_user_touch_not_allowed(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        v_schedule_data: ScheduleData,
        device_data_with_user_touch_not_allowed: MasterData,
        register_testing_device: str,
    ) -> None:
        db: DeviceDataManager = get_device_db()
        try:
            db._put_master_history(
                get_serial_number, device_data_with_user_touch_not_allowed
            )
        except (ValueError, RuntimeError):
            pytest.fail("Failed to put master history")

        response = test_client.put(
            f"/mobile/put-schedule?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=v_schedule_data.model_dump(),
        )
        assert (
            response.status_code == 403
        ), f"Expected 403 Forbidden, got {response.json()}"

    def test_get_schedules(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        get_schedule_data: ScheduleData,
    ) -> None:
        response = test_client.get(
            f"/mobile/get-schedules?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
        )

        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
        putData = get_schedule_data
        rcvData = ScheduleData(**response.json()[0])
        assert putData == rcvData, "Failed to get schedules"

    def test_update_state_device_not_found(
        self, test_client: TestClient, get_root_token: str
    ) -> None:
        invalid_serial_number = reserved_serial()
        newData = ClientData(updates=DeviceParamters(element="Fire", intensity=25))

        response = test_client.post(
            f"/mobile/update-state?serial_number={invalid_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=newData.model_dump(),
        )

        assert (
            response.status_code == 400
        ), f"Expected Bad Request: Device (Serial Number) Not Found, \
            got {response.json()}"

    def test_update_state(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        device_data_with_user_touch_allowed: MasterData,
        register_testing_device: str,
    ) -> None:
        db: DeviceDataManager = get_device_db()
        try:
            db._put_master_history(
                get_serial_number, device_data_with_user_touch_allowed
            )
        except (ValueError, RuntimeError) as err:
            pytest.fail(f"Failed to put master history, {err}")

        newData = ClientData(updates=DeviceParamters(element="Fire", intensity=25))
        response = test_client.post(
            f"/mobile/update-state?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
            json=newData.model_dump(),
        )

        assert (
            response.status_code == 202
        ), f"Expected 202 Accepted, got {response.json()}"
        try:
            rcvData = db.get_master_data(get_serial_number, "Order")
        except (SyntaxError, RuntimeError) as err:
            pytest.fail(f"Failed to get master data, {err}")

        assert rcvData is not None, "Failed to update state"
        assert newData.updates == rcvData.updates, "Failed to update state"

        try:
            db._remove_master_order(get_serial_number)
            db._remove_master_history(get_serial_number)
        except RuntimeError as err:
            print(err)
            pytest.fail("Unexpected error occurred in AWS!")

    def test_get_device_state(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        device_data_with_user_touch_allowed: MasterData,
        register_testing_device: str,
    ) -> None:
        db: DeviceDataManager = get_device_db()

        try:
            db._put_master_history(
                get_serial_number, device_data_with_user_touch_allowed
            )
        except (ValueError, RuntimeError) as err:
            pytest.fail(f"Failed to put master history, {err}")

        response = test_client.get(
            f"/mobile/get-device-state?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_root_token}"},
        )

        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
        rcvData = ClientData(**response.json())
        assert (
            device_data_with_user_touch_allowed.updates == rcvData.updates
        ), "Failed to get device state"

        try:
            db._remove_master_history(get_serial_number)
        except ValueError as err:
            print(err)
            pytest.fail("Unexpected error occurred!")

    def test_delete_schedule(
        self,
        test_client: TestClient,
        get_serial_number: str,
        get_root_token: str,
        v_schedule_data: ScheduleData,
    ) -> None:
        db: DeviceDataManager = get_device_db()

        try:
            db.put_schedule(get_serial_number, v_schedule_data)
        except (RuntimeError, ValueError) as err:
            pytest.fail(f"Failed to put schedule, {err}")

        response = test_client.delete(
            f"/mobile/delete-schedule?serial_number={get_serial_number}&start_time="
            + urllib.parse.quote(f"{v_schedule_data.start_time}"),
            headers={"Authorization": f"Bearer {get_root_token}"},
        )

        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
        assert db.get_schedules(get_serial_number) == [], "Failed to delete schedule"
