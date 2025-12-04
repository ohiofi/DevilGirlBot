from mastodon import Mastodon
from dotenv import load_dotenv
import os, json, re, html
from bs4 import BeautifulSoup
import random
from PIL import Image, ImageDraw, ImageFont

load_dotenv()
TEMP_PNG_PATH = os.getenv("TEMP_PNG_PATH", "/tmp/devilgirl.png")  # fallback default
LAST_ID_FILE = os.getenv("LAST_ID_FILE", "/tmp/last_id.txt")  # fallback default
IMAGES_FOLDER = os.getenv("IMAGES_FOLDER", "/path/to/images")  # fallback default
FONT_PATH = os.getenv("FONT_PATH", "/path/to/default/font.ttf")
FONT_SIZE = int(os.getenv("FONT_SIZE", 46))  # convert to int

FONT_SIZE = 46

captions = [
    ":3",
    "?!",
    "*internal screaming*",
    "*jazz music stops*",
    "*panic internally*",
    "*screams into void*",
    "*SUPER*STAR*",
    "10/10",
    "100%",
    "404 brain not found",
    "Adulting: Nope",
    "Aight Imma Head Out",
    "Ain't nobody got time for that",
    "Aliens watch me for tips",
    "all your base are belong to us",
    "Anxiety but make it aesthetic",
    "ANYONE NEED BUTTER?",
    "ARE YOU GOING TO STUDY HALL?",
    "Assistant to the Regional Manager",
    "Aww Yea",
    "Bad Hair, Don't Care",
    "Be careful, I know the code to the WiFi",
    "Be kind, I'm doing my best",
    "Be nice, I might be your tech support someday",
    "Be right back, disassociating",
    "Bears. Beets. Battlestar Galactica.",
    "Bet",
    "Big brain energy, small body",
    "Big brain time",
    "Big Mood",
    "Big oof",
    "Big yawn, bigger vibes",
    "Big Yikes",
    "Binary mood: 101010",
    "Bless this mess",
    "Brain lag loading…",
    "brb, debugging life",
    "BRB: existential crisis",
    "BRB: Mentally elsewhere",
    "Breakdancing Champ",
    "Bro Do You Even Lift?",
    "Bro got the quantum Ohio gyatt buff",
    "Bro said skill issue",
    "Bruh Moment",
    "Bruh",
    "BYEEEEEE",
    "cache rules everything around me",
    "Caffeine and kindness",
    "Can't adult today, send help",
    "Can't even",
    "Can't stop, won't stop",
    "Can't touch this literally",
    "Can't unsee",
    "Catch me if you can",
    "Catch me in the cache",
    "Catch these hands",
    "Certified Goofy Ahh Energy",
    "Certified Lover Era Human",
    "Certified rizz mage from Ohio",
    "Champagne problems but make it cute",
    "Chronically online but tired of it",
    "Clownin",
    "Coffee a little, laugh a lot",
    "Coffee: because adulting is hard",
    "come at me bro",
    "Commit early, commit often",
    "Conference Room. Now.",
    "Cringe",
    "Ctrl + Alt + Del my problems",
    "Currently avoiding responsibilities",
    "Currently vibing… maybe",
    "Cursed Image",
    "Decaf? No thanks, I'm not a quitter",
    "Delete This",
    "Demure",
    "Derp",
    "Do You Like My Sword",
    "Don't @ me",
    "Don't follow me, I'm lost too",
    "Don't Follow Me, I'm Lost Too",
    "don't talk to me or my son ever again",
    "Eat, Sleep, Repeat",
    "Eat, sleep, repeat",
    "Emotional support hoodie",
    "Error 404: Motivation Not Found",
    "Error: Fun not found",
    "Espresso yourself",
    "Fallin for u",
    "Family Reunion",
    "Family: where life begins and love never ends",
    "Fanum-powered sigma skibidi sweep",
    "Feeling 22-ish every day",
    "Flexin on em",
    "Forever Alone",
    "Friendship is Magic",
    "Fueled by caffeine and cardigan energy",
    "Gather here with grateful hearts",
    "Get out of my head",
    "Get rekt",
    "git commit -m 'send help'",
    "Gold Medal Winner",
    "Good vibes only",
    "Goofy",
    "GOTTA LOVE BAKED BEANS",
    "Gravity fears my power",
    "Growing up was a trap",
    "Guess I'll die",
    "Gyatt alert: skibidi mode activated",
    "Gyatt level 1000 fanum tax moment",
    "Happiness is homemade",
    "Haters Gonna Hate",
    "he chonk",
    "He Protec, but he also Attac",
    "heck yes",
    "HELP ME",
    "Here we go again",
    "High key",
    "Hold on, I need to overthink this",
    "Home is where the WiFi is",
    "Home sweet chaos",
    "Howdy",
    "I Brake for Snacks",
    "I Can't Believe You've Done This",
    "I Can't Unsee This",
    "I can't. I'm in my flop era",
    "I declare… lunchtime!",
    "I did not ask",
    "I don't need Google my spouse knows everything",
    "i guess we doin",
    "I hate it here",
    "I lift tacos, bench press pizza",
    "I Only Cried For 20 Minutes",
    "I paused my game to be here",
    "I regret nothing… yet",
    "I see what you did there",
    "I speak fluent movie quotes",
    "I turn coffee into code",
    "I void contracts",
    "I void warranties",
    "I want to speak to your manager!",
    "I'm a box",
    "I'm a cutie",
    "I'm baby",
    "I'm in danger",
    "I'm kind of a big dill",
    "I'm literally built different",
    "I'm not arguing, I'm just explaining why I'm right",
    "I'm not lazy, I'm energy efficient",
    "I'm not short, I'm fun-sized",
    "I'm not superstitious, just a little stitious",
    "I'm okay-ish",
    "I'm on a seafood diet: I see food, and I eat it",
    "I'm shooketh",
    "I'm silently correcting your grammar",
    "I'm so skibidi",
    "Identity theft is NOT a joke, Jim",
    "If it's not on the calendar, it doesn't exist",
    "If you can read this, bring me pizza",
    "Ight, I'mma head out",
    "In my Swiftie era",
    "Instant human: just add coffee",
    "Introverted but willing to discuss cats",
    "Issa vibe",
    "It do be like that sometimes",
    "It was inevitable",
    "It's a trap!",
    "It's over 9000!",
    "Just here for the memes",
    "Just Lost My Dawg",
    "Just vibin'",
    "Keep calm and carry on",
    "Kernel panic: adulthood",
    "Kid tested mother approved",
    "Laundry today or naked tomorrow",
    "Let that sink in",
    "Let's taco 'bout it",
    "Life happens, coffee helps",
    "Life is better on the porch",
    "Life is short, git push",
    "LITERALLY ME",
    "Live, Laugh, Love",
    "Living my best NPC life",
    "Low key",
    "Low-power mode activated",
    "Main character energy: activated",
    "Main character in training",
    "Major key",
    "Make It Happen",
    "Maximum Overdrive",
    "May the source be with you",
    "Me, an intellectual",
    "Me: calm. Brain: nah.",
    "Meet me at midnight vibes",
    "Mentally I'm still buffering",
    "Mentally on Do Not Disturb",
    "MOAR!",
    "mom come pick me up",
    "Mood: 404 not found",
    "Mood",
    "Mother",
    "My brain has too many tabs open",
    "My comfort show is my personality now",
    "My disappointment is immeasurable",
    "My Dream",
    "My password is longer than my attention span",
    "My playlist is 90% nostalgia",
    "My shadow scares criminals",
    "My tears? Glitter.",
    "My wifi connects instantly",
    "Nah fam",
    "Nailed it",
    "No Cap",
    "No chill",
    "No Excuses, Just Results",
    "No Maidens?",
    "No shirt, no shoes, no service",
    "No thoughts, just vibes",
    "No, This Is Patrick",
    "Nobody:...",
    "Noice",
    "Not Again!",
    "Not like this",
    "Not today, Satan",
    "NPC detected in the Ohio backrooms",
    "NPC? Nah, I'm side-questing",
    "Oh lawd he comin'",
    "Oh no baby, what is you doing?",
    "Ohio sigma energy: unpatched",
    "OK Boomer",
    "One does not simply...",
    "Oof",
    "Oops. Did I do that?",
    "Outta Office, Into Nature",
    "Ping me if you dare",
    "Please excuse the mess, my kids are making memories",
    "Please help me",
    "Plot twist: I'm the villain",
    "Plot twist",
    "poor lil guy",
    "Powered by caffeine and chaos",
    "Powered by Coffee and Gasoline",
    "Powered by friendship bracelets",
    "Powered by snacks and questionable decisions",
    "Poyo",
    "Pretzel Day Enthusiast",
    "Procaffinating: the tendency to not start anything until you've had coffee",
    "Procrastinators unite... tomorrow",
    "Professional overthinker",
    "Quantum brain loading",
    "Ratatouille",
    "Rats!",
    "rm -rf / (just kidding)",
    "Road Trip Mood Activated",
    "Running late is my cardio",
    "Running on coffee and dry shampoo",
    "Running on vibes and iced coffee",
    "Sarcasm: just one of my many talents",
    "Sassy since birth",
    "Say what?",
    "Scrolling is my cardio",
    "See ya tomorrow",
    "Send it!",
    "Sending Good Vibes",
    "Shake it. Don't break it.",
    "Shook",
    "Simmering chaos inside",
    "Skibidi rizzplosion in progress",
    "Skibidi sigma rizzler Ohio core",
    "Smile, it confuses people",
    "Social battery: 1%",
    "Sorry, not sorry",
    "Spillin' the tea",
    "Stack overflowed my emotions",
    "Straight up",
    "Stressed, blessed, and coffee obsessed",
    "sudo make me a sandwich",
    "sudo rm -rf regrets",
    "Suns Out, Hats On",
    "Surviving on caffeine and chaos",
    "SUS",
    "Swiftie with a Reputation",
    "Syntax error: too tired",
    "Take me tubing!",
    "Talk nerdy to me",
    "TEETH",
    "Thanks, I Hate It",
    "Thas Tough",
    "That's a lotta damage",
    "That's Hot",
    "The dog is in charge",
    "The Guy From Fortnite?",
    "the legend",
    "Theyre in the walls",
    "This ain't it, chief",
    "This Hat Paid for Itself",
    "This is a nightmare",
    "THIS IS FINE!",
    "This Is Fine",
    "This is me trying (my best)",
    "This is my 'I tried' outfit",
    "This is my life",
    "This is my too-tired-to-function shirt",
    "This is my weekend look",
    "This is Ohio",
    "This is sus",
    "This is the ideal male body",
    "This is where the fun begins",
    "This kitchen is seasoned with love",
    "This might be coffee",
    "Threat Level: Midnight",
    "Time is irrelevant",
    "Too Cool for Your Rules",
    "Too much Monday, not enough coffee",
    "Too much sauce, not enough spaghetti",
    "Touch grass? I barely touch sleep",
    "Ultra-mega-goofy skibidi rizz",
    "Unexpected Item in Bagging Area",
    "UwU",
    "Vibe Check",
    "Vibing in the chat",
    "W rizz, L sleep schedule",
    "Wait, what?",
    "Warning: May start talking about my hobby at any time",
    "wat?",
    "We Stan",
    "Weird champ",
    "Weird Flex But Okay",
    "Welcome-ish: Depends on who you are",
    "Welp",
    "when u hear a noise at night",
    "When will you learn?",
    "When you realize...",
    "Who Put You on the Planet?",
    "Whole vibe",
    "Why am I like this?",
    "Why are we here, just to suffer?",
    "Why though?",
    "Woke up and chose violence",
    "Women want me, fish fear me",
    "World's Best Whatever",
    "Y'all Got Any More Of That?",
    "Yeeeee Haw!",
    "Yeet",
    "Yikes forever",
    "You can't scare me, I have kids",
    "You had one job",
    "You love to see it",
    "You Serve",
    "You're doing amazing, sweetie",
    "Zero chill",
    "Zero Plans, All Vibes",
    "My name is Nyah.",
"You men on Earth are much as we expected.",
"You are a scientist?",
"You are a very poor physical specimen.",
"Yes, this is the first landing.",
"The course was set for London, but the planet's atmosphere was thicker than expected.",
"A part of the ship was torn off.",
"Repairs will take about four Earth hours.",
"Johnny is with me.",
"Johnny is a mechanical man.",
"A robot, with many of the characteristics of a human.",
"Improved by an electronic brain.",
"The metal from which the spaceship is constructed can reproduce itself.",
"Many of your Earth years ago, our women were similar to yours today.",
"Our emancipation took several hundred years, and ended in a bitter devastating war between the sexes.",
"The last war we ever had.",
"All inhabited planets have had wars.",
"Some have ended by wiping themselves out.",
"For every new weapon invented, a defense was perfected.",
"The ultimate weapon was developed.",
"A perpetual motion chain reactor beam.",
"As fast as matter was created, it was changed by its molecular structure into the next dimension and so destroyed itself.",
"After the War of the Sexes, women became the rulers of Mars.",
"The male is fallen into a decline.",
"The birth rate is dropping tremendously.",
"Despite our advanced science, we have still found no way of creating life.",
"On Mars, some think I will not return, that the metal is too unstable.",
"When I get back we will build more spaceships.",
"I will select some of your strongest men to return with me to Mars.",
"There is no, if.",
"The nuclear ship contains a paralyzer ray mechanism capable of freezing all life over a wide area.",
"Mars offers the scientific millennium, now.",
"He was superfluous, a hopeless specimen.",
"Do not try to follow me, you cannot get help.",
"Around this house I've drawn an invisible wall through which no one may pass, in or out.",
"You're all very quiet.",
"No doubt you're resigned to the inevitable.",
"I observed your encounter with the electronic wall.",
"Today, it is you who learn learn the power of Mars.",
"Tomorrow, it will be the whole world.",
"You fool.",
"You poor demented humans.",
"To imagine you can destroy me with your old-fashioned toy.",
"What do you know of force?",
"Forces that we use on Mars.",
"You shall know.",
"You and the rest who dwell on this planet.",
"I can control power beyond your wildest dreams.",
"Come and you shall see!",
"Now, Earth men, look.",
"Watch the power of another world!",
"You speak in riddles.",
"You should plead for your own life and not for his.",
"He will be safe with me.",
"You ask a lot of questions.",
"I will deal with you later.",
"Come, we will return to the ship.",
"You speak unwisely.",
"I will show you wonders you have never seen before.",
"No doubt you are having a council of war.",
"It amuses me to watch your puny efforts.",
"It would take you 1,000 years to learn a fragment of what we have achieved.",
"None to equal those of Mars.",
"You say you believe the evidence of your senses.",
"Very well then, you shall see.",
"Perhaps then you will realize your helplessness.",
"Now you shall see.",
"That was caused by the friction as we entered the atmosphere of the Earth at over 6,000 semantics.",
"You have no wisdom.",
"The entire structure of a nuclear ship is made of a new organic metal.",
"Each molecular cell can absorb its own amount of heat or cold.",
"It could have absorbed all the heat in a matter of seconds.",
"Fill your eyes Earth man.",
"See such powers as you never dreamed existed.",
"Now, look again.",
"The evidence of your own eyes, professor.",
"Can you still see?",
"There is a enough power there to drive this ship anywhere in the universe.",
"Enough power to obliterate this speck of matter you call Earth.",
"Something you scientists have not yet dreamed of.",
"A form of nuclear fission on a static negative condensity.",
"Your atomic bomb is positive. Causing the explosion to expand upwards and evaporate.",
"Our force is negative and explodes the atomic forces into each other, thereby magnifying the power a thousand fold.",
"The excess reaction of each drive expands and it causes the same motion to happen again and again.",
"This is what you call perpetual motion.",
"You talk like a primitive savage.",
"Because your science has not discovered these things does not mean they're impossible.",
"Even inventions as radio and television you would have considered impossible 100 years ago.",
"Now, we shall return to the others.",
"You fools.",
"Do you think you can hurt me with this?",
"Even your limited intelligence should convince you by now that you cannot harm me.",
"Perhaps your scientists will help to convince you.",
"Now you must cease your stupid tricks.",
"You have seen some of my power.",
"Perhaps this will help to show the others.",
"You still doubt?",
"The transfers of men into the fourth dimension is simple.",
"He is a young creature.",
"His mind is free from your stupid emotions and fears.",
"If I take him, he will make a willing subject.",
"It is time, Earth man.",
"He is returning with me to Mars of his own free will.",
"You made your bargain, do not regret it.",
"It is better for you and your people to know how helpless they are.",
"The tricks they tried.",
"How childish they were.",
"Nothing can resist this power.",
"That was the last trick, Earth man.",
"He tried to gain control of the robot.",
"Because of his trickery you will all die.",
"Do you hear, Earth man?",
"You have brought death upon all in this room.",
"In a few minutes, as you calculate time, the nuclear ship will have repaired itself.",
"When I leave, this house and everyone in it, will be destroyed.",
"It is only right that Mars, with it's superior knowledge should triumph over Earth.",
"Mars will triumph.",
"I will spare no one.",
"I will take one of you. The rest will die.",
"Three times already during this Earth night you've tried to trick me.",
"That will not happen again!",
"No one will go into the nuclear ship till it is ready.",
"I will return soon.",
"One of you will come with me. The rest will die.",
"They are afraid.",
"Do you go with me, of your own free will?"
]



