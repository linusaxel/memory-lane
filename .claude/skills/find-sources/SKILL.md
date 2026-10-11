---
name: find-sources
description: Find, vet and trial new sources of place memories for Memory Lane (podcasts, press, books, archives, open data). Use when asked to find more memories, new sources, or to check whether a feed, book, archive or channel is worth ingesting.
---

# Find sources

A source is worth it when its stories happen *at a spot a walker can stand on*,
we may use it, and it yields memories that score on the walk rubric. This is
the funnel, in order. Each step is cheap until the one marked **bills**.

Read first: `docs/10-decisions.md` → *The sources' legal footing* (the table),
*Sources are a Protocol and a registry*, *Sources are rows with a status*.

## 0. Already searched (read before researching)

Re-check only what is marked open. Dated, so a stale entry can be re-tried.

**Without permission (2026-10-05)** is allowed for sources that don't opt
out, as long as nothing circumvents a block: docs/10, *Recent sources without permission*.

**By era (2026-10-05).** The free sources stop at about 1945. Living memory,
and above all the 2010s to now, comes only from permission or from people in
the app. Don't search the open web for *openly licensed* recent stories
again. The modern seam is first-party pages under the without-permission rule:
festivals', venues' and institutions' own history pages and news archives.

| Era | Where it is | State |
|---|---|---|
| 2010s-now | Wikidata events in the bbox with P585 ≥ 2010: about 10 (Hotel Jørgensen 2010, the 2015 shootings, Field's 2022, Børsen 2024). Mostly grim, so they fail "glad to know" | Not worth a source |
| 2010s-now | Nonprofit local papers as PDFs, with no TDM reservation: Bryggebladet (redaktion@bryggebladet.dk, about 21 issues a year 2003-26), Christianshavneren (christianshavneren@beboerhus.dk, 2011-17 plus web), Havnefronten (red@havne-fronten.dk, since 2020, mostly openings) | Registered (`pdfs:` index pages): Bryggebladet 247 from 2019 (the archive page lists only 2019 onwards; news plus ad pages), Christianshavneren 250 (homepage PDFs, mostly event listings), Nørrebro yearbooks 248 from 2010 (recent issues write about older history). Havnefronten 249 was rejected: its feed is council news through a tracker. Trialled 5 items each (2026-10-07): 247 mean 4.5 and 250 mean 4.3 (civic news), 248 mean 6.3 but every memory is pre-1900. All under the bar |
| 2000-now | Small papers with no opt-out (2026-10-07): NABO, Humleby's residents' paper (humleby.dk/nabo, 153 issues 2008-26, one hop post→PDF, HTML behind a browser check, PDFs open); fsb beboeren (fsb.dk/om-fsb/udgivelser/fsb-beboeren, about 22 issues 2010-20, one hop); Kilden, Strandvejskvarteret (one 352 MB PDF 1981-2021); Magasinet KBH (magasinetkbh.dk/arkiv, 43 PDFs 2005-09, a company, "må ikke eftertrykkes", mostly architecture); Valby Lokalhistoriske's newsletter (valbylokalhistorie.dk/aarsskrifter, 11 PDFs 1985-2003, mostly pre-1960, one gem: the 1991 village pond dig) | Registered 2026-10-07 as 252 NABO, 253 Kilden, 254 Magasinet KBH, 255 Valby (5 items each, screen 1.00/0.40/0.60/1.00). fsb's issue pages didn't render for us: not registered. Trialled 2026-10-07 on the 5 most story-like chunks each: KBH 8 memories, mean 3.9, all old history retold; NABO 1 memory, score 4. Both under the bar. Kilden and Valby untrialled |
| 2000-now | First-party dated posts: noma.dk blog (dozens of fun, spot-tied posts; 403 to plain bots, so only if our crawler gets through as is), Tivoli's history timeline (about 10 since 2000, one spot), cphdistortion.dk/history (about 6; robots.txt has Cloudflare's preamble without a Content-Signal line, re-check before every run) | Registered 2026-10-07 via `webpages:` as 256 Noma (83 items, sitemap), 257 Tivoli, 258 Distortion. Untrialled |
| 2000-now | 1960-now | Exhaustive sweep, 2026-10-07 (8 agents: festivals, one-off events, food, institutions, music/film, blogs, community, open data). First-party history pages, each one spot: K.B. Hallen 261, Copenhagen Pride 263, Kjeld Frandsen's jazz-festival history 265, Jazzhus Montmartre 266, Parken 267, Fiskebaren 268, Eurovision 2001 272. Archives: Københavns Museum's digs and building stories 260, LGBT+ Danmark 264, Rundetårn 269, Zoo 270, Københavns Biblioteker's 281 history articles 271 (mostly pre-1960) | Screened: 1.00 for 261, 263, 265-268, 271; 0.67 for 260, 264, 269, 270; 0 for 272. Rejected: By & Havn 259 (0/6, notices), Olsen-banden Drehorte 262 (text in tables). Trialled 261, 263, 265-268 (first window each): 10 memories, mean 4.3, none 7+, all rejected. 260, 264, 269-272 untrialled. Not yet registered, one page each: Sticks'n'Sushi /dk/en/about/, groed.com/om-grod, Torvehallerne /om-os/arkitekten-bag, fantask.dk/history.asp, ab-b.dk/om-amagerbio-2/, cirkusbygningen.dk/historie/, folketshus.dk/da/historie2/, copenhagenmarathon.dk/om-os/, kbhallen.dk/om/byggeriet/, eurovision.com copenhagen-1964 and -2014. Larger, low hit rate: indenforvoldene.dk (wp-sitemap.xml, one page per address, venue lines in architecture text; source 18's "all rights reserved" predates the without-permission rule), VisitCopenhagen POIs (sitemap.xml `gdk\d+$`, 1,826 pages, 3-5% with an anecdote), Reffen, Culture Box, Kongehuset's begivenheder |
| 1001 fortællinger om Danmark: 305 places in the bbox, about 10-15 really post-2000. The KML dump survives at web.archive.org (`kulturarv.dk/1001fortaellinger/gps/1001.kml`); text rights sit with Slots- og Kulturstyrelsen, which may license partners | Read 2026-10-07: encyclopedic short entries (architecture, founding dates), like Wikipedia. Skip even with permission |
| 2010s-now | Bar stories: VLTV's *De Brune Værtshuse* on YouTube (vltv@hotmail.com, auto-captions); the podcasts *Sidste Omgang* (86 episodes, one bar each, Instagram @sidste.omgang) and *Barvox* (info@barvox.com); the book *Stamsteder* (220 pubs, 2021, print only) | VLTV is registered as source 251: 10 bar videos ingested (two others are gone), with captions waiting on YouTube's IP block. *Sidste Omgang* is on YouTube with Danish auto-captions (2026-10-11): source 311. Barvox is careers, not places |
| 1950-2000 | Local-history society yearbooks: Nørrebro (24 PDFs 2000-23, about 80-100 good), Sydhavnen (26 articles), SLAK for the other 8 | Email drafted in `docs/permission-request.md`, not sent |
| 2000-now | Events at their spots: festivals' own history pages, Wikidata P276+P585 events in the bbox (see step 1) | Open: not searched. Distortion (258) and Tivoli (257) are the first two |
| Trials of the screened text, 2026-10-07 | 2-3 richest items each | Rundetårn 269 active (8 and 6). Københavns Biblioteker 271 stays trial (4 memories, mean 5.5). Rejected: Valby 255 (4.75, all occupation bombings), Kilden 253 (0), Københavns Museum 260 (4, 3), LGBT+ 264 (5), Zoo 270 (0) |
| 1960-now | YouTube sweep, 2026-10-07 (2 agents). Registered as candidates, with 2-4 story videos each ingested and waiting on captions (IP block): Københavns Museum's Nørrebro oral-history films 273, Bøllemis' Olsen-banden locations 274, TV 2 Kosmopol 275 was rejected: robots.txt opts out of AI crawlers by name, Gotha & Petersen walks 192, Paul-Erik Lind's Sydhavnen 277, *Ungeren indefra* 278. Registered, nothing ingested: Rundetaarn 279, Den Kongelige Samling 280. Not registered: Ditlev Tamm's legal history (playlist `PL1alpxNggDi6Erk5DneRYCpVjuVooKUb_`), P3 Essensen's TV-Avisen clips (news), Jewish Copenhagen and Københavnerture (promos), Frederiksberg-erindringer (trailers; the full films are at stadsarkivet.frederiksberg.dk/video, an open lead). No channel found for the Amager, Sundby, Vanløse, Brønshøj, Østerbro or Nordvest societies | Captions came back 2026-10-08 (most clips are under the 20-minute floor: fetch with `MIN_VIDEO_MINUTES=0`). 274 has captions disabled. Trialled 6 videos: 11 memories, 1 good, mean 4.0. Guided walks (192) read as lectures; 273's own people 5 each. Not worth more |
| 1940-45 | Stolpersteine, `stolpersteine:Liste der Stolpersteine im Großraum Kopenhagen` (source 246, 46 addresses) | Ingested, not screened |
| 1860-1919 | Public-domain memoirs: Gottschalksen `archive:engladmusikantsd00gott` (densest), Bang `runeberg:bang/6 København`, Grandjean `archive:spredtemindergen00gran`, Egan `gutenberg:36412 Copenhagen` | Trialled 2026-10-07, 5 windows each: 5 good of 6 memories on the new scale, but only 6 from 20 windows. Active: Grandjean 283 (4 memories, 3 good), Gottschalksen 281 (1, an 8); both fully ingested, 46 windows pending. Rejected: Bang 282 (vol. 6 is touring, 0), Egan 284 (royalty outside the bbox, 1) |
| 1790-1890 | Copenhagen-only memoirs, sweep 2026-10-08 (2 agents: runeberg via its `authors/a.lst`+`t.lst` catalogue and `download.pl?mode=ocrtext&work=<key>`; archive.org with a common-word ratio to tell roman OCR, about 0.3, from Fraktur, about 0.15) | Registered and ingested whole: Bergsøe *De forbistrede drenge* 285, Schorn *Da Voldene stod* 286, Sødring *Erindringer* 287, Zinck *Fra mit Studenter- og Teater-Liv* 288, Foersom's *levnedsskildring* `runeberg:foersom` 289; trialled 5 densest windows each. Bergsøe vol. 2 done with fact sheets 2026-10-10 (290, 15 good); vol. 3 (291) not run: Bergsøe is over the per-author cap and little known. Open leads: Muusmann's three *glade København* (`archive:muusmann-det-glade-kbh-bd-1..3`, venue history by an eyewitness), Lorck `archive:femoghalvfjerdsi00lorc` (death year unchecked), Bauditz `archive:livserindringer00baudgoog` (half Copenhagen), `runeberg:paheiberg` (Bakkehus letters, 40%), `runeberg:billedhugg` (Sinding, 30%). Fraktur OCR, unusable: Rahbek *Erindringer*, Bournonville *Mit Theaterliv*, Davidsen *Fra det gamle Kongens Kjøbenhavn*, Falkenskjold, Martensen, Friis. Not online: Overskou, Hostrup. `runeberg:eberindr` (Bøgh) downloads empty |

