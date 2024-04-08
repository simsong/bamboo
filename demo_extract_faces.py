#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos and write them to a directory.
"""

import os

from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import ShowTags, WriteToDirectory
from bamboo.face_yolo8 import Yolo8FaceDetect
from bamboo.face import ExtractFacesToFrames
from bamboo.frame import Frame
from bamboo.source import FrameStream

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("root", help='Directory to process.')
    parser.add_argument("outdir", help="Output directory.")
    args = parser.parse_args()

    p = SingleThreadedPipeline()
    p.addLinearPipeline([ Yolo8FaceDetect(),
                          ShowTags(wait=500),
                          ExtractFacesToFrames(scale=1.3),
                          WriteToDirectory(args.outdir, template="{counter:08}.jpg") ])

    p.process_list( FrameStream( args.root ) )
