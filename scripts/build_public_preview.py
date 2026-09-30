"""Export a source-only, non-analytical static website preview."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path
import shutil


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / ".test-tmp" / "public-preview"
COPY_MAP = {
    "src/app/index.html": "index.html",
    "src/app/assets/style.css": "assets/style.css",
    "src/app/assets/theme.js": "assets/theme.js",
    "deploy/public-preview/preview.js": "assets/preview.js",
    "LICENSE": "LICENSE",
    "LICENSE-MIT-LEGACY.txt": "LICENSE-MIT-LEGACY.txt",
}
EXPECTED_SCRIPT = '<script defer src="/assets/app.js"></script>'
STATIC_SCRIPT = '<script defer src="assets/preview.js"></script>'
STATIC_BANNER = (
    '<section id="static-preview-banner" class="preview-banner" role="status">'
    '<strong>Static website preview</strong>'
    '<span>This free-hosted preview does not analyze documents. Do not enter or upload personal information.</span>'
    '</section>'
)


class _DisablePreviewControls(HTMLParser):
    """Collect start-tag edits without reserializing or otherwise changing the HTML."""

    DISABLED_IDS = {
        "resume-text", "resume-file", "sample-select", "tab-text", "tab-pdf",
        "submit-analysis", "cancel-analysis", "clear-input", "remove-file",
        "analyze-sample", "explore-sample",
    }

    def __init__(self, source: str):
        super().__init__(convert_charrefs=False)
        self.source = source
        self.lines = source.splitlines(keepends=True)
        self.line_offsets = []
        offset = 0
        for line in self.lines:
            self.line_offsets.append(offset)
            offset += len(line)
        self.edits: list[tuple[int, int, str]] = []

    def _start_tag(self, tag: str):
        raw = self.get_starttag_text()
        attrs = dict(self.get_starttag_text_attrs())
        should_disable = (
            attrs.get("id") in self.DISABLED_IDS
            or "data-sample-line" in attrs
        ) and tag in {"input", "textarea", "select", "button"}
        if should_disable and "disabled" not in attrs:
            line, column = self.getpos()
            start = self.line_offsets[line - 1] + column
            # Insert immediately before the closing bracket while preserving the tag.
            close = raw.rfind("/>")
            if close < 0:
                close = raw.rfind(">")
            self.edits.append((start + close, start + close, " disabled"))

    def get_starttag_text_attrs(self):
        # HTMLParser doesn't expose attrs for the current tag in its callback;
        # parse only this tag with a tiny nested parser and retain source bytes.
        raw = self.get_starttag_text()

        class AttrReader(HTMLParser):
            attrs = []

            def handle_starttag(self, _tag, attrs):
                self.attrs = attrs

            def handle_startendtag(self, _tag, attrs):
                self.attrs = attrs

        reader = AttrReader(convert_charrefs=False)
        reader.feed(raw)
        return reader.attrs

    def handle_starttag(self, tag, _attrs):
        self._start_tag(tag)

    def handle_startendtag(self, tag, _attrs):
        self._start_tag(tag)


def disable_preview_controls(html: str) -> str:
    parser = _DisablePreviewControls(html)
    parser.feed(html)
    parser.close()
    for start, end, replacement in reversed(parser.edits):
        html = html[:start] + replacement + html[end:]
    return html


def export_preview(output: Path, *, flat: bool = False) -> Path:
    output = output.expanduser().resolve()
    root = ROOT.resolve()
    if output == root or root not in output.parents:
        raise ValueError("Output must be a new directory inside the repository workspace")
    if output.exists():
        raise FileExistsError("Output directory already exists; choose a new path")

    copy_map = ({source: Path(target).name for source, target in COPY_MAP.items()}
                if flat else COPY_MAP)
    output.mkdir(parents=True)
    try:
        for source_name, target_name in copy_map.items():
            source = ROOT / source_name
            target = output / target_name
            target.parent.mkdir(parents=True, exist_ok=True)
            if source_name == "src/app/index.html":
                html = source.read_text(encoding="utf-8")
                if html.count(EXPECTED_SCRIPT) != 1:
                    raise ValueError("Maintained app script reference changed; review exporter before use")
                if html.count("<body>") != 1:
                    raise ValueError("Maintained document body changed; review exporter before use")
                html = html.replace(EXPECTED_SCRIPT, STATIC_SCRIPT)
                style_path = "style.css" if flat else "assets/style.css"
                theme_path = "theme.js" if flat else "assets/theme.js"
                preview_path = "preview.js" if flat else "assets/preview.js"
                html = html.replace(STATIC_SCRIPT, f'<script defer src="{preview_path}"></script>')
                html = html.replace('href="/assets/style.css"', f'href="{style_path}"')
                html = html.replace('src="/assets/theme.js"', f'src="{theme_path}"')
                html = html.replace('href="/license"', 'href="LICENSE"')
                html = html.replace('href="/license-legacy"', 'href="LICENSE-MIT-LEGACY.txt"')
                html = html.replace(
                    "Content is sent to this application’s analysis server. Upload personal information only when you are authorized to process it.",
                    "This free static website preview does not accept or analyze documents. Do not enter personal information.",
                )
                html = html.replace(
                    "Content is sent to the application server for analysis. Send personal data only with authorization. A finding describes a document pattern, not a person’s intent, character or suitability.",
                    "This static preview does not send content to an analysis server. A finding describes a document pattern, not a person’s intent, character or suitability.",
                )
                html = html.replace("<body>", "<body>" + STATIC_BANNER, 1)
                html = disable_preview_controls(html)
                target.write_text(html, encoding="utf-8")
            else:
                if source.is_symlink() or ROOT.resolve() not in source.resolve().parents:
                    raise ValueError(f"Allowlisted source is not a regular workspace file: {source_name}")
                shutil.copyfile(source, target)

        style = output / ("style.css" if flat else "assets/style.css")
        with style.open("a", encoding="utf-8", newline="") as css:
            css.write(
                "\n/* Static-host preview notice */\n"
                ".preview-banner{display:flex;justify-content:center;gap:12px;flex-wrap:wrap;"
                "padding:12px 20px;background:#302749;color:#fff;font-size:.9rem;text-align:center}\n"
                ".preview-banner strong{color:#ffd08a}\n"
                ".preview-notice{margin:24px 0;padding:24px;border:2px solid #b29bd9}\n"
                ".preview-notice h2{margin:8px 0}\n"
            )

        (output / "README.md").write_text(
            "---\n"
            "title: ATS Final Boss static preview\n"
            "sdk: static\n"
            "app_file: index.html\n"
            "---\n\n"
            "A static interface preview only. It does not analyze or upload documents.\n",
            encoding="utf-8",
        )
    except Exception:
        # Remove only the explicit files and directories created by this run.
        for target_name in [*copy_map.values(), "README.md"]:
            candidate = output / target_name
            if candidate.is_file():
                candidate.unlink()
        candidate = output / "assets"
        if candidate.is_dir() and not any(candidate.iterdir()):
            candidate.rmdir()
        if output.is_dir() and not any(output.iterdir()):
            output.rmdir()
        raise
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="new output directory inside the repository workspace")
    parser.add_argument("--flat", action="store_true",
                        help="place all seven upload files at the output root for browser-based publishing")
    args = parser.parse_args()
    print(export_preview(args.output, flat=args.flat))


if __name__ == "__main__":
    main()
