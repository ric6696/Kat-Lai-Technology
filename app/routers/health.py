from fastapi import APIRouter, HTTPException, Security

from ..sleepAPI.real_time import get_real_time
from ..models.SerialNumber import Serial_Number

from ..internal.Authentication import get_current_active_user


router = APIRouter(
    prefix="/medical",
    tags=["Health"],
    responses={404: {"description": "Not Found"}},
    dependencies=[Security(get_current_active_user, scopes=["Device"])],
)


# TODO: Fix this shitty peice of code [Good Luck]
@router.post("/realtimeHrRrData")
async def get_real_time_data(serial_number: Serial_Number) -> dict:
    # TODO: Handle offline
    try:
        res = get_real_time(serial_number)
    except ValueError as err:
        print(err)
        raise HTTPException(
            status_code=404, detail="Unable to fetch real-time data"
        ) from err

    if "data" not in res:
        return {"HR": 0, "RR": 0, "Status": -1, "Timestamp": None}

    data = res["data"]
    return {
        "HR": data["hr"],
        "RR": data["rr"],
        "Status": data["status"],
        "Timestamp": data["time"],
    }
