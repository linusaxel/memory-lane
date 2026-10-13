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

## How to send

From the research of 2026-10-13 (cold-email reply data from Hunter, Gong,
Woodpecker and Boomerang; Flynn & Bohns and Roghanizad & Bohns on asking
strangers; university permission-letter guides from Stanford and Columbia):

- One email per rights holder, sent by hand from your own address, with no
  open tracking. Strangers say yes more often than we expect, but email is
  the weakest way to ask: where a society lists a phone number, a call works
  better.
- Short: under about 120 words. Who you are, what the app gives people, then
  one ask they can answer with "yes". No compliments about their work: they
  read as fake.
- Say the app is a business. A yes to commercial use only counts if they
  knew.
- Say what we already use of theirs.
- At most one link, no attachments.
- Follow up twice in the same thread, shorter each time: after about a week,
  then after three. Then stop. No reply means no.
- Keep the yes in writing and file it on the source row.

Follow-up, as a reply in the same thread:

> Hi [first name], just bumping this in case it got buried. A yes or no is
> all I need. Thanks!

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

---

## 1. Arbejdermuseet: Humlen ved Carlsberg

To: am@arbejdermuseet.dk

Subject: Humlen ved Carlsberg

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the workers' stories from Humlen ved Carlsberg in the app.

We'd write them in our own words, credit you with a link, and take anything down if you ask. I saw that the site allows non-commercial use only, so I'm asking first.

A yes or no is all I need, and tell me if you'd like the credit worded a certain way.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 2. Lokalhistorisk Selskab for Brønshøj, Husum og Utterslev

To: bo.oehrstroem@gmail.com
Cc: info.lhsbhu@gmail.com

Subject: Your local history articles

Hi Bo,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the articles from Nyt fra Lokalhistorien in the app.

We have very few stories from Brønshøj, Husum and Utterslev so far. We'd write them in our own words, credit you with a link, and take anything down if you ask.

A yes or no is all I need. If Min barndom på Bispebjerg exists as text, I'd like to ask about that too.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 3. Københavns Stadsarkiv: the memoirs

To: XM9P@kk.dk
Cc: stadsarkiv@kk.dk

Subject: Access to the memoir collection

Hi Eva,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the memoirs in your collection in the app.

We'd write them in our own words, link to each memoir, leave out private people's names, and take anything down if you ask. Could we get them as text, through an API or an export? I didn't want to scrape kbharkiv.dk.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 4. Kgs. Enghave Lokalhistoriske Arkiv (Sydhavnens historie)

To: sydhavnen@outlook.dk

Subject: Your memoir articles

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the memoir articles on sydhavnenshistorie.dk in the app.

We have almost no stories from Sydhavnen so far. We'd write them in our own words, credit you with a link, leave out private people's names, and take anything down if you ask.

A yes or no is all I need.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 5. Frederiksberg Stadsarkiv: Frederiksberg-erindringer

To: cach01@frederiksberg.dk
Cc: stadsarkivet@frederiksberg.dk

Subject: Frederiksberg-erindringer transcripts

Hi Caspar,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the Frederiksberg-erindringer films in the app.

We'd write them in our own words, credit the archive and the storyteller with a link to the film, and take anything down if you ask. Do the films have transcripts or subtitles? We don't transcribe audio, so we need text to find the places.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 6. Bryggebladet

To: redaktion@bryggebladet.dk

Subject: Bryggebladet stories

Hi Andreas,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of Bryggebladet's stories in the app.

We'd write them in our own words, credit you with a link, and take anything down if you ask. We already tried this on a few issues from 2019 on, before I saw your copyright page. If you'd rather we didn't, we'll delete it.

A yes or no is all I need.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 7. Nørrebro Lokalhistoriske Forening

To: info@noerrebrolokalhistorie.dk

Subject: Your yearbooks

Hi Jan,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from your yearbooks in the app.

We'd write them in our own words, credit you with a link, and take anything down if you ask. We already tried this on a few yearbooks, and I should have asked first. If you'd rather we didn't, we'll delete it.

A yes or no is all I need.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 8. SLAK

To: helge.olesen@email.dk

Subject: Local history societies

Hi Helge,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask the local history societies for permission to use some of their articles in the app.

I'd like to ask the local history societies in Østerbro, Valby and Vesterbro if it would be okay to retell some of their articles at the places they're about. Could you tell me who to write to?

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 9. Københavnerglimt

To: info@dnrmedia.dk

Subject: Københavnerglimt

