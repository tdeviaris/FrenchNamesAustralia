#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/generate_avif_previews.sh [options] [paths...]

Generates lightweight preview AVIF files (same basename, .avif extension) next to JPEGs.
Default behavior keeps the original image resolution and uses very low quality, so the preview
often weighs only a few kilobytes while preserving layout and overall readability.

Options:
  --max-size N     Longest side in pixels (optional; when omitted keeps original resolution)
  --quality N      AVIF quality 0..100 (default: 1)
  --speed N        AVIF encoder speed 0..10 (0 slowest/best, 10 fastest) (default: 0)
  --overwrite      Re-generate even if output is newer than input

Examples:
  scripts/generate_avif_previews.sh img
  scripts/generate_avif_previews.sh --max-size 256 img/baudin.jpg

Requires:
  - avifenc (brew install libavif)
  - ffmpeg (only if --max-size is used)
EOF
}

max_size=""
quality="1"
speed="0"
overwrite="0"

while [[ $# -gt 0 ]]; do
  case "${1:-}" in
    -h|--help)
      usage
      exit 0
      ;;
    --max-size)
      max_size="${2:-}"
      shift 2
      ;;
    --quality)
      quality="${2:-}"
      shift 2
      ;;
    --speed)
      speed="${2:-}"
      shift 2
      ;;
    --overwrite)
      overwrite="1"
      shift
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Unknown flag: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      break
      ;;
  esac
done

avifenc_bin="$(command -v avifenc || true)"
ffmpeg_bin="$(command -v ffmpeg || true)"

if [[ -z "$avifenc_bin" ]]; then
  echo "avifenc not found. Install with: brew install libavif" >&2
  exit 1
fi
if [[ -n "$max_size" && -z "$ffmpeg_bin" ]]; then
  echo "ffmpeg not found (required with --max-size). Install with: brew install ffmpeg" >&2
  exit 1
fi

if [[ $# -gt 0 ]]; then
  roots=("$@")
else
  roots=("img")
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "$tmp_dir"' EXIT

find "${roots[@]}" -type f \( -iname "*.jpg" -o -iname "*.jpeg" \) -not -path "*/node_modules/*" | while IFS= read -r in_jpg; do
  out_avif="${in_jpg%.*}.avif"

  if [[ "$overwrite" != "1" && -f "$out_avif" && "$out_avif" -nt "$in_jpg" ]]; then
    continue
  fi

  if [[ -z "$max_size" ]]; then
    "$avifenc_bin" \
      -q "$quality" \
      -s "$speed" \
      -y 420 \
      --jobs all \
      --ignore-exif --ignore-xmp --ignore-icc \
      "$in_jpg" "$out_avif" >/dev/null
  else
    tmp_png="${tmp_dir}/$(basename "${in_jpg%.*}").png"

    "$ffmpeg_bin" -hide_banner -loglevel error -y -i "$in_jpg" \
      -vf "scale='if(gt(iw,ih),min(${max_size},iw),-2)':'if(gt(iw,ih),-2,min(${max_size},ih))':flags=bicubic" \
      -frames:v 1 "$tmp_png"

    "$avifenc_bin" \
      -q "$quality" \
      -s "$speed" \
      -y 420 \
      --jobs all \
      --ignore-exif --ignore-xmp --ignore-icc \
      "$tmp_png" "$out_avif" >/dev/null
  fi
done
