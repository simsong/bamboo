import sys
import tempfile
import os
import logging
import json

from os.path import dirname,basename,join,abspath
from subprocess import call

sys.path.append( dirname(dirname(abspath(__file__))))

DATA_DIR = join(dirname(dirname(abspath(__file__))),"data")
DEMO_TAG = json.loads('{"version": 1, "text": "", "tag_type": "face", "emotion": {"angry": 9.52778275937995e-07, "disgust": 7.882377837815784e-10, "fear": 2.5058534302413856e-05, "happy": 99.98201728081497, "sad": 0.001632746703755969, "surprise": 3.7605314375977046e-08, "neutral": 0.016322338579446694}, "dominant_emotion": "happy", "region": {"x": 8, "y": 3, "w": 49, "h": 65, "left_eye": [18, 29], "right_eye": [42, 29]}, "face_confidence": 0.82, "age": 42, "gender": {"Woman": 0.12094306293874979, "Man": 99.87905621528625}, "dominant_gender": "Man", "race": {"asian": 0.0058471058160722775, "indian": 0.00425640850344646, "black": 9.962893676987368e-05, "white": 98.84788407708596, "middle eastern": 0.37026547603869725, "latino hispanic": 0.7716490898550642}, "dominant_race": "white"}')

DEMO_TAG_CAPTION="age: 42<br/>emotion: happy<br/>gender: Man<br/>race: white<br/>"

import demo_cluster_faces

def test_tag_parser():
    assert demo_cluster_faces.caption_from_tag(DEMO_TAG) == DEMO_TAG_CAPTION

def test_cluster_faces():
    # We don't clea up the cluster so that you can view it!
    with tempfile.TemporaryDirectory(delete=False) as td:
        os.makedirs( facedir := join(td,'facedir'))
        os.makedirs( tagdir  := join(td,'tagdir'))

    demo_cluster_faces.cluster_faces(rootdir = DATA_DIR, facedir=facedir, tagdir=tagdir, show=False)
    print(td)
    call(['find',td,'-ls'])
