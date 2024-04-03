from ingest import Frame
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
