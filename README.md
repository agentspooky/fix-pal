# fix-pal

Slow down a Matroska-contained movie to correct for PAL speedup.

In regions that historically used the PAL television standard, films shot at
24 frames per second (fps) were converted for television (including VHS and
DVD) at 25 fps, resulting in a 4% speedup with audio pitched up by nearly a
semitone. This problem generally does not affect newer digital formats (e.g.
Blu-ray), except in rare cases where a "new" release is created by upscaling
an older transfer that already exhibits speedup (looking at you, Doctor Who
TV movie!). Learn more about PAL speedup
[here](https://en.wikipedia.org/wiki/576i#PAL_speed-up).

This script forces a framerate change to the video track(s), avoiding re-
encoding and leaving the underlying data alone. Audio tracks' sample rates
are also reduced by the same rate, fixing the pitch issue and ensuring audio
and video remain in sync. Subtitles and chapters are re-timed to match.

I prefer this solution to re-encoding, as the latter adds the possibility of
quality loss. The resulting framerate will almost always be nonstandard, but
capable video players (e.g. VLC) have no issue with this -- and there is no
excuse in this digital era for video players not to support arbitrary
framerates.

Prerequesites:
- [MKVToolNix](https://mkvtoolnix.download)
- [FFmpeg](https://ffmpeg.org)

usage: `./fix_pal.sh <infile> <outfile>`
