# Permission requests

Every source we may only use with a yes, and the email that asks for it. Send
from the founder's own address, one at a time, and fill in `[name]` and
`[phone]`. When a reply comes, file its date and wording on the `sources`
row (`pipeline.sources set <id> ... --note`) and update the tracker.

docs/10-decisions.md, *The sources' legal footing* and *Recent sources without
permission*, says why each needs asking: a channel always does; a site whose
terms say "non-commercial", "after agreement" or "no digital copies" does; a
block (WAF, robots, ai.txt) is never gone around.

Contacts were checked on each organisation's own pages on 2026-10-13. Where
the address is a guess or sits behind YouTube's "View email" button, the
tracker says so.

## Tracker

Ordered by what a yes adds to the goal's empty cells (make-memories skill,
step 0).

| # | Who | Send to | What a yes unlocks | Status |
|---|---|---|---|---|
| 1 | Arbejdermuseet, *Humlen ved Carlsberg* | am@arbejdermuseet.dk (rights go through the museum; site by Kathrine Noes Sørensen and Hans Uwe Petersen) | 195 brewery workers' posts, 1950s-2008; Carlsberg cell is empty | Not sent |
| 2 | Lokalhistorisk Selskab for Brønshøj, Husum og Utterslev | Bo Öhrström, formand, bo.oehrstroem@gmail.com, cc info.lhsbhu@gmail.com | *Nyt fra Lokalhistorien* and the Bispebjerg and Nordvest books; empty cells | Not sent |
| 3 | Københavns Stadsarkiv, erindringer | Eva Greve Mortensen, arkivar, XM9P@kk.dk, cc stadsarkiv@kk.dk | ~3,300 memoirs from 1969 and 1995, every district | Not sent (an older thread exists; mention it if it was with her) |
| 4 | Kgs. Enghave Lokalhistoriske Arkiv (sydhavnenshistorie.dk) | sydhavnen@outlook.dk (no names on the site) | 26 erindringsartikler, 1940s-60s; Sydhavn cells are empty | Not sent |
| 5 | Frederiksberg Stadsarkiv, *Frederiksberg-erindringer* | Caspar Christiansen, stadsarkivar, cach01@frederiksberg.dk, cc stadsarkivet@frederiksberg.dk | 50+ first-person films, if transcripts exist; west Frederiksberg | Not sent |
| 6 | Bryggebladet | Andreas Kirkeskov, redaktør, redaktion@bryggebladet.dk | A yes for source 247 (in use), and the 2003-06 archive | Not sent |
| 7 | Nørrebro Lokalhistoriske Forening | Jan Malinowski, formand, info@noerrebrolokalhistorie.dk | A yes for source 248 (in use), 24 yearbooks | Not sent |
| 8 | SLAK | Helge Rørdam Olesen, formand, helge.olesen@email.dk | An introduction to the Østerbro, Valby and Vesterbro societies | Not sent |
| 9 | Københavnerglimt | info@dnrmedia.dk (a guess from the videos' #DNRmedia.dk tag); presenter Allan Mylius Thomsen | A yes for source 3, our biggest (336 memories) | Not sent |
| 10 | Københavnerliv | YouTube About page, "View email" (sign in); kbherliv.dk blocks us | A yes for source 2 (in use) | Not sent |
| 11 | Christiania1 | caarkiv@gmail.com (Christianias Arkiv, where the channel says it sits) | A yes for source 7 (in use) | Not sent |
| 12 | Kim Greiner, rejsefortaelling.dk | kim@greiner.dk | A courtesy yes for sources 387-412 (in use, no opt-out) | Not sent |
| 13 | Refshaleøen TV, Kim Bargsteen | No address found. Ask mail@refshaleoen.dk (the landlord) to pass it on | *Refshaleøens historie* (2022), if there is a transcript | Not sent |
| 14 | Dansk rockhistorie | YouTube About page, "View email"; maybe kontakt@peterbak.dk (a guess via budowski.dk) | Source 414, five videos waiting | Not sent |
| 15 | Kenneth A. Balfelt | kenneth@kennethbalfelt.org | The Enghave Plads films, if there is a transcript | Not sent |
| 16 | Shazia Khan, *Al Magt til Kærligheden* | zarzia@gmail.com | 61 Christiania portraits, if there is text | Not sent |
| 17 | Stemmer fra Bjerget (Bispebjerg and Frederiksberg Hospital) | YouTube About page, "View email" | Hospital podcast with captions | Not sent |
| 18 | kbhbilleder | kbhbilleder@kff.kk.dk (unverified: the site blocks us); else stadsarkiv@kk.dk | ~5,000 free, placed photos via the API | Not sent |
| 19 | Historisk Atlas | info@historiskatlas.dk (it@ is not on their pages) | Each story's licence via the API | Not sent |

Later, no email drafted: Marinehistorisk Selskab (Gustav Lang,
langgustav@gmail.com), DieselHouse (dieselhouse@everllence.com),
Christianshavns Kvarter (info@christianshavnskvarter.dk) and Frederiksberg
Lokal TV (form at frbtv.dk/kontakt), both uncaptioned. Dropped: Euroman and
Eurowoman have no *Mit København* series (that was Copenhagen Sundays', which
opts out), and Realdania's *Mit sted* is a podcast with no text.

## What every email promises

Each has to be true before we send:

- Our own words: a short text about one episode, never more than a line
  quoted, never an excerpt or a clip.
- They are named as the source, with a link back, on every memory.
- The text is forgotten once extracted (`pipeline.transcripts.forget`; for
  videos, run `python -m pipeline.transcripts --forget-extracted` first).
- A stop is honoured within a day, for one story or the whole source.
- No proxy for a permitted channel: drop `WEBSHARE_PROXY_*` for it.
- A private person who may be alive is not named without asking.

The price line follows *A free walk a week* (docs/10). Change it in every
email if that decision changes.

---

## 1. Arbejdermuseet: Humlen ved Carlsberg

To: am@arbejdermuseet.dk

Subject: Humlen ved Carlsberg in a walking app

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Humlen ved Carlsberg is full of those. The two-øre strike in 1965, for
example. People walk through Carlsberg Byen today without knowing what went
on in the buildings, and it's exactly the kind of neighbourhood where we're
short of stories.

The site says the texts may only be quoted in a non-commercial setting, so
I'm asking first. This is how we would use them:

We write a short text about one episode in our own words and quote at most
a single line. Every story names Arbejdermuseet and Humlen ved Carlsberg as
the source, with a link to the post. We don't keep the texts after reading
them. We don't name colleagues without asking. And if you want a story
taken down, or all of them, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you? I'm happy to answer questions, by phone too.

Best regards,
[name]
[phone]

---

## 2. Lokalhistorisk Selskab for Brønshøj, Husum og Utterslev

To: bo.oehrstroem@gmail.com
Cc: info.lhsbhu@gmail.com

Subject: Your local history in a walking app

Hi Bo,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Brønshøj, Husum, Utterslev and Bispebjerg are where we have the fewest
stories. Your magazine has exactly those, like the memorial stone by the
village pond in 1931, and the films shot at Emdrupborg from 1911 to 1917. It
says reprinting is allowed by agreement, so I'm asking if we may use the
articles like this:

We write a short text about one episode in our own words and quote at most
a single line. Every story names the society as the source, with a link to
you, including how to become a member. We don't keep the texts after reading
them. We don't name private people who may still be alive without asking.
And if you want a story taken down, or all of them, it's gone within a day.

If you also have Min barndom på Bispebjerg or Erindringssamtaler fra
Nordvest-Bispebjerg as text, I'd like to ask the same for those.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 3. Københavns Stadsarkiv: the memoirs

To: XM9P@kk.dk
Cc: stadsarkiv@kk.dk

Subject: The 1969 and 1995 memoirs in a walking app

Hi Eva,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Your memoirs are the best record there is of what the city was like to live
in, street by street. The children playing on Sønder Boulevard in 1955, or
where people stood on 4 May 1945. We haven't taken anything from
kbharkiv.dk, and we won't without permission.

Could we get access to the memoirs as text, through an API or an export?
This is how we would use them:

We write a short text about one episode in our own words and quote at most
a single line. Every story names the City Archives as the source, with a
link to the memoir on your site. We don't name private people, only the
place and what happened. We don't keep the texts after reading them. And if
you want a story taken down, or all of them, it's gone within a day.

If there are special rules for memoirs whose writers may still be alive,
I'd like to know them.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]

---

## 4. Kgs. Enghave Lokalhistoriske Arkiv (Sydhavnens historie)

To: sydhavnen@outlook.dk

Subject: Your memoir articles in a walking app

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

We have almost no stories from Sydhavnen yet. Your memoir articles from the
40s, 50s and 60s are exactly what we're missing. The site says they may only
be reproduced by agreement, so I'm asking if we may use them like this:

We write a short text about one episode in our own words and quote at most
a single line. Every story names the archive as the source, with a link to
the article. We don't keep the texts after reading them. We don't name
private people who may still be alive without asking. And if you want a
story taken down, or all of them, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 5. Frederiksberg Stadsarkiv: Frederiksberg-erindringer

To: cach01@frederiksberg.dk
Cc: stadsarkivet@frederiksberg.dk

Subject: Frederiksberg-erindringer in a walking app

Hi Caspar,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen and Frederiksberg. Along the way you pass places where something
happened, and when you stand there, you can read a short story about it.

Your films of people telling their own Frederiksberg are exactly that, like
Elektrikeren og Mariendalskvarteret. I have two questions.

Are there transcripts or subtitles for the films? We don't transcribe audio
ourselves, so without text we can't find the places.

And may we use them like this: We write a short text about one episode in
our own words and never show clips. Every story names the archive and the
storyteller as the source, with a link to the film. We don't keep the text
after reading it. We don't name other private people the storyteller
mentions. And if you want a story taken down, or all of them, it's gone
within a day.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]

