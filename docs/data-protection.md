# Data protection: legitimate interest and DPIA

Draft, 2026-10-09. Written from the code and `docs/10-decisions.md` by the
team, not by a lawyer, for the Danish lawyer who reads *The sources' legal
footing* before launch. **Unsure** marks what we do not know. "Today" means
what the code does now; "Before launch" means what it does not do yet.

Two assessments:

1. A DPIA of the users' location, and of the step count the app no longer
   collects.
2. A legitimate-interest assessment (and the DPIA questions) for summarising
   third-party sources that name private people.

The user-facing version is the privacy policy, `api/privacy.py` (served at
`/privacy`) and its twin `mobile/store/privacy.md`.

## Who is responsible

- **Controller:** [COMPANY NAME AB], a Swedish company not yet registered.
  One founder; no employees.
- **Contact:** `CONTACT_EMAIL`, not yet chosen. No DPO; with no large-scale
  systematic monitoring as a core activity we believe none is required
  (Art 37). **Unsure**, given the background location below.
- **Which law. Unsure, and the first question for the lawyer.** The
  controller will be Swedish and the launch city is Copenhagen. Sweden's
  supervisory authority (IMY) would lead (Art 56). The national rules this
  repo has relied on are Danish: databeskyttelsesloven §2(5) (the dead
  protected for 10 years) and §3(8) (journalism). Which member state's Art
  85 law governs a Swedish company's text read in Denmark, and whether the
  Danish rules on the dead apply at all, we do not know. Danish copyright
  and criminal law (§264d, §267) still matter for text read in Denmark.

## 1. Location (DPIA)

### What is processed

| Data | When | Kept where, how long |
|---|---|---|
| Precise position | Planning a walk (`GET /v1/routes/preview`, accept) | Not in the database: the start is never stored (*A route is anchored on where you were*). The walk's stops and the street shape between them are stored in `daily_routes`, linked to the device, until the account is deleted. The first stop is usually within about a kilometre of the start |
| Precise position | Opening a story (`POST` unlock) | Not stored. `unlocks` keeps the memory and the time. The memory's spot is known, so each row says "this account stood within 20 m of here, then" |
| Precise position | The map (`GET /v1/memories/nearby`) | Not stored in the database |
| Background position (opt-in) | The proximity notification and the weekly surprise (`mobile/src/geofence.ts`): OS geofences on the phone; a coarse location task re-asks `/nearby` about every 500 m moved; a crossing asks `POST /v1/surprise` | Geofencing runs on the phone. `/nearby` as above. `surprises` keeps memory and time, like an unlock |
| Position of a post | Filing a memory | Public, by design (*Every memory is public*), until the post or account is deleted. The phone's own geocoder (Apple; Google on Android) gets it for the street name |
| Every GET's query string, with `lat`, `lng` and the device id | Every request above that is a GET | **The request log.** Uvicorn's access log and Railway's HTTP logs record the path with its query string and an IP. Retention is Railway's: **Unsure** how long; to be confirmed on the plan we buy |
| Step count | Not collected | `expo-sensors` and `POST /v1/me/steps` are gone (*Steps open a memory*, superseded). Nothing reads Core Motion or Health. If it comes back: the decision kept a balance, never a daily series, because steps beside precise location may be health data (WP29 2015 annex; CJEU C-184/20). Do that again, or reassess |

Routing (`api/streets.py`) runs on our own OSRM sidecar; no third party sees
the walk.

### Is a DPIA required

Probably. Location is "data of a highly personal nature" in the EDPB's
WP248 criteria, and the opt-in background watch is close to "systematic
monitoring". Two criteria usually mean a DPIA. **Unsure** whether IMY's or
Datatilsynet's lists name location apps outright; we do one either way.

### Necessity and proportionality

- The product is "a story opens only standing on its spot". Without a
  position there is no product; the 20 m check is the purpose, not a side
  use.
- The position is used for the request and dropped, except where a record
  is the feature (a walk, an opening, a post).
- No home address, no saved start, no trail between stops, no step series,
  no advertising id, no analytics SDK.
- Background location is off by default, behind an in-app toggle and the
  OS's own prompt, and stops when either is turned off.

### Risks to the people

| Risk | Likelihood | Severity | Notes |
|---|---|---|---|
| Our stored walks and openings reveal routine and home area | Medium for a regular walker | Medium | A year of walks from the same front door draws a circle around it. Only we, and the account holder, can read them |
| The request log holds raw positions beside the device id | Certain, today | Medium | The device id is the account's only credential (*No session tokens*), so the log is also a list of keys. Anyone with log access can act as any user |
| A leaked device id lets someone read a person's walks and openings | Low | Medium | Same credential; no session, no expiry |
| A post's coordinates locate the writer | Certain, by design | Low to high | The writer chose to post there; the policy and the compose screen say it is public. A post filed at home is the bad case |
| Background tracking felt as surveillance | Low | Low | Opt-in; nothing leaves the phone except `/nearby` and the weekly surprise |
| Spoofed position | Medium | Low for the user | Hurts the game, not a person (*The position is self-reported*) |

### Measures

In place:

