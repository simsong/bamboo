## Other Comparisons
In creating BambooDVR, we considered:

|Product|Description|Tech|
|---|---|---|
|[Frigate]([url](https://frigate.video)https://frigate.video)|Open Source DVR system|Python and Docker|

sudo apt-get install build-essential yasm cmake libtool libc6 libc6-dev unzip wget libnuma1 libnuma-dev
apt install ninja-build
sudo apt install python3-devel

# People who have done this with Meraki cameras
https://community.meraki.com/t5/Smart-Cameras/Facial-Recognition-ANPR/m-p/94387
https://community.meraki.com/t5/Smart-Cameras/meraki-mqtt-alpr-A-program-that-uses-MV-to-do-people-vehicle-and/m-p/67191#M1653

AWS Rekogition
* https://docs.aws.amazon.com/rekognition/latest/dg/faces-detect-images.html - detect the faces in the image
* https://docs.aws.amazon.com/rekognition/latest/dg/collections.html - faces and users (groups of faces)




# install ffmpeg with H.265 installed

You need to add the rpmfusion repos and update ffmpeg:

sudo dnf install https://mirrors.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm https://mirrors.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
sudo dnf groupupdate multimedia --setop="install_weak_deps=False" --exclude=PackageKit-gstreamer-plugin --allowerasing
sudo dnf groupupdate sound-and-video


# Tutorials:
* https://www.toptal.com/computer-vision/computer-vision-pipeline
* https://medium.com/deepvisionguru/video-processing-pipeline-with-opencv-ac10187d75b
* https://pyimagesearch.com/2017/08/21/deep-learning-with-opencv/
* https://pyimagesearch.com/2018/02/26/face-detection-with-opencv-and-deep-learning/
* https://pyimagesearch.com/2017/09/11/object-detection-with-deep-learning-and-opencv/
* https://pyimagesearch.com/2017/09/18/real-time-object-detection-with-deep-learning-and-opencv/


Pipelines:
Open Source Pipelines:
* jagin/image-processing-pipeline https://github.com/jagin/image-processing-pipeline
  - Makes it easy to create single-threaded, single-path pipeline
  - Good ideas, but code doesn't generalize.
  - Article: https://medium.com/deepvisionguru/modular-image-processing-pipeline-using-opencv-and-python-generators-9edca3ccb696
  - See also: https://medium.com/deepvisionguru/dvg-utils-a-swiss-army-knife-for-opencv-processing-pipeline-b680357c084b  which describes https://github.com/jagin/dvg-utils

* Google's Media Pipe: https://developers.google.com/mediapipe.
  - Designed to create on-device ML solutions.
  - Vision, Audio, Natural Language
  - Used by Google.

* https://github.com/pipeless-ai/pipeless
  - Designed for real-time video pipelines
  - Despite its name, doesn't work on cloud storage

License plate detection:
* https://medium.com/deepvisionguru/train-license-plates-detection-model-using-detectron2-dd166154f604

# Commercial Options
https://www.eyesonit.us/
- Comptuer vision pipeline. $25 per stream/month

* Tools on top of MediaPipe: https://viso.ai/computer-vision/mediapipe/

## Face Detection and recognition
2021 literature review:
* https://www.sciencedirect.com/science/article/abs/pii/S0925231220316945

* https://cmusatyalab.github.io/openface/
* https://github.com/TadasBaltrusaitis/OpenFace - OpenFace 2.2.0
* https://www.analyticsvidhya.com/blog/2021/06/face-detection-and-recognition-capable-of-beating-humans-using-facenet/
*

* https://cvlab.cse.msu.edu/project-adaface.html

viso.ai - wraps VGG-Face, Google FaceNet, OpenFace, Facebook DeepFace, DeepID, Dlib, ArcFace
https://viso.ai/computer-vision/deepface/
- Gender, Age, Emotions, nice demos that label

Object detection:
https://viso.ai/deep-learning/detr-end-to-end-object-detection-with-transformers/

Open CV:
* https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html


Profile faces:
* https://github.com/Itseez/opencv/blob/master/data/lbpcascades/lbpcascade_profileface.xml
* https://towardsdatascience.com/face-detection-in-2-minutes-using-opencv-python-90f89d7c0f81


# Configuration and Storage
Each camera should have a unique id that appears in the config.ini file.

```
[camera_xxx]
root=location
```
where location is either:
`/directory/` --- A directory
`s3://bucket/prefix` --- A location in Amazon S3

Frames in the following hiearchy, which is designed so that there are between 500-10,000 entries per prefix:

`{root}/camera/frames/{year}{month}/{day}{hour}/{timet}.jpg`  where {timet} is unixtime * 1000 (JavaScript Time). .jpg might be .heic or some other format.


# Code to steal:
test_face_detector.py:
