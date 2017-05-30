#!/usr/bin/env python3

'''Use ffmpeg to merge two video mp4 files with an video+audio crossfade
between them.'''

import argparse
import datetime
import logging
import os
import os.path
import subprocess
import sys
import tempfile

from . import common

_log = logging.getLogger()
_log.setLevel(logging.INFO)
_log.addHandler(logging.StreamHandler())

def parse_time(time):
    '''Parse a time in HH:MM:SS[.SSS] format into a `datetime.timedelta`
    object'''
    args = dict(zip(['hours', 'minutes', 'seconds'],
        [float(x) for x in time.split(':')]))
    return datetime.timedelta(**args)

def delta_to_str(delta):
    '''Concert a datetime.timedelta into a valid timestamp string for ffmpeg.'''
    total_sec = delta.total_seconds()
    hours, remainder = divmod(total_sec, 3600)
    minutes, seconds = divmod(remainder, 60)
    return '{:02.0f}:{:02.0f}:{:05.2f}'.format(hours, minutes, seconds)

def make_temp_file(filename=None, desc=None, **kwargs):
    prefix = ''
    if filename:
        prefix = os.path.basename(filename) + '-'
    if desc:
        prefix += desc + '-'
    if prefix:
        kwargs['prefix'] = prefix
    if 'dir' not in kwargs:
        kwargs['dir'] = os.getcwd()
    if 'suffix' not in kwargs:
        kwargs['suffix'] = '.mp4'
    return tempfile.NamedTemporaryFile(**kwargs)

def crossfade_split(filename, video_duration, crossfade_duration, at_end,
                    crossfade_start=None, delete_temp=True):
    '''Split the mp4 video in *filename* into two files, the first containing
    the main video we want to keep, the second containing enough video for a
    crossfade.  *video_duration* contains the video's length and
    *crossfade_duration* the crossfade length, both time formats as strings.
    *at_end* is boolean indicating if the crossfade is at the end of the video.
    Video after the crossfade ends is discarded if *at_end* is True and video
    before the crossfade begins is discarded otherwise. If *crossfade_start* is
    given as a time string, the crossfade begins at this time, otherwise it
    begins *crossfade_duration* from the end/beginning of the video, depending
    on *at_end*.'''

    ffmpeg_args = ['ffmpeg', '-i', filename, '-map', '0', '-c', 'copy']
    crossfade_duration_delta = parse_time(crossfade_duration)
    video_duration_delta = parse_time(video_duration)
    begin_delta = None
    end_delta = None
    if crossfade_start:
        crossfade_start_delta = parse_time(crossfade_start)

    # We create the first video, creating begin_delta and end_delta relative to
    # the original video and have ffmpeg trim out anything not between these.
    # If at_end is True, this will be from the beginning of our input video
    # until the beginning of the crossfade. If at_end is False, this will be
    # from the end of the crossfade until the end of the video.
    if crossfade_start:
        if at_end:
            end_delta = crossfade_start_delta
        else:
            begin_delta = crossfade_start_delta + crossfade_duration_delta
    # Since we don't have crossfade_start, beginning of crossfade is
    # crossfade_duration from end of video if at_end is True, otherwise it's
    # the beginning of the video.
    else:
        if at_end:
            end_delta = video_duration_delta - crossfade_duration_delta
        else:
            begin_delta = crossfade_duration_delta

    if begin_delta:
        ffmpeg_args += ['-ss', delta_to_str(begin_delta)]

    if end_delta:
        ffmpeg_args += ['-to', delta_to_str(end_delta)]

    main_fh = make_temp_file(filename, 'main', delete=delete_temp)
    ffmpeg_args += ['-y', main_fh.name]
    common.run_command(ffmpeg_args)

    # Create the second video containing a portion to be crossfaded.
    ffmpeg_args = ['ffmpeg', '-i', filename, '-map', '0', '-c', 'copy']

    begin_delta = None
    end_delta = None
    if crossfade_start:
        begin_delta = crossfade_start_delta
        end_delta = crossfade_start_delta + crossfade_duration_delta
    else:
        if at_end:
            begin_delta = video_duration_delta - crossfade_duration_delta
        else:
            end_delta = crossfade_duration_delta

    if begin_delta:
        ffmpeg_args += ['-ss', delta_to_str(begin_delta)]
    if end_delta:
        ffmpeg_args += ['-to', delta_to_str(end_delta)]

    crossfade_fh = make_temp_file(filename, 'crossf', delete=delete_temp)
    ffmpeg_args += ['-y', crossfade_fh.name]
    common.run_command(ffmpeg_args)

    return (main_fh, crossfade_fh)

