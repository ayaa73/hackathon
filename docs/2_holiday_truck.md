# Project 2: Should Stories go to the customer?

## 1. Conclusion

Start with Eid boxes and a limited-edition ma'amoul, then one pop-up stand. Rent a truck only if the pop-up holds about 80 orders a day. Do not buy a truck on this file: at Garden-sized demand it loses money, and even a Harbour-sized season does not pay a trailer back inside two years.

The Eid dip is how the question came up. It is not the size of the prize. Eid al-Fitr cost about **$923** of revenue. A used truck is **$51,300** before it sells anything.

> **Measured** = computed from `data/raw/stories_transactions.csv` (Jan-Jun 2026).
> **Estimated** = a measured input times a stated assumption, or a US list price. Every URL is in [2_truck_sources.md](2_truck_sources.md). Anything without one is marked **ASSUMPTION - verify locally**.

---

## 2. The observation

Branch sales dip on some holidays. The old write-up compared each Eid day with that weekday's average over all six months. That baseline is wrong: chain revenue grew **52.4%** from January to June, so a late-May day looked strong against a winter-heavy average.

The corrected baseline is local. For each holiday day, expected revenue is the average of the **same weekday within ±21 days**, and the holiday's own dates are left out of that average. Code: [`truck/holiday_dips.py`](../truck/holiday_dips.py).

| Holiday | Actual | Expected | Gap | Gross-profit gap |
|---|---|---|---|---|
| Eid al-Fitr, 20-23 Mar | $4,970 | $5,892 | **-$923 (-15.7%)** | -$533 |
| Orthodox Easter, 10-13 Apr | $5,893 | $6,045 | -$152 (-2.5%) | -$106 |
| Eid al-Adha, 27-28 May | $3,701 | $3,822 | **-$122 (-3.2%)** | -$40 |
| Easter, 3-6 Apr | $6,330 | $5,843 | +$487 (+8.3%) | +$262 |
| Labour Day, 1 May | $2,232 | $1,831 | +$401 (+21.9%) | +$275 |

21 Mar was the worst Fitr day, **$911**. It is the third-lowest day in the half-year (181 days). The lowest day overall was 17 Jan, at $830, and it was not a holiday.

Adha is a small dip, not a surge. The old "+13.5%, no dip" figure was the six-month weekday average.

![Holiday revenue gap](../outputs/truck/figures/eid_holiday_dips.png)

Chain context, measured: 33,887 orders, $305,184 revenue, $178,994 gross profit, 1.59 items per order, branches Garden, Harbour, and Uptown.

## 3. The question

Customers leave Beirut and spend Eid with family. Fitr shows up in the branches. That raises a bigger question than "how do we patch a $923 hole": **should Stories go to its customers when they are not near a branch?**

Three answers, cheapest first.

## 4. Option 1: Eid boxes and a limited edition

Use pastries the branches already sell and that travel at room temperature. The mix is weighted by measured popularity times measured profit per unit.

**Box of 6:** one each of butter croissant, cinnamon roll, chocolate croissant, chocolate cookie, banana bread, almond croissant.

**Family box of 12:** two each of the first four, plus one banana bread, one almond croissant, one brownie, one pistachio cookie.

Price is the branch's list prices times **0.90** (a 10% box discount, an assumption). Cost is that branch's measured unit cost.

| Assembled at | Box of 6 price | Profit | Margin | Family box profit |
|---|---|---|---|---|
| Harbour | $24.09 | **$14.74** | 61.2% | **$28.76** |
| Uptown | $22.02 | $13.05 | 59.3% | $25.42 |
| Garden | $22.95 | $9.58 | 41.7% | $18.43 |

Garden's unit cost on these pastries is about **43%** above Harbour's, so a Garden box earns about **35%** less profit. Assemble at Harbour or Uptown.

The Fitr revenue gap is $923 (measured). Apply the chain's measured gross margin (58.7%) and the gross profit in that gap is about **$541** (estimate). Replacing it takes **37 Harbour boxes of 6**, or **19 family boxes**. A one-time **$500** for bags, cards, and a week of posts (assumption) is covered by **34 boxes of 6** or **18 family boxes**. If pre-orders do both, the programme is about **$41** ahead. That is a test, not a profit centre.

Limited edition, not in the file, all estimates, priced by analogy:

| Item | Priced like | Price | Profit |
|---|---|---|---|
| Ma'amoul (date, pistachio, or walnut) | Pistachio cookie | $3.51 | $2.17 |
| Pistachio baklava | Cinnamon roll | $5.24 | $2.73 |
| Rose-pistachio latte | Spanish latte | $6.06 | $3.81 |

