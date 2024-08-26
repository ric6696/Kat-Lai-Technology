import logging
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from ..models.Device import (
    # Device,
    DeviceData,
    DeviceParamters,
    MasterData,
    ScheduleData,
)
from ..models.SerialNumber import Serial_Number, DeviceSetup

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="./Logs/Devices/DataBase.log",
    filemode="a",
    encoding="utf-8",
    level=logging.DEBUG,
)


class DeviceDataManager:
    def __init__(self, dyn_resource):
        """
        : param dyn_resource: A Boto3 DynamoDB resource.
        """
        self.dyn_resource = dyn_resource
        # Table to register Serial Numbers
        self.serial_table = None
        # Table to store state history of devices
        self.device_table = None
        # Tables to manage controlling actions on Devices remotely
        self.master_order_table = None
        self.master_history_table = None
        # Tables to manage Aroma Schedulues for Devices
        self.schedule_table = None
        self.schedule_control_table = None
        self.standard_timezone = ZoneInfo("GMT")

    def load_tables(
        self,
        device_table: str,
        master_order_table: str,
        master_history_table: str,
        schedule_table: str,
        schedule_control_table: str,
        serial_number_table: str,
    ) -> bool:
        """
        Attempts to load the given tables, storing them in a disctionary that is stored
        as a member variable. Returns a boolean indicating whether all tables were
        loaded or not.
        """
        table_names = (
            device_table,
            master_order_table,
            master_history_table,
            schedule_table,
            schedule_control_table,
            serial_number_table,
        )
        table_existence = [False] * len(table_names)
        loading_tables = []
        for i, table_in in enumerate(table_names):
            try:
                table = self.dyn_resource.Table(table_in)
                table.load()
                table_existence[i] = True
            except ClientError as err:
                if err.response["Error"]["Code"] == "ResourceNotFoundException":
                    table_existence[i] = False
                else:
                    logger.error(
                        "Couldn't check for existence of tables. Here's why: %s: %s",
                        err.response["Error"]["Code"],
                        err.response["Error"]["Message"],
                    )
                    raise ValueError from err
            else:
                loading_tables.append(table)
        try:
            self.device_table = loading_tables[0]
            self.master_order_table, self.master_history_table = loading_tables[1:3]
            self.schedule_table, self.schedule_control_table = loading_tables[3:5]
            self.serial_table = loading_tables[5]
        except ValueError:
            return False
        return all(table_existence)

    ### Serial Number Registration ###
    # Not Central is it ..., How do you scale this ...
    # Serial Number Versioning, ... coupled at the moment ...
    def generate_serial_number(
        self, country_code: str, device_type: str
    ) -> Serial_Number:
        """
        Requests a new serial number from the databse that can be binded to a device.
        Adds an entry for the serial_number with state as inactive, needs to be
        activated by calling acknowlegde_registeration.
        # Exceptions
        Raises a RuntimeError if there is an issue with the database, or an
        AssertionError if reserved keywords (eg. TEST) used in the serial number.
        """
        assert (
            self.serial_table is not None
        ), "Serial Table not loaded, call load_tables()"
        # Get the latest sequence number
        try:
            response = self.serial_table.get_item(
                Key={"Serial_Number": "Available_Serial_Seq"}
            )
            sequence_number = int(response.get("Item")["Value"])
        except ClientError as err:
            raise RuntimeError("Error with Available_Serial_Seq") from err
        # Update New
        try:
            self.serial_table.update_item(
                Key={"Serial_Number": "Available_Serial_Seq"},
                # Increment the sequence number
                UpdateExpression="SET #V = #V + :inc",
                ExpressionAttributeNames={"#V": "Value"},  # Reserved Keyword Value
                ExpressionAttributeValues={":inc": 1},
            )
        except ClientError as err:
            raise RuntimeError("Error incrementing sequence value") from err
        # Add entry with inactive field
        try:
            new_serial_number = DeviceSetup.create_serial_code(
                country_code, device_type, sequence_number
            )
            # RESERVED: TEST
            assert (
                "TEST" not in new_serial_number
            ), "Serial Number cannot contain 'TEST'"
            # TODO@Ziya Check if Serial Number already exists
            # in database before putting!!!
            self.serial_table.put_item(
                Item={"Serial_Number": new_serial_number, "Active": False}
            )
        except ClientError as err:
            raise RuntimeError("Client Error") from err
        return new_serial_number

    def activate_device_serial(self, serial: str) -> None:
        """
        Acknowleges the registeration of a device with the given serial number.
        Activates the serial number in the database, raises error if already
        activated. Assumes valid format of serial number is given.

        # Exceptions
        Raises a ValueError if the serial number is not found in the database,
        or if it is already active.
        Raises a RuntimeError if there is an issue with the database.
        """
        assert (
            self.serial_table is not None
        ), "Serial Table not loaded, call load_tables()"
        # Attempt to activate device with serial_code
        try:
            self.serial_table.update_item(
                Key={"Serial_Number": serial},
                ConditionExpression="Active = :Old",
                UpdateExpression="set Active = :New",
                ExpressionAttributeValues={":New": True, ":Old": False},
            )
        except ClientError as err:
            if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(
                    f"Serial Number {serial} is not yet allocated or already activated."
                    + " Request a new serial number from the API."
                ) from err
            else:
                raise RuntimeError(
                    f"Unable to update entry, when attempting to activate {serial}!"
                ) from err
        # Update Device Count
        try:
            self.serial_table.update_item(
                Key={"Serial_Number": "Device_Count"},
                UpdateExpression="SET #V = #V + :inc",
                ExpressionAttributeNames={"#V": "Value"},  # Reserved Keyword Value
                ExpressionAttributeValues={":inc": 1},
            )
        except ClientError as err:
            raise RuntimeError(
                f"Error updating Device_Count in {self.serial_table}"
            ) from err

    def deactivate_device_serial(self, serial: str) -> None:
        """
        Deactivates the serial number in the database.
        Assumes valid serial number is given.

        # Exceptions
        Raises a ValueError if the serial number is not found in the database,
        or if it is already inactive.
        Raises a RuntimeError if there is an issue with the database.
        """
        assert (
            self.serial_table is not None
        ), "Serial Table not loaded, call load_tables()"
        # Attempt to deactivate device with serial_code
        try:
            self.serial_table.update_item(
                Key={"Serial_Number": serial},
                ConditionExpression="Active = :Old",
                UpdateExpression="set Active = :New",
                ExpressionAttributeValues={":New": False, ":Old": True},
            )
        except ClientError as err:
            if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError(
                    f"Serial Number {serial} is not yet allocated or already"
                    + "deallocated. Request a new serial number from the API."
                ) from err
            else:
                raise RuntimeError(
                    f"Unable to update entry, when attempting to deactivate {serial}!"
                ) from err
        # Update Device Count
        try:
            self.serial_table.update_item(
                Key={"Serial_Number": "Device_Count"},
                UpdateExpression="SET #V = #V - :inc",
                ExpressionAttributeNames={"#V": "Value"},  # Reserved Keyword Value
                ExpressionAttributeValues={":inc": 1},
            )
        except ClientError as err:
            raise RuntimeError(
                f"Error updating Device_Count in {self.serial_table}"
            ) from err

    def is_serial_registered(self, serial: str, is_active: bool = True) -> bool:
        """
        Checks if the serial number is registered in the database.
        Returns True if it is registered and active, False otherwise.
        Also takes an optional argument is_active, which if set to False
        will return True if the serial number is registered but inactive.


        # Exceptions
        Raises a RuntimeError if there is an issue with the database.
        """
        assert (
            self.serial_table is not None
        ), "Serial Table not loaded, call load_tables()"
        try:
            response = self.serial_table.get_item(Key={"Serial_Number": serial})
        except ClientError as err:
            raise RuntimeError("Error with AWS DynamoDB") from err
        else:
            if "Item" in response:
                return response.get("Item").get("Active") == is_active
            return False

    def _register_testing_device(self, serial_code: str) -> Serial_Number:
        """
        [For Testing purposes only] Registers a device for testing purposes.

        # Exceptions
        Raises a Runtime Error if the Serial Table is not loaded.
        Raises ValueError if the serial number is already in use (or reserved)
        """
        if self.serial_table is None:
            raise RuntimeError("User_Table not loaded!")
        elif serial_code == "00000000":
            raise ValueError(f"Serial Number: {serial_code} is reserved for testing")
        try:
            serial_number = "TEST" + str(serial_code)
            self.serial_table.put_item(
                Item={"Serial_Number": serial_number, "Active": True},
                ConditionExpression="attribute_not_exists(Serial_Number)",
            )
        except ClientError as err:
            if err.response["Error"]["Code"] == "ConditionalCheckFailedException":
                raise ValueError("Serial Number already exists") from err
            raise ValueError("Error registering device") from err
        return serial_number

    def _deregister_testing_device(self, serial_code: str) -> Serial_Number:
        """
        [For Testing purposes only] Deregisters a device for testing purposes.

        # Exceptions
        Raises a Runtime Error if the Serial Table is not loaded.
        """
        if self.serial_table is None:
            raise RuntimeError("User_Table not loaded!")
        try:
            self.serial_table.delete_item(Key={"Serial_Number": "TEST" + serial_code})
        except ClientError as err:
            raise ValueError("Serial Number not found") from err
        # TODO: Check all tables
        return "TEST" + serial_code

    ###  Device History Tables ###
    def put_device_data(self, data: DeviceData) -> None:
        """
        Puts an item into the device history table.

        # Exceptions
        Raises a ValueError if there is an issue with the AWS.
        """
        if self.device_table is None:
            raise RuntimeError("User_Table not loaded!")
        try:
            assert (
                self.device_table is not None
            ), "Device Table not loaded, call load_tables()"
            self.device_table.put_item(Item=data.model_dump())
        except ClientError as err:
            raise RuntimeError("Issue encountered with AWS DynamoDB") from err

    def get_device_data(self, serial: str) -> list[DeviceData] | None:
        """
        Gets an item from the Device Data Table

        # Exceptions
        Raises a ValueError if the item is not found.
        """
        try:
            assert (
                self.device_table is not None
            ), "Device Table not loaded, call load_tables()"
            response = self.device_table.query(
                KeyConditionExpression=(Key("Serial_Number").eq(serial))
            )
        except ClientError as err:
            raise ValueError("Issue encountered with AWS") from err
        else:
            if response.get("Items"):
                return [DeviceData(**dt) for dt in response.get("Items")]
            return None

    def _remove_device_history(self, serial: str) -> None:
        """
        [For Testing purposes only] Removes all items with the given serial number

        # Exceptions
        Raises a ValueError if an issue with AWS arises.
        """
        assert (
            self.device_table is not None
        ), "Device Table not loaded, call load_tables()"
        try:
            response = self.device_table.query(
                KeyConditionExpression=(Key("Serial_Number").eq(serial))
            )
            for item in response["Items"]:
                self.device_table.delete_item(
                    Key={
                        "Serial_Number": serial,
                        "Local_Time_Str": item["Local_Time_Str"],
                    }
                )
        except ClientError as err:
            raise ValueError("Unexpected response from AWS DynamoDB") from err

    ### Master Control Management ###
    def get_master_data(self, serial: str, table_class: str) -> MasterData | None:
        """
        Gets an item from the Master Control Table(s) given a serial.
        table can be either History or Order, anything else will be rejected.
        If no order found, return None.

        # Exceptions
        Raises a Syntax Error if the table_class is not "Order" or "History".
        Throws a Runtime Error if the Master Tables are not loaded or if
        there is an issue with the AWS.
        """
        if self.master_order_table is None or self.master_history_table is None:
            raise RuntimeError("Master Tables not loaded!")
        if table_class == "Order":
            table = self.master_order_table
        elif table_class == "History":
            table = self.master_history_table
        else:
            raise SyntaxError("Table must be either 'Order' or 'History'")

        try:
            response = table.get_item(Key={"Serial_Number": serial})
        except ClientError as err:
            logger.error(
                "Couldn't get item from order table. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise RuntimeError(
                "AWS DynamoDB is being uncooperative right now."
            ) from err
        if "Item" in response:
            return MasterData(**response.get("Item"))
        return None

    def put_master_order(self, serial: str, data: MasterData) -> None:
        """
        Puts an item into the Master Order Table.

        # Exceptions
        Raises a RuntimeError if the Master Order Table is not loaded or
        if there is an issue with the AWS.
        """
        if self.master_order_table is None:
            raise RuntimeError("Master Order Table not loaded!")
        try:
            entry = data.model_dump()
            entry["Serial_Number"] = serial
            self.master_order_table.put_item(Item=entry)
        except ClientError as err:
            raise RuntimeError("Issue encountered with AWS DynamoDB") from err

    def serve_order(self, serial: str, order_data: MasterData) -> None:
        """
        Takes an order from the Master Order Table and moves it to the
        Master History Table. Removes it from the Master Order Table.
        Should be called once the order is served to the device
        (i.e. after device calls get_master_data with "Order" table
        and if order exists for that device).

        # Exceptions

        Raises a ValueError if unsuccessful, when there is an issue with the AWS,
        i.e. unable to either move the message to the history table or
        remove it from the order table.
        """
        self._put_master_history(serial, order_data)
        self._remove_master_order(serial)

    def _put_master_history(self, serial: str, data: MasterData) -> None:
        """
        [For internal use only] Puts an item into the Master History Table.

        # Exceptions
        Raises a ValueError if there is an issue with the AWS.
        Raises a RuntimeError if the Master History Table is not loaded.
        """
        if self.master_history_table is None:
            raise RuntimeError("Master History Table not loaded!")
        try:
            entry = data.model_dump()
            entry["Serial_Number"] = serial
            self.master_history_table.put_item(Item=entry)
        except ClientError as err:
            logger.error(
                "Couldn't put item in history table. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise ValueError(
                f"Unable to store item in {self.master_history_table}. "
                + "Issue encountered with AWS DynamoDB"
            ) from err

    def _remove_master_order(self, serial: str) -> None:
        """
        [For internal/testing use only] Removes an item from the Master Order Table.

        # Exceptions
        Raises a RuntimeError if the Master Order Table is not loaded.
        Raises a ValueError if there is an issue with the AWS.
        """
        if self.master_order_table is None:
            raise RuntimeError("Master Order Table not loaded!")
        try:
            self.master_order_table.delete_item(Key={"Serial_Number": serial})
        except ClientError as err:
            logger.error(
                "Couldn't remove item from order table. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise RuntimeError("AWS is being a lil' b*tch right now") from err

    def handle_interrupt_signal(self, serial: str, update: DeviceParamters) -> None:
        """
        Called when user changes the device state from directly the device.
        This function is used to update the state in the master table.
        """
        try:
            self._update_master_state(serial, update)
        except ClientError as err:
            raise ValueError("Encountered AWS's wrath") from err

    def _update_master_state(self, serial: str, new_params: DeviceParamters) -> None:
        """
        [For internal use only] Updates the state in the Master Order Table.

        # Exceptions

        Raises a RuntimeError if the Master History Table is not loaded.
        Raises a ValueError if there is an issue with the AWS.
        """
        if self.master_history_table is None:
            raise RuntimeError("Master History Table not loaded!")
        try:
            # FIXME (Add a slow fix for fetch-control interrupt)
            old = self.get_master_data(serial, "History")

            entry = {
                "Serial_Number": serial,
                "updates": new_params.model_dump(),
                "user_touch_allowed": old.user_touch_allowed
                if old is not None
                else True,
            }
            # FIXME
            self.master_history_table.put_item(Item=entry)

            # self.master_order_table.update_item(
            #     Key={"Serial_Number": serial},
            #     UpdateExpression="SET updates = :new_state",
            #     ExpressionAttributeValues={":new_state": new_params.model_dump()},
            # )
        except ClientError as err:
            logger.error(
                "Couldn't update state in order table. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise ValueError("Issue encountered with AWS DynamoDB") from err

    def _remove_master_history(self, serial: str) -> None:
        """
        [For testing use only] Removes an item from the Master History Table.

        # Exceptions
        Raises a RuntimeError if the Master History Table is not loaded.
        Raises a ValueError if there is an issue with the AWS.
        """
        if self.master_history_table is None:
            raise RuntimeError("Master History Table not loaded!")
        try:
            self.master_history_table.delete_item(Key={"Serial_Number": serial})
        except ClientError as err:
            raise RuntimeError("DynamoDB, chill dude. Go smoke like Angaa") from err

    ### Schedule Control Management ###
    def put_schedule(self, serial: str, data: ScheduleData) -> dict | None:
        """
        Puts an item into the Schedule Table. If succesful returns the item
        (in a dict), else if the scehdule is invalid, it throws a ValueError.

        # Exceptions
        Raises a RuntimeError if the Schedule Table is not loaded.
        Raises a ValueError if invalid schedule or an issue with AWS
        """
        if self.schedule_table is None:
            raise RuntimeError("Schedule Table not loaded!")
        try:
            if not (self._validate_schedule(serial, data.start_time, data.end_time)):
                raise ValueError("Schedule is invalid!")
            # If valid, add Serial Number to data entry, convert to the standard
            # timezone, then to a string to be stored in the database.
            entry = data.model_dump()
            entry["Serial_Number"] = serial

            entry["start_time"] = data.start_time.astimezone(
                self.standard_timezone
            ).isoformat()

            entry["end_time"] = data.end_time.astimezone(
                self.standard_timezone
            ).isoformat()

            self.schedule_table.put_item(Item=entry)
            return self._refresh_schedule_control(serial)

        except ClientError as err:
            raise RuntimeError("Problem encountered with AWS") from err

    def get_schedule_control(self, serial: str) -> ScheduleData:
        """
        Gets the current schedule for a device.

        # Exceptions
        Raises a RuntimeError if the Schedule Control Table is not loaded.
        Raises a ValueError if the item is not found or when no item sent from AWS
        """
        if self.schedule_control_table is None:
            raise RuntimeError("Schedule Control Table not loaded!")
        try:
            response = self.schedule_control_table.get_item(
                Key={"Serial_Number": serial}
            )
        except ClientError as err:
            logger.error(
                "Couldn't get current schedule. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            raise ValueError("Item not found") from err
        else:
            responseData = response.get("Item")
            if responseData is None:
                raise ValueError("Empty Response when fetching from Schedule Control")
            return ScheduleData(**responseData)

    def remove_schedule_order(self, serial: str) -> bool:
        """
        Removes the current schedule for a device.
        Returns True if successful, False otherwise.

        # Exceptions
        Raises a RuntimeError if the Schedule Control Table is not loaded.
        """
        if self.schedule_control_table is None:
            raise RuntimeError("Schedule Control Table not loaded!")
        try:
            self.schedule_control_table.delete_item(Key={"Serial_Number": serial})
        except ClientError as err:
            logger.error(
                "Couldn't remove current schedule. Here's why: %s: %s",
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            return False
        return True

    def get_schedules(self, serial: str) -> list[ScheduleData]:
        """
        Gets all schedules for a device.

        # Exceptions
        Raises a Runtime Error if the Schedule Table is not loaded or if
        AWS is being a b*tch.
        """
        if self.schedule_table is None:
            raise RuntimeError("Schedule Table not loaded!")
        try:
            self._refresh_schedules(serial)
            response = self.schedule_table.query(
                KeyConditionExpression=(Key("Serial_Number").eq(serial))
            )
        except ClientError as err:
            raise RuntimeError("AWS CLient Error: Item not found") from err
        else:
            return [ScheduleData(**schedule) for schedule in response.get("Items")]

    def _refresh_schedules(self, serial: str) -> dict | None:
        """
        [For internal use only]

        Goes through the Schedule Table and removes any
        scheduled sessions that have already ended.

        If there is a future schedule,
        returns the entry for that schedule, otherwise returns None.

        This method should be called everytime the schedule table is to be
        read or written to.

        # Exceptions
        Raises a RuntimeError if the Schedule Table is not loaded.
        Raises a ValueError if the item is not found.
        """
        if self.schedule_table is None:
            raise RuntimeError("Schedule Table not loaded!")
        try:
            response = self.schedule_table.query(
                KeyConditionExpression=(Key("Serial_Number").eq(serial))
            )
            for item in response["Items"]:
                if (datetime.fromisoformat(item["end_time"])) < (
                    datetime.now(timezone.utc)
                ):
                    self.schedule_table.delete_item(
                        Key={"Serial_Number": serial, "start_time": item["start_time"]}
                    )
                # End iteration and return the first future schedule
                else:
                    return item
            return None
        except ClientError as err:
            raise ValueError(f"Item not found for Serial Number: {serial}") from err

    def _refresh_schedule_control(self, serial: str) -> dict | None:
        """
        [For internal use only] Fetches the latest schedule from the
        Schedule Table if it exists and updates the Schedule Control
        Table with it. If a schedule doesn't exist,
        it removes the entry from the Schedule Control Table
        (if it exists in the control table).

        # Exceptions
        Raises a RuntimeError if the Schedule Control Table is not loaded.
        Raises a ValueError if error with AWS.
        """
        # Grab the schedule with the earliest start time
        latest = self._refresh_schedules(serial)
        # Push that to Control Table
        if self.schedule_control_table is None:
            raise RuntimeError("Schedule Control Table not loaded!")
        try:
            if latest:
                latest["Serial_Number"] = serial
                self.schedule_control_table.put_item(Item=latest)
                return latest
            else:
                self.schedule_control_table.delete_item(Key={"Serial_Number": serial})
                return None
        except ClientError as err:
            raise ValueError("Error in AWS: Could not update Schedule Control") from err

    def _validate_schedule(
        self, serial: str, start_time: datetime, end_time: datetime
    ) -> bool:
        """
        [For internal use only] Checks if the schedule is valid.
        If a schedule overlaps with any other return False, else return True.

        # Exceptions
        Raises a RuntimeError if the Schedule Table is not loaded.
        Raises a ValueError if issue with AWS
        """
        self._refresh_schedules(serial)
        if self.schedule_table is None:
            raise RuntimeError("Schedule Table not loaded!")
        try:
            schedule_list = self.schedule_table.query(
                KeyConditionExpression=(Key("Serial_Number").eq(serial))
            )["Items"]
        except ClientError as err:
            raise ValueError("Item not found") from err

        for item in schedule_list:
            # Return False if the schedule overlaps with any other schedule
            """
            Refer to https://stackoverflow.com/questions/143552/comparing-date-ranges/143568#143568
            & https://stackoverflow.com/questions/12283559/find-overlapping-appointments-in-on-time
            """
            start_check = datetime.fromisoformat(item["start_time"])
            end_check = datetime.fromisoformat(item["end_time"])
            # Conflict only occurs if e_2 < s_1 or e_1 < s_2;
            if not ((start_time > end_check) or (end_time < start_check)):
                return False
        return True

    def remove_schedule(self, serial: str, start_time: datetime | str) -> ScheduleData:
        """
        Removes an item from the Schedule Table.

        # Exceptions
        Raises a RuntimeError if the Schedule Table is not loaded, or if there is
        an issue with AWS.
        Raises a ValueError if issues with handling the input start times, such
        as converting timezones or converting types.
        """
        if self.schedule_table is None:
            raise RuntimeError("Schedule Table not loaded!")
        try:
            # Convert start_time to standard timezone, and then to a string for querying
            if isinstance(start_time, str):
                start_time = (
                    datetime.fromisoformat(start_time)
                    .astimezone(self.standard_timezone)
                    .isoformat()
                )

            if isinstance(start_time, datetime):
                start_time = start_time.astimezone(self.standard_timezone).isoformat()

            response = self.schedule_table.delete_item(
                Key={"Serial_Number": serial, "start_time": start_time},
                ReturnValues="ALL_OLD",
            )

            self._refresh_schedule_control(serial)

        except ClientError as err:
            raise RuntimeError("AWS's problem, probably also ours though") from err
        except Exception as err:
            raise ValueError("Failed in converting timezones, or in querying") from err

        try:
            return ScheduleData(**response.get("Attributes"))
        except Exception as err:
            raise RuntimeError(
                "Failed to convert response from AWS to ScheduleData."
                + "Unexpected response from AWS."
            ) from err
