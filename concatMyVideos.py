#!/usr/bin/python

import getopt
import os
import subprocess
import sys


# helper class for static method
class Process:

  def __init__(self, temp_dir, concat_file, verbose):
    self.temp_dir = temp_dir
    self.concat_file = concat_file
    self.verbose = verbose

  """
    Recurse over all directories and find files
  """
  def recurse(self, directory, subdir_prefix):
    for filename in sorted(os.listdir(directory)):
      dir_path = os.path.join(directory, filename)
      if not os.path.isdir(dir_path):
        if filename.endswith(".mp4"):
          print('creating clips for:', dir_path)
          self.process(dir_path)
      else:
        if (len(subdir_prefix) > 0 and filename.startswith(subdir_prefix)) or len(subdir_prefix) == 0:
          self.recurse(dir_path, subdir_prefix)
    return

  def process(self, file_path):
    counter = 0
    start = 0
    length = 0
    filename = os.path.split(file_path)[1].split(".")[0]
    filename = filename.replace("&", "_")
    ffprobe_command = ["ffprobe", "-i", file_path, "-show_entries", "format=duration", "-v", "quiet"]

    p = subprocess.Popen(ffprobe_command, stdout=subprocess.PIPE, universal_newlines=True)
    p.stdout.readline()  # skip "[FORMAT]"

    # get only int "12" seconds out of the string: "duration=12.3246"
    duration = int(p.stdout.readline().split("=")[1].split(".")[0])

    # if duration > 50:
    #   start = 12
    #   length = 8
    #   while duration >= start + length:
    #     counter += 1
    #     self.trim(str(start), str(length), file_path, os.path.join(self.temp_dir, filename + "_" + str(counter) + ".mp4"))
    #     start = 20 + start + length
    if duration > 50:
      # create a maximum of three 10-seconds-clips out of the whole video
      start = duration//6
      length = 10
      while duration >= start + length:
        counter += 1
        self.trim(str(start), str(length), file_path, os.path.join(self.temp_dir, filename + "_" + str(counter) + ".mp4"))
        start = start + length + duration//6*counter
    elif duration > 30:
      start = 7
      length = 10
      while duration >= start + length:
        counter += 1
        self.trim(str(start), str(length), file_path, os.path.join(self.temp_dir, filename + "_" + str(counter) + ".mp4"))
        start = 10 + start + length
    elif 20 < duration < 30:
      start = 3
      length = duration - 5
      self.trim(str(start), str(length), file_path, os.path.join(self.temp_dir, filename + "_" + str(counter) + ".mp4"))
    else:
      start = 0
      length = duration
      self.trim(str(start), str(length), file_path, os.path.join(self.temp_dir, filename + "_" + str(counter) + ".mp4"))

    return

  def trim(self, start, length, file_path, output):

    suppress_verbose = ["-v", "quiet"]
    filename = os.path.split(output)[1]

    # dirArr = filePath.split("/")
    # date = dirArr[len(dirArr)-2]

    # temporary files
    temp_file = os.path.join(self.temp_dir, "trimmedTemp.mp4")
    temp_scale_file = os.path.join(self.temp_dir, "scaledTemp.mp4")

    # commands for trim and overlay recording date with ffmpeg and also scaling to 1080p
    ### TRIM ###
    command_trim = ["ffmpeg", "-ss", start, "-i", file_path, "-t", length, "-avoid_negative_ts", "1", "-c", "copy", "-y", temp_file]
    if not self.verbose:
      command_trim.extend(suppress_verbose)
    subprocess.call(command_trim)

    ### SCALE ###
    command_scale = ["ffmpeg", "-i", temp_file, "-vf", "scale=iw*min(1920/iw\,1080/ih):ih*min(1920/iw\,1080/ih), pad=1920:1080:(1920-iw*min(1920/iw\,1080/ih))/2:(1080-ih*min(1920/iw\,1080/ih))/2",
                    "-c:v", "h264_nvenc", "-preset", "llhq", "-rc:v", "vbr_minqp", "-qmin:v", "20", "-qmax:v", "23", "-b:v", "3000k", "-maxrate:v", "6000k", "-profile:v", "high", "-r", "30", "-c:a",
                    "copy", "-y", temp_scale_file]
    if not self.verbose:
      command_scale.extend(suppress_verbose)
    subprocess.call(command_scale)

    ### ADD OVERLAY ###
    command_overlay = ["ffmpeg", "-i", temp_scale_file, "-vf",
                      "drawtext='text=" + filename[:-6] + ": fontcolor=white: fontsize=32: box=1: boxcolor=black@0.5: boxborderw=5: x=(w-text_w-50): y=(h-text_h-40)'"]
    command_overlay2 = ["-c:v", "h264_nvenc", "-preset", "llhq", "-rc:v", "vbr_minqp", "-qmin:v", "20", "-qmax:v", "23", "-b:v", "3000k", "-maxrate:v", "6000k", "-profile:v", "high", "-r", "30",
                       "-c:a", "copy", output]
    command_overlay.extend(command_overlay2)
    if not self.verbose:
      command_overlay.extend(suppress_verbose)
    subprocess.call(command_overlay)

    ### NORMALIZE AUDIO ###
    subprocess.call(["ffmpeg-normalize", output, "-nt", "ebu", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-o", output, "-f"])
    self.concat_file.write("file " + filename + "\n")
    return

  def concatenate(self, name, output_path):
    # finally concat videos
    command = ["ffmpeg", "-auto_convert", "1", "-f", "concat", "-i", os.path.join(self.temp_dir, "concatList.txt"), "-c", "copy", "-y", os.path.join(output_path, "myVideos_" + name + ".mp4")]
    if not self.verbose:
      command.extend(["-v", "quiet"])
    subprocess.call(command)


def main(argv):
  help = print('concatMyVideos.py -d <directory> [-p <sub-dir-search-prefix>] [-c (concatenate only)] [-o <output-directory-path>] [-v (verbose)]')
  path = ''
  prefix = ''
  verbose = False
  concat_only = False
  output_path = os.path.expanduser('~/')
  temppath = os.path.expanduser('~/.cache/concatMyVideos')

  try:
    opts, args = getopt.getopt(argv, "hcovd:p:", ["directory=", "prefix="])
  except getopt.GetoptError:
    help
    sys.exit(2)
  for opt, arg in opts:
    if opt == '-h':
      help
      sys.exit()
    elif opt in ("-d", "--directory"):
      path = arg
    elif opt in ("-p", "--prefix"):
      prefix = arg
    elif opt in ("-c", "--concat"):
      concat_only = True
    elif opt in ("-v", "--verbose"):
      verbose = True
    elif opt in ("-o", "--output-path"):
      output_path = arg

  if path == '':
    print('No directory given!')
    help
    sys.exit(2)

  print('Directory: ', path)
  print('Prefix: ', prefix)
  print()

  if not concat_only:
    print("## cleanup old temp directory, if exists ##")
    if os.path.exists(temppath):
      os.rmdir(temppath)
    os.makedirs(temppath)

    # file for writing down the list of created files, which will be later concatenated with ffmpeg
    concat_file = open(os.path.join(temppath, "concatList.txt"), "w")
    process_video = Process(temppath, concat_file, verbose)
    process_video.recurse(path, prefix)
    concat_file.close()
  else:
    process_video = Process(temppath, None, verbose)

  process_video.concatenate(prefix, output_path)

  print("===================================")
  print("=====   PROCESSING FINISHED   =====")
  print("===================================")


# call main
if __name__ == "__main__":
  main(sys.argv[1:])
