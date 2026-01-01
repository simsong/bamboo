# https://cmusatyalab.github.io/openface/
# https://towardsdatascience.com/face-detection-in-2-minutes-using-opencv-python-90f89d7c0f81
# https://www.bogotobogo.com/python/OpenCV_Python/python_opencv3_Image_Object_Detection_Face_Detection_Haar_Cascade_Classifiers.php#google_vignette

import os
import cv2

def cv2_cascade(base):
    path = os.path.join( cv2.data.haarcascades, base)
    if not os.path.exists(path):
        print("pick on of these:")
        for _ in os.listdir(thedir):
            print(_)
        raise FileNotFoundError(base)
    return path



# Load the cascade
face_cascade = cv2.CascadeClassifier( cv2_cascade('haarcascade_frontalface_default.xml'))
profile_cascade = cv2.CascadeClassifier( cv2_cascade('haarcascade_profileface.xml'))

# To capture video from webcam.
cap = cv2.VideoCapture(0)
# To use a video file as input
# cap = cv2.VideoCapture('filename.mp4')

print("cap:",cap)

BLUE=(255,0,0)
GREEN=(0,255,0)

while True:
    # Read the frame
    _, img = cap.read()
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Detect the faces
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    # faces = []
    # Draw the rectangle around each face
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), BLUE, 2)

    faces = profile_cascade.detectMultiScale(gray, 1.1, 4)
    # faces = []
    # Draw the rectangle around each face
    for (x, y, w, h) in faces:
        cv2.rectangle(img, (x, y), (x+w, y+h), GREEN, 2)


    # Display
    cv2.imshow('img', img)
    # Stop if escape key is pressed
    k = cv2.waitKey(30) & 0xff
    if k==27 or k==ord('q'):
        break
# Release the VideoCapture object
cap.release()