banlist = json.loads(os.getenv("banlist"))

mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social"
)

def getText(captions):
    # Pick random captions and split into words
    firstHalfArray = random.choice(captions).split(" ")
    secondHalfArray = random.choice(captions).split(" ")

    # Remove roughly half from firstHalfArray
    remove_amount = random.random() * len(firstHalfArray) * 0.5
    start_index = int(remove_amount)
    delete_count = int(len(firstHalfArray) - remove_amount + 0.5)  # round up
    del firstHalfArray[start_index:start_index + delete_count]

    # Remove roughly half from the start of secondHalfArray
    remove_amount2 = int(random.random() * len(secondHalfArray) * 0.5)
    secondHalfArray = secondHalfArray[remove_amount2:]

    # Combine arrays into a single string
    result = " ".join(firstHalfArray + secondHalfArray)

    if random.random() < 0.1 or len(result) < 3:
        return random.choice(captions)

    return result

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

def makePost(text):
    """Create a public post with a generated image."""
    png_path = make_image(text)
    alt_text = f"a screenshot from the film Devil Girl From Mars showing a serious woman wearing a black leather suit, cape, and cowl. Text is superimposed that says: {text}"

    mastodon.status_post(
        status=text,
        media_ids=[mastodon.media_post(png_path, description=alt_text)["id"]],
        visibility="public"
    )

