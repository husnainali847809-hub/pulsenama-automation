# PulseNama Auto Publisher

Automated news review and publishing to Facebook through Buffer.

## AI-generated news images

PulseNama generates a new topic-matched 3D editorial illustration for each approved news item using Cloudflare Workers AI FLUX.1 schnell. The illustration is not represented as a real photograph of the event. The publisher overlays only the PulseNama logo and channel name; no headline or extra text is placed on the image. Feed and Story use the same generated scene with different crops.

### Required Cloudflare setup (free tier available)

1. Create or sign in to a Cloudflare account: https://dash.cloudflare.com/
2. Open Workers & Pages, then Workers AI, then Use REST API.
3. Create a Workers AI API token with Workers AI Read and Workers AI Edit permissions.
4. Copy your Cloudflare Account ID from the Workers AI page.
5. In this GitHub repository open Settings, Secrets and variables, Actions, then New repository secret.
6. Add these two secrets (never put their values in source code or chat):
   - CLOUDFLARE_ACCOUNT_ID — your Cloudflare Account ID
   - CLOUDFLARE_API_TOKEN — the Workers AI API token
7. Run Actions, PulseNama Auto Publisher, Run workflow.

Cloudflare Workers AI currently includes a daily free allocation on its Free plan. Usage above the free allocation requires the Paid plan. Check current pricing before increasing volume: https://developers.cloudflare.com/workers-ai/platform/pricing/

If image generation is not configured or fails, the article is not published with a random stock photo or a text-only fallback. Fix the Cloudflare configuration and retry the workflow.

## Other required GitHub Actions secrets

- OPENROUTER_API_KEY
- BUFFER_API_KEY
- BUFFER_CHANNEL_ID
- CLOUDINARY_CLOUD_NAME
- CLOUDINARY_API_KEY
- CLOUDINARY_API_SECRET

Optional: PEXELS_API_KEY is retained for legacy photo lookup code, but the current publishing flow uses generated images instead.