**Sweep 2026-10-10: well-known tellers, recent first, and pictures (5 agents).**
- **Video, 1960-now.** No new Københavnerglimt: famous Danes telling their
  spots on video belong to DR and TV 2. Best: Christiania1's
  *christianiahistorie* (source 7, 10 films, manual Danish subtitles, Jon
  Bang Carlsen, Mikael Fock); Roskilde TV's Ragnarock talks (Gasolin's
  Beckerlee, Lecia, Poul Krebs; auto-captions; part Copenhagen); Christiania
  TV (157), Loppen at 50. Low density: Christian Puglisi's channel,
  Munchies *Chef's Night Out*, *Ikke Et Ord Om Politik*, Louisiana Channel.
  Opt out: Copenhagen Sundays' *Mit København* (Squarespace AI block).
  Re-uploads of DR/TV 2 documentaries (DET SKÆVE ARKIV, Nostalgoteket) are
  traps. No captions: Lars H.U.G.'s Vartov talks, Huset-KBH 50 år.
  `yt-dlp -J`/`--list-subs` answered without the IP block.
- **Web text, 1960-now.** Nothing open collects them. The one clean lead at
  volume: Wikipedia event and tour articles by title (Led Zeppelin as "The
  Nobs" at K.B. Hallen 1970, the Little Mermaid's head 1964, the Beatles
  1964), about 30-60 scenes. Ask permission: Euroman/Eurowoman *Mit
  København*, Soundvenue, GAFFA (terms silent or grey). Opt out or blocked:
  cphpost.dk, thelocal.dk, dr.dk (robots), altinget.dk (ai.txt §11b), Vice,
  Kinfolk (terms); 403: zetland.dk, kristeligt-dagblad.dk, movie-locations.com.
  Low: forfatterweb.dk, heartbeats.dk, danskefilm.dk (tables).
