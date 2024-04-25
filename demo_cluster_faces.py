#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos, write them to a directory with metadata, and produce face clusters.
"""

import os
import math
import logging
import subprocess

from collections import defaultdict

from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
import numpy as np

from lib.ctools import clogging
from lib.ctools import timer

from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import Stage,SaveFramesToDirectory,ShowTags,Connect,WriteFrameObjectsToDirectory,FilterFrames,WriteFramesToHTMLGallery,WriteFramesToHTMLGallery_tag
from bamboo.face_deepface import DeepFaceTagFaces
from bamboo.face import ExtractFacesToFrames
from bamboo.source import DissimilarFrameStream,TagsFromDirectory,FrameStream,SourceOptions
from bamboo.frame import Frame,Tag,TAG_FACE


def frame_has_face_tag_with_embedding(f):
    for tag in f.tags:
        if (tag.tag_type==TAG_FACE) and tag.has('embedding'):
            return True
    return False


def caption_from_tag(tag):
    caption = ''
    try:
        caption += f'age: {tag["age"]}<br/>'
    except KeyError:
        pass
    for k,v in tag.dict().items():
        if k.startswith("dominant_"):
            caption += f'{k[9:]}: {v}<br/>'
    return caption

class CaptionFaces(Stage):
    def process(self, f:Frame):
        caption = ''
        for tag in f.findall_tags(TAG_FACE):
            caption += caption_from_tag(tag)

        if caption:
            f.add_tag( Tag(WriteFramesToHTMLGallery_tag, caption=caption))
        super().process(f)      # and continue processing

def cluster_faces(*, rootdir, facedir, tagdir, show, limit=None):
    os.makedirs(tagdir, exist_ok=True)
    os.makedirs(facedir, exist_ok=True)

    so = SourceOptions(limit=limit)
    print("cf. so.limit=",so.limit)

    # If a rootdir was specified, analyze the images and write all of the frames that have
    # and embedding
    if rootdir:
        with SingleThreadedPipeline() as p:
            p.addLinearPipeline([
                # For each frame, tag all of the faces:
                dt:= DeepFaceTagFaces(face_detector='yolov8', embeddings=True),

                # For each tag, create a new frame and send it down the pipeline:
                ExtractFacesToFrames(scale=1.3),

                # Filter for frames that have a face tag with an embedding
                FilterFrames(framefilter=frame_has_face_tag_with_embedding),

                # Add the analysis to each frame
                DeepFaceTagFaces(face_detector='yolov8', embeddings=False, analyze=True),

                # Generate captions for each tagged face (this is declared above)
                CaptionFaces(),

                # Write the new frames to a directory:
                SaveFramesToDirectory(root=facedir),

                # Write the Frame objects in JSON form
                # This won't include the frame images themselves, but it includes the saved path
                # from above, so the images can still be displayed.
                WriteFrameObjectsToDirectory(root=tagdir)
            ])

            if show:
                Connect(dt, ShowTags(wait=200))

            p.process_list( DissimilarFrameStream( rootdir, o=so ), verbose=True )

    # Now gather all of the paths and embeddings in order
    embeddings = []
    face_frames = []
    print("Start clustering.")
    with timer.Timer("time to read tags"):
        for f in FrameStream(tagdir,verbose=True):
            print("cluster f=",f)
            embeddings.append( f.findfirst_tag(TAG_FACE).embedding)
            face_frames.append(f)

    # embeddings is now a list of all the valid embeddings
    # frametags is a list of all the frametagdicts

    logging.debug("number of faces to cluster:%s",len(face_frames))
    if len(face_frames)==0:
        print("No faces to cluster")
        return

    # Convert list of embeddings to a numpy array for efficient computation
    X = np.array(embeddings)

    # Step 2: Perform DBSCAN clustering

    # Note: DBSCAN expects a distance matrix for the metric='precomputed',
    # so we use cosine_distances to compute the distance matrix from our embeddings
    # DBSCAN parameters like eps and min_samples can be adjusted based on your
    # specific dataset and needs
    with timer.Timer("time to cluster"):
        dbscan = DBSCAN(eps=0.5, min_samples=2, metric='precomputed')
        clusters = dbscan.fit_predict(cosine_distances(X))

    maxcluster = max(clusters)
    print("cluster count:",maxcluster)

    # Generate the gallery with a second pipeline, where the key for the gallery comes from the cluster number
    with SingleThreadedPipeline() as p:
        p.addLinearPipeline([WriteFramesToHTMLGallery(path='cluster.html')])

        for (cluster,f) in zip(clusters,face_frames):
            logging.debug("cluster %s frame %s",cluster,f)
            f.gallery_key = cluster
            p.process(f)


    # cluster.html is now made. On a mac just open it


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--rootdir", help='add face(s) from this directory or file')
    parser.add_argument("--facedir", help="Where to write the faces")
    parser.add_argument("--tagdir", help="Where to write tags", required=True)
    parser.add_argument("--dump",help="dump the database before clustering",action='store_true')
    parser.add_argument("--show", help="Show faces as they are ingested", action='store_true')
    parser.add_argument("--limit", type=int)
    clogging.add_argument(parser, loglevel_default='WARNING')
    args = parser.parse_args()
    clogging.setup(level=args.loglevel)

    if args.rootdir and not args.facedir:
        raise RuntimeError("--add requires --facedir")
    cluster_faces(rootdir=args.rootdir, facedir=args.facedir, tagdir=args.tagdir, show=args.show, limit=args.limit)
    subprocess.call(['open','cluster.html'])
