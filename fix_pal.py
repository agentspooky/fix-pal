#!/usr/bin/env python3

"""
fix-pal.py

Slow down a Matroska-contained video to correct for PAL speedup.
"""


__author__ = "Jack Fisher"
__credits__ = ["Jack Fisher", "James Ainsley", "BlackScreen"]
__version__ = "2.0"


import argparse
import re
import subprocess
import sys
import tempfile

from fractions import Fraction
from os.path import realpath
from pathlib import Path
from shutil import which


# Modify this if the correction factor needs tweaking. It's treated as a constant
# throughout.
CORRECTION_FACTOR = "25/24"


# dict of tools that this script calls. The `None` values are replaced at runtime with
# each tool's absolute path if the tool is installed and executable.
tools = {"ffmpeg": None, "mkvextract": None, "mkvinfo": None, "mkvmerge": None}


def check_prereqs():
    """
    For each utility needed, see if it's installed and grab its absolute path.

    If any are missing, note which are and explain to the user that they must be
    installed.
    """
    global tools
    missing_tools = []
    for tool in tools:
        if not (path := which(tool)):
            missing_tools.append(tool)
        else:
            tools[tool] = path

    if len(missing_tools) > 0:
        msg = "Error: the following utilities are missing from your system:"
        for tool in missing_tools:
            msg += f"\n\t{tool}"
        msg += "\nPlease install them in order to use this script."
        sys.exit(msg)


def handle_args():
    """Basic arg handling"""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        dest="infile", metavar="input_file", help="The file to be processed."
    )
    parser.add_argument(
        dest="outfile",
        metavar="output_file",
        help="The filename for the new, processed file.",
    )
    return parser.parse_args()


def check_exists(path):
    """
    Check whether a path exists and is a file.

    If it doesn't or isn't, complain and quit.
    """
    path = Path(path)  # lol
    if not Path.exists(path):
        sys.exit("Error: input path does not exist.")
    if not Path.is_file(path):
        sys.exit("Error: input path is not a regular file.")


def confirm_overwrite(path):
    """
    Prompt the user to confirm overwriting a file at a given path.

    If the user does not confirm, or if the path points to a directory, quit.
    """
    path = Path(path)  # oops I did it again
    if Path.exists(path):
        if Path.is_dir(path):
            sys.exit("Error: output path is a directory!")

        query = (
            f"Output file `{path}` already exists.\n"
            + "Do you want to overwrite it? [y|N] "
        )
        proceed = input(query)
        if proceed.casefold() != "y".casefold():
            print("Stopping.")
            sys.exit()


def get_and_validate_args():
    """Handle arg and path validation."""
    args = handle_args()
    check_exists(args.infile)

    if realpath(args.infile) == realpath(args.outfile):
        # Don't allow directly overwriting the input file.
        sys.exit("Error: input and output paths are identical.")

    confirm_overwrite(args.outfile)
    return args.infile, args.outfile


def adjust_timestamp(matchobj):
    """
    Adjust a single timecode value by `CORRECTION_FACTOR`.

    This function modified from code by James Ainslie from
    <https://blog.delx.net.au/2016/05/fixing-pal-speedup-and-how-film-and-video-work/comment-page-1/#comment-100160>
    """
    old_timestamp = matchobj.group(0)
    hrs = int(old_timestamp[:2])
    mins = int(old_timestamp[3:5])
    secs = float(old_timestamp[6:])
    old_total_secs = (3600 * hrs) + (60 * mins) + secs
    new_total_secs = Fraction(CORRECTION_FACTOR) * old_total_secs
    new_timestamp = "{:02.0f}:{:02.0f}:{:02.9f}".format(
        new_total_secs // 3600, new_total_secs % 3600 // 60, new_total_secs % 60
    )
    return new_timestamp


def edit_timecodes(infile, outfile):
    """
    Read an arbitrary track file, and produce a new one with timecodes adjusted.

    This function inspired by code by James Ainslie from
    <https://blog.delx.net.au/2016/05/fixing-pal-speedup-and-how-film-and-video-work/comment-page-1/#comment-100160>
    """
    pattern = r"\d{2}:\d{2}:\d{2}.\d+"
    with open(infile, "r") as inf, open(outfile, "w") as outf:
        for line in inf:
            fixed_line = re.sub(pattern, adjust_timestamp, line)
            outf.write(fixed_line)


