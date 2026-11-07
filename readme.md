# Archive Alliance

## Setup
- Install requirements.txt
- Set the following environment variables:

| Key           | What to use for value                                                                         |
|---------------|-----------------------------------------------------------------------------------------------|
| HOST          | The address of a postgres database                                                            |
| PORT          | The port of the db                                                                            |
| USER          | The username for the db                                                                       |
| PASSWORD      | The password for the db                                                                       |
| INIT_USERNAME | The username you want initilized for the service (only needed on first startup)               |
| INIT_PASSWORD | The password you want initlized for the service (only needed on first startup)                |
| SECRET_KEY    | The key used for password hashing and JWT signing. Use openssl rand -hex 32 to get this value |

- Run with uvicorn, and it's all ready to go!
