.PHONY: build run terminal push

tag = latest
user = camerondevine
image = vhs_record

container = $(user)/$(image):$(tag)

build:
	sudo docker build -t $(container) .

video = video2
audio = 1

container_start = sudo docker run --device=/dev/$(video):/dev/video0 --device=/dev/snd:/dev/snd -v "$$(pwd)/data":/data -v "$$(pwd)/config:/config"  -e INPUT_FMT=v4l2 -e V4L2_FMT=mjpeg -e VIDEO_FILTER=yadif -e ALSA_AUDIO=true -e AUDIO_DEVICE=$(audio) -e AUDIO_CHANNELS=1 -e V4L2_FPS=30 -e V4L2_RES=640x480 -p 5000:5000 -it --rm $(container)

run:
	$(container_start)

terminal:
	$(container_start) bash

push:
	sudo docker push $(container)
