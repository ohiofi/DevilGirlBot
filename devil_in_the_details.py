import csv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from mastodon import Mastodon
import os
from dotenv import load_dotenv

# NOTE: Run this manually in terminal venv. Always crashes/times-out if I try to run via VSCode play button.

DEBUG_MODE = True # Set to False when ready to post publicly
THIS_WEEKS_EMOJI = "🐺"
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



def create_histogram(data_series, target_val, target_label, title, x_label, filename, histogram_color, bins=15, subtitle="", useMillions=False):
    """
    Generates a histogram. 
    If useMillions is True, scales data by 1,000,000 and updates axis labels.
    """
    output_dir = "charts"
    os.makedirs(output_dir, exist_ok=True) # Create 'charts/' folder if missing
    full_path = os.path.join(output_dir, filename)

    plt.figure(figsize=(15, 9))
    
    # 1. Scale data if necessary
    plot_data = data_series.copy()
    plot_target = target_val
    
    if useMillions and target_val != -1:
        plot_data = plot_data / 1_000_000
        plot_target = target_val / 1_000_000
        display_x_label = f"{x_label} (in Millions)"
    else:
        display_x_label = x_label

    # 2. Create the histogram
    n, bins_edges, patches = plt.hist(plot_data, bins=bins, color=histogram_color, edgecolor='black', alpha=0.7)
    
    # 3. Highlight the target value (this week's film)
    if plot_target is not None and plot_target != -1:
        for i in range(len(bins_edges)-1):
            if bins_edges[i] <= plot_target <= bins_edges[i+1]:
                patches[i].set_facecolor('orange')
                patches[i].set_label(f'{target_label}')
                break
    
    # 4. Titles and Subtitles
    plt.suptitle(title, fontsize=14, fontweight='bold', y=0.98)
    if subtitle:
        plt.title(subtitle, fontsize=10, color="#444444", pad=15)
    else:
        plt.title("", pad=10)

    plt.xlabel(display_x_label)
    plt.ylabel('Number of Monsterdon Films')

    # This forces the y-axis to only show whole numbers
    plt.gca().yaxis.set_major_locator(ticker.MaxNLocator(integer=True))
    
    if plot_target is not None and plot_target != -1:
        plt.legend(loc='upper right')
        
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    plt.savefig(full_path)
    plt.close()



def create_horizontal_bar_chart(df_sorted, metric_col, target_title, title, x_label, filename, bar_color, subtitle="", useMillions=False, decimals=2):
    """Generates a sorted horizontal bar chart for the 4-week window."""
    output_dir = "charts"
    os.makedirs(output_dir, exist_ok=True) # Create 'charts/' folder if missing
    full_path = os.path.join(output_dir, filename)

    plt.figure(figsize=(15, 9 + len(df_sorted)*0.025))
    # plt.figure(figsize=(15, 9))
    
    # Work on a copy to avoid modifying the original df
    plot_df = df_sorted.copy()
    
    # Scale if necessary
    if useMillions:
        plot_df[metric_col] = plot_df[metric_col] / 1_000_000
        display_x_label = f"{x_label} (MILLIONS)"
    else:
        display_x_label = x_label

    # Matplotlib plots from bottom to top, so we reverse to get the leader at the top
    plot_df = plot_df.iloc[::-1]

    # Create bars
    bars = plt.barh(plot_df['title_and_year'], plot_df[metric_col], color=bar_color, edgecolor='black', alpha=0.8)

    # Highlight target film and add labels to bars
    for bar, title_label, val in zip(bars, plot_df['title_and_year'], plot_df[metric_col]):
        # Formatting for the label on the bar
        label_str = f"{val:,.{decimals}f}"
        font_weight = 'normal'
        if title_label == target_title:
            bar.set_facecolor('orange')
            # font_weight = 'bold'
        
        # Add the numeric value to the end of the bar for quick reading
        plt.text(bar.get_width(), bar.get_y() + bar.get_height()/2, 
                 f' {label_str}', va='center', fontweight=font_weight)

    # Titles and Subtitles
    plt.suptitle(title, fontsize=14, fontweight='bold', y=0.98)
    if subtitle:
        plt.title(subtitle, fontsize=10, color='#666666', pad=15)
    else:
        plt.title("", pad=10)

    plt.xlabel(display_x_label)
    
    # Format X-axis with commas/decimals
    plt.gca().xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.2f}' if decimals > 0 else '{x:,.0f}'))
    
    plt.grid(axis='x', linestyle='--', alpha=0.5)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    plt.savefig(full_path)
    plt.close()


