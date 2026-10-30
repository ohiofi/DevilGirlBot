import os
import re
import sys
import json
import logging
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from mastodon import Mastodon

DEBUG_MODE = False # Set to False to go live

WORKING_DIR = "/Users/justinriley/DevilGirlBot"
LOG_DIR = os.path.join(WORKING_DIR, "logs")
ENV_PATH = os.path.join(WORKING_DIR, ".env")

os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "give_warnings_poll_checker.log")

load_dotenv(ENV_PATH)

# Configure logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)

JSON_PATH = os.getenv("GIVE_WARNINGS_JSON_PATH") or os.getenv("GIVE_WARNINGS_LIST_PATH") or os.path.join(WORKING_DIR, "give_warnings.json")
if JSON_PATH.endswith(".txt"):
    JSON_PATH = os.path.join(os.path.dirname(JSON_PATH), "give_warnings.json")

DDD_API_KEY = os.getenv("DOESTHEDOGDIE_API_KEY")

TARGET_HASHTAG = "MonsterdonAlert"
TARGET_FULL_HANDLE = "Taweret@timeloop.cafe" # must NOT begin with @ sign
LOOKBACK_MINUTES = 30

MASTODON_TOKEN = os.getenv("access_token")
MASTODON_BASE_URL = os.getenv("MASTODON_BASE_URL", "https://mastodon.social")

