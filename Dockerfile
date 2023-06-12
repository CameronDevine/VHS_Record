FROM linuxserver/ffmpeg

RUN echo -n "deb https://ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu $(cat /etc/lsb-release | grep DISTRIB_CODENAME | cut -d "=" -f 2) main" > /etc/apt/sources.list.d/deadsnakes.list && \
    apt-key adv --keyserver hkp://keyserver.ubuntu.com:80 --recv F23C5A6CF475977595C89F51BA6932366A755776
RUN apt-get update && \
    apt-get install -y \
      python3.8 \
      python3.8-distutils \
      alsa-base \
      alsa-utils \
      libsndfile1-dev \
      gstreamer1.0-tools \
      gstreamer1.0-plugins-good \
    && apt-get clean
ADD https://bootstrap.pypa.io/get-pip.py .
RUN python3.8 get-pip.py && rm get-pip.py
RUN pip install \
      flask \
      flask-socketio \
#      eventlet \
      apscheduler \
      tflite-runtime \
      rtp
COPY server /server

#ENTRYPOINT gst-launch-1.0 v4l2src device=/dev/video ! tee name=t ! queue ! v4l2sink device=/dev/video1 t. ! queue ! v4l2sink device=/dev/video2; bash
#ENTRYPOINT gst-launch-1.0 -q v4l2src device=/dev/video ! tee name=t ! queue ! autovideosink t. ! queue ! autovideosink & bash
#ENTRYPOINT bash
ENTRYPOINT []

#CMD flask --app server/app run -h 0.0.0.0
CMD python3.8 server/app.py
