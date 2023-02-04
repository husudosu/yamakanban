# Yamakanban

Yamakanban is a self-hosted kanban style board system. You can run on your own server withtout a big hassle.

**_This is an Alpha version!You can experience lot of issues, some features missing. Check out Roadmap for planned features._**

# Features

-   Invite/revoke user access to boards,
-   Has basic permission support for boards,
-   Card features:
    -   Assign multiple dates, users to your cards,
    -   Create checklists and assign items to your users,
    -   Edit description of cards by using Markdown syntax,
    -   Communicate with other board members via a simple comment system,
    -   Browse history of your cards.
-   Archive your boards and cards and restore them later or delete them permanently.
-   Check out board activities including all events
-   See most of activities without refreshing your browser.

# Setup

You need docker, docker-compose and git client on your PC.

Clone the repo with this command:

```bash
# This command gonna fetch yamakanban and frontend module.
git clone https://github.com/husudosu/yamakanban --recurse-submodules
cd yamakanban
```

After cloning is done, you have to create a production.env, you could copy sample.env.

## Configuration variables:

| Variable                | Description                                                              | Required to change | Default value |
| ----------------------- | ------------------------------------------------------------------------ | ------------------ | ------------- |
| **SECRET_KEY**          | **VERY IMPORTANT!** You have to use unique key see "Generate secure key" | **YES**            | N/A           |
| **JWT_SECRET_KEY**      | **VERY IMPORTANT!** You have to use unique key see "Generate secure key" | **YES**            | N/A           |
| **POSTGRES_PASSWORD**   | **VERY IMPORTANT!** Create a secure password for your database!          | **YES**            | change-it     |
| **POSTGRES_USER**       | PostgreSQL username.                                                     |                    | yamakanban    |
| **POSTGRES_DB**         | PostgreSQL database name.                                                |                    | yamakanban    |
| **POSTGRES_HOST**       | PostgreSQL database host.                                                |                    | yamakanban_db |
| **DEFAULT_TIMEZONE**    | Default timezone.                                                        |                    | UTC           |
| **MAIL_SERVER**         | Mail server                                                              |                    | N/A           |
| **MAIL_PORT**           | Mail port                                                                |                    | N/A           |
| **MAIL_USE_TLS**        | Mail use TLS                                                             |                    | 0             |
| **MAIL_USE_SSL**        | Mail use SSL                                                             |                    | 0             |
| **MAIL_USERNAME**       | Mail username                                                            |                    | N/A           |
| **MAIL_PASSWORD**       | Mail password                                                            |                    | N/A           |
| **MAIL_DEFAULT_SENDER** | Mail default sender                                                      |                    | N/A           |
| **PROFILER_ENABLED**    | Profiler useful for developers. Disabled by default                      |                    | 0             |

### Generate secure key

**JWT_SECRET_KEY** and **SECRET_KEY** requires an unique safe key!
You can generate by using:

```bash
python3 -c "import os; print(os.urandom(10))"
b'=\xb0\x19\xcf\xa8LAz\xc8\xc8'
# THIS IS AN EXAMPLE OUTPUT DO NOT USE FOR PRODUCTION!
# Copy the string between the two apostrophes!
```

## Build and run container

```bash
docker-compose build
docker-compose up -d
```

That's all you could access the system by using your browser. https://localhost

## Default username and password

**username:** admin

**password:** admin

# Updating

Go into the root of the project where docker-compose.yml file is and run:

```bash
docker-compose stop
git pull --recurse-submodules
docker-compose build
docker-compose up -d
```

# Reporting issues

Please provide some information before you report an issue here.

Be sure you running on the most recent version of the project! For reporting issue please provide exact insturctions, how to reproduce the issue!

# Roadmap

Before we go into beta phase, need to implement these functions:

-   [ ] Do unit tests (already existing unit tests are very old.)
-   [ ] E-mail notification system
    -   [ ] You've been assigned to card/checklsit item,
    -   [ ] Date notification for assigned users (created, due date near, expired, date have been changed),
    -   [ ] New checklist, checklist item created,
-   [ ] Add @usertomention support to comment system,
-   [ ] Make better user experience,
-   [ ] Notify users about new versions on frontend,
-   [ ] Better smartphone support,
-   [ ] Refactor code both on backend and frontend. Create API documentation.

And of course fix all the bugs :-)

# For developers

## Create environment

```bash
virtualenv venv
source venv/bin/activate
pip install -r REQUIREMENTS.txt
```

## Run development Flask server

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1
pyhton3 run.py
```

## Run celery worker

```bash
export FLASK_APP=run.py
export FLASK_ENV=development
export FLASK_DEBUG=1
celery -A run.celery worker -l info -c 4 -n my_worker -E
```
