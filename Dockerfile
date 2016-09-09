FROM python:3.5
MAINTAINER Alexey Kachalov <kachalov@kistriver.com>

WORKDIR /home/app

COPY requirements.txt /home/app
RUN \
groupadd app && \
useradd --create-home --home-dir /home/app -g app app && \
pip3 install -r /home/app/requirements.txt && \
rm -rf /var/cache/apt/* /home/app/deb-packets.txt /home/app/requirements.txt
COPY src /home/app
CMD ["python3", "."]