- **Old, well-known, free text.** Johanne Luise Heiberg, *Et Liv gjenoplevet*
  (tekster.kb.dk `adl-texts-heibfr05val-root`, `06`, `07`; FRI; clean TEI;
  ~80% Copenhagen; avoid heibfr01-04 and 08, in copyright). Andersen, *Mit
  Livs Eventyr* in Danish to 1867 (`runeberg:miteventyr`). Edmund Gosse,
  *Two Visits to Denmark* 1872/74 (`archive:twovisitstodenma00gossuoft`,
  dehyphenate). Bernhardt, *My Double Life* (`gutenberg:9100`, 1880 visit,
  short). Thinner: Heiberg-Krieger letters, Gade, Drachmann's letters home,
  Ørsted's letters (all tekster.kb.dk, free), Nelson 1801, Wraxall 1774,
  Carr 1805, Marryat 1860 (obscure), Madvig (`gutenberg:44967`, politics).
  Fraktur or in copyright: Steffens, Holberg's Epistler, Baggesen, Ewald,
  Biehl, Wied.
- **Pictures** (picture-first: a great, placeable picture of a moment is a
  memory). Wikimedia Commons is the one usable at volume: `deepcat:` Events
  in Copenhagen 10,318, decades 1960s-90s 701/247/121/57, protests 121;
  about 25% geotagged, most placeable from the caption; licence via
  `extmetadata` as enrich.py reads it. Also on Commons: Frihedsmuseet's 1945
  photos (324, CC BY-SA), Elfelt (1,420, PD). SMK's API: 171 public-domain
  paintings naming their spot (Kongens Nytorv 1807, Brandes at the
  university). kbhbilleder.dk: 50,000+ placed photos, mostly PD, but an AWS
  WAF challenge: ask Stadsarkiv for API access, don't spoof. Not usable: KB
  COP (storied photos "muligvis beskyttet"), Arbejdermuseet (InC), Flickr
  API (terms), Europeana (thin), Polfoto/Ritzau.
  Trialled through `pipeline.pictures` (docs/04 *Road*): only 1940-45 moments
  scored (8 good of 20, now capped as WW2) and Eurovision 2014 (Conchita, 6-7).
  Recent concerts, protests, 1960s/70s street life and events score 2-5: a
  famous name or a crowd at a spot is not a story. Recent pictures: dead end
  unless an iconic moment.

