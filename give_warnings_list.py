import os
import sys
import re
import time
import requests
from dotenv import load_dotenv
from mastodon import Mastodon
from datetime import datetime

# =====================================================================
# CONFIGURATION
# =====================================================================
WORKING_DIR = "/Users/justinriley/DevilGirlBot"
ENV_PATH = os.path.join(WORKING_DIR, ".env")
LIST_PATH = os.path.join(WORKING_DIR, "give_warnings_list.txt")

# set DEBUG_MODE to False to post on Mastodon
DEBUG_MODE = False

load_dotenv(ENV_PATH)

LIST_PATH = os.getenv("GIVE_WARNINGS_LIST_PATH")
DDD_API_KEY = os.getenv("DOESTHEDOGDIE_API_KEY") 
MASTODON_TOKEN = os.getenv("access_token")
MASTODON_BASE_URL = os.getenv("MASTODON_BASE_URL", "https://mastodon.social")

def apply_stop_guard(processed_movie):
    """Appends !STOP immediately following the single processed movie."""
    if not os.path.exists(LIST_PATH):
        return
        
    with open(LIST_PATH, "r") as f:
        content = f.read()
        
    # Safely find the raw movie string and place the !STOP anchor directly under it
    # This keeps things perfectly tracked even if there are multiple movies stacked below it
    target_pattern = re.escape(processed_movie)
    if processed_movie in content and f"{processed_movie}\n!STOP" not in content:
        updated_content = content.replace(processed_movie, f"{processed_movie}\n!STOP", 1)
        with open(LIST_PATH, "w") as f:
            f.write(updated_content)
        print(f"Successfully locked '{processed_movie}' transaction with !STOP.")

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
            f"Source: {movie_url}\n#MonsterdonWarnings"
        )
    else:
        post_text = (
            f"🍿⚠️ MONSTERDON WARNINGS ⚠️🍿\n\n"
            f"Automated content check for\n"
            f"{display_name}\n\n"
            f"0 community content flags reported for this title\n\n"
            f"Source: {movie_url}\n#MonsterdonWarnings"
        )
        
    return display_name, post_text

def check_guard_rail():
    """Reads the text file to extract all movies that need processing."""
    if not os.path.exists(LIST_PATH):
        print(f"Error: {LIST_PATH} does not exist.")
        sys.exit(0)
        
    with open(LIST_PATH, "r") as f:
        lines = [line.strip() for line in f.readlines() if line.strip()]
        
    if not lines:
        print("Warning list file is empty. Nothing to do.")
        sys.exit(0)
        
    if lines[-1] == "!STOP":
        print(f"{datetime.today().strftime('%Y-%m-%d')} !STOP at end of file ✅")
        sys.exit(0)
        
    # Split the file by previous !STOP markers to find only the fresh movies at the bottom
    # Or if there are no !STOP markers, process all lines
    unprocessed_movies = []
    for line in lines:
        if line == "!STOP":
            unprocessed_movies = [] # Reset, because everything above this !STOP is already done
        else:
            unprocessed_movies.append(line)
            
    return unprocessed_movies

def chunk_warnings(warnings, max_body_chars=320):
    """Step 2: Groups warnings dynamically so no single post overflows Mastodon's 500-char limit."""
    chunks = []
    if not warnings:
        return chunks
        
    current_chunk = []
    current_char_count = 0
    
    for warning in warnings:
        line_item = f"\n• {warning}"
        # Start a new chunk if adding this item exceeds the safe character budget
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
    """Parses year details from the entry parenthesis, searches DDD, and aligns matching identifiers."""
    if not DDD_API_KEY:
        print("CRITICAL ERROR: DOESTHEDOGDIE_API_KEY is empty or not found in your .env file!")
        sys.exit(1)

    # Extract any 4-digit numeric string nested inside parentheses (e.g., (1954))
    year_match = re.search(r'\((19\d{2}|20\d{2})\)', raw_input)
    target_year = year_match.group(1) if year_match else None
    
    # Strip the parenthesis block out of the textual query string cleanly
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
        print(f"DDD API Search failed with code {search_response.status_code}")
        sys.exit(0)
        
    search_data = search_response.json()
    items = search_data.get("items", [])
    if not items:
        print(f"No movie match found on DoesTheDogDie for: '{movie_query}'")
        sys.exit(0)
        
    selected_item = handle_duplicate_films(items, movie_query, target_year)

    item_id = selected_item["id"]
    display_title = selected_item.get("name", movie_query)
    
    # Query specific details for the target item ID
    media_url = f"https://www.doesthedogdie.com/media/{item_id}"
    media_response = requests.get(media_url, headers=headers, timeout=10)
    if media_response.status_code != 200:
        print(f"Failed to fetch specific movie topic metadata. Code: {media_response.status_code}")
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
    """
    Filters a list of API search results to find the best matching film entry
    by comparing the target year cleanly against explicit API release attributes.
    """
    if not items:
        return None

    if not target_year:
        print(f"No year specified. Defaulting to top API result: '{items[0].get('name')}'")
        return items[0]

    print(f"Searching specific results for release year: {target_year}...")
    target_year_str = str(target_year).strip()

    # Tier 1: Look for an explicit, native release year attribute from the API data structure
    for item in items:
        # Check standard DDD JSON API properties for explicit year attributes
        api_year = item.get("releaseYear") or item.get("year") or item.get("release_date")
        if api_year and target_year_str in str(api_year):
            print(f"Tier 1 Match (Explicit API Release Year): '{item.get('name')}' ({api_year})")
            return item

    # Tier 2: Look for an explicit year embedded directly in the title string using boundaries
    # e.g., "Godzilla (1954)" or "King Kong 2005"
    for item in items:
        name_text = item.get("name", "")
        if re.search(r'\b' + re.escape(target_year_str) + r'\b', name_text):
            print(f"Tier 2 Match (Year bounded in Title): '{name_text}'")
            return item

    # Tier 3: Loose match on the title text being a clean exact match to your query text string
    # (Prioritizes the bare root title over secondary text-heavy results)
    for item in items:
        name_text = item.get("name", "").strip()
        if name_text.lower() == movie_query.lower():
            print(f"Tier 3 Match (Exact Root Title Match): '{name_text}'")
            return item

    # Tier 4 Fallback: If no year structural criteria hit, return the top search result
    print(f"Tier 4 Fallback (No exact year criteria matched. Using top API result): '{items[0].get('name')}'")
    return items[0]

