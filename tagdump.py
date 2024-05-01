"""
Dump the contents of a file as pickles
"""

import pickle
import json

def dump_keys(obj, indent, verbose):
    if not isinstance(obj,dict):
        return
    for (k,v) in obj.items():
        print(" "*indent, k, type(v), end='')
        if verbose:
            print(v,end='')
        print("")
        if isinstance(v,dict):
            dump_keys(v,indent+4, verbose)
        if isinstance(v,list):
            for i in v:
                dump_keys(i,indent+4, verbose)


def dump(fname, verbose):
    with open(fname,"rb") as p:
        obj = json.load(p)
    dump_keys(obj,indent=0,verbose=verbose)


if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Extract all faces from a list of photos",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("files", nargs="+")
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    for fname in args.files:
        dump(fname, args.verbose)
