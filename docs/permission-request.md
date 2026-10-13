# Permission requests

Every source we may only use with a yes, and the email that asks for it. Send
from the founder's own address, one at a time. When a reply comes, file its
date and wording on the `sources` row (`pipeline.sources set <id> ... --note`)
and update the tracker below.

docs/10-decisions.md, *The sources' legal footing* and *Recent sources without
permission*, says why each needs asking: a channel always does; a site whose
terms say "non-commercial", "after agreement" or "no digital copies" does; a
block (WAF, robots, ai.txt) is never gone around.

## Tracker

Ordered by what a yes would add to the goal's empty cells (make-memories
skill, step 0). "Cells" are the 1 km cells within 4 km of Rådhuspladsen.

| # | Who | What a yes unlocks | Cells | Contact | Status |
|---|---|---|---|---|---|
| 1 | Arbejdermuseet, *Humlen ved Carlsberg* | 195 posts of brewery workers telling their own buildings, 1950s-2008 | Carlsberg (empty) | find on humlenvedcarlsberg.dk / arbejdermuseet.dk | Not sent |
| 2 | Lokalhistorisk Selskab for Brønshøj, Husum og Utterslev | *Nyt fra Lokalhistorien* story pages; *Min barndom på Bispebjerg*, *Erindringssamtaler fra Nordvest-Bispebjerg* | Nordvest, Bispebjerg (empty) | info.lhsbhu@gmail.com | Not sent |
| 3 | Københavns Stadsarkiv, memoirs | ~3,300 memoirs from the 1969 and 1995 calls, behind kbharkiv.dk's WAF | every district | the open thread (see §3) | Thread open, not asked for memoirs |
| 4 | Sydhavnens Lokalhistoriske Arkiv | 26 *erindringsartikler*, 1940s-60s | Sydhavn (empty) | sydhavnen@outlook.dk | Not sent |
| 5 | Refshaleøen TV, Kim Bargsteen | *Refshaleøens historie* (2022) with a former B&W worker; uncaptioned, so a transcript or subtitles | Refshaleøen, Holmen (empty) | YouTube `UC-z4gV_vcO2_rrJIpddwvCg`, About page | Not sent |
| 6 | Frederiksberg Stadsarkiv, *Frederiksberg-erindringer* | 50+ first-person films of 6-20 min on Dream Broker, no subtitles | west Frederiksberg (empty) | find on stadsarkivet.frederiksberg.dk | Not sent |
| 7 | Bryggebladet | the 2003-06 HTML archive's resident portraits, and a yes for source 247 already in use | Islands Brygge (empty) | redaktion@bryggebladet.dk | Not sent |
| 8 | Nørrebro Lokalhistoriske Forening | 24 yearbooks 2000-23 (source 248 in use) | Nørrebro, Nordvest edge | info@noerrebrolokalhistorie.dk | Not sent |
| 9 | SLAK | an introduction to the Østerbro, Valby and Vesterbro societies | outer districts | `slak.dk/kontakt` | Not sent |
| 10 | Københavnerliv, Københavnerglimt | the YouTube corpus, 107 visible memories (sources in use) | Indre By, Vesterbro | the channels | Check: not recorded as sent |
| 11 | kbhbilleder (Stadsarkivet) | ~5,000 free, placed photos through the APACS API | every district | kbhbilleder@kff.kk.dk | Not sent |
| 12 | Historisk Atlas | the API's per-story licence, so CC stories can be used | every district | it@historiskatlas.dk | Not sent |

Later, if the above come back yes: Kenneth A. Balfelt's Enghave Plads films
(uncaptioned), Bispebjerg and Frederiksberg Hospital's *Stemmer fra Bjerget*
(YouTube `UCzkyW2Y9sGT4eC1S4gMkAgg`), Marinehistorisk Selskab, DieselHouse
(B&W), Shazia Khan's *Al Magt til Kærligheden* (Christiania).

## What every email promises

Each has to be true before we send:

