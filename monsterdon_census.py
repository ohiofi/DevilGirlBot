import os
import time
import pandas as pd
from datetime import datetime, timedelta
from mastodon import Mastodon
from urllib.parse import urlparse
from dotenv import load_dotenv
import pytz

# Mastodon has a rate limit (usually 300 requests per 5 minutes)
# --- Configuration ---
load_dotenv()
CSV_FILE = 'Monsterdon - Sheet3.csv'
LOCAL_TZ = pytz.timezone("US/Eastern") 
BATCH_SIZE = 10 
DELAY_BETWEEN_MOVIES = 2 

mastodon = Mastodon(
    access_token=os.getenv("access_token"),
    api_base_url='https://mastodon.social'
)

def fetch_census_data(start_dt, duration):
    """Fetches unique users, total toots, and unique servers for #Monsterdon."""
    end_dt = start_dt + timedelta(minutes=int(duration))
    unique_users = set()
    unique_servers = set()
    total_hashtags_found = 0
    max_id = None
    done = False

    while not done:
        toots = mastodon.timeline_hashtag('monsterdon', max_id=max_id, limit=40)
        if not toots:
            break

        for toot in toots:
            created_at = toot['created_at'].astimezone(LOCAL_TZ)
            
            if start_dt <= created_at <= end_dt:
                # 1. Track User
                acct = toot['account']['acct']
                unique_users.add(acct)
                
                # 2. Track Server 
                # If the user is remote, acct is 'user@domain.com'. 
                # If local, it's just 'user'. We'll use the account URL to be certain.
                server_domain = urlparse(toot['account']['url']).netloc
                unique_servers.add(server_domain)
                
                # 3. Track Volume
                total_hashtags_found += 1
            
            if created_at < start_dt:
                done = True
                break
        
        if not toots or done:
            break
        max_id = toots[-1]['id']
        
        if toots[-1]['created_at'].astimezone(LOCAL_TZ) < (start_dt - timedelta(days=1)):
            done = True

    return len(unique_users), total_hashtags_found, len(unique_servers)

def main():
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: {CSV_FILE} not found.")
        return

    df = pd.read_csv(CSV_FILE)
    df['watched_date'] = pd.to_datetime(df['watched_date'])
    
    # Ensure all three census columns exist
    for col in ['attendees', 'event_toots', 'unique_servers']:
        if col not in df.columns:
            df[col] = None

    # Filter for rows missing any of the three metrics
    missing_data = df[pd.isna(df['attendees']) | pd.isna(df['event_toots']) | pd.isna(df['unique_servers'])]
    
    if missing_data.empty:
        print("✨ All films already have complete census data!")
        return

    print(f"🧐 Found {len(missing_data)} films needing data. Processing batch of {BATCH_SIZE}...")

    processed_count = 0
    for index, row in missing_data.iterrows():
        if processed_count >= BATCH_SIZE:
            print(f"\n🛑 Batch limit reached. Run again later!")
            break

        movie_time = row['watched_date']
        duration = row['duration_minutes']
        
        if pd.isna(duration) or duration <= 0: continue
        if movie_time.tzinfo is None: movie_time = LOCAL_TZ.localize(movie_time)

        print(f"[{processed_count+1}/{BATCH_SIZE}] Analyzing: {row['title']}...")
        
        try:
            users, toots, servers = fetch_census_data(movie_time, duration)
            
            df.at[index, 'attendees'] = users
            df.at[index, 'event_toots'] = toots
            df.at[index, 'unique_servers'] = servers
            
            # Incremental Save
            df_to_save = df.copy()
            df_to_save['watched_date'] = df_to_save['watched_date'].dt.strftime('%Y-%m-%d %H:%M:%S')
            df_to_save.to_csv(CSV_FILE, index=False)
            
            print(f"   ✅ Saved: {users} users from {servers} servers ({toots} toots).")
            processed_count += 1
            time.sleep(DELAY_BETWEEN_MOVIES)

        except Exception as e:
            print(f"   ❌ Error on {row['title']}: {e}")
            break

    print(f"\n🎉 Batch complete. {processed_count} records updated.")

if __name__ == "__main__":
    main()