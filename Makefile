.PHONY: build run terminal push

tag = latest
user = camerondevine
image = vhs_record

container = $(user)/$(image):$(tag)

build:
	sudo docker build -t $(container) .

video = video2
audio = 1

container_start = sudo docker run --device=/dev/$(video):/dev/video0 -v "$$(pwd)/data":/data -v "$$(pwd)/config:/config" -e INPUT_PATH=file:/dev/video0 -e INPUT_FMT=mpegts -e SETUP_COMMAND="v4l2-ctl -i 2 --set-audio-input 1" -e SETUP_DELAY=1 -e VIDEO_FILTER=yadif -p 5000:5000 -it --rm $(container)

run:
	$(container_start)

terminal:
	$(container_start) bash

push:
	sudo docker push $(container)
