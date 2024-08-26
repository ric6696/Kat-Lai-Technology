# Operation [Outdated]

This directory holds the source code for running, operating and managing the backend.

## Starting The Server

Esure that you are in the Backend directory.

1. First locate the file ``aws.env.local`` and add the access keys for DynamoDB (including a region name, keyID and the key itself). [Optional] You can modify the paths to the key by editing the ``Config`` class in ``databaseManager.py``. Finally rename the file to ``aws.env``.
2. Create a virtual environment using `venv`, activate it and install all dependencies for the project.

   ```
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
   To deactivate the virtual environment, simply type ``deactivate`` in the terminal **if needed**.
3. Launch the backend server app in the virtual environment in dev mode.

   ```
   python -m uvicorn main:app --reload
   ```
   ## Database Commands

   For interacting with the database, refer to the source code in the file ``databaseManager.py``.

   To initialize a database client instance connection, use the following.


   ```
   db = DataBase(boto3.resource(
       'dynamodb',
       region_name=Config.DB_REGION_NAME,
       aws_access_key_id=Config.DB_ACCESS_KEY_ID,
       aws_secret_access_key=Config.DB_SECRET_ACCESS_KEY
       ))

   if not db.exists("Test_Data"):
       db.create_table("Test_Data")
   ```
