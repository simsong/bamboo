#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos, write them to a directory with metadata, and produce face clusters.
"""

import os
import math
from collections import defaultdict

from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
import numpy as np

from lib.ctools import clogging
from lib.ctools import timer

from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import WriteFramesToDirectory,WriteTagsToDirectory,ShowTags,Connect
from bamboo.face_deepface import DeepFaceTag
from bamboo.face import ExtractFacesToFrames
from bamboo.source import DissimilarFrameStream,TagsFromDirectory
from bamboo.frame import TAG_FACE


HTML_HEAD = """
<html>
<style>
img.Image {
max-width:128px;
width:128px;
}
</style>
<body>
"""

def any_nan(vect):
    for v in vect:
        if math.isnan(v):
            return True
    return False

def cluster_faces(*, rootdir, facedir, tagdir, dump, show):

    os.makedirs(tagdir, exist_ok=True)

    def face_tags(t):
        """A filter for face tags"""
        return t.tag_type == TAG_FACE

    if rootdir:
        with SingleThreadedPipeline() as p:
            p.addLinearPipeline([ dt:= DeepFaceTag(face_detector='yolov8'),
                                  ExtractFacesToFrames(scale=1.3),
                                  WriteFramesToDirectory(root=facedir),
                                  WriteTagsToDirectory(tagfilter = face_tags, path=tagdir)])

        if show:
            Connect(dt, ShowTags(wait=200))

        p.process_list( DissimilarFrameStream( rootdir ) )

    # Now gather all of the paths and embeddings in order
    embeddings = []
    frametags = []
    with timer.Timer("time to read tags"):
        for v in TagsFromDirectory(tagdir):
            # First make sure that none of the embeddings are nan.
            embedding = v['tag'].embedding
            if any_nan(embedding):
                continue
            frametags.append(v)
            embeddings.append(embedding)


    # Convert list of embeddings to a numpy array for efficient computation
    X = np.array(embeddings)

    # Step 2: Perform DBSCAN clustering
    # Note: DBSCAN expects a distance matrix for the metric='precomputed',
    # so we use cosine_distances to compute the distance matrix from our embeddings
    # DBSCAN parameters like eps and min_samples can be adjusted based on your specific dataset and needs
    with timer.Timer("time to cluster"):
        dbscan = DBSCAN(eps=0.5, min_samples=2, metric='precomputed')
        clusters = dbscan.fit_predict(cosine_distances(X))

    maxcluster = max(clusters)
    print("cluster count:","max:",maxcluster)

    # Assign each tag to its cluster
    ftdict = defaultdict(list)
    for (cluster,frametag) in zip(clusters,frametags):
        frametag['tag'].cluster = cluster
        ftdict[cluster] =frametag

    with open("cluster.html","w") as c:
        c.write(HTML_HEAD)
        for cl in range(maxcluster+1):
            c.write(f"<h2>Cluster {cl}:</h2>")
            for (ct,frametag) in enumerate(ftdict[cl]):
                if ct<5:
                    path = frametag['path']
                    try:
                        src  = frametag['tag'].src
                    except AttributeError:
                        print("no src for:",frametag['tag'])
                        src  = ""
                    c.write(f"<a href='{src}'> <img src='{path}' class='Image'/></a>\n  ")
                elif ct==5:
                    c.write("...")
                else:
                    break
            c.write("<br/><hr/>")


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--rootdir", help='add face(s) from this directory or file')
    parser.add_argument("--facedir", help="Where to write the faces")
    parser.add_argument("--tagdir", help="Where to write tags", required=True)
    parser.add_argument("--dump",help="dump the database before clustering",action='store_true')
    parser.add_argument("--show", help="Show faces as they are ingested", action='store_true')
    clogging.add_argument(parser, loglevel_default='WARNING')
    args = parser.parse_args()
    clogging.setup(level=args.loglevel)

    if args.rootdir and not args.facedir:
        raise RuntimeError("--add requires --facedir")

    cluster_faces(rootdir=args.rootdir, facedir=args.facedir, tagdir=args.tagdir, dump=args.dump, show=args.show)
