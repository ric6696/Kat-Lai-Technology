from ...database import DeviceDataManager, get_device_db
from ...models.Device import DeviceData, MasterData, DeviceParamters
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
def get_device_token(
    test_client: TestClient, get_username: str, get_password: str, get_root_token: str
):
    scope = "Device"
    device_username = get_username + f"-{scope}"
    register_user_with_scopes(
        test_client, device_username, get_password, get_root_token, scope
    )
    device_token = get_test_access_token(
        test_client, device_username, get_password, [scope]
    )
    yield device_token
    delete_manager(test_client, device_username, get_root_token)


class TestDevicePermissions:
    pass


class TestDevice:
    def test_fetch_control(
        self,
        test_client: TestClient,
        get_device_token: str,
        get_serial_number: str,
    ) -> None:
        db: DeviceDataManager = get_device_db()

        putData = MasterData(
            updates=DeviceParamters(element="Wood", intensity=50),
            user_touch_allowed=False,
        )

        put_master_order(get_serial_number, putData)

        response = test_client.post(
            f"/device/fetch-control?serial={get_serial_number}&refresh=false",
            headers={"Authorization": f"Bearer {get_device_token}"},
        )

        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

        try:
            rcvData = db.get_master_data(get_serial_number, "History")
        except RuntimeError as err:
            print(err)
            pytest.fail("Unexpected error occurred in AWS, RUN!")

        assert putData == rcvData, "Failed to device fetch control"

        remove_master_order(get_serial_number)
        remove_master_history(get_serial_number)

    def test_fetch_control_no_master_order(
        self,
        test_client: TestClient,
        get_device_token: str,
        get_serial_number: str,
    ) -> None:
        response = test_client.post(
            f"/device/fetch-control?serial={get_serial_number}&refresh=false",
            headers={"Authorization": f"Bearer {get_device_token}"},
        )
        assert (
            response.status_code == 404
        ), f"Expected 404 Not Found, got {response.json()}"

    def test_put_device(
        self, test_client: TestClient, get_device_token: str, get_serial_number: str
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
            state=DeviceParamters(element="Fire", intensity=40),
        )

        response = test_client.post(
            "/device/put-device/",
            json=putData.model_dump(mode="json"),
            headers={"Authorization": f"Bearer {get_device_token}"},
        )

        assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"

        try:
            rcvData = db.get_device_data(get_serial_number)
        except ValueError:
            pytest.fail("failed to get device data")

        assert [putData] == rcvData, "Recevied and placed data do not match"

        try:
            db._remove_device_history(get_serial_number)
        except ValueError as err:
            pytest.fail(f"failed to remove device history, {err}!")

    # def test_remove_device_history(self, get_serial_number: str):
    #     db: DeviceDataManager = get_device_db()
    #     print(get_serial_number)
    #     db._remove_device_history(get_serial_number)