def create_lollipop_chart(df_sorted, metric_col, target_title, title, x_label, filename, color, subtitle="", useMillions=False, decimals=2):
    """Generates a clean horizontal lollipop chart for the 26-week window."""
    output_dir = "charts"
    os.makedirs(output_dir, exist_ok=True) # Create 'charts/' folder if missing
    full_path = os.path.join(output_dir, filename)

    tiny_font_size = 10
    # Adjust figure size slightly taller to give 26 rows breathing room
    plt.figure(figsize=(9, 7)) 
    
    plot_df = df_sorted.copy()
    if useMillions:
        plot_df[metric_col] = plot_df[metric_col] / 1_000_000
        display_x_label = f"{x_label} (MILLIONS)"
    else:
        display_x_label = x_label

    # Reverse for top-down leaderboard display
    plot_df = plot_df.iloc[::-1]

    max_val = plot_df[metric_col].max() if not plot_df[metric_col].empty else 1
    x_offset = max_val * 0.015

    # 1. Draw the "sticks"
    stickColor = ['orange' if t == target_title else color for t in plot_df['title']]
    plt.hlines(y=plot_df['title_and_year'], xmin=0, xmax=plot_df[metric_col], 
               color=stickColor, linestyle='-', alpha=0.8, linewidth=4)
    
    # 2. Draw the "pops" (dots)
    # Create a color list to highlight the target film
    colors = ['orange' if t == target_title else color for t in plot_df['title']]
    sizes = [15 if t == target_title else 10 for t in plot_df['title']]
    
    plt.scatter(plot_df[metric_col], plot_df['title_and_year'], c=colors, s=sizes, 
                edgecolor=colors, alpha=1, zorder=3)

    # Add numeric labels to the right of the dots
    for title_label, val in zip(plot_df['title_and_year'], plot_df[metric_col]):
        label_str = f"{val:,.{decimals}f}"
        # font_weight = 'bold' if target_title in title_label else 'normal'
        font_weight = 'normal'
        plt.text(val + x_offset, title_label, f' {label_str}', va='center',ha='left', fontsize=tiny_font_size, fontweight=font_weight)

    # Titles and Axis Formatting
    plt.suptitle(title, fontsize=14, fontweight='bold', y=0.96)
    if subtitle:
        plt.title(subtitle, fontsize=10, color='#555555', pad=15)
    
    plt.xlabel(display_x_label)
    plt.yticks(fontsize=tiny_font_size) # Sized down slightly so 26 titles don't overlap
    #plt.gca().xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.2f}' if decimals > 0 else '{x:,.0f}'))
    # Snap text to the sticks
    plt.gca().tick_params(axis='y', pad=2)
    plt.xlim(0, max_val * 1.12)
    
    plt.gca().xaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.2f}' if decimals > 0 else '{x:,.0f}'))

    plt.grid(axis='x', linestyle='--', alpha=0.3)
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    
    plt.savefig(full_path)
    plt.close()