---

## 6. Bryggebladet

To: redaktion@bryggebladet.dk

Subject: Islands Brygge stories in a walking app

Hi Andreas,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Bryggebladet has stories about Islands Brygge that nobody else has, like
the two centenarians who moved into Egilsgade 59 in 1908. We tried finding
stories in some of your issues from 2019 onwards. Afterwards I saw your
copyright page, so I'm asking now. If you say no, we'll delete it.

This is how we would use the articles: We write a short text about one
episode in our own words and quote at most a single line. Every story names
Bryggebladet with the date and a link to the article. We don't keep the
texts after reading them. We don't name private people who may still be
alive without asking. And if you want a story taken down, or all of them,
it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 7. Nørrebro Lokalhistoriske Forening

To: info@noerrebrolokalhistorie.dk

Subject: Your yearbooks in a walking app

Hi Jan,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Your yearbooks are full of those. The best one we've found is Kierkegaard's
burial at Assistens Cemetery in 1855, from the 2023 yearbook. We tried it out
on some of the yearbooks, and I should have asked first. If you say no,
we'll delete it.

This is how we would use them: We write a short text about one episode in
our own words and quote at most a single line. Every story names the society
with a link to the yearbook, including how to become a member. We don't keep
the texts after reading them. We don't name private people who may still be
alive without asking. And if you want a story taken down, or all of them,
it's gone within a day.

