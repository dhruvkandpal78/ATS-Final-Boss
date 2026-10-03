from pathlib import Path
import sys
import unittest
from html.parser import HTMLParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.build_public_preview import COPY_MAP, ROOT, export_preview


class ControlReader(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.controls = {}
        self.sample_controls = []
        self.banner_seen = False
        self.body_seen = False
        self.header_after_banner = False

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        element_id = attributes.get("id")
        if element_id:
            self.controls[element_id] = (tag, attributes)
        if "data-sample-line" in attributes:
            self.sample_controls.append(attributes)
        if tag == "body":
            self.body_seen = True
        if element_id == "static-preview-banner":
            self.banner_seen = self.body_seen
        if tag == "header":
            self.header_after_banner = self.banner_seen


def cleanup_output(output, *, flat=False):
    # Explicitly remove this test's known files; never recursively clean a path.
    targets = ([Path(name).name for name in COPY_MAP.values()] if flat else list(COPY_MAP.values()))
    for relative in [*targets, "README.md"]:
        candidate = output / relative
        if candidate.is_file():
            candidate.unlink()
    for folder in (output / "assets", output):
        if folder.is_dir() and not any(folder.iterdir()):
            folder.rmdir()


class PublicPreviewTests(unittest.TestCase):
    def test_export_contains_only_allowlisted_static_preview_files(self):
        output = export_preview(ROOT / ".test-tmp" / "preview-test-output")
        try:
            expected = {"README.md", *COPY_MAP.values()}
            actual = {str(path.relative_to(output)).replace("\\", "/")
                      for path in output.rglob("*") if path.is_file()}
            self.assertEqual(actual, expected)
            readme = (output / "README.md").read_text(encoding="utf-8")
            self.assertIn("sdk: static", readme)
            self.assertIn("app_file: index.html", readme)
            self.assertNotIn("license:", readme.lower())
        finally:
            cleanup_output(output)

    def test_export_disables_all_document_analysis_and_never_includes_backend(self):
        output = export_preview(ROOT / ".test-tmp" / "preview-test-analysis")
        try:
            html = (output / "index.html").read_text(encoding="utf-8")
            script = (output / "assets" / "preview.js").read_text(encoding="utf-8")
            self.assertIn('src="assets/preview.js"', html)
            self.assertNotIn('src="/assets/app.js"', html)
            self.assertIn("no analysis backend", script)
            self.assertNotIn("fetch(", script)
            self.assertNotIn("XMLHttpRequest", script)
            self.assertNotIn("FileReader", script)
            self.assertIn("does not accept or analyze documents", html)
            self.assertIn("does not send content to an analysis server", html)
            self.assertIn("resume-file", html)
            self.assertIn("resume-text", html)
            reader = ControlReader()
            reader.feed(html)
            for control_id in (
                "resume-file", "resume-text", "sample-select", "tab-text", "tab-pdf",
                "submit-analysis", "cancel-analysis", "clear-input", "remove-file",
            ):
                self.assertIn("disabled", reader.controls[control_id][1], control_id)
            self.assertFalse(reader.sample_controls)
            self.assertNotIn("analyze-sample", reader.controls)
            self.assertNotIn("explore-sample", reader.controls)
            self.assertNotIn("disabled", reader.controls["theme-toggle"][1])
            self.assertNotIn("disabled", reader.controls["menu-toggle"][1])
            self.assertTrue(reader.banner_seen)
            self.assertTrue(reader.header_after_banner)
            self.assertIn("disabled = true", script)
            self.assertIn("addEventListener('submit'", script)
            self.assertFalse(any(path.suffix.lower() == ".pdf" for path in output.rglob("*")))
            self.assertFalse(any("models" in path.parts or "results" in path.parts
                                 for path in output.rglob("*")))
        finally:
            cleanup_output(output)

    def test_flat_export_places_allowlisted_files_at_root_with_relative_assets(self):
        output = export_preview(ROOT / ".test-tmp" / "preview-test-flat", flat=True)
        try:
            expected = {"README.md", *(Path(name).name for name in COPY_MAP.values())}
            actual = {path.name for path in output.iterdir() if path.is_file()}
            self.assertEqual(actual, expected)
            self.assertEqual(len(actual), len(COPY_MAP) + 1)
            html = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('href="style.css"', html)
            self.assertIn('src="theme.js"', html)
            self.assertIn('src="preview.js"', html)
            for name in ("gsap.min.js", "ScrollTrigger.min.js", "SplitText.min.js", "pipeline-timeline.js"):
                self.assertIn(f'src="{name}"', html)
                self.assertTrue((output / name).is_file())
            self.assertFalse((output / "assets").exists())
        finally:
            cleanup_output(output, flat=True)

    def test_export_refuses_existing_output_and_paths_outside_workspace(self):
        output = ROOT / ".test-tmp" / "preview-test-existing"
        output.mkdir(parents=True)
        try:
            with self.assertRaises(FileExistsError):
                export_preview(output)
        finally:
            output.rmdir()
        with self.assertRaises(ValueError):
            export_preview(ROOT.parent / "outside-public-preview")


if __name__ == "__main__":
    unittest.main()
