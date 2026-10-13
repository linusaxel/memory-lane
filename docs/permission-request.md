# Permission requests

Every source we may only use with a yes, and the email that asks for it. Send
from the founder's own address, one at a time, and fill in `[navn]` and
`[telefon]`. When a reply comes, file its date and wording on the `sources`
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

Til: am@arbejdermuseet.dk

Emne: Humlen ved Carlsberg i en gåtursapp

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Humlen ved Carlsberg er fuld af den slags. Fx to-øres-strejken i 1965. I dag
går folk gennem Carlsberg Byen uden at vide, hvad der skete i bygningerne, og
det er netop et kvarter, hvor vi mangler historier.

På siden står der, at teksterne kun må citeres i ikke-kommerciel sammenhæng,
så derfor spørger jeg først. Sådan ville vi bruge dem:

Vi skriver selv en kort tekst om én episode med vores egne ord og citerer
højst en enkelt linje. Ved hver historie står Arbejdermuseet og Humlen ved
Carlsberg som kilde, med et link til indlægget. Vi gemmer ikke teksterne,
når vi har læst dem. Vi nævner ikke kolleger ved navn uden at spørge. Og vil
I have en historie fjernet, eller det hele, så er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer? Jeg svarer gerne på spørgsmål, også på telefon.

Venlig hilsen
[navn]
[telefon]

---

## 2. Lokalhistorisk Selskab for Brønshøj, Husum og Utterslev

Til: bo.oehrstroem@gmail.com
Cc: info.lhsbhu@gmail.com

Emne: Jeres lokalhistorie i en gåtursapp

Hej Bo,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Brønshøj, Husum, Utterslev og Bispebjerg er de kvarterer, hvor vi har færrest
historier. Jeres blad har netop dem, fx mindestenen ved gadekæret i 1931 og
filmoptagelserne på Emdrupborg fra 1911 til 1917. Der står "eftertryk efter
aftale", så jeg spørger, om vi må bruge artiklerne sådan her:

Vi skriver selv en kort tekst om én episode med vores egne ord og citerer
højst en enkelt linje. Ved hver historie står selskabets navn og et link til
jer, også til hvordan man bliver medlem. Vi gemmer ikke teksterne, når vi har
læst dem. Vi nævner ikke privatpersoner, der kan være i live, uden at spørge.
Og vil I have en historie fjernet, eller det hele, så er den væk inden for et
døgn.

Har I også Min barndom på Bispebjerg eller Erindringssamtaler fra
Nordvest-Bispebjerg som tekst, vil jeg gerne spørge om det samme for dem.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 3. Københavns Stadsarkiv: erindringerne

Til: XM9P@kk.dk
Cc: stadsarkiv@kk.dk

Emne: Erindringerne fra 1969 og 1995 i en gåtursapp

Hej Eva,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Jeres erindringer er det bedste, der findes, om hvordan byen var at leve i,
gade for gade. Børnene der legede på Sønder Boulevard i 1955, eller hvor folk
stod den 4. maj 1945. Vi har ikke hentet noget fra kbharkiv.dk, og det vil vi
heller ikke gøre uden lov.

Kan vi få adgang til erindringerne som tekst, fx gennem et API eller et
udtræk? Sådan ville vi bruge dem:

Vi skriver selv en kort tekst om én episode med vores egne ord og citerer
højst en enkelt linje. Ved hver historie står Stadsarkivet som kilde, med et
link til erindringen hos jer. Vi nævner ikke privatpersoner ved navn, kun
stedet og det der skete. Vi gemmer ikke teksterne, når vi har læst dem. Og
vil I have en historie fjernet, eller det hele, så er den væk inden for et
døgn.

Gælder der særlige regler for erindringer, hvor skribenten kan være i live,
vil jeg gerne kende dem.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]

---

## 4. Kgs. Enghave Lokalhistoriske Arkiv (Sydhavnens historie)

Til: sydhavnen@outlook.dk

Emne: Jeres erindringsartikler i en gåtursapp

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

I Sydhavnen har vi næsten ingen historier endnu. Jeres erindringsartikler fra
40'erne, 50'erne og 60'erne er præcis det, vi mangler. Der står, at de kun må
gengives efter aftale, så jeg spørger, om vi må bruge dem sådan her:

Vi skriver selv en kort tekst om én episode med vores egne ord og citerer
højst en enkelt linje. Ved hver historie står arkivet som kilde, med et link
til artiklen. Vi gemmer ikke teksterne, når vi har læst dem. Vi nævner ikke
privatpersoner, der kan være i live, uden at spørge. Og vil I have en
historie fjernet, eller det hele, så er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 5. Frederiksberg Stadsarkiv: Frederiksberg-erindringer

