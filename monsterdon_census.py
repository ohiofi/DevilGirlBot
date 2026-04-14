import os
import time
import pandas as pd
from datetime import datetime, timedelta
from mastodon import Mastodon
from dotenv import load_dotenv
import pytz

# --- Configuration ---
load_dotenv()
CSV_FILE = 'Monsterdon - Sheet3.csv'
LOCAL_TZ = pytz.timezone("US/Eastern") 
BATCH_SIZE = 5  # How many movies to process in one run
DELAY_BETWEEN_MOVIES = 2  # Seconds to wait between movies to be polite to the API

mastodon = Mastodon(
    access_token=os.getenv("access_token"),
    api_base_url='https://mastodon.social'
)

def fetch_census_data(start_dt, duration):
    """Fetches unique users and total toot volume for #Monsterdon."""
    end_dt = start_dt + timedelta(minutes=int(duration))
    unique_users = set()
    total_hashtags_found = 0
    max_id = None
    done = False

    while not done:
        # Each call here counts against your rate limit
        toots = mastodon.timeline_hashtag('monsterdon', max_id=max_id, limit=40)
        if not toots:
            break

        for toot in toots:
            created_at = toot['created_at'].astimezone(LOCAL_TZ)
            if start_dt <= created_at <= end_dt:
                unique_users.add(toot['account']['acct'])
                total_hashtags_found += 1
            if created_at < start_dt:
                done = True
                break
        
        if not toots or done:
            break
        max_id = toots[-1]['id']
        
        # Safety cutoff
        if toots[-1]['created_at'].astimezone(LOCAL_TZ) < (start_dt - timedelta(days=1)):
            done = True

    return len(unique_users), total_hashtags_found

def main():
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: {CSV_FILE} not found.")
        return

    df = pd.read_csv(CSV_FILE)
    df['watched_date'] = pd.to_datetime(df['watched_date'])
    
    if 'attendees' not in df.columns: df['attendees'] = None
    if 'event_toots' not in df.columns: df['event_toots'] = None

    # Filter for rows that actually need data
    missing_data = df[pd.isna(df['attendees']) | pd.isna(df['event_toots'])]
    
    if missing_data.empty:
        print("✨ All films already have census data!")
        return

    print(f"🧐 Found {len(missing_data)} films missing data. Processing a batch of {BATCH_SIZE}...")

    processed_count = 0
    for index, row in missing_data.iterrows():
        if processed_count >= BATCH_SIZE:
            print(f"\n🛑 Batch limit of {BATCH_SIZE} reached. Run the script again later!")
            break

        movie_time = row['watched_date']
        duration = row['duration_minutes']
        
        if pd.isna(duration) or duration <= 0: continue
        if movie_time.tzinfo is None: movie_time = LOCAL_TZ.localize(movie_time)

        print(f"[{processed_count+1}/{BATCH_SIZE}] Analyzing: {row['title']}...")
        
        try:
            user_count, toot_count = fetch_census_data(movie_time, duration)
            
            # Update the main dataframe
            df.at[index, 'attendees'] = user_count
            df.at[index, 'event_toots'] = toot_count
            
            # --- INCREMENTAL SAVE ---
            # We save after EVERY successful movie so progress is never lost.
            df_to_save = df.copy()
            df_to_save['watched_date'] = df_to_save['watched_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df_to_save.to_csv(CSV_FILE, index=False)
            
            print(f"   ✅ Saved: {user_count} users, {toot_count} toots.")
            processed_count += 1
            
            # Short sleep to avoid hitting rate limits too fast
            time.sleep(DELAY_BETWEEN_MOVIES)

        except Exception as e:
            print(f"   ❌ Error on {row['title']}: {e}")
            print("Stopping batch to be safe.")
            break

    print(f"\n🎉 Batch complete. {processed_count} records updated in {CSV_FILE}.")

if __name__ == "__main__":
    main()