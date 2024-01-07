[![GitHub](https://img.shields.io/github/license/camerondevine/VHS_Record)](https://github.com/CameronDevine/VHS_Record/blob/master/LICENSE)
[![Docker Image Size (tag)](https://img.shields.io/docker/image-size/camerondevine/vhs_record/latest)](https://hub.docker.com/repository/docker/camerondevine/vhs_record/general)
[![GitHub issues](https://img.shields.io/github/issues/camerondevine/VHS_Record)](https://github.com/CameronDevine/VHS_Record/issues)

# VHS Record

This repository contains the source to create a Docker container for digitizing VHS tapes. This container uses Video4Linux and FFmpeg to do the recording and also includes an AI system for detecting when to stop recording. This software needs to be paired with hardware such as a USB or PCI based capture card and a VHS player.

## VHS End Detector

The VHS end detection system uses an AI based system. It can currently detect blue or black screens common at the end of the media being recorded. Both of these can be enabled or disabled and the confidence level to stop the recording can be set. As blue and black screens can also appear in the middle of a film, a low pass filter can be used to avoid the video stopping when these screens appear for a short period of time in the middle of a recording.

## Docker Settings

Below are the necessary and optional settings needed to setup the container.

### Port

The port 5000 must be exposed by Docker so the web UI can be accessed.

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
| V4L2_FMT                |               | The video format to request from V4L2                               |
| V4L2_FPS                |               | The frames per second to request from V4L2                          |
| V4L2_RES                |               | The resolution to request from V4L2                                 |
| VCODEC                  | h264          | The video codec to use in the output file                           |
| ACODEC                  | aac           | The audio codec to use in the output file                           |
| OUTPUT_RES              | 640x480       | The resolution to use in the output file                            |
| VIDEO_THREAD_QUEUE_SIZE | 64            | The size of the video thread queue in FFmpeg                        |
| VIDEO_FILTER            |               | FFmpeg filters to apply to the video stream                         |
| ALSA_AUDIO              | false         | Set to "true" to enable ALSA audio recording                        |
| AUDIO_DEVICE            | 1             | The audio device to use when recording audio via ALSA               |
| AUDIO_THREAD_QUEUE_SIZE | 2048          | The size of the FFmpeg audio thread queue when recording via ALSA   |
| AUDIO_CHANNELS          |               | The number of audio channels to record when using ALSA              |
| EXTENSION               | mp4           | The file extension to apply to when none is given                   |
| FFMPEG_LOG_LEVEL        | info          | The FFmpeg log level that will show up in the container logs        |
| SETUP_COMMAND           |               | An arbitrary command to run immediately before recording is started |
| SETUP_SUCCESS           | 0             | If `SETUP_COMMAND` is set, the return value to checked for          |
| SETUP_DELAY             | 0             | Number of seconds to wait before recording after the setup command  |
| MIN_LENGTH              | 30            | Minimum number of seconds to record before automatically stopping   |
