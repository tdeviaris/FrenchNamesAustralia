#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage:
  scripts/encode_pngs_to_jpg_mozjpeg.sh [--quality N] [--out-dir DIR] [--include-favicons] <file.png>...

Notes:
  - Requires: brew install mozjpeg, ffmpeg
  - Outputs progressive JPEGs encoded with MozJPEG (cjpeg).
  - PNGs are NOT deleted.
EOF
}

quality="95"
out_dir=""
include_favicons="0"

while [[ $# -gt 0 ]]; do
  case "${1:-}" in
    -h|--help)
      usage
      exit 0
      ;;
    --quality)
      quality="${2:-}"
      shift 2
      ;;
    --out-dir)
      out_dir="${2:-}"
      shift 2
      ;;
    --include-favicons)
      include_favicons="1"
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

if [[ $# -lt 1 ]]; then
  usage >&2
  exit 2
fi

mozjpeg_prefix="${MOZJPEG_PREFIX:-}"
if [[ -z "$mozjpeg_prefix" ]]; then
  mozjpeg_prefix="$(brew --prefix mozjpeg 2>/dev/null || true)"
fi

cjpeg="${mozjpeg_prefix}/bin/cjpeg"
ffmpeg_bin="$(command -v ffmpeg || true)"

if [[ ! -x "$cjpeg" ]]; then
  echo "MozJPEG not found. Install with: brew install mozjpeg" >&2
  echo "Or set MOZJPEG_PREFIX (expected cjpeg at: <prefix>/bin/cjpeg)." >&2
  exit 1
fi

if [[ -z "$ffmpeg_bin" ]]; then
  echo "ffmpeg not found. Install with: brew install ffmpeg" >&2
  exit 1
fi

if [[ -n "$out_dir" ]]; then
  mkdir -p "$out_dir"
fi

ffmpeg_filter='color=white:s=16x16[bg];[bg][0:v]scale2ref[bg2][fg];[bg2][fg]overlay=format=auto,format=rgb24'

for in_png in "$@"; do
  if [[ ! -f "$in_png" ]]; then
    echo "Missing input file: $in_png" >&2
    exit 1
  fi

  base_name="$(basename "$in_png")"
  if [[ "$include_favicons" != "1" ]] && [[ "$base_name" == favicon*.png ]]; then
    continue
  fi

  out_name="${base_name%.png}.jpg"
  if [[ -n "$out_dir" ]]; then
    out_jpg="${out_dir%/}/$out_name"
  else
    out_jpg="${in_png%.png}.jpg"
  fi

  tmp_out="$(mktemp)"
  "$ffmpeg_bin" -hide_banner -loglevel error -i "$in_png" \
    -filter_complex "$ffmpeg_filter" \
    -frames:v 1 -f image2pipe -vcodec ppm - \
    | "$cjpeg" -quality "$quality" -progressive -optimize > "$tmp_out"

  mv "$tmp_out" "$out_jpg"
done