- Start never stored; walks that opened nothing deleted when ended.
- Photo EXIF (including GPS) stripped on upload (`api/media.py`).
- Account deletion in the app deletes walks, openings, surprises, posts and
  media (*Deleting an account deletes what it made*); `python -m
  api.my_data` answers access requests from the same definition.
- Self-hosted routing. The map is Apple's on iOS; on Android it is Google
  Maps, which sees the viewport and IP.

Before launch (recommended, not built):

- **Keep positions and the device id out of the logs:** run uvicorn with
  `--no-access-log`, or log the path without its query string, and check
  Railway's HTTP log. Better still, move `lat`, `lng` and `device` from GET
  query strings into a header or POST body. Without this, the policy's
  "not saved" is only true of the database.
- Set a retention for `daily_routes`, `unlocks` and `surprises` of inactive
  accounts (none today; rows live until deletion). **Unsure** what period
  is defensible; a year of inactivity is a common choice.
- Decide whether the walk's first stop needs to be stored at all once the
  walk ends.
- Confirm Railway's region (EU) and sign its DPA; same for RevenueCat.

## 2. Summaries of third-party sources about private people

### What is processed

The pipeline reads published sources (books, old newspapers, archive
stories, plaques, YouTube videos, local magazines; see *The sources' legal
footing* and *Recent sources without permission*), sends the text to
Anthropic's API, and stores a 40-180 word retelling at a spot, credited and
linked to its source and labelled "Retold by AI". Some name people. Kept:
the summary, a one-line quote, the model's raw JSON
(`extraction_chunks.response`) and review rows (`memory_reviews`). Video
transcripts are deleted once extracted (*A video's transcript is deleted*);
book and archive texts are kept.

Who is named: historical figures; public figures at a spot (*Famous people
at a spot*); private people in old sources (mostly long dead); and, in the
recent sources, living private people named by a local weekly or a video's
creator.

### Legitimate-interest assessment (Art 6(1)(f))

**Purpose.** Telling a walker what happened where they stand: local history
and culture, which is a recognised interest (Art 85, recital 153), and a
commercial one, which counts too. We do not rely on the journalism
exemption: LLM output without an editorial check does not meet it (CJEU
C-199/24, as read in *The sources' legal footing*). **Unsure** whether the
Swedish rules (dataskyddslagen 1:7, or an utgivningsbevis) change that.

**Necessity.** The place is the point, not the person. A story usually
survives without a private person's name ("a baker", "a widow"); a famous
person's name is often the story. So: name public figures; name private
people only where the story fails without them; never their door number.

**Balancing.**

- For: the source was already published, often a century ago; the dead are
  outside GDPR (recital 27), save national rules. A story can be read only
  by someone standing within 20 m of it, on a walk the app planned, about
  one a kilometre: it is not searchable, indexed, or browsable on a map. A
  privacy report hides it at once (*A legal report hides at once*).
- Against: the person never expected an app to retell it, and the model can
  get it wrong (Art 5(1)(d)): wrong names and causes of death have been seen
  (TODO.md, grounding). A recent local story about a living private person
  carries the most weight against us. Art 9 and Art 10 data (health,
  politics, crime) about a private person is not allowed on 6(1)(f) at all.
- Result: acceptable for public figures and the long dead; acceptable for
  living private people only with the measures below in place, and not for
  their health, politics or crimes.

**Art 14 (telling the people named).** We cannot find most of them. We rely
on Art 14(5)(b) (disproportionate effort), publish this assessment's gist in
the privacy policy (*Stories about other people*), and give a takedown
route. **Unsure** whether that is enough for recent sources.

### Measures

In place:

- Credit, link and "Retold by AI" on every card (AI Act Art 50(4)).
- The proximity gate: nothing is served off the spot (`api/gate.py`).
- Report with a reason; privacy, defamation and copyright hide at once from
  a signed-in account (`api/write.py`, `api/moderate.py`).
- Pictures and links leave out private people (`pipeline/enrich.py`,
  `pipeline/links.py`); the walk score sinks a private person's death,
  illness or crime (`pipeline/walk_score.py`), but does not remove it.
- Transcripts deleted after extraction.

Before launch (from *The sources' legal footing* and TODO.md, not built):

- **Suppress** health, crime and WWII politics about private people in the
  extraction prompt, and check the existing corpus for them.
- **Place private people at the street**, not the door, or drop the name.
- Leave living relatives' names out (Stolpersteine row).
- A takedown honoured within a day needs a monitored `CONTACT_EMAIL`.
- Ground the summary against its source, to catch a wrong name or cause
  before it ships (TODO.md, *grounding*).

## Open questions for the lawyer

1. Which national law applies (Swedish controller, Danish readers), and
   does it change the journalism exemption or the 10-year rule on the dead?
2. Is Art 14(5)(b) enough for living private people named in recent local
   sources, or must they be left out?
3. Is background location consent under Art 6(1)(a), or covered by 6(1)(b)
   once the user turns the feature on? And does the ePrivacy rule on
   reading the device (Sweden's LEK 9:28, Denmark's cookiebekendtgørelse)
   need more than the OS prompt?
4. Is a DPO or a prior consultation (Art 36) needed?
5. Is defaulting the public display name to the name Google hands over
   compatible with Art 25 (privacy by default)?
