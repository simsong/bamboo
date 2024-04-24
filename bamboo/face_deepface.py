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

from .stage import Stage,ShowTags,ShowFrames
from .frame import Frame,Tag,TAG_FACE
from .pipeline import SingleThreadedPipeline
from .face import ExtractFacesToFrames
from .source import FrameStream
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

def deepface_normalization_names():
    ret = set()
    pat = re.compile('.*normalization == "([a-zA-Z0-9]+)"')
    with open(join(dirname(deepface.modules.__file__),"preprocessing.py")) as f:
        for line in f:
            m = pat.search(line)
            if m:
                ret.add(m.group(1))
    return ret

def any_nan(vect):
    for v in vect:
        if math.isnan(v):
            return True
    return False

class DeepFaceTagFaces(Stage):
    """
    :param: embedding - also produce embeddings.
    :param: analyze - also produce face analysis.
    :param: model_name - which model to use.
    :param: face_detector - which face detector DeepFace should use.
    :param: normalization - how to normalize faces
    :param: scale - enlarge boxes around faces.
    """

    def __init__(self,
                 embeddings=True,
                 analyze=False,
                 model_name = 'VGG-Face',
                 face_detector='opencv',
                 normalization='base',
                 scale=1.0):
        super().__init__()
        assert model_name in deepface_model_names()
        assert face_detector in deepface_detector_names()
        assert normalization in deepface_normalization_names()

        if embeddings and analyze:
            raise ValueError("Currently DeepFaceTagFaces can only generate embeddings or attributes.")

        if embeddings:
            def eng(*args,**kwargs):
                return deepface.DeepFace.represent(*args,model_name=model_name,
                                                   normalization = self.normalization,
                                                   **kwargs)
            self.engine = eng
        elif analyze:
            self.engine = deepface.DeepFace.analyze
        else:
            raise ValueError("Please specify embeddings=True or analyze=True")

        self.face_detector = face_detector
        self.normalization = normalization
        self.scale       = scale

    def process(self, f:Frame):
        # Detect Objects
        f = f.copy()            # we will be adding tags
        expand_percentage = (self.scale - 1.0) * 100
        try:
            found_faces = self.engine(f.img,
                                      enforce_detection = False,
                                      detector_backend = self.face_detector,
                                      align = True,
                                      expand_percentage = expand_percentage)
        except ValueError as e:
                print(f"{f} DeepFace error {str(e)[0:100]}")
                return

        for found in found_faces:
            # deepface sometimes creates embeddings with nan's.
            # If we find them, remove them
            if ('embedding' in found) and any_nan(found['embedding']):
                del found['embedding']

            kwargs = {}
            if 'facial_area' in found:
                facial_area = found['facial_area']
                kwargs = {'xy':(facial_area['x'],facial_area['y']),
                          'w':facial_area['w'],
                          'h':facial_area['h']}

            if self.engine == deepface.DeepFace.analyze:
                print("found=",found)

            f.add_tag(Tag(TAG_FACE, **{**found,**kwargs} ))
        self.output(f)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('image', type=str, help="image path")
    args = parser.parse_args()

    p = SingleThreadedPipeline()
    p.addLinearPipeline([ DeepFaceTagFaces(detector_backend='yolov8'),
                          ShowTags(wait=0),
                          ExtractFacesToFrames(scale=1.3),
                          ShowFrames(wait=0) ])
    p.process_stream(  FrameStream(root=args.image))