def load_warnings_json(filepath):
    """Loads JSON data list."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except Exception as e:
        logging.error(f"Error loading JSON {filepath}: {e}")
        return []

def save_warnings_json(filepath, data):
    """Atomic write to prevent corruption."""
    temp_path = f"{filepath}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, filepath)
    except Exception as e:
        logging.error(f"Error saving JSON {filepath}: {e}")

def append_to_warnings_list(movie_titles):
    """Safely appends movie items to give_warnings.json if not already tracked."""
    data = load_warnings_json(JSON_PATH)

    existing_names = set()
    for entry in data:
        if entry.get("name"):
            existing_names.add(entry["name"].strip().lower())
        for alias in entry.get("aliasNamesList", []):
            existing_names.add(alias.strip().lower())

    added_any = False
    for title in movie_titles:
        clean_title = title.strip()
        if clean_title.lower() not in existing_names:
            new_entry = {
                "name": clean_title,
                "hasPosted": False,
                "datePosted": None,
                "postID": None,
                "warningsList": [],
                "aliasNamesList": [],
                "doesTheDogDieUrl": None
            }
            data.append(new_entry)
            existing_names.add(clean_title.lower())
            added_any = True
            logging.info(f"  📝 Appended to JSON queue: '{clean_title}'")

    if added_any:
        save_warnings_json(JSON_PATH, data)
    else:
        logging.info("  All titles from this poll are already present in the file.")

def fetch_and_check_polls(mastodon_client):
    logging.info(f"Resolving federated handle across instances: @{TARGET_FULL_HANDLE}...")
    try:
        search_results = mastodon_client.search_v2(q=TARGET_FULL_HANDLE, result_type="accounts")
        accounts = search_results.get("accounts", [])
        
        if not accounts:
            logging.error(f"Could not resolve federated user '{TARGET_FULL_HANDLE}' from mastodon.social")
            return
        
        target_account = accounts[0]
        target_account_id = target_account["id"]
        actual_username = target_account["username"]
        logging.info(f"🎯 Successfully resolved to local-cached ID: {target_account_id} (@{actual_username})")
        
    except Exception as e:
        logging.error(f"Error communicating with Mastodon API during federated account search: {e}")
        return

    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=LOOKBACK_MINUTES)
    logging.info(f"Checking statuses posted since: {time_threshold.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    try:
        statuses = mastodon_client.account_statuses(id=target_account_id, limit=20)
    except Exception as e:
        logging.error(f"Error fetching statuses for resolved account ID {target_account_id}: {e}")
        return

    matched_any = False

    for status in statuses:
        created_at = status.get("created_at")
        if not created_at or created_at < time_threshold:
            break

        poll_data = status.get("poll")
        if not poll_data:
            continue

        tags = [t.get("name", "").lower() for t in status.get("tags", [])]
        if TARGET_HASHTAG.lower() not in tags:
            continue

        matched_any = True
        status_id = status.get("id")
        logging.info(f"[MATCH] Found matching poll post from {created_at.strftime('%H:%M:%S UTC')}!")
        
        options = poll_data.get("options", [])
        new_entries = []
        
        for option in options:
            title_text = option.get("title", "").strip()
            if title_text:
                if re.search(r'\((19\d{2}|20\d{2})\)', title_text):
                    logging.info(f"  🎬 Valid film format found: {title_text}")
                else:
                    logging.warning(f"  ⚠️ Text found (does not strictly fit Title (Year)): {title_text}")
                
                new_entries.append(title_text)

        if new_entries:
            append_to_warnings_list(new_entries)
            post_poll_summary_reply(mastodon_client, status_id, new_entries)

    if not matched_any:
        logging.info("No new matching polls found from the target user in the last 30 minutes.")

def get_ddd_warning_count(raw_input):
    """Searches DoesTheDogDie for a title string and counts topics where yesSum > noSum."""
    if not DDD_API_KEY:
        logging.warning("DOESTHEDOGDIE_API_KEY is missing. Defaulting flag count to 0.")
        return 0

    year_match = re.search(r'\((19\d{2}|20\d{2})\)', raw_input)
    target_year = year_match.group(1) if year_match else None
    
    if target_year:
        movie_query = raw_input.replace(f"({target_year})", "").strip()
    else:
        movie_query = raw_input.strip()

    search_url = f"https://www.doesthedogdie.com/dddsearch?q={movie_query}"
    headers = {
        "Accept": "application/json",
        "X-API-KEY": str(DDD_API_KEY).strip(),
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        search_resp = requests.get(search_url, headers=headers, timeout=10)
        if search_resp.status_code != 200:
            return 0
        
        items = search_resp.json().get("items", [])
        if not items:
            return 0
        
        selected_item = items[0]
        if target_year:
            for item in items:
                api_year = item.get("releaseYear") or item.get("year") or item.get("release_date")
                if api_year and str(target_year) in str(api_year):
                    selected_item = item
                    break

        item_id = selected_item["id"]
        media_url = f"https://www.doesthedogdie.com/media/{item_id}"
        media_resp = requests.get(media_url, headers=headers, timeout=10)
        if media_resp.status_code != 200:
            return 0
        
        media_data = media_resp.json()
        yes_count = 0
        for topic_item in media_data.get("topicItemStats", []):
            if topic_item.get("yesSum", 0) > topic_item.get("noSum", 0):
                yes_count += 1
                
        return yes_count
    except Exception as e:
        logging.error(f"Error fetching DDD warning count for '{raw_input}': {e}")
        return 0

def post_poll_summary_reply(mastodon_client, status_id, movie_titles):
    """Formats and posts the warning count summary reply to the original poll post."""
    lines = ["🍿⚠️ CONTENT WARNINGS COUNT ⚠️🍿\n"]
    for title in movie_titles:
        count = get_ddd_warning_count(title)
        lines.append(f"{count} flags, {title}")
    
    lines.append("\nSee #MonsterdonWarnings or DoesTheDogDie for more info\nPowered by DoesTheDogDie.com")
    reply_text = "\n".join(lines)

    if DEBUG_MODE:
        logging.info("=== DEBUG MODE ACTIVE - MOCKING REPLY POST ===")
        logging.info(f"--- MOCK REPLY TO STATUS ID: {status_id} ---")
        logging.info(reply_text)
        logging.info("-------------------------------------------\n")
        return

    try:
        mastodon_client.status_post(
            status=reply_text,
            in_reply_to_id=status_id,
            visibility="public"
        )
        logging.info(f"Successfully posted summary reply to status ID {status_id}.")
    except Exception as e:
        logging.error(f"Failed to post summary reply to status ID {status_id}: {e}")

def main():
    if not MASTODON_TOKEN:
        logging.critical("CRITICAL ERROR: access_token not found in your environment configuration!")
        sys.exit(1)

    logging.info("Initializing Federated Poll Checker (30-Minute Lookback)...")
    try:
        mastodon_client = Mastodon(
            access_token=MASTODON_TOKEN,
            api_base_url=MASTODON_BASE_URL,
            request_timeout=15
        )
        fetch_and_check_polls(mastodon_client)
    except Exception as e:
        logging.error(f"Unhandled exception during execution: {e}")
        sys.exit(1)

    logging.info("Run complete.\n")

if __name__ == "__main__":
    main()