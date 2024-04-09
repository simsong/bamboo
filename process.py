"""
process frames that have been ingested.
"""


import cv2
from ingest import Frame
from bamboo.stage import Stage,ShowTags
from bamboo.facedetect_yolo8 import Yolo8FaceDetect
from bamboo.facedetect_cv2 import OpenCVFaceDetector



def run_root(pipeline, root):
    for frame in Frame.FrameStream(root):
        print(frame)
        try:
            pipeline.process(frame)
        except cv2.error as e:
            print(f"Uncaught cv2 error in {frame.path}")
            print(e)


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process an image. Prototype version",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("roots", nargs="*", help='Directories to process. By default, process the config file')
    args = parser.parse_args()

    # Create a simple pipline - run a face recognizer and print the results
    yfd = Yolo8FaceDetect()
    yfd.add_output( ShowTags() )
    #yfd.add_output( ocd := OpenCVFaceDetector())
    #ocd.add_output( st:=ShowTags())

    if args.roots:
        for root in args.roots:
            run_root(yfd, root)
