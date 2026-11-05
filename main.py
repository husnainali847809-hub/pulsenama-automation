#!/usr/bin/env python3
"""
Unique News - automated Facebook news publisher (v2)

Pipeline:
  RSS (many sources) -> dedupe/balance -> Gemini review + copy (with retries)
  -> AI Horde artwork (Pillow fallback) -> Pillow branding -> Cloudinary
  -> Buffer Facebook FEED post (queued) -> Buffer Facebook STORY (queued)

Important facts:
  * "Queued" means accepted by Buffer's queue. It is NOT the same as published.
  * Feed and Story are two separate Buffer posts with separate status tracking
    in seen.json, so a failed Story never causes a duplicate Feed post.
  * Secrets are read from environment variables only and are redacted in logs.
"""

import hashlib
import json
import logging
import os
import random
import re
    total = sum(len(line.split()) for line in lines)
    highlight = 2 if total >= 5 else 1
    index = 0
    for line in lines:
        cursor = x
        for word in line.split():
            color = yellow if index >= total - highlight else white
            draw.text(
                (cursor, y), word, font=font, fill=color,
                stroke_width=2, stroke_fill=(0, 0, 0),
            )
            cursor += draw.textlength(word + " ", font=font)
            index += 1
        y += line_height


YELLOW = (255, 204, 35)
WHITE = (255, 255, 255)
GREY = (185, 185, 185)
DARK = (12, 12, 17)
BLACK_BRAND = (5, 5, 8)


def draw_brand_logo(draw, right, top, scale=1.0):
    """UNIQUE NEWS logo: yellow 'U' mark + white/yellow wordmark, right-aligned."""
    mark = int(54 * scale)
    gap = int(14 * scale)
    font = load_news_font(int(34 * scale))
    mark_font = load_news_font(int(36 * scale))
    word_a = "UNIQUE "
    word_b = "NEWS"
    wa = draw.textlength(word_a, font=font)
    wb = draw.textlength(word_b, font=font)
    total = mark + gap + wa + wb
        if stats["feeds_queued"] == 0 and failures > 0:
            exit_code = 1

    except StateError as exc:
        log.error("%s", describe_error(exc))
        gha("error", describe_error(exc))
        exit_code = 1
    except FatalError as exc:
        log.error("Fatal configuration/authentication error: %s", describe_error(exc))
        gha("error", describe_error(exc))
        exit_code = 1
    except Exception as exc:  # noqa: BLE001
        log.error("Unexpected error: %s", describe_error(exc))
        gha("error", f"Unexpected error: {describe_error(exc)}")
        exit_code = 1

    log.info(
        "Finished. Feed queued: %d | Story queued: %d | Story failures: %d | "
        "Unsuitable: %d | Gemini failures: %d | Other failures: %d",
        stats["feeds_queued"], stats["stories_queued"], stats["story_failures"],
        stats["unsuitable"], stats["gemini_failures"], stats["other_failures"],
    )
    write_step_summary(stats)
    return exit_code


# ==========================================================================
# START
# ==========================================================================

if __name__ == "__main__":
    sys.exit(main())
