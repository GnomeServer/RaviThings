#!/usr/bin/env python3
"""Public-site boundary regressions using isolated authored test courses."""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import tempfile
import unittest
import zlib
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("course_build", ROOT / "scripts/build_course.py")
builder = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = builder
SPEC.loader.exec_module(builder)

PROCEDURE = """# Example

## Read a file

Read the supplied source before deciding what it supports.

**Terminal: Bash or zsh, ordinary user.**

```bash
printf '%s\\n' 'a < b & c'
```

**Expected:** You see the literal comparison text.

```text
a < b & c
```

**Stop:** If the command fails, keep the error. **Recovery:** Correct the path and rerun.

[Input file](shared/case/SOURCE.md)

| Field | Meaning |
|:---|---:|
| state | An observed state. |
"""

GUIDED_PROCEDURE = PROCEDURE + """

<details class="rf-stretch" markdown="1">
<summary>Optional stretch: inspect a second source</summary>

## Compare the second source

This is optional authored lesson prose, not raw case data.

<details><summary>Figure text</summary><p>The source and claim stay separate.</p></details>

</details>

The continuation remains outside the optional disclosure.

## Preserve the decision

Keep the unsupported claim unresolved.
"""


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return len(data).to_bytes(4, "big") + kind + data + zlib.crc32(kind + data).to_bytes(4, "big")


def _png_image(width: int, height: int) -> bytes:
    """An opaque black, 8-bit RGB image with unfiltered scanlines."""
    header = width.to_bytes(4, "big") + height.to_bytes(4, "big") + bytes((8, 2, 0, 0, 0))
    pixels = (b"\0" + b"\0\0\0" * width) * height
    return b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", header) + _png_chunk(b"IDAT", zlib.compress(pixels)) + _png_chunk(b"IEND", b"")


def _webp_container(kind: bytes, payload: bytes) -> bytes:
    chunk = kind + len(payload).to_bytes(4, "little") + payload + b"\0" * (len(payload) & 1)
    return b"RIFF" + (4 + len(chunk)).to_bytes(4, "little") + b"WEBP" + chunk


def _webp_image(width: int, height: int, kind: bytes = b"VP8L") -> bytes:
    """Minimal dimension headers; pixel decoding is outside the publisher's contract."""
    if kind == b"VP8L":
        payload = b"\x2f" + ((width - 1) | ((height - 1) << 14)).to_bytes(4, "little")
    elif kind == b"VP8 ":
        payload = b"\x10\0\0\x9d\x01\x2a" + width.to_bytes(2, "little") + height.to_bytes(2, "little")
    else:
        payload = b"\0" * 4 + (width - 1).to_bytes(3, "little") + (height - 1).to_bytes(3, "little")
    return _webp_container(kind, payload)


class WebPDimensions(unittest.TestCase):
    def test_webp_dimensions_read_vp8l_vp8_and_vp8x(self):
        for kind, width, height in ((b"VP8L", 1672, 716), (b"VP8 ", 1672, 941), (b"VP8X", 70001, 80003)):
            with self.subTest(kind=kind):
                self.assertEqual(builder._webp_dimensions(_webp_image(width, height, kind), PurePosixPath("image.webp")), (str(width), str(height)))
        scaled = _webp_image(1672 | 0xc000, 941 | 0x8000, b"VP8 ")
        self.assertEqual(builder._webp_dimensions(scaled, PurePosixPath("scaled.webp")), ("1672", "941"))

    def test_webp_dimensions_reject_malformed_containers(self):
        valid = _webp_image(1672, 941)
        variants = {
            "truncated": valid[:-1],
            "RIFF signature": b"NOPE" + valid[4:],
            "WEBP signature": valid[:8] + b"NOPE" + valid[12:],
            "RIFF size": valid[:4] + (len(valid) - 9).to_bytes(4, "little") + valid[8:],
            "trailing garbage": valid + b"garbage",
            "zero width": _webp_image(0, 941, b"VP8 "),
            "zero height": _webp_image(1672, 0, b"VP8 "),
            "unknown chunk": _webp_container(b"NOPE", b"\0" * 10),
            "chunk bounds": valid[:16] + (100).to_bytes(4, "little") + valid[20:],
            "VP8 start code": _webp_container(b"VP8 ", b"\0" * 10),
            "VP8L signature": _webp_container(b"VP8L", b"\0" * 5),
            "short VP8": _webp_container(b"VP8 ", b"\0" * 9),
            "short VP8L": _webp_container(b"VP8L", b"\x2f\0\0\0"),
            "short VP8X": _webp_container(b"VP8X", b"\0" * 9),
        }
        for label, data in variants.items():
            with self.subTest(case=label), self.assertRaises(ValueError):
                builder._webp_dimensions(data, PurePosixPath("broken.webp"))


