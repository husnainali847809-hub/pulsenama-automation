
def main():
    seen = load_seen()
    articles = get_news()

    print("Articles collected:", len(articles))

    MAX_ARTICLES_PER_RUN = 3
    processed = 0

    for article in articles:

        article_id = hashlib.sha256(
            article["link"].encode("utf-8")
        ).hexdigest()

        if article_id in seen:
            continue

        if processed >= MAX_ARTICLES_PER_RUN:
            print("Maximum article limit reached.")
            break

        processed += 1

        print("Processing:", article["title"])

        try:
            post = make_post(article)

            if not post:
                print("Article skipped:", article["title"])
                seen.append(article_id)
                save_seen(seen)
                continue

            generate_story_image(article)

            post_id = publish_to_facebook(
                post,
                article["link"]
            )

            print("Facebook photo post published:", post_id)

            seen.append(article_id)
            save_seen(seen)

            try:
                publish_story()

            except Exception as story_error:
                print(
                    "Story publishing failed:",
                    str(story_error)
                )

            print("Publishing completed successfully.")
            return

        except Exception as e:
            error = str(e).lower()

            print("Processing error:", str(e))

            if "429" in error or "resource_exhausted" in error:
                print("Gemini quota exhausted. Stopping workflow.")
                break

            if "503" in error or "unavailable" in error:
                print("Gemini temporarily unavailable. Stopping workflow.")
                break

            print("Error detected. Stopping to prevent unnecessary API calls.")
            break

    print("Workflow finished.")
    if __name__ == "__main__":
        main()
    print("MAIN.PY STARTED SUCCESSFULLY")
    