- **Our own words.** A short text about one episode, never a quote longer than
  a line, an excerpt or a clip.
- **They are the source**, by name, with a link back to them on every memory.
- **The text is forgotten once extracted** (`pipeline.transcripts.forget`;
  for videos, `python -m pipeline.transcripts --forget-extracted` for the
  backlog before sending).
- **A stop is honoured within a day**, for one story or the whole source.
- **No proxy** for a permitted channel: drop `WEBSHARE_PROXY_*` for it.
- **Private names**: a story about a private person who may be alive doesn't
  name them without asking.

The price line is *A free walk a week* (docs/10): "Appen er gratis med én
gåtur om ugen; et abonnement giver en hver dag." Change it in every email if
that decision changes.

---

## 1. Arbejdermuseet: Humlen ved Carlsberg

The richest find of the 2026-10-12 sweep: workers telling where things
happened at the brewery ("over på værtshuset 'Als', som lå lige over for
porten"), the 1985 strike, the last can line. The site says "må kun citeres
i ikke-kommerciel sammenhæng", so it is closed without a yes. The Carlsberg
cell has no good memory.

**Emne:** Må vi fortælle bryggeriarbejdernes historier på stedet i Carlsberg Byen?

Hej [navn],

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér.

*Humlen ved Carlsberg* er fuld af den slags: [ét konkret eksempel, fx
værtshuset Als over for porten, hvor arbejderne gik over efter
portreglerne]. I dag er Carlsberg Byen et kvarter mange går igennem uden
at vide, hvad der foregik i bygningerne. Jeg vil gerne spørge om lov til
at bruge fortællingerne sådan:

- **Vi skriver selv en kort tekst** om én episode, med vores egne ord,
  aldrig et uddrag af indlægget.
- **I står som kilde** med Arbejdermuseets og *Humlen ved Carlsberg*s navn,
  og et link til indlægget hos jer.
- **Vi gemmer ikke jeres tekster.** Vi læser hvert indlæg én gang for at
  finde stedet, og sletter teksten bagefter.
- **Navne**: fortæller en tidligere medarbejder om en kollega, nævner vi
  ikke kollegaens navn uden at have spurgt.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag. Jeg
ved, at I har skrevet "ikke-kommerciel sammenhæng", og derfor spørger jeg
først.

Er det i orden med jer? Og skal jeres navn stå på en bestemt måde?

Venlig hilsen
[navn]
[telefon]

---

## 2. Lokalhistorisk Selskab for Brønshøj, Husum og Utterslev

`lokalhistorie-bhu.dk` (use http: the https certificate fails). Eight issues
of *Nyt fra Lokalhistorien* as HTML, by named members, 1900-1970: Emdrupborg
as a film studio 1911-17, Bispebjerg Kirkegård, Nørrebro Station. Every issue
says "Eftertryk er tilladt efter aftale". Their print books on Bispebjerg and
Nordvest are what the open web lacks.

**Emne:** Må vi fortælle historierne fra Nyt fra Lokalhistorien på stedet?

Hej,

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér.

Jeres blad er fuldt af den slags: [ét konkret eksempel, fx Emdrupborgs park,
hvor Filmfabrikken Skandinavien optog film 1911-17]. Nordvest og Bispebjerg
er netop de kvarterer, hvor vi har færrest historier. Jeg vil gerne spørge
om lov til at bruge jeres artikler sådan:

- **Vi skriver selv en kort tekst** om én episode, med vores egne ord,
  aldrig et uddrag af artiklen.
- **I står som kilde** med selskabets navn, og et link til bladet og til
  hvordan man bliver medlem.
- **Vi gemmer ikke jeres tekster.** Vi læser hver artikel én gang for at
  finde stederne, og sletter teksten bagefter.
- **Private navne**: handler en historie om en privatperson, der kan være i
  live, nævner vi ikke navnet uden at have spurgt.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.

Har I også *Min barndom på Bispebjerg* eller *Erindringssamtaler fra
Nordvest-Bispebjerg* som tekst, vil jeg gerne spørge om de samme vilkår for
dem.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Er det i orden med jer? Og skal jeres navn stå på en bestemt måde?

Venlig hilsen
[navn]
[telefon]

---

## 3. Københavns Stadsarkiv: the memoirs

About 3,300 memoirs from the archive's 1969 and 1995 calls, mostly before
1950, read on kbharkiv.dk behind an AWS WAF challenge: never scraped. A
thread with Stadsarkivet is already open (find-sources skill); ask in it,
and combine with §11 (kbhbilleder) if that has not gone yet.

**Emne:** Erindringerne fra 1969 og 1995 i en gåtursapp om København

Hej [navn],

[En linje om tråden I allerede har.]

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér. Jeres indsamlede erindringer er den bedste
kilde, der findes, til hvordan byen var at leve i, gade for gade.

Kan vi få adgang til erindringerne som tekst, gennem et API eller et
udtræk, i stedet for at belaste kbharkiv.dk? Vi vil bruge dem sådan:

- **Vi skriver selv en kort tekst** om én episode, med vores egne ord,
  aldrig et uddrag af erindringen.
- **I står som kilde** med Stadsarkivets navn og et link til erindringen
  hos jer.
- **Private navne**: vi nævner ikke privatpersoner ved navn, kun stedet og
  det der skete.
- **Vi gemmer ikke teksterne.** Vi læser hver erindring én gang for at finde
  stederne, og sletter teksten bagefter.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.

Gælder der særlige vilkår for erindringer, hvor skribenten stadig kan være
i live, vil jeg gerne kende dem.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Venlig hilsen
[navn]
[telefon]

---

## 4. Sydhavnens Lokalhistoriske Arkiv

sydhavnen@outlook.dk. 26 *erindringsartikler*, 1940s-60s, about 25 good;
"reproduction only by prior agreement". The two Sydhavn cells are empty.
Use the local-history society email (§8) with this example: [én artikel fra
sydhavnenshistorie.dk, med sted].

---

## 5. Refshaleøen TV, Kim Bargsteen

YouTube `UC-z4gV_vcO2_rrJIpddwvCg`, *Refshaleøens historie* (2022): Kim
Bargsteen, who worked at Burmeister & Wain, tells the island. No captions,
and we don't transcribe audio, so the ask is a transcript or subtitles, and
permission. The east harbour column has almost nothing open.

**Emne:** Må vi fortælle Refshaleøens historie på stedet?

Hej [navn],

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér.

Jeres film *Refshaleøens historie* med Kim Bargsteen er præcis den slags:
[ét konkret øjeblik fra filmen, med sted]. Om Refshaleøen og B&W findes der
næsten intet, der er fortalt af nogen, der var der. Jeg vil gerne spørge om
to ting:

1. Må vi bruge filmen sådan som beskrevet herunder?
2. Har I en tekst eller undertekster til den? Vi lytter ikke selv lyd af,
   så uden tekst kan vi ikke finde stederne.

- **Vi skriver selv en kort tekst** om én episode, med vores egne ord,
  aldrig et klip eller en afskrift.
- **I står som kilde** med jeres navn og Kim Bargsteens, og et link der
  åbner filmen på YouTube præcis hvor historien bliver fortalt.
- **Vi gemmer ikke teksten.** Vi læser den én gang for at finde stederne,
  og sletter den bagefter.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Er det i orden med jer, og med Kim?

Venlig hilsen
[navn]
[telefon]

---

## 6. Frederiksberg Stadsarkiv: Frederiksberg-erindringer

50+ films of 6-20 min on Dream Broker (`fosreg5v`), people telling their own
Frederiksberg. No subtitles and no opt-out; YouTube has only trailers. The
ask is transcripts and permission. West Frederiksberg (Grøndal, Fuglebakken,
Flintholm) has no open source at all.

**Emne:** Frederiksberg-erindringerne i en gåtursapp: må vi, og findes der tekst?

Hej [navn],

Jeg bygger Memory Lane, en app der planlægger gåture i København og på
Frederiksberg forbi steder hvor noget er sket. Når man står på stedet,
åbner en kort historie om hvad der skete netop dér.

*Frederiksberg-erindringer* er præcis den slags: [én konkret erindring fra
en film, med sted]. Jeg vil gerne spørge om to ting:

1. Må vi bruge filmene sådan som beskrevet herunder?
2. Findes der udskrifter eller undertekster til dem? Vi lytter ikke selv lyd
   af, så uden tekst kan vi ikke finde stederne.

- **Vi skriver selv en kort tekst** om én episode, med vores egne ord,
  aldrig et klip eller en afskrift.
- **I står som kilde** med Stadsarkivets navn og fortællerens, og et link
  til filmen hos jer.
- **Private navne**: nævner en fortæller andre privatpersoner, nævner vi dem
  ikke.
- **Vi gemmer ikke teksten.** Vi læser den én gang for at finde stederne,
  og sletter den bagefter.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Venlig hilsen
[navn]
[telefon]

---

## 7. Bryggebladet

redaktion@bryggebladet.dk. Source 247 (issues 2019-26) is used today under
*Recent sources without permission*, but `/ombryggebladet/ophavsret/` says
"Det er ikke tilladt at tage kopi i elektronisk/digital form… Al yderligere
anvendelse kræver tilladelse". A yes turns that risk into a credit, and opens
the 2003-06 HTML archive (about 540 articles, resident portraits such as the
centenarians of Egilsgade 59).

**Emne:** Må vi fortælle Bryggens historier fra Bryggebladet på stedet?

Hej,

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér.

Bryggebladet har den slags historier om Islands Brygge, som ingen andre har:
[ét konkret eksempel, fx de to hundredårige, der flyttede til Egilsgade 59
i 1908]. Jeg har læst jeres side om ophavsret, og derfor spørger jeg om lov
til at bruge artiklerne sådan:

- **Vi skriver selv en kort tekst** om én episode, med vores egne ord,
  aldrig et uddrag af artiklen.
- **I står som kilde** som "Bryggebladet" med dato, som I beder om, og et
  link til artiklen.
- **Vi gemmer ikke jeres tekster.** Vi læser hver artikel én gang for at
  finde stederne, og sletter teksten bagefter.
- **Private navne**: handler en historie om en privatperson, der kan være i
  live, nævner vi ikke navnet uden at have spurgt.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 8-9. Local-history societies: Nørrebro, SLAK (and §4's wording)

Their first-hand stories from living memory are what the free sources lack
(research 2026-10-05). Ask in this order, one at a time:

1. Nørrebro Lokalhistoriske Forening, info@noerrebrolokalhistorie.dk: 24
   yearbooks 2000-2023 as text PDFs at `noerrebrolokalhistorie.dk/aarsskrifter/`
2. Sydhavnens Lokalhistoriske Arkiv, sydhavnen@outlook.dk: 26 "erindringsartikler"
3. SLAK, `slak.dk/kontakt`: the umbrella for the city's ten societies, for an
   introduction to Østerbro, Valby and Vesterbro

**Emne:** Må vi fortælle historierne fra jeres årsskrifter på stedet?

Hej [navn],

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér.

Jeres årsskrifter er fulde af den slags: [ét konkret eksempel, fx Esthers
frisørsalon i Korsgade 10, "Korsgades sidste butik"]. Jeg vil gerne spørge
om lov til at bruge dem sådan:

- **Vi skriver selv en kort tekst** om én episode, med vores egne ord,
  aldrig et uddrag af artiklen.
- **I står som kilde** med foreningens navn, og et link til årsskriftet og
  til hvordan man bliver medlem.
- **Vi gemmer ikke jeres tekster.** Vi læser hvert årsskrift én gang for at
  finde stederne, og sletter teksten bagefter.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.
- **Private navne**: handler en historie om en privatperson, der kan være i
  live, nævner vi ikke navnet uden at have spurgt.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Er det i orden med jer? Og skal jeres navn stå på en bestemt måde?

Venlig hilsen
[navn]
[telefon]

---

## 10. YouTube channels: Københavnerliv, Københavnerglimt

docs/10, *The sources' legal footing*, rates the YouTube corpus "No, as
built": every channel needs written permission. Københavnerliv and
Københavnerglimt first (107 of the visible memories).

**Emne:** Må vi fortælle jeres Københavnerhistorier på stedet?

Hej [navn],

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér.

Jeres videoer er fulde af den slags: [ét konkret eksempel fra kanalen, fx
"historien om …" på …]. Jeg vil gerne spørge om lov til at bruge dem sådan:

- **Vi skriver selv en kort tekst** om én episode fra en video, med vores
  egne ord, aldrig et klip eller en afskrift.
- **I står som kilde** med kanalens navn øverst, og et link der åbner videoen
  på YouTube præcis hvor historien bliver fortalt. Seerne ender hos jer.
- **Vi gemmer ikke jeres videoer.** Vi læser undertekstsporet én gang for at
  finde stederne, og sletter det bagefter.
- **I kan altid sige stop**, også for en enkelt historie, og så er den væk
  inden for et døgn.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag. Vi sælger
aldrig adgang til jeres indhold enkeltvis.

Er det i orden med jer? Og skal jeres navn stå på en bestemt måde?

Venlig hilsen
[navn]
[telefon]

---

## 11. kbhbilleder

kbhbilleder@kff.kk.dk. 41,779 photos, maps and drawings, about 5,000 out of
copyright and free for commercial use, many geotagged. The site is
bot-protected, so ask and never scrape. The code is open with a public APACS
API (github.com/CopenhagenCityArchives). A great, precisely located picture
of a scene is a memory in itself.

**Emne:** Jeres frie billeder i en gåtursapp om Københavns historie

Hej,

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér, og et gammelt billede fra præcis det sted er
ofte den bedste historie af alle.

Må jeg hente de billeder der er fri af ophavsret og frie til kommerciel
brug, med deres placering, gennem jeres API i stedet for at belaste
hjemmesiden? Og findes der en liste over netop dem, eller et felt der
siger det?

- **I står som kilde** under hvert billede, med arkivets navn, fotografen
  og et link til billedet hos jer.
- **Kun frie billeder**: vi bruger intet der stadig er beskyttet.
- **I kan altid sige stop**, også for et enkelt billede, og så er det væk
  inden for et døgn.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Venlig hilsen
[navn]
[telefon]

---

## 12. Historisk Atlas

it@historiskatlas.dk. Their API carries each story's licence ("Geo"), which
the public pages don't show; the sitemap gives only a title and an intro.
Ingest only stories under CC BY, BY-SA or public domain (docs/10, *The
sources' legal footing*). They are partly a competitor, so ask for access,
not a partnership.

**Emne:** Adgang til jeres API til en gåtursapp om Københavns historie

Hej,

Jeg bygger Memory Lane, en app der planlægger gåture i København forbi
steder hvor noget er sket. Når man står på stedet, åbner en kort historie
om hvad der skete netop dér.

Jeres fortællinger passer præcis til det, fx [én konkret historie]. Må jeg
få adgang til jeres API, så jeg kan se hver fortællings licens og hele
teksten?

- **Kun åbne licenser**: vi bruger kun fortællinger under CC BY, CC BY-SA
  eller i public domain, og følger licensens krav.
- **I står som kilde** med Historisk Atlas' navn og et link til
  fortællingen hos jer.
- **I kan altid sige stop**, også for en enkelt fortælling, og så er den
  væk inden for et døgn.

Appen er gratis med én gåtur om ugen; et abonnement giver en hver dag.

Venlig hilsen
[navn]
[telefon]
