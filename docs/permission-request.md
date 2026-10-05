# Asking a channel for permission

docs/10-decisions.md, *The sources' legal footing*, rates the YouTube corpus
"No, as built": every channel needs written permission. This is the email,
for Københavnerliv and Københavnerglimt first (107 of the visible memories).
Send it from the founder's own address, one channel at a time, and file the
reply's date and wording on the `sources` row (`--note`).

What we promise in it has to be true before we send it:

- **The proxy is gone.** Drop `WEBSHARE_PROXY_*` for permitted channels; a
  permitted channel can be drip-fetched without it.
- **A transcript is deleted once it is extracted.** Built 2026-10-04: aggregation
  forgets a video's captions (docs/10, *A video's transcript is deleted once it
  is extracted*). Run `python -m pipeline.transcripts --forget-extracted` once
  for the backlog before sending.

---

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

Appen er gratis med én gåtur om dagen; et abonnement giver flere. Vi sælger
aldrig adgang til jeres indhold enkeltvis.

Er det i orden med jer? Og skal jeres navn stå på en bestemt måde?

Venlig hilsen
[navn]
[telefon]

## For a local-history society's yearbooks

Their first-hand stories from living memory are what the free sources lack
(research 2026-10-05). Ask in this order, one at a time:

1. Nørrebro Lokalhistoriske Forening, info@noerrebrolokalhistorie.dk: 24
   yearbooks 2000-2023 as text PDFs at `noerrebrolokalhistorie.dk/aarsskrifter/`
2. Sydhavnens Lokalhistoriske Arkiv, sydhavnen@outlook.dk: 26 "erindringsartikler"
3. SLAK, `slak.dk/kontakt`: the umbrella for the city's ten societies, for an
   introduction to Østerbro, Valby and Vesterbro

The same promise holds: the text is forgotten once extracted
(`pipeline.transcripts.forget`), so the source needs that before we send.

---

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

Appen er gratis med én gåtur om dagen; et abonnement giver flere.

Er det i orden med jer? Og skal jeres navn stå på en bestemt måde?

Venlig hilsen
[navn]
[telefon]
