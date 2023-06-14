.PHONY: build run terminal push

tag = latest
user = camerondevine
image = vhs_record

container = $(user)/$(image):$(tag)

build:
	sudo docker build -t $(container) .

video = video2
audio = 1

run:
	sudo docker run --user 0:$$(id -g) --device=/dev/$(video):/dev/video --device=/dev/snd -v "$$(pwd)/data":/data -v "$$(pwd)/config:/config" -p 5000:5000 -e AUDIO_DEVICE=$(audio) -it $(container)

terminal:
	sudo docker run --device=/dev/$(video):/dev/video --device=/dev/snd -v "$$(pwd)/data":/data -v "$$(pwd)/config:/config" -p 5000:5000 -it $(container) bash

push:
	sudo docker push $(container)
