#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos, write them to a directory with metadata, and produce face clusters.
"""

import shelve

from sklearn.cluster import DBSCAN
from sklearn.metrics.pairwise import cosine_distances
import numpy as np


from bamboo.pipeline import SingleThreadedPipeline
from bamboo.stage import WriteFramesToDirectory,SaveTagsToShelf,ShowTags
from bamboo.face_deepface import DeepFaceTag
from bamboo.face import ExtractFacesToFrames
from bamboo.source import FrameStream
from bamboo.frame import TAG_FACE


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("--add", help='add face(s) from this directory or file')
    parser.add_argument("--facedir", help="Where to write the faces")
    parser.add_argument("--db", help="Output databaae.", required=True, default='faces')
    parser.add_argument("--dump",help="dump the database before clustering",action='store_true')
    args = parser.parse_args()

    if args.add and not args.facedir:
        raise RuntimeError("--add requires --facedir")


    def face_tags(t):
        """A filter for face tags"""
        return t.tag_type == TAG_FACE

    if args.add:
        p = SingleThreadedPipeline()
        p.addLinearPipeline(
            [ DeepFaceTag(face_detector='yolov8'),
              ShowTags(wait=200),
              ExtractFacesToFrames(scale=1.3),
              WriteFramesToDirectory(root=args.facedir),
              SaveTagsToShelf(tagfilter = face_tags,
                              path=args.db,
                              requirePaths=True)])
        p.process_list( FrameStream( args.add ) )

    # Now gather all of the paths and embeddings in order
    paths = []
    embeddings = []
    with shelve.open(args.db, writeback=False) as db:
        for (k,v) in db.items():
            paths.append(v['path'])
            embeddings.append(v['tag'].embedding)
            if args.dump:
                print("k=",k,"v=",v)


    # Convert list of embeddings to a numpy array for efficient computation
    X = np.array(embeddings)

    # Step 2: Perform DBSCAN clustering
    # Note: DBSCAN expects a distance matrix for the metric='precomputed',
    # so we use cosine_distances to compute the distance matrix from our embeddings
    # DBSCAN parameters like eps and min_samples can be adjusted based on your specific dataset and needs
    dbscan = DBSCAN(eps=0.5, min_samples=2, metric='precomputed')
    clusters = dbscan.fit_predict(cosine_distances(X))
    print("clusters:",clusters)
    maxcluster = max(clusters)
    for cl in range(maxcluster+1):
        print(f"Cluster {cl}")
        for (ct,path) in enumerate(paths):
            if clusters[ct]==cl:
                print("  ",path)
