# fix-pal

Slow down a Matroska-contained movie to correct for PAL speedup.

In regions that historically used the
[PAL television standard](https://en.wikipedia.org/wiki/PAL), films shot at 24
frames per second (fps) were converted for television (including VHS and DVD)
at 25 fps, resulting in a 4% speedup with audio pitched up by nearly a
semitone. This problem generally does not affect newer digital formats (e.g.
Blu-ray), except in rare cases where a "new" release is created by upscaling an
older transfer that already exhibits speedup. (Looking at you, Doctor Who TV
movie!) Learn more about PAL speedup
[here](https://en.wikipedia.org/wiki/576i#PAL_speed-up).

This script forces a framerate change to the video track(s), avoiding
re-encoding and leaving the underlying data alone. Audio tracks' sample rates
are also reduced by the same rate, fixing the pitch issue and ensuring audio
and video remain in sync. Subtitles and chapters are re-timed to match.

I prefer this solution to re-encoding, as the latter adds the possibility of
quality loss. The resulting framerate will almost always be nonstandard, but
capable video players (e.g. [VLC](https://www.videolan.org/vlc/index.html))
have no issue with this -- and there is no excuse in this day and age for video
players not to support arbitrary framerates.

Portions of this script were adapted from code posted by James Ainslie
[here](https://blog.delx.net.au/2016/05/fixing-pal-speedup-and-how-film-and-video-work/comment-page-1/#comment-100160). These portions are marked.

Prerequesites:
- [MKVToolNix](https://mkvtoolnix.download)
- [FFmpeg](https://ffmpeg.org)

usage: `./fix_pal.sh <infile> <outfile>`
