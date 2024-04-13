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
import errno
import logging

import cv2
import numpy as np
import hashlib

from .constants import C
from .image_utils import img_sim
from .storage import bamboo_load, bamboo_save

MAXSIZE_CACHE=128
DEFAULT_JPEG_QUALITY = 90

TAG_FACE='face'
TAG_FACE_COUNT='face_count'
TAG_SKIPPED='skipped'

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
    if img is None:
        raise FileNotFoundError("cannot read:"+path)
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
    return (t[0],t[1],img_sim(t[2],t[3]))


P_PATH = 'path'
P_CROP = 'crop'

class Frame:
    """Abstraction to hold an image frame.
    If a stage modifies a Frame, it needs to make a copy first."""
    jpeg_quality = DEFAULT_JPEG_QUALITY
    def __init__(self, *, path=None, img=None, src=None, mime_type=None):
        self.path = path        # if read or written to a file, the path
        self.uri  = None        # the full uri; to replace path
        if src is not None:
            self.history = copy.copy(src.history)
        else:
            self.history  = [(P_PATH,path)]          # new history
        self.tags = []
        self.tags_added = 0

        # These are for overriding the properties
        self.w_ = None
        self.h_ = None
        self.depth_ = None
        self.bytes_ = None
        self.img_   = None
        self.mime_type_ = mime_type

        # Set the timestamp
        if path is not None:
            try:
                self.mtime = datetime.fromisoformat( os.path.splitext(os.path.basename(path))[0] )
            except ValueError:
                self.mtime = datetime.fromtimestamp(os.path.getmtime(path))
        elif img is not None:
            self.mtime = datetime.now()

    def __lt__(self, b):
        return  self.mtime < b.mtime
    def __repr__(self):
        return f"<Frame path={self.path} history={self.history} tags={[tag.tag_type for tag in self.tags]}>"

    def save(self, path):
        logging.debug("save path=%s self=%s",path,self)
        bamboo_save(path, self.jpeg_bytes)
        self.history.append((P_PATH,path))
        self.path = path


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

    def annotate( self, i, xy, w, h, text, *, textcolor=C.GREEN, boxcolor=C.RED, thickness=2):
        cv2.rectangle(i, xy, (xy[0]+w, xy[1]+h), boxcolor, thickness=thickness)
        cv2.putText(i, text, (xy[0], xy[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, textcolor, thickness=thickness)

    def add_tag(self, tag):
        # Before we add the first tag, copy the tags array so that this frame
        # has its own copy of the array
        if self.tags_added == 0:
            self.tags = copy.copy(self.tags)
        self.tags.append(tag)
        self.tags_added += 1

    def show(self, i=None, title=None, wait=0):
        """show the frame, optionally waiting for keyboard"""
        if title is None:
            title = self.path
        if title is None:
            title = str(self.history[0])
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
            if tag.tag_type==TAG_FACE:
                self.annotate( i, tag.xy, tag.w, tag.h, text=tag.text)
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
    def jpeg_bytes(self):
        """Returns as disk bytes or, if there are none, as a JPEG compressed"""
        logging.debug("self=%s",self)
        if self.path is not None:
            return bytes_read(self.path)
        return cv2.imencode('.jpg', self.img_, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])[1]

    @property
    @functools.lru_cache(maxsize=3)
    def w(self):
        return self.w_ if self.w_ is not None else self.img.shape[1]

    @property
    @functools.lru_cache(maxsize=3)
    def h(self):
        """height (y) is the first index in the shape. nparray goes from lsb to msb"""
        return self.h_  if self.h_  is not None else self.img.shape[0]

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

    def crop(self, *, xy, w, h):
        """Return a new Frame that is the old one cropped. So copy over the provenance."""
        cf = CroppedFrame(src=self, xy=xy, w=w, h=h)
        return cf

class CroppedFrame(Frame):
    def __init__(self, *, src, xy, w, h):
        super().__init__(src=src)
        self.w_ = w
        self.h_ = h
        # This is weird, but correct.
        # Slice order is y,x but the point stores x at xy[0].
        self.img_ = np.copy(src.img[xy[1]:xy[1]+h, xy[0]:xy[0]+w])
        self.path = None        # no path
        self.history.append((P_CROP, (xy,(w,h))))

class Tag:
    def __init__(self, tag_type, **kwargs):
        self.text = ""
        self.tag_type = tag_type
        for (k,v) in kwargs.items():
            setattr(self, k, v)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.tag_type} {self.__dict__.keys()}>"

    def dict(self):
        return self.__dict__

class Patch(Tag):
    """A Patch is a special kind of tag that refers to just a specific area of the Frame"""
    def __init__(self, tag_type, **kwargs):
        super().__init__(tag_type, **kwargs)

def FrameTagDict(f,t):
    return {'path':f.path, 'history':f.history, 'tag':t}
