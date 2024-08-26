import logging
from datetime import datetime, timezone

from botocore.exceptions import ClientError

from ..models.Authentication import UserInDB

logger = logging.getLogger(__name__)
logging.basicConfig(
    filename="./Logs/Authentication/DataBase.log",
    filemode="a",
    encoding="utf-8",
    level=logging.DEBUG,
)


class UserDataManager:
    def __init__(self, dyn_resource):
        """
        : param dyn_resource: A Boto3 DynamoDB resource.
        """
        self.dyn_resource = dyn_resource
        self.user_table = None

    def load_user_table(self, user_table_name: str) -> bool:
        """
        Loads the given user table, storing it as a member variable. Returns True if
        successful and false otherwise.
        """
        try:
            table = self.dyn_resource.Table(user_table_name)
            table.load()
            exists = True
        except ClientError as err:
            if err.response["Error"]["Code"] == "ResourceNotFoundException":
                exists = False
            else:
                logger.error(
                    "Couldn't check for existence of %s. Here's why: %s: %s",
                    user_table_name,
                    err.response["Error"]["Code"],
                    err.response["Error"]["Message"],
                )
                raise
        else:
            self.user_table = table

        return exists

    def get_user(self, username: str, is_login_attempt: bool) -> UserInDB | None:
        """
        Get a user from the database given their username. If is_login_attempt is True,
        the user's last_login attribute will be updated to the current time.

        If is_login_attempt is set to False, last_login will not be updated, otherwise
        it will be updated. Authenticating or registering users should be considered
        login_attempts.

        Returns the user if found, and None otherwise.
        """

        if self.user_table is None:
            raise RuntimeError("User_Table not loaded!")

        try:
            response = self.user_table.get_item(Key={"username": username})
            user = response.get("Item")
            if is_login_attempt and user:
                user = self._update_last_login(username)
        except ClientError as err:
            logger.error(
                "Couldn't get item from %s. Here's why: %s: %s",
                self.user_table.name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
        return UserInDB(**user) if user is not None else None

    def register_user(self, user_data: dict, hashed_password: str, scopes: str) -> bool:
        """
        Register a user in the database.

        :param user_data: A dictionary containing the user's data.
        The dictionary must contain the following keys:
        - username: The user's username.
        - email: The user's email address.
        - full_name: The user's full name.
        - disabled: A boolean indicating whether the user is disabled.

        :param hashed_password: The user's hashed password.

        :param scopes: The user's scopes.
        """
        if self.user_table is None:
            raise RuntimeError("User_Table not loaded!")

        try:
            user_dict = {
                "username": user_data["username"],
                "email": user_data["email"],
                "full_name": user_data["full_name"],
                "hashed_password": hashed_password,
                "scopes": scopes,
                "disabled": user_data["disabled"],
                "last_login": str(datetime.now(timezone.utc)),
            }

            self.user_table.put_item(Item=user_dict)
        except ClientError as err:
            logger.error(
                "Couldn't put item into %s. Here's why: %s: %s",
                self.user_table.name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            return False

        logger.info("Successfully registered user %s", user_data["username"])
        return True

    def _update_last_login(self, username: str) -> dict:
        if self.user_table is None:
            raise RuntimeError("User_Table not loaded!")

        response = self.user_table.update_item(
            Key={"username": username},
            UpdateExpression="set last_login = :ll",
            ExpressionAttributeValues={":ll": str(datetime.now(timezone.utc))},
            ReturnValues="ALL_NEW",
        )
        return response.get("Attributes")

    def delete_user(self, username: str) -> bool:
        """
        Deletes a user from the database.
        """
        if self.user_table is None:
            raise RuntimeError("User_Table not loaded!")

        try:
            self.user_table.delete_item(Key={"username": username})
        except ClientError as err:
            logger.error(
                "Couldn't delete item from %s. Here's why: %s: %s",
                self.user_table.name,
                err.response["Error"]["Code"],
                err.response["Error"]["Message"],
            )
            return False
        return True
