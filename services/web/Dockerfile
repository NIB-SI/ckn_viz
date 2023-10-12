# pull official base image
FROM continuumio/miniconda3:23.5.2-0

# set work directory
WORKDIR /usr/src/app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

RUN conda install -c conda-forge -y gcc
RUN conda install -c conda-forge graph-tool

# install dependencies
RUN pip install --upgrade pip
COPY ./requirements.txt /usr/src/app/requirements.txt
RUN pip install -r requirements.txt

#RUN echo "deb http://downloads.skewed.de/apt bullseye main" >> /etc/apt/sources.list && \
#    apt-key adv --keyserver keyserver.ubuntu.com --recv-key 612DEFB798507F25 && \
#    apt-get update && \
#    apt-get install python3-graph-tool -y

#RUN --mount=type=cache,target=/root/.cache/pip pip install -r requirements.txt

# copy project
COPY . /usr/src/app/

# run entrypoint.sh
ENTRYPOINT ["/usr/src/app/entrypoint.sh"]
