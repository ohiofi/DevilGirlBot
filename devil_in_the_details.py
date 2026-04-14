import csv
import pandas as pd
import matplotlib.pyplot as plt
from mastodon import Mastodon
import os
from dotenv import load_dotenv

DEBUG_MODE = True # Set to False when ready to post publicly
THIS_WEEKS_EMOJI = "🧛"
THIS_WEEKS_INDEX_LOCATION = 1 # use index 1 to skip double feature and treat the main film as latest
CSV_FILE = "details.csv"

load_dotenv()

mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social",
    request_timeout=40
)



# def import_csv_as_dictionaries():
#     with open(CSV_FILE) as f:
#         mylist = [{k: v for k, v in row.items()}
#             for row in csv.DictReader(f, skipinitialspace=True)]
#     for each in mylist:
#         each["duration_minutes"] = int(each["duration_minutes"])
#         each["toots"] = int(each["toots"])
#     return mylist



def get_deduplicated_df(df):
    """
    Returns a dataframe where each IMDB ID appears only once, 
    keeping the entry with the highest number of toots.
    """
    # Sort by ID, then by toots descending
    # drop_duplicates(keep='first') will now keep the one with the most toots
    return df.sort_values(['imdb_lookup', 'toots'], ascending=[True, False]).drop_duplicates(subset=['imdb_lookup'], keep='first')



def create_histogram(data_series, target_val, target_label, title, x_label, filename, histogram_color, bins=15):
    """Generates a histogram and highlights the bin containing the latest film."""
    plt.figure(figsize=(10, 6))
    
    # Create the histogram
    #n, bins, patches = plt.hist(tpm_data, bins=50, color='purple', edgecolor='black', alpha=0.7)
    n, bins_edges, patches = plt.hist(data_series, bins=bins, color=histogram_color, edgecolor='black', alpha=0.7)
    
    # Highlight the target value if one is provided
    if target_val is not None:
        for i in range(len(bins_edges)-1):
            if bins_edges[i] <= target_val <= bins_edges[i+1]:
                patches[i].set_facecolor('orange')
                patches[i].set_label(f'{target_label}')
                break
            
    plt.title(title)
    plt.xlabel(x_label)
    plt.ylabel('Frequency')
    if target_val is not None:
        plt.legend()
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()



def get_rank_text(df_sorted, latest_title, metric_col, unit, rank_start=1, rank_end=5, show_current=True):
    """Builds the ranking text. Shows Top N. Appends latest film if outside Top N."""
    lines = []
    
    current_film_row = df_sorted[df_sorted['title'] == latest_title]
    current_rank = current_film_row.index[0] + 1
    current_val = current_film_row[metric_col].values[0]
    current_year = current_film_row['release_year'].values[0]

    # Convert 1-based ranks to 0-based index for Pandas
    start_idx = rank_start - 1
    end_idx = min(rank_end, len(df_sorted))

    # Get the specific slice (e.g., 1-5 or 6-10)
    for i in range(start_idx, end_idx):
        row = df_sorted.iloc[i]
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if row['title'] == latest_title else f"#{i+1}: "
        
        # Format decimal for TPM, integer for volume/minutes
        val_str = f"{row[metric_col]:.1f}" if isinstance(row[metric_col], float) else f"{row[metric_col]}"
        lines.append(f"{rank_mark}{val_str} {unit}, {row['title']} ({row['release_year']})")

    # Append current film only if we want to show it AND it falls below our current visual range
    if show_current and current_rank > rank_end:
        lines.append(f"...")
        val_str = f"{current_val:.1f}" if isinstance(current_val, float) else f"{current_val}"
        lines.append(f"{THIS_WEEKS_EMOJI} #{current_rank}: {val_str} {unit}, {latest_title} ({current_year})")

    return "\n".join(lines)



def get_film_or_films(amount):
    if amount == 1:
        return "film"
    return "films"



