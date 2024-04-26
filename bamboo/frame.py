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

class NotImageError(RuntimeError):
    """cv2 cannot read image"""

def json_loads_removing_version(d):
    nd = json.loads(d)
    if 'version' in nd:
        del nd['version']
    return nd

## several functions for reading images. All cache.
## This allows us to just pass around the urn and read the bytes or the cv2 image rapidly from the cache

@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def bytes_read(urn):
    """Returns the file, which is compressed as a JPEG"""
    assert urn is not None
    with open(urn,"rb") as f:
        return f.read()

@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def hash_read(urn):
    """Return the first 256 bits of a SHA-512 hash. We do this because SHA-512 is faster than SHA-256"""
    return "SHA-512/256:" + hashlib.sha512(bytes_read(urn)).digest()[:32].hex()


@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def image_read(urn):
    """Caching image read. We cache to minimize what's stored in memory. We make it immutable to allow sharing"""
    assert urn is not None
    img = cv2.imdecode(np.frombuffer( bytes_read(urn), np.uint8), cv2.IMREAD_ANYCOLOR)
    if img is None:
        raise RuntimeError(urn)
        raise NotImageError("cannot read:"+urn)

    if len(img.shape)==2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)

    img.flags.writeable = False
    return img

@functools.lru_cache(maxsize=MAXSIZE_CACHE)
def image_grayscale(urn):
    """Caching image bw. We cache to minimize what's stored in memory"""
    img = cv2.cvtColor(image_read(urn), cv2.COLOR_BGR2GRAY)
    img.flags.writable = False
    return img

def similarity_for_two(t):
    """Similarity of two CV2 images on a scale of 0 to 1.0.
    This form is used to allow for multiprocessing, since we cannot send . """
    return (t[0],t[1],img_sim(t[2],t[3]))


P_URN = 'urn'
P_CROP = 'crop'

