#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos, write them to a directory with metadata, and produce face clusters.
"""

import os
import shelve
from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import WriteToDirectory,SaveTagsToShelf
from bamboo.face_deepface import DeepFaceTag
from bamboo.face import ExtractFacesToFrames
from bamboo.source import FrameStream
from bamboo.frame import TAG_FACE


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("root", help='Directory to process.')
    parser.add_argument("db", help="Output databsae.")
    parser.add_argument("--dump",help="just dump the database",action='store_true')
    args = parser.parse_args()

    p = SingleThreadedPipeline()

    def tagfilter(t):
        print("Filter type=",t.tag_type)
        return t.tag_type == TAG_FACE

    p.addLinearPipeline([ DeepFaceTag(face_detector='yolov8'),
                          ExtractFacesToFrames(scale=1.3),
                          SaveTagsToShelf(tagfilter = tagfilter, path=args.db)])

    if not args.dump:
        p.process_list( FrameStream( args.root ) )
    with shelve.open(args.db, writeback=False) as db:
        for (k,v) in db.items():
            print("k=",k,"v=",v)
