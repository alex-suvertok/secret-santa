# Secret Santa

Secret Santa by Alex Suvertok

License: Open source

## Stack

- Django 5.2 LTS + PostgreSQL
- Email via the built-in `des` app — SMTP credentials live in the
  `DynamicEmailConfiguration` singleton (editable in admin, no restart needed)
- Docker Compose for local running: **web on `http://localhost:8001`**, Postgres on `5433`
  (host ports 8000/8080/5432 may be busy with other local projects)

## Installation

### Local (without Docker)

Requirements: Python 3.12 + virtualenv, e.g.:

```
mkvirtualenv santa
pip install -r requirements.txt
```

Create `secret_santa/secret_santa/.env` from the template:

```
cp secret_santa/secret_santa/.env.example secret_santa/secret_santa/.env
```

Then fill in real values (especially `DJANGO_SECRET_KEY` and `HASH_SALT`). The
app fails fast on missing env vars — there are no insecure hardcoded defaults.

Finally migrate and run:

```
cd secret_santa
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

### Docker (web + PostgreSQL)

```
cd secret_santa
cp secret_santa/.env.example secret_santa/secret_santa/.env   # fill in values
docker compose up --build
```

- Web app: http://localhost:8001
- Admin: http://localhost:8001/admin/
- PostgreSQL: `localhost:5433` (user/pass/db: `secret_santa`)
- On start the container waits for the DB, applies migrations and serves static
  files via WhiteNoise.

## Setting basic data

```
sh utility/loaddata_all_fixtures.sh
```

## Email setup

1. Open admin -> `DynamicEmailConfiguration` (the `des` app).
2. Set SMTP host/port/user/password, e.g. Gmail: `smtp.gmail.com`, `587`,
   `use_tls=True`, `use_ssl=False`.
3. Gmail requires an **App password** (2FA) — a regular account password is
   rejected with `535 Username and Password not accepted`.
4. Switch `fail_silently` off temporarily to see errors in logs while testing.

## Instructions for work

* Check the availability of the list of members - /admin/core/member/
  * If they are not there, check the presence of the team - /admin/core/team/
    * If the team does not exist, then create it
  * Add members to the team - /admin/core/member/
* Create a celebration - /admin/core/celebration/
* Run "Let the celebration begin!" action on selected celebrations
* Check the build on the tab "Secret santas" - /admin/core/secretsanta/
* Expect letters to the specified e-mails. To resend the letter, use action "Receive a follow-up letter with the recipient of the gift" - /admin/core/secretsanta/