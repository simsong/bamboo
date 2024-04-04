"""
Frame holds individual frames and logic for working on individual frames with OpenCV.
"""
import os
import functools
from datetime import datetime
import json

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
    """Caching image read. We cache to minimize what's stored in memory"""
    #return cv2.imread(path)
    return cv2.imdecode(np.frombuffer( bytes_read(path), np.uint8), cv2.IMREAD_ANYCOLOR)

@functools.lru_cache(maxsize=128)
def image_grayscale(path):
    """Caching image bw. We cache to minimize what's stored in memory"""
    return cv2.cvtColor(image_read(path), cv2.COLOR_BGR2GRAY)

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
    """Abstraction to hold an image frame."""
    def __init__(self, *, path=None):
        self.path = path
        self.tags = []
        self.prev = None        # previous image
        self.copy = None        # for annotation
        # Read the timestamp from the filename if present, otherwise gram from mtime
        try:
            self.mtime = datetime.fromisoformat( os.path.splitext(os.path.basename(path))[0] )
        except ValueError:
            self.mtime = datetime.fromtimestamp(os.path.getmtime(path))

    def __lt__(self, b):
        return  self.mtime < b.mtime
    def __repr__(self):
        return f"<Frame {os.path.basename(self.path)}>"

    def hash(self):
        """Return a unique hash of the image"""
        return hash_read(self.path)

    def annotate( self, i, pt1, pt2, text, *, textcolor=C.GREEN, boxcolor=C.RED, thickness=2):
        (x,y) = pt1
        cv2.rectangle(i, pt1, pt2, boxcolor, thickness=thickness)
        cv2.putText(i, text, (x, y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.8, textcolor, thickness=thickness)

    def add_tag(self, tag):
        self.tags.append(tag)

    def show_tags(self, title=None, wait=0):
        if title is None:
            title=self.path
        i = self.img.copy()
        for tag in self.tags:
            if tag.type==FACE:
                self.annotate( i, tag.pt1, tag.pt2, text=tag.text)
        cv2.namedWindow(title, 0)
        cv2.imshow(title, i)
        cv2.waitKey(wait)

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
        """return an opencv image object."""
        return image_read(self.path)

    @property
    def img_grayscale(self):
        """return an opencv image object in grayscale."""
        return image_read(self.path)

    @property
    def bytes(self):
        return bytes_read(self.path)

    @property
    @functools.lru_cache(maxsize=3)
    def width(self):
        return self.img.shape[0]

    @property
    @functools.lru_cache(maxsize=3)
    def height(self):
        return self.img.shape[1]

    @property
    @functools.lru_cache(maxsize=3)
    def depth(self):
        return self.img.shape[2]

    @functools.lru_cache(maxsize=10)
    def similarity(self, i2):
        """Return the simularity score with img"""
        if i2 is None:
            return 0            # not similar at all
        return img_sim(self.img, i2.img)

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

    def set_prev_pointers(self):
        self.sort()
        for n in range(1,len(self)):
            self[n].prev = self[n-1]
