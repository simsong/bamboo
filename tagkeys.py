"""
dump a json file
"""


import json
import sys

if __name__=="__main__":
    with open(sys.argv[1],"r") as f:
        obj = json.load(f)
    print(json.dumps(obj,indent=4))
