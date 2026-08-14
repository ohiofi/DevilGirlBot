import os, time
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
BATCH_SIZE = 4
DELAY_BETWEEN_MOVIES = 10

mastodon = Mastodon(
    access_token=os.getenv("access_token"), api_base_url="https://mastodon.social"
)


def export_attendance_txt_report(toots_list, film_title, watched_date_str):
    """
    Exports a numbered attendance list text file for a given screening.
    Ensures unique user identification using account IDs/full handles to prevent user collisions.
    """
    if not toots_list:
        print("⚠️ No toots provided for attendance report export.")
        return

    extracted_data = []
    for toot in toots_list:
        account_info = toot.get('account', {})
        
        # 1. Unique ID to prevent collapsing different users across instances
        user_id = account_info.get('id') or account_info.get('acct') or toot.get('id')
        
        # 2. Extract full handle (e.g., user@domain or user)
        full_acct = account_info.get('acct') or account_info.get('username') or 'unknown_user'
        
        # 3. Clean display username (keep instance domain if needed, or strip leading @)
        clean_user = str(full_acct).lstrip('@')
        # If you want local-only display names without remote domains:
        display_name = clean_user.split('@')[0]

        created_at = toot.get('created_at')

        extracted_data.append({
            'user_id': user_id,
            'clean_user': clean_user,
            'display_name': display_name,
            'created_at': created_at
        })

    df = pd.DataFrame(extracted_data)

    # Convert timestamps to UTC then Local TZ
    df['created_at'] = pd.to_datetime(df['created_at'], utc=True)
    df['created_at_local'] = df['created_at'].dt.tz_convert(LOCAL_TZ)

    # GROUP BY UNIQUE USER_ID (Not display_name!) to prevent merging attendees
    first_posts = (
        df.groupby('user_id')
        .agg({
            'display_name': 'first',
            'clean_user': 'first',
            'created_at_local': 'min'
        })
        .reset_index()
        .sort_values(by='created_at_local', ascending=True)
        .reset_index(drop=True)
    )

    # Format timestamp to local HH:MM:SS
    first_posts['first_post_time'] = first_posts['created_at_local'].dt.strftime('%H:%M:%S')

    # Target directory setup
    output_dir = "charts"
    os.makedirs(output_dir, exist_ok=True)
    
    date_clean = pd.to_datetime(watched_date_str).strftime('%Y%m%d')
    output_path = os.path.join(output_dir, f"attendance_{date_clean}.txt")

    # Assemble report text
    lines = [
        "==================================================",
        f"MONSTERDON ATTENDANCE REPORT: {film_title}",
        f"Total Attendees: {len(first_posts)}",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "==================================================\n"
    ]

    for idx, row in first_posts.iterrows():
        lines.append(f"{idx + 1}. {row['display_name']} - {row['first_post_time']}")

    report_content = "\n".join(lines)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_content)

    print(f"   📄 Attendance report saved to: {output_path} (Total Attendees: {len(first_posts)})")
    return output_path


def fetch_census_data(start_dt, duration, starting_max_id=None):
    """Fetches census data with Gap-Jumping logic to prevent backlog stalls."""
    # Ensure starting_max_id isn't the literal string "None"
    if starting_max_id == "None":
        starting_max_id = None
    
    # include the 10 minutes after the end of the film
    end_dt = start_dt + timedelta(minutes = int(duration) + 10) 
   
    unique_users = set()
    unique_servers = set()
    collected_toots = []  # <--- ACCUMULATOR LIST FOR ALL TOOTS IN TARGET WINDOW
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
            batch_toots = mastodon.timeline_hashtag("monsterdon", max_id=current_max_id, limit=40)
        except Exception as e:
            print(f"\n   ❌ API Error: {e}")
            break

        if not batch_toots:
            # This is the "Gap". We stop scrolling for this movie, 
            # but we return our current max_id so the next movie knows where to start.
            print("\n   ℹ️ Reached end of history or hit a paging gap.")
            break

        for toot in batch_toots:
            total_checked += 1
            created_at = toot["created_at"].astimezone(LOCAL_TZ)

            if start_dt <= created_at <= end_dt:
                unique_users.add(toot["account"]["acct"])
                server_domain = urlparse(toot["account"]["url"]).netloc
                unique_servers.add(server_domain)

                total_hashtags_found += 1
                collected_toots.append(toot)  # <--- APPEND TO ACCUMULATOR

                # Engagement Metrics
                total_favorites += toot.get('favourites_count', 0)
                total_boosts += toot.get('reblogs_count', 0)
                total_replies += toot.get('replies_count', 0)

            if created_at < start_dt:
                done = True
                break

        # Update the pointer to the last toot in this batch
        current_max_id = batch_toots[-1]["id"]
        
        current_pos = batch_toots[-1]["created_at"].astimezone(LOCAL_TZ).strftime("%Y-%m-%d %H:%M")
        print(
            f"   ⏳ Scrolling back... Checked: {total_checked} Currently at: {current_pos} Toots: {total_hashtags_found} Users: {len(unique_users)}",
            end="\r",
        )

    # --- THE GAP-JUMPER UPDATE ---
    if total_hashtags_found == 0:
        print(f"\n   ⚠️ No toots found. Recording 0 and moving to next movie...")
    else:
        print(f"\n   ✅ Done. Found {total_hashtags_found} toots.")
    
    return {
        'users': len(unique_users),
        'event_toots': total_hashtags_found,
        'servers': len(unique_servers),
        'favs': total_favorites,
        'boosts': total_boosts,
        'replies': total_replies,
        'next_id': current_max_id,
        'toots': collected_toots  # <--- RETURNS ALL 3,102 TOOTS IN WINDOW
    }


