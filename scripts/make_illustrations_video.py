#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


def _build_filter(
    n: int,
    *,
    width: int,
    height: int,
    seconds_per_image: float,
    fade_seconds: float,
    fps: int,
) -> str:
    if n < 1:
        raise ValueError("Need at least 1 image.")
    if fade_seconds <= 0 or fade_seconds >= seconds_per_image:
        raise ValueError("fade_seconds must be > 0 and < seconds_per_image.")

    base_step = seconds_per_image - fade_seconds

    parts: list[str] = []
    for i in range(n):
        parts.append(
            f"[{i}:v]"
            f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,"
            f"format=rgba,setsar=1"
            f"[v{i}]"
        )

    prev = "v0"
    for k in range(1, n):
        offset = base_step * k
        out = f"x{k}"
        parts.append(
            f"[{prev}][v{k}]"
            f"xfade=transition=fade:duration={fade_seconds}:offset={offset:.3f}"
            f"[{out}]"
        )
        prev = out

    parts.append(f"[{prev}]fps={fps},format=yuv420p[vout]")
    return ";".join(parts)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Create an MP4 slideshow from illustrations (3s/image + quick crossfade)."
    )
    parser.add_argument("--dir", default="illustrations", help="Input directory (default: illustrations)")
    parser.add_argument("--pattern", default="illus*.jpg", help="Glob pattern (default: illus*.jpg)")
    parser.add_argument("--out", default="illustrations/illustrations.mp4", help="Output mp4 path")
    parser.add_argument("--seconds", type=float, default=3.0, help="Seconds per image (default: 3)")
    parser.add_argument("--fade", type=float, default=0.30, help="Crossfade duration in seconds (default: 0.30)")
    parser.add_argument("--size", default="1080x1080", help="Output size WxH (default: 1080x1080)")
    parser.add_argument("--fps", type=int, default=30, help="Output FPS (default: 30)")
    parser.add_argument(
        "--include-illus00",
        action="store_true",
        help="Include illustrations/illus00.jpg if present (default: excluded)",
    )
    parser.add_argument("--crf", type=int, default=18, help="x264 CRF (default: 18)")
    parser.add_argument("--preset", default="medium", help="x264 preset (default: medium)")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite output if it exists")
    parser.add_argument("--dry-run", action="store_true", help="Print ffmpeg command only")
    args = parser.parse_args(argv)

    if not shutil.which("ffmpeg"):
        print("ffmpeg not found in PATH", file=sys.stderr)
        return 2

    try:
        width_s, height_s = args.size.lower().split("x", 1)
        width, height = int(width_s), int(height_s)
    except Exception:
        print(f"Invalid --size: {args.size} (expected WxH)", file=sys.stderr)
        return 2

    in_dir = Path(args.dir)
    images = sorted(in_dir.glob(args.pattern))
    images = [p for p in images if p.is_file()]
    if not args.include_illus00:
        images = [p for p in images if p.name != "illus00.jpg"]
    if not images:
        print(f"No images found: {in_dir / args.pattern}", file=sys.stderr)
        return 2

    out_path = Path(args.out)
    if out_path.exists() and not args.overwrite:
        print(f"Output exists (use --overwrite): {out_path}", file=sys.stderr)
        return 3
    out_path.parent.mkdir(parents=True, exist_ok=True)

    filter_complex = _build_filter(
        len(images),
        width=width,
        height=height,
        seconds_per_image=args.seconds,
        fade_seconds=args.fade,
        fps=args.fps,
    )

    cmd: list[str] = ["ffmpeg"]
    if args.overwrite:
        cmd.append("-y")
    else:
        cmd.append("-n")

    for img in images:
        cmd += ["-loop", "1", "-t", f"{args.seconds}", "-i", str(img)]

    cmd += [
        "-filter_complex",
        filter_complex,
        "-map",
        "[vout]",
        "-an",
        "-c:v",
        "libx264",
        "-crf",
        str(args.crf),
        "-preset",
        str(args.preset),
        "-movflags",
        "+faststart",
        str(out_path),
    ]

    if args.dry_run:
        print(" ".join(subprocess.list2cmdline([c]) if " " in c else c for c in cmd))
        return 0

    subprocess.check_call(cmd)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
