#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos, write them to a directory with metadata, and produce face clusters.
"""

import os
import shelve
from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import WriteFramesToDirectory,SaveTagsToShelf
from bamboo.face_deepface import DeepFaceTag
from bamboo.face import ExtractFacesToFrames
from bamboo.source import FrameStream
from bamboo.frame import TAG_FACE


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("root", help='Directory to process.')
    parser.add_argument("--db", help="Output databaae.", nargs=1, default='faces')
    parser.add_argument("--dump",help="dump the database before clustering",action='store_true')
    args = parser.parse_args()

    p = SingleThreadedPipeline()

    def tagfilter(t):
        print("Filter type=",t.tag_type)
        return t.tag_type == TAG_FACE

    dbpath  = args.db
    p.addLinearPipeline([ DeepFaceTag(face_detector='yolov8'),
                          ExtractFacesToFrames(scale=1.3),
                          SaveTagsToShelf(tagfilter = tagfilter, path=dbpath)])

    p.process_list( FrameStream( args.root ) )

    with shelve.open(args.db, writeback=False) as db:
        if args.dump:
            for (k,v) in db.items():
                print("k=",k,"v=",v)
