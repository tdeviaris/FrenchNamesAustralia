#!/usr/bin/env python3
from __future__ import annotations

import html
import os
import re
import subprocess
import sys
from typing import List, Tuple

from bs4 import BeautifulSoup


CSS_BLOCK = """
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 2em 1.5em;
            background-color: #fdfdfd;
        }
        .document-header {
            text-align: center;
            margin: 1.5em 0 2em;
        }
        .document-header p {
            margin: 0.2em 0;
            font-weight: 600;
        }
        figure {
            margin: 2.5em 0;
            text-align: center;
        }
        figure img {
            width: 100%;
            max-width: 720px;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 5px;
            box-sizing: border-box;
            background: #fff;
        }
        figure figcaption {
            margin-top: 0.8em;
            font-size: 0.9em;
            font-style: italic;
            color: #555;
        }
        figure figcaption p {
            margin: 0.25em 0;
        }
        .main-text {
            text-align: justify;
            margin-bottom: 2em;
        }
        .main-text p {
            margin: 0 0 1em;
        }
        .references-section {
            border-top: 1px solid #ccc;
            padding-top: 1em;
            margin-top: 2em;
            font-size: 0.95em;
        }
        .references-section h2 {
            font-size: 1.2em;
            font-style: normal;
        }
        .references-section ul {
            list-style: disc;
            padding-left: 1.5em;
            margin: 0.5em 0 0;
        }
        .references-section li {
            margin: 0.4em 0;
        }
        a {
            color: #0056b3;
            text-decoration: none;
        }
        a:hover {
            text-decoration: underline;
        }
"""


