FROM python:3.8-alpine

RUN apk add --no-cache aria2
RUN pip install -U pip

WORKDIR /code

COPY ./requirements.txt .
RUN pip install -r requirements.txt

COPY ./init.sh .
ENTRYPOINT ["/code/init.sh"]

COPY ./src/ /code/
CMD ["python", "start.py"]