class PublicationBehavior(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="course-publish-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        boot = self.root / "AI_Harness_Bootcamp_2"
        boot.mkdir()
        self.course = {"schema_version": 1, "course_id": "AI_Harness_Bootcamp_2", "source_root": "AI_Harness_Bootcamp_2", "site_dir": "site", "index": {"source": "README.md", "dest": "index.html", "kind": "home"}, "modules": [], "shared_downloads": []}
        (self.root / "ui").mkdir()
        self.course["ui_assets"] = []
        for name, content in {
            "course.css": "body { background-image: url('texture.svg'); }\n",
            "course.js": "'use strict';\n",
            "theme-init.js": "'use strict';\n",
            "texture.svg": '<svg xmlns="http://www.w3.org/2000/svg" width="1" height="1"></svg>\n',
        }.items():
            (self.root / "ui" / name).write_text(content, encoding="utf-8")
            self.course["ui_assets"].append({"source": f"ui/{name}", "dest": f"assets/{name}"})
        links = []
        for i in range(11):
            directory = f"module-{i:02d}-example"
            module = boot / directory
            (module / "shared/case").mkdir(parents=True)
            (module / "shared/case/SOURCE.md").write_text("# Authored test input\nRAW_CASE_SENTINEL_8f341\n", encoding="utf-8")
            (module / "README.md").write_text(PROCEDURE, encoding="utf-8")
            links.append(f"[Assignment {i}]({directory}/README.md)")
            pages = [{"source": "README.md", "dest": "README.html", "kind": "overview"}]
            (module / "lab.md").write_text(GUIDED_PROCEDURE, encoding="utf-8")
            pages.append({"source": "lab.md", "dest": "lab.html", "kind": "lab", "guide": {"context_sections": [], "optional_sections": []}})
            self.course["modules"].append({"id": f"{i:02d}", "directory": directory, "title": "Module · Example", "case_name": f"Example {i}", "summary": "Inspect the supplied evidence.", "nav_summary": "Terminal · Source inspection",
                                           "outcomes": {"can": "Inspect a supplied source before deciding what it supports.", "will": ["Read the file.", "Keep an unsupported claim unresolved."]}, "pages": pages, "download_dirs": ["shared/case"]})
        (boot / "README.md").write_text("# Synthetic publication test\n\nInspect the supplied course.\n\n## Work through the assignments\n\n<div data-course-map></div>\n\n" + "\n\n".join(links), encoding="utf-8")
        self.save_manifest()
        self.page = boot / "module-00-example/README.md"
        self.published = self.root / "site/AI_Harness_Bootcamp_2/module-00-example/README.html"

    def save_manifest(self):
        (self.root / "course.json").write_text(json.dumps(self.course), encoding="utf-8")

    def build(self, check=False):
        with contextlib.redirect_stdout(io.StringIO()):
            return builder.build(self.root, check)

    def add_webp(self, name: str, width: int, height: int) -> str:
        (self.root / "ui" / name).write_bytes(_webp_image(width, height))
        dest = f"assets/images/{name}"
        self.course["ui_assets"].append({"source": f"ui/{name}", "dest": dest})
        return dest

    def add_home_band(self, placeholder: str = '<div data-photo-band="custody"></div>'):
        self.add_webp("hero.webp", 1672, 941)
        self.course["home_bands"] = {"custody": self.add_webp("custody.webp", 1672, 716)}
        home = self.root / "AI_Harness_Bootcamp_2/README.md"
        home.write_text(home.read_text(encoding="utf-8") + "\n\n" + placeholder + "\n", encoding="utf-8")
        self.save_manifest()

    def test_procedure_cards_pair_shells_number_steps_and_publish_outcomes(self):
        lab = self.page.parent / "lab.md"
        split = ("## Preserve the decision\n\n**Terminal: Bash or zsh, ordinary user.**\n\n```bash\necho 1; printf 'EXIT=%s\\n' \"$?\"\n```\n\n**Expected:** `EXIT=0`.\n\n**Stop:** Any other exit.\n\n**Recovery:** Rerun.\n\n"
                 "**Terminal: PowerShell, ordinary user.**\n\n```powershell\nWrite-Output 1\nWrite-Output \"EXIT=$LASTEXITCODE\"\n```\n\n**Expected:** `EXIT=0` on its own line.\n\n**Stop:** Any other exit.\n\n**Recovery:** Rerun.\n\n")
        lab.write_text(GUIDED_PROCEDURE.replace("```bash\nprintf '%s\\n' 'a < b & c'\n```\n",
                                                "```bash\nprintf '%s\\n' 'a < b & c'\n```\n\n**Terminal: PowerShell, ordinary user.**\n\n```powershell\nWrite-Output 'a < b & c'\n```\n", 1)
                       .replace("## Preserve the decision\n\n", split, 1), encoding="utf-8")
        self.build()
        tree = builder.parse_html((self.published.parent / "lab.html").read_text())
        nodes = list(tree.walk())
        pairs = [node for node in nodes if "rf-shell-pair" in node.attrs.get("class", "").split()]
        self.assertEqual(len(pairs), 2)
        shared, own = pairs
        for pair in pairs:
            panels = [node for node in pair.children if isinstance(node, builder.Node)]
            self.assertEqual([(panel.attrs["class"], panel.attrs["data-shell"], panel.attrs["data-shell-name"]) for panel in panels],
                             [("rf-shell-panel", "bash", "Bash or zsh"), ("rf-shell-panel", "powershell", "PowerShell")])
            self.assertEqual([panel.children[0].attrs["class"] for panel in panels], ["rf-command", "rf-command"])
            self.assertEqual([panel.children[0].children[0].attrs.get("class") for panel in panels], ["rf-command-head", "rf-command-head"])
        self.assertEqual([len([child for child in panel.children if isinstance(child, builder.Node)]) for panel in shared.children if isinstance(panel, builder.Node)], [1, 1])
        own_panels = [panel for panel in own.children if isinstance(panel, builder.Node)]
        self.assertEqual([[child.attrs.get("class") for child in panel.children if isinstance(child, builder.Node)] for panel in own_panels],
                         [["rf-command", "rf-callout rf-callout--expected", "rf-callout rf-callout--stop", "rf-callout rf-callout--recovery"]] * 2)
        self.assertEqual([node.attrs["class"] for node in nodes if node.attrs.get("class", "").startswith("rf-callout ")],
                         ["rf-callout rf-callout--expected", "rf-callout rf-callout--stop"] + ["rf-callout rf-callout--expected", "rf-callout rf-callout--stop", "rf-callout rf-callout--recovery"] * 2)
        steps = [node for node in nodes if "data-step-index" in node.attrs]
        self.assertEqual([(node.attrs["data-step-id"], node.attrs["data-step-index"]) for node in steps], [("read-a-file", "1"), ("preserve-the-decision", "2")])
        self.assertEqual([node.text() for node in nodes if node.attrs.get("class") == "rf-step-number"], ["1", "2"])
        self.assertEqual([node.attrs["data-step-done"] for node in nodes if "data-step-done" in node.attrs], ["read-a-file", "preserve-the-decision"])
        self.assertEqual(next(node for node in nodes if "data-progress" in node.attrs).attrs["data-step-total"], "2")
        self.assertEqual(len([node for node in nodes if node.attrs.get("class") == "rf-callout rf-callout--expected"]), 3)
        data = json.loads(next(node.text() for node in nodes if node.attrs.get("id") == "rf-page-data"))
        self.assertEqual(next(page for page in data["pages"] if page["path"].endswith("module-00-example/lab.html"))["steps"], ["read-a-file", "preserve-the-decision"])
        overview = builder.parse_html(self.published.read_text())
        self.assertEqual(next(node.text() for node in overview.walk() if node.attrs.get("class") == "rf-outcomes-can"), "Inspect a supplied source before deciding what it supports.")
        self.assertEqual(next(node for node in overview.walk() if "data-module-progress" in node.attrs).attrs["data-step-total"], "2")
        home = builder.parse_html((self.root / "site/index.html").read_text())
        self.assertEqual(len([node for node in home.walk() if node.attrs.get("class") == "rf-map-outcome"]), 11)

    def test_authored_step_numbers_win_over_sequential_labels(self):
        lab = self.page.parent / "lab.md"
        lab.write_text(GUIDED_PROCEDURE.replace("## Preserve the decision", "## 4. Preserve the decision", 1), encoding="utf-8")
        self.build()
        tree = builder.parse_html((self.published.parent / "lab.html").read_text())
        nodes = list(tree.walk())
        headings = [node for node in nodes if node.tag == "h2" and node.attrs.get("id") in {"read-a-file", "4-preserve-the-decision"}]
        self.assertEqual([(node.attrs["id"], node.children[0].text(), node.text()) for node in headings],
                         [("read-a-file", "·", "·Read a file"), ("4-preserve-the-decision", "4", "4Preserve the decision")])
        checks = [node for node in nodes if "data-step-done" in node.attrs]
        self.assertEqual([node.attrs["aria-label"] for node in checks], ["Done: Read a file", "Step 4 done: Preserve the decision"])
        lab.write_text(GUIDED_PROCEDURE, encoding="utf-8")
        self.build()
        tree = builder.parse_html((self.published.parent / "lab.html").read_text())
        self.assertEqual([node.text() for node in tree.walk() if node.attrs.get("class") == "rf-step-number"], ["1", "2"])

    def test_home_band_renders_decorative_image_with_relative_src(self):
        self.add_home_band()
        self.course["index"]["dest"] = "home/index.html"
        self.save_manifest()
        self.build()
        tree = builder.parse_html((self.root / "site/home/index.html").read_text(encoding="utf-8"))
        bands = [node for node in tree.walk() if "rf-band" in node.attrs.get("class", "").split()]
        self.assertEqual(len(bands), 1)
        band = bands[0]
        self.assertEqual(band.tag, "figure")
        self.assertEqual(band.attrs, {"class": "rf-band sc-photo", "data-sc-theme": "dark"})
        self.assertEqual(len(band.children), 1)
        image = band.children[0]
        self.assertEqual(image.tag, "img")
        self.assertEqual(image.attrs, {"class": "rf-band-image", "src": "../assets/images/custody.webp",
                                      "width": "1672", "height": "716", "alt": "", "loading": "lazy", "decoding": "async"})
        self.assertFalse(any("data-figure-open" in node.attrs or "rf-figure" in node.attrs.get("class", "").split() for node in tree.walk()))
        search = (self.root / "site/assets/search-index.json").read_text(encoding="utf-8")
        self.assertNotIn("custody", search)
        self.assertEqual(self.build(check=True), 0)

    def test_hero_renders_intrinsic_webp_dimensions(self):
        self.add_webp("hero.webp", 1672, 941)
        self.save_manifest()
        self.build()
        tree = builder.parse_html((self.root / "site/index.html").read_text(encoding="utf-8"))
        image = next(node for node in tree.walk() if node.attrs.get("class") == "rf-hero-image")
        self.assertEqual((image.attrs["width"], image.attrs["height"]), ("1672", "941"))
        self.assertEqual(image.attrs["src"], "assets/images/hero.webp")

    def test_unknown_home_band_placeholder_fails(self):
        self.add_home_band('<div data-photo-band="unknown"></div>')
        with self.assertRaises(ValueError):
            self.build()

    def test_unused_home_band_fails(self):
        self.add_home_band("")
        with self.assertRaises(ValueError):
            self.build()

    def test_duplicate_home_band_placeholder_fails(self):
        self.add_home_band('<div data-photo-band="custody"></div>\n\n<div data-photo-band="custody"></div>')
        with self.assertRaises(ValueError):
            self.build()

    def test_non_home_band_placeholder_fails(self):
        self.add_home_band()
        self.page.write_text(PROCEDURE + '\n\n<div data-photo-band="custody"></div>\n', encoding="utf-8")
        with self.assertRaises(ValueError):
            self.build()

    def test_nonempty_home_band_placeholder_fails(self):
        self.add_home_band("")
        home = self.root / "AI_Harness_Bootcamp_2/README.md"
        original = home.read_text(encoding="utf-8")
        for content in ("Unexpected text", "<span></span>"):
            with self.subTest(content=content):
                home.write_text(original + f'\n<div data-photo-band="custody">{content}</div>\n', encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.build()

    def test_home_band_without_declaration_fails(self):
        self.add_home_band()
        del self.course["home_bands"]
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()

    def test_unlisted_home_band_destination_fails(self):
        self.add_home_band()
        self.course["home_bands"]["custody"] = "assets/images/unlisted.webp"
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()

    def test_shared_home_band_destination_fails(self):
        self.add_home_band('<div data-photo-band="custody"></div>\n\n<div data-photo-band="route"></div>')
        self.course["home_bands"]["route"] = self.course["home_bands"]["custody"]
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()

    def test_invalid_home_band_manifest_fails(self):
        self.add_home_band()
        for bands in ([], {"Bad-ID": "assets/images/custody.webp"}, {"custody": "assets/course.css"}, {"custody": "assets/images/hero.webp"}):
            with self.subTest(bands=bands):
                self.course["home_bands"] = bands
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.build()

    def test_rendered_links_raw_inputs_commands_and_accessible_tables(self):
        self.build()
        document = self.published.read_text(encoding="utf-8")
        tree = builder.parse_html(document)
        commands = [node for node in tree.walk() if "data-command" in node.attrs]
        self.assertEqual([node.text() for node in commands], ["printf '%s\\n' 'a < b & c'\n"])
        self.assertIn('href="shared/case/SOURCE.md"', document)
        self.assertIn('href="AI_Harness_Bootcamp_2/module-00-example/README.html"', (self.root / "site/index.html").read_text())
        self.assertEqual(len([node for node in tree.walk() if node.tag == "caption"]), 1)
        self.assertTrue(all(node.attrs.get("scope") == "col" for node in tree.walk() if node.tag == "th"))
        self.assertEqual(self.build(check=True), 0)

    def test_check_missing_site_and_raw_tampering_fail_without_writing(self):
        with self.assertRaises(ValueError):
            self.build(check=True)
        self.assertFalse((self.root / "site").exists())
        self.build()
        raw = self.published.parent / "shared/case/SOURCE.md"
        raw.write_text("tampered", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.build(check=True)
        self.assertEqual(raw.read_text(), "tampered")

    def test_png_and_svg_figures_publish_dimensions_lazy_loading_and_full_size_links(self):
        figures = {
            "workflow.png": (_png_image(257, 3), "257", "3"),
            "sized.svg": (b'<svg xmlns="http://www.w3.org/2000/svg" width="37" height="19"></svg>', "37", "19"),
            "viewbox.svg": (b'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 53 29"></svg>', "53", "29"),
        }
        (self.page.parent / "figures").mkdir()
        entries = self.course["modules"][0]["figures"] = []
        additions = []
        for name, (data, width, height) in figures.items():
            (self.page.parent / "figures" / name).write_bytes(data)
            entries.append({"source": f"figures/{name}", "dest": f"figures/published-{name}"})
            additions.append(f"![Diagram {name}](figures/{name})")
        self.page.write_text(PROCEDURE + "\n\n" + "\n\n".join(additions), encoding="utf-8")
        self.save_manifest()
        self.build()
        tree = builder.parse_html(self.published.read_text(encoding="utf-8"))
        wrappers = [node for node in tree.walk() if "rf-figure" in node.attrs.get("class", "").split()]
        self.assertEqual(len(wrappers), len(figures))
        for wrapper, (name, (data, width, height)) in zip(wrappers, figures.items()):
            with self.subTest(name=name):
                image = next(node for node in wrapper.walk() if node.tag == "img")
                link = next(node for node in wrapper.walk() if node.tag == "a")
                self.assertEqual((image.attrs["width"], image.attrs["height"]), (width, height))
                self.assertEqual(image.attrs["loading"], "lazy")
                self.assertEqual(image.attrs["alt"], f"Diagram {name}")
                self.assertEqual(image.attrs["src"], f"figures/published-{name}")
                self.assertEqual(link.attrs["href"], image.attrs["src"])
                self.assertIn("data-figure-open", link.attrs)
                self.assertEqual((self.published.parent / link.attrs["href"]).read_bytes(), data)
        self.assertEqual(self.build(check=True), 0)

    def test_malformed_png_figures_fail_before_publication(self):
        (self.page.parent / "figures").mkdir()
        figure = self.page.parent / "figures/broken.png"
        self.course["modules"][0]["figures"] = [{"source": "figures/broken.png", "dest": "figures/broken.png"}]
        self.page.write_text(PROCEDURE + "\n\n![Workflow](figures/broken.png)\n", encoding="utf-8")
        self.save_manifest()
        valid = _png_image(2, 3)
        variants = {
            "signature": b"not PNG!" + valid[8:],
            "first chunk": valid[:12] + b"IDAT" + valid[16:],
            "short IHDR length": valid[:8] + (12).to_bytes(4, "big") + valid[12:],
            "long IHDR length": valid[:8] + (14).to_bytes(4, "big") + valid[12:],
            "checksum": valid[:29] + bytes(byte ^ 0xff for byte in valid[29:33]) + valid[33:],
        }
        for length in (0, 7, 8, 15, 23, 24, 28, 29, 32):
            variants[f"truncated at {length}"] = valid[:length]
        for offset, value in ((0, 0), (4, 0), (0, 0x80000000), (4, 0x80000000), (0, 0xffffffff), (4, 0xffffffff)):
            header = bytearray(valid[16:29])
            header[offset:offset + 4] = value.to_bytes(4, "big")
            variants[f"dimension {offset}={value}"] = valid[:8] + _png_chunk(b"IHDR", header) + valid[33:]
        for offset, value in ((8, 3), (9, 1), (10, 1), (11, 1), (12, 2)):
            header = bytearray(valid[16:29])
            header[offset] = value
            variants[f"IHDR field {offset}={value}"] = valid[:8] + _png_chunk(b"IHDR", header) + valid[33:]
        for label, data in variants.items():
            with self.subTest(case=label):
                figure.write_bytes(data)
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse((self.root / "site").exists())

    def test_duplicate_destinations_and_escaping_paths_fail(self):
        self.course["modules"][0]["pages"].append({"source": "README.md", "dest": "README.html", "kind": "reference"})
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((self.root / "site").exists())
        for path in ("../outside", "/outside", "C:thing", "a\\b"):
            with self.subTest(path=path), self.assertRaises(ValueError):
                builder.safe_relative(path)

    def test_unlisted_staff_links_and_active_html_fail_before_publication(self):
        for addition in ("\n[Staff](reference/REFERENCE.md)\n", "\n<script>alert('unsafe')</script>\n", '\n<img src="shared/case/SOURCE.md" onerror="alert(1)">\n'):
            with self.subTest(addition=addition):
                self.page.write_text(PROCEDURE + addition, encoding="utf-8")
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse((self.root / "site").exists())

    def test_broken_anchor_and_unlisted_output_are_rejected(self):
        self.page.write_text(PROCEDURE + "\n[Missing](#missing)\n", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.build()
        self.page.write_text(PROCEDURE, encoding="utf-8")
        self.build()
        stray = self.root / "site/private.txt"
        stray.write_text("preserve me", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.build()
        self.assertEqual(stray.read_text(), "preserve me")

    def test_symlinked_data_cannot_escape_the_public_allowlist(self):
        outside = self.root / "outside-secret.txt"
        outside.write_text("secret", encoding="utf-8")
        (self.page.parent / "shared/case/link.txt").symlink_to(outside)
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((self.root / "site").exists())

    def test_ui_dependencies_resolve_at_root_and_prefix_mounts(self):
        from urllib.parse import urljoin
        self.build()
        for path in ("index.html", "AI_Harness_Bootcamp_2/module-00-example/lab.html"):
            tree = builder.parse_html((self.root / "site" / path).read_text())
            data = json.loads(next(node.text() for node in tree.walk() if node.attrs.get("id") == "rf-page-data"))
            assets = [node.attrs.get("href", node.attrs.get("src")) for node in tree.walk() if node.tag in {"link", "script"} and ("src" in node.attrs or "href" in node.attrs)]
            for prefix in ("/", "/reformation/site/"):
                base = "https://example.test" + prefix
                for value in assets:
                    self.assertTrue(urljoin(base + path, value).startswith(base + "assets/"))
                self.assertEqual(urljoin(base + path, data["root"] + "assets/search-index.json"), base + "assets/search-index.json")
                self.assertTrue(all(urljoin(base, item["overview"]).startswith(base) for item in data["modules"]))

    def test_invalid_ui_sources_fail_before_writing(self):
        entry = self.course["ui_assets"][0]
        original = entry["source"]
        for source in ("ui/missing.css", "../outside.css", "staff/private.css"):
            with self.subTest(source=source):
                entry["source"] = source
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse((self.root / "site").exists())
        entry["source"] = original
        (self.root / original).unlink()
        (self.root / original).symlink_to(self.root / "ui/theme-init.js")
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()
        self.assertFalse((self.root / "site").exists())

    def test_missing_or_network_css_dependencies_are_rejected(self):
        for value in ("missing.svg", "../../outside.svg", "https://example.test/texture.svg", "//example.test/font.woff2"):
            with self.subTest(value=value):
                (self.root / "ui/course.css").write_text(f"body {{ background: url('{value}'); }}")
                with self.assertRaises(ValueError):
                    self.build()
                self.assertFalse((self.root / "site").exists())

    def test_guided_groups_keep_commands_context_fragments_and_optional_boundaries(self):
        self.build()
        original = builder.parse_html(builder.markdown.markdown(
            GUIDED_PROCEDURE, extensions=["fenced_code", "tables", "toc", "md_in_html"],
            extension_configs={"tables": {"use_align_attribute": True}},
        ))
        original_ids = {node.attrs["id"] for node in original.walk() if "id" in node.attrs}
        tree = builder.parse_html((self.published.parent / "lab.html").read_text())
        nodes = list(tree.walk())
        self.assertTrue(original_ids.issubset({node.attrs["id"] for node in nodes if "id" in node.attrs}))
        steps = [node for node in nodes if "data-step-id" in node.attrs]
        self.assertEqual([node.attrs["data-step-id"] for node in steps], ["read-a-file", "preserve-the-decision"])
        first = list(steps[0].walk())
        self.assertEqual([node.text() for node in first if "data-command" in node.attrs], ["printf '%s\\n' 'a < b & c'\n"])
        self.assertEqual([node.text() for node in first if node.tag == "p" and node.text().startswith(("Terminal:", "Expected:", "Stop:"))], [
            "Terminal: Bash or zsh, ordinary user.",
            "Expected: You see the literal comparison text.",
            "Stop: If the command fails, keep the error. Recovery: Correct the path and rerun.",
        ])
        stretch = next(node for node in nodes if "rf-stretch" in node.attrs.get("class", "").split())
        self.assertFalse(any("data-step-id" in node.attrs for node in stretch.walk()))
        self.assertNotIn("The continuation remains", stretch.text())
        self.assertTrue(all("hidden" not in node.attrs for step in steps for node in step.walk()))
        data = json.loads(next(node.text() for node in nodes if node.attrs.get("id") == "rf-page-data"))
        self.assertEqual([step["id"] for step in data["steps"]], ["read-a-file", "preserve-the-decision"])

    def test_invalid_guide_anchors_are_rejected(self):
        lab = self.page.parent / "lab.md"
        guide = self.course["modules"][0]["pages"][1]["guide"]
        for anchors in (["missing"], ["read-a-file", "read-a-file"]):
            guide["context_sections"] = anchors
            self.save_manifest()
            with self.assertRaises(ValueError):
                self.build()
        self.assertFalse((self.root / "site").exists())

    def test_search_contains_lesson_prose_not_raw_private_or_fenced_bytes(self):
        (self.root / "staff").mkdir()
        (self.root / "staff/private.md").write_text("PRIVATE_SENTINEL_d839c")
        self.build()
        text = (self.root / "site/assets/search-index.json").read_text()
        index = json.loads(text)
        self.assertIn("Read the supplied source before deciding what it supports.", text)
        self.assertNotIn("RAW_CASE_SENTINEL_8f341", text)
        self.assertNotIn("PRIVATE_SENTINEL_d839c", text)
        self.assertNotIn("printf", text)
        self.assertNotIn("a < b & c", text)
        page = next(page for page in index["pages"] if page["path"].endswith("module-00-example/lab.html"))
        optional = next(section for section in page["sections"] if section["id"] == "compare-the-second-source")
        self.assertTrue(optional["optional"])
        self.assertEqual(sum(section["text"].count("This is optional authored lesson prose") for section in page["sections"]), 1)
        self.assertEqual({page["path"] for page in index["pages"]}, {p.relative_to(self.root / "site").as_posix() for p in (self.root / "site").rglob("*.html")})

    def test_generated_search_and_style_tampering_fail_without_writing(self):
        self.build()
        for relative in ("assets/search-index.json", "assets/course.css"):
            path = self.root / "site" / relative
            original = path.read_bytes()
            path.write_bytes(b"tampered generated asset")
            with self.assertRaises(ValueError):
                self.build(check=True)
            self.assertEqual(path.read_bytes(), b"tampered generated asset")
            path.write_bytes(original)

    def test_page_metadata_contract_rejects_missing_roles_and_home_placeholders(self):
        self.course["modules"][0]["case_name"] = ""
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()
        self.course["modules"][0]["case_name"] = "Example"
        self.course["modules"][0]["pages"][1]["kind"] = "reference"
        self.save_manifest()
        with self.assertRaises(ValueError):
            self.build()
        self.course["modules"][0]["pages"][1]["kind"] = "lab"
        self.save_manifest()
        home = self.root / "AI_Harness_Bootcamp_2/README.md"
        original = home.read_text()
        for text in (original.replace("<div data-course-map></div>", ""), original + "\n<div data-course-map></div>\n"):
            home.write_text(text)
            with self.assertRaises(ValueError):
                self.build()
        self.assertFalse((self.root / "site").exists())

    def test_unguided_lab_publishes_mixed_content_without_fake_progress(self):
        module = self.course["modules"][0]
        del module["outcomes"]
        del module["pages"][1]["guide"]
        (self.page.parent / "figures").mkdir()
        (self.page.parent / "figures/flow.png").write_bytes(_png_image(40, 20))
        module["figures"] = [{"source": "figures/flow.png", "dest": "figures/flow.png"}]
        prompt = "Help me run this exercise using the supplied tools.\n  Keep this indented line, a < b & c, unchanged.\n"
        (self.page.parent / "lab.md").write_text(
            "# Mixed lesson\n\nWhy this page exists, in plain prose.\n\n## Background\n\nSome explanation.\n\n### A detail\n\nMore explanation.\n\n"
            "```\nunlabeled sample\n```\n\n**In Oh My Pi:**\n\n```text\n" + prompt + "```\n\n```bash\nprintf 'no card rhetoric\\n'\n```\n\n"
            "![A labelled flow](figures/flow.png)\n\n<details><summary>More detail</summary><p>Ordinary disclosure text.</p></details>\n\n"
            "## Next idea\n\nClosing prose.\n\n<details class=\"rf-stretch\" markdown=\"1\">\n<summary>Optional stretch: go further</summary>\n\n## Further work\n\nOptional prose.\n\n</details>\n",
            encoding="utf-8")
        self.save_manifest()
        self.build()
        lab = (self.published.parent / "lab.html").read_text(encoding="utf-8")
        nodes = list(builder.parse_html(lab).walk())
        self.assertTrue({"background", "a-detail", "next-idea", "further-work", "rf-stretch"} <= {node.attrs.get("id") for node in nodes})
        pres = [node for node in nodes if node.tag == "pre"]
        self.assertEqual([next(child for child in pre.children if isinstance(child, builder.Node)).text() for pre in pres],
                         ["unlabeled sample\n", prompt, "printf 'no card rhetoric\\n'\n"])
        self.assertEqual([pre.attrs.get("data-command") for pre in pres], [None, None, "bash"])
        self.assertFalse(any("rf-command" in node.attrs.get("class", "").split() for node in nodes))
        for marker in ("data-step-id", "data-step-done", "data-progress"):
            self.assertFalse(any(marker in node.attrs for node in nodes), marker)
        self.assertFalse(any(node.attrs.get("id") == "rf-reader-controls" or node.attrs.get("class") == "rf-outcome-line" for node in nodes))
        rail = next(node for node in nodes if node.attrs.get("id") == "rf-outline")
        self.assertEqual((rail.attrs["aria-label"], rail.attrs.get("class")), ("On this page", None))
        image = next(node for node in nodes if node.tag == "img")
        self.assertEqual((image.attrs["alt"], image.attrs["width"], image.attrs["height"]), ("A labelled flow", "40", "20"))
        disclosure = next(node for node in nodes if node.tag == "details" and any(isinstance(child, builder.Node) and child.tag == "summary" and child.text() == "More detail" for child in node.children))
        self.assertIn("Ordinary disclosure text.", disclosure.text())
        data = json.loads(next(node.text() for node in nodes if node.attrs.get("id") == "rf-page-data"))
        self.assertEqual(data["steps"], [])
        self.assertNotIn(data["page"], data["resume"])
        overview = self.published.read_text(encoding="utf-8")
        for document in (lab, overview):
            self.assertNotIn("0 steps", document)
        self.assertNotIn("rf-outcomes", overview)
        self.assertNotIn("data-module-progress", overview)
        home = builder.parse_html((self.root / "site/index.html").read_text(encoding="utf-8"))
        self.assertEqual(len([node for node in home.walk() if node.attrs.get("class") == "rf-map-outcome"]), 10)
        search = json.loads((self.root / "site/assets/search-index.json").read_text(encoding="utf-8"))
        sections = next(page for page in search["pages"] if page["path"] == data["page"])["sections"]
        self.assertTrue(next(section for section in sections if section["id"] == "further-work")["optional"])
        self.assertEqual(self.build(check=True), 0)

    def test_optional_outcomes_render_only_their_content(self):
        long_can = "Explain " + "a supported capability in detail, " * 12 + "and then name what remains open."
        self.assertGreater(len(long_can), 320)
        cases = {
            "can only": {"can": long_can},
            "will only": {"will": ["Read the OPENROUTER_API_KEY guidance before the VERIFY: checks in Module 4."]},
            "many activities": {"can": "Inspect the source.", "will": [f"Activity {number}." for number in range(6)]},
            "one activity": {"can": "Inspect the source.", "will": ["Only one activity."]},
            "blank": {"can": "  ", "will": []},
        }
        for label, outcomes in cases.items():
            with self.subTest(case=label):
                self.course["modules"][0]["outcomes"] = outcomes
                self.save_manifest()
                self.build()
                can, will = outcomes.get("can", "").strip(), outcomes.get("will", [])
                nodes = list(builder.parse_html(self.published.read_text(encoding="utf-8")).walk())
                text = lambda css: [node.text() for node in nodes if node.attrs.get("class") == css]
                self.assertEqual(text("rf-outcomes-can"), [can] if can else [])
                self.assertEqual([node.text() for node in nodes if node.tag == "li" and node.attrs == {} and will and node.text() in will], will)
                self.assertEqual(len(text("rf-outcomes-sub")), 1 if can and will else 0)
                expected_title = "After this assignment you can" if can else "You will" if will else None
                self.assertEqual(next((node.text() for node in nodes if node.attrs.get("id") == "rf-outcomes-title"), None), expected_title)
                outline_links = [node.text() for node in nodes if node.tag == "a" and node.attrs.get("href") == "#rf-outcomes-title"]
                self.assertEqual(outline_links, [expected_title] * 2 if expected_title else [])
                lab = builder.parse_html((self.published.parent / "lab.html").read_text(encoding="utf-8"))
                self.assertEqual(len([node for node in lab.walk() if node.attrs.get("class") == "rf-outcome-line"]), 1 if can else 0)
                home = builder.parse_html((self.root / "site/index.html").read_text(encoding="utf-8"))
                self.assertEqual(len([node for node in home.walk() if node.attrs.get("class") == "rf-map-outcome"]), 11 if can else 10)
        for bad in (None, [], {"can": 3}, {"will": "Read the file."}, {"will": ["Fine.", " "]}, {"can": "Fine.", "extra": "x"}):
            with self.subTest(outcomes=bad):
                self.course["modules"][0]["outcomes"] = bad
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.build()

    def test_explicit_guides_without_steps_stay_readable_and_reference_steps_count(self):
        module = self.course["modules"][0]
        module["pages"][1]["guide"] = {"context_sections": ["read-a-file", "preserve-the-decision"]}
        (self.page.parent / "sheet.md").write_text("# Prompt sheet\n\nUse these when you are ready.\n\n## First prompt\n\nCopy it.\n\n## Second prompt\n\nCopy this one too.\n", encoding="utf-8")
        (self.page.parent / "plain.md").write_text("# Plain guided page\n\nOnly prose, without any second-level heading.\n", encoding="utf-8")
        module["pages"] += [{"source": "sheet.md", "dest": "sheet.html", "kind": "reference", "guide": {}},
                            {"source": "plain.md", "dest": "plain.html", "kind": "reference", "guide": {}}]
        self.save_manifest()
        self.build()
        parse = lambda name: list(builder.parse_html((self.published.parent / name).read_text(encoding="utf-8")).walk())
        for name in ("lab.html", "plain.html"):
            with self.subTest(page=name):
                nodes = parse(name)
                self.assertFalse(any("data-step-id" in node.attrs or "data-progress" in node.attrs or node.attrs.get("id") == "rf-reader-controls" for node in nodes))
                self.assertEqual(next(node for node in nodes if node.attrs.get("id") == "rf-outline").attrs["aria-label"], "On this page")
                self.assertFalse(any("hidden" in node.attrs for node in nodes if node.attrs.get("class") == "rf-context-body"))
        lab = parse("lab.html")
        self.assertEqual([node.attrs["data-context-id"] for node in lab if "data-context-id" in node.attrs], ["read-a-file", "preserve-the-decision"])
        self.assertEqual([node.text() for node in lab if "data-command" in node.attrs], ["printf '%s\\n' 'a < b & c'\n"])
        sheet = parse("sheet.html")
        self.assertEqual([node.attrs["data-step-id"] for node in sheet if "data-step-id" in node.attrs], ["first-prompt", "second-prompt"])
        self.assertTrue(any(node.attrs.get("id") == "rf-reader-controls" for node in sheet))
        self.assertEqual(next(node for node in sheet if "data-progress" in node.attrs).attrs["data-step-total"], "2")
        self.assertEqual(next(node for node in sheet if node.attrs.get("id") == "rf-outline").attrs["aria-label"], "Steps")
        data = json.loads(next(node.text() for node in sheet if node.attrs.get("id") == "rf-page-data"))
        self.assertEqual({page["path"].rsplit("/", 1)[1]: page["steps"] for page in data["pages"] if page["moduleId"] == "00"},
                         {"README.html": [], "lab.html": [], "sheet.html": ["first-prompt", "second-prompt"], "plain.html": []})
        self.assertEqual({path.rsplit("/", 1)[1] for path in data["resume"] if "/module-00-example/" in path}, {"sheet.html"})
        overview = parse("README.html")
        self.assertEqual(next(node for node in overview if "data-module-progress" in node.attrs).attrs["data-step-total"], "2")
        for bad in (None, {"steps": []}, {"context_sections": "read-a-file"}):
            with self.subTest(guide=bad):
                module["pages"][1]["guide"] = bad
                self.save_manifest()
                with self.assertRaises(ValueError):
                    self.build()

    def test_hero_and_band_publish_their_actual_dimensions(self):
        self.add_webp("hero.webp", 800, 600)
        self.course["home_bands"] = {"custody": self.add_webp("custody.webp", 960, 480)}
        home = self.root / "AI_Harness_Bootcamp_2/README.md"
        home.write_text(home.read_text(encoding="utf-8") + '\n\n<div data-photo-band="custody"></div>\n', encoding="utf-8")
        self.save_manifest()
        self.build()
        tree = builder.parse_html((self.root / "site/index.html").read_text(encoding="utf-8"))
        images = {node.attrs["class"]: (node.attrs["width"], node.attrs["height"]) for node in tree.walk() if node.tag == "img"}
        self.assertEqual(images, {"rf-hero-image": ("800", "600"), "rf-band-image": ("960", "480")})
        self.assertEqual(self.build(check=True), 0)

    def test_allowlisted_supplementary_reference_page_links_and_is_searchable(self):
        module = self.course["modules"][0]
        (self.page.parent / "shared/PROMPTS.md").write_text("# Prompt sheet\n\nEvery prompt for this assignment, collected for printing.\n", encoding="utf-8")
        module["pages"].append({"source": "shared/PROMPTS.md", "dest": "shared/PROMPTS.html", "kind": "reference"})
        (self.page.parent / "lab.md").write_text(GUIDED_PROCEDURE + "\n[Prompt sheet](shared/PROMPTS.md)\n", encoding="utf-8")
        self.save_manifest()
        self.build()
        self.assertIn('href="shared/PROMPTS.html"', (self.published.parent / "lab.html").read_text(encoding="utf-8"))
        search = json.loads((self.root / "site/assets/search-index.json").read_text(encoding="utf-8"))
        page = next(page for page in search["pages"] if page["path"].endswith("module-00-example/shared/PROMPTS.html"))
        self.assertEqual((page["kind"], page["moduleId"]), ("reference", "00"))
        self.assertIn("Every prompt for this assignment, collected for printing.", " ".join(section["text"] for section in page["sections"]))
        self.assertEqual(self.build(check=True), 0)


if __name__ == "__main__":
    unittest.main()
