# Free static website preview

The static preview is a source-only presentation of the maintained website. It includes the existing home, methodology, research-lab and ownership views, plus the applicable rights notices. Its analysis screen is explicitly disabled: it has no analysis backend, model artifacts, PDF processing, upload path, API request, or simulated result. Do not enter or upload personal information.

## Build and publish

From the repository root, export into a new workspace directory:

```text
python scripts/build_public_preview.py --output .test-tmp/public-preview
```

The exporter refuses an existing output directory and paths outside the repository. It writes only an explicit allowlist of the maintained HTML, stylesheet, theme/preview scripts, and rights notices, plus the static-host metadata file. It does not copy datasets, model weights, results, PDFs, Git history, environment files, or the rest of the checkout. Choose an unused output directory for each export; the script does not recursively remove existing paths.

The generated `README.md` contains Hugging Face Space metadata with `sdk: static`, `app_file: index.html`, and a title; it intentionally declares no license field. Review the generated files and rights notices before publishing. Repository ownership terms state that written permission is required to reuse new original additions; hosting this preview does not grant broader commercial reuse rights.

The free Static Space is only a website preview. As of **2026-09-30**, Hugging Face's official [Docker Spaces documentation](https://huggingface.co/docs/hub/spaces-sdks-docker) describes Docker Spaces as a paid-plan creation feature; that is separate from compute pricing, where the CPU Basic hardware is listed with free hourly usage in the [Spaces hardware reference](https://huggingface.co/docs/hub/spaces-overview#hardware). This static export therefore does not provide the Python analysis service. A hosted analysis backend is a separate deployment decision with its own customer security, privacy, rights, and operating gates; do not imply that the preview performs analysis.
