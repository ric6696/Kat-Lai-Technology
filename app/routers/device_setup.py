from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status

from ..database import DeviceDataManager, get_device_db
from ..internal.Authentication import get_current_active_user
from ..models.SerialNumber import Country_Code, Device_Type, Serial_Number


router = APIRouter(
    prefix="/device-setup",
    tags=["Device Setup"],
    responses={404: {"description": "Not Found"}},
    dependencies=[Security(get_current_active_user, scopes=["Device-Setup"])],
)


@router.post("/allocate-serial-number", response_model=str)
async def get_available_serial(
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
    country_code: Country_Code,
    device_type: Device_Type,
) -> Serial_Number:
    try:
        return db.generate_serial_number(country_code, device_type)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error",
        ) from err
    except AssertionError as err:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Invalid Serial Code"
        ) from err


@router.post("/activate-serial-number", response_model=str)
async def activate_serial_number(
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
    serial: Serial_Number,
) -> str:
    try:
        db.activate_device_serial(serial)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        ) from err
    return f"Device {serial} activated successfully"


@router.get("/is-registered", response_model=bool)
async def is_registered(
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
    serial: Serial_Number,
) -> bool:
    try:
        return db.is_serial_registered(serial)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to retrieve registration information from database",
        ) from err


@router.delete("/deactivate-device", response_model=str)
async def deactivate_device(
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
    serial: Serial_Number,
) -> str:
    try:
        db.deactivate_device_serial(serial)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(err)
        ) from err
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(err)
        ) from err
    return f"Device {serial} deactivated successfully"
