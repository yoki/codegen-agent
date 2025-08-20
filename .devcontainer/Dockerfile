
FROM python:3.13-slim
ENV TZ=Asia/Singapore

# Install dependencies
RUN apt-get update --yes \
    && apt-get upgrade --yes \
    && apt install -y --no-install-recommends \
    wget git nano sudo curl fuse-overlayfs

# configure locale
RUN apt-get update && apt-get install -y locales-all 
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Install docker from official source to use fuse-overlayfs
# fuse-overlayfs is 5 times faster than vfs (default) 
RUN curl -fsSL https://get.docker.com -o get-docker.sh && sh get-docker.sh && rm get-docker.sh
RUN mkdir -p /etc/docker && \
    echo '{\n  "storage-driver": "fuse-overlayfs"\n}' > /etc/docker/daemon.json

# uv is faster when rebuilding the container
RUN python -m pip install -U pip setuptools wheel uv

# # create vscode-server folder for persistence of vs code extensions across reloads
RUN mkdir -p /root/.vscode-server 

# set up git (line ending and user info)
RUN git config --global user.name "Yoki" \
    && git config --global user.email "yotokyos@gmail.com" \
    && git config --global core.autocrlf input \
    && git config --global core.eol lf

# Create the idempotent Docker startup command
RUN echo '#!/bin/sh\n\
set -e\n\
if ! docker ps > /dev/null 2>&1; then\n\
    echo "Starting Docker daemon..."\n\
    nohup dockerd > /var/log/dockerd.log 2>&1 &\n\
    timeout=20\n\
    while [ ! -S /var/run/docker.sock ]; do\n\
        if [ "$timeout" -eq 0 ]; then exit 1; fi\n\
        sleep 1\n\
        timeout=$((timeout - 1))\n\
    done\n\
fi' > /usr/local/bin/start-docker \
&& chmod +x /usr/local/bin/start-docker

# nicer terminal
COPY .devcontainer/.bashrc /root/.bashrc
COPY .devcontainer/.bash_history /root/.bash_history

# Set the entrypoint to run when the container starts
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