def run_textutil_lines(path: str) -> List[str]:
    result = subprocess.run(
        ["textutil", "-convert", "txt", "-stdout", path],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()


def extract_sections(lines: List[str]) -> Tuple[List[str], List[List[str]], List[str], List[str]]:
    titles: List[str] = []
    legends: List[List[str]] = []
    body_paragraphs: List[str] = []
    references: List[str] = []

    state = "titles"
    current_legend: List[str] = []
    current_paragraph: List[str] = []

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        lower = stripped.lower()

        if state == "titles":
            if stripped:
                titles.append(stripped)
                continue
            if titles:
                state = "pre_fig"
            continue

        if state == "pre_fig":
            if not stripped:
                continue
            if lower.startswith("fig") or lower.startswith("source"):
                current_legend = [stripped]
                state = "legend"
                continue
            if lower.startswith("references"):
                state = "refs"
                references.append(stripped)
                continue
            current_paragraph = [stripped]
            state = "body"
            continue

        if state == "legend":
            if not stripped:
                if current_legend:
                    legends.append(current_legend)
                    current_legend = []
                state = "pre_fig"
                continue
            if lower.startswith("references"):
                if current_legend:
                    legends.append(current_legend)
                    current_legend = []
                references.append(stripped)
                state = "refs"
                continue
            if lower.startswith("fig") or lower.startswith("source"):
                if current_legend:
                    legends.append(current_legend)
                current_legend = [stripped]
            else:
                current_legend.append(stripped)
            continue

        if state == "body":
            if not stripped:
                if current_paragraph:
                    body_paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = []
                continue
            if lower.startswith("references"):
                if current_paragraph:
                    body_paragraphs.append(" ".join(current_paragraph))
                    current_paragraph = []
                references.append(stripped)
                state = "refs"
                continue
            current_paragraph.append(stripped)
            continue

        if state == "refs":
            if stripped:
                references.append(stripped)

    if current_legend:
        legends.append(current_legend)
    if current_paragraph:
        body_paragraphs.append(" ".join(current_paragraph))

    return titles, legends, body_paragraphs, references


def merge_legends(blocks: List[List[str]], num_images: int) -> List[List[str]]:
    if num_images <= 0:
        return []

    merged: List[List[str]] = [[] for _ in range(num_images)]
    block_index = 0

    for img_idx in range(num_images):
        while block_index < len(blocks):
            block = blocks[block_index]
            block_index += 1
            if not block:
                continue

            merged[img_idx].extend(block)

            blocks_left = len(blocks) - block_index
            images_left = num_images - img_idx - 1
            if blocks_left <= images_left:
                break

    return merged


def ensure_head(soup: BeautifulSoup):
    if not soup.head:
        head = soup.new_tag("head")
        soup.html.insert(0, head)
    else:
        head = soup.head

    head.clear()
    head.append(soup.new_tag("meta", charset="UTF-8"))
    head.append(
        soup.new_tag(
            "meta", attrs={"name": "viewport", "content": "width=device-width, initial-scale=1.0"}
        )
    )
    title_tag = soup.new_tag("title")
    head.append(title_tag)
    head.append(
        soup.new_tag(
            "link",
            rel="icon",
            type="image/png",
            sizes="32x32",
            href="../img/favicon32.png",
        )
    )
    head.append(
        soup.new_tag(
            "link",
            rel="icon",
            type="image/png",
            sizes="16x16",
            href="../img/favicon16.png",
        )
    )
    style_tag = soup.new_tag("style")
    style_tag.string = CSS_BLOCK
    head.append(style_tag)
    return head


def line_to_span(soup: BeautifulSoup, line: str):
    parts = []
    last = 0
    for match in re.finditer(r"https?://\S+", line):
        start, end = match.span()
        parts.append(html.escape(line[last:start]))
        url = match.group(0)
        stripped = url.rstrip(".,);")
        trailing = url[len(stripped):]
        parts.append(f'<a href="{html.escape(stripped)}">{html.escape(stripped)}</a>{html.escape(trailing)}')
        last = end
    parts.append(html.escape(line[last:]))
    container = BeautifulSoup(f"<span>{''.join(parts)}</span>", "html.parser").span
    return container


def append_line(tag, soup: BeautifulSoup, line: str):
    span = line_to_span(soup, line)
    for child in list(span.contents):
        tag.append(child)


def build_document(html_path: str, titles: List[str], legend_blocks: List[List[str]], body_paragraphs: List[str], references: List[str]):
    with open(html_path, "r", encoding="utf-8") as fh:
        soup = BeautifulSoup(fh, "html.parser")

    head = ensure_head(soup)
    if titles:
        head.title.string = " / ".join(titles[:2]) if len(titles) >= 2 else titles[0]
    else:
        head.title.string = os.path.basename(html_path)

    display_titles = list(titles)
    if display_titles:
        first_line = display_titles[0].lower()
        if "aus" in first_line and "name" in first_line:
            # In some documents the first line already mixes both languages
            display_titles.pop(0)
        else:
            display_titles = display_titles[1:]
    if display_titles and "name" in display_titles[0].lower():
        display_titles = display_titles[1:]

    body = soup.body or soup.new_tag("body")
    images = body.find_all("img")
    merged_legends = merge_legends(legend_blocks, len(images))

    new_body = soup.new_tag("body")

    if display_titles:
        header = soup.new_tag("header", attrs={"class": "document-header"})
        for line in display_titles:
            p = soup.new_tag("p")
            append_line(p, soup, line)
            header.append(p)
        new_body.append(header)

    for idx, img in enumerate(images):
        if not img.has_attr("src"):
            continue
        figure = soup.new_tag("figure")
        new_img = soup.new_tag("img", src=img["src"], alt=img.get("alt", ""))
        figure.append(new_img)

        legend = merged_legends[idx] if idx < len(merged_legends) else []
        if legend:
            figcaption = soup.new_tag("figcaption")
            for line in legend:
                p = soup.new_tag("p")
                append_line(p, soup, line)
                figcaption.append(p)
            figure.append(figcaption)

        new_body.append(figure)

    if body_paragraphs:
        main_div = soup.new_tag("div", attrs={"class": "main-text"})
        for paragraph in body_paragraphs:
            if not paragraph.strip():
                continue
            p = soup.new_tag("p")
            append_line(p, soup, paragraph)
            main_div.append(p)
        if main_div.contents:
            new_body.append(main_div)

    if references:
        ref_section = soup.new_tag("section", attrs={"class": "references-section"})
        heading_text = references[0].rstrip(":") or "References"
        h2 = soup.new_tag("h2")
        h2.string = heading_text
        ref_section.append(h2)
        if len(references) > 1:
            ul = soup.new_tag("ul")
            for item in references[1:]:
                if not item.strip():
                    continue
                li = soup.new_tag("li")
                append_line(li, soup, item)
                ul.append(li)
            ref_section.append(ul)
        new_body.append(ref_section)

    soup.body.replace_with(new_body)

    with open(html_path, "w", encoding="utf-8") as fh:
        fh.write(soup.prettify())


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage : postprocess_html.py <source_doc> <fichier_html>", file=sys.stderr)
        return 1

    source_path = sys.argv[1]
    html_path = sys.argv[2]

    if not os.path.exists(source_path):
        raise FileNotFoundError(source_path)
    if not os.path.exists(html_path):
        raise FileNotFoundError(html_path)

    lines = run_textutil_lines(source_path)
    titles, legends, body_paragraphs, references = extract_sections(lines)
    build_document(html_path, titles, legends, body_paragraphs, references)
    print(f"[postprocess] Fichier mis à jour : {os.path.basename(html_path)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
