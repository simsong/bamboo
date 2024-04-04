"""
Stage for facedetect using cv2
"""

import os
from frame import Frame,Tag,FACE
from stage import Stage
import cv2

class OpenCVFaceDetector(Stage):
    """OpenCV Face Detector using Harr cascades."""
    @staticmethod
    def cv2_cascade(name):
        """Return a harr cascade from OpenCV installation."""
        thedir = os.path.join(os.path.dirname(cv2.__file__), "data")
        path = os.path.join( thedir, name)
        if not os.path.exists(path) or name is None:
            raise ValueError("Cascade name '"+name+
                             "' must be one of "+" ".join(list(sorted(os.listdir(thedir)))))
        return path

    frontal_face_cascade = cv2.CascadeClassifier( cv2_cascade('haarcascade_frontalface_default.xml'))
    profile_cascade = cv2.CascadeClassifier( cv2_cascade('haarcascade_profileface.xml'))

    def process(self, f:Frame):
        front_faces = self.frontal_face_cascade.detectMultiScale(f.img_grayscale,
                                                                 scaleFactor=1.1,
                                                                 minNeighbors=10,
                                                                 minSize=(40,40),
                                                                 flags=cv2.CASCADE_SCALE_IMAGE)
        for (x,y,w,h) in front_faces:
            f.add_tag(Tag( FACE,
                               pt1 = (x,y),
                               pt2 = (x+w,y+h),
                               text = "cv2 frontal_face"))

        profile_faces = self.profile_cascade.detectMultiScale(
            f.img_grayscale, scaleFactor=1.1, minNeighbors=10,
            minSize=(40,40),
            flags=cv2.CASCADE_SCALE_IMAGE)

        for (x,y,w,h) in profile_faces:
            f.add_tag(Tag(FACE, pt1=(x,y),pt2=(x+w,y+h), text="cv2 profile_face"))

        self.output(f)