def get_attendance_report(index=0):
    """
    Fetches census toot data for a target film from history and exports an attendance text report.
    
    Parameters:
    - index (int): Offset position relative to the latest film.
                   index=0 -> Latest film
                   index=1 -> Next-to-last (2nd latest)
                   index=2 -> 3rd latest, etc.
    """
    if not os.path.exists(CSV_FILE):
        print(f"❌ CSV file not found: {CSV_FILE}")
        return

    # 1. Load details database and sort chronologically (oldest to newest)
    df = pd.read_csv(CSV_FILE)
    df['watched_date'] = pd.to_datetime(df['watched_date'])
    sorted_df = df.sort_values('watched_date', ascending=True).reset_index(drop=True)

    # 2. Select target row using negative positional indexing (-1 - index)
    target_pos = -1 - index
    
    # Boundary check to prevent IndexError
    if abs(target_pos) > len(sorted_df):
        print(f"❌ Index {index} out of range. Max index available is {len(sorted_df) - 1}.")
        return

    target_row = sorted_df.iloc[target_pos]

    # Extract film metadata
    title = target_row['title']
    year = int(target_row['release_year']) if 'release_year' in target_row and pd.notna(target_row['release_year']) else ""
    film_title = f"{title} ({year})" if year else title
    watched_date_str = target_row['watched_date'].strftime('%Y-%m-%d')
    movie_time = target_row['watched_date']
    duration = target_row['duration_minutes']

    if pd.isna(duration) or duration <= 0:
        print(f"⚠️ Invalid duration for {film_title}. Cannot generate report.")
        return

    if movie_time.tzinfo is None:
        movie_time = LOCAL_TZ.localize(movie_time)

    # 3. Read persistent ID pointer
    last_max_id = None
    if os.path.exists(ID_FILE):
        with open(ID_FILE, 'r') as f:
            content = f.read().strip()
            if content and content != "None":
                last_max_id = content

    print(f"🧐 Fetching attendance report [Offset Index: {index}] for: {film_title} ({watched_date_str})...")

    try:
        results = fetch_census_data(movie_time, duration, last_max_id)
        session_toots = results.get('toots', [])
        print(f"DEBUG: session_toots length = {len(session_toots)}")
        print(f"DEBUG: reported unique users count = {results.get('users')}")

        if not session_toots:
            print("⚠️ No toot records returned for this screening.")
            return

        # Export to text file
        export_attendance_txt_report(
            toots_list=session_toots,
            film_title=film_title,
            watched_date_str=watched_date_str
        )

    except Exception as e:
        print(f"❌ Error generating attendance report for index {index}: {e}")


def run_census_scan():
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

            # Calculate additional metrics
            engagementsPerToot = (results['favs'] + results['boosts']) / max(row['toots'], results['event_toots'])
            participationPerUser = ( max(row['toots'], results['event_toots']) + results['favs'] + results['boosts'] ) / results['users']

            # Update the DataFrame with all metrics
            df.at[index, 'attendees'] = results['users']
            df.at[index, 'event_toots'] = results['event_toots']
            df.at[index, 'unique_servers'] = results['servers']
            df.at[index, 'total_favorites'] = results['favs']
            df.at[index, 'total_boosts'] = results['boosts']
            df.at[index, 'total_replies'] = results['replies']
            df.at[index, 'engagement_score'] = engagementsPerToot
            df.at[index, 'participation_score'] = participationPerUser
            
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

def main():
    run_census_scan()
    # get_attendance_report(index=1)

if __name__ == "__main__":
    main()
