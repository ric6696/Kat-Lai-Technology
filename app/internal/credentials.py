from pathlib import Path

_environment_var_dir = Path("./app/environment/")


def _extract_value(line: str, key: str):
    "Get the string in line after the key substring, excluding the newline character."
    return line[line.index(key) + len(key) :].strip(" \n\r\f\t")


def AWS_credentials() -> tuple[str, str, str]:
    """
    ### Description
    Read and return the AWS Region, Access Key, and Secret Key from the
    environment variables.

    ### Exceptions
    FileNotFoundError: If the file path does not exist.
    ValueError: If the file is not formatted correctly.
    """

    aws_key_path = _environment_var_dir.joinpath("aws.env")
    if not aws_key_path.exists():
        raise FileNotFoundError(
            f"Credentials not found for (AWS) DynamoDB Client at {aws_key_path}"
        )

    with open(aws_key_path) as creds_file:
        try:
            region = _extract_value(creds_file.readline(), "DB_REGION_NAME=")
            access_key = _extract_value(creds_file.readline(), "DB_ACCESS_KEY_ID=")
            secret_key = _extract_value(creds_file.readline(), "DB_SECRET_ACCESS_KEY=")
        except ValueError as err:
            raise ValueError(
                f"Invalid Format for AWS Credentials in {aws_key_path}"
            ) from err

    if not (region and access_key and secret_key):
        raise ValueError(f"Invalid Format for AWS Credentials in {aws_key_path}")

    return region, access_key, secret_key


def iSuke_credentials() -> tuple[str, str, str]:
    """
    ### Description
    Read and return the API URL, API Key and Custoemr Code from the
    environment variables.

    ### Exceptions
    FileNotFoundError: If the file path does not exist.
    ValueError: If the file is not formatted correctly.
    """
    iSuke_key_path = _environment_var_dir.joinpath("isuke_key.env")

    if not iSuke_key_path.exists():
        raise FileNotFoundError(
            f"Credentials not found for iSuke API at {iSuke_key_path}"
        )

    with open(iSuke_key_path) as creds_file:
        try:
            API_URL = _extract_value(creds_file.readline(), "API_URL=")
            API_KEY = _extract_value(creds_file.readline(), "API_KEY=")
            CUSTOMER_CODE = _extract_value(creds_file.readline(), "CUSTOMER_CODE=")
        except ValueError as err:
            raise ValueError(
                f"Invalid Format for iSuke API Credentials in {iSuke_key_path}"
            ) from err

    if not (API_URL and API_KEY and CUSTOMER_CODE):
        raise ValueError(
            f"Invalid Format for iSuke API Credentials in {iSuke_key_path}"
        )

    return API_URL, API_KEY, CUSTOMER_CODE


def User_Auth_Credentials() -> tuple[str, str, str]:
    """
    Description
    Read and return the User Auth Credentials from the environment variables.

    Exceptions
    FileNotFoundError: If the file path does not exist.
    ValueError: If the file is not formatted correctly.
    """

    user_auth_path = _environment_var_dir.joinpath("user_auth.env")

    if not user_auth_path.exists():
        raise FileNotFoundError(
            f"Credentials not found for User Authentication at {user_auth_path}"
        )

    with open(user_auth_path) as creds_file:
        try:
            SECRET_KEY = _extract_value(creds_file.readline(), "AUTH_SECRET_KEY=")
            ALGORITHM = _extract_value(creds_file.readline(), "ALGORITHM=")
            EXP = _extract_value(creds_file.readline(), "ACCESS_TOKEN_EXPIRE_MINUTES=")
        except ValueError as err:
            raise ValueError(
                f"Invalid Format for Authentication Credentials in {user_auth_path}"
            ) from err
    try:
        int(EXP)
    except Exception as err:
        raise ValueError(
            f"Invalid Type for 'ACCESS_TOKEN_EXPIRE_MINUTES' in {user_auth_path}"
        ) from err

    if not (SECRET_KEY and ALGORITHM and EXP):
        raise ValueError(
            f"Invalid Format for Authentication Credentials in {user_auth_path}"
        )

    return SECRET_KEY, ALGORITHM, EXP