Ma'amoul is the one product that serves both Eid and Easter. L'Orient Today records it as the Lebanese sweet for Easter and for both Eids. The same box can be offered again at Easter. Baklava and the rose-pistachio latte are seasonal add-ons with no Stories sales history.

How it sells: pre-order on WhatsApp or Instagram the week before Eid, pick up at any branch on the last days of Ramadan, and sell the limited edition in the branches during Eid week. Detail: [`outputs/truck/tables/eid_boxes.csv`](../outputs/truck/tables/eid_boxes.csv).

## 5. Option 2: a pop-up stand

One event, not a fleet. Beirut Holidays runs **16-28 Jul 2026** at Antelias-Naccache (13 days, from the calendar, sourced to Annahar).

Assumptions: a stand at **$100 a day**, two staff at **$40** each, a spare branch espresso machine at **$0**. Cash cost **$180 a day**. Break-even is **37 orders a day**, using the truck menu's estimated **$4.85** product profit per order. That is below Uptown's average, so it is a fair test. At Garden's order rate the 13 days net about **$1,550**. At Harbour's rate, about **$3,350**. Upfront is $0 in this model.

## 6. Option 3: a truck, at demand Stories has actually seen

The old 100 / 200 / 300 orders a day sit above any branch-day in the file. The scenarios now are measured:

| What the branches did | Orders per day |
|---|---|
| Uptown average | 35 |
| Garden average | 62 |
| Harbour average (busiest branch) | 90 |
| Harbour on Tuesdays | 137 |
| Best single branch-day in six months | 193 |

200 and 300 are labelled **STRETCH**. No Stories day has reached them.

A trading day, if the vehicle is owned: 2 x $40 staff + $40 fuel + $50 site + $30 misc = **$200**. Rent adds $150 for the vehicle and $40 for a generator: **$390**. Owned trucks also carry, per year, insurance $1,500, maintenance $2,000, storage $1,200, and straight-line depreciation over 5 years. Those four are assumptions. An unpaid travel day (staff + fuel, no sales) is in the model as a flag for trips outside Beirut. The numbers below leave it off.

Ticket **$7.50** and product profit **$4.85** per order are the truck menu (measured prices, times the measured 1.59 items per order).

At **44 trading days**:

| | Rent | Buy used | Buy new |
|---|---|---|---|
| Upfront | $1,500 | $51,300 | $59,299 |
| Break-even, orders/day | **80** | **111** | **119** |
| Net at Garden (62/day) | **-$3,992** | **-$10,592** | -$12,192 |
| Net at Harbour (90/day) | **+$2,107** | **-$4,493** | -$6,092 |
| Cash payback at Harbour | 0.7 years | 8.9 years | 10.3 years |

Renting at Garden-like demand loses money. At Harbour-like demand it is a small profit, about $2,100, close to break-even relative to the decision. Buying does not pay back within 2 years at Uptown, Garden, Harbour, or Harbour Tuesday. A used trailer needs about **183 orders a day** for 44 days to pay back in two years on a cash basis. That is above Harbour Tuesday and only just under the single best day the chain has ever had. Repeating that day all season is not a plan.

![Profit per day](../outputs/truck/figures/truck_profit_per_day.png)

![Payback](../outputs/truck/figures/truck_payback.png)

![Break-even](../outputs/truck/figures/truck_breakeven.png)

## 7. The four options side by side

![Channel comparison](../outputs/truck/figures/truck_channel_comparison.png)

| | Upfront | Cost per trading day | Break-even | Net, Garden-like | Net, Harbour-like | Risk | What a pass proves |
|---|---|---|---|---|---|---|---|
| Eid boxes | $500 | $0 extra | 34 boxes of 6 | $41 | $41 | Low | People will pre-order before they leave |
| Pop-up, 13 days | $0 | $180 | 37 orders/day | $1,550 | $3,353 | Medium | Off-site demand can clear a cheap day |
| Rent a truck, 44 days | $1,500 | $390 | 80 orders/day | -$3,992 | $2,107 | High | A mobile shop can hold Harbour-sized demand |
| Buy used, 44 days | $51,300 | $307 cash | 111 orders/day | -$10,592 | -$4,493 | Highest | Nothing yet |

The box "net" is the same in both columns on purpose. Boxes are not sold at a branch's orders-per-day. The $41 is what is left if pre-orders replace the Fitr profit gap and then pay the $500.

Ranking, in the order to try them: **boxes, pop-up, rent, buy.**

## 8. Where and when

Full rows: [`truck/holiday_calendar.csv`](../truck/holiday_calendar.csv). Rule on every row: **no stop under an evacuation order or active strikes.** Follow official guidance that week. A ceasefire date is not a permit. Ashoura (26 Jun) stays off the plan. A commercial truck is not appropriate on a mourning day.