**Sweep 2026-10-10 (evening): recent first-person, after Christiania1 gave
6 of 6 (2 agents).**
- **Christiania1 (7)** has more: 8 *christianiahistorie* films (Louise Gehl,
  Peter Larsen, Henrik Gottlieb, Ole Sol, Mo Elisabeth Hansen, Sanne & Hanne,
  Ida Klemann, Nadia Køvedal Reich), Solvognens aktionsteater 1:2/2:2, Ygge
  *Opvokset i Benenden*, *Stormen på plankeværket*. Christiania is a theme
  (20 good then, cap 30): 5 ingested (4321-4325), waiting on captions.
- **Local TV, first-person but uncaptioned** (we don't transcribe audio):
  Christianshavns Kvarter 155 (647 videos; Stig Weye has auto-captions),
  Frederiksberg Lokal TV 159's *Fortælleklubben* (Diakonissestiftelsen
  p83lsFRs79A captioned, ingested), Kgs. Enghave Lokalhistoriske Arkiv,
  Korridoren's *Sådan var min barndom*. Bispebjerg Lokal-TV 146 is experts
  guiding (Skrammellegepladsen nEmNfJ0lwtE ingested). Frederiksberg-erindringer
  on YouTube is trailers; the films are on stadsarkivet.frederiksberg.dk/video.
- **Text: no open recent first-person collection exists.** Stadsarkiv's ~3,000
  memoirs (1969 and 1995 calls, mostly pre-1950) sit behind an AWS WAF
  challenge on kbharkiv.dk; chrarkiv.dk's 99 *Erindringer* are third-person
  stubs linking there. Blocked or restricted: lgbt.dk (455), Information.dk
  and Jacket2 (ClaudeBot), Sundby and Vanløse archives, slaegtsbibliotek.dk.
  Arbejdermuseet's 1968 activists are audio. Recent material is in print
  (*Bunk, Monk & Funk*, *Stemmer fra 68*). Ask Stadsarkiv (thread already open).

**Sweep 2026-10-11: Wikipedia by title, third round (2 agents, en and da).**
Sources 308 (en), 309 (da), 310 (Bjørn Nørgaard): 40 windows, 23 memories,
15 good, mean 6.3. Danish happening, squat and action articles are the seam
(Allotria 11, Ryesgade, Solvognen, Bøssernes Befrielsesfront 8): 9 good of 15.
English live albums and sports games read as "X played here", 4-5. Title mode
keeps only windows that say "København", so articles naming only Børsen,
Christiania or Parken are skipped silently (Uddrivelsen af templet,
Junkblokaden, Kvindehuset, Danmark-Sverige 2007): use an en article that says
Copenhagen. Open: more da articles in "Uroligheder i København", "Aktivisme i
Danmark", "København i 1900-tallet". Activism and squats are now a theme:
count them against the cap of 30.

