from fastapi import APIRouter, Depends, HTTPException, Response, Security, status

# Authentication
from ..internal.Authentication import get_current_active_user

from ..database import DeviceDataManager, get_device_db
from ..models.Device import ControlData, DeviceData, DeviceParamters
from ..models.SerialNumber import Serial_Number

# Timezone Utilities
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from typing import Annotated


router = APIRouter(
    prefix="/device",
    tags=["Device"],
    responses={404: {"description": "Not Found"}},
    dependencies=[Security(get_current_active_user, scopes=["Device"])],
)


@router.post("/fetch-control", response_model=ControlData)
async def fetch_control(
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
    response: Response,
    serial: Serial_Number,
    refresh: bool,
    device_update: DeviceParamters | None = None,
    timezone_id: str = "Asia/Hong_Kong",  # TODO: Add documentation for timezone_id
) -> ControlData:
    # TODO: Attempt to offload validation to Pydantic

    # Obtain Device Timezone to return local time for device
    try:
        time_zoneinfo = ZoneInfo(timezone_id)
    except ZoneInfoNotFoundError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request: Invalid Timezone ID",
        ) from err

    """
    Manage Device Schedule Refresh and Interrupts
    Important to update the control tables before fetching the control data
    See https://github.com/Kat-Lai-Technologies/Kat-Lai-Backend/issues/19
    """
    control_info = ""
    if refresh:
        db._refresh_schedule_control(serial)
        control_info += "Refreshed."
    if device_update is not None:
        db.handle_interrupt_signal(serial, device_update)
        control_info += "Interrupted."
    if not control_info:
        control_info = "Not Interrupted or Refreshed."

    master_order, schedule_order = None, None
    # Fetch Master Control
    try:
        master_order = db.get_master_data(serial, "Order")
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Unable to fetch master data",
        ) from err
    if master_order is not None:
        try:
            db.serve_order(serial, master_order)
        except ValueError as err:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal Server Error: Unable to serve master order",
            ) from err

    # Fetch Schedule Control asynchronously [TODO@Ziya]
    try:
        schedule_order = db.get_schedule_control(serial)
        schedule_order.start_time = schedule_order.start_time.astimezone(time_zoneinfo)
        schedule_order.end_time = schedule_order.end_time.astimezone(time_zoneinfo)
        # TODO@Ziya Modify to case with exceptions
        if schedule_order and not (db.remove_schedule_order(serial)):
            # If entry found in control table but unable to remove it.
            raise HTTPException(
                status_code=500, detail="Unable to serve schedule order"
            )
    except ValueError:
        pass

    # Add the local time and control info in the header
    response.headers["X-local-time"] = (
        datetime.now(timezone.utc).astimezone(time_zoneinfo).isoformat()
    )
    response.headers["X-control-info"] = control_info

    if (master_order is not None) or (schedule_order is not None):
        return ControlData(
            Serial_Number=serial,
            master_data=master_order,
            schedule_data=schedule_order,
        )

    raise HTTPException(
        status_code=404,
        detail="Item not found",
        headers={
            "X-local-time": response.headers["X-local-time"],
            "X-control-info": response.headers["X-control-info"],
        },
    )


@router.post("/put-device/", response_model=DeviceData)
async def put_item(
    item: DeviceData, db: Annotated[DeviceDataManager, Depends(get_device_db)]
) -> DeviceData:
    try:
        db.put_device_data(item)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Unable to put device data",
        ) from err
    return item
