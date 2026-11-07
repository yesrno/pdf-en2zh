#!/usr/bin/env python3
"""Local PDF geometry helpers; semantic translation is performed by the agent."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

try:
    import pymupdf as fitz
except ImportError:
    raise SystemExit('Install dependency: python -m pip install "PyMuPDF>=1.26,<2"')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def fresh(path):
    path = Path(path)
    require(not path.exists(), f"Output already exists: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def open_pdf(path, normalize=False):
    doc = fitz.open(path)
    require(doc.is_pdf and not doc.needs_pass, "Expected an accessible, unlocked PDF")
    require(len(doc) > 0, "Empty PDF")
    if normalize:
        doc.bake()  # Keep visible annotation/widget appearances in a static copy.
        for page in doc:
            page.remove_rotation()
    return doc


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def inspect_doc(path, doc):
    result = {"schema": 1, "source_sha256": digest(path), "pages": []}
    for i, page in enumerate(doc):
        blocks = []
        for j, block in enumerate(page.get_text("dict", flags=fitz.TEXTFLAGS_DICT & ~fitz.TEXT_PRESERVE_IMAGES)["blocks"]):
            if block["type"] != 0:
                continue
            lines = []
            for line in block["lines"]:
                spans = [{k: s[k] for k in ("text", "bbox", "font", "size", "color", "flags")} for s in line["spans"]]
                lines.append({"bbox": line["bbox"], "dir": line["dir"], "spans": spans})
            source = "\n".join("".join(s["text"] for s in line["spans"]) for line in lines)
            if source.strip():
                blocks.append({"id": f"p{i+1}-b{j}", "bbox": block["bbox"], "source": source,
                               "lines": lines, "action": None, "zh": ""})
        images = [list(info["bbox"]) for info in page.get_image_info()]
        result["pages"].append({"page": i+1, "width": page.rect.width, "height": page.rect.height,
                                "image_rects": images, "needs_visual_review": not blocks or bool(images), "blocks": blocks})
    # Normalize tuples to JSON lists so reload comparisons are stable.
    return json.loads(json.dumps(result, ensure_ascii=False))


def extract(args):
    output = fresh(args.output)
    with open_pdf(args.input, normalize=True) as doc:
        data = inspect_doc(args.input, doc)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Extracted {len(data['pages'])} pages to {output}")


def rect_inside(rect, bounds):
    return all(math.isfinite(x) for x in rect) and not rect.is_empty and bounds.contains(rect)


def apply(args):
    output = fresh(args.output)
    data = json.loads(Path(args.layout).read_text(encoding="utf-8-sig"))
    with open_pdf(args.input, normalize=True) as doc:
        original = inspect_doc(args.input, doc)
        require(data.get("source_sha256") == original["source_sha256"], "Source PDF hash mismatch")
        require(len(data["pages"]) == len(doc), "Page count mismatch")
        report = []
        for page, saved, actual in zip(doc, data["pages"], original["pages"]):
            for key in ("page", "width", "height"):
                require(saved[key] == actual[key], f"Changed page geometry: {actual['page']}")
            require(len(saved["blocks"]) == len(actual["blocks"]), "Blocks missing or added; use a custom layout path")
            tasks = []
            for block, raw in zip(saved["blocks"], actual["blocks"]):
                for key in ("id", "bbox", "source", "lines"):
                    require(block[key] == raw[key], f"Changed source field {key}: {raw['id']}")
                name = block["id"]
                action = block.get("action")
                require(action in ("translate", "keep"), f"Unreviewed block: {name}")
                if action == "keep":
                    require(str(block.get("reason", "")).strip(), f"Keep reason required: {name}")
                    continue
                text = block.get("zh", "")
                require(isinstance(text, str) and text.strip(), f"Missing translation: {name}")
                spans = [s for line in block["lines"] for s in line["spans"] if s["text"].strip()]
                require(all(abs(l["dir"][0]-1) < 0.001 and abs(l["dir"][1]) < 0.001 for l in block["lines"]), f"Rotated text needs custom layout: {name}")
                styles = {(s["font"], round(s["size"], 2), s["color"], s["flags"]) for s in spans}
                require(len(styles) == 1, f"Mixed styles need custom layout: {name}")
                source_rect = fitz.Rect(block["bbox"])
                target = fitz.Rect(block.get("target_bbox", block["bbox"]))
                require(rect_inside(target, page.rect), f"Invalid target rectangle: {name}")
                require(not any(source_rect.intersects(fitz.Rect(r)) or target.intersects(fitz.Rect(r)) for r in actual["image_rects"]), f"Image overlap / possible OCR layer needs custom layout: {name}")
                erase = [fitz.Rect(s["bbox"]) for s in spans]
                for other in actual["blocks"]:
                    if other["id"] != name:
                        require(not target.intersects(fitz.Rect(other["bbox"])), f"Target overlaps another block: {name}")
                        require(not any(r.intersects(fitz.Rect(s["bbox"])) for r in erase for l in other["lines"] for s in l["spans"]), f"Possible adjacent-text removal: {name}")
                font_path = Path(block.get("font_file", args.font)).resolve()
                require(font_path.is_file(), f"Missing font: {font_path}")
                font = fitz.Font(fontfile=str(font_path))
                missing = sorted({c for c in text if not c.isspace() and not font.has_glyph(ord(c))})
                require(not missing, f"Font lacks characters in {name}: {''.join(missing)}")
                color_int = spans[0]["color"]
                color = tuple(((color_int >> shift) & 255)/255 for shift in (16, 8, 0))
                align = int(block.get("align", 0))
                lineheight = float(block.get("lineheight", 1.2))
                require(align in (0, 1, 2, 3) and 1 <= lineheight <= 2, f"Invalid spacing/alignment: {name}")
                original_size = spans[0]["size"]
                candidates = [original_size] if original_size < 8 else [original_size*(1-0.01*k) for k in range(11)]
                font_name = "ZH" + hashlib.sha256(str(font_path).encode()).hexdigest()[:12]
                params = dict(fontfile=str(font_path), fontname=font_name, align=align, lineheight=lineheight, color=color)
                # Test fit on a separate page so failed layouts cannot partly alter the output.
                with fitz.open() as probe_doc:
                    probe = probe_doc.new_page(width=page.rect.width, height=page.rect.height)
                    size = None
                    for candidate in candidates:
                        if probe.insert_textbox(target, text, fontsize=candidate, **params) >= 0:
                            size = candidate
                            break
                require(size is not None, f"Translation does not fit at 90-100% font size: {name}; refine wording or a reviewed target_bbox")
                require(not any(target.intersects(t["rect"]) for t in tasks), f"Translated boxes overlap: {name}")
                tasks.append(dict(id=name, rect=target, text=text, size=size, params=params, erase=erase))
            # Erase all old text first, preserving images and vector paths.
            for task in tasks:
                for r in task["erase"]:
                    page.add_redact_annot(r, fill=False, cross_out=False)
            if tasks:
                page.apply_redactions(images=0, graphics=0, text=0)
            for task in tasks:
                spare = page.insert_textbox(task["rect"], task["text"], fontsize=task["size"], **task["params"])
                require(spare >= 0, f"Unexpected insertion failure: {task['id']}")
                report.append({"id": task["id"], "font_size": task["size"]})
        doc.subset_fonts()
        doc.save(output, garbage=4, deflate=True)
    print(json.dumps({"output": str(output), "translated_blocks": report}, ensure_ascii=False))


def pair(args):
    output = fresh(args.output)
    require(math.isfinite(args.gap) and args.gap >= 0, "Gap must be finite and nonnegative")
    with open_pdf(args.english) as raw, open_pdf(args.english, True) as en, open_pdf(args.chinese, True) as zh, fitz.open() as result:
        require(len(en) == len(zh), "English and Chinese page counts differ")
        for i, (left, right) in enumerate(zip(en, zh)):
            w, h = left.rect.width, left.rect.height
            require(abs(w-right.rect.width) < 0.01 and abs(h-right.rect.height) < 0.01, f"Page {i+1} sizes differ")
            page = result.new_page(width=2*w+args.gap, height=h)
            page.draw_rect(page.rect, color=None, fill=(1, 1, 1))
            # Truly empty source pages do not have a content stream to embed.
            if left.get_contents():
                page.show_pdf_page(fitz.Rect(0, 0, w, h), en, i)
            if right.get_contents():
                page.show_pdf_page(fitz.Rect(w+args.gap, 0, 2*w+args.gap, h), zh, i)
            matrix = fitz.Matrix(96/72, 96/72)
            expected = raw[i].get_pixmap(matrix=matrix, alpha=False, annots=True)
            observed = page.get_pixmap(matrix=matrix, clip=fitz.Rect(0, 0, w, h), alpha=False)
            require((expected.width, expected.height, expected.n) == (observed.width, observed.height, observed.n), f"Page {i+1}: left render dimensions changed")
            diff = sum(abs(a-b) for a, b in zip(expected.samples, observed.samples))/len(expected.samples)
            require(diff <= 0.5, f"Page {i+1}: original visual changed (mean channel error {diff:.3f}); inspect normalization/annotations")
        result.save(output, garbage=4, deflate=True)
    print(f"Created {output}; left-page render comparisons passed")


def render(args):
    directory = fresh(args.directory)
    directory.mkdir()
    require(36 <= args.dpi <= 600, "DPI must be between 36 and 600")
    with open_pdf(args.input) as doc:
        for i, page in enumerate(doc):
            page.get_pixmap(dpi=args.dpi, alpha=False).save(directory / f"page-{i+1:04d}.png")
    print(f"Rendered {len(list(directory.glob('*.png')))} pages to {directory}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("extract")
    p.add_argument("input"); p.add_argument("output"); p.set_defaults(run=extract)
    p = sub.add_parser("apply")
    p.add_argument("input"); p.add_argument("layout"); p.add_argument("output")
    p.add_argument("--font", required=True); p.set_defaults(run=apply)
    p = sub.add_parser("pair")
    p.add_argument("english"); p.add_argument("chinese"); p.add_argument("output")
    p.add_argument("--gap", type=float, default=0); p.set_defaults(run=pair)
    p = sub.add_parser("render")
    p.add_argument("input"); p.add_argument("directory")
    p.add_argument("--dpi", type=int, default=140); p.set_defaults(run=render)
    args = parser.parse_args()
    try:
        args.run(args)
    except (ValueError, KeyError, RuntimeError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
