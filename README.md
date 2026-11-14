# Pulsenama — AI Poetry Video Creator

Pulsenama automatically creates short vertical poetry videos in Urdu, Roman Urdu, and English.

## What it does

- Chooses the mood, language, and duration automatically.
- Generates a short 2–3 line poem, with a built-in poem fallback when the AI response is unavailable.
- Finds a mood-matched portrait video or photo for the background.
- Uses a language-matched vocal song when one is available.
- If no vocal song can be fetched, creates and uses its own mood-matched piano-and-strings instrumental so video generation continues.
- Keeps a Google Drive music-loader hook in the pipeline for the planned Drive song library; the Drive connection itself is not configured yet.
- Renders a 1080×1920 MP4 and a text/attribution file.

## Automatic schedule

GitHub Actions runs four times daily at approximately **09:00, 13:00, 17:00, and 21:00 Pakistan time**. GitHub may start scheduled jobs a little later than the exact cron time. You can also run the workflow manually from **Actions → Pulsenama AI Poetry Video Creator → Run workflow**.

Each successful run creates a public GitHub Release asset for the MP4 so Buffer can access the video URL.

## Buffer setup

Add these repository Actions secrets:

- `BUFFER_API_KEY` — your Buffer API key.
- `BUFFER_CHANNEL_ID` — the Buffer channel where videos should be queued.

When both are configured, each generated video is sent to that channel using Buffer's **Add to Queue** mode. Buffer then uses the channel's configured queue schedule. If either secret is missing, video generation still completes and the workflow logs that Buffer publishing was skipped.

## Other required secrets

- `OPENROUTER_API_KEY` — AI poem generation.
- `PEXELS_API_KEY` — Pexels video/photo search (optional).
- `PIXABAY_API_KEY` — Pixabay video/photo search (optional).
- `JAMENDO_CLIENT_ID` — vocal-song search (optional).

## Generated files

The workflow stores `poetry_demo.mp4` and `poetry_demo.txt` as downloadable workflow artifacts for 7 days. The MP4 is also attached to a public GitHub Release to provide Buffer with a publicly accessible media URL.
