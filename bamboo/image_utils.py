"""
 https://pyimagesearch.com/2017/06/19/image-difference-with-opencv-and-python/

 https://scikit-image.org/docs/stable/api/skimage.metrics.html#skimage.metrics.structural_similarity

pip install --upgrade scikit-image
pip install --upgrade imutils
"""

from skimage.metrics import structural_similarity as compare_ssim
import argparse
import imutils
import cv2

def img_sim(imageA, imageB):
    # convert the images to grayscale
    grayA = cv2.cvtColor(imageA, cv2.COLOR_BGR2GRAY)
    grayB = cv2.cvtColor(imageB, cv2.COLOR_BGR2GRAY)

    # compute the Structural Similarity Index (SSIM) between the two
    # images, ensuring that the difference image is returned
    if grayA.shape == grayB.shape:
        (score, diff) = compare_ssim(grayA, grayB, full=True)
        return score
    else:
        return 0



def show(imageA, imageB, diff):

    # threshold the difference image, followed by finding contours to
    # obtain the regions of the two input images that differ
    thresh = cv2.threshold(diff, 0, 255,
            cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU)[1]
    cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE)
    cnts = imutils.grab_contours(cnts)

    # loop over the contours
    for c in cnts:
            # compute the bounding box of the contour and then draw the
            # bounding box on both input images to represent where the two
            # images differ
            (x, y, w, h) = cv2.boundingRect(c)
            cv2.rectangle(imageA, (x, y), (x + w, y + h), (0, 0, 255), 2)
            cv2.rectangle(imageB, (x, y), (x + w, y + h), (0, 0, 255), 2)
    # show the output images
    cv2.imshow(args.first, imageA)
    cv2.imshow(args.second, imageB)
    cv2.imshow("Diff", diff)
    cv2.imshow("Thresh", thresh)
    cv2.waitKey(0)


if __name__=="__main__":
    # construct the argument parse and parse the arguments
    ap = argparse.ArgumentParser()
    ap.add_argument("first", help="first input image")
    ap.add_argument("second", help="second")
    args = ap.parse_args()

    # load the two input images
    imageA = cv2.imread(args.first)
    imageB = cv2.imread(args.second)

    (score,diff) = img_sim(imageA, imageB)
    show(imageA, imageB, diff)
