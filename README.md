# Elysium Aroma API ![example workflow](https://github.com/MatthewSummons/DK-Asia/actions/workflows/Test.yml/badge.svg)

This *private* repository contains the source code for the Elysium Aroma API which is used to
manage Aroma Pod Pros, iSuke Sleeping Pads & Belts. This REST API is built in FastAPI
and hosted on AWS EC2 instances, it uses DynamoDB as the database.

The repository also contains scripts that are used to extract data from the iSuke API.

Documentation can be found the respective directories. The Documentation directory contains miscellaneous documents that are used to help with the development of the API, hosting, CI/CD etc.

# Structure of the repository

```bash
├── API/
├── iSuke API Scripts/
├── Documentation/
├── README.md
├── .gitignore
├── .pre-commit-config.yaml
└── .github/
    └── workflows/
```

*For further details refer to the README files in the respective directories.*

## [***API***](API/Setup.md)
### Contains the Elysium Aroma API codebase

The app directory holds the source code for the API. The archive directory holds the archived scripts/tests etc.. The Logs directory holds the logs for the API from production.

## **iSuke API Scripts** 
### Contains the iSuke API scripts

These contain code that is used to extract data for devices from the iSuke API. The url is provided in the directory although the API key and Customer Code might be required to access the API.

