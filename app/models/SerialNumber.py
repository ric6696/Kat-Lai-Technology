from typing import Annotated
from pydantic.functional_validators import AfterValidator

# DO NOT MODIFY LEGACY SERIAL NUMBER CLASSES
# Doing so will drop support for older devices


class DeviceSetup:
    __Current_Version = "01"
    __NumDigits = 8

    @classmethod
    def create_serial_code(
        cls, country_code: str, device_type: str, sqnce_num: int
    ) -> str:
        return (
            f"{country_code}{device_type}{cls.__Current_Version}"
            + f"{str(sqnce_num).zfill(cls.__NumDigits)}"
        )

    @classmethod
    def validate_serial_number(cls, serial_number: str):
        assert len(serial_number) > 6, "Invalid, unsupported serial number"

        match serial_number:
            case serial_number if serial_number[:4] == "HKSW":  # e.g. HKSW001
                return SerialNumber_V0.validate(serial_number)
            case serial_number if serial_number[4:6] == "01":  # e.g. HKAP0100000001
                return SerialNumber_V1.validate(serial_number)
            case serial_number if serial_number[4:6] != "01":
                raise AssertionError("Invalid Version Code -- Expected ****01********")


class SerialNumber_V0:
    __Version = "00"
    __NumDigits = 3

    @classmethod
    def validate(cls, serial_number: str) -> str:
        assert (
            len(serial_number) == 4 + cls.__NumDigits
        ), f"Serial Number (V0) should be {4 + cls.__NumDigits} characters long"

        Country_Code, Location_Code = serial_number[:2], serial_number[2:4]
        Manufacturer_Code = serial_number[4:]

        assert (
            len(Country_Code) == 2 and Country_Code.isalpha()
        ), "Country_Code should be 2 alphabets"
        assert (
            len(Location_Code) == 2 and Location_Code.isalpha()
        ), "Location_Code should be 2 alphabets"
        assert (
            len(Manufacturer_Code) == cls.__NumDigits and Manufacturer_Code.isdigit()
        ), f"Manufacturer_Code [last {cls.__NumDigits} digits] should be a number"

        return serial_number


class SerialNumber_V1:
    __Version = "01"
    __NumDigits = 8

    @classmethod
    def validate_country_code(cls, country_code: str) -> str:
        assert (
            len(country_code) == 2 and country_code.isalpha()
        ), "Country_Code should be 2 alphabets"
        return country_code

    @classmethod
    def validate_device_type(cls, device_type: str) -> str:
        assert (
            len(device_type) == 2 and device_type.isalpha()
        ), "Device_Type should be 2 alphabets"
        return device_type

    @classmethod
    def validate(cls, serial_number: str) -> str:
        assert (
            len(serial_number) == 6 + cls.__NumDigits
        ), f"Serial Number (V1) should be {6 + cls.__NumDigits} characters long"

        Country_Code = serial_number[:2]
        Device_Type = serial_number[2:4]
        Version_Code = serial_number[4:6]
        Manufacturer_Code = serial_number[6:]

        cls.validate_country_code(Country_Code)
        cls.validate_device_type(Device_Type)

        assert len(Version_Code) == 2 and Version_Code == str(
            cls.__Version
        ), "Version_Code [first two digits] are invalid"

        assert (
            len(Manufacturer_Code) == cls.__NumDigits and Manufacturer_Code.isdigit()
        ), f"Manufacturer_Code [last {cls.__NumDigits} digits] should be a number"

        return serial_number


# Fields obtained from query in the API and validated to create a serial number
# When upgrading can be replaced/removed or modified, although of course their instances
# should be replaced with the new version
Country_Code = Annotated[str, AfterValidator(SerialNumber_V1.validate_country_code)]
Device_Type = Annotated[str, AfterValidator(SerialNumber_V1.validate_device_type)]

Serial_Number = Annotated[str, AfterValidator(DeviceSetup.validate_serial_number)]
