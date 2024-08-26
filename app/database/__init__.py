import boto3

from .DeviceDataManager import DeviceDataManager
from .UserDataManager import UserDataManager

from ..internal.credentials import AWS_credentials


class __Credentials:
    DB_REGION_NAME, DB_ACCESS_KEY_ID, DB_SECRET_ACCESS_KEY = AWS_credentials()


class __DB_Connections:
    DeviceDB: DeviceDataManager | None = None
    UserDB: UserDataManager | None = None


def __init_device_db(
    device_table: str = "Device_Data",
    order_table: str = "Master_Order",
    history_table: str = "Master_History",
    schedule_table: str = "Schedule_Data",
    schedule_control: str = "Schedule_Control",
    serial_table: str = "Serial_Number_Registration",
) -> DeviceDataManager:
    """
    Creates an instance of DeviceDataManager allowing access to the DynamoDB's table.
    """
    db = DeviceDataManager(
        boto3.resource(
            "dynamodb",
            region_name=__Credentials.DB_REGION_NAME,
            aws_access_key_id=__Credentials.DB_ACCESS_KEY_ID,
            aws_secret_access_key=__Credentials.DB_SECRET_ACCESS_KEY,
        )
    )

    if not db.load_tables(
        device_table,
        order_table,
        history_table,
        schedule_table,
        schedule_control,
        serial_table,
    ):
        raise FileNotFoundError("One or more tables not found!")
    return db


def __init_user_db(user_table: str = "User_Table"):
    """
    Creates an instance of UserDataManager allowing access to the DynamoDB's table.
    """
    db = UserDataManager(
        boto3.resource(
            "dynamodb",
            region_name=__Credentials.DB_REGION_NAME,
            aws_access_key_id=__Credentials.DB_ACCESS_KEY_ID,
            aws_secret_access_key=__Credentials.DB_SECRET_ACCESS_KEY,
        )
    )

    if not (db.load_user_table(user_table)):
        raise FileNotFoundError("User Table not found!")
    return db


def _init_tables() -> None:
    __DB_Connections.DeviceDB, __DB_Connections.UserDB = (
        __init_device_db(),
        __init_user_db(),
    )

    del __Credentials.DB_ACCESS_KEY_ID, __Credentials.DB_SECRET_ACCESS_KEY


_init_tables()


def get_device_db() -> DeviceDataManager:
    """
    Dependency Injector for DeviceDataManager
    """
    assert __DB_Connections.DeviceDB is not None, "DeviceDB not initialized"
    return __DB_Connections.DeviceDB


def get_user_db() -> UserDataManager:
    """
    Dependency Injector for UserDataManager
    """
    assert __DB_Connections.UserDB is not None, "UserDB not initialized"
    return __DB_Connections.UserDB
