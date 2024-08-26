from ...database import DeviceDataManager, get_device_db
from ...models.Device import MasterData, DeviceParamters, DeviceData
import pytest
from fastapi.testclient import TestClient
from ..Utils.registration import (
    put_master_order,
    register_user_with_scopes,
    get_test_access_token,
    delete_manager,
    remove_master_order,
    remove_master_history,
)
from decimal import Decimal


@pytest.fixture(scope="module")
def get_manager_token(
    test_client: TestClient, get_username: str, get_password: str, get_root_token: str
):
    scope = "Manager"
    manager_username = get_username + f"-{scope}"
    register_user_with_scopes(
        test_client, manager_username, get_password, get_root_token, scope
    )
    manager_token = get_test_access_token(
        test_client, manager_username, get_password, [scope]
    )
    yield manager_token
    delete_manager(test_client, manager_username, get_root_token)


class TestManager:
    def test_put_master_order(
        self, test_client, get_manager_token, get_serial_number
    ) -> None:
        db: DeviceDataManager = get_device_db()
        putData = MasterData(
            updates=DeviceParamters(element="Wood", intensity=50),
            user_touch_allowed=False,
        )
        response = test_client.post(
            f"/manager/put-master-order?serial_number={get_serial_number}",
            headers={"Authorization": f"Bearer {get_manager_token}"},
            json=putData.model_dump(),
        )
        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

        try:
            rcvData = db.get_master_data(get_serial_number, "Order")
        except (SyntaxError, RuntimeError) as err:
            pytest.fail(f"failed to get master data, {err}")

        assert putData == rcvData, "Failed to put master order"

        remove_master_order(get_serial_number)

    def test_put_master_history(self, get_serial_number) -> None:
        db: DeviceDataManager = get_device_db()
        putData = MasterData(
            updates=DeviceParamters(element="Wood", intensity=50),
            user_touch_allowed=False,
        )
        db._put_master_history(get_serial_number, putData)
        rcvData = db.get_master_data(get_serial_number, "History")
        assert putData == rcvData, "Failed to put master history"

        remove_master_history(get_serial_number)

    def test_get_master_state_none(
        self, test_client, get_manager_token, get_serial_number
    ) -> None:
        response = test_client.get(
            f"/manager/get-master-state?serial={get_serial_number}",
            headers={"Authorization": f"Bearer {get_manager_token}"},
        )
        assert (
            response.status_code == 404
        ), f"Expected 404 Not Found, got {response.json()}"

    def test_get_master_state(
        self, test_client, get_manager_token, get_serial_number
    ) -> None:
        db: DeviceDataManager = get_device_db()
        putData = MasterData(
            updates=DeviceParamters(element="Wood", intensity=50),
            user_touch_allowed=False,
        )
        db._put_master_history(get_serial_number, putData)
        response = test_client.get(
            f"/manager/get-master-state?serial={get_serial_number}",
            headers={"Authorization": f"Bearer {get_manager_token}"},
        )
        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
        assert putData.model_dump() == response.json(), "Failed to get master state"

        remove_master_history(get_serial_number)

    def test_get_device_history_none(
        self, test_client, get_manager_token, get_serial_number
    ) -> None:
        response = test_client.get(
            f"/manager/get-device-history?serial={get_serial_number}",
            headers={"Authorization": f"Bearer {get_manager_token}"},
        )
        assert (
            response.status_code == 404
        ), f"Expected 404 Not Found, got {response.json()}"

    def test_get_device_history(
        self, test_client, get_manager_token, get_serial_number
    ) -> None:
        db: DeviceDataManager = get_device_db()
        putData = DeviceData(
            Serial_Number=get_serial_number,
            Local_Time_Str="string",
            local_ip="string",
            location="string",
            region="string",
            country="string",
            latitude="string",
            longitude="string",
            temperature=Decimal(0),
            condition="string",
            wind_speed=Decimal(0),
            humidity=Decimal(0),
            state=DeviceParamters(element="Wood", intensity=40),
        )
        try:
            db.put_device_data(putData)
        except ValueError as err:
            pytest.fail(f"failed to put device data, {err}")

        response = test_client.get(
            f"/manager/get-device-history?serial={get_serial_number}",
            headers={"Authorization": f"Bearer {get_manager_token}"},
        )

        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
        rcvData = response.json()
        assert [putData] == [
            DeviceData(**data) for data in rcvData
        ], "Put and Rcv data mismatch"

        remove_master_history(get_serial_number)
        db._remove_device_history(get_serial_number)

    def test_remove_master_order(
        self,
        get_serial_number,
    ) -> None:
        db: DeviceDataManager = get_device_db()
        putData = MasterData(
            updates=DeviceParamters(element="Wood", intensity=50),
            user_touch_allowed=False,
        )

        put_master_order(get_serial_number, putData)

        try:
            db._remove_master_order(f"{get_serial_number}")
        except (ValueError, RuntimeError) as err:
            pytest.fail(f"failed to remove master order, {err}")

        try:
            rcvData = db.get_master_data(get_serial_number, "Order")
        except (SyntaxError, RuntimeError) as err:
            pytest.fail(f"failed to get master data, {err}")

        assert rcvData is None, "Failed to remove master order"

    def test_remove_master_history(self, get_serial_number) -> None:
        db: DeviceDataManager = get_device_db()
        putData = MasterData(
            updates=DeviceParamters(element="Wood", intensity=50),
            user_touch_allowed=False,
        )
        try:
            db._put_master_history(get_serial_number, putData)
        except (ValueError, RuntimeError) as err:
            pytest.fail(f"failed to put master history, {err}")

        try:
            db._remove_master_history(f"{get_serial_number}")
        except ValueError as err:
            print(err)
            pytest.fail("Unexpected error occurred!")

        try:
            rcvData = db.get_master_data(get_serial_number, "History")
        except (SyntaxError, RuntimeError) as err:
            pytest.fail(f"failed to get master data, {err}")

        assert rcvData is None, "Failed to remove master history"
