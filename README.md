# Pulsenama — AI Poetry Video Creator

Pulsenama creates short cinematic poetry videos in Urdu, Roman Urdu, and English.

## What it does

- Generates an original poem for the selected mood and language using OpenRouter, with built-in original poems as a fallback.
- Searches for a mood-matched portrait video from Pexels first.
- If no suitable video is available, searches for a reusable internet photo from Pexels and then Wikimedia Commons.
- Records the photo creator/licence/source in `poetry_demo.txt` where the source provides that information.
- Animates the background with a slow cinematic zoom, overlays the poem, and adds a Pulsenama watermark.
- Creates an original instrumental music bed matched to the selected mood.
- Exports a vertical 1080×1920 MP4. The GitHub Actions workflow makes the MP4 available as a downloadable artifact.

## Run it

1. Add the `OPENROUTER_API_KEY` repository secret for AI poem generation.
2. Add `PEXELS_API_KEY` for Pexels video and photo search. Without it, the script can still try Wikimedia Commons photos, but it cannot search Pexels.
3. Open **Actions → Pulsenama AI Poetry Video Creator → Run workflow**.
4. Select mood, language, and duration.
5. Download the generated MP4 from the workflow run's Artifacts section.

## Image reuse and copyright

Pulsenama does not download arbitrary images from random websites. It uses Pexels under its licence or Wikimedia Commons files whose returned licence metadata indicates CC0, Public Domain, or CC BY. Wikimedia creator, licence, and file-page information is recorded for attribution. Always review the source licence terms before commercial redistribution.

## Technical requirements

- Python 3.11+
- FFmpeg
- Python packages: `requests`, `Pillow`

## Notes

- No AI-generated background image is used. If no reusable internet image can be found, the workflow stops with an error rather than silently using an AI-generated or unlicensed image.
- The poetry workflow only creates a video artifact; it does not publish to social accounts.
