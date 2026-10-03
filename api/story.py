"""A story's words without its markdown. mobile/src/story.ts is the parser;
this mirrors its plain(), and tests/fixtures/story.json holds both to the
same answers (docs/10, "A story has a little markdown")."""

import re

MARK = re.compile(r"\*\*([^\s*](?:.*?[^\s*])?)\*\*|\*([^\s*](?:.*?[^\s*])?)\*")
PHOTO = re.compile(r"^!\[.*\]\(photo:\d+(?: [sml])?(?: (?:left|center|right))?\)$", re.S)


def plain(md: str) -> str:
    words = []
    for chunk in re.split(r"\n\s*\n", md.strip()):
        line = chunk.strip()
        if not line or PHOTO.match(line) or re.fullmatch(r"-{3,}", line):
            continue
        if line.startswith("## "):
            line = line[3:]
        elif line.startswith(">"):
            line = re.sub(r"^> ?", "", line, flags=re.M)
        words.append(MARK.sub(lambda m: m.group(1) or m.group(2), line))
    return "\n\n".join(words)