def create_timeline_reports(df, latest_film, metric_col, unit, report_title, subtitle="", isDollars=False, useMillions=False, decimals=2):
    """
    Generates chronological timeline charts but formats the accompanying post text
    as classic leaderboard ranking summary threads.
    """
    current_val = latest_film[metric_col]
    if current_val == -1:
        print(f"⚠️ Skipping {report_title} timeline: Current film has no data (-1).")
        return []

    clean_df = df[df[metric_col] != -1].copy()
    posts = []

    ref_date = pd.Timestamp.now()
    sub_text = f"{subtitle}\n" if subtitle else ""

    # --- 1. Last 4 Weeks Timeline ---
    last_4_weeks = clean_df[clean_df['watched_date'] > (ref_date - pd.Timedelta(weeks=4))].copy()
    # Sort descending for the rank generator engine
    df_04w_ranked = last_4_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_04w_line = f"{metric_col}_timeline_04w.png"
    
    create_timeline_trend_chart(
        df_chronological=last_4_weeks,
        metric_col=metric_col,
        target_identifier=latest_film['title_and_year'],
        title=f"{report_title}: 4-Week Chronological View",
        y_label=unit.upper(),
        filename=fname_04w_line,
        bar_color="purple",
        subtitle=subtitle,
        useMillions=useMillions,
        decimals=decimals,
        show_x_labels=True
    )
    
    # Generate old-style leaderboard text using the rank engine
    text_04w_line = f"😈📊 {report_title.upper()}: Last 4 Weeks\n{sub_text}" + \
                    get_rank_text(df_04w_ranked, latest_film['title'], metric_col, unit, 1, 5, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_04w_line, 'image': os.path.join("charts", fname_04w_line), 'desc': f'Chronological bar chart of {report_title} for Last 4 Weeks'})

    # --- 2. Last 16 Weeks Timeline ---
    last_16_weeks = clean_df[clean_df['watched_date'] > (ref_date - pd.Timedelta(weeks=16))].copy()
    # Sort descending for the rank generator engine
    df_16w_ranked = last_16_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_16w_line = f"{metric_col}_timeline_16w.png"
    
    create_timeline_trend_chart(
        df_chronological=last_16_weeks,
        metric_col=metric_col,
        target_identifier=latest_film['title_and_year'],
        title=f"{report_title}: 16-Week Chronological View",
        y_label=unit.upper(),
        filename=fname_16w_line,
        bar_color="purple",
        subtitle=subtitle,
        useMillions=useMillions,
        decimals=decimals,
        show_x_labels=True
    )
    
    # Generate old-style leaderboard text using the rank engine
    text_16w_line = f"😈📊 {report_title.upper()}: Last 16 Weeks\n{sub_text}" + \
                    get_rank_text(df_16w_ranked, latest_film['title'], metric_col, unit, 1, 5, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_16w_line, 'image': os.path.join("charts", fname_16w_line), 'desc': f'Chronological bar chart of {report_title} for Last 16 Weeks'})

    # --- 3. All Time History Timeline (Top 1-5) ---
    all_time = clean_df.copy()
    df_all_ranked = all_time.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_all_line = f"{metric_col}_timeline_all.png"
    
    create_timeline_trend_chart(
        df_chronological=all_time,
        metric_col=metric_col,
        target_identifier=latest_film['title_and_year'],
        title=f"{report_title}: All-Time Chronological View",
        y_label=unit.upper(),
        filename=fname_all_line,
        bar_color="purple",
        subtitle=subtitle,
        useMillions=useMillions,
        decimals=decimals,
        show_x_labels=False # Kept False to hide chaotic layout strings
    )
    
    # Generate old-style leaderboard text for the top 5 spots
    text_all_line = f"😈📊 {report_title.upper()}: All Time Top 5\n{sub_text}" + \
                    get_rank_text(df_all_ranked, latest_film['title'], metric_col, unit, 1, 5, show_current=False, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_all_line, 'image': os.path.join("charts", fname_all_line), 'desc': f'Chronological bar chart of {report_title} across All-Time rows'})

    # --- 4. All Time History Timeline (Ranks 6-10 Text-Only fallback) ---
    text_all_2 = f"😈📊 {report_title.upper()}: All Time 6-10\n{sub_text}" + \
                 get_rank_text(df_all_ranked, latest_film['title'], metric_col, unit, 6, 10, show_current=True, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_all_2, 'image': None, 'desc': None})

    return posts

def create_timeline_trend_chart(df_chronological, metric_col, target_identifier, title, y_label, filename, bar_color, subtitle="", useMillions=False, decimals=2, show_x_labels=True):
    """
    Generates a vertical bar chart where EVERY individual row gets its own equidistant bar.
    No rows are collapsed or grouped.
    """
    output_dir = "charts"
    os.makedirs(output_dir, exist_ok=True)
    full_path = os.path.join(output_dir, filename)

    # Sort strictly by date, oldest to newest (left to right) without collapsing rows
    plot_df = df_chronological.sort_values('watched_date', ascending=True).copy()

    if useMillions:
        plot_df[metric_col] = plot_df[metric_col] / 1_000_000
        display_y_label = f"{y_label} (MILLIONS)"
    else:
        display_y_label = y_label

    plt.figure(figsize=(12, 6))

    colors = ['yellow' if t == target_identifier else bar_color for t in plot_df['title_and_year']]

    # --- THE EQUIDISTANT SEQUENTIAL POSITION FIX ---
    # We place bars at positions [0, 1, 2, 3...] so duplicate films sit side-by-side instead of overlapping
    x_positions = range(len(plot_df))
    bars = plt.bar(x_positions, plot_df[metric_col], color=colors, edgecolor='black', alpha=0.85, zorder=3)

    # Only print numeric values on top of bars if the layout isn't overcrowded
    if len(plot_df) <= 20:
        for bar in bars:
            y_val = bar.get_height()
            label_str = f"{y_val:,.{decimals}f}"
            
            is_target = (bar.get_facecolor() == (1.0, 1.0, 0.0, 0.85))
            font_w = 'bold' if is_target else 'normal'
            
            plt.text(bar.get_x() + bar.get_width()/2, y_val, f"{label_str}", 
                     va='bottom', ha='center', fontsize=8, fontweight=font_w)

    # --- X-AXIS CUSTOM LABEL MAPPING ---
    if show_x_labels:
        # Assigned size=7 so long movie titles don't overpower the canvas height
        plt.xticks(
            ticks=x_positions, 
            labels=plot_df['title_and_year'], 
            rotation=45, 
            ha='right', 
            fontsize=7, # <--- Dropped from 9 to 7
            rotation_mode='anchor' # Ensures cleaner alignment at 45 degrees
        )
        bottom_margin = 0.02  # <--- Safely reduced from 0.28 since font is smaller
    else:
        # Strip all text and structural tick markers for the All Time view
        plt.gca().set_xticklabels([]) 
        plt.gca().set_xticks([])      
        plt.xlabel("Monsterdon Sessions Over Time", fontsize=10, labelpad=10)
        bottom_margin = 0.01  # <--- Tighter layout padding

    # Titles and Formatting
    plt.suptitle(title, fontsize=14, fontweight='bold', y=0.96)
    if subtitle:
        plt.title(subtitle, fontsize=10, color='#555555', pad=10)

    plt.ylabel(display_y_label)
    
    max_val = plot_df[metric_col].max() if not plot_df[metric_col].empty else 1
    plt.ylim(0, max_val * 1.12)
    
    plt.gca().yaxis.set_major_formatter(ticker.StrMethodFormatter('{x:,.2f}' if decimals > 0 else '{x:,.0f}'))
    plt.grid(axis='y', linestyle='--', alpha=0.3, zorder=1)
    
    plt.tight_layout(rect=[0, bottom_margin, 1, 0.90])
    
    plt.savefig(full_path)
    plt.close()

