# PulseNama Auto Publisher

Automated news review and publishing to Facebook through Buffer.

## AI-generated news images

PulseNama generates a new topic-matched 3D editorial illustration for every approved news item using **AI Horde**, a free, community-powered image-generation network run by volunteer workers. It uses anonymous public access, so no Cloudflare account, image API key, or credit card is required.

The image is an editorial illustration, not a real photograph of the actual event. PulseNama overlays only its logo and channel name; no headline or extra text is placed on the image. Feed and Story use the same generated scene with different crops.

### Important free-service limitations

- Anonymous requests have the lowest queue priority and can take a while.
- The public service may be busy or temporarily unavailable.
- Anonymous generation is requested at 512×512.
- If generation fails or times out, the story is skipped: the publisher does not use a random stock photo or a text-only fallback.
- The service is provided by volunteer workers; availability and quality are not guaranteed.

Official links:
- Generate images / learn about the queue: https://api.stablehorde.net/docs/image/
- API documentation: https://aihorde.net/api/
- Live service status: https://aihorde.net/

## Required GitHub Actions secrets

- OPENROUTER_API_KEY
- BUFFER_API_KEY
- BUFFER_CHANNEL_ID
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET

Optional: PEXELS_API_KEY is retained for legacy photo lookup code, but the current publishing flow uses AI-generated illustrations instead.
