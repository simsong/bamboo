#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos and write them to a directory.
We show them for fun!
"""

import os
from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import ShowTags, SaveFramesToDirectory
from bamboo.face_yolo8 import Yolo8FaceTag
from bamboo.face import ExtractFacesToFrames
from bamboo.source import FrameStream

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("root", help='Directory to process.')
    parser.add_argument("outdir", help="Output directory.")
    args = parser.parse_args()

    os.makedirs(args.outdir, exist_ok = True)
    p = SingleThreadedPipeline()
    p.addLinearPipeline([ Yolo8FaceTag(),
                          ShowTags(wait=200),
                          ExtractFacesToFrames(scale=1.3),
                          SaveFramesToDirectory(args.outdir, template="{counter:08}.jpg") ])

    p.process_list( FrameStream( args.root ) )
