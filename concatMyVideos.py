#!/usr/bin/python

import getopt
import os
import subprocess
import sys


# helper class for static method
class Process:

  def __init__(self, tempDir, concatFile, verbose):
    self.tempDir = tempDir
    self.concatFile = concatFile
    self.verbose = verbose

  """
    Recurse over all directories and find files
  """

  def recurse(self, directory, subdirPrefix):
    for filename in sorted(os.listdir(directory)):
      dirPath = os.path.join(directory, filename)
      if not os.path.isdir(dirPath):
        if filename.endswith(".mp4"):
          print('creating clips for:', dirPath)
          self.process(dirPath)
      else:
        if (len(subdirPrefix) > 0 and filename.startswith(subdirPrefix)) or len(subdirPrefix) == 0:
          self.recurse(dirPath, subdirPrefix)
    return

  def process(self, filePath):
    counter = 0
    start = 0
    length = 0
    filename = os.path.split(filePath)[1].split(".")[0]
    filename = filename.replace("&", "_")
    ffprobeCommand = ["ffprobe", "-i", filePath, "-show_entries", "format=duration", "-v", "quiet"]

    p = subprocess.Popen(ffprobeCommand, stdout=subprocess.PIPE, universal_newlines=True)
    p.stdout.readline()  # skip "[FORMAT]"

    # get only int "12" seconds out of the string: "duration=12.3246"
    duration = int(p.stdout.readline().split("=")[1].split(".")[0])

    if duration > 50:
      start = 12
      length = 8
      while duration >= start + length:
        counter += 1
        self.trim(str(start), str(length), filePath, self.tempDir + filename + "_" + str(counter) + ".mp4")
        start = 20 + start + length
    elif duration > 30:
      start = 7
      length = 10
      while duration >= start + length:
        counter += 1
        self.trim(str(start), str(length), filePath, self.tempDir + filename + "_" + str(counter) + ".mp4")
        start = 10 + start + length
    elif duration > 20 and duration < 30:
      start = 3
      length = duration - 5
      self.trim(str(start), str(length), filePath, self.tempDir + filename + "_" + str(counter) + ".mp4")
    else:
      start = 0
      length = duration
      self.trim(str(start), str(length), filePath, self.tempDir + filename + "_" + str(counter) + ".mp4")

    return

  def trim(self, start, length, filePath, output):

    suppressVerbose = ["-v", "quiet"]
    filename = os.path.split(output)[1]

    # dirArr = filePath.split("/")
    # date = dirArr[len(dirArr)-2]

    # temporary files
    tempFile = self.tempDir + "trimmedTemp.mp4"
    tempScaleFile = self.tempDir + "scaledTemp.mp4"

    # commands for trim and overlay recording date with ffmpeg and also scaling to 1080p
    ### TRIM ###
    commandTrim = ["ffmpeg", "-ss", start, "-i", filePath, "-t", length, "-avoid_negative_ts", "1", "-c", "copy", "-y", tempFile]
    if not self.verbose:
      commandTrim.extend(suppressVerbose)
    subprocess.call(commandTrim)

    ### SCALE ###
    command_scale = ["ffmpeg", "-i", tempFile, "-vf", "scale=iw*min(1920/iw\,1080/ih):ih*min(1920/iw\,1080/ih), pad=1920:1080:(1920-iw*min(1920/iw\,1080/ih))/2:(1080-ih*min(1920/iw\,1080/ih))/2",
                    "-c:v", "h264_nvenc", "-preset", "llhq", "-rc:v", "vbr_minqp", "-qmin:v", "20", "-qmax:v", "23", "-b:v", "3000k", "-maxrate:v", "6000k", "-profile:v", "high", "-r", "30", "-c:a",
                    "copy", "-y", tempScaleFile]
    if not self.verbose:
      command_scale.extend(suppressVerbose)
    subprocess.call(command_scale)

    ### ADD OVERLAY ###
    command_overlay = ["ffmpeg", "-i", tempScaleFile, "-vf",
                      "drawtext='text=" + filename[:-6] + ": fontcolor=white: fontsize=32: box=1: boxcolor=black@0.5: boxborderw=5: x=(w-text_w-50): y=(h-text_h-40)'"]
    commandOverlay2 = ["-c:v", "h264_nvenc", "-preset", "llhq", "-rc:v", "vbr_minqp", "-qmin:v", "20", "-qmax:v", "23", "-b:v", "3000k", "-maxrate:v", "6000k", "-profile:v", "high", "-r", "30",
                       "-c:a", "copy", output]
    command_overlay.extend(commandOverlay2)
    if not self.verbose:
      command_overlay.extend(suppressVerbose)
    subprocess.call(command_overlay)

    ### NORMALIZE AUDIO ###
    subprocess.call(["ffmpeg-normalize", output, "-nt", "ebu", "-c:a", "aac", "-ar", "48000", "-b:a", "192k", "-o", output, "-f"])
    self.concatFile.write("file " + filename + "\n")
    return

  def concatenate(self, name):
    # finally concat videos
    command = ["ffmpeg", "-auto_convert", "1", "-f", "concat", "-i", self.tempDir + "concatList.txt", "-c", "copy", "-y", "myVideos_" + name + ".mp4"]
    if not self.verbose:
      command.extend(["-v", "quiet"])
    subprocess.call(command)


def main(argv):
  help = print('concatMyVideos.py -d <directory> [-p <sub-dir-search-prefix>] [-c (concatenate only)] [-v (verbose)]')
  path = ''
  prefix = ''
  verbose = False
  concatonly = False

  try:
    opts, args = getopt.getopt(argv, "hcvd:p:",["directory=","prefix="])
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
      concatonly = True
    elif opt in ("-v", "--verbose"):
      verbose = True

  if path == '':
    print('No directory given!')
    help
    sys.exit(2)

  print('Directory: ', path)
  print('Prefix: ', prefix)
  print()

  if not concatonly:
    print("## remove old temp directory, if exists ##")
    os.system("rm -r -f workingTemp")
    os.system("mkdir workingTemp")

    # file for writing down the list of created files, which will be later concatenated with ffmpeg
    concatFile = open("workingTemp/concatList.txt", "w")
    processVideo = Process("workingTemp/", concatFile, verbose)
    processVideo.recurse(path, prefix)
    concatFile.close()
  else:
    processVideo = Process("workingTemp/", None, verbose)

  processVideo.concatenate(prefix)

  os.system("rm -r -f workingTemp")

  print("===================================")
  print("=====   PROCESSING FINISHED   =====")
  print("===================================")


# call main
if __name__ == "__main__":
  main(sys.argv[1:])
