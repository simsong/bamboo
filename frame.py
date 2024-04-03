"""
Frame holds individual frames and logic for working on individual frames with OpenCV.
"""
import os
import functools
from datetime import datetime

import cv2

from constants import C
from similarity.sim1 import img_sim

@functools.lru_cache(maxsize=128)
def image_read(path):
    """Caching image read. We cache to minimize what's stored in memory"""
    return cv2.imread(path)

@functools.lru_cache(maxsize=128)
def image_grayscale(path):
    """Caching image bw. We cache to minimize what's stored in memory"""
    return cv2.cvtColor(image_read(path), cv2.COLOR_BGR2GRAY)

def similarity_for_two(t):
    """Similarity of two CV2 images on a scale of 0 to 1.0.
    This form is used to allow for multiprocessing, since we cannot send . """
    return (t[0],t[1],img_sim(t[2],t[3]).score)


class Frame():
    """Abstraction to hold an image frame."""
    def __init__(self, *, path=None):
        self.path = path
        self.tags = {}
        self.prev = None        # previous image
        # Read the timestamp from the filename if present, otherwise gram from mtime
        try:
            self.mtime = datetime.fromisoformat( os.path.splitext(os.path.basename(path))[0] )
        except ValueError:
            self.mtime = datetime.fromtimestamp(os.path.getmtime(path))

    def __lt__(self, b):
        return  self.mtime < b.mtime
    def __repr__(self):
        return f"<Frame {os.path.basename(self.path)}>"

    def annotate( pt1, pt2, text, *, color=C.GREEN, thickness=2):
        if self.copy is None:
            self.copy = self.img.copy()

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
