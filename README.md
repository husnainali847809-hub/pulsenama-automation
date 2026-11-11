# Biz Pakistan Auto Publisher

Automated worldwide news review and publishing to Facebook through Buffer, with strong Pakistan coverage.

## Coverage

The feed collector searches multiple categories and regions, including breaking and world news, Pakistan, politics, business and economy, technology and AI, cricket, football and other sports, entertainment, science, health, and education. Cricket is a dedicated category; coverage is not limited to cricket or Pakistan-only stories.

The publisher reviews fresh candidates, removes duplicates, balances categories against recent posting history, and queues up to the configured per-run and daily limits. No automated news system can guarantee that every story from every publisher is captured.

## Facebook post design

Each Feed graphic uses a full-bleed landscape real photograph; each Story uses a vertical version of the same image-only design. The only overlay is the Biz Pakistan logo and channel name. No headline, category label, Breaking badge, slogan, dark text panel, gradients, or decorative graphics are placed over the photograph. The post caption carries the factual summary, original news source, image attribution where required, and relevant hashtags.

The image renderer uses separate landscape Feed and vertical Story dimensions while keeping the real photograph as the entire background. If a suitable real photo with verified commercial reuse rights cannot be found, the article is skipped rather than posted with a random, unrelated, AI-generated, or low-quality image.

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
