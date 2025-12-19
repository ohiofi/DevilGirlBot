from mastodon import Mastodon
from dotenv import load_dotenv
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from PIL import Image, ImageDraw, ImageFont
import warnings

import os, json, re, html, time
import random

from corpora.adjectives import ADJECTIVES as adjectives
from corpora.adverbs import ADVERBS as adverbs
from corpora.comparative_adjectives import COMPARATIVE_ADJECTIVES as comparative_adjectives
from corpora.irregular_verbs import IRREGULAR_VERBS as irregular_verbs
from corpora.names import NAMES as names
from corpora.nouns import NOUNS as nouns
from corpora.places import PLACES as places
from corpora.prepositions import PREPOSITIONS as prepositions
from corpora.random_captions import RANDOM_CAPTIONS as captions
from corpora.snowclones import SNOWCLONES as snowClones
from corpora.xmas_snowclones import XMAS_SNOWCLONES as xmas_snowClones
from corpora.verbs import VERBS as verbs

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)
load_dotenv()
TEMP_PNG_PATH = os.getenv("TEMP_PNG_PATH", "/tmp/devilgirl.png")  # fallback default
LAST_ID_FILE = os.getenv("LAST_ID_FILE", "/tmp/last_id.txt")  # fallback default
LAST_RANDOM_POST_FILE = os.getenv("LAST_RANDOM_POST_FILE", "/tmp/last_random_post.txt")
IMAGES_FOLDER = os.getenv("IMAGES_FOLDER", "/path/to/images")  # fallback default
FONT_PATH = os.getenv("FONT_PATH", "/path/to/default/font.ttf")
FONT_SIZE = int(os.getenv("FONT_SIZE", 46))  # convert to int
POST_INTERVAL = 2 * 60 * 60  # 2 hours
banlist = json.loads(os.getenv("banlist"))
mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social",
)

SNOWCLONE_WORD_TYPES = ['adjective', 'adverb', 'comparativeadjective','name', 'noun', 'place',  'verb', ]

def get_word_list(word_type):
    """Maps marker type to the appropriate word list."""
    if 'adjective' in word_type:
        return adjectives
    if 'adverbs' in word_type:
        return adverbs
    if 'comparativeadjective' in word_type:
        return comparative_adjectives
    if 'name' in word_type:
        return names
    if 'noun' in word_type:
        return nouns
    if 'place' in word_type:
        return places
    if 'verb' in word_type:
        return verbs
    
    # Add other types like 'exclamation' or 'number' here
    return []

def a_or_an(word):
    return "an" if word[0].lower() in "aeiou" else "a"


def pluralize(noun):
    if noun.endswith("y") and noun[-2] not in "aeiou":
        return noun[:-1] + "ies"
    if noun.endswith(("s", "x", "z", "ch", "sh")):
        return noun + "es"
    return noun + "s"


def verb_s(verb):
    if verb.endswith("y") and verb[-2] not in "aeiou":
        return verb[:-1] + "ies"
    if verb.endswith(("s", "x", "z", "ch", "sh")):
        return verb + "es"
    return verb + "s"


def verb_ing(verb):
    if verb.endswith("e"):
        # Handles 'ie' verbs like 'lie' -> 'lying' (by not removing 'e')
        if verb.endswith("ie"):
            return verb[:-2] + "ying"
        # Handles 'e' removal for most others
        return verb[:-1] + "ing"

    # 2. Handle CVC doubling for single-syllable verbs (e.g., run -> running, stop -> stopping)
    # This check is simplified: it looks for CVC pattern at the end.
    # It will miss complex cases (like multi-syllable verbs), but is effective for common single-syllable verbs.
    if len(verb) >= 3 and not verb.endswith(('y', 'w', 'x')): # Exclude common non-doublers
        
        # Check if the last three letters follow the Consonant-Vowel-Consonant pattern
        last_char = verb[-1]
        vowel = verb[-2]
        pre_vowel = verb[-3]
        
        VOWELS = "aeiou"

        # Check for CVC pattern
        if last_char not in VOWELS and vowel in VOWELS and pre_vowel not in VOWELS:
            # Double the final consonant
            return verb + last_char + "ing"
            
    # 3. Default: just add 'ing' (e.g., talk -> talking, sing -> singing)
    return verb + "ing"

