"""Design document.

Abstractions related to image content:

Frame - Represents a single frame of a video or a JPEG read from the
        disk. Can also represent a frame cropped from a JPEG or Video.

        Frames are immutable when they a stage; as a JPEG moves
        through the pipeline, the underlying representaiton is moved
        from one Frame object to another.

        Frames can be tagged with any number of properties.

        Frame is a class; each frame is an instance.

Patch - Patch is a rectangular part of a frame. It supports several
        operations, including .frame() which creates a copy of the
        original frame that can be manipulated.

Tag -   Frames can have one or more tags. Tags are kept in a list and
        are tuples consisting of (tag type, engine, patch, attributes)
        where attributes is an arbitrary python object. If patch is
        not Null then the attribute refers to just a single rectangular
        are.

Abstractions related to image processing:

Stage - the nodes of the pipeline. They have inputs and
        outputs. Frames can be copied from inputs to output, but if
        they are modified or if there are multiple outputs, then new
        frames are created.

        "Stage" is a class that is subclassed. Each node is an instance.

Sources - Generators that produce Frames.

Pipeline - An abstract super class. Subclassed for specific kinds of
           pipelines. Holds all of the stages and moves the frames
           between stages.  (Although in the current implementation,
           the actual list of stage inputs and outputs is kept in each
           stage, rather than in the pipeline.)



"""
