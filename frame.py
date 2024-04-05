"""
Frame holds individual frames and logic for working on individual frames with OpenCV.
"""
import os
import functools
from datetime import datetime
import json
import copy

import cv2
import numpy as np
import hashlib

from constants import C
from similarity.sim1 import img_sim

## several functions for reading images. All cache.
## This allows us to just pass around the path and read the bytes or the cv2 image rapidly from the cache

@functools.lru_cache(maxsize=128)
def bytes_read(path):
    with open(path,"rb") as f:
        return f.read()

@functools.lru_cache(maxsize=128)
def hash_read(path):
    """Return the first 256 bits of a SHA-512 hash. We do this because SHA-512 is faster than SHA-256"""
    return "SHA-512/256:" + hashlib.sha512(bytes_read(path)).digest()[:32].hex()


@functools.lru_cache(maxsize=128)
def image_read(path):
    """Caching image read. We cache to minimize what's stored in memory. We make it immutable to allow sharing"""
    img = cv2.imdecode(np.frombuffer( bytes_read(path), np.uint8), cv2.IMREAD_ANYCOLOR)
    img.flags.writeable = False
    return img

@functools.lru_cache(maxsize=128)
def image_grayscale(path):
    """Caching image bw. We cache to minimize what's stored in memory"""
    img = cv2.cvtColor(image_read(path), cv2.COLOR_BGR2GRAY)
    img.flags.writable = False
    return img

def similarity_for_two(t):
    """Similarity of two CV2 images on a scale of 0 to 1.0.
    This form is used to allow for multiprocessing, since we cannot send . """
    return (t[0],t[1],img_sim(t[2],t[3]).score)


FACE='face'
PT1 = 'pt1'
PT2 = 'pt2'
TEXT = 'text'

class Tag:
    def __init__(self, *args, **kwargs):
        if len(args)==1:
            self.type = args[0]
        for (k,v) in kwargs.items():
            setattr(self, k, v)
    def __repr__(self):
        return f"<TAG {self.type} {json.dumps(self.__dict__)}>"


class Frame:
    """Abstraction to hold an image frame. If a stage modifies a Frame, it needs to make a copy first."""
    def __init__(self, *, path=None):
        self.path = path
        self.src  = path
        self.tags = []
        self.tags_added = 0
        # These are for overriding the properties
        self.width_ = None
        self.height_ = None
        self.depth_ = None
        self.bytes_ = None
        self.img_   = None
        # Read the timestamp from the filename if present, otherwise gram from mtime
        try:
            self.mtime = datetime.fromisoformat( os.path.splitext(os.path.basename(path))[0] )
        except ValueError:
            self.mtime = datetime.fromtimestamp(os.path.getmtime(path))
        except TypeError:
            self.mtime = datetime.now()

    def __lt__(self, b):
        return  self.mtime < b.mtime
    def __repr__(self):
        return f"<Frame path={self.path}>"

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

    @classmethod
    def FrameStream(cls, source):
        """Generator for a series of Frame() objects."""
        if os.path.isdir(source):
            for (dirpath, dirnames, filenames) in os.walk(source): # pylint: disable=unused-variable
                for fname in sorted(filenames):
                    if os.path.splitext(fname)[1].lower() in C.IMAGE_EXTENSIONS:
                        path = os.path.join(dirpath, fname)
                        if os.path.getsize(path)>0:
                            yield Frame(path=path)
        else:
            yield Frame(path=source)

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
        return self.img.tobytes()

    @property
    @functools.lru_cache(maxsize=3)
    def width(self):
        return self.width_ if self.width_ is not None else self.img.shape[0]

    @property
    @functools.lru_cache(maxsize=3)
    def height(self):
        return self.height_  if self.height_  is not None else self.img.shape[1]

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
        cf.src = "Cropped from "+self.src
        return cf

class CroppedFrame(Frame):
    def __init__(self, src, pt1, pt2):
        super().__init__()
        self.width_ = pt2[0]-pt1[0]
        self.height_ = pt2[1]-pt1[1]
        self.img_ = np.copy(src.img[pt1[1]:pt2[1], pt1[0]:pt2[0]])
        self.bytes_ = self.img_.tobytes()

class FrameArray(list):
    """Array of frames"""
    def __init__(self, *args, **kwargs):
        super().__init__(self, *args, **kwargs)
        self.sorted = False

    def add(self, item):
        self.append(item)
        self.sorted = False

    def sort(self):
        if not self.sorted:
            super().sort()
            self.sorted=True

    def firstn(self, n):
        self.sort()
        return self[0:n]

    def lastn(self, n):
        self.sort()
        return sorted(self[-n:], reverse=True)

    def first(self):
        return self.firstn(1)[0]
