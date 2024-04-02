#!/usr/bin/env python3
"""
Find new photos test program.
Finds them and archives photos significantly different from previous ones with a window.os +/-

"""

import os
import os.path
import subprocess
import json
from datetime import datetime
import queue
from multiprocessing import Pool
import functools
import uuid
import urllib.parse
import shutil
import mimetypes
from os.path import basename,dirname,join

import boto3
import yaml
import cv2
from lib.ctools.timer import Timer
from similarity.sim1 import img_sim
from constants import C

THRESHOLD=0.92

def file_generator(root):
    """Generator for a series of images from a root"""
    for (dirpath, _, filenames) in os.walk(root):
        for fname in sorted(filenames):
            if os.path.splitext(fname)[1].lower() in C.IMAGE_EXTENSIONS:
                yield os.path.join(dirpath, fname)

def yaml_items(item):
    if not isinstance(item,list):
        item = [item]
    for i in item:
        yield i

def filename_template(*,camera,path=None,mtime=None):
    """Returns the path"""
    if path and not mtime:
        mtime = datetime.fromtimestamp( os.stat(path).st_mtime )

    fmt =  f"{camera}/{mtime.year:04}-{mtime.month:02}/{mtime.year:04}{mtime.month:02}{mtime.day:02}-{mtime.hour:02}{mtime.minute}{mtime.second:02}"
    if mtime.microsecond>0:
        fmt += f"{mtime.microsecond:06}"
    fmt += os.path.splitext(path)[1]
    return fmt

def similarity_for_two(t):
    """Similarity of two CV2 images on a scale of 0 to 1.0.
    This form is used to allow for multiprocessing, since we cannot send . """
    return (t[0],t[1],img_sim(t[2],t[3]).score)


def s3_client():
    return boto3.session.Session().client( 's3' )
def s3_resource():
    return boto3.Session().resource( 's3' )

# We use the cache to avoid making the same directory twice
@functools.lru_cache(maxsize=128)
def mkdirs(path):
    print("mkdirs",path)
    os.makedirs(path, exist_ok = True)

@functools.lru_cache(maxsize=128)
def image_read(path):
    """Caching image read"""
    return cv2.imread(path)

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
        """return an opencv image object"""
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

class IngestCamera():
    """Master class for camera ingester"""
    def __init__(self, *, camera, config, show=False):
        self.camera = camera
        self.root   = config['archive']['root']
        self.config = config['cameras'][camera]
        self.show   = show
        self.sim_threshold = C.DEFAULT_SIM_THRESHOLD
        self.total_kept = 0

    def notice(self, msg, endl=False):
        """Display a message"""
        print("\r" + msg + "\033[K", end="") # print and clear to end of line
        if endl:
            print("")           # next line

    def ingest_save_image(self, i):
        if self.show:
            cv2.imshow("changes",i.img)
            cv2.waitKey(1) # waits for 1 milisecond and makes sure window is displayed

        # Loop through all possible roots
        for r in yaml_items(self.root):
            new_name = r + '/' + filename_template(camera=self.camera, path=i.path)
            self.total_kept += 1
            self.notice(f"{i.path} → {new_name}", endl=True)
            o = urllib.parse.urlparse(new_name)
            print(o)
            if o.scheme == 'file':
                mkdirs( dirname(o.path))
                shutil.copyfile( i.path, o.path )
            elif o.scheme == 's3':
                mimetype, _ = mimetypes.guess_type(i.path)
                s3_resource().Bucket(o.netloc).upload_file(Filename=i.path, Key=o.path[1:],
                                                         ExtraArgs={'ContentType': mimetype})
            else:
                raise ValueError("Unknown scheme: "+o.scheme)


    def ingest_from_root(self):
        """Ingest reads from the camera stream and generates and runs a callback for each frame that has changed a bit.
        The callback has access to the previous N frames as well, and for each it notes if the frame was saved or not.

        We use an array because it's okay to hold a million objects (a day of video?),
        as we are not going to hold the whole frame in memory
        This could be replaced with a priority queue or a double-ended queue.
        """
        ary = FrameArray()
        for f in Frame.FrameStream(self.config['source']):
            ary.add(f)

        ary.set_prev_pointers()

        # Get the first and retain
        ref = ary.first()
        self.ingest_save_image(ref)
        prev = ref
        skipped = 0

        # This could be a pipeline or parallelized? Would be nice to know fps
        with Timer(f"Ingesting {len(ary)} images") as t:
            # Now iterate through the list.
            # We will use the cached similarity scores when they are available
            for i in ary:
                self.notice(i.path)
                try:
                    score = i.similarity(ref)
                except cv2.error as e:
                    print(f"Error {e} with {i.path}")
                    continue
                if score > self.sim_threshold:
                    skipped += 1
                    i.tags['skipped'] = skipped
                else:
                    self.ingest_save_image(i)
                    # self.ingest_save_image(prev) # also save the previous one
                    ref = i
                prev = i
            print("fps: ",len(ary) / t.elapsed(),end=' ')

        print(f"Total kept: {self.total_kept} / {len(ary)} = {self.total_kept * 100//len(ary)}%")


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Ingest and archive a directory, optionally do stuff",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("roots", nargs="*", help='Directories to process. By default, process the config file')
    parser.add_argument("--config", help='Yaml file to process', default='config.yml')
    parser.add_argument("--show", help="show those we keep", action='store_true')
    args = parser.parse_args()

    if args.roots:
        for root in args.roots:
            print("processing",root)
            ing = IngestCamera( camera="camera", config=root, show=args.show)

    with open(args.config) as f:
        config = yaml.safe_load(f)
        print(json.dumps(config,indent=4,default=str))
        for camera in config['cameras']:
            ic = IngestCamera( camera=camera, config=config, show=args.show )
            ic.ingest_from_root()
