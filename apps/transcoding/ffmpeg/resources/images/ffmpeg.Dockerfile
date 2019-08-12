# Dockerfile with ffmpeg and python3.6

# From this image we will copy ffmpeg binaries.
FROM jrottenberg/ffmpeg:4.1-alpine AS ffmpeg-build


# Base image with alpine and python.
FROM python:3.6-alpine3.8

MAINTAINER Golem Tech <tech@golem.network>

# Create Golem standard directories.
RUN mkdir /golem \
 && mkdir /golem/work \
 && mkdir /golem/resources \
 && mkdir /golem/output


COPY ffmpeg-scripts/requirements.txt /golem/scripts/requirements.txt
RUN pip install -r /golem/scripts/requirements.txt

COPY ffmpeg-scripts/ /golem/scripts/

ENV PYTHONPATH=/golem/scripts:/golem:$PYTHONPATH

WORKDIR /golem/work/

# Copy ffmpeg bianries from jrottenberg/ffmpeg:4.1-alpine image.
COPY --from=ffmpeg-build /usr/local /usr/local
COPY --from=ffmpeg-build /usr/lib /usr/lib
COPY --from=ffmpeg-build /lib /lib

COPY ffmpeg-tools/ /ffmpeg-tools/
RUN pip3 install /ffmpeg-tools/ --upgrade

#ENTRYPOINT []
