from fastapi.testclient import TestClient
import pytest


@pytest.mark.skip(reason="Not implemented yet")
def test_apply_register_device(
    test_client: TestClient,
    get_root_token: str,
) -> None:
    country_code = "HK"
    device_type = "AP"

    response = test_client.post(
        f"/device-setup/apply-register-device?country_code={country_code}&device_type={device_type}",
        headers={"Authorization": f"Bearer {get_root_token}"},
    )
    print(response.json())
    assert response.status_code == 200, f"Expected 200 OK, got {response.json()}"
