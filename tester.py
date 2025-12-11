# from mastodon import Mastodon
# from dotenv import load_dotenv
import os, json, re, html, time
# from bs4 import BeautifulSoup
import random
# from PIL import Image, ImageDraw, ImageFont

from corpora.adjectives import ADJECTIVES as adjectives
from corpora.names import NAMES as names
from corpora.nouns import NOUNS as nouns
from corpora.random_captions import RANDOM_CAPTIONS as captions
from corpora.snowclones import SNOWCLONES as snowClones
from corpora.verbs import VERBS as verbs

TEMP_PNG_PATH = None
LAST_ID_FILE = None
LAST_RANDOM_POST_FILE = None
IMAGES_FOLDER = None
FONT_PATH = None
FONT_SIZE = None
POST_INTERVAL = None
banlist = None
mastodon = None

def setup_globals():
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
        return verb[:-1] + "ing"
    return verb + "ing"

def verb_ed(verb):
    if not verb:
        return ""
    last_letter = verb[-1].lower()
    last_two = verb[-2:].lower()
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
        if last_two not in ('er', 'el', 'on', 'ap'): # Avoid common exceptions
            return verb + last_letter + 'ed'
    # Default Rule: Just add 'ed' (e.g., "walk" -> "walked", "play" -> "played")
    return verb + 'ed'

def fill_snowclone(template):
    output = template

    # Handle repeated words first
    # REPEATED NOUN
    # Check for *any* repeatednoun marker before choosing a word
    if re.search(r"\*a?\.?repeatednoun(?:\.s)?\*", output):
        n = random.choice(nouns)
        output = output.replace("*repeatednoun.s*", pluralize(n))
        output = output.replace("*a.repeatednoun*", f"{a_or_an(n)} {n}")
        output = output.replace("*repeatednoun*", n)

    # REPEATED VERB
    if re.search(r"\*repeatedverb(?:\..+)?\*", output):
        v = random.choice(verbs)
        output = output.replace("*repeatedverb.s*", verb_s(v))
        output = output.replace("*repeatedverb.ing*", verb_ing(v))
        output = output.replace("*repeatedverb.ed*", verb_ed(v))
        output = output.replace("*repeatedverb*", v)

    # REPEATED ADJECTIVE
    if "*repeatedadjective*" in output:
        a = random.choice(adjectives)
        output = output.replace("*repeatedadjective*", a)

    # *a.noun*
    for match in re.findall(r"\*a\.noun\*", output):
        n = random.choice(nouns)
        output = output.replace(match, f"{a_or_an(n)} {n}", 1)

    # *a.adjective*
    for match in re.findall(r"\*a\.adjective\*", output):
        adj = random.choice(adjectives)
        output = output.replace(match, f"{a_or_an(adj)} {adj}", 1)

    # plural nouns *noun.s*
    for match in re.findall(r"\*noun\.s\*", output):
        n = pluralize(random.choice(nouns))
        output = output.replace(match, n, 1)

    # plural adjectives? (not used, but you had the pattern)
    for match in re.findall(r"\*adjective\.s\*", output):
        adj = random.choice(adjectives) + "s"
        output = output.replace(match, adj, 1)

    # verb.s → 3rd-person singular
    for match in re.findall(r"\*verb\.s\*", output):
        v = verb_s(random.choice(verbs))
        output = output.replace(match, v, 1)

    # *verb*ing (gerund)
    for match in re.findall(r"\*verb\*ing", output):
        v = verb_ing(random.choice(verbs))
        output = output.replace(match, v, 1)

    # *verb*ed (past tense — naive)
    for match in re.findall(r"\*verb\*ed", output):
        v = random.choice(verbs) + "ed"
        output = output.replace(match, v, 1)

    # *verb*
    for match in re.findall(r"\*verb\*", output):
        v = random.choice(verbs)
        output = output.replace(match, v, 1)

    # *adjective*
    for match in re.findall(r"\*adjective\*", output):
        a = random.choice(adjectives)
        output = output.replace(match, a, 1)

    # *noun*
    for match in re.findall(r"\*noun\*", output):
        n = random.choice(nouns)
        output = output.replace(match, n, 1)

    # *name*
    for match in re.findall(r"\*name\*", output):
        n = random.choice(names)
        output = output.replace(match, n, 1)

    return output


def get_random_snowclone():
    template = random.choice(snowClones)
    return fill_snowclone(template)





def getText(captions):
    if random.random() < 0.75:
        return get_random_snowclone()
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
        "a screenshot from the film Devil Girl From Mars showing a "
        "serious woman wearing a black leather suit, cape, and cowl. "
        'Text is superimposed that says: "' + clean + '"'
    )


def pick_random_image():
    # folder containing images adjust if needed
    images_folder = "/Volumes/Verbatim/Documents/GitHub/DevilGirlBot/images"

    # generate a random number between 0 and 64 inclusive
    idx = random.randint(0, 64)

    # zero-pad to 2 digits: 0 → "00", 5 → "05"
    filename = f"devilgirl{idx:02d}.png"

    # full path to file
    return os.path.join(images_folder, filename)


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
    alt_text = f"a screenshot from the film Devil Girl From Mars showing a serious woman wearing a black leather suit, cape, and cowl. Text is superimposed that says: {text}"

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
    alt_text = f"a screenshot from the film Devil Girl From Mars showing a serious woman wearing a black leather suit, cape, and cowl. Text is superimposed that says: {text}"

    # hashtag_text = ""
    # if hashtags:
    #     hashtag_text = " " + " ".join(f"#{tag['name']}" for tag in hashtags)

    mastodon.status_post(
        status=f"@{user_acct} {text}",
        media_ids=[mastodon.media_post(png_path, description=alt_text)["id"]],
        in_reply_to_id=in_reply_to_id,
        visibility="public",
    )


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
        mention = note["status"]  # Correct: the post that mentioned the bot
        user_acct = mention["account"]["acct"]

        # Skip banned users
        if user_acct in banlist:
            continue

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

        makeReply(user_acct, text, mention["id"])

        # Update last_seen_id to the notification ID
        last_seen_id = max(last_seen_id or 0, int(note["id"]))
        save_last_seen_id(last_seen_id)
        break  # rate limit this so that if there are multiple mentions, it will only reply to the oldest one. Other mentions can be processed when the bot runs again.

    return last_seen_id







if __name__ == "__main__":
    for i in range(100):
        print(get_random_snowclone())
