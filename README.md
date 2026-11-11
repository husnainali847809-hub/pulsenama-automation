# Biz Pakistan Auto Publisher

Automated worldwide news review and publishing to Facebook through Buffer, with strong Pakistan coverage.

## Coverage

The feed collector searches multiple categories and regions, including breaking and world news, Pakistan, politics, business and economy, technology and AI, cricket, football and other sports, entertainment, science, health, and education. Cricket is a dedicated category; coverage is not limited to cricket or Pakistan-only stories.

The publisher reviews fresh candidates, removes duplicates, balances categories against recent posting history, and queues up to the configured per-run and daily limits. No automated news system can guarantee that every story from every publisher is captured.

## Facebook post design

Each Feed and Story graphic uses a real, topic-relevant photograph. The full photo is fitted into the design without cropping important people or details. A clean dark lower panel carries a readable category label and a short headline highlighted in green, with Biz Pakistan branding. The caption includes a factual summary, original news source, image attribution where required, and relevant hashtags.

The image renderer passes the headline, category, and Feed/Story layout explicitly. If a suitable real photo with verified commercial reuse rights cannot be found, the article is skipped rather than posted with a random, unrelated, or low-quality image.

## Image sources and reuse

- Article-provided images are used only when reuse rights are established.
- Openverse and Wikimedia Commons candidates are filtered for licences that permit commercial reuse.
- Pexels is optional and requires `PEXELS_API_KEY`; searches use topic-specific query variants and preserve photographer/source attribution.
- Add domains to `IMAGE_ALLOWED_DOMAINS` only when you have genuine permission to reuse images from those domains.
- Do not assume that a photo visible on another news website is free to copy.

## Required GitHub Actions secrets

- OPENROUTER_API_KEY
- BUFFER_API_KEY
- BUFFER_CHANNEL_ID
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET

Optional: `PEXELS_API_KEY` for additional licensed photo results.
