import os

# Setup the bas logging directory
try:
    os.mkdir("./Logs")
except FileExistsError:
    pass  # Directory already exists
except Exception as err:
    raise RuntimeError("Initialization Error creating log directory: Logs") from err

__subdirectories = ("Devices", "Authentication")
for subdir in __subdirectories:
    try:
        os.mkdir(f"./Logs/{subdir}")
    except FileExistsError:
        pass  # Directory
    except Exception as err:
        raise RuntimeError(
            f"Initialization Error creating log directory: Logs/{subdir}"
        ) from err

del __subdirectories, subdir
