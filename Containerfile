FROM python:slim

WORKDIR /proxy

RUN mkdir sockets

COPY proxy.py .

CMD ["python3", "proxy.py"]
