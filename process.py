"""
process frames that have been ingested.
"""

import os
import os.path

import cv2
from ingest import Frame
from stage import Stage

class OpenCVFaceDetector(Stage):
    """OpenCV Face Detector using Harr cascades."""
    @staticmethod
    def cv2_cascade(name):
        """Return a harr cascade from OpenCV installation."""
        thedir = os.path.join(os.path.dirname(cv2.__file__), "data")
        path = os.path.join( thedir, name)
        if not os.path.exists(path) or name is None:
            raise ValueError("Cascade name '"+name+"' must be one of "+" ".join(list(sorted(os.listdir(thedir)))))
        return path

    frontal_face_cascade = cv2.CascadeClassifier( cv2_cascade('haarcascade_frontalface_default.xml'))
    profile_cascade = cv2.CascadeClassifier( cv2_cascade('haarcascade_profileface.xml'))

    def process(self, frame:Frame):
        front_faces = self.frontal_face_cascade.detectMultiScale(frame.img_grayscale,
                                                                 scaleFactor=1.1,
                                                                 minNeighbors=10,
                                                                 minSize=(40,40),
                                                                 flags=cv2.CASCADE_SCALE_IMAGE)

        profile_faces = self.profile_cascade.detectMultiScale(frame.img_grayscale, scaleFactor=1.1, minNeighbors=10,
                                                              minSize=(40,40),
                                                              flags=cv2.CASCADE_SCALE_IMAGE)
        if len(front_faces):
            print(frame.path,"front faces:",front_faces)
        if len(profile_faces):
            print(frame.path,"profile faces:",profile_faces)

    def done(self):
        """This is terminal."""

def run_root(pipeline, root):
    for frame in Frame.FrameStream(root):
        print(frame)
        pipeline.process(frame)

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Process an image. Prototype version",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("roots", nargs="*", help='Directories to process. By default, process the config file')
    args = parser.parse_args()

    # Create a simple pipline - run a face recognizer and print the results
    pipeline = OpenCVFaceDetector()

    if args.roots:
        for root in args.roots:
            run_root(pipeline, root)
