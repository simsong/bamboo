"""
"Deepface is a lightweight face recognition and facial attribute analysis (age, gender, emotion and race) framework for python. It is a hybrid face recognition framework wrapping state-of-the-art models: VGG-Face, Google FaceNet, OpenFace, Facebook DeepFace, DeepID, ArcFace, Dlib, SFace and GhostFaceNet."
https://github.com/serengil/deepface

This module wraps deepface with the Bamboo API and makes it easy to use Deepface to extract vectors.
Cheats:

DeepFace.verify(img1_path=path, img2_path=path2, [model_name = ])
           - Just verify if they are the same person.. No normalization required.. Optionally specify model_name
DeepFace.represent(img_path = path) - Returns the embeddings as en embedding vector and a bounding box.
DeepFace.analyze(img_path = path, actions = ["age", "gender", "emotion", "race"] - Returns a dictionary of analysis
DeepFace.find(img_path=path, db_path="faces", model_name, enforce_detection=False)[0] - Searches directory "faces" for face closest to path

Note: paths can all be str or np.ndarray in BGR format, or base64 encoded image. "If the source image contains multiple faces, the result will include information for each detected face."

Note: It may be necessary to download:
https://github.com/serengil/deepface_models/releases/download/v1.0/vgg_face_weights.h5

"""

from deepface import DeepFace

import cv2
import numpy as np
import math
import argparse
import re
from os.path import join, abspath, basename, dirname


from .stage import Stage
from .frame import Frame,Tag,FACE

import deepface.modules
import deepface.detectors

# Surprisingly, the list of models is not available in DeepFace; we need to read it from the source code. Ick

def deepface_model_names():
    ret = set()
    pat = re.compile('.*"([-a-zA-Z0-9]+)": .*Client,')
    with open(join(dirname(deepface.modules.__file__),"modeling.py")) as f:
        for line in f:
            m = pat.search(line)
            if m:
                ret.add(m.group(1))
    return ret

def deepface_detector_names():
    ret = set()
    pat = re.compile('.*"([-a-zA-Z0-9]+)": .*Client,')
    with open(join(dirname(deepface.detectors.__file__),"DetectorWrapper.py")) as f:
        for line in f:
            m = pat.search(line)
            if m:
                ret.add(m.group(1))
    return ret





class DeepFaceTag(Stage):
    def __init__(self, embeddings=True, attributes=True, detector_backend='opencv'):
        self.embeddings = embeddings
        self.attributes = attributes


    def process(self, f:Frame):
        # Detect Objects
        f = f.copy()            # we will be adding tags
        boxes, scores, classids, kpts = self.face_detector.detect(f.img)
        for i, box in enumerate(boxes):
            x, y, w, h = box.astype(int)
            crop_img = f.img[y:y + h, x:x + w]  # crop - can also be done after facial alignment
            fqa_probs = self.fqa.detect(crop_img)    # get the face quality
            fqa_prob_mean = round(np.mean(fqa_probs), 2)

            f.add_tag(Tag(FACE, pt1=(x,y), pt2=(x+w,y+h), fqa = fqa_prob_mean,
                          text=f"fqa_score {fqa_prob_mean:4.2f}"))
        self.output(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=str, help="image path")
    parser.add_argument('--confThreshold', default=CONF_THRESHOLD, type=float, help='class confidence')
    parser.add_argument('--nmsThreshold', default=NMS_THRESHOLD, type=float, help='nms iou thresh')
    args = parser.parse_args()

    p = SingleThreadedPipeline()
    p.addLinearPipeline([ Yolo8FaceDetect(), ShowTags(wait=0), ExtractFaces(scale=1.3), ShowFrames(wait=0) ])
    f = Frame(path=args.image)
    p.process(f)
    print(f.tags)