Til: cach01@frederiksberg.dk
Cc: stadsarkivet@frederiksberg.dk

Emne: Frederiksberg-erindringerne i en gåtursapp

Hej Caspar,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København og på Frederiksberg. Undervejs kommer man forbi steder,
hvor noget er sket, og når man står der, kan man læse en kort historie om
det.

Jeres film med folk, der fortæller om deres eget Frederiksberg, er præcis
den slags, fx Elektrikeren og Mariendalskvarteret. Jeg har to spørgsmål:

Findes der udskrifter eller undertekster til filmene? Vi lytter ikke selv
lyd af, så uden tekst kan vi ikke finde stederne.

Og må vi bruge dem sådan her: Vi skriver selv en kort tekst om én episode
med vores egne ord og viser aldrig klip. Ved hver historie står Stadsarkivet
og fortælleren som kilde, med et link til filmen. Vi gemmer ikke teksten,
når vi har læst den. Vi nævner ikke andre privatpersoner, som fortælleren
taler om. Og vil I have en historie fjernet, eller det hele, så er den væk
inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]

---

## 6. Bryggebladet

Til: redaktion@bryggebladet.dk

Emne: Bryggens historier i en gåtursapp

Hej Andreas,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Bryggebladet har historier om Islands Brygge, som ingen andre har, fx de to
hundredårige, der flyttede ind i Egilsgade 59 i 1908. Vi har prøvet at finde
historier i nogle af jeres numre fra 2019 og frem. Bagefter så jeg jeres side
om ophavsret, og derfor spørger jeg nu. Siger I nej, sletter vi det.

Sådan ville vi bruge artiklerne: Vi skriver selv en kort tekst om én episode
med vores egne ord og citerer højst en enkelt linje. Ved hver historie står
Bryggebladet med dato og et link til artiklen. Vi gemmer ikke teksterne, når
vi har læst dem. Vi nævner ikke privatpersoner, der kan være i live, uden at
spørge. Og vil I have en historie fjernet, eller det hele, så er den væk
inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 7. Nørrebro Lokalhistoriske Forening

Til: info@noerrebrolokalhistorie.dk

Emne: Jeres årsskrifter i en gåtursapp

Hej Jan,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Jeres årsskrifter er fulde af den slags. Den bedste historie, vi har fundet,
er Kierkegaards begravelse på Assistens Kirkegård i 1855, fra årsskriftet
2023. Vi har prøvet det af på nogle af årsskrifterne, og jeg burde have
spurgt først. Siger I nej, sletter vi det.

Sådan ville vi bruge dem: Vi skriver selv en kort tekst om én episode med
vores egne ord og citerer højst en enkelt linje. Ved hver historie står
foreningens navn og et link til årsskriftet, også til hvordan man bliver
medlem. Vi gemmer ikke teksterne, når vi har læst dem. Vi nævner ikke
privatpersoner, der kan være i live, uden at spørge. Og vil I have en
historie fjernet, eller det hele, så er den væk inden for et døgn.

Er der artikler, hvor den der gav materialet har sat begrænsninger, så sig
endelig til.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 8. SLAK

Til: helge.olesen@email.dk

Emne: Kan du hjælpe mig videre til de lokalhistoriske foreninger?

Hej Helge,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

De bedste historier, vi har fundet, kommer fra de lokalhistoriske foreninger:
folk der fortæller om deres egen gade. Jeg spørger allerede Nørrebro og
Sydhavnen, men vil gerne også i kontakt med foreningerne på Østerbro, i Valby
og på Vesterbro.

Vi skriver selv en kort tekst om én episode med vores egne ord, foreningen
står som kilde med et link, vi gemmer ikke teksterne, og en forening kan
altid sige stop.

Vil du sende det her videre, eller fortælle mig hvem jeg skal skrive til?

Venlig hilsen
[navn]
[telefon]

---

## 9. Københavnerglimt

Til: info@dnrmedia.dk

Emne: Københavnerglimt i en gåtursapp

Hej Allan,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Jeg skriver til DNR Media, fordi jeg tror, det er jer, der laver
Københavnerglimt. Er det forkert, vil I så sende det videre?

Jeres videoer er de bedste, vi har fundet. Fx fodboldspillerne fra KB, der
blev anholdt i Guldbergsgade for at vise benene, eller Vor Frues klokker, der
spillede som en salme, mens tårnet brændte. Vi har prøvet det af på jeres
videoer, og jeg burde have spurgt først. Siger I nej, sletter vi det.

