# GenAI ALBUS
  
This repository contains the APIs fo GENAI ALBUS module in the DEXTRUS. An interactive Swagger UI that lists all of the APIs and their documentation at `http://{ip-address}:{port}/docs` For example: `http://127.0.0.1:8000/docs`. develop, qa and master branches are hosted in develop, qa and demo servers respectively and their documentation can be accessed at `8000` port of the servers hosting those branches. Refer to the [systems details file](https://rightdata.sharepoint.com/:x:/r/sites/Dextrus26/_layouts/15/Doc.aspx?sourcedoc=%7BED655A38-9B15-4A7C-8F8D-55F8751EF004%7D&file=System%20Details.xlsx&action=default&mobileredirect=true&DefaultItemOpen=1) for more information.


## Local Setup

### Non docker setup

1. Install [Miniconda](https://docs.conda.io/en/latest/miniconda.html) and use the commands below
   - `conda env create --file environment.yml`
   - `conda activate genai_albus`
   - `poetry install`
   - pip install hypercorn
2. In the folder configs wh have the enviroment variables and the settings for the app. **Do not commit this local path specific to your system to the repository**
3. Configure your environment variables. We need 3 environment variables as required:

   1. `DB_URI`: with the database credentials.
   2. `GENAI_ALBUS_PATH`: Path to save the logs and alembic logs
   3. `OPENAI_API_KEY`: API key for openai
4.  We need 4 environment variables as optional:
    1.  `LOG_LEVEL`: set the debug level for the logs
    2.  `LOG_RETENTION`: set the number of days to retain the logs
    3.  `LOG_ROTATION`: set the number of days to rotate the logs
    4.  `RUN_ALEMBIC`: set to `True` to run alembic migrations and create the tables in your db

5. Run the following commands to run the api server locally
   - `cd app/`
   - `hypercorn main:app --bind 0.0.0.0:8000` Use `--reload` flag to enable restarting of the application on any code change.

### Docker setup

1. Install [Docker](https://docs.docker.com/engine/install/)
2. Create a folder for a path as mentioned in the `properties.py` to store the data files. **Do not commit this local path specific to your system to the repository**
3. Remove --root-path parameter in Dockerfile in hypercorn command at the end.
4. Build the docker image using `docker build -t image_name ./` Rebuild this image on any code change
5. use docker-compose.yml for regular deployments for 5008 port deployments. If not use the below docker run command with preferred port number.
6. Once the image has been create start the container using `sudo docker run -p <port number>:8000 -v /home/ubuntu/spark-warehouse/:/home/ubuntu/spark-warehouse/ --env-file /home/ubuntu/python/python.env -dt image_name` Replace `/home/ubuntu/spark-warehouse/` with the path in the `properties.py` file where the data files are stored and replace `/home/ubuntu/python/python.env` with the location where the ENV variables are stores in `.env` file. Also the server 10.10.20.28 is the server where trino is running, changing accordingly.
7. Based on requirement also change the `--network=python_python_services` according to docker-compose file in dev system it is python_python_services. If network is not found try running `docker network list` command.
8. docker-compose.yml file is located in `/home/ubuntu/python/docker-compose.yml`. By changing to that directory run `sudo docker-compose up -d`.

### Docker setup with executable

1. Remove dist/ and build/ folder if any.
2. Run three scripts.
   1. python3 ./executable_docker/clean_pyinstaller.py for cleaning previously generated pyinstaller command.
   2. python3 ./executable_docker/create_pyinstaller.py for generating pyinstaller command.
   3. bash ./executable_docker/install_dependencies.bash to install all the dependencies including miniconda, dextrus_datascience environment and also pyproject dependencies.
3. Build the docker image using `docker build -t image_name ./executable_docker/Dockerfile .` Rebuild this image on any code change.
4. use docker-compose.yml for regular deployments for 5008 port deployments. If not use the below docker run command with preferred port number.
5. Once the image has been create start the container using `sudo docker run -p <port number>:8000 -v /home/ubuntu/spark-warehouse/:/home/ubuntu/spark-warehouse/ --env-file /home/ubuntu/python/python.env --network=python_python_services --add-host trino.getrightdata.com:10.10.20.28 -dt image_name` Replace `/home/ubuntu/spark-warehouse/` with the path in the `properties.py` file where the data files are stored and replace `/home/ubuntu/python/python.env` with the location where the ENV variables are stores in `.env` file. Also the server 10.10.20.28 is the server where trino is running, changing accordingly.
6. Based on requirement also change the `--network=python_python_services` according to docker-compose file in dev system it is python_python_services. If network is not found try running `docker network list` command.
7. docker-compose.yml file is located in `/home/ubuntu/python/docker-compose.yml`. By changing to that directory run `sudo docker-compose up -d`.

## Deploying on server

1. Obtain credentials from server admin.
2. ssh into the Dextrus Server (ssh <-username->@<-address->).
3. Provide appropriate password.
4. Navigate to folder python/testing/dextrus_datascience.
5. Git pull from personal development repo.
6. Create docker image using an appropriate, and free port.

## Branch

- All the active development of the python team gets merged into `python_develop` branch
- `python_develop` gets merged into `develop` when the feature is to be made available for integration with UI
- `develop` branch gets merged into `qa` branch when development cycle completes and all the features are to be tested with `qa`
- Once `qa` confirms quality check, `qa` is merged into `master` and tagged with a suitable version

## Environment

- The repository makes use of [conda](https://docs.conda.io/projects/conda/en/4.6.0/_downloads/52a95608c49671267e40c689e0bc00ca/conda-cheatsheet.pdf) and [poetry](https://python-poetry.org/docs/cli/) for managing the environment. Once the conda environment created above is activated, python specific packages are installed using `poetry`.
- Conda is used primarily for non-python packages, python packages that are either not compatible for installation with the environment setup or highly optimized as compared to [pypi](https://pypi.org) version (packages that are installed with `pip`)
- Packages can be installed using `poetry add package_name` for poetry and `conda install package_name` for conda
- In poetry all the packages that are not confirmed to be actually useful and still in the development stage can be installed using `-D` flag. `poetry add -D package_name`
- If a package is added or updated using `conda` create a new conda environment file using `conda env export --from-history > environment.yml`
- If a package is added or updated using `poetry` update the lock file using `poetry lock --no-update`

## Contributing guidelines

- Before start creating a new feature you _should_ run the unit test to check that everything is working fine.
- After you create you new feature you _should_ create your unit test for this new feature and run all the unit test to check that everything is working fine.

## General guidelines

- Follow [pep8](https://realpython.com/python-pep8/#:~:text=PEP%208%2C%20sometimes%20spelled%20PEP8,and%20consistency%20of%20Python%20code.) coding conventions for maintaining the consistency in the code style.
- For code formatting use [black code formatter](https://pypi.org/project/black/)
- For linting use [flake8](https://pypi.org/project/flake8/)
- Find the data if required in below link which are used in any of the APIs.
- <https://rightdata.sharepoint.com/:f:/s/Dextrus26/Ehu253pCR0tFjuDuhcEi3isBHacJqXhH7bWdWV3la_5FVA?e=QQNzce>

## Send Kafka Messages

- To send messages to kafka you should follow these steps:

1. Import kafka function to your file:

   - `from routers.routers_dependency.kafka import send_kafka_message`

2. You can use the function to send messages to kafka:
   - send_kafka_message(topic, message)

- Remember send_kafka_message is an async function, so you should use await before the function.

## Logging

- Log messages will be shown on the terminal, but will also be saved on a .log file located at the env path.
- To log messages when developing endpoints you should follow these steps:

1. Import log function to your file:

   - `from logs import log`

2. You can use multiple levels of logging through the log variable:
   - log.trace(message)
   - log.debug(message)
   - log.info(message)
   - log.success(message)
   - log.warning(message)
   - log.error(message)
   - log.critical(message)

- NOTE: debug level is the typical when developing endpoints.

## Alembic Migrations

- DB Migrations operations are handled by [Alembic](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- Migrations are ran automatically when the application is started.
- If you are getting `Can't locate revision identified by 'xxxx'` error, you can follow the steps below to resolve it:
  - DROP the alembic_version table from the database
  - Run `alembic stamp head` to set the current revision to the latest revision
  - Run `alembic revision --autogenerate` to generate a new revision
  - Run `alembic upgrade head` to apply the new revision to the database

## Ask Albus Running on Jupyterhub

- When `ALBUS_TYPE` is set to `DOCKER` or `KUBERNETES` special care needs to be taken to ensure that the jupyterhub server is running on the same network as the dextrus data science server. This is because the dextrus data science server needs to be able to access the jupyterhub server to run the ask albus queries. To start jupyterhub please follow instructions on python_repl repository, switch between docker or kubernetes branch depending on the type of jupyterhub server you want to run. Make sure to set the environment variables `JUPYTERHUB_URL` and `JUPYTERHUB_API_TOKEN` as mentioned above.

> > > > > > > 86c8bdf091466bedb41355b2b06d4f5c1f6965b5

## data product creation help documents and successful csv stored files

<https://rightdata.sharepoint.com/:f:/s/Dextrus26/El0XUkm1txlNhYCVCP9PKn4BsygkF1hb-noF5kWcg368mA?e=fIHmad>

## creation of data product

<https://rightdata.sharepoint.com/:v:/s/Dextrus26/EfQJ8nJpoSRHnfn3TnketwQBs4hPcaF1RTmcXYpUUS04Aw?e=N4NfPv>

## DB connection creation

<https://rightdata.sharepoint.com/:v:/s/Dextrus26/EVnE2_RlyIxHlVpJAxEH6V0BfSlYRy-o-HD2_GCcOeyaMA?e=NP22tZ>

## store data from SQL server to local

<https://rightdata.sharepoint.com/:w:/s/Dextrus26/EWJU06-W9F1Ij2H8YK1UX6MBVMVoS0cFkLocqxsF6S69Vw?e=8H74vH>

### list if data products and details  

<https://rightdata.sharepoint.com/:x:/s/Dextrus26/EW-0AtSwGjZNiotXDHJ-ddgBkeUKPrs0aVVQ5UwDNAU8qQ?e=3mQT8u>

### jenkins details

### jenkins credentials

jenkins server details. <http://10.10.20.77:8080/>
Username: deploy
Password: deploy

## jenkins kt documemnt 

<https://rightdata.sharepoint.com/:w:/s/Dextrus26/EcrEwgjaFjxCg7RK8sKf2QQBfOp7NkMapzAlKJD7XvrMdQ?e=yoI9wA>
