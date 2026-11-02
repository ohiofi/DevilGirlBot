import os
import sys
import re
import time
import json
import logging
import requests
from dotenv import load_dotenv
from mastodon import Mastodon
from datetime import datetime

# =====================================================================
# CONFIGURATION
# =====================================================================
WORKING_DIR = "/Users/justinriley/DevilGirlBot"
LOG_DIR = os.path.join(WORKING_DIR, "logs")
ENV_PATH = os.path.join(WORKING_DIR, ".env")

# Ensure logs directory exists and set log file target
os.makedirs(LOG_DIR, exist_ok=True)
LOG_PATH = os.path.join(LOG_DIR, "give_warnings_list.log")


# Configure logger to output to both log file and stdout
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH),
        logging.StreamHandler(sys.stdout)
    ]
)

# Set DEBUG_MODE to False to post live on Mastodon
DEBUG_MODE = False

load_dotenv(ENV_PATH)

# JSON_PATH = os.getenv("GIVE_WARNINGS_JSON_PATH") or os.getenv("GIVE_WARNINGS_LIST_PATH") or os.path.join(WORKING_DIR, "give_warnings.json")
JSON_PATH = os.getenv("GIVE_WARNINGS_LIST_PATH")
if JSON_PATH.endswith(".txt"):
    JSON_PATH = os.path.join(os.path.dirname(JSON_PATH), "give_warnings.json")

DDD_API_KEY = os.getenv("DOESTHEDOGDIE_API_KEY") 
MASTODON_TOKEN = os.getenv("access_token")
MASTODON_BASE_URL = os.getenv("MASTODON_BASE_URL", "https://mastodon.social")

DEFAULT_ENTRY = {
    "name": "",
    "hasPosted": False,
    "datePosted": None,
    "postID": None,
    "warningsList": [],
    "aliasNamesList": [],
    "doesTheDogDieUrl": None
}


def load_warnings_json(filepath):
    """Loads the JSON list of movie entries and normalizes missing fields."""
    if not os.path.exists(filepath):
        return []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                return [normalize_movie_entry(item) for item in data if isinstance(item, dict)]
            return []
    except Exception as e:
        logging.error(f"Error reading JSON file {filepath}: {e}")
        return []

def save_warnings_json(filepath, data):
    """Atomic write to prevent file corruption during execution."""
    temp_path = f"{filepath}.tmp"
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(temp_path, filepath)
    except Exception as e:
        logging.error(f"Error saving JSON file {filepath}: {e}")

def check_guard_rail():
    """Reads JSON queue and returns full dataset and the first unposted movie object."""
    data = load_warnings_json(JSON_PATH)
    if not data:
        logging.warning(f"Warning queue in {JSON_PATH} is empty or does not exist.")
        sys.exit(0)

    for entry in data:
        if not entry.get("hasPosted", False):
            return data, entry

    logging.info(f"{datetime.today().strftime('%Y-%m-%d')} All movies in JSON queue have been posted ✅")
    sys.exit(0)

def build_main_post(movie_title, num_warnings, movie_url, target_year=None):
    """Step 1: Formats the display title and prepares the Post 1 text."""
    display_name = movie_title
    if target_year and str(target_year) not in movie_title:
        display_name = f"{movie_title} ({target_year})"
        
    if num_warnings > 0:
        post_text = (
            f"🍿⚠️ MONSTERDON WARNINGS ⚠️🍿\n\n"
            f"Automated content check for\n"
            f"{display_name}\n\n"
            f"{num_warnings} community content flags found\n"
            f"The detailed breakdown is attached as a content warning reply below\n\n"
            f"Source: {movie_url}\n"
            f"Powered by DoesTheDogDie.com\n\n#MonsterdonWarnings"
        )
    else:
        post_text = (
            f"🍿⚠️ MONSTERDON WARNINGS ⚠️🍿\n\n"
            f"Automated content check for\n"
            f"{display_name}\n\n"
            f"0 community content flags reported for this title\n\n"
            f"Source: {movie_url}\n"
            f"Powered by DoesTheDogDie.com\n\n#MonsterdonWarnings"
        )
        
    return display_name, post_text

