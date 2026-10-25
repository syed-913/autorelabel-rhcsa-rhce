#!/usr/bin/env bash
# Renders the README demo animation (demo.py) with Manim Community and ffmpeg.
# Manim: `pip install manim` in a virtual environment; it builds against the cairo and pango
# development headers (Debian/Ubuntu: libcairo2-dev libpango1.0-dev pkg-config).
#
#   scripts/dev/demo/render.sh [output dir]       default: the current directory
#
# Writes demo.mp4 (1080p, 30 fps, about 8 MB). It isn't committed: drag it into README.md on
# github.com (up to 10 MB on free plans) and onto release pages.
# MANIM=/path/to/manim picks the manim binary (default: manim on PATH).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="${1:-.}"
manim="${MANIM:-manim}"
scenes=(Banner Lab Exam Grading Results Finale)

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
mkdir -p "$out"

for scene in "${scenes[@]}"; do
  echo "== $scene"
  "$manim" render -q h --frame_rate 30 --disable_caching --progress_bar none \
    --media_dir "$work/media" "$here/demo.py" "$scene"
  printf "file '%s'\n" "$work/media/videos/demo/1080p30/$scene.mp4" >> "$work/scenes.txt"
done

echo "== demo.mp4"
ffmpeg -v error -y -f concat -safe 0 -i "$work/scenes.txt" -c:v libx264 -preset slow -crf 20 \
  -pix_fmt yuv420p -movflags +faststart -an "$out/demo.mp4"
ls -l "$out/demo.mp4"
