import os
import time
import pandas as pd
from datetime import datetime, timedelta
from mastodon import Mastodon
from urllib.parse import urlparse
from dotenv import load_dotenv
import pytz

# NOTE: Whenever you add a new movie that was watched recently, delete census_max_id.txt
# The script will start from "Now" rather than back in time


# Mastodon has a rate limit (usually 300 requests per 5 minutes)

# --- Configuration ---
load_dotenv()
CSV_FILE = "details.csv"
ID_FILE = "census_max_id.txt"  # The file that stores our "place" in time
LOCAL_TZ = pytz.timezone("US/Eastern")
BATCH_SIZE = 15
DELAY_BETWEEN_MOVIES = 60

mastodon = Mastodon(
    access_token=os.getenv("access_token"), api_base_url="https://mastodon.social"
)


def fetch_census_data(start_dt, duration, starting_max_id=None):
    """Fetches census data with Gap-Jumping logic to prevent backlog stalls."""
    # Ensure starting_max_id isn't the literal string "None"
    if starting_max_id == "None":
        starting_max_id = None
    
    # include the 10 minutes after the end of the film
    end_dt = start_dt + timedelta(minutes = int(duration) + 10) 
   
    unique_users = set()
    unique_servers = set()
    total_hashtags_found = 0
    
    # Engagement Counters
    total_favorites = 0
    total_boosts = 0
    total_replies = 0
    
    total_checked = 0
    current_max_id = starting_max_id
    done = False

    print(f"   🎯 Target Window: {start_dt.strftime('%Y-%m-%d %H:%M')} to {end_dt.strftime('%H:%M')}")

    while not done:
        try:
            toots = mastodon.timeline_hashtag("monsterdon", max_id=current_max_id, limit=40)
        except Exception as e:
            print(f"\n   ❌ API Error: {e}")
            break

        if not toots:
            # This is the "Gap". We stop scrolling for this movie, 
            # but we return our current max_id so the next movie knows where to start.
            print("\n   ℹ️ Reached end of history or hit a paging gap.")
            break

        for toot in toots:
            total_checked += 1
            created_at = toot["created_at"].astimezone(LOCAL_TZ)

            if start_dt <= created_at <= end_dt:
                unique_users.add(toot["account"]["acct"])
                server_domain = urlparse(toot["account"]["url"]).netloc
                unique_servers.add(server_domain)

                total_hashtags_found += 1

                # Engagement Metrics
                total_favorites += toot.get('favourites_count', 0)
                total_boosts += toot.get('reblogs_count', 0)
                total_replies += toot.get('replies_count', 0)

            if created_at < start_dt:
                done = True
                break

        # Update the pointer to the last toot in this batch
        current_max_id = toots[-1]["id"]
        
        current_pos = toots[-1]["created_at"].astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
        print(
            f"   ⏳ Scrolling back... Checked: {total_checked} Currently at: {current_pos} Toots: {total_hashtags_found} Users: {len(unique_users)}",
            end="\r",
        )

    # --- THE GAP-JUMPER UPDATE ---
    # We no longer return None if toots == 0. 
    # Recording 0 allows the script to progress past dead dates in the backlog.
    if total_hashtags_found == 0:
        print(f"\n   ⚠️ No toots found. Recording 0 and moving to next movie...")
    else:
        print(f"\n   ✅ Done. Found {total_hashtags_found} toots.")

    return {
        'users': len(unique_users),
        'toots': total_hashtags_found,
        'servers': len(unique_servers),
        'favs': total_favorites,
        'boosts': total_boosts,
        'replies': total_replies,
        'next_id': current_max_id
    }


def main():
    if not os.path.exists(CSV_FILE):
        print("❌ CSV not found.")
        return

    df = pd.read_csv(CSV_FILE)
    df['watched_date'] = pd.to_datetime(df['watched_date'])
    
    # Initialize all columns (Identity + Volume + Engagement)
    required_cols = [
        'attendees', 'event_toots', 'unique_servers', 
        'total_favorites', 'total_boosts', 'total_replies'
    ]
    for col in required_cols:
        if col not in df.columns: 
            df[col] = None

    # Sort descending to go back in time
    # We look for films where 'attendees' is still empty
    missing_data = df[pd.isna(df['attendees'])].copy()
    missing_data = missing_data.sort_values('watched_date', ascending=False)
    
    if missing_data.empty:
        print("✨ All films updated.")
        return

    # 1. LOAD PERSISTENT ID
    last_max_id = None
    if os.path.exists(ID_FILE):
        with open(ID_FILE, 'r') as f:
            content = f.read().strip()
            # Robust check for empty or "None" strings
            if content and content != "None":
                last_max_id = content
                print(f"🔄 Resuming from saved ID: {last_max_id}")

    print(f"🧐 Processing batch of {BATCH_SIZE} films...")

    processed_count = 0
    for index, row in missing_data.iterrows():
        if processed_count >= BATCH_SIZE: 
            break

        movie_time = row['watched_date']
        duration = row['duration_minutes']
        
        # Validation for duration
        if pd.isna(duration) or duration <= 0: 
            print(f"⚠️ Skipping {row['title']} due to invalid duration.")
            continue

        if movie_time.tzinfo is None: 
            movie_time = LOCAL_TZ.localize(movie_time)

        print(f"[{processed_count+1}/{BATCH_SIZE}] Analyzing: {row['title']}...")
        
        try:
            # fetch_census_data now always returns a dict, even with 0 toots
            results = fetch_census_data(movie_time, duration, last_max_id)
            
            # Update the pointer (Crucial for leaping gaps!)
            last_max_id = results['next_id']

            # Update the DataFrame with all metrics
            df.at[index, 'attendees'] = results['users']
            df.at[index, 'event_toots'] = results['toots']
            df.at[index, 'unique_servers'] = results['servers']
            df.at[index, 'total_favorites'] = results['favs']
            df.at[index, 'total_boosts'] = results['boosts']
            df.at[index, 'total_replies'] = results['replies']
            
            # Save CSV state
            df_to_save = df.copy()
            df_to_save['watched_date'] = df_to_save['watched_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df_to_save.to_csv(CSV_FILE, index=False)
            
            # 2. SAVE PERSISTENT ID
            # We save this every time so we never lose our place in the timeline
            with open(ID_FILE, 'w') as f:
                f.write(str(last_max_id))
            
            print(f"   📍 Last max id updated to: {last_max_id}")

            processed_count += 1
            
            if processed_count < BATCH_SIZE:
                print(f"   😴 Sleeping {DELAY_BETWEEN_MOVIES} secs...")
                time.sleep(DELAY_BETWEEN_MOVIES)

        except Exception as e:
            print(f"   ❌ Error processing {row['title']}: {e}")
            # We break the loop on a hard error to prevent corrupting the CSV
            break

    print(f"\n🎉 Batch complete. Pointer saved to {ID_FILE}.")

if __name__ == "__main__":
    main()
