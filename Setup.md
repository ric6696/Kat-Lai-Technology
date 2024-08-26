# Structure

```
API/
├── app       # Main application source code.
├── archive   # Code no longer in use.
├── Logs      # Production/Development logs from the application.
└── Setup.md  # Setup instructions for the application. (You are here)
```

It is possible that the `Logs/` directory does not exist, in which case the directory (and its subdirectories) will be generated automatically on application startup.

If you encounter an issue with the logs refer to this section, otherwise you may skip ahead.

If that fails, please verify/modify the code in `app/__init__.py` file, and or otherwise use that as reference to create the directories manually.

# Setup

There are a few steps to follow to set up the application. The following instructions are for a Linux environment, but the steps should be similar for other operating systems.
Please note that the application is built using Python 3.12.4 (and is supported for Python 3.9 and above). If you machine doesnot have python installed, please install it from the official website.

Furthermore please note that the application is not tested on Windows, and therefore it is recommended to use a Linux environment for deployment. Development was performed on MacOS, and the application is currently deployed on an Ubuntu server.

## Clone the repository

To deploy/use the application, begin by cloning the repository. The current name of the repository is Kat-Lai-Backend, under the Kat-Lai-Technologies organization, although this might change in the future (and so might the clone link provided, therefore please refer to the latest clone link on the repository page).

```
git clone https://github.com/Kat-Lai-Technologies/Kat-Lai-Backend.git
```

## Setup Credentials

Please note that the application uses a few credentials that are not included in the repository. These credentials are stored in different `.env` files in the `app\environment` directory. 

The file should look like this:
```
app/
├── ...
├── environment/
│   ├── aws.env.local
│   ├── isuke_key.env.local
│   └── user_auth.env.local
└── ... 
```

The contents of these files should look similar, here are the contents of `aws.env.local` for example:

>### _aws.env.local_
>```
>DB_REGION_NAME=<put region name here, e.g. ap-east-1>
>DB_ACCESS_KEY_ID=<put access key ID here>
>DB_SECRET_ACCESS_KEY=<put secret access key here>
>```

Please note that the credentials are not included in the repository, and you will need to obtain them from the owner of the repository or your manager.

For the AWS credentials, you can request for an AWS IAMA account with the necessary permissions. You can then obtain the access key ID and secret access key from the AWS console.

For the `isuke_key.env.local` file, you will need to obtain the url, key and customer_code from the owner of the repository or your manager.

Lastly, for the `user_auth.env.local` file, you will need to obtain the secret key from the owner of the repository or your manager.

Replace the true credentials with the placeholders in the `.env` files.
After inputting the correct credentials you should rename the file and remove the.local extensions from the file names.

The edited files should look as follows, where `***` represents the actual credentials:
>### _aws.env_
>```
>DB_REGION_NAME=****
>DB_ACCESS_KEY_ID=***
>DB_SECRET_ACCESS_KEY=***
>```

## Install Project Dependencies

Although you could install the dependencies globally, it is recommended to use a virtual environment. 


The virtual environment package should be bundled with your python installation, but if it is not, please install it. You can refer to the official docs here: [venv — Creation of virtual environments][venv-docs-link].

Once you have the `venv` package, navigate to the `API/` directory (the reccomended directory for holding the virtual environment) and create a virtual environment in the project directory by running the following command, where `.venv` is the name of the virtual environment (you can name it anything you want):

```zsh
python3 -m venv .venv
```

Next *activate* the virtual environment by running the following command on linux machines:

```zsh
source .venv/bin/activate
```

Please note that you need to provide the path to the virtual environment to *activate* the virtual environemnt.
Therefore the above command only works if you are in the same directory as the virtual environment, otherwise you need to provide the path to the virtual environment.

Please also note that the command might be different on Windows machines or machines using non bash/zsh shells. Please refer to the [official documentation][venv-docs-link] for more information.

Once you have successfully activated the virtual environment, you can install the dependencies. There are two files that you can use to install the dependencies as shown in the directory tree below:

```
app/
├── requirements.txt
├── requirements-dev.txt
├── ...
├── environment/
├── models/
├── ...
└── main.py
```

The `requirements.txt` file contains the dependencies required for the application to run, while the `requirements-dev.txt` file contains additonal dependencies required for development.

To install the dependencies for running/deploying, run the following command:

```zsh
pip3 install -r app/requirements.txt
```

To install the dependencies for development/testing, run the following command:

```zsh
pip3 install -r app/requirements.txt -r app/requirements-dev.txt
```

If you are on a **Windows** machine, you need additional dependencies for the API to run. You can use the following command to install the dependencies:

```zsh
pip install -r app/requirements.txt -r app/requirements-dev.txt -r app/requirements-windows.txt
```

If you encounter issues downloading the dependencies, please ensure that you have the correct version of Python installed, and that you have the correct version of `pip` installed, namely `pip 24.2`.

Otherwise if you are unable to download dependeinces, please refer to the official documentation for more information.
It is also possible you might be fetching the wrong version for the dependencies, in which case you can refer to the `requirements.txt` or `requirements-dev.txt` file to see the versions of the dependencies used in development.

## [Optional] Setup Pre-Commit

The application uses `pre-commit` to run checks before committing code. This is to ensure that the code is formatted correctly, and that there are no issues with the code before it is committed.

To install `pre-commit`, run the following command:

```zsh
pre-commit install
```

This will install the `pre-commit` hooks, and will run the checks before you commit code. If there are any issues, the commit will be aborted, and you will need to fix the issues before you can commit the code.

## [Optional] Running Tests

Ensure that you are in the `API/` directory, have activatved the virtual environment, and have installed the dependencies for *development*. Once ready, simply run the tests by running the following command:

```zsh
pytest
```

This will run the tests in the `tests/` directory, and will output the results to the console.

To obtain the coverage report, run the following command:

```zsh
pytest --cov --cov-report=html:coverage_report --cov-config=app/tests/.coveragerc
```

This will create a directory called `coverage_report/` in the `API/` directory (or the directory from where you execute `pytest`), which contains the coverage report.

You can view the coverage report by opening the `index.html` file in the `coverage_report/` directory in your browser.

## Running the Application

Once you have installed the dependencies, you can run the application. To run the application, run the following command (from the `API/` directory):

```zsh
uvicorn app.main:app
```

This will run the server on `localhost:8000`. You can access the server by visiting `http://localhost:8000/docs` in your browser.

[venv-docs-link]: https://docs.python.org/3/library/venv.html