def verb_ed(verb):
    if not verb:
        return ""
    verb_lower = verb.lower()
    # Rule 0: Irregular Verb Check
    if verb_lower in irregular_verbs:
        result = irregular_verbs[verb_lower]
        # Maintain capitalization if the original was Title Case
        return result.capitalize() if verb[0].isupper() else result

    last_letter = verb_lower[-1]
    last_two = verb_lower[-2:]
    # Rule 1: Verbs ending in 'e' (e.g., "live" -> "lived")
    if last_letter == 'e':
        return verb + 'd'
    # Rule 2: Verbs ending in 'y' preceded by a consonant (e.g., "try" -> "tried")
    # Note: If preceded by a vowel (e.g., "play"), just add 'ed'.
    if last_letter == 'y' and len(verb) > 1 and verb[-2].lower() not in 'aeiou':
        return verb[:-1] + 'ied'
    # Rule 3: CVC pattern (Consonant-Vowel-Consonant) at the end, 
    # where the stress is on the last syllable (e.g., "stop" -> "stopped", "occur" -> "occurred")
    # This is complex to check perfectly, but we can check common single-syllable cases.
    vowels = 'aeiou'
    if len(verb) >= 3 and last_letter not in vowels and verb[-2].lower() in vowels and verb[-3].lower() not in vowels:
        # Simple check for common CVC endings (e.g., stop, drop, beg, tap)
        if last_two not in ('er', 'el', 'on'): # Avoid common exceptions
            return verb + last_letter + 'ed'
    # Default Rule: Just add 'ed' (e.g., "walk" -> "walked", "play" -> "played")
    return verb + 'ed'



def apply_modifier(word, modifier, *args):
    """Applies a single modifier to the word."""
    if modifier == 's':       # Plural (Nouns) / 3rd-person singular (Verbs)
        return pluralize(word) if 'noun' in args else verb_s(word)
    if modifier == 'ed':      # Past Tense
        return verb_ed(word)
    if modifier == 'ing':     # Present Participle
        return verb_ing(word)
    if modifier == 'title':   # Capitalize first letter (e.g., Title Case)
        return word.title()
    if modifier == 'upper':   # Uppercase
        return word.upper()
    if modifier == 'lower':   # Lowercase (useful after .title)
        return word.lower()
    # Add more modifiers here (e.g., 'reverse', 'hyphenate')
    return word

