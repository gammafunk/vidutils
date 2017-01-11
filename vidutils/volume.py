#!/usr/bin/env python3

"""Adjust an audio channel in segments and merge it with another."""

import argparse
import datetime
import logging
import subprocess
import sys

from . import common

_log = logging.getLogger()
_log.setLevel(logging.INFO)
_log.addHandler(logging.StreamHandler())

def edit_volume(input_file, num_chan, output_file, audio_segs, volume_levs,
        target_chan, do_merge, exclude_chans):
    '''Build the audio volume filter and run ffmpeg.'''

    # Argument order matters for ffmpeg per the synopsis:

    # ffmpeg [global_options] {[input_file_options] -i input_url} ...
    # {[output_file_options] output_url} ...

    # Input file (and end of input args), then start output args with
    # copying the video codec.

    volume_statements = []
    ffmpeg_args = ["ffmpeg", "-i", input_file, "-vcodec", "copy"]
    for i, m in enumerate(audio_segs):
        start, stop = m.split("-")
        start_h, start_m, start_s = [int(x) for x in start.split(":")]
        start_delta = datetime.timedelta(seconds=start_s, minutes=start_m,
                                         hours=start_h)
        stop_h, stop_m, stop_s = [int(x) for x in stop.split(":")]
        stop_delta = datetime.timedelta(seconds=stop_s, minutes=stop_m,
                hours=stop_h)

        # Add a filter statement to adjust the volume in the audio duration.
        statement = "volume=enable='between(t,{},{})':volume={}".format(
                int(start_delta.total_seconds()),
                int(stop_delta.total_seconds()), volume_levs[i])
        volume_statements.append(statement)


    filter = "[0:a:{}]{}[aedit]".format(target_chan - 1,
        ",".join(volume_statements))

    map_args = ["-map", "0:v"]
    if do_merge:
        filter += ";"
        num_merge = num_chan - len(exclude_chans)
        for n in range(1, num_chan + 1):
            if n in exclude_chans or n is target_chan:
                continue

            filter += "[0:a:{}]".format(n - 1)

        # Make our merge filter to merge mic audio with the edited desktop
        # audio.
        filter += "[aedit]amerge=inputs={}[aout]".format(num_merge)
        map_args += ["-map", "[aout]"]
    else:
        for n in range(1, num_chan + 1):
            if n is target_chan:
                map_args += ["-map", "[aedit]"]
            else:
                map_args += ["-map", "0:a:{}".format(n - 1)]

    # Add the stream filter and maps for video and edited audio.
    ffmpeg_args += ["-filter_complex", filter] + map_args

    # Enable aac audio codec and set quality/channels.
    ffmpeg_args += ["-strict", "-2", "-ac", "2"]

    # Copy video codec and specify the output file.
    ffmpeg_args += ["-vcodec", "copy", output_file]

    common.run_command(ffmpeg_args)

def main():

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_file", nargs=1, metavar="<filename>",
            help="mp4 video file")
    parser.add_argument("audio_segments", nargs='+', metavar="<time>-<time>",
                        help="Segments in which to adjust the desktop audio.")
    parser.add_argument("-o", dest="output_file", metavar="<filename>",
            default="out.mp4", help="Output filename")
    parser.add_argument("-m", dest="do_merge", default=False,
            action='store_true', help="In a file with multiple channels, "
            "merge all non-excluded channels with the modified target channel")
    parser.add_argument("-c", dest="target_channel", metavar="N",
            default=1, type=int,
            help="In a file with multiple channels, target this channel for "
            "volume change")
    parser.add_argument("-x", dest="exclude_channels", metavar="N[,N...]",
            default=None, help="In a file with multiple channels, exclude "
            "these channels from merge")
    parser.add_argument("-v", dest="volume", metavar="<volume>", default='0',
                        help="Adjusted volume level")
    args = parser.parse_args()

    vid_details = common.probe_video(args.input_file[0])
    num_chan = vid_details["num_channels"]
    print("Found {} audio channel(s) in file {}".format(num_chan,
        args.input_file[0]))

    target_chan = args.target_channel
    if target_chan < 1 or target_chan > num_chan:
        _log.error("Invalid target channel number: %d", n)
        sys.exit(1)

    exclude_chans = []
    if args.exclude_channels:
        exclude_chans = [int(n) for n in args.exclude_channels.split(',')]
        exclude_chans = sorted(set(exclude_chans))
        for n in exclude_chans:
            if n < 1 or n > num_chan or n == target_chan:
                _log.error("Invalid channel number to exclude: %d", n)
                sys.exit(1)

    volume_levs = args.volume.split(',')
    if len(volume_levs) == 1:
        volume_levs = [args.volume for m in args.audio_segments]
    elif len(volume_levs) != len(args.audio_segments):
        print("Error: Number of volume values in -v must match number of audio"
                "segments")
        sys.exit(1)

    edit_volume(args.input_file[0], num_chan, args.output_file,
            args.audio_segments, volume_levs, target_chan, args.do_merge,
            exclude_chans)
