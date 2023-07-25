# VHS Record

This repository contains the source to create a Docker container for digitizing VHS tapes. This container uses Video4Linux and FFmpeg to do the recording and also includes an AI system for detecting when to stop recording. This software needs to be paired with hardware such as a USB or PCI based capture card and a VHS player.

## VHS End Detector

The VHS end detection system uses an AI based system. It can currently detect blue or black screens common at the end of the media being recorded. Both of these can be enabled or disabled and the confidence level to stop the recording can be set. As blue and black screens can also appear in the middle of a film, a low pass filter can be used to avoid the video stopping when these screens appear for a short period of time in the middle of a recording. The code used to train this AI system can be found here.

## Docker Settings

Below are the necessary and optional settings needed to setup the container.

### Devices

To allow the Docker container to access the capture card, one or more devices must be mapped into the container.

| Docker Mountpoint | Use                                   |
| ----------------- | ------------------------------------- |
| `/dev/video0`     | The capture device to use             |
| `/dev/snd`        | Necessary if ALSA audio is to be used |

### Volumes

Two volumes are necessary for the container to operate.

| Docker Mountpoint | Use                                      |
| ----------------- | ---------------------------------------- |
| `/config`         | The location where settings are saved to |
| `/data`           | The location to save recordings to       |

### Environment Variables

There are multiple environment variables that can be used to customize the function of the Docker container.

| Environment Variable    | Default Value | Use                                                                 |
| ----------------------- | ------------- | ------------------------------------------------------------------- |
| INPUT_FMT               | v4l2          | The input format for the capture card used in FFmpeg                |
| INPUT_PATH              | /dev/video0   | The path to the capture card to use with FFmpeg                     |
| VCODEC                  | h264          | The video codec to use in the output file                           |
| ACODEC                  | aac           | The audio codec to use in the output file                           |
| OUTPUT_RES              | 640x480       | The resolution to use in the output file                            |
| VIDEO_THREAD_QUEUE_SIZE | 64            | The size of the video thread queue in FFmpeg                        |
| VIDEO_FILTER            |               | FFmpeg filters to apply to the video stream                         |
| ALSA_AUDIO              | false         | Set to "true" to enable ALSA audio recording                        |
| AUDIO_DEVICE            | 1             | The audio device to use when recording audio via ALSA               |
| AUDIO_THREAD_QUEUE_SIZE | 2048          | The size of the FFmpeg audio thread queue when recording via ALSA   |
| EXTENSION               | mp4           | The file extension to apply to when none is given                   |
| FFMPEG_LOG_LEVEL        | info          | The FFmpeg log level that will show up in the container logs        |
| SETUP_COMMAND           |               | An arbitrary command to run immediately before recording is started |
| SETUP_SUCCESS           | 0             | If `SETUP_COMMAND` is set, the return value to checked for          |
| SETUP_DELAY             | 0             | Number of seconds to wait before recording after the setup command  |
