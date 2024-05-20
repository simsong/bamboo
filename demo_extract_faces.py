#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos and write them to a directory.
We show them for fun!
"""

import os
from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import ShowTags, SaveFramesToDirectory, ShowFrames
from bamboo.face_yolo8 import Yolo8FaceTag
from bamboo.face import ExtractFacesToFrames
from bamboo.source import FrameStream,DissimilarFrameStream

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("root", help='Directory to process.')
    parser.add_argument("outdir", help="Output directory.")
    parser.add_argument("--verbose", help="Show each filename as processed and each face as found", action='store_true')
    args = parser.parse_args()

    stages = []
    if args.verbose:
        stages += [ ShowFrames(wait=10, title='source') ]

    stages += [ Yolo8FaceTag(),
               ShowTags(wait=200),
               ExtractFacesToFrames(scale=1.3, verbose=args.verbose),
               SaveFramesToDirectory(args.outdir, template="{counter:08}.jpg") ]

    os.makedirs(args.outdir, exist_ok = True)
    with SingleThreadedPipeline() as p:
        p.addLinearPipeline(stages)
        p.process_list( DissimilarFrameStream( args.root) )
