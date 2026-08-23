import os, json, re, html, random
from datetime import datetime
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()
TEMP_PNG_PATH = os.getenv("TEMP_PNG_PATH", "/tmp/devilgirl.png")  # fallback default
IMAGES_FOLDER = os.getenv("IMAGES_FOLDER", "/path/to/images")  # fallback default
FONT_PATH = os.getenv("FONT_PATH", "/path/to/default/font.ttf")
FONT_SIZE = int(os.getenv("FONT_SIZE", 46))  # convert to int
HISTORY_FILE = os.getenv("HISTORY_FILE", "/tmp/previous_posts.txt")
SENTENCE_FILE = os.getenv("SENTENCE_FILE", "/tmp/possible_sentences.txt")




def build_alt_text(user_text, subject="screenshot from the film Devil Girl From Mars showing a serious woman wearing a black leather suit, cape, and cowl"):
    clean = html.unescape(user_text).strip()[:255]
    return f"{subject}. Text reads: \"{clean}\""

def does_text_contain_banned(html_content, banlist):
    """
    Strips HTML, lowercases the text, and checks against a banlist.
    """
    # Remove HTML tags using regex (standard for simple text extraction)
    # This turns "<p>Hello STOP words</p>" into "hello stop words"
    clean_text = re.sub("<[^<]+?>", "", html_content).lower()

    # Check if any banned word/phrase exists within the cleaned text
    for forbidden in banlist:
        if forbidden.lower() in clean_text:
            return True

    return False


def extract_raw_text(html_content):
    return BeautifulSoup(html_content, "html.parser").get_text().lower()

def find_source_by_parent_id(parent_id):
    """Looks through history to find which original post inspired a meme."""
    if not parent_id:
        return None
    
    history_data = load_previous_posts()

    target_id = str(parent_id)
    
    for item in history_data:
        # 1. Skip entries that aren't dictionaries (handles old raw string entries)
        if not isinstance(item, dict):
            continue
            
        # 2. Extract potential URLs, ignoring literal "unknown" strings
        meme_url = item.get("meme_post_url")
        source_url = item.get("source_url") or item.get("url")
        
        # Clean up "unknown" values so they don't get searched
        if meme_url == "unknown":
            meme_url = None
        if source_url == "unknown":
            source_url = None
            
        # 3. Check for a match against the bot's post URL first, then the source
        if meme_url and target_id in meme_url:
            return item
        if source_url and target_id in source_url:
            return item
            
    return None

def is_sentence_valid(s, author_username, sentence_pool, history_text_only, banned_words, banned_users):
    """Centralized validation for incoming scraped sentences, filtering by content and author."""
    # 1. Check if the user who wrote this is on the banned users list (e.g., 'devilgirlbot')
    if author_username and any(banned.lower() in author_username.lower() for banned in banned_users):
        return False

    # 2. Check length constraints
    if not (5 <= len(s) <= 150):
        return False
        
    # 3. Check against the keyword/phrase banned_words list
    if does_text_contain_banned(s, banned_words):
        return False
        
    # 4. Check if it already exists in the current scraped pool
    if any(item["sentence"] == s for item in sentence_pool):
        return False
        
    # 5. Check if we have already posted it in our history file
    if s in history_text_only:
        return False
        
    return True

def load_last_seen_id(filename):
    try:
        with open(filename, "r") as f:
            return int(f.read().strip())
    except:
        return None


def load_previous_posts():
    """Loads the history of post objects."""
    if not os.path.exists(HISTORY_FILE) or os.path.getsize(HISTORY_FILE) == 0:
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else []
    except (json.JSONDecodeError, UnicodeDecodeError):
        return []


