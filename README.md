# vidutils

Some scripts to automate some basic kinds of video manipulation with ffmpeg.

### Details

  Run any of these commands with `-h` to see usage info. All of these except
  `vid-split` use the `-o` option to set the output filename.

##### vid-split

Split a video into separate videos at the given timepoints. The following
command

    vid-split -p stream_part input.mp4 00:30:00 01:00:00 01:30:00

will take `input.mp4` and split it into 4 videos with video from times
00:00:00-00:30:00, 00:30:00-01:00:00, 01:00:00-01:30:00, and from 01:30:00 to
the end of the video. Each video will have a filename of "stream_partN.mp4",
where N begins counting at 1.

You can also trim video off the start and the end of the input video with `-s`
and `-e`. The following command

    vid-split -s 00:05:00 -e 01:55:00 -p stream_part input.mp4 00:35:00 01:05:00 01:35:00

will trim 5 minutes off the start of the video and any video after 01:55:00,
splitting the video into 4 parts like the previous example.

##### vid-volume

Adjust volume of segments of a specific audio channel in a video, optionally
merging the edited channel with others to make a final audio channel. The
default volume adjustment is to mute audio in the segment, but any valid ffmpeg
volume level can be specified through `-v`. The following command

    vid-volume -c 2 input.mp4 00:20:00-00:22:00 01:00:00-01:00:10

will mute the audio in the second audio channel for two minutes from 00:20:00
and for 10 seconds from 01:00:00. The following command

    vid-volume -c 2 -x 1 -m -v 2 input.mp4 00:20:00-00:22:00 01:00:00-01:00:10

will double the volume at the same times in the same channel and merge the
audio from any other audio channels except for channel 1. The `-x` option
accepts a comma-separated list of channels to exclude.

##### vid-merge

Merge two videos using a short audio and video crossfade between the two files.
The following command

    vid-merge input1.mp4 input2.mp4

will make an output video containing video from input1.mp4 and input2.mp4 with
a crossfade merging 5 seconds of video from the end of the first video and 5
seconds from the start of the second video.

You can change when the crossfade begins in the first video with `-s1`, when it
beings in the second video with `-s2`, and the crossfade duration with `-d`.
The first and second input file can be the same file, so you effectively cut
out video from a single file with a crossfade over the cut. The following
command

    vid-merge -s1 00:59:58 -s2 02:00:00 -d 00:00:02 input.mp4 input.mp4

makes a video file from input.mp4 with one hour of video removed from
01:00:00-02:00:00 and with a 2 second crossfade bridging the cut.

### Installation

ffmpeg and python 3 are the only requirements:

     pip3 install --user git+https://github.com/gammafunk/vidutils.git

With a user install of the package, the scripts will be available in
`~/.local/bin/`, otherwise they will be installed in `/usr/local/bin`.