def get_rank_text(df_sorted, latest_title, metric_col, unit, rank_start=1, rank_end=5, show_current=True, isDollars=False, useMillions=False, decimals=2):
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
        
        val = row[metric_col]
        
        if val == -1:
            val_str = "N/A"
        else:
            # 1. Handle Million conversion
            display_val = val / 1_000_000 if useMillions else val
            
            # 2. Handle Formatting with dynamic decimals
            # The {decimals} inside the f-string sets the precision
            if isDollars or useMillions:
                val_str = f"{display_val:,.{decimals}f}"
            else:
                # Still uses commas for large non-dollar numbers, but respects precision
                val_str = f"{display_val:,.{decimals}f}"
            
        lines.append(f"{rank_mark}{val_str} {unit}, {row['title']} ({row['release_year']})")

    if show_current and current_rank > rank_end:
        lines.append(f"...")
        if current_val == -1:
            val_str = "N/A"
        else:
            display_val = current_val / 1_000_000 if useMillions else current_val
            val_str = f"{display_val:,.{decimals}f}"
            
        lines.append(f"{THIS_WEEKS_EMOJI} #{current_rank}: {val_str} {unit}, {latest_title} ({current_year})")

    return "\n".join(lines)



def get_film_or_films(amount):
    if amount == 1:
        return "film"
    return "films"



