#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


CAPTURE_RE = re.compile(
    r"(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2}).*?(?P<h>\d{2})[.:](?P<mi>\d{2})[.:](?P<s>\d{2})"
)


@dataclass(frozen=True)
class Item:
    path: Path
    capture_dt: datetime


def _parse_capture_dt_from_name(name: str) -> datetime | None:
    match = CAPTURE_RE.search(name)
    if not match:
        return None
    try:
        return datetime(
            int(match.group("y")),
            int(match.group("m")),
            int(match.group("d")),
            int(match.group("h")),
            int(match.group("mi")),
            int(match.group("s")),
        )
    except ValueError:
        return None


def _exiftool_capture_dt(path: Path) -> datetime | None:
    if not shutil.which("exiftool"):
        return None
    cmd = [
        "exiftool",
        "-s3",
        "-DateTimeOriginal",
        "-CreateDate",
        "-MediaCreateDate",
        "-TrackCreateDate",
        "-ModifyDate",
        "-d",
        "%Y-%m-%dT%H:%M:%S",
        str(path),
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
    except Exception:
        return None
    if not out:
        return None
    for line in out.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            return datetime.fromisoformat(line)
        except ValueError:
            continue
    return None


def _file_time_capture_dt(path: Path) -> datetime:
    st = path.stat()
    # macOS has st_birthtime; fall back to mtime elsewhere.
    birth = getattr(st, "st_birthtime", None)
    ts = birth if birth is not None else st.st_mtime
    return datetime.fromtimestamp(ts)


def _capture_dt(path: Path) -> datetime:
    from_name = _parse_capture_dt_from_name(path.name)
    if from_name:
        return from_name
    from_exif = _exiftool_capture_dt(path)
    if from_exif:
        return from_exif
    return _file_time_capture_dt(path)


def _convert_one(
    src: Path,
    dst: Path,
    *,
    quality: int,
    progressive: bool,
    keep_markers: bool,
    dry_run: bool,
) -> None:
    if dst.exists():
        raise FileExistsError(f"Destination already exists: {dst}")

    tmp = dst.with_suffix(dst.suffix + ".tmp")
    if tmp.exists():
        tmp.unlink()

    try:
        if dry_run:
            return

        # Convert to JPEG (baseline) via sips.
        subprocess.check_call(
            [
                "sips",
                "-s",
                "format",
                "jpeg",
                "-s",
                "formatOptions",
                str(quality),
                str(src),
                "--out",
                str(tmp),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        if progressive:
            if not shutil.which("jpegtran"):
                raise RuntimeError("jpegtran not found (required for progressive JPG).")
            copy_mode = "all" if keep_markers else "none"
            progressive_tmp = tmp.with_suffix(".prog.jpg")
            if progressive_tmp.exists():
                progressive_tmp.unlink()
            subprocess.check_call(
                [
                    "jpegtran",
                    "-optimize",
                    "-progressive",
                    "-copy",
                    copy_mode,
                    "-outfile",
                    str(progressive_tmp),
                    str(tmp),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            tmp.unlink(missing_ok=True)
            progressive_tmp.rename(tmp)

        if not tmp.exists() or tmp.stat().st_size == 0:
            raise RuntimeError(f"Conversion failed for {src}")

        tmp.rename(dst)
    finally:
        if tmp.exists() and not dry_run:
            tmp.unlink()


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Convert PNGs in a directory to progressive JPG and rename illus01, illus02... by capture time."
    )
    parser.add_argument("dir", nargs="?", default="illustrations", help="Directory to process (default: illustrations)")
    parser.add_argument("--prefix", default="illus", help="Output filename prefix (default: illus)")
    parser.add_argument("--quality", type=int, default=90, help="JPEG quality 1-100 (default: 90)")
    parser.add_argument("--no-progressive", action="store_true", help="Disable progressive output")
    parser.add_argument(
        "--no-keep-markers",
        action="store_true",
        help="Do not keep JPEG markers when running jpegtran",
    )
    parser.add_argument("--dry-run", action="store_true", help="Print actions without writing/deleting files")
    args = parser.parse_args(argv)

    directory = Path(args.dir)
    if not directory.is_dir():
        print(f"Not a directory: {directory}", file=sys.stderr)
        return 2

    quality = max(1, min(100, args.quality))
    progressive = not args.no_progressive
    keep_markers = not args.no_keep_markers

    pngs = sorted([p for p in directory.iterdir() if p.is_file() and p.suffix.lower() == ".png"])
    if not pngs:
        print(f"No PNG files found in {directory}")
        return 0

    items: list[Item] = [Item(path=p, capture_dt=_capture_dt(p)) for p in pngs]
    items.sort(key=lambda it: (it.capture_dt, it.path.name))

    pad = max(2, len(str(len(items))))
    planned: list[tuple[Path, Path]] = []
    for idx, item in enumerate(items, start=1):
        dst = directory / f"{args.prefix}{idx:0{pad}d}.jpg"
        planned.append((item.path, dst))

    collisions = [dst for _, dst in planned if dst.exists()]
    if collisions:
        print("Refusing to overwrite existing files:", file=sys.stderr)
        for c in collisions:
            print(f"- {c}", file=sys.stderr)
        return 3

    for src, dst in planned:
        if args.dry_run:
            print(f"{src.name} -> {dst.name}")
            continue
        _convert_one(
            src,
            dst,
            quality=quality,
            progressive=progressive,
            keep_markers=keep_markers,
            dry_run=False,
        )
        src.unlink()

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
