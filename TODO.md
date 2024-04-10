- [ ] Review Apache Airflow. airflow.apache.com. Is this worth using?

- [ ] DissimilarFramesIterator should take a threadcount. If >1 then it runs one process that is stuffing the dequeue with (frame,frame+1) similarity values (4 threads should do it).

# Metadata we need:
- [ ] Something like the forensic path

# Stages we need:
- [ ] Stage that implement If statements.
- [ ] Stage that implement forks

# Configuration:
- [ ] build stages from a YAML file

- [ ] Add face quality score to tags; make face extractor enforce minimum.

# Sources:
- [ ] Google Drive photos
- [ ] S3 Bucket recursively
- [ ] S3 Bucket with Lambda notification

# Application:
- [ ] Find similar photographs on your disk
- [ ] Rotate photos to normal


Ideas:
* Show people in your google drive photos

* source module - Frame, Root, Live Video, S3 bucket uploads, HTTP post, video to frames.
* https://github.com/michaelben/OCR-handwriting-recognition-libraries