def generate_decade_report(df, latest_film):
    """Generates the Most Popular Decade report."""

    # Get the decade of the film we just watched
    latest_decade = (latest_film['release_year'] // 10) * 10

    # Deduplicate based on IMDB ID so we don't double-count 
    # movies appearing twice in the CSV.
    uniqueData = get_deduplicated_df(df)

    uniqueData['decade'] = (uniqueData['release_year'] // 10) * 10
    decade_counts = uniqueData['decade'].value_counts().reset_index()
    decade_counts.columns = ['decade', 'count']
    
    top_decades = decade_counts.head(9)
    lines = [f"😈📊 Most Popular Monsterdon Decades\n".upper()]
    for i, row in top_decades.iterrows():
        # Add the emoji if this row matches the decade of the latest film
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if row['decade'] == latest_decade else f"#{i+1}: "
        lines.append(f"{rank_mark}{row['decade']}s ({row['count']} {get_film_or_films(row['count'])})")
    text = "\n".join(lines)
    fname = "hist_decades.png"
    
    # Histogram of release years automatically shows decades if bins are set right
    min_year = uniqueData['decade'].min()
    max_year = uniqueData['decade'].max()
    bins = range(min_year, max_year + 20, 10) # 10-year bins
    
    create_histogram(uniqueData['release_year'], None, None, "Monsterdon Films by Decade", "Release Year", fname, "purple", bins=bins)
    
    return {'text': text, 'image': fname, 'desc': 'Histogram of Monsterdon films watched by decade'}



def generate_most_popular_actors(df, latest_film):
    """
    Deduplicates films, counts actor appearances, 
    and returns two post dictionaries (1-5 and 6-10).
    """
    # Get this week's actors as a clean list for comparison
    # Handles strings like "Geena Davis, Jeff Goldblum, Jim Carrey"
    latest_actors_str = str(latest_film.get('actors', ""))
    latest_actors_list = [a.strip() for a in latest_actors_str.split(',') if a.strip()]
    
    # Deduplicate based on IMDB ID so we don't double-count 
    # movies appearing twice in the CSV.
    uniqueData = get_deduplicated_df(df)

    # Split the 'actors' strings into lists and 'explode' them into individual rows
    # We strip whitespace to ensure ' Ringo Starr' and 'Ringo Starr' match.
    actor_series = uniqueData['actors'].str.split(',').explode().str.strip()
    
    # Count occurrences
    actor_counts = actor_series.value_counts().reset_index()
    actor_counts.columns = ['actor', 'count']

    # --- Build Post 1: Top 1-5 ---
    lines1 = ["😈📊 Most Popular Monsterdon Actors: Top 5\n".upper()]
    for i in range(min(5, len(actor_counts))):
        row = actor_counts.iloc[i]
        
        # Highlight if the actor is in this week's list
        is_this_week = row['actor'] in latest_actors_list
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if is_this_week else f"#{i+1}: "
        
        lines1.append(f"{rank_mark}{row['actor']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post1 = {'text': "\n".join(lines1), 'image': None, 'desc': None}

    # --- Build Post 2: 6-10 ---
    lines2 = ["😈📊 Most Popular Monsterdon Actors: 6-10\n".upper()]
    # If we have fewer than 6 actors, this range will just be empty/ignored
    for i in range(5, min(10, len(actor_counts))):
        row = actor_counts.iloc[i]
        
        # Highlight logic again for the second post
        is_this_week = row['actor'] in latest_actors_list
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if is_this_week else f"#{i+1}: "
        
        lines2.append(f"{rank_mark}{row['actor']} ({row['count']} {get_film_or_films(row['count'])})")
    
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



def generate_most_popular_directors(df, latest_film):
    """
    Deduplicates films, counts director appearances (handling multiple directors), 
    and returns two post dictionaries (1-5 and 6-10).
    """
    # Cleanly parse this week's director(s)
    latest_dirs_str = str(latest_film.get('director', ""))
    latest_dirs_list = [d.strip() for d in latest_dirs_str.split(',') if d.strip()]
    
    # Deduplicate based on IMDB ID
    unique_df = get_deduplicated_df(df)

    # Split 'director' strings into lists and 'explode' into individual rows
    # This handles cases like "Kazuki Ômori, Kôji Hashimoto"
    director_series = unique_df['director'].str.split(',').explode().str.strip()
    
    # Count occurrences
    director_counts = director_series.value_counts().reset_index()
    director_counts.columns = ['director', 'count']

    # --- Build Post 1: Top 1-5 ---
    lines1 = ["😈📊 Top Monsterdon Directors: Top 5\n".upper()]
    for i in range(min(5, len(director_counts))):
        row = director_counts.iloc[i]
        
        # Check if this director is one of the directors from tonight's film
        is_this_week = row['director'] in latest_dirs_list
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if is_this_week else f"#{i+1}: "
        
        lines1.append(f"{rank_mark}{row['director']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post1 = {'text': "\n".join(lines1), 'image': None, 'desc': None}

    # --- Build Post 2: 6-10 ---
    lines2 = ["😈📊 Top Monsterdon Directors: 6-10\n".upper()]
    for i in range(5, min(10, len(director_counts))):
        row = director_counts.iloc[i]
        
        is_this_week = row['director'] in latest_dirs_list
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if is_this_week else f"#{i+1}: "
        
        lines2.append(f"{rank_mark}{row['director']} ({row['count']} {get_film_or_films(row['count'])})")
    
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



def generate_most_popular_genres(df, latest_film):
    """
    Deduplicates films, counts genre appearances (handling multiples), 
    and highlights genres from the latest film in the rankings.
    """
    # 1. Cleanly parse this week's genre(s)
    latest_genres_str = str(latest_film.get('genre', ""))
    latest_genres_list = [g.strip() for g in latest_genres_str.split(',') if g.strip()]

    # 2. Deduplicate based on IMDB ID
    unique_df = get_deduplicated_df(df)

    # 3. Split and explode for all-time counts
    # This handles "Action, Horror, Sci-Fi" by creating 3 rows for that one movie
    genre_series = unique_df['genre'].str.split(',').explode().str.strip()
    
    # 4. Count occurrences
    genre_counts = genre_series.value_counts().reset_index()
    genre_counts.columns = ['genre', 'count']

    # --- Build Post 1: Top 1-5 ---
    lines1 = ["😈📊 Most Popular Monsterdon Genres: 1-5\n".upper()]
    for i in range(min(5, len(genre_counts))):
        row = genre_counts.iloc[i]
        
        # Check if this genre is part of tonight's movie
        is_this_week = row['genre'] in latest_genres_list
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if is_this_week else f"#{i+1}: "
        
        lines1.append(f"{rank_mark}{row['genre']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post1 = {'text': "\n".join(lines1), 'image': None, 'desc': None}

    # --- Build Post 2: 6-10 ---
    lines2 = ["😈📊 Most Popular Monsterdon Genres: 6-10\n".upper()]
    for i in range(5, min(10, len(genre_counts))):
        row = genre_counts.iloc[i]
        
        is_this_week = row['genre'] in latest_genres_list
        rank_mark = f"{THIS_WEEKS_EMOJI} #{i+1}: " if is_this_week else f"#{i+1}: "
        
        lines2.append(f"{rank_mark}{row['genre']} ({row['count']} {get_film_or_films(row['count'])})")
    
    post2 = {'text': "\n".join(lines2), 'image': None, 'desc': None}

    return [post1, post2]



def create_timeframe_reports(df, latest_film, metric_col, unit, report_title, subtitle="", isDollars=False, useMillions=False, decimals=2):
    """Generates 4w, 52w, and All Time reports, skipping records where metric is -1."""
    
    # 1. Guard Clause: Skip if the current film has no data for this metric
    current_val = latest_film[metric_col]
    if current_val == -1:
        print(f"⚠️ Skipping {report_title} report: Current film has no data (-1).")
        return []

    # 2. Filter the main dataframe to exclude "null" (-1) values
    # This ensures ranks and histograms only include valid data
    clean_df = df[df[metric_col] != -1].copy()

    posts = []

    # Use clean_df for all timeframe slices
    #ref_date = latest_film['watched_date']
    ref_date = pd.Timestamp.now()
    last_4_weeks = clean_df[clean_df['watched_date'] > (ref_date - pd.Timedelta(weeks=4))].copy()
    
    
    
    

    # Formatting helper for the histogram labels
    target_val_display = current_val / 1_000_000 if useMillions else current_val
    target_label = f"{latest_film['title']}: {target_val_display:,.{decimals}f} {unit}"

    # --- 1. Last 4 Weeks (NOW A BAR CHART) ---
    df_04w = last_4_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_04w = f"{metric_col}_04w.png"
    
    create_horizontal_bar_chart(
        df_04w, 
        metric_col, 
        latest_film['title_and_year'], 
        f"{report_title}: Last 4 Weeks", 
        unit.upper(), 
        fname_04w, 
        "purple", 
        subtitle=subtitle, 
        useMillions=useMillions, 
        decimals=decimals
    )
    
    text_04w = f"😈📊 {report_title.upper()}: Last 4 Weeks\n{subtitle}\n" + \
              get_rank_text(df_04w, latest_film['title'], metric_col, unit, 1, 5, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_04w, 'image': os.path.join("charts", fname_04w), 'desc': f'Bar chart of {report_title} for Last 4 Weeks'})

    # ---  Last 12 Weeks ---
    # last_12_weeks = clean_df[clean_df['watched_date'] > (ref_date - pd.Timedelta(weeks=12))].copy()
    # df_12w = last_12_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    # fname_12w = f"{metric_col}_12w.png"
    # create_horizontal_bar_chart(
    #     df_12w, 
    #     metric_col, 
    #     latest_film['title_and_year'], 
    #     f"{report_title}: Last 12 Weeks", 
    #     unit.upper(), 
    #     fname_12w, 
    #     "purple", 
    #     subtitle=subtitle, 
    #     useMillions=useMillions, 
    #     decimals=decimals
    # )   
    # text_12w = f"😈📊 {report_title.upper()}: Last 12 Weeks\n{subtitle}\n" + \
    #           get_rank_text(df_12w, latest_film['title'], metric_col, unit, 1, 5, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    # posts.append({'text': text_12w, 'image': fname_12w, 'desc': f'Bar chart of {report_title} for Last 12 Weeks'})

    # # ---  Last 16 Weeks ---
    last_16_weeks = clean_df[clean_df['watched_date'] > (ref_date - pd.Timedelta(weeks=16))].copy()
    df_16w = last_16_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_16w = f"{metric_col}_16w.png"
    create_horizontal_bar_chart(
        df_16w, 
        metric_col, 
        latest_film['title_and_year'], 
        f"{report_title}: Last 16 Weeks", 
        unit.upper(), 
        fname_16w, 
        "purple", 
        subtitle=subtitle, 
        useMillions=useMillions, 
        decimals=decimals
    )   
    text_16w = f"😈📊 {report_title.upper()}: Last 16 Weeks\n{subtitle}\n" + \
              get_rank_text(df_16w, latest_film['title'], metric_col, unit, 1, 5, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_16w, 'image': os.path.join("charts", fname_16w), 'desc': f'Bar chart of {report_title} for Last 16 Weeks'})

    # ---  Last 26 Weeks ---
    # last_26_weeks = clean_df[clean_df['watched_date'] > (ref_date - pd.Timedelta(weeks=26))].copy()
    # df_26w = last_26_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    # fname_26w = f"{metric_col}_26w.png"
    # create_horizontal_bar_chart(
    #     df_26w, 
    #     metric_col, 
    #     latest_film['title_and_year'], 
    #     f"{report_title}: Last 26 Weeks", 
    #     unit.upper(), 
    #     fname_26w, 
    #     "purple", 
    #     subtitle=subtitle, 
    #     useMillions=useMillions, 
    #     decimals=decimals
    # )   
    # text_26w = f"😈📊 {report_title.upper()}: Last 6 Months\n{subtitle}\n" + \
    #           get_rank_text(df_26w, latest_film['title'], metric_col, unit, 1, 5, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    # posts.append({'text': text_26w, 'image': os.path.join("charts", fname_26w), 'desc': f'Bar chart of {report_title} for Last 6 Months'})

    # --- Last 52 Weeks ---
    # last_52_weeks = clean_df[clean_df['watched_date'] > (ref_date - pd.Timedelta(weeks=52))].copy()
    # df_52w = last_52_weeks.sort_values(metric_col, ascending=False).reset_index(drop=True)
    # fname_52w = f"{metric_col}_52w.png"
    # create_histogram(df_52w[metric_col], current_val, target_label, 
    #                  f"{report_title}: Last 52 Weeks", unit.upper(), fname_52w, "purple", 80, subtitle, useMillions)
    
    # text_52w = f"😈📊 {report_title.upper()}: Last 52 Weeks\n{subtitle}\n\n" + get_rank_text(df_52w, latest_film['title'], metric_col, unit, 1, 5, show_current=True, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    # posts.append({'text': text_52w, 'image': os.path.join("charts", fname_52w), 'desc': f'Histogram of {report_title} for Last 52 Weeks'})

    # --- All Time (Top 1-5) ---
    all_time = clean_df.copy()
    df_all = all_time.sort_values(metric_col, ascending=False).reset_index(drop=True)
    fname_all = f"{metric_col}_all.png"
    create_histogram(df_all[metric_col], current_val, target_label, 
                     f"{report_title}: All Time", unit.upper(), fname_all, "purple", 80, subtitle, useMillions)
    
    text_all_1 = f"😈📊 {report_title.upper()}: All Time Top 5\n{subtitle}\n\n" + get_rank_text(df_all, latest_film['title'], metric_col, unit, 1, 5, show_current=False, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_all_1, 'image': os.path.join("charts", fname_all), 'desc': f'Histogram of {report_title} for All Time'})

    # --- All Time (Ranks 6-10) ---
    text_all_2 = f"😈📊 {report_title.upper()}: All Time 6-10\n{subtitle}\n\n" + get_rank_text(df_all, latest_film['title'], metric_col, unit, 6, 10, show_current=True, isDollars=isDollars, useMillions=useMillions, decimals=decimals)
    posts.append({'text': text_all_2, 'image': None, 'desc': None})
        
    return posts



def post_thread(posts):
    """Iterates through the list and publishes them as a thread with numbering."""
    previous_post_id = None
    
    total_posts = len(posts)
    
    for i, post_data in enumerate(posts):
        # First post (index 0) is public. Everything else (1-9) is unlisted.
        current_visibility = "public" if i == 0 else "unlisted"
        if DEBUG_MODE:
            current_visibility = "private"
        
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
            visibility=current_visibility
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
        
        print(f"--- POST {i+1}/{total_posts} --- Char count: {len(full_text)}/500 ---")
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
    df['release_year'] = df['release_year'].astype(int)
    
    # Sort by date
    df = df.sort_values('watched_date', ascending=False).reset_index(drop=True)
    latest_film = df.iloc[THIS_WEEKS_INDEX_LOCATION] # use index 1 to skip double feature and treat the main film as latest
    
    # 2. Assemble Thread Content
    thread_posts = []
    
    # - How will our rookie rank?
    # - Will our newbie be noteworthy?
    # - Where did our fresh face finish?
    # - Will our new recruit rise?
    # - Where does our startup stand?
    # - What position for our new premiere?
    # - How will our greenhorn be graded?
    # - Where does our baby belong?
    # - Does our challenger stand a chance?
    # - Is it new kid for the win?
    # - Where does our fledgling fit?
    # What's the status of our startup?
    # Will our rookie be highly regarded?
    # Where will our new punk get placed?
    # What's the tally for our trainee?
    # Will our beginner bloom?
    # Can our candidate climb?
    # Does our debut deliver?
    # How will our entry endure?
    # Will our first-timer find fame?
    # Does our prodigy prevail?
    # Will our underdog overperform?
    # Post 1: Intro
    intro_text = (
        f"😈📊 DEVIL IN THE DETAILS 📊😈\n\n"
        f"An occasional thread with Monsterdon data rankings.\n"
        f"Will Wolfen win or wipe out?\n"
        f"{THIS_WEEKS_EMOJI} {latest_film['title']} ({latest_film['release_year']})\n"
        f"{THIS_WEEKS_EMOJI} PARTICIPATION TROPHY: Participations Per User or PPU. Calculated as (Toots + Favs + Boosts) / Users.\n" 
        f"Data Sources: census of toots from mastodon.social, monsterdon-replay.gerlach.dev, imdb.com\n"
        f"\n#Monsterdon"
    )
    thread_posts.append({'text': intro_text, 'image': None, 'desc': None})
    # 1. TOOT RATE
    # f"{THIS_WEEKS_EMOJI} TOOT RATE: Toots Per Minute or TPM. Calculated as Toots / Minutes\n"  
    # 2. Participation Trophy
    # f"{THIS_WEEKS_EMOJI} PARTICIPATION TROPHY: Participations Per User or PPU. Calculated as (Toots + Favs + Boosts) / Users.\n" 
    # 3. Toot Volume
    # f"{THIS_WEEKS_EMOJI} Toot Volume: Total Toots\n"  
    # 4. Toot Strength
    # f"{THIS_WEEKS_EMOJI} TOOT STRENGTH: Engagements Per Toot. Doesn't count Replies due to users threading posts. Calculated (Favs + Boosts) / Toots.\n"
    # 5. Attendees
    # f"{THIS_WEEKS_EMOJI} ATTENDEES: Total People (ppl)"
    
    # footnotes = (
    #     f"😈📊 Footnotes:\n\n"
    #     f" * Toot Rate: Toots Per Minute or TPM. Calculated as Toots / Minutes\n"    
    #     f"* Genres: Pulled from imdb.com. {THIS_WEEKS_EMOJI} {latest_film['title']} ({latest_film['release_year']}) is {latest_film['genre']}.\n"
    #     f"* Real Box Office: Gross US & Canada from imdb.com inflation adjusted using consumer price index of film's release year.\n"
    #     f"* Toot Strength: Engagements Per Toot. Doesn't count Replies due to users threading posts. Calculated (Favs + Boosts) / Toots.\n"
    # )
    # thread_posts.append({'text': footnotes, 'image': None, 'desc': None})
    
    # # Toot Rate - TPM Reports
    # tpm_posts = create_timeline_reports(df, latest_film, metric_col='tpm', unit='tpm', report_title='Monsterdon Toot Rate', subtitle="Toots per minute (tpm)", isDollars=False, useMillions=False, decimals=1)
    # thread_posts.extend(tpm_posts)

    # Participation - PPU Reports
    ppu_posts = create_timeline_reports(df, latest_film, metric_col='participation_score', unit='ppu', report_title='Monsterdon Participations Per User', subtitle="Participations Per User (ppu)", isDollars=False, useMillions=False, decimals=1)
    thread_posts.extend(ppu_posts)

    # Toot Volume Reports
    # vol_posts = create_timeline_reports(df, latest_film, metric_col='toots', unit='toots', report_title='Monsterdon Toot Volume', subtitle="Total toots", isDollars=False, useMillions=False, decimals=0)
    # thread_posts.extend(vol_posts)

    # # # Top Strength Reports
    # tpm_posts = create_timeline_reports(df, latest_film, metric_col='engagement_score', unit='ept', report_title='Monsterdon Toot Strength', subtitle="Engagements per toot (ept)", isDollars=False, useMillions=False, decimals=2)
    # thread_posts.extend(tpm_posts)

    # # # Attendance Reports
    # attendance_posts = create_timeline_reports(df, latest_film, metric_col='attendees', unit='ppl', report_title='Monsterdon Attendees', subtitle="Total People (ppl)", isDollars=False, useMillions=False, decimals=0)
    # thread_posts.extend(attendance_posts)

    # -=-=-=-=-=-=-=-=-

    # Decade Report
    # thread_posts.append(generate_decade_report(df, latest_film))

    # Add the Actor reports
    # actor_posts = generate_most_popular_actors(df, latest_film)
    # thread_posts.extend(actor_posts)

    # Add the Director reports 
    # thread_posts.extend(generate_most_popular_directors(df, latest_film))

    # Most popular genres
    # thread_posts.extend(generate_most_popular_genres(df, latest_film))

    # # # Box Office Reports
    # tpm_posts = create_timeframe_reports(df, latest_film, metric_col='real_box_office', unit='Adj USD', report_title='Monsterdon Box Office', subtitle="Millions grossed, adjusted for inflation", isDollars=False, useMillions=True, decimals=1)
    # thread_posts.extend(tpm_posts)

    
    
    # # Longest Movies
    # thread_posts.append(generate_longest_movies_report(df))
    
    

    # 3. Publish Thread
    if DEBUG_MODE:
        debug_print_thread(thread_posts)
    else:
        print("Beginning live thread publish sequence...")
        post_thread(thread_posts)
        print("🎉 Thread published successfully!")



if __name__ == "__main__":
    main()