**Sweep 2026-10-11: YouTube, podcasts, archive TV (3 agents).**
- **Podcasts:** 255 Apple feeds (27 da/en terms, DR excluded) grepped for
  `<podcast:transcript>`: 11 have it, none Copenhagen history. No show site
  publishes episode text. Route that works: the show's own YouTube with
  auto-captions. Found one: *Sidste Omgang* (Nicolai Banck,
  `UChogeDFZc7wgo3yB2-c_ZYg`, ~52 Copenhagen bars, titles `S\dE\d+: <district>:`;
  the rest is English CEO talk), registered 311. No text and no YouTube copy:
  Bag om København, Københavnerhistorier, Gang i gaden, Under Byen, Byen på
  Bakken, Frederiksberg Stadsarkiv's, Al Magt til Kærligheden (61 Christiania
  portraits, ask Shazia Khan for transcripts). *Byen rundt* (KNR) reads out
  kbharkiv memoirs; københavnLIV's *Byens Lommer* reserves AI in ai.txt.
- **YouTube:** TV Østerbro's archive (Kjeld Lykke, `UCoNKLuIdQrAUFpekqqCrzGQ`,
  99 × 25 min, *Mennesker og By* first-person, mostly debate), registered 312.
  Burhan Bayhan's oral history (`UCPivCzNhMwx_v6jwrirn2-A`, ~10 Copenhagen WW2
  eyewitnesses, first-person, © line only): good, but WW2 is at its cap. No:
  Valby Lokalhistorie (silent rides), Regensianer (one spot), ASSISTENS
  (graves), Copenhagen Walkers, byvandring.nu, True story (crime), Soundvenue
  On The Road, Katrine og Maries Historiepodcast (lectures).
- **Archive TV:** DR (incl. its own P3 Essensen channel) and TV 2 Kosmopol opt
  out (robots ClaudeBot; tv2.dk/ai.txt §11b); DFI and Filmcentralen too.
  Frederiksberg-erindringer: 50+ films of 6-20 min on Dream Broker
  (`fosreg5v`), no subtitles, no opt-out: ask the archive for transcripts.
  Københavns Museum's YouTube is clean but finds, not eyewitnesses.

**Dead ends.** Don't retry these without new evidence.
- **Encyclopedic Wikipedia.** The en category set (venues, riots, crimes,
  clubs) gave 4 good from 67 items (source 245). Danish Wikipedia's 2,783
  geotagged articles read the same, with a rare gem such as Elmegade 23 or
  Cafe Intime.
- **Historisk Atlas** gives title and intro only, with no licence in the
  public JSON. The sabotage set scored 0 good.
- **Records that are labels, not stories:** Europeana's listed buildings (CC0,
  boilerplate), the Kommune's open data (`monumenter` has no text), Wikinews,
  Wikivoyage, OpenHistoricalMap, and one-line Wikidata descriptions.
- **No usable text:** Nationalmuseet, modstand.natmus.dk, Arbejdermuseet and
  the Folklore Archives (no open licence or only on site); Københavns Museum
  podcasts (no transcripts).
- **No Copenhagen memoir as free text:** Nexø's *Erindringer*, Pontoppidan,
  Michaëlis, J.V. Jensen, Wied, Drachmann and Aakjær. Thit Jensen and
  Johannes Jørgensen are still in copyright.
- **District weeklies** (Vesterbro Bladet, Østerbro Avis, Valby Bladet,
  Amager Bladet/amagerliv, City Avisen) are Jysk Fynske Medier.
  lokalavisen.dk redirects to dinavis.dk, which reserves TDM and blocks
  anthropic-ai. They're closed, as the press row says.
- **Collections that turned out to be pre-2010 or not stories:** Københavns
  Museum's and Københavns Biblioteker's podcasts (older history), *Gang i
  gaden* (centuries ago, retold), the corona collections (objects, or for
  researchers only), and Kanal København (shut 2009).
- **Unchecked:** Copenhagen history accounts on Instagram, which search
  doesn't index. Look by hand.
