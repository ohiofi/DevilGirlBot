from mastodon import Mastodon
from dotenv import load_dotenv
import os, json, re, html
from bs4 import BeautifulSoup
import random
import cairosvg


load_dotenv()

banlist = json.loads(os.getenv("banlist"))

mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social"
)

LAST_ID_FILE = "last_mention_id.txt"



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
    images_folder = "images"

    # generate a random number between 0 and 64 inclusive
    idx = random.randint(0, 64)

    # zero-pad to 2 digits: 0 → "00", 5 → "05"
    filename = f"devilgirl{idx:02d}.png"

    # full path to file
    return os.path.join(images_folder, filename)



# ---------------------------------------------------------
# LOAD / SAVE LAST PROCESSED MENTION
# ---------------------------------------------------------
def load_last_id():
    if not os.path.exists(LAST_ID_FILE):
        return None
    with open(LAST_ID_FILE, "r") as f:
        return f.read().strip() or None

def save_last_id(id_str):
    with open(LAST_ID_FILE, "w") as f:
        f.write(str(id_str))


# ---------------------------------------------------------
# CLEAN USER TEXT
# ---------------------------------------------------------
def extract_user_text(status):
    html_content = status["content"]
    soup = BeautifulSoup(html_content, "html.parser")
    text = soup.get_text().strip()
    text = re.sub(r"@[A-Za-z0-9_@.]+", "", text).strip()  # remove mentions
    return text


# ---------------------------------------------------------
# SVG GENERATOR
# ---------------------------------------------------------
def make_svg(text, max_chars_per_line=22, base_font_size=48):
    import html
    safe = html.escape(text)

    # -------------------------------------------------------
    # PICK RANDOM IMAGE
    # -------------------------------------------------------
    image_path = pick_random_image()

    # -------------------------------------------------------
    # WORD WRAP INTO MULTIPLE LINES
    # -------------------------------------------------------
    words = safe.split()
    lines = []
    current = ""

    for w in words:
        if len(current + " " + w) <= max_chars_per_line:
            if current == "":
                current = w
            else:
                current += " " + w
        else:
            lines.append(current)
            current = w

    if current:
        lines.append(current)

    # -------------------------------------------------------
    # DYNAMIC FONT SIZE IF TOO MANY LINES
    # -------------------------------------------------------
    font_size = base_font_size
    if len(lines) > 3:
        font_size = int(base_font_size * 0.85)
    if len(lines) > 4:
        font_size = int(base_font_size * 0.70)
    if len(lines) > 5:
        font_size = int(base_font_size * 0.55)

    # -------------------------------------------------------
    # BOTTOM TEXT POSITIONING
    # -------------------------------------------------------
    # Last line should be near bottom (e.g., y = 92%)
    # Lines stack upward by 7% each
    bottom_y = 92
    line_step = 7  # percentage spacing between lines

    svg_lines = []
    total_lines = len(lines)

    for i, line in enumerate(lines):
        # Example: 3 lines → indexes 0,1,2
        # bottom line (i=2) is at y=92
        # line above is y=85, then 78
        y = bottom_y - (total_lines - 1 - i) * line_step

        svg_lines.append(f"""
        <text x="50%" y="{y}%" text-anchor="middle"
              font-size="{font_size}"
              fill="white" stroke="black" stroke-width="3"
              font-family="Impact">{html.escape(line.upper())}</text>
        """)

    svg_text = "\n".join(svg_lines)

    # -------------------------------------------------------
    # FINAL SVG
    # -------------------------------------------------------
    svg = f"""
<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540">
  <rect width="100%" height="100%" fill="black"/>
  <image href="{image_path}"
         x="0" y="0" width="960" height="540"/>
  {svg_text}
</svg>
"""
    return svg.strip()



# ---------------------------------------------------------
# PROCESS NEW MENTIONS
# ---------------------------------------------------------
def process_mentions(last_seen_id=None):
    # Fetch mentions newer than last_seen_id
    mentions = mastodon.notifications(
        types=["mention"],
        since_id=last_seen_id
    )

    if not mentions:
        return last_seen_id  # nothing new

    # Process from oldest → newest
    mentions = list(reversed(mentions))

    for note in mentions:
        mention = note["status"]
        user_acct = mention["account"]["acct"]

        # Skip banned users
        if user_acct in banlist:
            continue

        # Extract plain text from the mention
        soup = BeautifulSoup(mention["content"], "html.parser")
        text = soup.get_text().strip()

        # Remove the bot's own @mention from the user's text
        # Example: "@YourBot Hello" → "Hello"
        text = re.sub(r"@\w+", "", text).strip()

        if not text:
            text = " "  # prevent blank caption breaking SVG

        # ---- Generate SVG and save temporary file ----
        svg_data = make_svg(text)

        temp_path = "temp.svg"
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(svg_data)

        # ---- Build alt text ----
        alt_text = build_alt_text(text)

        # ---- Upload to Mastodon with ALT TEXT ----
        media = mastodon.media_post(
            temp_path,
            mime_type="image/svg+xml",
            description=alt_text     # <-- ALT TEXT HERE
        )

        # ---- Reply to the mention ----
        mastodon.status_post(
            status=f"@{user_acct}",
            media_ids=[media["id"]],
            in_reply_to_id=mention["id"],
            visibility=mention["visibility"]
        )

        # Update last seen ID
        last_seen_id = note["id"]

    return last_seen_id



# ---------------------------------------------------------
# MAIN (single run)
# ---------------------------------------------------------
if __name__ == "__main__":
    process_mentions()
