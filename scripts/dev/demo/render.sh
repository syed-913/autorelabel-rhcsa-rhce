#!/usr/bin/env bash
# Renders the README demo animation (demo.py) with Manim Community and ffmpeg.
# Manim: `pip install manim` in a virtual environment; it builds against the cairo and pango
# development headers (Debian/Ubuntu: libcairo2-dev libpango1.0-dev pkg-config).
#
#   scripts/dev/demo/render.sh [output dir]       default: docs/media
#
# Writes demo.gif (shown in the README) and demo.mp4 (1080p, for a release page).
# MANIM=/path/to/manim picks the manim binary (default: manim on PATH).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="${1:-$here/../../../docs/media}"
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

# One 96-colour palette for the whole clip and no dithering (dither noise changes every frame),
# so each frame stores only the rectangle that changed. (Lossy animated WebP is smaller, but
# libwebp skips changes below its quality threshold, so slow fades leave ghosts behind.)
echo "== demo.gif"
ffmpeg -v error -y -i "$out/demo.mp4" -filter_complex \
  "fps=12,scale=880:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=96:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle" \
  -loop 0 "$out/demo.gif"
ls -l "$out/demo.mp4" "$out/demo.gif"
