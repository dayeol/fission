FROM ubuntu:18.04

WORKDIR /app

RUN apt-get update && apt-get install -y build-essential && \
    apt-get install -y python3 python3-dev libev-dev libffi-dev bash \
		python3-pip && \
    pip3 install --upgrade pip && \
    rm -r /root/.cache

COPY requirements.txt /app
RUN pip3 install -r requirements.txt

COPY . /app

ENTRYPOINT ["python3"]
CMD ["server.py"]

