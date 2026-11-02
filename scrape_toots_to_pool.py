from mastodon import Mastodon
from shared_utils import (
    load_sentences, save_sentences, load_previous_posts,
    text_only_cleaning_algorithm, replace_non_terminating_punctuation,
    is_sentence_valid, load_dotenv, load_last_seen_id, save_last_seen_id
)
import os, re, json, time

load_dotenv()
mastodon = Mastodon(access_token=os.getenv("access_token"), api_base_url="https://mastodon.social")
BANNED_WORDS = json.loads(os.getenv("banned_words"))
BANNED_USERS = json.loads(os.getenv("banned_users"))

def scrape_monsterdon():
    sentence_pool = load_sentences()
    history = load_previous_posts()
    history_text_only = [item["text"] for item in history]
    
    # We track the last ID specifically for the hashtag timeline
    last_id = load_last_seen_id("last_hashtag_scraping_id.txt") 
    
    new_toots_count = 0
    max_id = None
    keep_fetching = True

    print("Scraping #monsterdon...")

    while keep_fetching:
        try:
            # Fetch 40 toots at a time
            toots = mastodon.timeline_hashtag(
                hashtag="monsterdon", 
                since_id=last_id, 
                max_id=max_id, 
                limit=40
            )

            if not toots:
                keep_fetching = False
                break

            # Update the latest ID we've seen from the very first toot in the batch
            if new_toots_count == 0:
                save_last_seen_id(toots[0]["id"], "last_hashtag_scraping_id.txt")

            for toot in toots:
                source_url = toot["url"]
                author = toot["account"]["acct"]
                full_text = text_only_cleaning_algorithm(toot["content"])
                full_text = replace_non_terminating_punctuation(full_text)

                # Split and filter sentences
                new_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_text) if s.strip()]

                # 1 toot can have many sentences. Each sentence is added to the sentence pool separately
                for s in new_sentences:
                    if is_sentence_valid(full_text, author, sentence_pool, history_text_only, BANNED_WORDS, BANNED_USERS):
                        sentence_pool.append({"sentence": s, "url": source_url})
                        new_toots_count += 1

            # Prepare for next page: set max_id to the oldest toot in this batch
            max_id = toots[-1]["id"]
            
            # API safety: don't hammer the server too hard in a tight loop
            time.sleep(1) 

            # Safety break: stop if we've fetched a massive amount (e.g., 1000 toots)
            if new_toots_count > 1000:
                print("Safety cap reached (900+ sentences). Stopping scrape.")
                keep_fetching = False

        except Exception as e:
            print(f"Scrape batch failed: {e}")
            keep_fetching = False

    save_sentences(sentence_pool)
    print(f"Scrape complete. Added {new_toots_count} candidates. Pool total: {len(sentence_pool)}")

if __name__ == "__main__":
    scrape_monsterdon()