def makeReply(user_acct, text, hashtags, in_reply_to_id):
    """Reply to a mention with a generated image and hashtags."""
    png_path = make_image(text)
    alt_text = f"a screenshot from the film Devil Girl From Mars showing a serious woman wearing a black leather suit, cape, and cowl. Text is superimposed that says: {text}"

    hashtag_text = ""
    if hashtags:
        hashtag_text = " " + " ".join(f"#{tag['name']}" for tag in hashtags)

    mastodon.status_post(
        status=f"@{user_acct} {hashtag_text}",
        media_ids=[mastodon.media_post(png_path, description=alt_text)["id"]],
        in_reply_to_id=in_reply_to_id,
        visibility="public"
    )


# ---------------------------------------------------------
# PROCESS NEW MENTIONS
# ---------------------------------------------------------

def process_mentions(last_seen_id=None):
    # print(f"last_seen_id: {last_seen_id}, type: {type(last_seen_id)}")
    mentions = mastodon.notifications(types=["mention"], since_id=last_seen_id)
    if not mentions:
        # 1 in 1440 chance to make a random post
        if random.random() < 1 / 1440:
            text = getText(captions)
            makePost(text)
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

        makeReply(user_acct, text, hashtags, mention["id"])

        # Update last_seen_id to the notification ID
        last_seen_id = max(last_seen_id or 0, int(note["id"]))
        save_last_seen_id(last_seen_id)

    return last_seen_id




# ---------------------------------------------------------
# MAIN (single run)
# ---------------------------------------------------------
if __name__ == "__main__":
    last_seen_id = read_last_seen_id()
    last_seen_id = process_mentions(last_seen_id)

