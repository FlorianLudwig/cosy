FROM fedora:latest

RUN dnf install pipenv -y

RUN dnf install python3-setuptools

WORKDIR /app

COPY Pipfile* ./

RUN pipenv install --dev

COPY . .

RUN pipenv run pip install -e .
