from mastodon import Mastodon
from dotenv import load_dotenv
import os, random

load_dotenv()

mastodon = Mastodon(
    client_id=os.getenv("client_key"),
    client_secret=os.getenv("client_secret"),
    access_token=os.getenv("access_token"),
    api_base_url="https://mastodon.social",
)

movieCriteria = [
    "Which movie feels the LEAST likely to pass the Bechdel test?",
    "Which movie feels the MOST like a cash grab?",
    "Which movie feels the MOST like a ripoff of a better film?",
    "Which movie feels the MOST outdated?",
    "Which movie had the MOST wasted potential?",
    "Which movie has the CHEAPEST looking sets?",
    "Which movie has the LEAST amount of actual monster footage?",
    "Which movie has the LEAST amount of effort?",
    "Which movie has the LEAST rizz?",
    "Which movie has the LEAST threatening villian?",
    "Which movie has the MOST 'Damsel in Distress' energy?",
    "Which movie has the MOST 'Mad Scientist' energy?",
    "Which movie has the MOST aggressive Male Gaze?",
    "Which movie has the MOST annoying dialogue?",
    "Which movie has the MOST boring filler scenes?",
    "Which movie has the MOST confusing plot?",
    "Which movie has the MOST nonsensical science?",
    "Which movie has the MOST toxic masculinity?",
    "Which movie has the MOST toxic vibe?",
    "Which movie has the STUPIDEST character decisions?",
    "Which movie has the WORST acting?",
    "Which movie has the WORST characters?",
    "Which movie has the WORST cinematography?",
    "Which movie has the WORST costume and production design?",
    "Which movie has the WORST day-for-night lighting?",
    "Which movie has the WORST ending?",
    "Which movie has the WORST hero?",
    "Which movie has the WORST monster/creature design?",
    "Which movie has the WORST music and sound design?",
    "Which movie has the WORST plot twist?",
    "Which movie has the WORST story/script?",
    "Which movie has the WORST title?",
    "Which movie has the WORST visual effects/CGI?",
    "Which movie is the BIGGEST disaster?",
    "Which movie is the LEAST dramatic?",
    "Which movie is the LEAST fun?",
    "Which movie is the LEAST interesting?",
    "Which movie is the LEAST memorable?",
    "Which movie is the LEAST rewatchable?",
    "Which movie is the LEAST scary?",
    "Which movie is the LEAST thought-provoking?",
    "Which movie is the MOST annoying?",
    "Which movie is the MOST cheap?",
    "Which movie is the MOST cringe?",
    "Which movie is the MOST cursed?",
    "Which movie is the MOST dusty?",
    "Which movie is the MOST embarrassing?",
    "Which movie is the MOST fake?",
    "Which movie is the MOST hideous?",
    "Which movie is the MOST lazy?",
    "Which movie is the MOST offensive?",
    "Which movie is the MOST pointless?",
    "Which movie is the MOST small?",
    "Which movie is the MOST stiff?",
    "Which movie is the MOST thirsty?",
    "Which movie is the MOST tone deaf?",
    "Which movie is the MOST unnecessary?",
]


movieList = [
"Dr. Who and the Daleks (1965)",
"4D Man (1959)",
"Devil Doll (1964)",
"Planet Earth (1974)",
"The Quatermass Xperiment (1955)",
"Mothra (1961)",
"Godzilla (1998)",
"Death Race 2000 (1975)",
"Time Walker (1982)",
"Tales from the Crypt (1972)",
"The She-Creature (1956)",
"Attack of the Puppet People (1958)",
"The Asphyx (1972)",
"Space Master X-7 (1958)",
"Alligator (1980)",
"Vampires on Bikini Beach (1988)",
"Critters 3 (1991)",
"The Howling (1981)",
"Pumpkinhead (1988)",
"The Hunger (1983)",
"Fright Night (1985)",
"The Food of the Gods (1976)",
"The Angry Red Planet (1959)",
"Creature from the Black Lagoon (1954)",
"The Man from Planet X (1951)",
"Grizzly (1976)",
"Swamp Thing (1982)",
"The Little Shop of Horrors (1960)",
"Godzilla, Mothra and King Ghidorah: Giant Monsters All-Out Attack (2001)",
"The Raven (1963)",
"Vampire Circus (1972)",
"Maximum Overdrive (1986)",
"X: The Man with the X-Ray Eyes (1963)",
"Frankenstein Meets the Space Monster (1965)",
"Clash of the Titans (1981)",
"Starcrash (1978)",
"Bog (1979)",
"Dracula, Prisoner of Frankenstein (1972)",
"Godzilla: Final Wars (2004)",
"Forbidden Planet (1956)",
"Beyond Atlantis (1973)",
"Slugs (1988)",
"The Gate (1987)",
"The Bat People (1974)",
"First Men in the Moon (1964)",
"Krull (1983)",
"Laserblast (1978)",
"Cat Girl (1957)",
"Critters 2 (1988)",
"Yeti: The Giant of the 20th Century (1977)",
"Critters (1986)",
"C.H.U.D. (1984)"
]



def main():
    emojis = ["🚨","🧟", "👾", "👺", "☢️", "💀", "🦇", "🏚️", "🧪", "🎥", "🔥", "🎬", "🎞️", "🍿", "🧛", "🛸","🤢","🩸","😱","👻","👽","🎃","👹"]
        
    movie1, movie2 = random.sample(movieList, 2)
    question = random.choice(movieCriteria)
    
    poll = mastodon.make_poll(
        options=[movie1, movie2],
        expires_in=86400, 
        multiple=False
    )
    e1, e2 = random.sample(emojis, 2)
    post_text = f"{e1}{e2} MARCH BADNESS POLL {e2}{e1} {question}\n\n#monsterdon #MarchBadness" 
    mastodon.status_post(
        status=f'{post_text}',
        poll=poll,
        visibility="public",
    )

if __name__ == "__main__":
    main()