def fill_snowclone(template):
    output = template
    
    # Dictionary to track words chosen for repeated markers in this run
    processed_markers = {} 

    # --- Handle Repeated Words First (Logic remains the same) ---
    for match in re.findall(r"\*repeated[a-z]+(?:\.[a-z]+)*\*", output):
        full_marker = match
        parts = full_marker[1:-1].split('.')
        base_type = parts[0]
        modifiers = parts[1:]

        if base_type not in processed_markers:
            base_word = random.choice(get_word_list(base_type))
            processed_markers[base_type] = base_word
        else:
            base_word = processed_markers[base_type]
            
        final_word = base_word
        a_an_prefix = ""
        for mod in modifiers:
            if mod == 'a': continue
            final_word = apply_modifier(final_word, mod, base_type)
        
        if 'a' in modifiers:
            a_an_prefix = a_or_an(final_word) + " "

        # Replace ALL occurrences of this specific repeated marker
        output = output.replace(full_marker, a_an_prefix + final_word)


    # --- Handle Unique Words (revised to ensure every *instance* is unique) ---

    for type_name in SNOWCLONE_WORD_TYPES:
        # Regex to find all markers starting with the current type (e.g., *noun*, *noun.s*, *noun.a.ing*)
        marker_pattern = re.compile(rf"\*{type_name}(?:\.[a-z]+)*\*")
        
        # Find every instance of a marker that matches the pattern
        # The key is that we must replace them one by one.
        
        # We find ALL instances of the marker string (e.g., all "*noun.a*")
        found_markers = re.findall(marker_pattern, output)
        
        for full_marker in found_markers:
            
            # --- Generate the unique word for THIS specific instance ---
            
            parts = full_marker[1:-1].split('.')
            base_type = parts[0]
            modifiers = parts[1:]

            base_word = random.choice(get_word_list(base_type))
            
            final_word = base_word
            a_an_prefix = ""
            for mod in modifiers:
                if mod == 'a': continue
                final_word = apply_modifier(final_word, mod, base_type)
            
            if 'a' in modifiers:
                a_an_prefix = a_or_an(final_word) + " "
            
            replacement_value = a_an_prefix + final_word
            
            # --- Replace only ONE occurrence in the output string ---
            # Using the count=1 argument ensures that if the template contains
            # two *noun* markers, we replace the first one with one random word,
            # and the second one with a second random word in the next iteration.
            output = output.replace(full_marker, replacement_value, 1)

    return output


def get_random_snowclone(mylist):
    template = random.choice(mylist)
    return fill_snowclone(template)

def make_mashup_text(captions):
    firstHalfArray = []
    secondHalfArray = []
    for i in range(10):  # try at max 10 times
        # Pick random captions and split into words
        firstHalfArray = random.choice(captions).split(" ")
        # Keep roughly half from firstHalfArray
        start_index = int(
            random.random() * len(firstHalfArray) * 0.5
            + random.random() * len(firstHalfArray) * 0.5
        )
        firstHalfArray = firstHalfArray[0:start_index]
        if len(firstHalfArray) > 1:
            break
    for i in range(10):  # try at max 10 times
        secondHalfArray = random.choice(captions).split(" ")
        # Remove roughly half from the start of secondHalfArray
        start_index = int(
            random.random() * len(secondHalfArray) * 0.5
            + random.random() * len(secondHalfArray) * 0.5
        )
        secondHalfArray = secondHalfArray[start_index:]
        if len(secondHalfArray) > 1:
            break
    # Combine arrays into a single string
    result = " ".join(firstHalfArray + secondHalfArray)
    if random.random() < 0.001 or len(result) < 3:
        return random.choice(captions)
    return result


    


def build_alt_text(user_text: str) -> str:
    # Strip markup just in case
    clean = html.unescape(user_text).strip()

    return (
        "screenshot from the film Devil Girl From Mars showing a "
        "serious woman wearing a black leather suit, cape, and cowl. "
        'Superimposed text says: "' + clean + '"'
    )


def pick_random_image():
    # generate a random number between 0 and 64 inclusive
    idx = random.randint(0, 64)

    # zero-pad to 2 digits: 0 → "00", 5 → "05"
    filename = f"devilgirl{idx:02d}.png"

    # full path to file
    return os.path.join(IMAGES_FOLDER, filename)


# ---------------------------------------------------------
# LOAD / SAVE LAST PROCESSED MENTION
# ---------------------------------------------------------
def read_last_seen_id():
    try:
        with open(LAST_ID_FILE, "r") as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError):
        return None


def save_last_seen_id(last_id):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(last_id))


def load_last_random_post():
    if not os.path.exists(LAST_RANDOM_POST_FILE):
        return 0
    with open(LAST_RANDOM_POST_FILE, "r") as f:
        try:
            return float(f.read().strip())
        except:
            return 0


def save_last_random_post(ts):
    with open(LAST_RANDOM_POST_FILE, "w") as f:
        f.write(str(ts))


