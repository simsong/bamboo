import os
import cv2

from pipeline.libs.face_detector import FaceDetector
import tests.config as config


class TestFaceDetector:
    def test_face_detector(self):
        prototxt = os.path.join(config.MODELS_FACE_DETECTOR_DIR, "deploy.prototxt.txt")
        model = os.path.join(config.MODELS_FACE_DETECTOR_DIR, "res10_300x300_ssd_iter_140000.caffemodel")
        detector = FaceDetector(prototxt, model)

        test_image = cv2.imread(os.path.join(config.ASSETS_IMAGES_DIR, "friends", "friends_01.jpg"))
        faces = detector.detect([test_image])

        assert len(faces) == 1
        assert len(faces[0])  # Should recognize some faces from friends_01.jpg