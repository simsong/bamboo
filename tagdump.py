"""
Dump the contents of a file as pickles
"""

import os
import pickle
import json

def dump(fname):
    with open(fname,"rb") as p:
        obj = pickle.load(p)
        print(obj)
        g = obj['tag']
        print("g=",g,json.dumps(g.dict()))


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("files", nargs="+")
    args = parser.parse_args()

    for fname in args.files:
        dump(fname)