def generate_decade_report(df):
    """Generates the Most Popular Decade report."""
    # 1. Deduplicate based on IMDB ID so we don't double-count 
    # movies appearing twice in the CSV.
    uniqueData = get_deduplicated_df(df)

    uniqueData['decade'] = (uniqueData['release_year'] // 10) * 10
    decade_counts = uniqueData['decade'].value_counts().reset_index()
    decade_counts.columns = ['decade', 'count']
    
    top_decades = decade_counts.head(9)
    lines = [f"😈📊 Most Popular Monsterdon Decades\n".upper()]
    for i, row in top_decades.iterrows():
        lines.append(f"#{i+1}: {row['decade']}s ({row['count']} {get_film_or_films(row['count'])})")
        
    text = "\n".join(lines)
    fname = "hist_decades.png"
    
    # Histogram of release years automatically shows decades if bins are set right
    min_year = uniqueData['decade'].min()
    max_year = uniqueData['decade'].max()
    bins = range(min_year, max_year + 20, 10) # 10-year bins
    
    create_histogram(uniqueData['release_year'], None, None, "Monsterdon Films by Decade", "Release Year", fname, "purple", bins=bins)
    
    return {'text': text, 'image': fname, 'desc': 'Histogram of Monsterdon films watched by decade'}



def generate_most_popular_actors(df):
    """
    Deduplicates films, counts actor appearances, 
    and returns two post dictionaries (1-5 and 6-10).
    """
    # 1. Deduplicate based on IMDB ID so we don't double-count 
    # movies appearing twice in the CSV.
    uniqueData = get_deduplicated_df(df)

    # 2. Split the 'actors' strings into lists and 'explode' them into individual rows
    # We strip whitespace to ensure ' Ringo Starr' and 'Ringo Starr' match.
    actor_series = uniqueData['actors'].str.split(',').explode().str.strip()
    
    # 3. Count occurrences
    actor_counts = actor_series.value_counts().reset_index()
    actor_counts.columns = ['actor', 'count']

    # --- Build Post 1: Top 1-5 ---
    lines1 = ["😈📊 Most Popular Monsterdon Actors: Top 5\n".upper()]
    for i in range(min(5, len(actor_counts))):
        row = actor_counts.iloc[i]
        lines1.append(f"#{i+1}: {row['actor']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post1 = {'text': "\n".join(lines1), 'image': None, 'desc': None}

    # --- Build Post 2: 6-10 ---
    lines2 = ["😈📊 Most Popular Monsterdon Actors: 6-10\n".upper()]
    # If we have fewer than 6 actors, this range will just be empty/ignored
    for i in range(5, min(10, len(actor_counts))):
        row = actor_counts.iloc[i]
        lines2.append(f"#{i+1}: {row['actor']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post2 = {'text': "\n".join(lines2), 'image': None, 'desc': None}

    #  # --- Build Post 3: 11-15 ---
    # lines3 = ["😈📊 Most Popular Monsterdon Actors: 11-15\n".upper()]
    # # If we have fewer than 11 actors, this range will just be empty/ignored
    # for i in range(10, min(15, len(actor_counts))):
    #     row = actor_counts.iloc[i]
    #     lines3.append(f"#{i+1}: {row['actor']} ({row['count']} {get_film_or_films(row['count'])})")
    
    # post3 = {'text': "\n".join(lines3), 'image': None, 'desc': None}

    # return [post1, post2, post3]

    return [post1, post2]



def generate_most_popular_directors(df):
    """
    Deduplicates films, counts director appearances (handling multiple directors), 
    and returns two post dictionaries (1-5 and 6-10).
    """
    # 1. Deduplicate based on IMDB ID
    unique_df = get_deduplicated_df(df)

    # 2. Split 'director' strings into lists and 'explode' into individual rows
    # This handles cases like "Kazuki Ômori, Kôji Hashimoto"
    director_series = unique_df['director'].str.split(',').explode().str.strip()
    
    # 3. Count occurrences
    director_counts = director_series.value_counts().reset_index()
    director_counts.columns = ['director', 'count']

    # --- Build Post 1: Top 1-5 ---
    lines1 = ["😈📊 Top Monsterdon Directors: 1-5\n".upper()]
    for i in range(min(5, len(director_counts))):
        row = director_counts.iloc[i]
        lines1.append(f"#{i+1}: {row['director']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post1 = {'text': "\n".join(lines1), 'image': None, 'desc': None}

    # --- Build Post 2: 6-10 ---
    lines2 = ["😈📊 Top Monsterdon Directors: 6-10\n".upper()]
    for i in range(5, min(10, len(director_counts))):
        row = director_counts.iloc[i]
        lines2.append(f"#{i+1}: {row['director']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post2 = {'text': "\n".join(lines2), 'image': None, 'desc': None}

    return [post1, post2]



def generate_longest_movies_report(df):
    """Generates the Longest Movies list (No histogram)."""
    # 1. Deduplicate based on IMDB ID
    uniqueData = get_deduplicated_df(df)
    df_sorted = uniqueData.sort_values('duration_minutes', ascending=False).reset_index(drop=True)
    
    lines = [f"😈📊 Longest Monsterdon Movies Watched \n".upper()]
    for i in range(min(5, len(df_sorted))):
        row = df_sorted.iloc[i]
        lines.append(f"#{i+1}: {row['duration_minutes']} mins, {row['title']} ({row['release_year']})")
        
    return {'text': "\n".join(lines), 'image': None, 'desc': None}



def create_timeframe_reports(df, latest_film, metric_col, unit, report_title):
    """Generates 4w, 52w, and two All Time reports (1-5 and 6-10) for any metric."""
    posts = []
    current_val = latest_film[metric_col]
    
    last_4_weeks = df[df['watched_date'] >= (latest_film['watched_date'] - pd.Timedelta(weeks=4))].copy()
    last_52_weeks = df[df['watched_date'] >= (latest_film['watched_date'] - pd.Timedelta(weeks=52))].copy()
    all_time = df.copy()

    # 1. Last 4 Weeks
    df_4w = last_4_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_4w = f"{metric_col}_4w.png"
    create_histogram(df_4w[metric_col], current_val, f"{latest_film['title']} ({latest_film['release_year']}): {current_val:.1f} {unit}", f"{report_title}: {latest_film['title']} ({latest_film['release_year']}) vs Last 4 Weeks", unit.upper(), fname_4w, "purple")
    text_4w = f"😈📊 {report_title.upper()}: Last 4 Weeks\n\n" + get_rank_text(df_4w, latest_film['title'], metric_col, unit, 1, 5, show_current=True)
    posts.append({'text': text_4w, 'image': fname_4w, 'desc': f'Histogram of {report_title} for Last 4 Weeks'})

    # 2. Last 52 Weeks
    df_52w = last_52_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_52w = f"{metric_col}_52w.png"
    create_histogram(df_52w[metric_col], current_val, f"{latest_film['title']} ({latest_film['release_year']}): {current_val:.1f} {unit}", f"{report_title}: {latest_film['title']} ({latest_film['release_year']}) vs Last 52 Weeks", unit.upper(), fname_52w, "purple")
    text_52w = f"😈📊 {report_title.upper()}: Last 52 Weeks\n\n" + get_rank_text(df_52w, latest_film['title'], metric_col, unit, 1, 5, show_current=True)
    posts.append({'text': text_52w, 'image': fname_52w, 'desc': f'Histogram of {report_title} for Last 52 Weeks'})

    # 3. All Time (Top 1-5)
    df_all = all_time.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_all = f"{metric_col}_all.png"
    create_histogram(df_all[metric_col], current_val, f"{latest_film['title']} ({latest_film['release_year']}): {current_val:.1f} {unit}", f"{report_title}: {latest_film['title']} ({latest_film['release_year']}) vs All Time", unit.upper(), fname_all, "purple")
    # Note: show_current=False here so it doesn't duplicate info if the movie is further down the list.
    text_all_1 = f"😈📊 {report_title.upper()}: All Time Top 5\n\n" + get_rank_text(df_all, latest_film['title'], metric_col, unit, 1, 5, show_current=False)
    posts.append({'text': text_all_1, 'image': fname_all, 'desc': f'Histogram of {report_title} for All Time'})

    # 4. All Time (Ranks 6-10) - No histogram attached to keep it clean
    text_all_2 = f"😈📊 {report_title.upper()}: All Time 6-10\n\n" + get_rank_text(df_all, latest_film['title'], metric_col, unit, 6, 10, show_current=True)
    posts.append({'text': text_all_2, 'image': None, 'desc': None})
        
    return posts



def post_thread(posts):
    """Iterates through the list and publishes them as a thread with numbering."""
    previous_post_id = None
    visibility = 'private' if DEBUG_MODE else 'public'
    total_posts = len(posts)
    
    for i, post_data in enumerate(posts):
        # Append thread numbering to the end of the text
        full_text = f"{post_data['text']}\n\n🧵 {i+1}/{total_posts}\n\n#DevilInTheDetails"
        
        print(f"Uploading post {i+1}/{total_posts}...")
        
        media_ids = []
        if post_data['image']:
            media = mastodon.media_post(post_data['image'], description=post_data['desc'])
            media_ids = [media]
            
        post = mastodon.status_post(
            full_text,
            media_ids=media_ids if media_ids else None,
            in_reply_to_id=previous_post_id,
            visibility=visibility
        )
        
        previous_post_id = post['id']
        print(f"✅ Posted {i+1}/{total_posts}")



def debug_print_thread(posts):
    """Prints the entire thread to the console with numbering appended."""
    total_posts = len(posts)

    print("\n" + "="*50)
    print("DEBUG MODE: SIMULATING THREAD OUTPUT")
    print("="*50 + "\n")
    
    for i, post_data in enumerate(posts):
        # Append thread numbering to the end of the text
        full_text = f"{post_data['text']}\n\n🧵 {i+1}/{total_posts}\n\n#DevilInTheDetails"
        
        print(f"--- POST {i+1}/{total_posts} ---")
        print(full_text)
        
        if post_data['image']:
            print(f"\n[IMAGE ATTACHED]: {post_data['image']}")
            print(f"[ALT TEXT]: {post_data['desc']}")
            
        print("\n" + "-"*30 + "\n")
        
    print("="*50)
    print(f"DEBUG COMPLETE: {len(posts)} posts generated.")
    print("="*50 + "\n")



def main():
    # 1. Load Data
    df = pd.read_csv(CSV_FILE, skipinitialspace=True)
    df['watched_date'] = pd.to_datetime(df['watched_date'])
    df['tpm'] = df['toots'] / df['duration_minutes']
    
    # Sort by date
    df = df.sort_values('watched_date', ascending=False).reset_index(drop=True)
    latest_film = df.iloc[THIS_WEEKS_INDEX_LOCATION] # use index 1 to skip double feature and treat the main film as latest
    
    # 2. Assemble Thread Content
    thread_posts = []
    
    # Post 1: Intro
    intro_text = (
        f"😈📊 DEVIL IN THE DETAILS 😈📊\n\n"
        f"An occasional thread with Monsterdon data rankings. This time it's the Most Popular Decades, Actors, Directors, and Toot Volume.\n"
        f"{THIS_WEEKS_EMOJI} {latest_film['title']} ({latest_film['release_year']})\n"
        f"Data sources: monsterdon-replay.gerlach.dev, imdb.com\n\n"
        f"#Monsterdon"
    )
    thread_posts.append({'text': intro_text, 'image': None, 'desc': None})
    
    # Decade Report
    thread_posts.append(generate_decade_report(df))
    
    # # TPM Reports
    # tpm_posts = create_timeframe_reports(df, latest_film, metric_col='tpm', unit='tpm', report_title='Monsterdon Toot Rate')
    # thread_posts.extend(tpm_posts)

    # Add the Actor reports
    actor_posts = generate_most_popular_actors(df)
    thread_posts.extend(actor_posts)

    # Add the Director reports 
    thread_posts.extend(generate_most_popular_directors(df))

    
    # # Longest Movies
    # thread_posts.append(generate_longest_movies_report(df))
    
    # Toot Volume Reports
    vol_posts = create_timeframe_reports(df, latest_film, metric_col='toots', unit='toots', report_title='Monsterdon Toot Volume')
    thread_posts.extend(vol_posts)

    # 3. Publish Thread
    if DEBUG_MODE:
        debug_print_thread(thread_posts)
    else:
        print("Beginning live thread publish sequence...")
        post_thread(thread_posts)
        print("🎉 Thread published successfully!")



if __name__ == "__main__":
    main()