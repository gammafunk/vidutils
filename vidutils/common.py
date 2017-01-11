import datetime
import logging
import re
import subprocess
import sys

_log = logging.getLogger()
_log.setLevel(logging.INFO)
_log.addHandler(logging.StreamHandler())

def run_command(args):
    '''Run command with args and check that we didn't error'''
    _log.info('Running command: %s', ' '.join(args))
    result = subprocess.run(args)
    result.check_returncode()

def probe_video(filename):
    '''Run ffprobe on the given file and parse out the video length, video
    resolution, video bitrate (rounded to nearest 1000 kb/s), and video fps.'''

    _log.info('Checking video file %s', filename)
    result = subprocess.run(['ffprobe', filename], stderr=subprocess.PIPE)
    result.check_returncode()

    ffprobe_out = result.stderr.decode('utf-8')
    match = re.search('Duration: *([^,]+),', ffprobe_out)
    if not match:
        _log.error("Can't find video duration in file %s\n%s", filename,
                   ffprobe_out)
        sys.exit(1)

    values = {'duration' : match.group(1)}

    vid_pat = 'Stream #0:0.*Video.*, ([0-9]+x[0-9]+), ([0-9]+) kb/s, ([0-9]+) fps'
    match = re.search(vid_pat, ffprobe_out)
    if not match:
        _log.error("Can't find video details in %s\n%s", filename, ffprobe_out)
        sys.exit(1)
    fields = ['resolution', 'bitrate', 'fps']
    for i,f in enumerate(fields):
        value = match.group(i + 1)
        if not value:
            _log.error("Can't find video %s for file %s", f, filename)
            sys.exit(1)
        values[f] = value

    values['bitrate'] = int(round(int(values['bitrate']), -2))
    values['fps'] = int(values['fps'])
    fields = ['duration'] + fields

    num_channels = 0
    audio_pat = 'Stream #0:([0-9]+).*Audio'
    for line in ffprobe_out.split('\n'):
        match = re.search(audio_pat, line)
        if not match:
            continue

        num_channels = int(match.group(1))
    values['num_channels'] = num_channels

    _log.info('Video Details: Length: %s, Resolution: %s, Bitrate: %d kb/s, '
            'FPS: %d', *[values[f] for f in fields])
    _log.info('Audio channels: %d', num_channels)
    return values
