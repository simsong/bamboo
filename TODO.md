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


Passive Front Desk features

Anonymous Visitor stats (to measure facility utilization)
Count of guests per day: people who stay more than 10 minutes in the space
Count of guests per hour: how many people are in the facility at some point during each hour block
Count of parking spaces used each day: How many of the spaces filled at some point each day for more than 10 minutes
Count of parking space availability by hour block: how many of the parking spaces were open during each hour block of the day on a given day
A way to view the above data that highlights times of high usage and low usage
A view of the above data that gives a reasonable measurement of facility usage compared to max capacity and compared to a rolling weekly average

CRM connected insights
A sync with the CRM that records when someone visits and for how long
A view that allows all unknown guests to be matched with a profile or added to a queue for review.
List of all visitors each day who are not badged accelerator users
A way to set up alerts that someone is desirable or undesirable is in the space
A way to alert when an unknown vehicle is parked in a Basis parking space
