#!/usr/bin/env python3
"""
A simple pipeline to extract all of the faces from a set of photos, write them to a directory with metadata, and produce face clusters.
"""

import os
import math
import logging
from subprocess import call
import platform

from collections import defaultdict

from sklearn.cluster import DBSCAN,SpectralClustering
from sklearn.metrics import silhouette_score, davies_bouldin_score
from sklearn.metrics.pairwise import cosine_distances,cosine_similarity
import numpy as np

from lib.ctools import clogging
from lib.ctools import timer

from bamboo.stage  import Stage,SaveFramesToDirectory,ShowTags,Connect,WriteFrameObjectsToDirectory,FilterFrames,WriteFramesToHTMLGallery,WriteFramesToHTMLGallery_tag
from bamboo.face_deepface import DeepFaceTagFaces
from bamboo.face   import ExtractFacesToFrames
from bamboo.source import DissimilarFrameStream,TagsFromDirectory,FrameStream,SourceOptions
from bamboo.frame  import Frame,Tag,TAG_FACE
from bamboo.pipeline import SingleThreadedPipeline

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

def cluster_faces(*, rootdir, facedir, tagdir, show, out, epsilon,algorithm='dbscan',limit=None):
    if algorithm not in ['dbscan','sc']:
        raise RuntimeError("Clustering algorithm must be 'dbscan' or 'sc'.")

    os.makedirs(tagdir, exist_ok=True)
    os.makedirs(facedir, exist_ok=True)

    so = SourceOptions(limit=limit)

    # Get all the tags and build a list of urns. We won't scan them a second time.
    seen_urns = set()
    for f in FrameStream(tagdir):
        seen_urns.add(f.src_urn)
    print(f"{len(seen_urns)} in {tagdir}")

    # If a rootdir was specified, analyze the images and write all of the frames that have
    # and embedding
    if rootdir:
        with SingleThreadedPipeline( verbose=True ) as p:
            p.addLinearPipeline([
                # For each frame, tag all of the faces:
                dt:= DeepFaceTagFaces(face_detector='yolov8', embeddings=True),

                # For each tag, create a new frame and send it down the pipeline:
                ExtractFacesToFrames(scale=1.3),

                # Filter for frames that have a face tag with an embedding
                FilterFrames(input_filter=frame_has_face_tag_with_embedding),

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

            def not_seen(f):
                if f.urn in seen_urns:
                    return False
                return True

            p.process_list( DissimilarFrameStream( rootdir, o=so, output_filter=not_seen ))

    # Now gather all of the paths and embeddings in order
    embeddings = []
    face_frames = []
    for f in FrameStream(tagdir,verbose=True):
        embeddings.append( f.findfirst_tag(TAG_FACE).embedding)
        face_frames.append(f)

    # embeddings is now a list of all the valid embeddings
    # frametags is a list of all the frametagdicts

    if len(face_frames)==0:
        print("No faces to cluster")
        return

    # Convert list of embeddings to a numpy array for efficient computation
    print(f"Start clustering {len(face_frames)} faces.")
    X = np.array(embeddings)

    # Step 2: Perform DBSCAN clustering

    # Note: DBSCAN expects a distance matrix for the metric='precomputed',
    # so we use cosine_distances to compute the distance matrix from our embeddings
    # DBSCAN parameters like eps and min_samples can be adjusted based on your
    # specific dataset and needs
    with timer.Timer("time to cluster"):

        if algorithm=='dbscan':
            dbscan = DBSCAN(eps=epsilon, min_samples=2, metric='precomputed', n_jobs=-1)
            clusters = dbscan.fit_predict(cosine_distances(X))

        if algorithm=='sc':
            # First generate the affinity matrix
            cosine_dist_matrix = cosine_distances(X)
            sigma = 0.1
            affinity_matrix = np.exp(-cosine_dist_matrix / (2 * sigma**2))
            np.fill_diagonal(affinity_matrix, 0) # enforce zero diagonal

            # symmetrize the affinity matrix
            affinity_matrix = 0.5 * (affinity_matrix + affinity_matrix.T)

            # Range of clusters to try
            min_clusters = 20
            max_clusters = 50

            best_score = -1
            best_n_clusters = -1

            for n_clusters in range(min_clusters, max_clusters + 1):
                print("n_clusters=",n_clusters)
                sc = SpectralClustering(n_clusters=n_clusters, affinity='precomputed')
                labels = sc.fit_predict(affinity_matrix)

                # Evaluate clustering performance using silhouette score or Davies–Bouldin index
                silhouette_avg = silhouette_score(affinity_matrix, labels)
                # davies_bouldin_index = davies_bouldin_score(affinity_matrix, labels)

                # Choose the number of clusters that maximizes the silhouette score
                if silhouette_avg > best_score:
                    best_score = silhouette_avg
                    best_n_clusters = n_clusters
                    clusters = labels

            print("Best number of clusters:", best_n_clusters)
            print("Best silhouette score:", best_score)

    maxcluster = max(clusters)
    print("cluster count:",maxcluster)

    # Generate the gallery with a second pipeline, where the key for the gallery comes from the cluster number
    with SingleThreadedPipeline() as p:
        p.addLinearPipeline([WriteFramesToHTMLGallery(path=out)])

        for (cluster,f) in zip(clusters,face_frames):
            logging.debug("cluster %s frame %s",cluster,f)
            f.gallery_key = cluster
            p.process(f)




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
    parser.add_argument("--epsilon", type=float, default=0.5, help="DBSCAN parameter")
    parser.add_argument("--out", help="output html file", default="cluster.html")
    parser.add_argument("--algorithm", help="Specify algorithm to use. default is dbscan. other option is sc for SpectralClustering")
    clogging.add_argument(parser, loglevel_default='WARNING')
    args = parser.parse_args()
    clogging.setup(level=args.loglevel)

    if args.rootdir and not args.facedir:
        raise RuntimeError("--add requires --facedir")
    cluster_faces(rootdir=args.rootdir, facedir=args.facedir, tagdir=args.tagdir, show=args.show, out=args.out, epsilon=args.epsilon,algorithm=args.algorithm,limit=args.limit)


    match platform.system():
        case 'Linux':
            call(['xdg-open',args.out])
        case 'Darwin':
            call(['open',args.out])
        case 'Windows':
            call(['start',args.out])
