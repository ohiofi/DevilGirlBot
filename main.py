from mastodon import Mastodon
from dotenv import load_dotenv
import os, json, re, html
from bs4 import BeautifulSoup
import random
from PIL import Image, ImageDraw, ImageFont


LAST_ID_FILE = "/Volumes/Verbatim/Documents/GitHub/DevilGirlBot/last_mention_id.txt"
IMAGES_FOLDER = "/Volumes/Verbatim/Documents/GitHub/DevilGirlBot/images"
TEMP_PNG_PATH = "/Volumes/Verbatim/Documents/GitHub/DevilGirlBot/temp.png"
FONT_PATH = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
FONT_SIZE = 46

load_dotenv()

banlist = json.loads(os.getenv("banlist"))

mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social"
)



def build_alt_text(user_text: str) -> str:
    # Strip markup just in case
    clean = html.unescape(user_text).strip()

    return (
        "a screenshot from the film Devil Girl From Mars showing a "
        "serious woman wearing a black leather suit, cape, and cowl. "
        "Text is superimposed that says: \"" + clean + "\""
    )


def pick_random_image():
    # folder containing images — adjust if needed
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
        bbox = draw.textbbox((0,0), test_line, font=font)
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

        draw.text((x_text, y_text), line, font=font, fill="white",
                  stroke_width=5, stroke_fill="black")
        y_text += line_height

    im.save(output_path)
    return output_path






# ---------------------------------------------------------
# PROCESS NEW MENTIONS
# ---------------------------------------------------------

def process_mentions(last_seen_id=None):
    mentions = mastodon.notifications(types=["mention"], since_id=last_seen_id)
    if not mentions:
        return last_seen_id

    mentions = list(reversed(mentions))  # Process oldest first
    for note in mentions:
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
        hashtags = mention.get("tags", [])
        hashtag_text = ""
        if hashtags:
            hashtag_text = " " + " ".join(f"#{tag['name']}" for tag in hashtags)


        # Extract clean text
        soup = BeautifulSoup(mention["content"], "html.parser")
        text = soup.get_text().strip()
        text = re.sub(r"@\w+", "", text).strip()
        if not text:
            text = " "  # prevent empty caption

        # Generate PNG
        png_path = make_image(text)

        # Upload image with alt text
        alt_text = build_alt_text(text)
        media = mastodon.media_post(png_path, description=alt_text)

        # Reply properly to trigger notifications
        mastodon.status_post(
            status=f"@{user_acct} {hashtag_text}",
            media_ids=[media["id"]],
            in_reply_to_id=mention["id"],  # must be status ID, not notification ID
            visibility="public"  # or use mention["visibility"] to match original
        )

        # Update last_seen_id to the notification ID
        last_seen_id = note["id"]

    return last_seen_id




# ---------------------------------------------------------
# MAIN (single run)
# ---------------------------------------------------------
if __name__ == "__main__":
    last_seen_id = read_last_seen_id()
    last_seen_id = process_mentions(last_seen_id)
    if last_seen_id:
        save_last_seen_id(last_seen_id)