If the person who donated a piece has put limits on it, please tell me.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 8. SLAK

To: helge.olesen@email.dk

Subject: Could you point me to the local history societies?

Hi Helge,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

The best stories we've found come from the local history societies: people
telling about their own street. I'm already asking Nørrebro and Sydhavnen,
and I'd like to reach the societies in Østerbro, Valby and Vesterbro too.

We write a short text about one episode in our own words, the society is
named as the source with a link, we don't keep the texts, and a society can
always say stop.

Would you pass this on, or tell me who to write to?

Best regards,
[name]
[phone]

---

## 9. Københavnerglimt

To: info@dnrmedia.dk

Subject: Københavnerglimt in a walking app

Hi Allan,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

I'm writing to DNR Media because I believe you make Københavnerglimt. If
that's wrong, could you pass this on?

Your videos are the best we've found. The KB footballers arrested in
Guldbergsgade for showing their legs, for example, or the bells of Vor Frue
playing like a hymn while the tower burned. We tried it out on your videos,
and I should have asked first. If you say no, we'll delete it.

This is how we would use them: We write a short text about one episode in
our own words and never show clips. Every story names Københavnerglimt at
the top, with a link that opens the video on YouTube right where the story
is told. We read the subtitles once to find the places and delete them
afterwards. And if you want a story taken down, or all of them, it's gone
within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 10. Københavnerliv

To: the address behind "View email" on youtube.com/@Kbherliv/about

Subject: Københavnerliv in a walking app

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Your videos are full of those. The bar in the old Hotel Kong Frederik, for
example, where Politiken's journalists and Tom Kristensen sat after work. We
tried it out on your videos, and I should have asked first. If you say no,
we'll delete it.

This is how we would use them: We write a short text about one episode in
our own words and never show clips. Every story names Københavnerliv at the
top, with a link that opens the video on YouTube right where the story is
told. We read the subtitles once to find the places and delete them
afterwards. And if you want a story taken down, or all of them, it's gone
within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 11. Christiania1 (via Christianias Arkiv)

To: caarkiv@gmail.com

Subject: The Christiania stories in a walking app

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

The YouTube channel Christiania1 says it belongs to your archive, so I hope
you're the right people to ask. If not, could you pass this on?

The christianiahistorie films are full of those stories. Mikael Fock on
Solvognen and the poison store at Sadolin & Holmblad, for example. We tried
it out on some of the films, and I should have asked first. If you say no,
we'll delete it.

This is how we would use them: We write a short text about one episode in
our own words and never show clips. Every story names the channel and the
storyteller as the source, with a link that opens the film right where the
story is told. We read the subtitles once and delete them afterwards. And
if you want a story taken down, or all of them, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 12. Kim Greiner

To: kim@greiner.dk

Subject: Your stories about Nyhavn and Christianshavn

Hi Kim,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Your pages on the houses of Nyhavn and on Christianshavn are some of the
best we've found. The Titanic tickets sold at Nyhavn 1, for example, and the
prison revolt of 1817 where Lagkagehuset is now. We've already used them,
and I'd like to hear if that's all right with you.

