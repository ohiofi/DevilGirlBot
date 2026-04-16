from mastodon import Mastodon
from shared_utils import does_text_contain_banned, text_only_cleaning_algorithm, make_image, build_alt_text, load_dotenv
import os, time, random, json

load_dotenv()
mastodon = Mastodon(access_token=os.getenv("access_token"), api_base_url="https://mastodon.social")
BANLIST = json.loads(os.getenv("banlist"))
LAST_ID_FILE = os.getenv("LAST_ID_FILE", "/tmp/last_id.txt")

def load_last_seen_id():
    try:
        with open(LAST_ID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None

def save_last_seen_id(last_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(last_id))

def process_mentions():
    last_id = load_last_seen_id()
    mentions = mastodon.notifications(types=["mention"], since_id=last_id)
    
    if not mentions:
        return

    # Process oldest first
    for note in reversed(mentions):
        mention = note["status"]
        user_acct = mention["account"]["acct"]
        
        # 1. Guards
        if user_acct in BANLIST or does_text_contain_banned(mention["content"]):
            continue
        if random.random() < 0.01: # 1% skip
            continue

        # 2. Extract Text
        clean_text = text_only_cleaning_algorithm(mention["content"])
        if not clean_text or len(clean_text) > 255:
            continue

        # 3. Reply
        print(f"Replying to {user_acct}...")
        png_path = make_image(clean_text)
        mastodon.status_post(
            status=f"@{user_acct} {clean_text}",
            media_ids=[mastodon.media_post(png_path, description=build_alt_text(clean_text))["id"]],
            in_reply_to_id=mention["id"],
            visibility="public"
        )
        
        save_last_seen_id(note["id"])
        break

if __name__ == "__main__":
    process_mentions()