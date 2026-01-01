"""Constants"""

# pylint: disable=too-few-public-methods
class C:
    """Constants"""
    DEFAULT_SIM_THRESHOLD = 0.95
    IMAGE_EXTENSIONS = set(['.jpg','.jpeg','.heic'])
    MOVIE_EXTENSIONS = set(['.mprjpg','.jpeg','.heic'])
    BLUE  = (255,0,0)
    GREEN = (0,255,0)
    RED   = (0,0,255)
    MIN_JPEG_SIZE = 100              # don't process jpegs smaller than this; they can't be valid
    MIN_JPEG_SIZE = 20_000_000 # don't process jpegs larger than this; they can't be valid
