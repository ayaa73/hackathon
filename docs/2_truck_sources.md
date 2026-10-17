# Truck business case: sources

Every URL used in `truck/holiday_calendar.csv`, `truck/truck_model.py`, and `docs/2_holiday_truck.md`. If a destination or a Lebanon price has no URL, the calendar marks it `confidence = low` and the model tags it `ASSUMPTION - verify locally`. Nothing below is a made-up link.

Measured sales figures are not from a webpage. They come from `data/raw/stories_transactions.csv` (Jan-Jun 2026), after `src/clean.py` drops 132 exact duplicate rows.

## Holiday dates

- [HolidayDB, Lebanon public holidays 2026](https://holidaydb.com/guides/public-holidays/lebanon/2026) supports the dates: 1 Jan New Year, 6 Jan Orthodox Christmas, 9 Feb St Maron, 20-23 Mar Eid al-Fitr, 25 Mar Annunciation, 3-6 Apr Good Friday through Easter Monday, 10-13 Apr Orthodox Easter, 1 May Labour Day, 25 May Liberation Day, 27-28 May Eid al-Adha, 26 Jun Ashoura, 15 Aug Assumption, 25 Dec Christmas.
- St Maron, Annunciation, Labour Day, and Liberation Day are on that list and are **not** truck days in this plan. They are recorded here so the date list is complete.

The 18-day "holidays only" scenario is the sum of the dated rows we would even consider, before the 2026 security cut: Eid al-Fitr 4 + Eid al-Adha 2 + New Year / Orthodox Christmas / Christmas 3 + Easter 4 + Orthodox Easter 4 + Assumption 1 = **18**. Ashoura is not included.

The 44-day scenario adds Jul-Aug 2026 Fridays, Saturdays, and Sundays (27 days) and does not double-count Saturday 15 Aug, which is already in the 18: 18 + 27 - 1 = **44**. The 80-day scenario is **not** a count of sourced dates. It is a planning assumption for a longer mix of holidays, weekends, and events.

## Security and where people actually were in 2026

- [Reuters, 16 Apr 2026](https://www.reuters.com/world/middle-east/trump-says-lebanese-israeli-leaders-will-speak-2026-04-16/) supports the war timing: Lebanon was drawn in on **2 Mar 2026**, and a 10-day ceasefire was agreed on **16 Apr 2026**.
- [US State Department, 16 Apr 2026](https://www.state.gov/releases/office-of-the-spokesperson/2026/04/ten-day-cessation-of-hostilities-to-enable-peace-negotiations-between-israel-and-lebanon) is the text of that cessation of hostilities, starting 16 Apr 2026 at 17:00 EST.
- [Reuters explainer, 17 Apr 2026](https://www.reuters.com/world/middle-east/whats-lebanon-ceasefire-deal-will-it-hold-2026-04-17/) supports a limit on the "ceasefire" word: the deal did **not** require Israeli forces to leave southern Lebanon. The South is not treated as a truck destination after 16 Apr.
- [Anadolu Agency](https://www.aa.com.tr/en/world/-families-no-longer-gather-war-overshadows-eid-al-adha-in-south-lebanon/3949449) supports the Eid al-Adha finding: in southern border villages (the piece names Shebaa, Kfarhamam, and Marj al-Zouhour), families no longer gathered for the holiday. This is why Nabatieh, Tyre, and the rest of the border South are out of the plan.
- [Annahar, page dated 12 Jun 2026](https://www.annahar.com/lifestyle/arts/319317/%D8%B5%D9%8A%D9%81-%D8%A7%D9%84%D9%85%D9%87%D8%B1%D8%AC%D8%A7%D9%86%D8%A7%D8%AA-%D8%A7%D9%84%D8%BA%D8%A7%D8%A6%D8%A8-%D9%87%D9%84-%D9%8A%D8%A8%D9%82%D9%89-%D9%84%D8%A8%D9%86%D8%A7%D9%86-%D8%B9%D9%84%D9%89-%D8%AE%D8%A7%D8%B1%D8%B7%D8%A9-%D8%A7%D9%84%D9%81%D8%B1%D8%AD) (the English Annahar index lists the same story on 13 Jun 2026) supports the festival status: Ehdeniyat absent in 2026, Beiteddine cancelled, Baalbek moving toward postponement, Byblos not cancelled but without its international programme and waiting on security, Beirut Holidays moved to Antelias-Naccache and running **16-28 Jul 2026**.
- [Annahar, 12 Jun 2026, on Baalbek](https://www.annahar.com/lifestyle/arts/319602/%D9%85%D9%87%D8%B1%D8%AC%D8%A7%D9%86%D8%A7%D8%AA-%D8%A8%D8%B9%D9%84%D8%A8%D9%83-%D8%AA%D8%A4%D8%AC%D9%84-%D8%B9%D8%B1%D9%88%D8%B6-2026-%D9%86%D8%A3%D8%B3%D9%81-%D9%84%D8%A7%D8%AA%D8%AE%D8%A7%D8%B0-%D9%87%D8%B0%D8%A7-%D8%A7%D9%84%D9%82%D8%B1%D8%A7%D8%B1) supports the later confirmation that Baalbek International Festival postponed its 2026 summer shows because of the security and political situation.

No URL in this file supports Faraya, Kfardebian, Jounieh, Byblos-as-a-market, Batroun, Ehden weekend traffic, Mount Lebanon villages, or Chtaura/Zahle as measured truck sites. Those rows stay low confidence.

## Truck cost (US listings, not Lebanon quotes)

- [Zion Foodtrucks](https://zionfoodtrucks.com/how-much-does-a-coffee-truck-cost/) supports the ranges used as bounds, not as a Lebanon invoice: used outfitted trailer $30k-60k; new custom coffee trailer $40k-55k; new truck from $55k; espresso machine $5k-25k (entry 2-group about $5.5k); grinder $1.5k-4k; fridge $1.5k-4k; generator $2k-8k; full equipment package $15k-40k; wrap $2.5k-5k; permits about $800-17k+; opening inventory $3k-5k; strong operators $14k-21k per month in sales, keeping 15-25% profit.
- [HorecaStore](https://www.thehorecastore.com/food-trailers-and-trucks/coffee-truck) supports the new-trailer price: a 14-ft fully equipped coffee trailer at **$49,999**, plus shipping. Shipping is not priced on that page. This case uses $3,000 shipping and labels it an assumption.

The model takes the **low end** of the Zion ranges where it needs a single number (used trailer $30,000, equipment package $15,000, wrap $2,500, permits $800, opening inventory $3,000, machine $5,500, grinder $1,500). That is optimistic. Lebanon permits, fuel, wages, and municipality fees are not on either page.

## Ma'amoul, and why one pastry covers Eid and Easter

- [L'Orient Today](https://today.lorientlejour.com/cooking-food-lebanon/1334757/for-the-love-of-maamoul-from-gold-coins-to-nutella.html) supports the product, not a price. Ma'amoul fillings in Lebanon are pistachios, walnuts, and dates. The same piece quotes a historian that ma'amoul is the sweet typical of Christian Easter and of Eid al-Fitr and Eid al-Adha, and that it keeps for weeks because it is baked. There is no Stories price for ma'amoul in the transaction file. The model prices it like a pistachio cookie and labels that an estimate.

## 2027 dates for the next test

Lunar holidays move, and the calendars do not agree yet. Both of these are provisional:

- [timeanddate, Lebanon 2027](https://www.timeanddate.com/holidays/lebanon/2027) lists Eid al-Fitr as a tentative public holiday on **10-11 Mar 2027** and Eid al-Adha as a tentative public holiday on **17-18 May 2027**.
- [PublicHolidays.me](https://publicholidays.me/lebanon/eid-al-fitr/) lists Eid al-Fitr 2027 as **9 Mar**. [Egazat](https://egazat.com/en/eid/2027.html) lists Lebanon's Eid al-Adha 2027 as **16-17 May**.

The validation plan uses the timeanddate window and says to confirm the moon-sighting announcement before pre-orders open. No source here is an official Lebanese decree for 2027.

## Not a source

A recall that southerners still went home for Eid in earlier wars has **no URL** in the material used here. It is not treated as evidence and it is not a reason to send a truck south in 2026. The sourced 2026 account is the Anadolu piece above.

Google Maps Popular Times for Batroun, Byblos, Saida, and Chtaura/Zahle is a check still to be done. It is not a source until someone saves the screenshots.
