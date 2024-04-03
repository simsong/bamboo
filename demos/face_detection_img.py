# https://towardsdatascience.com/face-detection-in-2-minutes-using-opencv-python-90f89d7c0f81

import cv2
import sys
import os.path

BLUE = (255,0,0)
GREEN = (0,255,0)

def cv2_cascade(base):
    thedir = os.path.join(os.path.dirname(cv2.__file__), "data")
    path = os.path.join( thedir, base)
    if not os.path.exists(path) or base is None:
        print("pick on of these:")
        for _ in sorted(os.listdir(thedir)):
            print(_)
        raise FileNotFoundError(base)
    return path

def process(fname):
    # https://docs.opencv.org/3.4/d1/de5/classcv_1_1CascadeClassifier.html
    # https://stackoverflow.com/questions/20801015/recommended-values-for-opencv-detectmultiscale-parameters
    # https://opencv-tutorial.readthedocs.io/en/latest/face/face.html
    frontal_face_cascade = cv2.CascadeClassifier( cv2_cascade('haarcascade_frontalface_default.xml'))

    # Read the input image
    img = cv2.imread(fname)
    assert img is not None

    # Convert into grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    faces = frontal_face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40,40),
                                                  flags=cv2.CASCADE_SCALE_IMAGE)
    # Draw rectangle around the faces
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), BLUE, 2)

    # Display the output
    cv2.imshow('img', img)
    cv2.waitKey()


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Face Finder",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--list",help="list detectors", action='store_true')
    parser.add_argument("file", help='file to face find')
    args = parser.parse_args()
    if args.list:
        cv2_cascade('x')
    process(args.file)
