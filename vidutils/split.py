#!/usr/bin/env python3

'''Use ffmpeg split a video mp4 file into multiple files at the given times.'''

import argparse
import datetime
import logging
import os
import os.path
import sys

from . import common

_log = logging.getLogger()
_log.setLevel(logging.INFO)
_log.addHandler(logging.StreamHandler())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input_file', nargs=1, metavar='<filename>',
                        help='An mp4 video file to split into multiple files')
    parser.add_argument("split_times", nargs='+', metavar="<time>",
                        help="Time at which to split the video")
    parser.add_argument('-p', dest='output_prefix', metavar='<prefix>',
                        default=None, help='Output video filename prefix')
    parser.add_argument('-s', dest='start', metavar='<time>',
            default=None, help='Trim video before the given time')
    parser.add_argument('-e', dest='end', metavar='<time>',
            default=None, help='Trim video after the given time')
    args = parser.parse_args()

    prefix = args.output_prefix
    if not prefix:
        prefix = os.path.basename(args.input_file[0]) + "_part"
    for i in range(0, len(args.split_times) + 1):
        ffmpeg_args = ["ffmpeg", "-i", args.input_file[0]]
        if args.start and i == 0:
            ffmpeg_args += ["-ss", args.start]
        elif i > 0:
            ffmpeg_args += ["-ss", args.split_times[i - 1]]
        if args.end and i == len(args.split_times):
            ffmpeg_args += ["-to", args.end]
        elif i < len(args.split_times):
            ffmpeg_args += ["-to", args.split_times[i]]
        out_file = "{}{}.mp4".format(prefix, i + 1)
        ffmpeg_args += ["-map", "0", "-acodec", "copy", "-vcodec", "copy",
                out_file]
        common.run_command(ffmpeg_args)
