"""
This module provides the following functions:

FrameStream(root) - A generator of frames from a root
DissimilarFrameStream(root, score=0.90) - Generates a stream of frames that have a similarity score less than socre

Details:
https://stackoverflow.com/questions/11420748/setting-camera-parameters-in-opencv-python
https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html

"""

import os
import functools
from datetime import datetime
import json
import copy
import mimetypes

import cv2
import numpy as np
import hashlib

from .frame import Frame
from .constants import C
from .image_utils import img_sim

def FrameFromFile(path, mime_type=None):
    if mime_type is None:
        mine_type = mimetypes.guess_type(path)[0].split("/")[0]
    if mime_type == 'image':
        return Frame(path)
    elif mime_type == 'video':
        cap = cv2.VideoCapture(path)
        for ct in enumerate():
            ret, img = cap.read()
            if not ret:
                break
            yield frame.Frame(img = img,
                              src=pathlib.Path(absolute_path_string).as_uri() + "?frame="+ct)


def FrameStream(root):
    """Generator for a series of Frame() objects from a disk file.
    Returns frames in sort order within each directory"""
    if os.path.isdir(root):
        for (dirpath, dirnames, filenames) in os.walk(root): # pylint: disable=unused-variable
            dirnames.sort()                                  # makes the directories recurse in sort order
            for fname in sorted(filenames):
                mtype = mimetypes.guess_type(fname)[0]
                if mtype is None:
                    continue
                if mtype.split("/")[0] in ['video','image']:
                    path = os.path.join(dirpath, fname)
                    if os.path.getsize(path)>0:
                        yield Frame(path=path, mime_type=mtype)
    else:
        yield Frame(path=root)

def DissimilarFrameStream(root, score=0.90):
    ref = None
    for f in FrameStream(root):
        try:
            score = f.similarity(ref)
        except cv2.error as e: # pylint: disable=catching-non-exception
            print(f"Error {e} with {i.path}",file=sys.stderr)
            continue
        if score <= self.sim_threshold:
            yield f
            ref = f

def CameraFrameStream(camera=0,*, frameWidth=None,frameHeight=0):
    # https://docs.opencv.org/3.4/dd/d01/group__videoio__c.html
    cap = cv2.VideoCapture(camera)
    if frameWidth is not None:
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, frameWidth)
    if frameHeight is not None:
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, frameHeight)
    while True:
        ret, img = cap.read()
        if not ret:
            break
        yield Frame(src=f"camera{camera}")
