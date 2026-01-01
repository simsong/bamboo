"""Detect faces
https://docs.aws.amazon.com/rekognition/latest/dg/faces-detect-images.html
https://docs.aws.amazon.com/rekognition/latest/APIReference/API_DetectFaces.html

Amazon Rekognition Image provides the DetectFaces operation that looks
for key facial features such as eyes, nose, and mouth to detect faces
in an input image. Amazon Rekognition Image detects the 100 largest
faces in an image.

You can provide the input image as an image byte array (base64-encoded
image bytes), or specify an Amazon S3 object. In this procedure, you
upload an image (JPEG or PNG) to your S3 bucket and specify the object
key name.

Amazon recommends using an IAM user that has:
  AmazonRekognitionFullAccess
  AmazonS3ReadOnlyAccess

"""

import boto3
import json
import urllib.parse
import base64
import cv2

PROFILE_NAME='default'
DEFAULT_REGION='us-east-2'

# response = client.get_bucket_location( Bucket='string', ExpectedBucketOwner='string' )

def detect_faces(path):
    region = DEFAULT_REGION # # get the actual region?
    image = {}

    o = urllib.parse.urlparse(path)
    if o.scheme=='s3':
        image['S3Object'] = {'Bucket': o.netloc, 'Name': o.path[1:]}
    elif o.scheme=='' or o.scheme=='file':
        with open(path,'rb') as f:
            image['Bytes'] = f.read()
    else:
        raise ValueError('unknown scheme: '+o.scheme)

    session  = boto3.Session(profile_name=PROFILE_NAME, region_name=region)
    client   = session.client('rekognition', region_name=region)
    response = client.detect_faces(Image=image, Attributes=['ALL'])


    faceDetails = response['FaceDetails']
    print(json.dumps(faceDetails, indent=4, sort_keys=True))

    with open("details.json","w") as f:
        f.write(json.dumps(faceDetails,indent=4,sort_keys=True))
    return faceDetails

def annotate(path,faceDetails,outfile):
    im = cv2.imread(path)
    print(im.shape)
    (width,height,depth) = im.shape
    print("height=",height,"width=",width)
    height = len(im[0])
    WHITE  = (255,255,255)
    BLUE  = (255,0,0)
    GREEN  = (0,255,0)
    RED  = (0,0,255)
    thickness = 40
    print("faces:",len(faceDetails))
    for face in faceDetails[0:1]:
        print(face['BoundingBox'])
        top_left = (int(face['BoundingBox']['Left'] * width),
                    int(face['BoundingBox']['Top'] * height))
        face_width = int(face['BoundingBox']['Width']*width)
        face_height = int(face['BoundingBox']['Height']*height)
        bot_right = (top_left[0] + face_width,
                     top_left[1] - face_height)

        print("top_left=",top_left,"face_width=",face_width,"face_height=",face_height)
        cv2.rectangle(im, top_left, bot_right, RED, thickness)
        print()
    cv2.imwrite(outfile, im)
    cv2.imshow("test",im)
    cv2.waitKey(0)
    print("wrote ",outfile)

def annotate2(path, faceDetails, outfile):



if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Demonstrate the detect_faces API.",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("path",help="Specify file or s3:// location of image to analyze")
    args = parser.parse_args()
    faceDetails = detect_faces(args.path)
    #with open("details.json","r") as f:
    #    faceDetails = json.load(f)
    annotate(args.path, faceDetails, "output.jpg")
