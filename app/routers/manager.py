from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Security, status

from ..database import DeviceDataManager, get_device_db
from ..internal.Authentication import get_current_active_user
from ..models.Device import DeviceData, MasterData
from ..models.SerialNumber import Serial_Number

router = APIRouter(
    prefix="/manager",
    tags=["Manager"],
    responses={404: {"description": "Not Found"}},
    dependencies=[Security(get_current_active_user, scopes=["Manager"])],
)


@router.post("/put-master-order/", response_model=MasterData)
async def put_order(
    serial_number: Serial_Number,
    item: MasterData,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> MasterData:
    try:
        db.put_master_order(serial_number, item)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Issue with database encountered",
        ) from err
    return item


@router.get("/get-master-state", response_model=MasterData)
async def get_master_state(
    serial: Serial_Number,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> MasterData:
    try:
        item = db.get_master_data(serial, "History")
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Issue with database encountered",
        ) from err

    if item is not None:
        return item
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")


@router.get("/get-device-history", response_model=list[DeviceData])
async def get_item(
    serial: Serial_Number,
    db: Annotated[DeviceDataManager, Depends(get_device_db)],
) -> list[DeviceData]:
    try:
        items = db.get_device_data(serial)
    except RuntimeError as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal Server Error: Issue with database encountered",
        ) from err
    if items:
        return items
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
