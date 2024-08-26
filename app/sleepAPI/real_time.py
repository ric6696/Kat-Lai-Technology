from datetime import datetime, timedelta
from ..internal.credentials import iSuke_credentials

import httpx

from typing import Generator


def _update_token(api_url: str, api_key: str, customer_code: str) -> str:
    params = {"apiKey": api_key, "customerCode": customer_code}
    response = httpx.post(api_url + "auth/getToken", params=params).json()
    if response["code"] != "0000":
        raise ValueError("Unable to fetch token for iSuke API")
    return response["data"]


def check_iSuke_API(api_url: str, api_key: str, customer_code: str) -> bool:
    try:
        _update_token(api_url, api_key, customer_code)
    except Exception:
        return False
    return True


try:
    API_URL, API_KEY, CUSTOMER_CODE = iSuke_credentials()
except (FileNotFoundError, ValueError):
    _iSuke_creds_loaded = False
else:
    _iSuke_creds_loaded = True
finally:
    if _iSuke_creds_loaded:
        iSuke_creds_valid = check_iSuke_API(API_URL, API_KEY, CUSTOMER_CODE)
    else:
        iSuke_creds_valid = False


serial_to_MAC_map: dict[str, str] = {
    "HKSP000": "638DC8F5FAC3",
    "HKSP001": "221220000002",
    "HKBKL001": "4EB11697EF4F",
    "HKBL002": "488095E6D542",
    "HKSP0100000001": "221220000002",
    "HKBL0100000001": "4EB11697EF4F",
    "HKBL0100000002": "488095E6D542",
}

# Shitty Code Ensues, but it (kinda) works. Please Refactor at a later occasion.
# To be replaced with WebScokets in the future.


def _real_time_data(
    api_url: str,
    api_key: str,
    customer_code: str,
    MAC: str,
    token: str,
    old_time: datetime,
) -> tuple[dict, str, datetime]:
    try:
        if (datetime.now() - old_time) > timedelta(minutes=5):
            token, old_time = (
                _update_token(api_url, api_key, customer_code),
                datetime.now(),
            )
    except ValueError as err:
        raise ValueError("Unable to update token") from err

    headers = {
        "token": token,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    res = httpx.post(
        url=api_url + "/getRealHrRrData", data={"mac": MAC}, headers=headers
    )

    return res.json(), token, old_time


def fetch_real_time_data(
    api_url: str, api_key: str, customer_code: str, MAC: str
) -> Generator[dict, None, None]:
    token, old_time = _update_token(api_url, api_key, customer_code), datetime.now()
    while True:
        try:
            data, token, old_time = _real_time_data(
                api_url, api_key, customer_code, MAC, token, old_time
            )
        except ValueError as err:
            raise ValueError("Unable to fetch real-time data") from err
        yield data


def get_real_time(serial_number: str) -> dict:
    MAC = serial_to_MAC_map.get(serial_number)
    if MAC is None:
        raise ValueError(f"Serial Number {serial_number} not found in database")
    try:
        gen = fetch_real_time_data(API_URL, API_KEY, CUSTOMER_CODE, MAC)
        res = next(gen)
    except ValueError as err:
        raise ValueError("Unable to fetch real-time data") from err

    if res["code"] != "0000":
        print("DEBUG:\n", res)
        raise ValueError("Unable to fetch data")
    return res
