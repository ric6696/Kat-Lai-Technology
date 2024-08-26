from fastapi import APIRouter, Depends, HTTPException, Response, status, Security

from ..database import DeviceDataManager, get_device_db

# Models
from ..internal.Authentication import get_current_active_user
from ..models.Device import ClientData, MasterData, ScheduleData, DeviceParamters
from ..models.SerialNumber import Serial_Number

# Utilities
from datetime import datetime, timezone
from typing import Annotated

router = APIRouter(
    prefix="/mobile",
    tags=["Mobile"],
    responses={404: {"description": "Not Found"}},
    dependencies=[Security(get_current_active_user, scopes=["Mobile"])],
)


def init_device_state(
    serial_number: Serial_Number, db: DeviceDataManager
) -> MasterData:
    """
    Initializes the device state to default values. Raises RuntimeError if
    unable to place master order in the database.
    """
    desired_state = MasterData(
        user_touch_allowed=True,
        updates=DeviceParamters(element="OFF", intensity=0),
    )
    db.put_master_order(serial_number, desired_state)
    return desired_state


@router.put("/put-schedule", response_model=ScheduleData)
async def put_schedule(
    serial_number: Serial_Number,
    schedule_data: ScheduleData,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> ScheduleData:
    """
    The start and end time for the schedule should obey iso8601 with offset format
    (timezone aware) (e.g. "2024-07-07 11:53:37.178721+00:00").
    """

    try:
        if not db.is_serial_registered(serial_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Device (Serial Number) Not Found",
            )

        device_state = db.get_master_data(serial_number, "History")
        if device_state is None:
            device_state = init_device_state(serial_number, db)

    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error:"
            + "Error in retrieving data (from database)"
            + "or initializing device state",
        ) from err

    if not device_state.user_touch_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient Permissions",
        )

    try:
        if schedule_data.start_time < datetime.now(timezone.utc):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Start time cannot be in the past",
            )

        db.put_schedule(serial_number, schedule_data)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Conflict: This schedule conflicts with other schedules",
        ) from err
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Error in updating schedule",
        ) from err

    return schedule_data


@router.get("/get-schedules", response_model=list[ScheduleData])
async def get_schedules(
    serial_number: Serial_Number,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> list[ScheduleData]:
    """
    Get all scheduled aroma events for a device (given its serial number),
    returns an empty list if no schedules are found.
    """
    try:
        if not db.is_serial_registered(serial_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Device (Serial Number) Not Found",
            )
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error:"
            + "Error in retrieving Master Data (from database)",
        ) from err

    try:
        return db.get_schedules(serial_number)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Error in retrieving schedules",
        ) from err


@router.post("/update-state", responses={202: {"model": DeviceParamters}})
async def request_state_update(
    serial_number: Serial_Number,
    client_request: ClientData,
    response: Response,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> DeviceParamters:
    """
    Request to change device state from the mobile page/app.
    The request should contain either
    the element or intensity or both. If both are not present,
    the request will be rejected. It may
    also be rejected if permissions deisbaled (from admin/manager).
    """
    try:
        if not db.is_serial_registered(serial_number):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Bad Request: Device (Serial Number) Not Found",
            )

        device_state = db.get_master_data(serial_number, "History")
        if device_state is None:
            device_state = init_device_state(serial_number, db)

    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error:"
            + "Error in retrieving data (from database)"
            + "or initializing device state",
        ) from err

    # Check permissions (see if user control is enabled)
    if not (device_state.user_touch_allowed):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient Permissions",
        )

    # TODO@Ziya: Handle the case when entry already in control table, not just history.

    new_element = client_request.updates.element
    if new_element is None:
        new_element = device_state.updates.element

    new_intensity = client_request.updates.intensity
    if new_intensity is None:
        new_intensity = device_state.updates.intensity

    new_update = DeviceParamters(element=new_element, intensity=new_intensity)

    try:
        db.put_master_order(
            serial_number,
            MasterData(
                user_touch_allowed=True,
                updates=new_update,
            ),
        )

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal Server Error: {err}",
        ) from err

    response.status_code = status.HTTP_202_ACCEPTED
    return new_update


@router.get("/get-device-state", response_model=ClientData)
async def get_device_state(
    serial_number: Serial_Number,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> ClientData:
    """
    Receive the current state of the device (element and intensity)
    along with the permissions
    """
    try:
        if not db.is_serial_registered(serial_number):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Not Found: Device (Serial Number) Not Found",
            )
        device_state = db.get_master_data(serial_number, "History")
        if device_state is None:
            device_state = init_device_state(serial_number, db)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER,
            detail=(
                "Internal Server Error: Unable to retrieve device state from database"
            ),
        ) from err
    return ClientData(updates=device_state.updates)


@router.delete("/delete-schedule", response_model=ScheduleData)
async def delete_schedule(
    serial_number: Serial_Number,
    start_time: datetime,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> ScheduleData:
    """
    Delete a scheduled aroma event for a device (given its serial number).
    """
    try:
        return db.remove_schedule(serial_number, start_time)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bad Request: Schedule Not Found",
        ) from err
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Error in deleting schedule",
        ) from err