Sådan ville vi bruge dem: Vi skriver selv en kort tekst om én episode med
vores egne ord og viser aldrig klip. Ved hver historie står Københavnerglimt
øverst, med et link der åbner videoen på YouTube præcis dér, hvor historien
bliver fortalt. Vi læser underteksterne én gang for at finde stederne og
sletter dem bagefter. Og vil I have en historie fjernet, eller det hele, så
er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 10. Københavnerliv

Til: the address behind "View email" on youtube.com/@Kbherliv/about

Emne: Københavnerliv i en gåtursapp

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Jeres videoer er fulde af den slags. Fx baren på det gamle Hotel Kong
Frederik, hvor Politikens journalister og Tom Kristensen sad efter fyraften.
Vi har prøvet det af på jeres videoer, og jeg burde have spurgt først. Siger
I nej, sletter vi det.

Sådan ville vi bruge dem: Vi skriver selv en kort tekst om én episode med
vores egne ord og viser aldrig klip. Ved hver historie står Københavnerliv
øverst, med et link der åbner videoen på YouTube præcis dér, hvor historien
bliver fortalt. Vi læser underteksterne én gang for at finde stederne og
sletter dem bagefter. Og vil I have en historie fjernet, eller det hele, så
er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 11. Christiania1 (via Christianias Arkiv)

Til: caarkiv@gmail.com

Emne: Christianiahistorierne i en gåtursapp

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

YouTube-kanalen Christiania1 skriver, at den ligger i jeres arkiv, så jeg
håber, I er de rigtige at spørge. Ellers vil I så sende det videre?

Filmene i serien christianiahistorie er fulde af den slags. Fx Mikael Focks
fortælling om Solvognen og giftlageret hos Sadolin & Holmblad. Vi har prøvet
det af på nogle af filmene, og jeg burde have spurgt først. Siger I nej,
sletter vi det.

Sådan ville vi bruge dem: Vi skriver selv en kort tekst om én episode med
vores egne ord og viser aldrig klip. Ved hver historie står kanalen og
fortælleren som kilde, med et link der åbner filmen præcis dér, hvor
historien bliver fortalt. Vi læser underteksterne én gang og sletter dem
bagefter. Og vil I have en historie fjernet, eller det hele, så er den væk
inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 12. Kim Greiner

Til: kim@greiner.dk

Emne: Dine historier om Nyhavn og Christianshavn

Hej Kim,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Dine sider om Nyhavns huse og om Christianshavn er noget af det bedste, vi
har fundet. Fx Titanic-billetterne, der blev solgt i Nyhavn 1, og
fangeoprøret i 1817, hvor Lagkagehuset ligger i dag. Vi har allerede brugt
dem, og jeg vil gerne høre, om det er i orden med dig.

Vi skriver selv en kort tekst om én episode med vores egne ord og citerer
højst en enkelt linje. Ved hver historie står dit navn og et link til din
side. Vi gemmer ikke teksterne, når vi har læst dem. Og vil du have en
historie fjernet, eller det hele, så er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]

---

## 13. Refshaleøen TV, Kim Bargsteen

Til: mail@refshaleoen.dk (no address for the channel; ask them to pass it on)

Emne: Til Refshaleøen TV og Kim Bargsteen: Refshaleøens historie

Hej,

Jeg kan ikke finde en adresse til Refshaleøen TV. Vil I sende det her videre
til dem, eller til Kim Bargsteen? Tak.

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Filmen Refshaleøens historie fra 2022, hvor Kim Bargsteen fortæller om B&W,
er præcis den slags. Der findes næsten intet om Refshaleøen fortalt af nogen,
der var der. Jeg har to spørgsmål:

Findes der en tekst eller undertekster til filmen? Vi lytter ikke selv lyd
af, så uden tekst kan vi ikke finde stederne.

Og må vi bruge den sådan her: Vi skriver selv en kort tekst om én episode
med vores egne ord og viser aldrig klip. Ved hver historie står kanalen og
Kim Bargsteen som kilde, med et link der åbner filmen præcis dér, hvor
historien bliver fortalt. Vi gemmer ikke teksten, når vi har læst den. Og
vil I have en historie fjernet, så er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]

---

## 14. Dansk rockhistorie

Til: the address behind "View email" on the channel's About page
(`UCz0mJQVpBbLIjOq-oOb2nkA`); kontakt@peterbak.dk only if that fails

