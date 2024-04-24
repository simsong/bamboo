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

from .frame import Frame
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
        for (k,v) in kwargs.items():
            print("set",k,v)
            setattr(self,k,v)
        print("self.limit=",self.limit)

    def draw(self):
        """Return True if we should sample."""
        print("self.limit=",self.limit)
        return self.sampling >= random.random()

    def atlimit(self):
        """Increment counter and return True if we are at the limit."""
        self.counter += 1
        if self.limit is None:
            return False
        elif self.counter >= self.limit:
            return True
        return False


def FrameFromFile(path, o:SourceOptions=SourceOptions()):
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
            if o.draw():
                yield frame.Frame(img = img,
                                  src=pathlib.Path(absolute_path_string).as_urn() + "?frame="+ct)
                if o.atlimit():
                    return

def FrameStream(root, o:SourceOptions=SourceOptions(), verbose=False):
    """Generator for a series of Frame() objects from a disk file.
    Returns frames in sort order within each directory"""
    if os.path.isdir(root):
        for (dirpath, dirnames, filenames) in os.walk(root): # pylint: disable=unused-variable
            dirnames.sort()                                  # makes the directories recurse in sort order
            for fname in sorted(filenames):
                path = os.path.join(dirpath, fname)
                mtype = mimetypes.guess_type(fname)[0]
                if mtype is None:
                    continue
                if mtype.split("/")[0] in ['video','image']:
                    if o.draw():
                        if os.path.getsize(path)>0:
                            try:
                                f = Frame(urn=path, mime_type=mtype)
                            except FileNotFoundError as e:
                                print(f"Cannot read '{path}': {e}",file=sys.stderr)
                                continue
                            yield f
                            if o.atlimit():
                                return
                if mtype=='application/json':
                    if o.draw():
                        with open(path,"r") as fd:
                            yield Frame.fromJSON(fd.read())
                        if o.atlimit():
                            return

    else:
        yield Frame(urn=root)

def DissimilarFrameStream(root, o=SourceOptions()):
    print("dfs. o.limit=",o.limit)
    ref = None
    count = 0
    for f in FrameStream(root, o=o): # do not pass options
        try:
            st = f.similarity(ref)
        except cv2.error as e: # pylint: disable=catching-non-exception
            print(f"Error: {e} with {f.urn}",file=sys.stderr)
            continue
        except FileNotFoundError as e:
            print(f"Cannot read '{f.urn}': {e}",file=sys.stderr)
            continue
        if st < o.score:
            if o.draw():
                yield f
            if o.atlimit():
                return
            ref = f
        else:
            count += 1
            logging.debug("count=%s skip %s",count,f)


def CameraFrameStream(camera=0, o:SourceOptions=SourceOptions()):
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
        if o.draw():
            yield Frame(src=f"camera{camera}")
        if o.atlimit():
            return

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
                    if o.atlimit():
                        return