Hi Allan,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from Københavnerglimt in the app.

We'd write them in our own words, show no clips, and link to the video at the moment the story is told. We already tried this on your videos, and I should have asked first. If you'd rather we didn't, we'll delete it.

I think DNR Media makes the channel. If not, could you pass this on? A yes or no is all I need.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 10. Københavnerliv

To: the address behind "View email" on youtube.com/@Kbherliv/about

Subject: Københavnerliv

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from your videos in the app.

We'd write them in our own words, show no clips, and link to the video at the moment the story is told. We already tried this on your videos, and I should have asked first. If you'd rather we didn't, we'll delete it.

A yes or no is all I need.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 11. Christiania1 (via Christianias Arkiv)

To: caarkiv@gmail.com

Subject: The christianiahistorie films

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from the christianiahistorie films on the Christiania1 channel in the app.

We'd write them in our own words, show no clips, and credit the channel and the storyteller with a link. We already tried this on a few films, and I should have asked first. If you'd rather we didn't, we'll delete it.

The channel says it's part of your archive. If I've got the wrong people, could you pass this on? A yes or no is all I need.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 12. Kim Greiner

To: kim@greiner.dk

Subject: Your Nyhavn and Christianshavn pages

Hi Kim,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from your pages on Nyhavn and Christianshavn in the app.

We'd write them in our own words, with your name and a link to your page, and take anything down if you ask. We've already done this with a few of them, and I should have asked first. If you'd rather we didn't, we'll delete it.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 13. Refshaleøen TV, Kim Bargsteen

To: mail@refshaleoen.dk (no address for the channel; ask them to pass it on)

Subject: For Refshaleøen TV and Kim Bargsteen

Hi,

I can't find an address for Refshaleøen TV. Could you pass this on to them, or to Kim Bargsteen? Thank you.

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from the film Refshaleøens historie in the app.

We'd write them in our own words, credit the channel and Kim Bargsteen with a link to the film, and take anything down if you ask. Is there a transcript of the film? We don't transcribe audio, so we need text to find the places.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 14. Dansk rockhistorie

To: the address behind "View email" on the channel's About page
(`UCz0mJQVpBbLIjOq-oOb2nkA`); kontakt@peterbak.dk only if that fails

Subject: Dansk rockhistorie

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from your videos in the app.

We'd write them in our own words, show no clips, link to the video at the moment the story is told, and take anything down if you ask.

A yes or no is all I need.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 15. Kenneth A. Balfelt

To: kenneth@kennethbalfelt.org

Subject: Your Enghave Plads films

Hi Kenneth,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from your Enghave Plads films in the app.

We'd write them in our own words, with your name and a link, without naming the people in them, and take anything down if you ask. Is there a transcript of the films? We don't transcribe audio, so we need text to find the places.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 16. Shazia Khan: Al Magt til Kærligheden

To: zarzia@gmail.com

Subject: Al Magt til Kærligheden

Hi Shazia,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the portraits from Al Magt til Kærligheden in the app.

We'd write them in our own words, with your name and a link, and take anything down if you ask. Do the portraits exist as text? We don't transcribe audio, so we need text to find the places.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 17. Stemmer fra Bjerget

To: the address behind "View email" on youtube.com/@bbh_frh_hosp/about

Subject: Stemmer fra Bjerget

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the stories from Stemmer fra Bjerget in the app.

We'd write them in our own words, credit you with a link to the episode, never name patients, and take anything down if you ask.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 18. kbhbilleder

To: kbhbilleder@kff.kk.dk (unverified; if it bounces, stadsarkiv@kk.dk)

Subject: Copyright-free photos through your API

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of your copyright-free photos in the app.

Each photo would carry the archive, the photographer and a link back, and we'd take anything down if you ask. Could I fetch them with their locations through your API? I don't want to load the website.

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]

---

## 19. Historisk Atlas

To: info@historiskatlas.dk

Subject: API access

Hi,

I'm [name], and I'm building Memory Lane, a walking app for Copenhagen. It plans a walk for you, and when you reach a place where something happened, it shows a short story about it. The idea is to get people out walking and curious about their own city.

I'm messaging you because I'd like to ask for permission to use some of the openly licensed stories from Historisk Atlas in the app.

We'd follow each licence and credit Historisk Atlas with a link. To see which stories are open, I'd need access to your API. Could I get that?

For the sake of transparency, the app is free to try and has a paid subscription.

Thanks so much for reading, and I'd be really happy to hear back from you!

Kind regards,
[name]
[phone]
