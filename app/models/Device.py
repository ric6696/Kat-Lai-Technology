# Models and Data
from pydantic import BaseModel, model_validator, field_serializer
from .SerialNumber import Serial_Number as SerialNumberModel
from . import Available_Elements

# Utilities
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing_extensions import Self


class DeviceParamters(BaseModel):
    element: str | None = None
    intensity: int | None = None

    @model_validator(mode="after")
    def validate_paramters(self) -> Self:
        if self.element is not None:
            assert (self.element.lower() in Available_Elements) and (
                self.element.isupper()
                or self.element.islower()
                or self.element.istitle()
            ), f"Element {self.element} is not a valid element"
        if self.intensity is not None:
            assert 0 <= self.intensity <= 100, (
                f"Intensity {self.intensity} is not a valid intensity."
                + "Inensity should be between 0 and 100."
            )
        assert (self.intensity is not None) or (
            self.element is not None
        ), "Both element and intensity cannot be None"
        return self


class Device(BaseModel):
    Serial_Number: SerialNumberModel


class ClientData(BaseModel):
    updates: DeviceParamters


class MasterData(ClientData):
    user_touch_allowed: bool


class ScheduleData(BaseModel):
    start_time: datetime  # Sort Key
    end_time: datetime
    scheduled_paramters: DeviceParamters

    @model_validator(mode="after")
    def validate_schedule_data(self) -> Self:
        if not (self.start_time.tzinfo) or not (self.end_time.tzinfo):
            raise ValueError("Inputs not in valid ISO8601 with timezone format")
        if self.start_time >= self.end_time:
            raise ValueError("Start time cannot be the same as or after end time")
        if self.end_time < (datetime.now(timezone.utc) - timedelta(minutes=5)):
            raise ValueError(
                "End time cannot be in the past, please provide a future start time"
            )
        return self

    @field_serializer("start_time")
    def serialize_start_time(self, strt_dt: datetime) -> str:
        return strt_dt.isoformat()

    @field_serializer("end_time")
    def serialize_end_time(self, end_dt: datetime) -> str:
        return end_dt.isoformat()


class ControlData(Device):
    master_data: MasterData | None = None
    schedule_data: ScheduleData | None = None

    @model_validator(mode="after")
    def validate_control_data(self) -> Self:
        assert (
            self.master_data or self.schedule_data
        ), "Both master_data and schedule_data cannot be null"
        return self


class DeviceData(Device):
    Local_Time_Str: str  # Sort Key
    local_ip: str
    location: str
    region: str
    country: str
    latitude: str
    longitude: str
    temperature: Decimal
    condition: str
    wind_speed: Decimal
    humidity: Decimal
    state: DeviceParamters

    @field_serializer("temperature", when_used="json")
    def serialize_temperature(self, temperature: Decimal) -> str:
        return str(temperature)

    @field_serializer("wind_speed", when_used="json")
    def serialize_wind_speed(self, wind_speed: Decimal) -> str:
        return str(wind_speed)

    @field_serializer("humidity", when_used="json")
    def serialize_humidity(self, humidity: Decimal) -> str:
        return str(humidity)
