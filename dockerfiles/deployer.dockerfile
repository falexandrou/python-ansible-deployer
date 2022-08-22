FROM python:3.8-alpine3.12

WORKDIR /root

RUN apk add --update redis \
    ansible=2.9.14-r0 \
    wget \
    bash \
    openssl openssl-dev openssh-client \
    gcc \
    musl-dev \
    libffi-dev \
    bind-tools \
    make

# Set up the environment variables
RUN mkdir -p /deployer/stackmate
RUN mkdir -p /deployer/project
RUN mkdir -p /deployer/configurations
RUN mkdir -p /deployer/ssh-keys

WORKDIR /deployer/stackmate
COPY setup.py /deployer/stackmate/setup.py
ENV CRYPTOGRAPHY_DONT_BUILD_RUST=1
RUN pip install --upgrade pip setuptools_rust
RUN pip install -e .[dev]

# Mitogen
ENV MITOGEN_DOWNLOAD_URL=https://github.com/mitogen-hq/mitogen/archive/v0.3.0rc1.tar.gz
ENV TAR_DIRECTORY_NAME=mitogen-0.3.0rc1
RUN wget ${MITOGEN_DOWNLOAD_URL} -O ${TAR_DIRECTORY_NAME}.tar.gz \
    && tar -xvzf ${TAR_DIRECTORY_NAME}.tar.gz \
    && mv ${TAR_DIRECTORY_NAME} /usr/src/mitogen \
    && rm ${TAR_DIRECTORY_NAME}.tar.gz

# Ansible config
ENV ANSIBLE_CONFIG /etc/ansible/ansible.cfg
COPY dockerfiles/ansible.cfg /etc/ansible/ansible.cfg

# SSH agent config
ENV SSH_DIR /deployer/ssh-keys
ENV SOCKET_DIR /tmp/ssh-agent
ENV SSH_AUTH_SOCK ${SOCKET_DIR}/socket
ENV SSH_AUTH_PROXY_SOCK ${SOCKET_DIR}/proxy-socket

VOLUME ${SOCKET_DIR}

# Enable mitogen - disabled for the time being
# ENV STACKMATE_MITOGEN_PATH /usr/src/mitogen/ansible_mitogen/plugins/strategy

SHELL [ "/bin/bash" ]