- **Venue "about" pages (2026-10-07)** give 0-2 dated anecdotes each, mostly
  openings and closures: Vega, Mojo, Pumpehuset, Empire, Grand, Bakken,
  Loppen, Stengade, Mikkeller. Ungdomshuset is grim, Pride's site is hacked,
  christiania.org is event notices, Atlas Obscura blocks us (403).
- **Blocked or closed (2026-10-07):** parish papers (Holmens Kirke's
  *Ankerkæden* and the shared parish platform block ClaudeBot), Vanløse's
  *Historisk Set* (needs prior agreement), Nordhavn/Ørestad Avis (paywall),
  Reddit (no AI or commercial use), Netarkivet (researchers only), arkiv.dk
  (private use only, labels), Kunstindeks Danmark (catalogue notes), and
  Ugespejlet (no online archive). Østerbro, Vesterbro, Sundby lokalhistorie
  sell their magazines.
- **Open data with modern text is thin:** the Kommune's WFS (CC BY, about
  230 dry route and renewal texts), iNaturalist CC0/BY (maybe 50-100 nature
  anecdotes), Commons and OSM descriptions (captions).
- **Local-history websites with no stories to read:** chrarkiv.dk (photos),
  Islands Brygge (books for sale), Kend Din By (film), erindringer.dk (dead).
- **Opt out for us (2026-10-07, robots/ai.txt as our UA):** lex.dk and
  danmarkshistorien.dk, DFI and Danmark på film, Copenhagenize, Historypin,
  Bremen Teater, DRS, Culture Trip, Fandom wikis, Resident Advisor, Ved
  Stranden 10, Den Vandrette, Hviids Vinstue, CPH Open, MIX Copenhagen,
  Kulturstationen Vanløse. 403 or a challenge: ft.dk, cph.dk, Visit Carlsberg,
  Atelier September, Amass, Copenhagen Cycle Chic, Spotted by Locals,
  kbhbilleder/kbharkiv (202 empty).