def load_sentences():
    """
    Loads the pool of potential sentences from SENTENCE_FILE.
    Returns a list of dictionaries: [{'sentence': '...', 'url': '...'}, ...]
    """
    # 1. Check if the file physically exists
    if not os.path.exists(SENTENCE_FILE):
        print(f"DEBUG: Sentence file not found at {SENTENCE_FILE}. Starting with empty pool.")
        return []

    # 2. Check if the file is empty
    if os.path.getsize(SENTENCE_FILE) == 0:
        print("DEBUG: Sentence file is empty.")
        return []

    try:
        with open(SENTENCE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

            # 3. Verify the data is a list
            if not isinstance(data, list):
                print(f"DEBUG: SENTENCE_FILE expected a list, but got {type(data)}.")
                return []

            print(f"DEBUG: Successfully loaded {len(data)} sentences from {SENTENCE_FILE}.")
            return data

    except json.JSONDecodeError:
        print("DEBUG: SENTENCE_FILE contains invalid JSON.")
        return []
    except Exception as e:
        print(f"DEBUG: Unexpected error loading sentences: {e}")
        return []


def make_image(image_path, user_text, target_size=None, output_path=TEMP_PNG_PATH):
    """
    Loads a specific image path, optionally resizes it, and overlays text.
    """
    user_text = user_text.upper()

    im = Image.open(image_path).convert("RGBA")

    if target_size:
        im = im.resize(target_size, Image.Resampling.LANCZOS)

    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # Dynamic wrapping based on actual width
    max_width = im.width - 40
    words = user_text.split()
    lines = []
    line = ""
    for word in words:
        test_line = f"{line} {word}".strip()
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if bbox[2] - bbox[0] <= max_width:
            line = test_line
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)

    # Calculate line height
    bbox = draw.textbbox((0, 0), "A", font=font)
    line_spacing = 10
    line_height = (bbox[3] - bbox[1]) + line_spacing
    total_text_height = line_height * len(lines)

    # Draw centered text
    y_text = im.height - total_text_height - 20
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        text_width = bbox[2] - bbox[0]
        x_text = (im.width - text_width) / 2

        draw.text(
            (x_text, y_text),
            line,
            font=font,
            fill="white",
            stroke_width=5,
            stroke_fill="black",
        )
        y_text += line_height

    im.save(output_path)
    return output_path


def replace_non_terminating_punctuation(text):
    # First fix internally dotted abbreviations a.m. and p.m.
    text = re.sub(r"\b([ap])\.m\.", r"\1m", text, flags=re.IGNORECASE)
    NON_TERMINATING = [
        "vs",
        "mr",
        "mrs",
        "ms",
        "mx",
        "dr",
        "prof",
        "sr",
        "jr",
        "rev",
        "etc",
        "eg",
        "ie",
        "cf",
        "al",
        "ca",
        "st",
        "ave",
        "blvd",
        "rd",
        "ln",
        "ct",
        "pl",
        "mt",
        "ft",
        "vol",
        "fig",
        "sec",
        "ch",
    ]
    pattern = r"\b(" + "|".join(NON_TERMINATING) + r")\."
    text = re.sub(pattern, r"\1", text, flags=re.IGNORECASE)
    return text


def save_last_seen_id(last_id, filename):
    with open(filename, "w") as f:
        f.write(str(last_id))


def save_previous_posts(history_list):
    """Saves the last 500 post objects."""
    if len(history_list) > 500:
        history_list = history_list[-500:]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history_list, f, ensure_ascii=False, indent=2)



def save_sentences(sentences):
    """
    Saves the sentence pool to SENTENCE_FILE. 
    Trims to 500 items to keep the file manageable.
    """
    # Keep the pool to a maximum of 500 items
    if len(sentences) > 500:
        # Optionally shuffle before trimming to keep a variety
        random.shuffle(sentences)
        sentences = sentences[:500]
        
    with open(SENTENCE_FILE, "w", encoding="utf-8") as f:
        # ensure_ascii=False keeps the text readable in the file
        json.dump(sentences, f, ensure_ascii=False, indent=2)

def select_random_image(images_folder=IMAGES_FOLDER):
    """
    Scans the provided folder and selects a random image file path.
    """
    valid_extensions = ('.png', '.jpg', '.jpeg', '.webp')
    image_files = [
        f for f in os.listdir(images_folder) 
        if f.lower().endswith(valid_extensions) and not f.startswith('.')
    ]

    if not image_files:
        raise FileNotFoundError(f"No valid image files found in directory: {images_folder}")

    selected_file = random.choice(image_files)
    return os.path.join(images_folder, selected_file)

def text_only_cleaning_algorithm(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for link in soup.find_all("a"):
        link.decompose()
    # Extract remaining text
    text = soup.get_text(separator=" ")
    # Standardize whitespace (handles \xa0 and tabs)
    text = " ".join(text.split()).strip()
    return text


def update_history(text, source_url, meme_url):
    """Adds a new entry to the history file and trims to 500."""
    history = load_previous_posts()
    
    new_entry = {
        "text": text,
        "source_url": source_url,
        "meme_post_url": meme_url,
        "timestamp": datetime.now().isoformat()
    }
    
    history.append(new_entry)
    save_previous_posts(history)
