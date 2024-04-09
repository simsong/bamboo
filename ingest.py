#!/usr/bin/env python3
"""
Find new photos test program.
Finds them and archives photos significantly different from previous ones with a window.os +/-

"""

import os
import os.path
import json
from datetime import datetime
import functools
import urllib.parse
import shutil
import mimetypes
from os.path import dirname

import boto3
import yaml
import cv2
from lib.ctools.timer import Timer

from  bamboo.frame import Tag

# We use the cache to avoid making the same directory twice
@functools.lru_cache(maxsize=128)
def mkdirs(path):
    print("mkdirs",path)
    os.makedirs(path, exist_ok = True)

def file_generator(root):
    """Generator for a series of images from a root"""
    for (dirpath, _, filenames) in os.walk(root):
        for fname in sorted(filenames):
            if os.path.splitext(fname)[1].lower() in C.IMAGE_EXTENSIONS:
                yield os.path.join(dirpath, fname)

def yaml_items(item):
    if not isinstance(item,list):
        item = [item]
    yield from item

def filename_template(*,camera,path=None,mtime=None):
    """Returns the path"""
    if path and not mtime:
        mtime = datetime.fromtimestamp( os.stat(path).st_mtime )

    fmt =  f"{camera}/{mtime.year:04}-{mtime.month:02}/{mtime.year:04}{mtime.month:02}{mtime.day:02}-{mtime.hour:02}{mtime.minute:02}{mtime.second:02}"
    if mtime.microsecond>0:
        fmt += f"{mtime.microsecond:06}"
    fmt += os.path.splitext(path)[1]
    return fmt


def s3_client():
    return boto3.session.Session().client( 's3' )
def s3_resource():
    return boto3.Session().resource( 's3' )

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


class IngestCamera():
    """Master class for camera ingester"""
    def __init__(self, *, camera, config, show=False):
        self.camera = camera
        self.root   = config['archive']['root']
        self.config = config['cameras'][camera]
        self.show   = show
        self.sim_threshold = self.config['threshold']
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

        # Get the first and retain
        ref = ary.first()
        self.ingest_save_image(ref)
        skipped = 0

        # This could be a pipeline or parallelized? Would be nice to know fps
        with Timer(f"Ingesting {len(ary)} images") as t:
            # Now iterate through the list.
            # We will use the cached similarity scores when they are available
            for i in ary:
                self.notice(i.path)
                try:
                    score = i.similarity(ref)
                except cv2.error as e: # pylint: disable=catching-non-exception
                    print(f"Error {e} with {i.path}")
                    continue
                if score > self.sim_threshold:
                    skipped += 1
                    i.add_tag(Tag("skipped"))
                else:
                    self.ingest_save_image(i)
                    ref = i
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
