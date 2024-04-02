# Bamboo DVR
Bamboom DVR is a smart digital video archiving and analysis platform.

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


## Enabling technologies we require (and what we are thinking of using)
Video change detection:


Object detection in a video:

Face recognition:

Structured database:
* Stores the result of the tagged video

Video storage:

* Can store frames or compressed video. Frames are higher quality; compressed video stores more.  (Video is compressed as a series of I & D frames)

# Prototype
Initially we will prototype a number of small scripts to get an ideas of how this stuff works.

## Storage
JPEGs: We're storing individual JPEGs in a directory hiearchy that is optimized to have 1000-5000 images per prefix (directory).

We anticipate that we'll have ~ 10-500 images per camera per day (local time or GMT is a config variables):

```
  {root}/{camera}/{year:04-month:02}/{yearmonthday-hourminsec}.jpeg
```

## ingest.py
- Iterate through all of the jpegs that have been captured in chronological order.
- When a JPEG has significantly changed, copy it to the image store (local or s3) and run it through image processing.
- Store the results of the image processing in a scalable store as a JSON object.
  - Store results by recognizer, so we can use several of them.

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


Processing Pipeline design:
1.

# Technology Stack
* Python
* OpenCV
* DynamoDB for tag storage (develop with (DynamoDB Local)[https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/DynamoDBLocal.html])
* AWS Rekognition
  - Pricing: https://aws.amazon.com/rekognition/pricing/


## Plug-in architecture
* It's clear that we will always want to be able to have a plug-in interface and be able to support multiple plugins at each step of the pipeline.
  1. We can have the plugins union, intersection, or vote.
  2. With two plugins, we can compare them against each other (for running experiments.)

Do we want to have an abstract pipeline object?
- Input and output
- Annotation
- Easily do experiments with an object that specifies multiple other objects.
- Connect them together with YAML
- Designed for running in a functions-as-a-service
- Designed for storage with an object store like S3.

# To check out
- [ ] https://docs.nvidia.com/tao/tao-toolkit-archive/5.2.0/text/visual_changenet/visual_changenet_segment.html
