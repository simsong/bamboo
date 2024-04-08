"""This module provides the following classes:

Patch - Describes a particular rectangular patch of a frame.

Frame - Holds individual frames and logic for working on individual frames with OpenCV.
FrameArray - An array of frames

Tag - For adding (k,v) tags to Frames. The "v" is an arbitrary python value or object.

Frames based on disk files are cached in memory with an LRU
cache. This allows millions of frames to be kept in memory using only
megabytes rather than terabytes of RAM.

"""
import os
import functools
from datetime import datetime
import json
import copy

import cv2
import numpy as np
import hashlib

from .constants import C
from .image_utils import img_sim

MAXSIZE_CACHE=128

FACE='face'
PT1 = 'pt1'
PT2 = 'pt2'
TEXT = 'text'



## several functions for reading images. All cache.
## This allows us to just pass around the path and read the bytes or the cv2 image rapidly from the cache

@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def bytes_read(path):
    """Returns the file, which is compressed as a JPEG"""
    with open(path,"rb") as f:
        return f.read()

@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def hash_read(path):
    """Return the first 256 bits of a SHA-512 hash. We do this because SHA-512 is faster than SHA-256"""
    return "SHA-512/256:" + hashlib.sha512(bytes_read(path)).digest()[:32].hex()


@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def image_read(path):
    """Caching image read. We cache to minimize what's stored in memory. We make it immutable to allow sharing"""
    img = cv2.imdecode(np.frombuffer( bytes_read(path), np.uint8), cv2.IMREAD_ANYCOLOR)
    img.flags.writeable = False
    return img

@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def image_grayscale(path):
    """Caching image bw. We cache to minimize what's stored in memory"""
    img = cv2.cvtColor(image_read(path), cv2.COLOR_BGR2GRAY)
    img.flags.writable = False
    return img

def similarity_for_two(t):
    """Similarity of two CV2 images on a scale of 0 to 1.0.
    This form is used to allow for multiprocessing, since we cannot send . """
    return (t[0],t[1],img_sim(t[2],t[3]).score)


