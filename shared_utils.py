import os, json, re, html, random, io
from bs4 import BeautifulSoup, NavigableString
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv

load_dotenv()
TEMP_PNG_PATH = os.getenv("TEMP_PNG_PATH", "/tmp/devilgirl.png")  # fallback default
IMAGES_FOLDER = os.getenv("IMAGES_FOLDER", "/path/to/images")  # fallback default
FONT_PATH = os.getenv("FONT_PATH", "/path/to/default/font.ttf")
FONT_SIZE = int(os.getenv("FONT_SIZE", 46))  # convert to int

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


def text_only_cleaning_algorithm(html_content):
    soup = BeautifulSoup(html_content, "html.parser")
    for link in soup.find_all("a"):
        link.decompose()
    # Extract remaining text
    text = soup.get_text(separator=" ")
    # Standardize whitespace (handles \xa0 and tabs)
    text = " ".join(text.split()).strip()
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

def build_alt_text(user_text):
    clean = html.unescape(user_text).strip()[:255]
    return (
        "screenshot from the film Devil Girl From Mars showing a "
        "serious woman wearing a black leather suit, cape, and cowl. "
        'Text reads: "' + clean + '"'
    )