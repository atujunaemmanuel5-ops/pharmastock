# PharmaStock AI - Project Scope (v2)

Version: 26 October 2026 (Day 3). Items marked **[CONFIRM]** must be checked and filled in by me before this scope is final.

## 1. Problem and users

Small pharmacies lose money and put patients at risk in four ways: they run out of medicines, they overstock, stock expires unsold, and restricted or dangerous items can be sold at the counter without a check. PharmaStock AI is a decision-support tool for a pharmacy owner, stock manager or dispenser. It forecasts demand, flags stockout and expiry risk, suggests reorders, and checks a dispensing cart for prescription rules and drug interactions.

It supports a licensed dispenser. It does not replace one.

## 2. What the system does

1. **Forecast and reorder.** A 7-day demand forecast per ATC product group, a stockout-risk level, a reorder point and a suggested reorder quantity.
2. **Fast-moving tracking.** Drugs ranked Fast, Medium or Slow from recent sales, with a trend.
3. **Expiry tracking.** Batches with expiry dates, no sale of expired stock, earliest-expiry-first picking, and units likely to expire unsold.
4. **Prescription gate.** Prescription-only drugs (for example misoprostol) cannot be dispensed without a prescription reference. Every attempt is logged.
5. **Interaction checker.** Every pair in a cart is checked, and the system gives a stop, a warning or a duplication alert.
6. **Ask assistant (RAG).** Answers questions and explains alerts from a small set of cited documents. It says "not found" when it has no source.
7. **Dispense console and audit log.** One screen to build a cart, see the decision, and confirm.

Rule: **rules decide, AI explains.** Blocking or warning comes from tested lookup rules. The assistant never allows or blocks a sale.

## 3. Real or simulated

| Item | Status |
|---|---|
| Daily sales per ATC group (Kaggle) | Real |
| Drug-level sales, stock on hand, batches, expiry dates, lead times | SIMULATED, built on the real group-level series with a fixed random seed |
| Prescription rules | From cited sources; only misoprostol has a source so far; the rest need pharmacist verification **[CONFIRM]** |
| Interaction data | DDInter once imported; the placeholder file is development-only and not clinical data |
| Assistant documents | Published guidelines and labels, cited by page |
| Patient data | None; demo carts only |

Everything simulated carries `is_simulated = true` and a visible SIMULATED badge. I will never say the system "predicts real stockouts"; I will say "stockout risk under simulated inventory".

## 4. Data decisions from the Day 2 inspection

**Main source: `salesdaily.csv`.** It has 2,106 rows from 2014-01-02 to 2019-10-08, one row per day, no absent days, no missing values, no duplicate dates and no negatives. Columns: `datum`, eight ATC groups (M01AB, M01AE, N02BA, N02BE, N05B, N05C, R03, R06), and `Year`, `Month`, `Hour`, `Weekday Name`.

- **Date format.** `datum` is month/day/year without zero-padding (`1/2/2014`). It will be parsed with an explicit format (`%m/%d/%Y`). The `Weekday Name` column confirms this reading (2 January 2014 was a Thursday).
- **Dropped columns.** `Year`, `Month` and `Weekday Name` can be rebuilt from the date. `Hour` is an artifact: it equals 276 (the sum of 0 to 23) on almost every row, so the daily file was made by adding up the hourly file.
- **Partial days.** The first day (2014-01-02) starts at 08:00 and the last day (2019-10-08) ends at 19:00 in the hourly file. Provisional decision: drop 2019-10-08 from the processed data; decide on 2014-01-02 on Day 5 **[CONFIRM]**.
- **Zeros are recorded values.** There are many zero days (N05C 1,430 of 2,106; R03 484; R06 256; the others between 26 and 78). The hourly file has every hour present, so zeros mean "no sales recorded", not "data lost". I will check whether any days are zero for all groups (possible closures) before the final decision **[CONFIRM]**.
- **Fractional values.** Values like 3.67 mean the unit is not a clean count, so the target is called "sales volume".
- **Daily versus monthly files.** They agree on most months, with a median ratio of 1.0, but some differ (for example N05C in 2014-01 at 0.60 and R03 in 2019-09 at 0.754). Recorded as a limitation; the daily file is the source **[CONFIRM full list]**.
- **One pharmacy.** The data is described as coming from one pharmacy; I could not verify this **[CONFIRM on the Kaggle page]**.
- **Licence.** **[CONFIRM and paste the exact licence text from the Kaggle page.]** Raw files are not committed to GitHub; the README credits the dataset.
- **Processed output.** Long format (`sale_date`, `product_group`, `quantity`), saved in `data/processed/`.

## 5. Targets and evaluation

- **Target:** daily sales volume per ATC group. **Horizon:** 7 days.
- **Baselines:** seasonal-naive (same weekday last week) and a 7-day moving average.
- **Model:** one scikit-learn model with lag and calendar features, only if it clearly beats the baselines; otherwise baselines are shipped and the result is reported honestly.
- **Metric:** MAE, with a chronological split (never random) and identical test windows for every method. Test period and minimum history rule are fixed on Day 8.
- **Known difficulty:** some groups, especially N05C, are intermittent (mostly zeros), so MAE will look small and baselines may be hard to beat. This will be stated in the evaluation.

## 6. In scope

Must: prescription gate, interaction checker, expiry rules, baseline forecast with reorder logic, dispense log, real-vs-simulated labels, deployed API health check plus a working local fallback, README with limitations.

Should: one ML model compared with baselines, velocity trend, units at risk of expiring, assistant with citations, CSV report, automated tests of the rules.

Could (cut first): vector retrieval, LLM-written answers, patient-flag contraindications, CSV upload endpoint, PDF report.

## 7. Out of scope

Deep learning, Docker, authentication, real pharmacy-system integrations, real patient data, live e-prescription verification, and any claim of clinical accuracy.

## 8. Constraints

- Free tiers only (GitHub, Neon, Render, Streamlit Community Cloud). No paid services.
- Build ends Thursday 19 November; submission Friday 20 November 2026.
- Hackathon deadline and demo length: **[CONFIRM from the hackathon rules]**.
- First end-to-end project, so a thin working version comes first (a blocked cart on the deployed API by 11 November).

## 9. Safety and limitations

- Decision support only; a licensed pharmacist makes the final call.
- The prescription gate checks that a reference was entered. It cannot verify that the prescription is genuine.
- "No interaction found" does not mean "safe".
- Forecasts are estimates from historical data, and drug-level numbers are simulated.
- Prescription rules and interaction results must be verified by a pharmacist before any demonstration.

## 10. Definition of done

1. The raw file loads and is validated; broken copies fail with clear messages.
2. The processed file has one row per date per product group, with no gaps or duplicates, and reloads correctly.
3. Baselines and (if kept) one ML model are compared with MAE on identical chronological windows.
4. Inventory and expiry formulas match two hand-worked examples, and edge cases do not crash.
5. A cart with misoprostol and no prescription is blocked, and the same cart with a prescription reference is allowed.
6. An expired batch is never offered; the earliest unexpired batch is suggested.
7. A known major interaction produces a stop and a moderate one a warning; the worst result in a cart wins.
8. The assistant returns a citation, or says "not found".
9. The API and dashboard work from a cart check to a downloaded report, locally and deployed (or locally with screenshots if deployment fails).
10. The README states what is real, what is simulated, the data credits and licence, the evaluation results, and the limitations.