def fix_chapters(infile, tmpdir):
    """
    Given an MKV file, pull out the existing chapters, then re-time them.

    This function modified from code by James Ainslie from
    <https://blog.delx.net.au/2016/05/fixing-pal-speedup-and-how-film-and-video-work/comment-page-1/#comment-100160>
    """
    cmd = [tools["mkvmerge"], "-i", infile]
    stdout = subprocess.run(cmd, text=True, capture_output=True).stdout
    if "Chapters".casefold() not in stdout.casefold():
        return ""

    old_chapter_file = tmpdir + "/hello-old-chap.xml"  # couldn't help it
    new_chapter_file = tmpdir + "/hello-new-chap.xml"
    subprocess.run([tools["mkvextract"], infile, "chapters", old_chapter_file])
    edit_timecodes(old_chapter_file, new_chapter_file)
    return ["--chapters", new_chapter_file]


def get_sync_flags(infile):
    """
    Get info on NON-AUDIO tracks and build an array of `--sync` args for later use.
    """
    sync_args = []
    cmd = [tools["mkvmerge"], "-i", infile]
    stdout = subprocess.run(cmd, text=True, capture_output=True).stdout
    pattern = r"()\d+(?=:)"
    for line in stdout.splitlines():
        if "Track ID".casefold() in line.casefold():
            if "audio".casefold() not in line.casefold():
                track_id = re.search(pattern, line).group(0)
                sync_args.extend(["--sync", f"{track_id}:0,{CORRECTION_FACTOR}"])
    return sync_args


# TODO: construct args that handle audio tracks individually, as in `get_sync_flags` above.
def get_audio_sample_rate(file):
    """
    Determine the sample rate for audio.

    If different tracks have different rates, choose that of the first audio track
    (technically, the first CHANNEL of the first audio track).
    """
    cmd = [tools["mkvinfo"], file]
    stdout = subprocess.run(cmd, text=True, capture_output=True).stdout
    pattern = r"\d+\.?\d*"
    for line in stdout.splitlines():
        if "Sampling frequency".casefold() in line.casefold():
            return re.search(pattern, line).group(0)


def fix_audio(infile, outfile):
    """
    Slow down the audio and re-sample at the original sample rate.

    Copy video, subtitles, chapters exactly as they are in the input file.
    """
    audio_factor = 1 / Fraction(CORRECTION_FACTOR)
    sample_rate = get_audio_sample_rate(infile)

    cmd = [
        tools["ffmpeg"],
        "-y",
        "-i",
        infile,
        "-map",
        "0",
        "-filter:a",
        f"asetrate={sample_rate}*{audio_factor}",
        "-c:v",
        "copy",
        "-c:s",
        "copy",
        "-max_interleave_delta",
        "0",
        outfile,
    ]
    subprocess.run(cmd)


def main():
    check_prereqs()
    (infile, outfile) = get_and_validate_args()

    with tempfile.TemporaryDirectory() as tmpdir:
        tmpfile = tmpdir + "/temp.mkv"

        # Get some info from the source file and build some of our args for the
        # `mkvmerge` call
        chapter_args = fix_chapters(infile, tmpdir)
        sync_args = get_sync_flags(infile)

        # For each video track, adjust the framerate by the correction factor. (No
        # re-encoding necessary!) Adjust subtitle timings to match. Add the adjusted
        # chapters from the new chapter file. Write everything to a temp file. (We'll
        # see why in the following step.)
        cmd = [tools["mkvmerge"], "--output", tmpfile]
        cmd.extend(sync_args)
        cmd.append("--no-chapters")
        cmd.extend(chapter_args)
        cmd.append(infile)
        subprocess.run(cmd)

        # This is why we used a temp file... we still have to re-encode audio in order
        # to keep the sample rate the same.
        fix_audio(tmpfile, outfile)


if __name__ == "__main__":
    main()