def publish_main_post(mastodon_client, text, debug_mode):
    """Step 3: Publishes the public-facing primary announcement post."""
    if debug_mode:
        print("\n=== DEBUG MODE ENABLED - MOCKING THREAD ===")
        print("--- POST 1 (MAIN POST - PUBLIC) ---")
        print(text)
        return "mock_parent_id"
    
    print("Publishing warning notice live to Mastodon...")
    parent_post = mastodon_client.status_post(text, visibility="public")
    return parent_post.get("id")

def publish_threaded_replies(mastodon_client, parent_id, chunks, display_name, debug_mode):
    """Step 4: Challs and chains the unlisted, spoiler-wrapped warning lists together."""
    total_parts = len(chunks)
    previous_post_id = parent_id
    
    for idx, chunk in enumerate(chunks):
        part_num = idx + 1
        cw_label = f"content warnings for {display_name} (part {part_num}/{total_parts})"
        
        formatted_warnings = "\n• ".join(chunk)
        reply_text = f"(part {part_num}/{total_parts}) content warnings for {display_name}:\n\n• {formatted_warnings}"
        
        if debug_mode:
            print(f"\n--- POST {part_num + 1} (REPLY - UNLISTED - Part {part_num}/{total_parts}) ---")
            print(f"Content Warning Banner: [{cw_label}]")
            print(reply_text)
        else:
            # Post replies as unlisted to avoid spamming the public local timeline
            reply_post = mastodon_client.status_post(
                status=reply_text,
                in_reply_to_id=previous_post_id,
                spoiler_text=cw_label,
                visibility="public"
            )
            previous_post_id = reply_post.get("id")
            time.sleep(1) # Keep ordering intact in the Mastodon DB
            
    if debug_mode and total_parts == 0:
        print("\n--- POST 2 SKIPPED (0 Warnings Found) ---")
        print("===========================================\n")

def publish_warnings_to_mastodon(movie_title, warnings, item_id, target_year=None):
    """Coordinates the 4 sub-steps to process, chunk, and post the warnings thread."""
    movie_url = f"https://www.doesthedogdie.com/media/{item_id}"
    
    # 1. Prepare Title & Body (Step 1)
    display_name, post1_text = build_main_post(
        movie_title, len(warnings), movie_url, target_year
    )
    
    # 2. Chunk Warnings Into Safe Lengths (Step 2)
    chunks = chunk_warnings(warnings)
    
    # Initialize Client (only if not debugging)
    mastodon_client = None
    if not DEBUG_MODE:
        mastodon_client = Mastodon(
            access_token=MASTODON_TOKEN,
            api_base_url=MASTODON_BASE_URL,
            request_timeout=15
        )
        
    # 3. Publish Main Notice (Step 3)
    parent_id = publish_main_post(mastodon_client, post1_text, DEBUG_MODE)
    
    # 4. Thread the Chunks (Step 4)
    publish_threaded_replies(mastodon_client, parent_id, chunks, display_name, DEBUG_MODE)
    
    if len(chunks) > 0:
        print(f"Thread successfully stitched with {len(chunks)} detail reply parts!")
    else:
        print("Clean bill of health! Skipped empty details reply.")

def main():
    # print("Initializing Trigger Warning Engine...")
    movies_to_check = check_guard_rail()
    
    print(f"Identified {len(movies_to_check)} movie(s) waiting in queue.")
    
    # Grab ONLY the first movie waiting to be processed
    movie_entry = movies_to_check[0]
    print(f"\n--- Processing Single Run: {movie_entry} ---")
    
    try:
        title, warnings_list, item_id, target_year = fetch_ddd_warnings(movie_entry)
        print(f"Found {len(warnings_list)} warnings for '{title}'")
        
        publish_warnings_to_mastodon(title, warnings_list, item_id, target_year)
        
        # Lock this specific movie down immediately!
        apply_stop_guard(movie_entry)
        print("Run Complete!")
        
    except Exception as e:
        print(f"ERROR processing '{movie_entry}': {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()