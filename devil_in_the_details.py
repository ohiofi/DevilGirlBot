import csv
import pandas as pd
import matplotlib.pyplot as plt
from mastodon import Mastodon
import os
from dotenv import load_dotenv

top_n_films = 5

load_dotenv()

mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social",
)



# def import_csv_as_dictionaries():
#     with open('Monsterdon - Sheet3.csv') as f:
#         mylist = [{k: v for k, v in row.items()}
#             for row in csv.DictReader(f, skipinitialspace=True)]
#     for each in mylist:
#         each["duration_minutes"] = int(each["duration_minutes"])
#         each["toots"] = int(each["toots"])
#     return mylist

def create_tpm_histogram(df, target_val, title, filename, latest_film_title):
    """Generates a histogram and highlights the bin containing the latest film."""
    plt.figure(figsize=(10, 6))
    
    # Calculate TPM for the group
    tpm_data = df['toots'] / df['duration_minutes']
    
    # Create the histogram
    n, bins, patches = plt.hist(tpm_data, bins=50, color='purple', edgecolor='black', alpha=0.7)
    
    # Highlight the specific bin where the target_val (latest film TPM) falls
    for i in range(len(bins)-1):
        if bins[i] <= target_val <= bins[i+1]:
            patches[i].set_facecolor('orange')
            patches[i].set_label(f'{latest_film_title} ({target_val:.2f} TPM)')
            break
            
    plt.title(title)
    plt.xlabel('Toots Per Minute (TPM)')
    plt.ylabel('Frequency')
    plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.savefig(filename)
    plt.close()

def get_rank_text(df_sorted, latest_title):
    """
    Returns a string formatted with the top 3 films by TPM 
    and the rank of the current film if it's not in the top 3.
    """
    lines = []
    # Find the current film's position in this specific sorted timeframe
    # We use .index[0] + 1 because index starts at 0
    current_film_row = df_sorted[df_sorted['title'] == latest_title]
    current_rank = current_film_row.index[0] + 1
    current_tpm = current_film_row['tpm'].values[0]
    current_year = current_film_row['release_year'].values[0]

    # Get Top N
    for i in range(min(top_n_films, len(df_sorted))):
        row = df_sorted.iloc[i]
        rank_mark = f"😈 #{i+1}: " if row['title'] == latest_title else f"#{i+1}: "
        lines.append(f"{rank_mark}{row['tpm']:.1f} TPM, {row['title']} ({row['release_year']})")

    # If the current film is not in the top N, add its specific rank at the bottom
    if current_rank > top_n_films:
        lines.append(f"...")
        lines.append(f"😈 #{current_rank}: {current_tpm:.1f} TPM, {latest_title} ({current_year})")

    return "\n".join(lines)

def main():
    # 1. Load and process data
    df = pd.read_csv('Monsterdon - Sheet3.csv', skipinitialspace=True)
    df['watched_date'] = pd.to_datetime(df['watched_date'])
    df['tpm'] = df['toots'] / df['duration_minutes']
    
    # Sort by date to get the most recent at the top
    df = df.sort_values('watched_date', ascending=False).reset_index(drop=True)
    
    latest_film = df.iloc[0]
    current_tpm = latest_film['tpm']
    
    # 2. Define the three timeframes
    # We use .copy() to avoid SettingWithCopy warnings
    last_4_weeks = df[df['watched_date'] >= (latest_film['watched_date'] - pd.Timedelta(weeks=4))].copy()
    last_52_weeks = df[df['watched_date'] >= (latest_film['watched_date'] - pd.Timedelta(weeks=52))].copy()
    all_time = df.copy()

    timeframes = [
        (last_4_weeks, "Last 4 Weeks", "hist_4w.png"),
        (last_52_weeks, "Last 52 Weeks", "hist_52w.png"),
        (all_time, "All Time", "hist_all.png")
    ]

    # 3. Post the Thread
    previous_post_id = None
    
    for i, (data, label, fname) in enumerate(timeframes):
        # 1. Sort the specific timeframe data by TPM for ranking
        # Note: 'data' is the filtered dataframe (4w, 52w, or all)
        df_ranked = data.sort_values('tpm', ascending=False).reset_index(drop=True)
        
        # 2. Generate the rank list text
        rank_list = get_rank_text(df_ranked, latest_film['title'])
        
        # 3. Create the chart
        print(f"Generating {label} chart...")
        create_tpm_histogram(df_ranked, current_tpm, f"Monsterdon TPM Analysis: {latest_film['title']} vs {label}", fname, latest_film['title'])
        
        # 4. Upload media
        print(f"Uploading {label} media to Mastodon (this may take a moment)...")
        media = mastodon.media_post(fname, description=f"Histogram of Toots Per Minute for Monsterdon {label}")

        # 5. Build the status text
        status_text = (
            f"😈📊 Monsterdon {label} Toots Per Minute Ranking 😈📊\n\n"
            f"{rank_list}\n\n"
            f"Comparison: {label}\n"
            f"Sample size: {len(data)} films\n"
            f"Data source: monsterdon-replay.gerlach.dev "
            f"#Monsterdon "
        )
        

        
        # Post (replying to previous if it exists)
        post = mastodon.status_post(
            status_text,
            media_ids=[media],
            in_reply_to_id=previous_post_id,
            visibility='public' # Options: 'public', 'unlisted', 'private', 'direct'
        )
        
        previous_post_id = post['id']
        print(f"Posted {label} chart.")

if __name__ == "__main__":
    main()