# ---------------------------------------------------------
# CLEAN USER TEXT
# ---------------------------------------------------------
def extract_user_text(status):
    html_content = status["content"]
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text().strip()
    text = re.sub(r"@[A-Za-z0-9_@.]+", "", text).strip()  # remove mentions
    return text


def make_image(user_text, output_path=TEMP_PNG_PATH):
    user_text = user_text.upper()

    # Pick random image
    img_number = random.randint(0, 64)
    img_filename = f"devilgirl{img_number:02d}.png"
    img_path = os.path.join(IMAGES_FOLDER, img_filename)

    im = Image.open(img_path).convert("RGBA")
    draw = ImageDraw.Draw(im)
    font = ImageFont.truetype(FONT_PATH, FONT_SIZE)

    # Dynamic wrapping based on image width
    max_width = im.width - 40  # 20px padding on each side
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

    # Draw each line, bottom-centered
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


def makePost(text):
    """Create a public post with a generated image."""
    png_path = make_image(text)
    alt_text = build_alt_text(text)

    mastodon.status_post(
        status=text,
        media_ids=[mastodon.media_post(png_path, description=alt_text)["id"]],
        visibility="public",
    )


def makeReply(user_acct, text, in_reply_to_id):
    """Reply to a mention with a generated image and hashtags."""
    if len(text.strip()) < 2:
        text = getText(captions)
        # makePost(text)
    png_path = make_image(text)
    alt_text = build_alt_text(text)

    # hashtag_text = ""
    # if hashtags:
    #     hashtag_text = " " + " ".join(f"#{tag['name']}" for tag in hashtags)

    mastodon.status_post(
        status=f"@{user_acct} {text}",
        media_ids=[mastodon.media_post(png_path, description=alt_text)["id"]],
        in_reply_to_id=in_reply_to_id,
        visibility="public",
    )

def does_text_contain_banned(html_content, banlist):
    """
    Strips HTML, lowercases the text, and checks against a banlist.
    """
    # Remove HTML tags using regex (standard for simple text extraction)
    # This turns "<p>Hello STOP words</p>" into "hello stop words"
    clean_text = re.sub('<[^<]+?>', '', html_content).lower()
    
    # Check if any banned word/phrase exists within the cleaned text
    for forbidden in banlist:
        if forbidden.lower() in clean_text:
            return True
            
    return False


def getText(captions):
    if random.random() < 0.33:
        return get_random_snowclone(xmas_snowClones)
    if random.random() < 0.50:
        return get_random_snowclone(snowClones)
    return make_mashup_text(captions)


# ---------------------------------------------------------
# PROCESS NEW MENTIONS
# ---------------------------------------------------------


def process_mentions(last_seen_id=None):
    # print(f"last_seen_id: {last_seen_id}, type: {type(last_seen_id)}")
    mentions = mastodon.notifications(types=["mention"], since_id=last_seen_id)
    if not mentions:
        # make a random post every post interval (2 hrs)
        last_random_post = load_last_random_post()
        now = time.time()
        if now - last_random_post >= POST_INTERVAL:
            text = getText(captions)
            makePost(text)
            save_last_random_post(now)
        return last_seen_id

    mentions = list(reversed(mentions))  # Process oldest first
    for note in mentions:

        if note["type"] != "mention":
            continue
        mention = note["status"]  # the post that mentioned the bot
        user_acct = mention["account"]["acct"]

        # Skip banned users
        if user_acct in banlist:
            continue
        # Skip banned words

        # 1% chance to skip reply
        if random.random() < 0.01:
            print(f"Skipping reply to {user_acct} to avoid infinite loop")
            continue

        # Collect all hashtags
        # hashtags = mention.get("tags", [])
        # hashtag_text = ""
        # if hashtags:
        #     hashtag_text = " " + " ".join(f"#{tag['name']}" for tag in hashtags)

        # Extract clean text
        soup = BeautifulSoup(mention["content"], "html.parser")
        text = soup.get_text().strip()
        text = re.sub(r"@\w+", "", text).strip()
        if not text:
            text = " "  # prevent empty caption

        # Update last_seen_id to the notification ID
        # maybe save id BEFORE the reply is uploaded, because slow upload times would mean that multiple replies were being generated
        # last_seen_id = max(last_seen_id or 0, int(note["id"]))
        # save_last_seen_id(last_seen_id)

        makeReply(user_acct, text, mention["id"])

        # Update last_seen_id to the notification ID
        last_seen_id = max(last_seen_id or 0, int(note["id"]))
        save_last_seen_id(last_seen_id)
        break  # rate limit this so that if there are multiple mentions, it will only reply to the oldest one. Other mentions can be processed when the bot runs again.

    return last_seen_id


