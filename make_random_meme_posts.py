from mastodon import Mastodon, MastodonNetworkError
from shared_utils import does_text_contain_banned, replace_non_terminating_punctuation, text_only_cleaning_algorithm, make_image, build_alt_text, load_dotenv
import os, json, random, re

load_dotenv()
SENTENCE_FILE = os.getenv("SENTENCE_FILE", "/tmp/possible_sentences.txt")
HISTORY_FILE = os.getenv("HISTORY_FILE", "/tmp/previous_posts.txt")
BANLIST = json.loads(os.getenv("banlist"))


mastodon = Mastodon(access_token=os.getenv("access_token"), api_base_url="https://mastodon.social")

def load_sentences():
    # 1. Check if the file physically exists
    if not os.path.exists(SENTENCE_FILE):
        print(f"DEBUG: File not found at {SENTENCE_FILE}")
        return []

    # 2. Check if the file is just an empty text file
    if os.path.getsize(SENTENCE_FILE) == 0:
        print("DEBUG: File exists but is 0 bytes (empty).")
        return []

    try:
        with open(SENTENCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            # 3. Check if the JSON is valid but isn't a list (e.g., a dictionary or string)
            if not isinstance(data, list):
                print(f"DEBUG: JSON loaded but it is a {type(data)}, not a list.")
                return []

            # 4. Success!
            print(
                f"DEBUG: Successfully loaded {len(data)} sentences from {SENTENCE_FILE}."
            )
            return data

    except json.JSONDecodeError:
        print("DEBUG: Failed to load. The file contains invalid JSON formatting.")
        return []
    except UnicodeDecodeError:
        print(
            "DEBUG: Failed to load. There is an encoding issue (likely non-UTF8 characters)."
        )
        return []
    except Exception as e:
        print(f"DEBUG: An unexpected error occurred: {e}")
        return []


def load_previous_posts():
    """Loads the history of posted strings."""
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []


def save_sentences(sentences):
    # Limit to 500 items
    if len(sentences) > 500:
        random.shuffle(sentences)
        sentences = sentences[:500]
    with open(SENTENCE_FILE, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps emojis/accents readable in the txt file
        json.dump(sentences, f, ensure_ascii=False, indent=2)


def save_previous_posts(history_list):
    """Saves the history, keeping only the last 500 items to save space."""
    # We keep a limit so the file doesn't grow forever
    if len(history_list) > 500:
        history_list = history_list[-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)



def get_hashtag_toot(last_seen_id=None):
    # new_toots = False
    # 1. LOAD: Get the existing sentences from the file first
    sentence_object_list = load_sentences()  # a list of dicts
    history_string_list = load_previous_posts()

    # # 2. FETCH: Get new toots from Mastodon
    # toots = mastodon.timeline_hashtag(
    #     hashtag="monsterdon", since_id=last_seen_id, limit=40
    # )
    # 2. FETCH: Wrap in try/except to prevent crashes
    try:
        toots = mastodon.timeline_hashtag(hashtag="monsterdon", since_id=last_seen_id, limit=40)
    except MastodonNetworkError as e:
        print(f"DEBUG: Mastodon server timed out or network is down: {e}")
        toots = None # Fall back to using the existing pool

    # 3. PROCESS: If there are new toots, clean them and add to the pool
    if toots:
        # print(f"DEBUG: Found {len(toots)} new toots. Processing...")
        for toot in toots:
            source_url = toot["url"]  # Grab the URL before cleaning

            full_text = text_only_cleaning_algorithm(toot["content"])

            full_text = replace_non_terminating_punctuation(full_text)

            # Split into sentences and filter out empty ones
            new_sentences = [
                s.strip() for s in re.split(r"(?<=[.!?])\s+", full_text) if s.strip()
            ]

            for s in new_sentences:
                # Standard validation checks
                if 5 <= len(s) <= 150 and not does_text_contain_banned(s, BANLIST):
                    # Check if the sentence text exists in the pool or history
                    # Use any() to check inside the list of dictionaries
                    is_in_pool = any(
                        item["sentence"] == s for item in sentence_object_list
                    )

                    if not is_in_pool and s not in history_string_list:
                        sentence_object_list.append({"sentence": s, "url": source_url})
    else:
        print("DEBUG: No new toots found, relying on existing pool.")

    # 4. PICK: If the pool is empty (no new toots AND no file data), we can't continue
    if not sentence_object_list:
        print("DEBUG: Pool is completely empty. Nothing to return.")
        return None

    print("step 5")
    # 5. RESULT: Choose a random sentence
    result_object = random.choice(sentence_object_list)
    if result_object["sentence"] in history_string_list:
        print("DEBUG: Already posted. Nothing to return.")
        sentence_object_list.remove(result_object)
        save_sentences(sentence_object_list)
        return None

    print("step 6")
    # 6. REMOVE: Take it out so we don't repeat it
    sentence_object_list.remove(result_object)
    history_string_list.append(result_object["sentence"])

    print("step 7")
    # 7. SAVE: Trim the list to 100 and write back to the file
    save_sentences(sentence_object_list)
    save_previous_posts(history_string_list)

    print(
        f"DEBUG: Returning sentence. Remaining pool size: {len(sentence_object_list)}"
    )
    return result_object


def run_random_post():
    # 1. Get content from your sentence pool
    text_object = get_hashtag_toot() # This function stays as is in your logic
    if not text_object:
        print("Pool empty, skipping post.")
        return

    sentence = text_object["sentence"]
    
    # 2. Post
    try:
        print(f"Posting random meme: {sentence[:30]}...")
        png_path = make_image(sentence)
        media = mastodon.media_post(png_path, description=build_alt_text(sentence))
        
        mastodon.status_post(
            status=sentence,
            media_ids=[media["id"]],
            visibility="public"
        )
        print("Post successful.")
    except Exception as e:
        print(f"Failed to post: {e}")

if __name__ == "__main__":
    run_random_post()