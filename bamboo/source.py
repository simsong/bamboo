"""
This module provides the following functions:

FrameStream(root) - A generator of frames from a root
DissimilarFrameStream(root, score=0.90) - Generates a stream of frames that have a similarity score less than socre

Details:
https://stackoverflow.com/questions/11420748/setting-camera-parameters-in-opencv-python
https://docs.opencv.org/4.x/dd/d43/tutorial_py_video_display.html

"""

import sys
import os
import functools
from datetime import datetime
import json
import copy
import mimetypes
import logging
import pickle

import cv2
import numpy as np
import hashlib

from .frame import Frame
from .constants import C
from .image_utils import img_sim

DEFAULT_SCORE = 0.90
class SourceOptions:
    __slots__=('limit','sampling','mime_type','score','frameWidth','frameHeight')
    def __init__(self,**kwargs):
        self.score = DEFAULT_SCORE
        self.frameWidth = None
        self.frameHeight = None
        for (k,v) in kwargs:
            setattr(self,k,v)


def FrameFromFile(path, o=SourceOptions()):
    if o.mime_type is None:
        o.mine_type = mimetypes.guess_type(path)[0].split("/")[0]
    if o.mime_type == 'image':
        return Frame(path)
    elif o.mime_type == 'video':
        cap = cv2.VideoCapture(path)
        for ct in enumerate():
            ret, img = cap.read()
            if not ret:
                break
            yield frame.Frame(img = img,
                              src=pathlib.Path(absolute_path_string).as_uri() + "?frame="+ct)


def FrameStream(root, o=SourceOptions()):
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
                        try:
                            f = Frame(path=path, mime_type=mtype)
                        except FileNotFoundError as e:
                            print(f"Cannot read '{path}': {e}",file=sys.stderr)
                            continue
                        yield f
    else:
        yield Frame(path=root)

def DissimilarFrameStream(root, o=SourceOptions):
    ref = None
    count = 0
    for f in FrameStream(root):
        try:
            st = f.similarity(ref)
        except cv2.error as e: # pylint: disable=catching-non-exception
            print(f"Error: {e} with {f.path}",file=sys.stderr)
            continue
        except FileNotFoundError as e:
            print(f"Cannot read '{f.path}': {e}",file=sys.stderr)
            continue
        if st < o.score:
            yield f
            ref = f
        else:
            count += 1
            logging.debug("count=%s skip %s",count,f)


def CameraFrameStream(camera=0, o=SourceOptions()):
    # https://docs.opencv.org/3.4/dd/d01/group__videoio__c.html
    cap = cv2.VideoCapture(camera)
    if o.frameWidth is not None:
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, frameWidth)
    if o.frameHeight is not None:
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, frameHeight)
    while True:
        ret, img = cap.read()
        if not ret:
            break
        yield Frame(src=f"camera{camera}")

def TagsFromDirectory(path):
    for (dirpath, dirnames, filenames) in os.walk(path):
        for name in os.listdir(path):
            dirnames.sort()                                  # makes the directories recurse in sort order
            for fname in sorted(filenames):
                if name.endswith(".tag"):
                    with open( os.path.join(dirpath, name), "rb") as f:
                        v = pickle.load(f)
                        yield v
