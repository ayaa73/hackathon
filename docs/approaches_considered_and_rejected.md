# Approaches Considered and Rejected

We tested whether outside events explain swings in daily sales: strikes, exam periods, expatriate
travel and football. None gave an effect we could trust or act on, so we dropped all four.
Everything below can be reproduced with `python rejected_approaches/event_tests.py`
(results: `outputs/tables/rejected_event_tests.csv`).

## How every idea was tested

- **Data:** Jan 1 to Jun 30 2026, 181 days, no missing days, 132 duplicate rows removed as in the
  rest of the project. Daily series for the chain and for each branch.
- **Baseline:** sales rise roughly 9% a month over the period, and Tuesdays are a large recurring
  spike (about 1.5x a normal weekday). Both are removed first (day-of-week effects plus a smooth
  trend; two trend specifications reported).
- **Single event day:** the model is fitted without that day, then the day's miss is compared with
  the misses of all 181 days.
- **Multi-day window:** the window's effect is compared with the same effect for placebo windows
  of the same length at every other position in the data.
- **Multiple testing:** the more dates we test, the more likely one looks special by luck, so
  Bonferroni-adjusted p-values are reported next to raw ones.
- **Measured vs assumed:** event dates come from the sources at the bottom. What counts as an
  "event" is an assumption and is marked as such.

## What we claimed vs what the data shows

| Idea | Our claim | Verdict |
|---|---|---|
| Strikes | Relation found only on 18 March | **Confirmed, but weak.** Only 18 Mar stands out (p = 0.033), and it does not survive correction for testing 8 strike days (p = 0.26) |
| University exams (Apr-May) | Little evidence | **Confirmed.** No effect (-2% to +1%, p >= 0.2) |
| High-school exams (May-Jun) | Little evidence | **Mostly confirmed.** Orders sit 3-7% above trend in May-June (p = 0.02-0.04) but revenue does not (p >= 0.39), and June alone shows nothing |
| Lebanese expats | No direct correlation | **Confirmed.** No window significant; Easter weekend orders +10% is the closest (p = 0.07) |
| Football match days | (tested for extra sales) | **No extra sales found** on Champions League semi-final and final nights or in the World Cup's first 20 days |

---

## Entries

### 1. Strikes (Israeli air strikes on Beirut) vs daily sales
- **What we tried:** compared sales on the days of dated strikes on Beirut with what the baseline
  predicted. Days tested: 4, 8, 12, 18 Mar; 1, 8 Apr; 6 May; 7 Jun. Revenue and order counts, for the
  chain and each branch (64 tests in total).
- **Assumption:** "strikes" means military strikes on Beirut. Labour strikes were not tested. The
  list is not complete: the sources date only some Beirut strikes, so days not on the list may also
  have had strikes.
- **Why we thought it might work:** a strike on the capital could keep customers home and cut
  sales, which would let Stories plan staffing around such days.
- **What we found (measured):**
  - 18 Mar is the only day that stands out: chain revenue 18% below the model (about 21% below the
    two neighbouring Wednesdays, $1,320 vs $1,655-$1,668); Garden 31% below. Raw p = 0.033 for both.
  - Orders fell less than revenue (chain -10%, p = 0.20), and revenue per order fell from about $9.30
    to $8.15.
  - The other seven strike days show nothing consistent: chain revenue effects run from -13% to
    +11% in both directions, none with p < 0.13.
  - Across all 64 tests, 2 reach p < 0.05; about 3 would by pure chance. After correcting for the 8
    strike days, 18 Mar has p = 0.26.
- **Alternative explanations we checked for 18 Mar:**
  - *Discounts:* discounted lines were 15.7% of lines that day against 3.6-5.0% on other Wednesdays,
    but the discounts only cost $27, so they do not explain a drop of about $340. List-price
    revenue itself was 19% down. Why discounting spiked that day is unknown.
  - *Data gap:* the shops were open all day and the drop is spread over most hours, so it is not a
    missing-data artefact.
  - *Eid:* 18 Mar is two days before Eid al-Fitr (20 Mar), and sales were low again on 20-22 Mar.
    We did not test whether the pre-Eid period, rather than the strike, explains the dip.
- **Why we dropped it:** one day out of eight, not significant after correction, and strikes cannot
  be forecast, so there is no decision Stories could take from it.
- **Could it change our recommendation?** Only with a complete dated list of strikes by
  neighbourhood and branch location, which would test whether branches closer to a strike fall
  further.

