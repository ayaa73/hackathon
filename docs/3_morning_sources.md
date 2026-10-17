# Project 3 sources

Every external number used in Project 3, what it supports, and where it is used. Everything
else in Project 3 is either computed from `data/raw/stories_transactions.csv` (MEASURED) or a
labelled DESIGN choice / ASSUMPTION at the top of `morning/morning_offer.py`.

## Public holidays (office days)

- [HolidayDB, Lebanon public holidays 2026](https://holidaydb.com/guides/public-holidays/lebanon/2026):
  the Jan-Jun 2026 public holidays (Jan 1, Jan 6, Feb 9, Feb 14, Mar 20-23, Mar 25, Apr 3-6,
  Apr 10-13, May 1, May 3, May 10, May 25, May 27-28, Jun 17, Jun 26).
  Used in `morning/morning_supply.py`: 129 weekdays in Jan-Jun 2026, 16 of them public holidays,
  so **113 office days**, annualized to **226**. Jul-Dec holidays are assumed to be similar.

## Delivery costs in Beirut

- [Voxire, "Best Delivery Apps in Lebanon 2026: Toters vs Talabat" (May 6, 2026)](https://voxire.com/blog/delivery-apps-lebanese-stores-2026/):
  - courier services such as Wakilni charge restaurants about **$2-6 per delivery in Beirut**,
    used as the low / mid / high own-courier cost ($2 / $4 / $6);
  - delivery apps (Toters, Talabat) charge **22-30% commission** on order value (22-25% for a
    strong brand), used as the 22% and 30% app scenarios.
  A secondary source (a Lebanese e-commerce blog), not an official rate card: get a quote
  from a courier before launch.

## Loyalty programs

- [Square, "Coffee shop loyalty program" (Feb 2024)](https://squareup.com/us/en/the-bottom-line/reaching-customers/coffee-shop-loyalty-program):
  - 48% of food and drink businesses on Square Loyalty reward with a **free item**, which
    supports the "6th bundle free" design;
  - enrolled customers spend **1.67x** more than non-enrolled. This is a correlation (loyal
    customers are the ones who join), so it is **not** used in any estimate.

## Not sourced (and therefore not claimed)

- That office workers are Stories' morning customers: the data shows no weekday or office
  pattern, so this is a hypothesis for the test.
- Staff schedules and labour cost: not in the data. The data shows only that all branches
  trade from 7:00 every day.
