# pull official base image
FROM mambaorg/micromamba:debian12-slim

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# install dependencies
RUN micromamba install -y -n base -c conda-forge python=3.12 pip graph-tool=2.97 && \
    micromamba clean --all --yes

ARG MAMBA_DOCKERFILE_ACTIVATE=1

COPY ./requirements.txt /usr/src/app/requirements.txt
RUN --mount=type=cache,target=/root/.cache/pip \
	pip install --upgrade pip && \
	pip install -r requirements.txt

# DOES NOT WORK BECAUE APT-GET INSTALL TO INCOMPATIBLE PYTHON EVN 
#RUN --mount=type=cache,target=/var/cache/apt,sharing=locked \
#    --mount=type=cache,target=/var/lib/apt,sharing=locked \
#    echo "deb http://downloads.skewed.de/apt bullseye main" >> /etc/apt/sources.list && \
#	apt-key adv --keyserver keyserver.ubuntu.com --recv-key 612DEFB798507F25 && \
#	apt-get update && \
#	apt-get install -y python3-graph-tool

# copy project
COPY . /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/local/bin/_entrypoint.sh", "/usr/src/app/entrypoint.sh"]
