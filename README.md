# Biz Pakistan Auto Publisher

Automated news review and publishing to Facebook through Buffer.

## News image policy

Biz Pakistan uses a relevant source photograph from the news item or a verified reusable image source. It does not generate abstract AI images or publish random images just to fill a post.

Each selected photo receives gentle professional enhancement for clearer detail, natural contrast, and richer depth. This creates a more dimensional, polished appearance while preserving the original photograph. It is not converted into a literal 3D render and does not invent details about a real event.

The only overlay is the Biz Pakistan logo and channel name. No headline, breaking-news label, category, slogan, or extra text is added. Feed and Story use the same source scene with different crops.

If a suitable photo with verified reuse rights cannot be found, that news item is skipped rather than publishing a poor-quality or unrelated visual.

## Image sources and reuse

- Article-provided images are used only when reuse rights are established.
- Openverse and Wikimedia Commons candidates are filtered for reusable licences.
- Pexels is optional and requires `PEXELS_API_KEY`.
- Add domains to `IMAGE_ALLOWED_DOMAINS` only when you have genuine permission to reuse images from those domains.

## Required GitHub Actions secrets

- OPENROUTER_API_KEY
- BUFFER_API_KEY
- BUFFER_CHANNEL_ID
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET

Optional: `PEXELS_API_KEY` for Pexels image search.
