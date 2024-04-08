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

"""

from deepface import DeepFace

import cv2
import numpy as np
import math
import argparse

from bamboo.stage import Stage
from bamboo.frame import Frame,Tag,FACE

CONF_THRESHOLD = 0.45
NMS_THRESHOLD = 0.50

class Yolo8FaceDetect(Stage):
    # Initialize YOLOv8_face object detector
    face_detector = YOLOv8_face("etc/yolov8/yolov8n-face.onnx", conf_thres=CONF_THRESHOLD, iou_thres=NMS_THRESHOLD)
    fqa = FaceQualityAssessment("etc/yolov8/face-quality-assessment.onnx")

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
