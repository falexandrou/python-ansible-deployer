# Base image for testing ansible roles
# Inspired by https://hub.docker.com/r/geerlingguy/docker-debian8-ansible/dockerfile
FROM ubuntu:18.04
LABEL maintainer="Fotis Alexandrou"

# tzdata noninteractive
ENV DEBIAN_FRONTEND noninteractive
ENV DEBCONF_NONINTERACTIVE_SEEN true
RUN echo 'Etc/UTC' >> /etc/timezone

# Install dependencies.
RUN apt-get update -o Acquire::CompressionTypes::Order::=gz \
    && apt-get install -y --no-install-recommends \
       sudo \
       git \
       rsync \
       build-essential libffi-dev libssl-dev software-properties-common \
       python3 python3-pip python3-dev python3-mysqldb python3-pymysql python3-setuptools \
       curl gpg \
       tzdata \
       apt-transport-https gnupg2 \
    && rm -rf /var/lib/apt/lists/* \
    && rm -Rf /usr/share/doc && rm -Rf /usr/share/man \
    && apt-get clean

RUN groupadd -g 2000 stackmate \
    && groupadd -g 2001 wheel \
    && useradd -m -d /home/stackmate -s /bin/bash -g stackmate -G wheel,users,sudo stackmate

RUN echo '%wheel  ALL=(ALL)       NOPASSWD: ALL' >> /etc/sudoers
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3 10
RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 10
RUN mkdir -p /workspace && chown stackmate:stackmate /workspace
WORKDIR /workspace

USER stackmate

ENTRYPOINT []