class Frame:
    """Abstraction to hold an image frame.
    If a stage modifies a Frame, it needs to make a copy first."""
    jpeg_quality = DEFAULT_JPEG_QUALITY
    FRAME_VERSION = 1
    def __init__(self, *, img=None, src=None, mime_type=None, _w=None, _h=None, _depth=None, urn=None,history=None,tags=[]):
        """src = the source frame from which this was copied"""
        self.version = self.FRAME_VERSION
        self.urn  = urn       # if read or written to a file, the urn to which it was read or written
        if history is not None:
            self.history = history
        elif src is not None:
            assert isinstance(src,Frame)
            self.history = copy.copy(src.history)
        else:
            self.history  = [[P_URN,urn]]          # new history
        self.tags = tags

        # These are for overriding the properties
        self._w = _w
        self._h = _h
        self._depth = _depth
        self.bytes_ = None
        self._img   = img
        self.mime_type = mime_type

        # Set the timestamp
        if urn is not None:
            try:
                self.mtime = datetime.fromisoformat( os.path.splitext(os.path.basename(urn))[0] )
            except ValueError:
                self.mtime = datetime.fromtimestamp(os.path.getmtime(urn))
        elif img is not None:
            self.mtime = datetime.now()

    def __hash__(self):
        """Objects need to be hashable for certain operations.
        Objects that are equal must have the same hash,
        but objects that have the same hash do not need to be identical.
        frozenset() is used becuase hashes need to be immutable.
        https://stackoverflow.com/questions/1151658/python-hashable-dicts
        """
        return hash( self.__repr__() )

    def __eq__(self, b):
        return self.__dict__ == b.__dict__

    def __lt__(self, b):
        return  self.mtime < b.mtime
    def __repr__(self):
        return f"<Frame urn={self.urn} history={self.history} tags={[tag.tag_type for tag in self.tags]}>"

    @property
    def json(self):
        """JSON representation of the frame (without the image)."""
        return json.dumps({'version':self.version,
                           'urn':self.urn,
                           'history':self.history,
                           'tags': [tag.dict() for tag in self.tags],
                           '_w':self._w,
                           '_h':self._h,
                           '_depth':self._depth,
                           'mime_type':self.mime_type}, default=str)

    @classmethod
    def fromJSON(cls, str):
        kwargs = json.loads(str)
        if kwargs['version']==cls.FRAME_VERSION:
            del kwargs['version']
            kwargs['tags'] = [Tag.fromDict(tagdict) for tagdict in kwargs['tags']]
            return Frame(**kwargs)
        else:
            raise ValueError(f"Cannot load Frame JSON version {kwargs['version']}")


    @property
    def src_urn(self):
        try:
            if self.history[0][0]==P_URN:
                return self.history[0][1]
        except (IndexError,KeyError):
            pass
        return None

    def save(self, urn):
        """Write the image to a file as a JPEG"""
        logging.debug("save urn=%s self=%s",urn,self)
        bamboo_save(urn, self.jpeg_bytes)
        self.history.append([P_URN,urn])
        self.urn = urn


    def copy(self):
        """Returns a copy, but with the original img and tags. Setting a tag makes that copy.
        If you want to draw into the img, use crop() or writable_copy()
        """
        return copy.copy(self)

    def writable_copy(self):
        """Returns a copy into which we can write"""
        c = self.copy()
        c._img = self.img.copy()
        c._img.flags.writable=True
        c.urn_ = None
        return c

    def hash(self):
        """Return a unique hash of the image"""
        return hash_read(self.urn)

    def annotate( self, i, xy, w, h, text, *, textcolor=C.GREEN, boxcolor=C.RED, thickness=2):
        cv2.rectangle(i, xy, (xy[0]+w, xy[1]+h), boxcolor, thickness=thickness)
        cv2.putText(i, text, (xy[0], xy[1] - 5),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, textcolor, thickness=thickness)

    def add_tag(self, tag):
        # Before we add the first tag, copy the tags array so that this frame
        # has its own copy of the array
        self.tags = copy.copy(self.tags)
        self.tags.append(tag)

    def show(self, i=None, title=None, wait=0):
        """show the frame, optionally waiting for keyboard"""
        if title is None:
            title = self.urn
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

    def findall_tags(self, tag_type):
        return [tag for tag in self.tags if tag.tag_type==TAG_FACE]

    def findfirst_tag(self, tag_type):
        for tag in self.tags:
            if tag.tag_type==tag_type:
                return tag
        return None


    @property
    def img(self):
        """return an opencv image object that is not writable."""
        return self._img if self._img is not None else image_read(self.urn)

    @property
    def img_grayscale(self):
        """return an opencv image object in grayscale."""
        return image_read(self.urn)

    @property
    def jpeg_bytes(self):
        """Returns as disk bytes or, if there are none, as a JPEG compressed"""
        logging.debug("self=%s",self)
        if self.urn is not None:
            return bytes_read(self.urn)
        return cv2.imencode('.jpg', self._img, [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality])[1]

    @property
    def shape(self):
        """Returns shape. note: shape[0] = height, shape[1]=width, shape[2]==depth"""
        if self._w is not None and self._h is not None and self._depth is not Nonde:
            return (self._h, self._w, self._depth)
        return tuple(self.img.shape)

    @functools.lru_cache(maxsize=10)
    def similarity(self, i2):
        """Return the simularity score with img"""
        if i2 is None:
            return 0            # not similar at all
        return img_sim(self.img, i2.img)

    def crop(self, *, xy, w, h):
        """Return a new Frame that is the old one cropped. So copy over the provenance. Tags are not copied."""
        cropped_img = np.copy( self.img[xy[1]:xy[1]+h, xy[0]:xy[0]+w])
        history     = copy.copy(self.history)
        history.append([P_CROP, (xy,(w,h))])
        return Frame(img = cropped_img,
                     mime_type = self.mime_type,
                     history=history)

class Tag:
    TAG_VERSION = 1
    def __init__(self, tag_type, text="", **kwargs):
        self.text = text
        self.tag_type = tag_type
        for (k,v) in kwargs.items():
            setattr(self, k, v)

    def __eq__(self, b):
        return self.__dict__ == b.__dict__

    def __getitem__(self, key):
        return self.__dict__.__getitem__(key)

    def __setitem__(self, k, v):
        return self.__dict__.__setitem__(k, v)

    @classmethod
    def fromDict(cls, t):
        assert t['version']==cls.TAG_VERSION
        del t['version']
        return Tag(**t)

    @classmethod
    def fromJSON(cls, str):
        return cls.fromDict(json.loads(str))

    @property
    def json(self):
        return json.dumps({**{'version':self.TAG_VERSION},
                             **self.__dict__}, default=str)

    def __repr__(self):
        return f"<{self.__class__.__name__} {self.tag_type} {self.__dict__.keys()}>"

    def dict(self):
        return {**{'version':self.TAG_VERSION},
                **self.__dict__}

    def has(self,attr):
        return hasattr(self,attr)


class Patch(Tag):
    """A Patch is a special kind of tag that refers to just a specific area of the Frame"""
    def __init__(self, tag_type, **kwargs):
        super().__init__(tag_type, **kwargs)

def FrameTagDict(f,t):
    return {'urn':f.urn, 'history':f.history, 'tag':t}
