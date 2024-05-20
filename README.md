# Bamboo
Bamboo is a python framework that makes it easy to build performant, production-quality research pipelines for processing video and stillframe images.

## Features

* Visually compare the results of face-detection or object-classification algorithms.
* Do the same comparision methodologically over a million images, storing the results in a structured database.
* Use the same pipeline to process from a disk directory, a video file, an RTSP camera stream, or JPEGs on-demand as they are loaded into an Amazon S3 bucket.
* Debug pipelines on your laptop in an easy-to-use single-threaded environment, then deploy them on a laptop or workstation with a multi-thread server, on a cluster of high-performance servers, or in a serverless cloud environment using Amazon Lambda.
* Provides a consistent, easy-to-program object-oriented abstraction layer that easily wraps existing computer vision systems including OpenCV, YOLOv8 and Amazon Rekognition.

## Demo programs provided with Bamboo

## Terminology
`scale` - the amount to expand a face area. scale=1.0 is default (no expansion)


# Goals

Process and archive surveillance video to answer useful questions such as:
* Who was present on which days?
* How many people did we see on a day?
* Which vehicles entered our garage?
* When were people in the office?

Take data from a variety of streams, including:
* Google Nest cameras (captured from the Google Nest cloud using the API)
* Any on-prem camera (captured using either an RTSP stream or a sequence of JPEGs)
* Uploaded video
* Cell phones repurposed as surveillance cameras
* (ESP32-cam)[https://google.com/search?q=ESP32-CAM]

Plug-in architecture:
* It's clear that we will always want to be able to have a plug-in interface and be able to support multiple plugins at each step of the pipeline.
  -  We can have the plugins union, intersection, or vote.
  - With two plugins, we can compare them against each other (for running experiments.)

Processing options:
* Single-threaded on local machine for debugging
* Multi-threaded on local machine for performance
* Lambda or GCF of Azure Functions


## Enabling technologies we require (and what we are thinking of using)
* Video change detection
* Object detection in a video
* Face recognition:
* Structured database
  - Stores the result of the tagged video
* Video storage
  - Can store frames or compressed video. Frames are higher quality; compressed video stores more.  (Video is compressed as a series of I & D frames)

# Prototype
Initially we will prototype a number of small scripts to get an ideas of how this stuff works.

## Acquisition
https://meraki.cisco.com/lib/pdf/meraki_datasheet_mv_sense.pdf
https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API

## ingest.py
- Iterate through all of the jpegs that have been captured in chronological order.
- When a JPEG has significantly changed, copy it to the image store (local or s3) and run it through image processing.
- Store the results of the image processing in a scalable store as a JSON object.
  - Store results by recognizer, so we can use several of them.

## Storage
JPEGs: We're storing individual JPEGs in a directory hiearchy that is optimized to have 1000-5000 images per prefix (directory).

We anticipate that we'll have ~ 10-500 images per camera per day (local time or GMT is a config variables):

```
  {root}/{camera}/{year:04-month:02}/{yearmonthday-hourminsec}.jpeg
```

## faces.py - show all faces on a given day

# Architecture



## Ingest

Identifying which frames to process:

1. Videos are chopped into frames. (Pretty standard; ffmpeg can do this.)
2. Each frame that is the first in a sequence or significnatly different from the previous frame is tagged for processing.
3. Optionally we will tag a window around the changed frames for tagging processing as well.
4. Videos and frames are expunged after a retention time.

Current implementation:
* (ingest.py)[./ingest.py]

## Processing
Processing frames:
1. Each frame is represented by an object.
2. Any number of processors can review a frame. We would likely have taggers for:
   - Faces (input: frame; output: face regions)
   - Objects (input: frame; output: objects)
   - Face vectors (input: face regions; output: face vectors)
   - Identities (input: face vectors; output: identities)
3. Pipeline is constructed as a series of producer/consumer queues.
   - Makes it easy to support multi-threaded and multi-processing environments.
   - Ensemble processors are processors that have a single input, run multiple sub-processors, and have a single output.
     - An ensemble processor automatically stores results that can be used for producing experimental reports.


# Technology Stack
* Python
* OpenCV
* DynamoDB for tag storage (develop with (DynamoDB Local)[https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html])
* AWS Rekognition
  - Pricing: https://aws.amazon.com/rekognition/pricing/
* Open Source Face Recognition options
  * OpenFace - https://github.com/TadasBaltrusaitis/OpenFace - v2.2.0 - July 13, 2019
* Open Source frameworks:
  * Facenet - https://github.com/davidsandberg/facenet - (2018)
  * face_recognition - https://github.com/ageitgey/face_recognition - "The world's simplest facial recognition api for Python and the command line" (2018)
  * https://github.com/serengil/deepface (current)
    - "A Lightweight Face Recognition and Facial Attribute Analysis (Age, Gender, Emotion and Race) Library for Python"
    - pip install
    - highly accurate detection
    - Creates embeddings
    - "Deepface is a hybrid face recognition package. It currently wraps many state-of-the-art face recognition models: VGG-Face , Google FaceNet, OpenFace, Facebook DeepFace, DeepID, ArcFace, Dlib, SFace and GhostFaceNet. The default configuration uses VGG-Face model."
  * https://github.com/SthPhoenix/InsightFace-REST (current) - NVIDIA & TensorRT for optimized inference

Face clustering:
 * https://pyimagesearch.com/2018/07/09/face-clustering-with-python/

Do we want to have an abstract pipeline object?
- Input and output
- Annotation
- Easily do experiments with an object that specifies multiple other objects.
- Connect them together with YAML
- Designed for running in a functions-as-a-service
- Designed for storage with an object store like S3.

# To check out
- [ ] https://docs.nvidia.com/tao/tao-toolkit-archive/5.2.0/text/visual_changenet/visual_changenet_segment.html

# See Also
* https://universe.roboflow.com/ - "The world's largest collection of open source computer vision datasets and APIs." (Unfortunately, no consistent API).
* https://dl.acm.org/doi/10.1145/2393347.2393394
* https://dl.acm.org/doi/10.1145/2733373.2806229
* https://ieeexplore.ieee.org/document/7225141
* https://ieeexplore.ieee.org/document/8438958

To test the deepface tagger:
python -m bamboo.face_deepface --debug --root <dir>
===
To optimize TensorFlow for my platform:
git clone https://github.com/tensorflow/tensorflow.git
./configure
bazel build --config=opt //tensorflow/tools/pip_package:build_pip_package
bazel-bin/tensorflow/tools/pip_package/build_pip_package /tmp/tensorflow_pkg
pip install /tmp/tensorflow_pkg/tensorflow-<version>-<build_info>.whl
===
Notes on using Yolov8 with the Coral TPU:
https://github.com/ultralytics/ultralytics/issues/4719
https://docs.ultralytics.com/guides/coral-edge-tpu-on-raspberry-pi/
https://ipcamtalk.com/threads/yolo-v8-issue-with-coral-tpu.74987/
https://docs.ultralytics.com/integrations/edge-tpu/

Dump the face confidence of every tag in a dir:
jq '.tags[0].face_confidence' ~/tagdir/000/*.json