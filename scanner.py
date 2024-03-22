#!/usr/bin/env python3
"""
Find new photos
"""

import cv2
import os
import os.path
import subprocess

THRESHOLD=0.96

from similarity.sim1 import img_sim

class Scanner:
    def __init__(self):
        self.current = None
        self.sim_threshold = THRESHOLD
        self.skipped = 0

    def ingest(self, fname):
        img = cv2.imread(fname)
        if img is None:
            return
        if self.current is None:
            self.current = img

        (score, diff) = img_sim(self.current, img)
        if score > self.sim_threshold:
            self.skipped += 1
        else:
            print(f"score={score} skipped={self.skipped}\t{fname}")
            subprocess.call(['open',fname])
            self.current = img
            self.skipped = 0


def process_root(root):
    sc = Scanner()

    for (dirpath, dirnames, filenames) in os.walk(root):
        for fname in sorted(filenames):
            print(fname+'\r',end='')
            if os.path.splitext(fname)[1].lower() in ['.jpg','/.jpeg']:
                sc.ingest( os.path.join(dirpath, fname))

if __name__=="__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Scan a directory",
                                     formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    parser.add_argument("root", help='Directory to process')
    args = parser.parse_args()

    process_root(args.root)