def chunk_warnings(warnings, max_body_chars=320):
    """Step 2: Groups warnings dynamically so no single post overflows Mastodon's limit."""
    chunks = []
    if not warnings:
        return chunks
        
    current_chunk = []
    current_char_count = 0
    
    for warning in warnings:
        line_item = f"\n• {warning}"
        if current_char_count + len(line_item) > max_body_chars and current_chunk:
            chunks.append(current_chunk)
            current_chunk = [warning]
            current_char_count = len(line_item)
        else:
            current_chunk.append(warning)
            current_char_count += len(line_item)
            
    if current_chunk:
        chunks.append(current_chunk)
        
    return chunks

def fetch_ddd_warnings(raw_input):
    """Parses year details from parenthesis, searches DDD, and aligns matching identifiers."""
    if not DDD_API_KEY:
        logging.critical("CRITICAL ERROR: DOESTHEDOGDIE_API_KEY is empty or not found in your .env file!")
        sys.exit(1)

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
    
    search_response = requests.get(search_url, headers=headers, timeout=10)
    if search_response.status_code != 200:
        logging.error(f"DDD API Search failed with code {search_response.status_code}")
        sys.exit(0)
        
    search_data = search_response.json()
    items = search_data.get("items", [])
    if not items:
        logging.warning(f"No movie match found on DoesTheDogDie for: '{movie_query}'")
        sys.exit(0)
        
    selected_item = handle_duplicate_films(items, movie_query, target_year)

    item_id = selected_item["id"]
    display_title = selected_item.get("name", movie_query)
    
    media_url = f"https://www.doesthedogdie.com/media/{item_id}"
    media_response = requests.get(media_url, headers=headers, timeout=10)
    if media_response.status_code != 200:
        logging.error(f"Failed to fetch specific movie topic metadata. Code: {media_response.status_code}")
        sys.exit(0)
        
    media_data = media_response.json()
    
    yes_warnings = []
    for topic_item in media_data.get("topicItemStats", []):
        yes_votes = topic_item.get("yesSum", 0)
        no_votes = topic_item.get("noSum", 0)
        if yes_votes > no_votes:
            topic_name = topic_item.get("topic", {}).get("name")
            if topic_name:
                yes_warnings.append(topic_name)
                
    return display_title, yes_warnings, item_id, target_year

def handle_duplicate_films(items, movie_query, target_year):
    """Filters API search results to find best matching film entry."""
    if not items:
        return None

    if not target_year:
        logging.info(f"No year specified. Defaulting to top API result: '{items[0].get('name')}'")
        return items[0]

    logging.info(f"Searching specific results for release year: {target_year}...")
    target_year_str = str(target_year).strip()

    for item in items:
        api_year = item.get("releaseYear") or item.get("year") or item.get("release_date")
        if api_year and target_year_str in str(api_year):
            logging.info(f"Tier 1 Match (Explicit API Release Year): '{item.get('name')}' ({api_year})")
            return item

    for item in items:
        name_text = item.get("name", "")
        if re.search(r'\b' + re.escape(target_year_str) + r'\b', name_text):
            logging.info(f"Tier 2 Match (Year bounded in Title): '{name_text}'")
            return item

    for item in items:
        name_text = item.get("name", "").strip()
        if name_text.lower() == movie_query.lower():
            logging.info(f"Tier 3 Match (Exact Root Title Match): '{name_text}'")
            return item

    logging.info(f"Tier 4 Fallback (No exact year criteria matched. Using top API result): '{items[0].get('name')}'")
    return items[0]

def normalize_movie_entry(entry):
    """Fills in any missing fields with their standard default values."""
    if not isinstance(entry, dict):
        return entry
    for key, default_val in DEFAULT_ENTRY.items():
        if key not in entry or entry[key] is None:
            # Create a new list copy for list defaults to avoid shared reference bugs
            if isinstance(default_val, list):
                entry[key] = []
            else:
                entry[key] = default_val
    return entry