### 2. University and high-school exam periods
- **What we tried:**
  - *Universities:* window 20 Apr to 17 May (AUB's in-person return and exam period) and the finals
    alone (8-17 May).
  - *High schools:* window 1 May to 30 Jun, and June alone.
- **Assumptions:** only AUB's dates were found, so other universities are assumed to be similar. We
  could not find school-level exam calendars. In 2026 the Brevet was cancelled and the first
  Baccalaureate session is 29 June (later sessions 27 July and 7 September), so "May-June" is our
  guess at internal school exams, not an official exam period.
- **Why we thought it might work:** students and parents studying late might buy more coffee and
  food around exams.
- **What we found (measured):**
  - Universities: revenue -2.4% / -2.1% over the long window and +0.7% / -0.3% for finals only
    (two trend models; all p >= 0.20). Placebo windows move by about 5-11% on their own, so only
    effects larger than that could be detected.
  - High schools: orders +6.5% / +2.9% above trend over May-June (raw p = 0.041 / 0.025; adjusted
    p = 0.082 / 0.049), revenue +3.8% / +1.4% (p >= 0.39). June alone: -0.4% / +0.2%.
- **Alternative explanation for the school result:** a ceasefire took effect in mid-April (16 or 17
  Apr, depending on the source) and sales were recovering throughout May-June. A two-month window at the end of the data cannot be
  separated from that recovery or from seasonal ramp-up.
- **Why we dropped it:** no revenue effect at either level, an order effect that is borderline and
  does not follow exam dates, and no lever Stories can pull.
- **Could it change our recommendation?** Branch-level data near campuses and school exam
  calendars, and more than one year of data.

### 3. Lebanese expatriate travel
- **What we tried:** looked for lifts around expat travel windows: the two Easter weekends (3-6 Apr
  and 10-13 Apr) and the late-June arrival ramp (15-30 Jun).
- **Assumption:** we have no day-level expat arrival data, so these windows are proxies. Airport
  data say April arrivals jumped 47.9% on March to 72,454, which the source attributes to Easter,
  and that daily arrivals rose from about 2,000 to about 12,000 in summer (the source does not
  give dates and does not separate expats from other travellers).
- **Why we thought it might work:** returning expats spend heavily at cafes, so arrivals could
  explain demand peaks.
- **What we found (measured):** no window is significant. Easter weekend 1: orders +10% (raw p =
  0.07, adjusted p = 0.22), revenue +5% (p = 0.4). Orthodox Easter: -3% revenue. Late June: +0.6%
  revenue, +0.4% to +2.3% orders.
- **Why we dropped it:** no direct correlation.
- **Could it change our recommendation?** Yes, but we cannot test it. The data end on 30 June, so
  the July-August expat peak is not in the file. Testing it needs a summer of data.

### 4. Football match nights
- **What we tried:** checked whether evening sales (20:00-23:59, the busiest hours) rise on big
  match nights: the Champions League semi-final legs (28 and 29 Apr, 5 and 6 May), the final (30
  May), and the World Cup's first 20 days (11-30 Jun; group stage ends 27 Jun).
- **Assumptions:** these are the matches most likely to matter. We do not know whether any branch
  screens matches. Local league games, national-team games and individual World Cup matches were
  not tested one by one.
- **Why we thought it might work:** match nights draw people out to watch together, which would
  mean more evening orders and a case for match-night staffing or promotions.
- **What we found (measured):** evening orders on the five nights range from -6.7% to +17.9%
  against the model, all p >= 0.20; evening share of orders shows no pattern (p >= 0.12). World
  Cup window: +2% to +5% in evening orders (p = 0.30 / 0.57).
- **Why we dropped it:** no extra sales on match days. The effects are not distinguishable from
  normal day-to-day noise.
- **Could it change our recommendation?** A pilot at a branch that screens matches, comparing it
  with a matched branch that does not, would show whether screening itself changes sales.

---

## Limits shared by all four tests

- Only six months of data, so seasonal effects and event effects cannot be told apart.
- The war and ceasefire period overlaps most of the event windows (war from 2 Mar, ceasefire from
  mid-April), so any result could be mixed with the security situation.
- The tests cannot rule out small effects. Placebo windows swing by roughly 3-12% on their own,
  depending on window length and trend model, so smaller effects are invisible.
- A "no significant effect" result means we could not detect one, not that there is none.

## Sources

- [Al Jazeera: Israel bombs central Beirut, 18 March 2026](https://www.aljazeera.com/news/2026/3/18/israel-bombs-central-beirut-killing-6-strafes-south-east-lebanon)
- [Wikipedia: 2026 in Lebanon](https://en.wikipedia.org/wiki/2026_in_Lebanon) (dates of Beirut strikes and truces)
- [Wikipedia: Timeline of the 2026 Lebanon war](https://en.wikipedia.org/wiki/Timeline_of_the_2026_Lebanon_war) (8 April strikes)
- [AUB provost letter: return to campus, classes end 4 May, finals 8-17 May](https://aub.edu.lb/Registrar/Documents/announcements/provostmessage-students-return2campus-april20%2C2-26.pdf)
- [Annahar: Brevet cancelled, three Baccalaureate sessions](https://en.annahar.com/en/310193/cancellation-of-the-brevet-exams-in-lebanon-2026-and-adoption-of-three-sessions-for-the-baccalaureate)
- [LBCI: Baccalaureate session dates](https://v7cdn.lbcgroup.tv/news/lebanon-news/932578/education-minister-announces-three-baccalaureate-sessions-cancels-brev/en)
- [Hospitality News: Beirut airport passenger traffic](https://www.hospitalitynewsmag.com/beirut-airport-passenger-traffic/)
- [Foot-Africa: Champions League 2026 semi-final dates](https://foot-africa.com/en/news/champions-league-2026-semi-finals-first-and-second-leg-dates-1169012/)
- [Al Jazeera: World Cup 2026 key dates](https://aljazeera.com/sports/2026/6/4/world-cup-2026-what-are-the-key-dates-from-the-opening-match-to-the-final)

## More entries

_Add further approaches below using the same format: what we tried, why we thought it might work,
what we found, why we dropped it, and whether it could change the recommendation._