class Frame:
    """Abstraction to hold an image frame.
    If a stage modifies a Frame, it needs to make a copy first."""
    def __init__(self, *, path=None, img=None, src=None, mime_type=None):
        self.path = path
        self.src  = src
        self.tags = []
        self.tags_added = 0
        # These are for overriding the properties
        self.width_ = None
        self.height_ = None
        self.depth_ = None
        self.bytes_ = None
        self.img_   = None
        self.mime_type_ = mime_type

        # Set the timestamp
        if path is not None:
            self.src = path
            try:
                self.mtime = datetime.fromisoformat( os.path.splitext(os.path.basename(path))[0] )
            except ValueError:
                self.mtime = datetime.fromtimestamp(os.path.getmtime(path))
        elif img is not None:
            self.mtime = datetime.now()

    def __lt__(self, b):
        return  self.mtime < b.mtime
    def __repr__(self):
        return f"<Frame path={self.path} src={self.src} tags={self.tags}>"

    def save(self, fname):
        cv2.imwrite(fname, self.img)

    def copy(self):
        """Returns a copy, but with the original img and tags. Setting a tag makes that copy.
        If you want to draw into the img, use crop() or writable_copy()
        """
        return copy.copy(self)

    def writable_copy(self):
        """Returns a copy into which we can write"""
        c = self.copy()
        c.img_ = self.img.copy()
        c.img_.flags.writable=True
        c.path_ = None
        return c

    def hash(self):
        """Return a unique hash of the image"""
        return hash_read(self.path)

    def annotate( self, i, pt1, pt2, text, *, textcolor=C.GREEN, boxcolor=C.RED, thickness=2):
        (x,y) = pt1
        cv2.rectangle(i, pt1, pt2, boxcolor, thickness=thickness)
        cv2.putText(i, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, textcolor, thickness=thickness)

    def add_tag(self, tag):
        # Before we add the first tag, copy the tags array so that this frame has its own copy of the array
        if self.tags_added == 0:
            self.tags = copy.copy(self.tags)
        self.tags.append(tag)
        self.tags_added += 1

    def show(self, i=None, title=None, wait=0):
        """show the frame, optionally waiting for keyboard"""
        if title is None:
            title = self.path
        if title is None:
            title = self.src
        if title is None:
            title = ""
        if i is None:
            i = self.img
        cv2.namedWindow(title, 0)
        cv2.imshow(title, i)
        cv2.waitKey(wait)

    def show_tags(self, title=None, wait=0):
        i = self.img.copy()
        for tag in self.tags:
            if tag.type==FACE:
                self.annotate( i, tag.pt1, tag.pt2, text=tag.text)
        self.show(i=i, title=title, wait=wait)

    @property
    def img(self):
        """return an opencv image object that is not writable."""
        return self.img_ if self.img_ is not None else image_read(self.path)

    @property
    def img_grayscale(self):
        """return an opencv image object in grayscale."""
        return image_read(self.path)

    @property
    def bytes(self):
        """Returns as disk bytes or, if there are none, as a JPEG compressed"""
        if self.path is not None:
            return bytes_read(self.path)
        return cv.imencode('.jpg', self.img_, [cv2.IMWRITE_JPEG_QUALITY, 90])[1]

    @property
    @functools.lru_cache(maxsize=3)
    def width(self):
        return self.width_ if self.width_ is not None else self.img.shape[1]

    @property
    @functools.lru_cache(maxsize=3)
    def height(self):
        """height (y) is the first index in the shape. nparray goes from lsb to msb"""
        return self.height_  if self.height_  is not None else self.img.shape[0]

    @property
    @functools.lru_cache(maxsize=3)
    def depth(self):
        return self.depth_ if self.depth_ is not None else self.img.shape[2]

    @functools.lru_cache(maxsize=10)
    def similarity(self, i2):
        """Return the simularity score with img"""
        if i2 is None:
            return 0            # not similar at all
        return img_sim(self.img, i2.img)

    def crop(self, pt1, pt2):
        """Return a new Frame that is the old one cropped"""
        cf = CroppedFrame(self, pt1, pt2)
        return cf

class CroppedFrame(Frame):
    def __init__(self, src, pt1, pt2):
        super().__init__()
        min_x = min(pt1[0],pt2[0])
        min_y = min(pt1[1],pt2[1])
        max_x = max(pt1[0],pt2[0])
        max_y = max(pt1[1],pt2[1])
        self.src = f"Cropped from {self.src} [{min_x}:{max_x}, {min_y}:{max_y}]"
        self.width_ = max_x - min_x
        self.height_ = max_y - min_y
        self.img_ = np.copy(src.img[min_y:max_y, min_x:max_x])

class Tag:
    def __init__(self, *args, **kwargs):
        self.text = ""
        self.pt2_ = None
        self.w_   = None
        self.h_   = None
        if len(args)==1:
            self.type = args[0]
        for (k,v) in kwargs.items():
            if k=='pt2':
                self.pt2_ = v
            elif k=='w':
                self.w_ = v
            elif k=='h':
                self.h_ = v
            else:
                setattr(self, k, v)

    @property
    def pt2(self):
        if self.pt2_ is not None:
            return self.pt2_
        if self.w_ is None or self.h_ is None:
            raise AttributeError(".pt2 requested but neither .pt2 nor .w and .h are set")
        return (self.pt1[0] + self.w_, self.pt1[0]+self.h_)

    def w(self):
        if self.w_ is not None:
            return self.w_
        return self.pt2[0]-self.pt1[0]

    def h(self):
        if self.h_ is not None:
            return self.h_
        return self.pt2[0]-self.pt1[0]

    def __repr__(self):
        return f"<TAG {self.type} {json.dumps(self.__dict__,default=str)}>"