def publish_main_post(mastodon_client, text, debug_mode):
    """Step 3: Publishes the public-facing primary announcement post."""
    if debug_mode:
        logging.info("=== DEBUG MODE ENABLED - MOCKING THREAD ===")
        logging.info("--- POST 1 (MAIN POST - PUBLIC) ---")
        logging.info(text)
        return "mock_parent_id"
    
    logging.info("Publishing warning notice live to Mastodon...")
    parent_post = mastodon_client.status_post(text, visibility="public")
    return parent_post.get("id")

def publish_threaded_replies(mastodon_client, parent_id, chunks, display_name, debug_mode):
    """Step 4: Chains spoiler-wrapped warning lists together."""
    total_parts = len(chunks)
    previous_post_id = parent_id
    
    for idx, chunk in enumerate(chunks):
        part_num = idx + 1
        cw_label = f"content warnings for {display_name} (part {part_num}/{total_parts})"
        
        formatted_warnings = "\n• ".join(chunk)
        reply_text = f"(part {part_num}/{total_parts}) content warnings for {display_name}:\n\n• {formatted_warnings}"
        
        if debug_mode:
            logging.info(f"--- POST {part_num + 1} (REPLY - UNLISTED - Part {part_num}/{total_parts}) ---")
            logging.info(f"Content Warning Banner: [{cw_label}]")
            logging.info(reply_text)
        else:
            reply_post = mastodon_client.status_post(
                status=reply_text,
                in_reply_to_id=previous_post_id,
                spoiler_text=cw_label,
                visibility="public"
            )
            previous_post_id = reply_post.get("id")
            time.sleep(1)
            
    if debug_mode and total_parts == 0:
        logging.info("--- POST 2 SKIPPED (0 Warnings Found) ---")

def main():
    all_data, movie_entry = check_guard_rail()
    raw_name = movie_entry.get("name")
    logging.info(f"--- Processing Single Run: {raw_name} ---")
    
    try:
        title, warnings_list, item_id, target_year = fetch_ddd_warnings(raw_name)
        movie_url = f"https://www.doesthedogdie.com/media/{item_id}"
        logging.info(f"Found {len(warnings_list)} warnings for '{title}'")
        
        display_name, post1_text = build_main_post(title, len(warnings_list), movie_url, target_year)
        chunks = chunk_warnings(warnings_list)
        
        mastodon_client = None
        if not DEBUG_MODE:
            mastodon_client = Mastodon(
                access_token=MASTODON_TOKEN,
                api_base_url=MASTODON_BASE_URL,
                request_timeout=15
            )

        # 1. Post Main Status
        parent_id = publish_main_post(mastodon_client, post1_text, DEBUG_MODE)

        # 2. ANTI-SPAM GUARD: Mark posted IMMEDIATELY in JSON to prevent re-posting loop
        movie_entry["hasPosted"] = True
        movie_entry["datePosted"] = datetime.now().isoformat()
        movie_entry["postID"] = str(parent_id) if parent_id else None
        movie_entry["warningsList"] = warnings_list
        movie_entry["doesTheDogDieUrl"] = movie_url
        
        if "aliasNamesList" not in movie_entry or not isinstance(movie_entry["aliasNamesList"], list):
            movie_entry["aliasNamesList"] = []
        if title and title != raw_name and title not in movie_entry["aliasNamesList"]:
            movie_entry["aliasNamesList"].append(title)

        save_warnings_json(JSON_PATH, all_data)
        logging.info(f"🔒 Locked '{raw_name}' state as posted in {JSON_PATH}.")

        # 3. Threaded replies
        publish_threaded_replies(mastodon_client, parent_id, chunks, display_name, DEBUG_MODE)
        logging.info("Run Complete!")
        
    except Exception as e:
        logging.error(f"ERROR processing '{raw_name}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()