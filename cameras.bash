RTSP0='rtsp://admin:bimboobamp12++@10.2.15.242/cam/realmonitor?channel=1&subtype=0'
RTSP1='rtsp://admin:bimboobamp13++@10.2.15.244/cam/realmonitor?channel=1&subtype=0'
DIR0=camera0
DIR1=camera1

# From chatGPT:
mkdir -p $DIR0 $DIR1
nohup ffmpeg -hide_banner -loglevel quiet -nostats -i "$RTSP0" -vf fps=1 $DIR0/img_%08d.jpg &
nohup ffmpeg -hide_banner -loglevel quiet -nostats -i "$RTSP1" -vf fps=1 $DIR1/img_%08d.jpg &
