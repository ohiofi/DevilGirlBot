from mastodon import Mastodon

import os, random, json
from shared_utils import (
    does_text_contain_banned,
    find_source_by_parent_id,
    text_only_cleaning_algorithm,
    make_image,
    build_alt_text,
    load_dotenv,
    load_last_seen_id,
    save_last_seen_id,
    update_history,
    extract_raw_text
)


load_dotenv()
mastodon = Mastodon(
    access_token=os.getenv("access_token"), api_base_url="https://mastodon.social"
)
BANLIST = json.loads(os.getenv("banned_words") or '[]')
LAST_ID_FILE = os.getenv("LAST_ID_FILE", "/tmp/last_id.txt")

def send_text_reply(original_mention, text):
    mastodon.status_post(status=text, in_reply_to_id=original_mention["id"], visibility="unlisted")

def context_lookup(mention, user_acct):
    parent_id = mention.get("in_reply_to_id")
    source_url = find_source_by_parent_id(parent_id)
    if source_url:
        return f"@{user_acct} Context lookup successful: {source_url}"
    else:
        return f"@{user_acct} I cannot find the origin of that transmission in my recent logs."

def process_mentions():
    last_id = load_last_seen_id("last_mention_id.txt")
    mentions = mastodon.notifications(types=["mention"], since_id=last_id)
    
    for note in reversed(mentions):
        mention = note["status"]
        user_acct = mention["account"]["acct"]
        raw_text = extract_raw_text(mention["content"])

        # --- COMMAND CHAIN ---
        if "!help" in raw_text:
            send_text_reply(mention, 
                            f"@{user_acct} DevilGirlBot is series of automated Python scripts.\n"
                            f"COMMANDS:\n"
                            f"  !context = reply !context to one of my random posts to get the source URL\n"
                            f"  !roll2d6 = roll two 6-sided die\n"
                            f"  !source = same as !context\n"
                            f"  !fuel = returns the ship's fuel level\n"
                            )
        elif "!context" in raw_text:
            send_text_reply(mention, context_lookup(mention, user_acct))
        elif "!source" in raw_text:
            send_text_reply(mention, context_lookup(mention, user_acct))
        elif "!status" in raw_text:
            send_text_reply(mention, f"@{user_acct} The ship's fueled level is {random.randint(1,100)}")
        elif "!roll2d6" in raw_text:
            d1 = random.randint(1,6)
            d2 = random.randint(1,6)
            send_text_reply(mention, f"@{user_acct} Rolled {d1} and {d2} for a total of {d1 + d2}")

        # --- DEFAULT: GENERATE MEME ---
        else:
            clean_text = text_only_cleaning_algorithm(mention["content"])
            if clean_text and len(clean_text) <= 255:
                png_path = make_image(clean_text)
                response = mastodon.status_post(
                    status=f"@{user_acct} {clean_text}",
                    media_ids=[mastodon.media_post(png_path, description=build_alt_text(clean_text))["id"]],
                    in_reply_to_id=mention["id"]
                )
                update_history(clean_text, mention["url"], response["url"])

        save_last_seen_id(note["id"], "last_mention_id.txt")

if __name__ == "__main__":
    process_mentions()