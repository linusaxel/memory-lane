# Research: has anyone built this before?

2026-10-11. The question: has anyone built a daily planned walk past real,
place-tied stories that open only when you stand on the spot? Four passes:
stand-here story apps, walk planners, automated place-story mining, and
postmortems. Most links come from research agents. Three were checked by hand:
Spatial Memory, Strolly and LitLong. Anything marked *(unverified)* could not
be confirmed.

**Answer: nobody has built all three parts together.** Those parts are one walk
planned for you each day, first-hand stories pinned to their spot, and a hard
gate. Several products have one or two of them, and most are dead.

## The closest attempts

- **Spatial Memory** (KevinTen, indie, on dev.to in June): memories pinned to
  GPS coordinates that "unlock only when you're physically there". This is
  almost exactly our gate. After launching on HN, Reddit and Discord he had
  "17 people" signed up, "23 pins" and "~3 (me + two friends)" daily users. He
  wrote that "the novelty of location-locked content wears off after your first
  pin." He measured GPS at 3-5 m in the open and "off by 20-30 meters" in urban
  canyons, so he added a "force unlock" button
  ([dev.to](https://dev.to/kevinten10/building-spatial-memory-part-4-the-brutal-reality-of-launching-a-location-based-side-project-4n2)).
- **Strolly** (Nil Coalescing, since 2024-07-01): up to three random loop walks
  a day from your door, with no stories. Strolly+ costs $2.99 a week or $24.99
  a year. It has 19 ratings
  ([App Store](https://apps.apple.com/us/app/strolly-generated-daily-walks/id6480581550)).
  It is our planner without the memories, and nobody uses it.
- **Rider Spoke** (Blast Theory and Nottingham's Mixed Reality Lab, 2007 and
  still touring). Strangers' recordings are played only "to you, alone, in the
  place where they were recorded": 15,000 recordings across 20+ cities. It is
  the strictest gate of any of these, but it lives as a ticketed art event,
  not a habit
  ([Blast Theory](https://www.blasttheory.co.uk/projects/rider-spoke/)).
- **Niantic Field Trip** (2012-19): curated cards pushed as you walked past,
  from Atlas Obscura and about 130-200 other publishers (sources disagree).
  About 1M downloads. It had no gate, no planned route and no revenue, and was
  retired so Niantic could "prioritize" AR. Its places became Pokémon Go stops
  ([Engadget](https://www.engadget.com/2019-07-13-niantic-to-shut-down-field-trip.html)).
- **Detour** (Andrew Mason, 2015-18): audio walks synced to GPS. Mason: "People
  who used Detour loved it, but after 4 years of working on it we never got
  widespread traction." A tour took 3-4 months to make. Bose bought the content
  and then shelved it, and Detour's in-house editing tool became Descript
  ([TechCrunch](https://techcrunch.com/2018/04/24/bose-acquires-andrew-masons-walking-tour-startup-detour),
  [TechCrunch 2015](https://techcrunch.com/2015/06/11/detour-andrew-masons-audio-tour-app-goes-global-and-expands-to-6-more-cities)).
- **Palimpsest / LitLong** (University of Edinburgh, St Andrews and EDINA;
  AHRC-funded, 2013-17). The closest prior work to our pipeline. It
  text-mined digitised books for passages set in Edinburgh and placed about
  47,000 of them, from about 550 books, at 1,600+ streets and buildings using
  an adapted Edinburgh Geoparser. It had a LitLong:Edinburgh iOS app with a
  "near me" mode. The parsing was not fully accurate at building level, so
  users could report wrong locations. The content was fiction, not first-hand
  stories, and nothing was gated
  ([REF 2021 output](https://results2021.ref.ac.uk/outputs/555e8146-7b0b-4409-ac65-af58a15f3c58),
  [Springer](https://link.springer.com/article/10.1007/s10579-019-09443-x),
  [Stirling preprint](https://www.storre.stir.ac.uk/bitstream/1893/28517/1/DSH_article_finalrevisions.pdf),
  [Jane Alexander](https://janealexander.net/2015/03/31/mapping-the-city/)).
- **Pokémon Go Routes** (2023): user-made walks between stops, reviewed before
  going live, with rewards. A planned walk at scale, but the stops carry no
  stories
  ([Pocket Gamer](https://www.pocketgamer.com/pokemon-go/routes/)).
- **StoryHunt** (Copenhagen, 2018): story walks with GPS guidance. 57 stories
  for 39 DKK, plus free local walks made with the city's visitor service. It
  has no hard gate and no daily walk. It is the local competitor, or a partner
  ([storyhunt.io](https://www.storyhunt.io/de/about),
  [The Hub](https://thehub.io/startups/storyhunt)).
  Also in Copenhagen: *Hidden Copenhagen*, a 7-site trail around a 1673 murder
  ([KU](https://teol.ku.dk/nyheder/nyheder-2023/immersive-app-brings-the-hidden-histories-of-copenhagen-to-life)).

## Older notes and stories left at places (mostly dead)

| Project | Years | Why it stopped |
|---|---|---|
| [murmur] (Toronto, then 25+ cities) | 2003- | Phone numbers on signs. A soft gate, since you can call from anywhere. Dormant ([TPL](https://blogs.tpl.ca/lillian-h-smith/2010/10/hear-you-are-listen-to-neighbourhood-stories-at-murmur-toronto/)) |
| Yellow Arrow | 2004-06 | Art project ran its course: 7,535 stickers, 467 cities ([MIT Docubase](https://docubase.mit.edu/lab/case-studies/yellow-arrow-case-study)) |
| Riot! 1831 (HP Labs, Bristol) | 2004, 2018 | An audio play heard only in Queen Square. A one-off ([Calvium](https://calvium.com/riot-1831-back-whats-new/)) |
| Broadcastr | 2011-12 | User audio on a map you could browse from anywhere. Pivoted to news ([VentureBeat](https://venturebeat.com/technology/location-based-storytelling-site-broadcastr-opens-to-the-public), [TechCrunch](https://techcrunch.com/2012/11/28/spun-app-launch/)) |
| Woices | 2007-~12 | Map browsing, empty spots *(shutdown unverified)* ([TNW](https://thenextweb.com/news/woices-audio-augmented-reality-iphone)) |
| Wallit | 2012 | You could post only when there but read from anywhere. Walls nobody visited died ([Vator](https://vator.tv/2012-03-06-wallit-app-leave-your-virtual-mark-on-historical-sites/)) |
| Hackney Hear | 2012 | Gated oral history in one park. Never grew past it ([Londonist](https://londonist.com/2012/03/app-review-hackney-hear)) |
| Sekai Camera, Layar | 2009-14 | Spam, the end of the AR hype, no reason to return ([The Bridge](https://thebridge.jp/en/tag/sekai-camera), [Silicon Canals](https://siliconcanals.com/layar-founders-dream-to-redeem-companys-property-from-blippar-crushed/)) |
| GeoNotes (SICS) | 2001 | Too many notes reaching people. A research trial ([ERCIM](https://ercim.eu/publication/Ercim_News/enw47/persson.html)) |
| Map Buddy | 2024 | 100+ users, 2 paying ([retrospective](https://thomashunter.name/posts/2024-08-19-map-buddy-product-retrospective-video)) |

Still alive but different: Echoes.xyz (geofenced audio for artists,
[docs](https://docs.echoes.xyz/docs/creator/intro)), and Museum of London's
Streetmuseum (old photos at the spot, a picture-first precedent, claimed 160k
downloads, [D&AD](https://www.dandad.org/work/d-ad-awards-archive/streetmuseum)).

## Mining place stories automatically

- **Extracting venues from video is solved; extracting stories is not.**
  Mindtrip's "Start Anywhere" (2024) and its copycats turn a YouTube or TikTok
  video into a list of places. Nobody extracts what happened at a spot, told
  by someone who was there
  ([TechCrunch](https://techcrunch.com/2024/07/31/travel-startup-mindtrips-new-feature-lets-you-build-an-itinerary-from-a-screenshot-youtube-or-tiktok-video)).
- **LLM coordinates are unreliable.** GPT-3 named places correctly but gave
  coordinates 500+ miles off ([arXiv](https://arxiv.org/pdf/2304.06798)).
  GDELT found LLMs invent place mentions and give different results each run
  ([GDELT](https://blog.gdeltproject.org/?p=21273)). Fine-tuned models choosing
  from gazetteer candidates do well, about 0.93
  ([CEUR](https://ceur-ws.org/Vol-3969/paper6.pdf)). In Sep 2025 a chatbot
  invented Peru's "Sacred Canyon of Humantay", and tourists went looking for it
  ([OECD AI](https://oecd.ai/en/incidents/2025-09-29-8b4f)).
- **Renamed streets break modern geocoders.** OldNYC needed a custom grid
  geocoder for streets that were renamed or gone
  ([danvk.org](https://www.danvk.org/2016/01/19/oldnyc-update.html)).
- **Copenhagen already has coordinates placed by people.** The public places
  about 54k kbhbilleder.dk photos by hand
  ([TV2 Kosmopol](https://www.tv2kosmopol.dk/kobenhavn/50000-historiske-fotos-museum-mangler-din-hjaelp)),
  and Danmark set fra luften's locations were also crowdsourced
  ([KB](https://www.kb.dk/danmarksetfraluften/english)).
- **Paid editors don't scale.** Atlas Obscura edits every submission, and its
  backlog runs to thousands. Autio paid writers for 20k+ stories and raised
  $5.6M
  ([TechCrunch](https://techcrunch.com/2023/03/29/kevin-costners-location-based-audio-storytelling-app-autio-raises-5-6m)).
- **AI narration is a commodity.** Google Arts & Culture's Talking Tours are
  free ([TechRadar](https://www.techradar.com/computing/websites-apps/googles-new-ai-generated-talking-tours-sound-like-the-future-of-free-guided-city-walks)),
  and VoiceMap now sells "human, not AI"
  ([VoiceMap](https://blog.voicemap.me/2026/07/voicemap-publishers-town-hall-webinar-highlights-and-recording/)).
- **Rights.** YouTube's terms bar scraping and reproduction
  ([terms](https://www.youtube.com/terms)). Under the Danish text-and-data-mining
  exception (Copyright Act §11b, opt-out), DR and JP/Politikens Hus have opted
  out. A May 2026 BoligPortal v ReData ruling on machine-readable opt-outs is
  *(unverified)*
  ([IRIS Merlin](https://merlin.obs.coe.int/article/10505)).

## What the survivors did

- **Geocaching**: a hard "be there" rule for 20+ years. The community places
  the content. Premium is $39.99 a year
  ([blog](https://www.geocaching.com/blog/?p=115074)).
- **Pikmin Bloom**: pays you back for the walk itself. $139M lifetime, $38.1M
  in 2025, up every year
  ([PocketGamer.biz](https://www.pocketgamer.biz/pikmin-bloom-hits-100m-after-four-years-as-2025-becomes-its-best-year-yet)).
- **Pokémon Go**: about 20M weekly players in 2025, about half of them every
  day ([PocketGamer.biz](https://www.pocketgamer.biz/pokmon-go-has-20m-weekly-active-players-nearly-nine-years-after-its-global-launch)).
- **VoiceMap**: 800+ publishers, sold through Viator and GetYourGuide. Tours of
  about an hour sell best
  ([VoiceMap](https://blog.voicemap.me/2024/03/voicemap-audiotours-ten-years-old-publishing-plans/)).
- **Sweatcoin** and **aruku&**: paying raises a daily cap. This is the closest
  precedent for "pay for more walks a day"
  ([aruku& Premium](https://onecompath.com/wp-content/uploads/2025/12/FIX【20251202NR】arukuプレミアムサブスク機能開始.pdf)).
- **Willingness to pay**: RevenueCat 2024 put Travel trial-to-paid conversion at
  54.3%, the highest of any category
  ([Gigazine](https://gigazine.net/gsc_news/en/20240313-apps-subscription-stats)).

## Why they died, and what it means here

1. **No daily loop.** Walks were occasional outings (Detour, Field Trip). One
   walk a day is the loop none of them had. Whether it holds without a game
   layer is the biggest open risk, now that the Locket-keeper was reverted.
2. **Content was too thin or too costly.** Made by hand, it was slow (Detour,
   Autio). Posted by strangers, it was empty or spam (Woices, Broadcastr,
   Sekai Camera). The pipeline is the way out, but only if every story clears
   "glad to know".
3. **Soft gates leaked** ([murmur], Broadcastr, Wallit), and the magic went
   with them. Keep the gate hard.
4. **The novelty of a locked story fades** (Spatial Memory, Randonautica's 2020
   TikTok spike, [Webworm](https://www.webworm.co/randonautica/)).
5. **GPS error is about the size of the gate** (20-30 m in urban canyons).
   That is our risk too, already accepted in docs/10, *20 m*.
6. **Getting found.** Detour ranked 400-700 in Travel even with a famous
   founder. The survivors had a channel (VoiceMap's marketplaces) or a game.
7. **Strangers' posts.** Yik Yak died of harassment
   ([Wikipedia](https://en.wikipedia.org/wiki/Yik_Yak)).

Concrete checks for the pipeline: confirm the place string appears in the
source text before geocoding it, keep an alias table for old street names,
reuse coordinates people have already placed, and let walkers report a wrong
spot (as LitLong and Smapshot did).

Nobody has published a threshold for how many stories per km a walk needs, so
our one per km is untested.
