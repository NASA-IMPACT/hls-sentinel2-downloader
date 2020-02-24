FROM python:3.8-alpine

RUN apk update
RUN apk add --no-cache aria2
RUN pip install -U pip

RUN apk add postgresql-dev gcc python3-dev musl-dev

WORKDIR /code

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./init.sh .
ENTRYPOINT ["/code/init.sh"]

COPY ./src/main/ /code/
COPY ./src/db/ /code/
CMD ["python", "start.py"]