2026, sourced:

- War from **2 Mar**. A 10-day cessation of hostilities from **16 Apr**. Reuters' 17 Apr explainer says Israeli forces were not required to leave the South.
- Anadolu: families no longer gathered in southern border villages for Eid al-Adha.
- Annahar: Ehdeniyat skipped, Beiteddine cancelled, Baalbek postponing, Byblos uncertain, Beirut Holidays moved to Antelias-Naccache for 16-28 Jul.

Do not send anything to Nabatieh, Tyre, or Baalbek-Hermel. Saida and Chtaura/Zahle are the safer names in the Eid note, and they have **no traffic source**. Batroun, Byblos, Faraya, and the mountain villages are the same: low confidence until someone checks them. There is no URL for the claim that southerners still went home for Eid in earlier wars. It is not a reason to deploy.

## 9. How we know if it works

Each stage runs only if the one before it passed.

**Stage 1. Boxes at the next Eid al-Fitr and Eid al-Adha.** timeanddate's tentative 2027 dates are **10-11 Mar** (Fitr) and **17-18 May** (Adha). Other calendars put Fitr on 9 Mar and Adha on 16 May. Confirm the moon-sighting announcement before opening pre-orders. **Go** if pre-orders cover the profit target: about **37 boxes of 6** (or **19 family boxes**) at Harbour, plus the **34 boxes** that pay back the $500.

**Stage 2. One pop-up.** A 2027 summer event, not a 2026 festival that has already been cancelled. Measure orders per hour and per day. **Go** if the stand holds at least the rent break-even, about **80 orders a day**. Clearing the pop-up's own 37 is not enough to justify a truck.

**Stage 3. Rent a truck for one summer season (44 days).** **Go to a purchase** only if it averages the two-year cash-payback level: about **183 orders a day** for a used trailer, over those 44 days. Harbour Tuesday (137) is not that level.

Before any out-of-Beirut stop, check Google Maps Popular Times and traffic for Batroun, Byblos, Saida, and Chtaura/Zahle on past holiday weekends, and keep the screenshots. Until those exist, those towns stay assumptions.

## 10. Measured vs estimated

| Figure | Kind |
|---|---|
| Fitr -$923 (-15.7%); Adha -$122 (-3.2%); 21 Mar at $911, third-lowest day | Measured |
| January-to-June revenue growth, 52.4% | Measured |
| 35 / 62 / 90 / 137 / 193 orders per day | Measured branch rates, not truck rates |
| Box mixes, branch list prices, branch unit costs, Garden's 43% cost gap | Measured |
| 10% box discount, $500 packaging, $541 profit in the Fitr gap | Estimate |
| Ma'amoul, baklava, rose-pistachio latte | Estimate, priced like a measured item |
| $180 pop-up day, $390 rent day, $200 owned day | Estimate. Verify locally |
| $1,500 / $51,300 / $59,299 upfront; insurance, maintenance, storage, 5-year depreciation | Estimate. US list prices at the low end, plus assumptions |
| 18, 44, and 80 trading days | 18 and 44 are counts from the calendar; 80 is not a sourced count |
| 200 and 300 orders a day | Stretch. Above any recorded Stories day |

## 11. Risks and what the file does not contain

- **Security.** The South and Baalbek stay out. See section 8.
- **The dip is small.** A bad Fitr is under $1,000 of revenue. It cannot pay for a trailer.
- **Permits.** $800 is the bottom of a US range that runs past $17,000. A Lebanese permit stack is not in the sources.
- **Wages, fuel, municipality fees, insurance, storage.** Not in the transaction file.
- **Cannibalisation.** Low if the customer was not going to a Beirut branch that day. The file cannot see that. Adha is the warning: the branches barely moved.
- **Travel days.** A trip outside Beirut costs a second day of staff and fuel with no sales. The tables above do not include it. Turn the flag on in `truck/truck_model.py` before pricing a Bekaa or coastal weekend.
- **Demand transfer.** Applying Harbour's 90 orders to a lay-by is an assumption, not a forecast.

## 12. Approaches rejected

- Buying a truck now.
- Pitching the truck as the fix for Eid. The hole is $923. The trailer is $51,300.
- Planning on 100, 200, or 300 orders a day. Stories has not had a branch-day that high. The best day was 193, once.
- The old six-month weekday baseline. It hid the Adha dip and flattered late spring.
- Deep-south deployment, Baalbek while its festival is postponing, Ehden or Beiteddine as 2026 festival stops, Easter 2026 (those dates were inside the war), and Ashoura.
