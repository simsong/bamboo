import sys
from os.path import dirname,basename,join,abspath

sys.path.append( dirname(dirname(dirname(abspath(__file__)))))

import bamboo.face_deepface as face_deepface

def test_finders():
    model_names = face_deepface.deepface_model_names()
    assert 'Dlib' in model_names
    assert len(model_names)>=10

    detector_names = face_deepface.deepface_detector_names()
    assert 'dlib' in detector_names
    assert len(detector_names)>=7

    normalization_names = face_deepface.deepface_normalization_names()
    assert 'Facenet2018' in normalization_names
    assert len(normalization_names)>=7
