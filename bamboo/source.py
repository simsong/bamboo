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
import random

import cv2
import numpy as np
import hashlib

from .frame import Frame,NotImageError
from .constants import C
from .image_utils import img_sim

DEFAULT_SCORE = 0.90
class SourceOptions:
    __slots__=('limit','sampling','mime_type','score','frameWidth','frameHeight','counter')
    def __init__(self,**kwargs):
        self.limit = None
        self.sampling = 1.0     # fraction we keep
        self.score = DEFAULT_SCORE
        self.frameWidth = None
        self.frameHeight = None
        self.counter = 0
        self.mime_type = None
        for (k,v) in kwargs.items():
            setattr(self,k,v)

    def draw(self):
        """Return True if we should sample."""
        return self.sampling >= random.random()

    def inc_counter(self):
        """Increment counter and return True if we are at the limit."""
        self.counter += 1
        if self.limit is None:
            return False
        elif self.counter >= self.limit:
            raise StopIteration()


    def __repr__(self):
        return f"<SourceOptions limit={self.limit} sampling={self.sampling} score={self.score} counter={self.counter}>"

FRAME_FILE_TYPES = ['image/jpeg', 'application/json', 'video/mp4']
def FramesFromFile(path, o:SourceOptions=SourceOptions()):
    # Check to see if mime type is being overridden by option
    logging.debug("FramesFromFile(%s,%s)",path,o)
    mime_type = o.mime_type
    if mime_type is None:
        mime_type = mimetypes.guess_type(path)[0]
    if mime_type == 'image/jpeg':
        # Process image
        if C.MIN_JPEG_SIZE <= os.path.getsize(path) <= C.MAX_JPEG_SIZE:
            try:
                yield Frame(urn=path, mime_type=mime_type)
            except FileNotFoundError as e:
                print(f"Cannot read '{path}': {e}",file=sys.stderr)
        else:
            logging.debug("JPEG file too big: %s (%s bytes)",path,os.path.getsize(path))
    elif mime_type == 'application/json':
        # Look for our JSON format
        with open(path,"r") as fd:
            yield Frame.fromJSON(fd.read())
    elif mime_type == 'video/mp4':
        # Read frames from a video file
        cap = cv2.VideoCapture(path)
        logging.debug("cv2.VideoCapture(%s)=%s",path,cap)
        for counter in range(1_000_000_000):
            ret, img = cap.read()
            if not ret:
                break;
            if len(img)==0:
                continue
            urn = f"{path}?frame={counter}"
            yield Frame(urn=urn, img=img)
    else:
        raise ValueError(f"Unknown mime type: {mime_type} path={path}")


def FrameStream(root, o:SourceOptions=SourceOptions(), verbose=False):
    """Generator for a series of Frame() objects from a disk file.
    Returns frames in sort order within each directory"""
    logging.debug("FrameStream(%s, %s, verbose=%s)", root, o, verbose)
    if os.path.isdir(root):
        for (dirpath, dirnames, filenames) in os.walk(root): # pylint: disable=unused-variable
            dirnames.sort()                                  # makes the directories recurse in sort order
            for fname in sorted(filenames):
                path = os.path.join(dirpath, fname)
                mtype = mimetypes.guess_type(fname)[0]
                if mtype in FRAME_FILE_TYPES:
                    yield from FramesFromFile(path, o)
                    o.inc_counter()

    else:
        yield from FramesFromFile(root)

def DissimilarFrameStream(root, o=SourceOptions()):
    logging.debug("DissimilarFrameStream(%s,%s,%s)",root,o)
    ref = None
    count = 0
    for f in FrameStream(root, o=o): # do not pass options
        logging.debug("f=%s",f)
        try:
            st = f.similarity(ref)
        except cv2.error as e: # pylint: disable=catching-non-exception
            print(f"Error: {e} with {f.urn}",file=sys.stderr)
            continue
        except FileNotFoundError as e:
            print(f"Cannot read '{f.urn}': {e}",file=sys.stderr)
            continue
        except NotImageError as e:
            print(f"Not an image file '{f.urn}': {e}",file=sys.stderr)
            continue
        print(f"st={st} o.score={o.score}")
        if st < o.score:
            if o.draw():
                yield f
            o.inc_counter()
            ref = f
        else:
            count += 1
            logging.debug("count=%s skip %s",count,f)


def CameraFrameStream(camera=0, o:SourceOptions=SourceOptions()):
    # https://docs.opencv.org/3.4/dd/d01/group__videoio__c.html
    logging.debug("CameraFrameStream(%s)",camera)
    cap = cv2.VideoCapture(camera)
    if o.frameWidth is not None:
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH, frameWidth)
    if o.frameHeight is not None:
        cap.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT, frameHeight)
    while True:
        ret, img = cap.read()
        if not ret:
            break
        if o.draw():
            yield Frame(src=f"camera{camera}")
        o.inc_counter()

def TagsFromDirectory(path, o:SourceOptions=SourceOptions()):
    logging.debug("path=%s",path)
    for (dirpath, dirnames, filenames) in os.walk(path):
        logging.debug("dirpath=%s",path)
        dirnames.sort()                                  # makes the directories recurse in sort order
        for fname in sorted(filenames):
            if fname.endswith(".tag"):
                with open( os.path.join(dirpath, fname), "rb") as f:
                    v = pickle.load(f)
                    if o.draw():
                        yield v
                    o.inc_counter()