We write a short text about one episode in our own words and quote at most
a single line. Every story carries your name and a link to your page. We
don't keep the texts after reading them. And if you want a story taken
down, or all of them, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]

---

## 13. Refshaleøen TV, Kim Bargsteen

To: mail@refshaleoen.dk (no address for the channel; ask them to pass it on)

Subject: For Refshaleøen TV and Kim Bargsteen: Refshaleøens historie

Hi,

I can't find an address for Refshaleøen TV. Could you pass this on to them,
or to Kim Bargsteen? Thank you.

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

The 2022 film Refshaleøens historie, where Kim Bargsteen tells about B&W, is
exactly that. There's almost nothing about Refshaleøen told by someone who
was there. I have two questions.

Is there a transcript or subtitles for the film? We don't transcribe audio
ourselves, so without text we can't find the places.

And may we use it like this: We write a short text about one episode in our
own words and never show clips. Every story names the channel and Kim
Bargsteen as the source, with a link that opens the film right where the
story is told. We don't keep the text after reading it. And if you want a
story taken down, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]

---

## 14. Dansk rockhistorie

To: the address behind "View email" on the channel's About page
(`UCz0mJQVpBbLIjOq-oOb2nkA`); kontakt@peterbak.dk only if that fails

Subject: Dansk rockhistorie in a walking app

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Your portraits of musicians tell about the rehearsal rooms, venues and
studios where it happened. Flemming Rasmussen on Sweet Silence Studio, for
example. We'd like to let people stand at the spot and hear the story.

This is how we would use them: We write a short text about one episode in
our own words and never show clips. Every story names the channel and the
musician as the source, with a link that opens the video on YouTube right
where the story is told. We read the subtitles once and delete them
afterwards. And if you want a story taken down, or all of them, it's gone
within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 15. Kenneth A. Balfelt

To: kenneth@kennethbalfelt.org

Subject: Your films from Enghave Plads

Hi Kenneth,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Your films with the beer drinkers at Enghave Plads are one of the few places
where people tell about Vesterbro and Sydhavnen themselves. I have two
questions.

Is there a transcript or subtitles for the films? We don't transcribe audio
ourselves, so without text we can't find the places.

And may we use them like this: We write a short text about one episode in
our own words and never show clips. Every story names you as the source,
with a link to the film. We don't name the people in them without asking.
We don't keep the text after reading it. And if you want a story taken
down, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]

---

## 16. Shazia Khan: Al Magt til Kærligheden

To: zarzia@gmail.com

Subject: Al Magt til Kærligheden in a walking app

Hi Shazia,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Your portraits of Christianites tell about life in Christiania, place by
place, from the people who were there. I have two questions.

Do the portraits exist as text? We don't transcribe audio ourselves, so
without text we can't find the places.

And may we use them like this: We write a short text about one episode in
our own words and quote at most a single line. Every story names you and
the storyteller, with a link to you. We don't keep the text after reading
it. And if you want a story taken down, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]

---

## 17. Stemmer fra Bjerget

To: the address behind "View email" on youtube.com/@bbh_frh_hosp/about

Subject: Stemmer fra Bjerget in a walking app

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Stemmer fra Bjerget tells about life at Bispebjerg Hospital from the people
who were there. Bispebjerg is one of the areas where we have the fewest
stories.

This is how we would use the episodes: We write a short text about one
episode in our own words and never show clips. Every story names the podcast
and the hospital as the source, with a link to the episode. We don't name
patients. We read the subtitles once and delete them afterwards. And if you
want a story taken down, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Is that all right with you?

Best regards,
[name]
[phone]

---

## 18. kbhbilleder

To: kbhbilleder@kff.kk.dk (unverified; if it bounces, stadsarkiv@kk.dk)

Subject: Your free pictures in a walking app

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you see a short story about it. An old picture of that
exact spot is often the best story of all.

May I fetch the pictures that are out of copyright and free for commercial
use, with their locations, through your API? I don't want to load the
website. And is there a list of exactly those pictures, or a field that
says so?

Under every picture we name the archive, the photographer and a link to the
picture on your site. We only use free pictures. And if you want a picture
taken down, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]

---

## 19. Historisk Atlas

To: info@historiskatlas.dk

Subject: Access to your API

Hi,

My name is [name], and I'm building Memory Lane, an app that plans walks in
Copenhagen. Along the way you pass places where something happened, and when
you stand there, you can read a short story about it.

Could I get access to your API, so I can see each story's licence and its
full text? We only use stories under CC BY, CC BY-SA or in the public domain,
and follow the licence's terms. Every story names Historisk Atlas as the
source, with a link to the story on your site. And if you want a story taken
down, it's gone within a day.

The app is free with one walk a week. More walks cost a subscription.

Best regards,
[name]
[phone]