Emne: Dansk rockhistorie i en gåtursapp

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Jeres portrætter af musikerne fortæller om de øvelokaler, spillesteder og
studier, hvor det skete. Fx Flemming Rasmussen om Sweet Silence Studio. Vi
vil gerne lade folk stå på stedet og høre historien.

Sådan ville vi bruge dem: Vi skriver selv en kort tekst om én episode med
vores egne ord og viser aldrig klip. Ved hver historie står kanalen og
musikeren som kilde, med et link der åbner videoen på YouTube præcis dér,
hvor historien bliver fortalt. Vi læser underteksterne én gang og sletter
dem bagefter. Og vil I have en historie fjernet, eller det hele, så er den
væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 15. Kenneth A. Balfelt

Til: kenneth@kennethbalfelt.org

Emne: Dine film fra Enghave Plads

Hej Kenneth,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Dine film med ølfolket på Enghave Plads er nogle af de få steder, hvor folk
selv fortæller om Vesterbro og Sydhavnen. Jeg har to spørgsmål:

Findes der en tekst eller undertekster til filmene? Vi lytter ikke selv lyd
af, så uden tekst kan vi ikke finde stederne.

Og må vi bruge dem sådan her: Vi skriver selv en kort tekst om én episode
med vores egne ord og viser aldrig klip. Ved hver historie står dit navn som
kilde, med et link til filmen. Vi nævner ikke de medvirkende ved navn uden
at spørge. Vi gemmer ikke teksten, når vi har læst den. Og vil du have en
historie fjernet, så er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]

---

## 16. Shazia Khan: Al Magt til Kærligheden

Til: zarzia@gmail.com

Emne: Al Magt til Kærligheden i en gåtursapp

Hej Shazia,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Dine portrætter af christianitter fortæller om livet i Christiania, sted for
sted, af dem der selv var der. Jeg har to spørgsmål:

Findes portrætterne som tekst? Vi lytter ikke selv lyd af, så uden tekst kan
vi ikke finde stederne.

Og må vi bruge dem sådan her: Vi skriver selv en kort tekst om én episode
med vores egne ord og citerer højst en enkelt linje. Ved hver historie står
dit navn og den der fortæller, med et link til dig. Vi gemmer ikke teksten,
når vi har læst den. Og vil du have en historie fjernet, så er den væk inden
for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]

---

## 17. Stemmer fra Bjerget

Til: the address behind "View email" on youtube.com/@bbh_frh_hosp/about

Emne: Stemmer fra Bjerget i en gåtursapp

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Stemmer fra Bjerget fortæller om livet på Bispebjerg Hospital af dem, der
var der. Bispebjerg er et af de kvarterer, hvor vi har færrest historier.

Sådan ville vi bruge afsnittene: Vi skriver selv en kort tekst om én episode
med vores egne ord og viser aldrig klip. Ved hver historie står podcasten og
hospitalet som kilde, med et link til afsnittet. Vi nævner ikke patienter
ved navn. Vi læser underteksterne én gang og sletter dem bagefter. Og vil I
have en historie fjernet, så er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Er det i orden med jer?

Venlig hilsen
[navn]
[telefon]

---

## 18. kbhbilleder

Til: kbhbilleder@kff.kk.dk (unverified; if it bounces, stadsarkiv@kk.dk)

Emne: Jeres frie billeder i en gåtursapp

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man se en kort historie om det. Et gammelt billede fra
præcis det sted er tit den bedste historie.

Må jeg hente de billeder, der er fri af ophavsret og frie til kommerciel
brug, med deres placering, gennem jeres API? Jeg vil ikke belaste
hjemmesiden. Og findes der en liste over netop de billeder, eller et felt
der siger det?

Under hvert billede står arkivet, fotografen og et link til billedet hos
jer. Vi bruger kun frie billeder. Og vil I have et billede fjernet, så er det
væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]

---

## 19. Historisk Atlas

Til: info@historiskatlas.dk

Emne: Adgang til jeres API

Hej,

Jeg hedder [navn], og jeg er ved at lave Memory Lane, en app der planlægger
gåture i København. Undervejs kommer man forbi steder, hvor noget er sket, og
når man står der, kan man læse en kort historie om det.

Må jeg få adgang til jeres API, så jeg kan se hver fortællings licens og
hele teksten? Vi bruger kun fortællinger under CC BY, CC BY-SA eller i public
domain og følger licensens krav. Ved hver historie står Historisk Atlas som
kilde, med et link til fortællingen hos jer. Og vil I have en fortælling
fjernet, så er den væk inden for et døgn.

Appen er gratis med én gåtur om ugen. Vil man gå flere, koster det et
abonnement.

Venlig hilsen
[navn]
[telefon]