- **Brochures, no story archive (2026-10-07):** almost every restaurant, bar
  and bakery (Geranium, Alchemist, Barr, WarPigs, Mikkeller news, Hart, Lille,
  La Glace, Manfreds, Lagkagehuset...), most festivals (Copenhell, CPH:DOX,
  Opera festival, Strøm, Light Festival, Photo Festival, Fashion Week, Royal
  Run, Kulturnatten: one fact, and its programme is one night's blurbs, 2026-10-09), SMK, Designmuseum, Charlottenborg, Det Kgl.
  Teater, Royal Arena, Bella Center, CopenHill, Cisternerne, kk.dk/nyheder
  (policy), lokaludvalg sites, tour companies' blogs, Rockmuseet, artist sites.
  FCK (match reports) and kongehuset.dk (programmes) are big but dry.
  Personal Copenhagen blogs barely exist; frostfestival.dk, kulturhavn.dk and
  refshaleoen.dk are SEO spam now.
- **Open data, modern (2026-10-07):** nothing. Vores Kunst is JS-only, KØS's
  database is offline, FBB is architecture, OpenAlex has no spot papers,
  Internet Archive CC texts are pre-1940, tidsskrift.dk is academic ©.
  Wikidata: 927 events since 1960 in the bbox, about 15 fun with a real
  article, none geotagged, so `wikipedia:` misses them (a `titles:` mode
  pinned at the P276 venue would catch them).
- **Made or found here, via Wikidata (2026-10-10, source 300 rejected):** in
  the bbox P1071 (location of creation) has 2 items, P189 (location of
  discovery) none. P840 (narrative location) has ~300, all novel and film
  plots: fiction is not something that happened here (1 of 8 screened).
  Paintings that depict a spot (P180) number 132, 14 with an article: a
  picture lead, not text. For works and breakthroughs made at a spot, read
  memoirs, letters and biographies (Ørsted, Andersen, Bohr), where the
  writer says where it happened.
- **Ørsted (2026-10-10).** Not on ADL or Runeberg; his letters are in French
  and German (Harding 1920). Kirstine Meyer's essays (d. 1941, PD) in
  `archive:h.-c.-orsted-naturvidenskabelige-skrifter-vol-i`/`-iii` hold the
  Lion Pharmacy (vol I, part 3, content 4300) and the 1820 discovery at
  Pingels Gaard, Nørregade (vol III, part 1, content 4296): sources 302, 301.
  Screened 0.25 and 0.00, the screen's bias, not the text. Harding's 1920
  *En kort levnedsskildring* names the spot best ("where Københavns Telefonhus
  is now") but his death year is unverified.
- **Restricted:** Street Art Cities (address metadata needs written
  permission), StoryHunt (stories in its paid app), Sydhavnens Historie
  ("reproduction only by prior agreement", 1940s-60s, about 25 good).

**Lessons.**
- A 1.00 screen doesn't predict the walk score. Venue history pages
  (K.B. Hallen, Parken, Montmartre) pass every screen and then read as
  "X played here" lists, scoring 3-6. A famous name at a spot is not yet a story.
- jazz.dk's sitemap URLs loop 301/302 forever; only the
  `/copenhagen-jazz-festival-<year>/nyheder/<slug>/` form answers, and the
  year changes.
- A source's last items can be off-topic: Københavnerliv's backlog ended in
  film chats and festivals. Read the pending titles before trusting `expected`.
- One event page often yields several memories at one spot; prefer festivals
  that moved between venues, since each move is a new spot.
- Ingest everything when a source is small, and trial the richest items, not
  the first five.

## 1. Research candidates (free)

Fan out parallel agents, one per kind, on primary sources only: the feed
itself, the catalogue page, the ToS page. Not listicles. Ask each for exact
locators and evidence.

**Genre predicts yield better than anything else** (docs/04, *Yield by genre*).
Hunt in this order, and register an institution's history of itself or an
encyclopedia only when the page shows a named person's anecdote on its spot:

Memoirs and channels were scored on the looser pre-10-05 scale, so trust the
order, not the gap. Within a genre, prefer a teller a walker may have heard of,
and many tellers over one: make-memories caps an author at 15 good memories
and a theme or era at 30 (WW2 is full), recent first (docs/10, *No teller or
theme dominates*).

| Genre | Good (6+) per memory, 2026-10-07 |
|---|---|
| First-person memoir of a city life | ~80% |
| People telling their own places (channels) | ~58% |
| Plaques, researched | high, few |
| Local-history society, story pages | 25-75% |
| An institution about itself (venue, festival, restaurant) | ~10% |
| Encyclopedic (Wikipedia) | 14% |

Kinds worth a fan-out beyond the table's archives, because a walker is glad to
know *this is where it happens*:

- **YouTube, every time.** The two best sources are channels (Københavnerglimt,
  Københavnerliv). Always fan out one agent on channels: local TV, local-history
  societies, storytellers, music and nightlife series. Skip ones already in
  `pipeline.sources list`; captions come from `pipeline.transcripts`, never
  through a proxy.
- **Recurring events at a fixed spot.** Festivals and their grounds:
  Copenhell (Refshaleøen), Distortion, Copenhagen Jazz Festival, CPH:PIX,
  CPH:DOX, Kulturnatten, Copenhagen Pride, Vinterjazz, Strøm, Copenhagen Light
  Festival, Copenhagen Cooking, the Marathon, Ironman, Royal Run, Tivoli's
  seasons. Good when its own history page names years and spots.
- **One-off events at a spot.** Eurovision 2014 (B&W Hallerne), the Tour de
  France Grand Départ 2022, COP15 (Bella Center), concerts that made history,
  royal events. Start from Wikidata events with P276 (location) and P585
  (date) in the bbox, keep the fun ones (not crimes or disasters), then read
  the event's own page for the story.
- **Venues and institutions with dated posts.** Restaurants, clubs, theatres,
  museums, harbour baths. "About" pages give 0-2 anecdotes; a blog or news
  archive read through its sitemap gives dozens (Noma, 2026-10-07).

| Kind | Plug-in (`crawler/`) | Locator (`<key>:<query>`) | What makes one good |
|---|---|---|---|
| Plaques, memorials | `plaques` | `plaques:<s,w,n,e>` | Already names its spot; exact pin |
| Film and TV shot here | `filming` | `filming:<s,w,n,e>` | Wikidata P915 to a spot, not a city |
| Wikipedia places | `wikipedia` | `wikipedia:<lang> <lat>,<lng> <metres>`, `wikipedia:<lang> category:<A>|<B>` or `wikipedia:<lang> titles:<A>|<B>` (an event no map pins: only its Copenhagen windows) | History sections with incidents; categories beat a radius, which drags in stubs and the citywide article |
| Stolpersteine | `stolpersteine` | `stolpersteine:<de.wikipedia list title>` | One record per door; the geocoder places the address |
| Back issues as PDFs | `pdfs` | `pdfs:<index page url> [<from year>] [<via regex>]` | A paper or society that links its issues; read for stories, not ads and listings |
| A site's own pages | `webpages` | `webpages:<page url>` or `webpages:<sitemap.xml> [<url regex>]` | First-party dated posts with spot-tied anecdotes |
| Events and festivals | `webpages` | `webpages:<history page>` or `webpages:<sitemap.xml> [<url regex>]` | Names its spot and years: firsts, moves, records, famous nights |
| Press feed | `press` | `press:<feed url>` | Only with the outlet's agreement: every Copenhagen outlet reserves TDM (§11b) |
| Podcast feed | `podcast` | `podcast:<feed url>` | Items carry `<podcast:transcript>` (no Copenhagen show did, 2026-10-04); no audio is transcribed |
| Public-domain book | `gutenberg`, `runeberg` | `gutenberg:<id> <word>`, `runeberg:<key> <word>` | Memoir of a city life, author dead 70+ years |
| Internet Archive book | `archive` | `archive:<item id> <word>` | A walk book by street or house, author dead 70+ years; roman type, not Fraktur |
| Old newspapers | `kb-aviser` | `kb-aviser:<query>` | Over 140 years old |
| Historisk Atlas | `historisk-atlas` | `historisk-atlas:<title word>` | CC or PD licence only |
| YouTube channel | `pipeline.sources discover` | channel URL | Only with written permission (`docs/permission-request.md`) |

A kind with no plug-in is one file in `crawler/` with a class that fits
`Source`, plus one line in `crawler.sources.SOURCES`, and an offline parser
test in `tests/test_crawler_sources.py`. A source with its own coordinates puts
them in the record's text ("X places this at lat, lng"), as `historisk_atlas`
does, so the pin can use them.

## 2. Legal check (free)

Find the kind's row in the legal table. If there is none, write it **before**
ingesting: the licence or ToS clause, quoted with its URL, and what it takes.
Hard stops: no reuse or TDM opt-out in the ToS, non-commercial only, a
private person's health, politics or crime (GDPR Art 9), and anything needing
a login, a paywall bypass or a proxy. Press and podcast text is forgotten once
extracted (`pipeline.transcripts.forget`); we keep facts in our own words and
a link.

A first-party page with no licence: fetch robots.txt *as us* (Python's
RobotFileParser.read() fetches as Python-urllib, which some sites refuse;
`crawler.webpages.robots` doesn't), ai.txt, `/.well-known/tdmrep.json`,
Cloudflare's `Content-Signal:` line, and the ToS. A 403 or a JavaScript
challenge to our user agent is a block: don't go around it.

## 3. Register and fetch a sample (free)

```bash
venv/bin/python -m pipeline.sources add text '<key>:<query>' "<credit name>" --licence "<licence>" --note "<why>"
venv/bin/python -m pipeline.ingest --source <key> --query '<query>' --limit 5 --bbox 55.60,12.45,55.74,12.66
```

Read two or three ingested texts yourself (`transcripts.full_text`). If they
don't name places a walker can stand on, `set <id> rejected --note` and stop.

## 4. Screen (a few cents, Haiku)

```bash
venv/bin/python -m pipeline.sources screen <id> --sample 3
```

Under about 0.3 pass rate: reject with a note.

## 5. Trial (**bills**: Sonnet extraction, check, judge, enrichment)

```bash
venv/bin/python -m pipeline.sources set <id> trial
# A book: scene-first with fact sheets, at half price (docs/10, *Scene-first is the book path*)
venv/bin/python -m pipeline.batch --content <content_id>... --run
# Text windows (Wikipedia, PDFs, pages): the same, with sheets
venv/bin/python -m pipeline.batch --content <content_id>... --scenes --run
# Anything else: one item; never pipeline.extract
venv/bin/python -m pipeline.enqueue --video <content_id>
venv/bin/python -m pipeline.worker --burst
```

Auto mode refuses billed runs: hand them to the founder as `!` commands.

Before enqueueing, check that it isn't already queued or extracted
(`content.memories_extracted`, the queue). After it runs, run the duplicate
summary query, then read every new memory and its `enrichment`.

## 6. Decide and record

- Yield: memories per item, mean `walk_score`, how many survived the check.
  Keep a source whose memories average 6 or more and that names spots.
- `set <id> active` or `rejected`, with `--note` saying why.
- Log the numbers in `docs/04-extract.md` or `docs/02-ingest.md`, and the
  legal row in `docs/10-decisions.md`.

## Don't

- Run `python -m pipeline.extract`: it bills every pending item.
- Ingest a whole feed or the 4,000-article Wikipedia set before a 5-item trial.
- Add a source whose stories are only *set* in a place: the judge drops them,
  and you pay for that.