# ---------------------------------------------------------
# MAIN 
# ---------------------------------------------------------
# if __name__ == "__main__":
#     last_seen_id = read_last_seen_id()
#     last_seen_id = process_mentions(last_seen_id)



def remove_only_emojis(text):
    emoji_pattern = re.compile(
        u"["
        u"\U00010000-\U0010ffff"  
        u"\u2600-\u26ff"          
        u"\u2700-\u27bf"          
        u"\ufe0f"                 
        u"\u200d"                 
        u"]+", 
        flags=re.UNICODE
    )
    return emoji_pattern.sub('', text)

def remove_hashtags_and_mentions(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    
    # 1. Target the anchor tags directly
    for link in soup.find_all("a"):
        # Mastodon marks mentions and hashtags with specific CSS classes
        classes = link.get("class", [])
        
        # If it's a mention or a hashtag, kill it!
        if "mention" in classes or "hashtag" in classes:
            link.decompose()
        
        # If it's a regular URL, it usually has no class or a 'u-url' class
        # We decompose these too to avoid the "shrapnel" numbers issue
        else:
            link.decompose()

    # 2. Extract the remaining text
    # We use a space separator so words don't get squashed together
    text = soup.get_text(separator=" ")
    
    # 3. Clean up whitespace
    # This handles \xa0 and extra spaces created by the decomposition
    text = " ".join(text.split()).strip()
    # 3. Strip Emojis
    # text = re.sub(r'[^\x00-\x7f]|[^\w\s,.!?-]', '', text)
    text = remove_only_emojis(text)
    # 4. Final cleanup of "RE:" and double spaces
    text = re.sub(r'\bRE:\b', '', text, flags=re.IGNORECASE)
    clean_text = " ".join(text.split()).strip()
    
    return clean_text

def get_hashtag_toot(last_seen_id=None):
    toots = mastodon.timeline_hashtag(hashtag="monsterdon", since_id=last_seen_id, limit=40)
    if not toots:
        print("no toots")
        return last_seen_id

    # Shuffle to avoid picking the same one repeatedly in the loop
    random.shuffle(toots)

    for toot in toots:
        # print(f"Original: {toot['content']}")
        full_text = remove_hashtags_and_mentions(toot['content'])
        # soup = BeautifulSoup(toot['content'], "html.parser")
        # full_text = soup.get_text(separator=" ")
        # full_text = " ".join(full_text.split())
        sentences = re.split(r'(?<=[.!?])\s+', full_text)
        
        raw_sentence = random.choice(sentences)
        clean_sentence = remove_hashtags_and_mentions(raw_sentence)
        
        if (len(clean_sentence) < 5 or 
            len(clean_sentence) > 100 or 
            does_text_contain_banned(clean_sentence, banlist)):
            continue
            
        # print(f"Cleaned:  {clean_sentence}")
        return clean_sentence
    return None



if __name__ == "__main__":
    print(does_text_contain_banned("hellow world", banlist))
    print(does_text_contain_banned("niglected", banlist))
    get_hashtag_toot()
    # for i in range(100):
    #     print(get_random_snowclone(snowClones))
