"""
Stage for face detection using AWS rekognition.
Because rekognition is expensive, results are cached (by some unique identifier) in a local database.
"""

import os
import sys
from os.path import join
import shelve
import json
import copy

from filelock import FileLock

import boto3

from .stage import Stage,ShowTags,ShowFrames
from .face import ExtractFacesToFrames
from .frame import Frame,Tag,TAG_FACE
from .pipeline import SingleThreadedPipeline
from .source import FrameStream

ARCHIVE_PATH = join(os.environ["HOME"],'.rekognition-cache')
ARCHIVE_LOCK = ARCHIVE_PATH + ".lock"
DEFAULT_PROFILE = 'default'
DEFAULT_REGION = 'us-east-2'

def save_info(f, info):
    with FileLock(ARCHIVE_LOCK) as lock:
        with shelve.open(ARCHIVE_PATH,writeback=True) as db:
            db[f.hash()] = info

def get_info(f):
    # Return info or raise KeyError
    with FileLock(ARCHIVE_LOCK) as lock:
        with shelve.open(ARCHIVE_PATH,writeback=True) as db:
            return db[f.hash()]

class RekognitionFaceDetect(Stage):
    region_name=DEFAULT_REGION
    profile_name=DEFAULT_PROFILE

    def process(self, f:Frame):
        # we will be adding tags, so make a copy of this frame.
        try:
            faceDetails = get_info(f)
        except KeyError:
            session = boto3.Session(profile_name=self.profile_name, region_name=self.region_name)
            client = session.client('rekognition', region_name=self.region_name)
            bytes = f.bytes
            response = client.detect_faces(Image={'Bytes':f.bytes}, Attributes=['ALL'])
            faceDetails = response['FaceDetails']
            save_info(f, faceDetails)

        for (ct,fd) in enumerate(faceDetails):
            if ct==0:
                f = f.copy()
            top_left = (int(fd['BoundingBox']['Left'] * f.width),
                        int(fd['BoundingBox']['Top'] * f.height))
            w  = int(fd['BoundingBox']['Width']*f.width)
            h = int(fd['BoundingBox']['Height']*f.height)

            f.add_tag( Patch( TAG_FACE,
                            xy = top_left,
                            w=w, h=h,
                            text = "aws face",
                            faceDetails = fd))
        self.output(f)




if __name__ == '__main__':
    """A little test program"""
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=str, help="image path")
    args = parser.parse_args()

    # Create a 4-step pipeline to recognize the face, show the tags, extract the faces, and show each
    p = SingleThreadedPipeline()
    p.addLinearPipeline([ RekognitionFaceDetect(),
                          ShowTags(wait=0),
                          ExtractFacesToFrames(scale=1.3),
                          ShowFrames(wait=0) ])
    p.process_stream(  FrameStream(root=args.image))
