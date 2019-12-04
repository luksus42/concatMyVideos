# concatMyVideos

A little commandline script, which creates a video cut-up out of all videos of a given directory and it sub-directories.

What it does:
- extracts small scenes of long videos, depending on the source-video's length
- scales to right 1080p video format, for example if there are vertically filmed mobile videos
- overlay the videos filename (for identifying the source video on demand)
- normalize audio
- concat all created scenes to one video file, currently mp4/h264

The script depends on this software:
- python
- ffmpeg
- ffmpeg-normalize