def crossfade_videos(first_file, second_file, duration_time, resolution, fps,
                     bitrate, num_channels, delete_temp=True):
    '''Given two videos of the same duration, merge their video/audio channels
    using a crossfade from the first video to the second.'''

    ffmpeg_args = ['ffmpeg', '-i', first_file, '-i', second_file]
    duration_sec = parse_time(duration_time).total_seconds()

    # Video filter
    # Make a black overlay at desired resolution for the length of the crossfade.
    filter = 'color=black:{}:d={}[base]; '.format(resolution, duration_sec)
    # Make fifo and setpts for first video.
    filter += '[0:v]fifo,setpts=PTS-STARTPTS[v0];'
    # Make fifo and fadein second video at t=0, do setpts.
    filter += ('[1:v]fifo,format=yuva420p,fade=in:st=0:d={}:alpha=1'
               ',setpts=PTS-STARTPTS[v1];').format(duration_sec)
    # Overlay base and first video, then overaly that and second video.
    filter += '[base][v0]overlay[tmp]; [tmp][v1]overlay,format=yuv420p[fv]; '

    # Audio filter
    # Crossfade each audio stream between the two files.
    audio_filters = []
    for i in range(0, num_channels):
        audio_filters.append('[0:a:{0}][1:a:{0}]acrossfade=d={1}[fa{0}]'.format(
            i, duration_sec))
    filter += ';'.join(audio_filters)

    # Assemble final args.
    ffmpeg_args += ['-filter_complex', filter, '-map', '[fv]']
    for i in range(0, num_channels):
        ffmpeg_args += ['-map', '[fa{}]'.format(i)]
    ffmpeg_args += ['-r', str(fps), '-b:v', str(bitrate) + 'k', '-strict',
            '-2', '-ac', '-2']
    out_file = make_temp_file(desc='final-crossf', delete=delete_temp)
    ffmpeg_args += ['-y', out_file.name]

    common.run_command(ffmpeg_args)
    return out_file

def concat_videos(files, output_filename, delete_temp=True):
    '''Use ffmpeg to concatenate the given list of files, in order, into a
    single video.'''

    input_fh = make_temp_file(desc='vid-list', mode='w+', suffix='.txt',
                              delete=False)
    for f in files:
        input_fh.write("file '{}'\n".format(f))
    input_fh.close()
    subprocess.run(['cat', input_fh.name])
    ffmpeg_args = ['ffmpeg', '-f', 'concat', '-safe', '0', '-i', input_fh.name,
            '-map', '0', '-c', 'copy', output_filename]
    try:
        common.run_command(ffmpeg_args)
    finally:
        if delete_temp:
            os.remove(input_fh.name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('files', nargs=2, metavar='<filename>',
                        help='An mp4 video file to merge')
    parser.add_argument('-o', dest='outfile', metavar='<filename>',
                        default='out.mp4', help='Output video filename')
    parser.add_argument('-s1', dest='start_first', metavar='<time>',
            default=None, help='When to start the crossfade in the first file')
    parser.add_argument('-s2', dest='start_second', metavar='<time>',
            default=None, help='When to start the crossfade in the second file')
    parser.add_argument('-d', dest='crossfade_duration', metavar='<HH:MM:SS>',
                        default='00:00:05',
                        help='How long for the crossfade to take.')
    parser.add_argument('-k', dest='delete_temp', action='store_false',
                        default=True, help='Keep all temporary files made')
    args = parser.parse_args()

    first_fields = common.probe_video(args.files[0])
    second_fields = common.probe_video(args.files[1])
    check_fields = ['resolution', 'fps']
    for f in check_fields:
        if first_fields[f] != second_fields[f]:
            _log.error("Error: %s (%s) of first file %s doesn't match %s (%s)"
                    "of second file %s", f, first_fields[f], args.files[0], f,
                    second_fields[f], args.files[1])
            sys.exit(1)

    if first_fields['num_channels'] != second_fields['num_channels']:
        _log.error("Error: Number of audio channels in files doesn't match")
        sys.exit(1)

    # Split each file into two files, the first having all video we want to keep,
    # and the second having video to crossfade.
    first_main_fh, first_crossfade_fh = crossfade_split(args.files[0],
            first_fields['duration'], args.crossfade_duration, True,
            args.start_first, args.delete_temp)
    second_main_fh, second_crossfade_fh = crossfade_split(args.files[1],
            second_fields['duration'], args.crossfade_duration, False,
            args.start_second, args.delete_temp)

    bitrate = max(first_fields['bitrate'], second_fields['bitrate'])
    crossfade_fh = crossfade_videos(first_crossfade_fh.name,
            second_crossfade_fh.name, args.crossfade_duration,
            first_fields['resolution'], first_fields['fps'], bitrate,
            first_fields['num_channels'], args.delete_temp)
    first_crossfade_fh.close()
    second_crossfade_fh.close()

    temp_files = [fh.name for fh in (first_main_fh, crossfade_fh, second_main_fh)]
    concat_videos(temp_files, args.outfile, args.delete_temp)
    _log.info('Video writen to %s', args.outfile)
