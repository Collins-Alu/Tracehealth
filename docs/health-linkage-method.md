# How TraceHealth links pollution reports to clinic visits

This page explains, in plain language, what the health-linkage engine
(`backend/app/services/linkage_engine.py` and `linkage_stats.py`) calculates,
why, and what it can and cannot tell you.

> **Every result is a statistical association. It is never evidence that the
> pollution caused anyone's illness.** The dashboard repeats this beside every
> result, and the API includes it in every linkage response.

## The question

For each **verified** pollution report: *at clinics near this report, did visits
for the health conditions usually linked to this kind of pollution go up in the
weeks after the report, compared with the weeks before it?*

Unverified, rejected and flagged reports are never linked (enforced by a
database trigger as well as in the code).

## Step by step

| Step | What happens | Setting (default) |
|---|---|---|
| 1. Nearby clinics | Every facility within the radius of the report, measured on the earth's surface (PostGIS). | `linkage.radius_km` (3 km) |
| 2. Conditions to check | Taken from the category mapping, e.g. open burning → respiratory. | `linkage.category_mapping` (D9) |
| 3. Baseline window | Clinic periods that **end** in the weeks before the report date. | `linkage.baseline_weeks` (8) |
| 4. Follow-up window | Clinic periods that **start** on or after the report date, within the follow-up weeks. | `linkage.followup_weeks` (4) |
| 5. Rates | Visits ÷ days of data in each window, so weekly and monthly counts mix fairly. | |
| 6. Rate ratio | follow-up rate ÷ baseline rate. 1.0 = no change; 1.8 = 80 % more visits per day. | |
| 7. p-value | Exact one-sided test (below). Small = a rise this big is unlikely to be chance alone. | |
| 8. Status | See the table below. | `linkage.p_value_threshold` (0.05) |
| 9. Correlation | Spearman correlation, for description only (below). | |

Whole clinic periods are assigned to a window, never split. The one period that
contains the report date mixes "before" and "after", so it is left out of both
windows (it is still used for the correlation).

### Status

| Status | Meaning |
|---|---|
| `INSUFFICIENT_DATA` | Less than half of either window is covered by clinic data, or the baseline has fewer visits than `linkage.min_baseline_visits` (10). **No statistics are produced**; the reason is stored and shown ("too little clinic data before the report", etc.). Nothing is guessed or filled in. |
| `SIGNAL` | Rate ratio above 1 **and** p-value below the threshold. Shown in amber on the dashboard. |
| `NO_SIGNAL` | Enough data, but no clear rise. |

## The statistical test

Clinic visits are counts, so they are modelled as Poisson counts. If the daily
visit rate were the same before and after the report, then out of the total
`N = x_f + x_b` visits, the share falling in the follow-up window would follow a
binomial distribution with probability

    p0 = t_f / (t_f + t_b)        (t = days of data in each window)

The p-value is `P(X ≥ x_f)` for `X ~ Binomial(N, p0)`: the chance of seeing at
least this many follow-up visits if nothing had changed. This is the standard
exact *conditional test for two Poisson rates*. It is computed in log space
(`linkage_stats.poisson_rate_test_greater`) so very large counts do not
underflow.

**Validation.** During development the function was compared with SciPy's
`scipy.stats.binomtest(..., alternative="greater")` over a grid of counts and
window lengths; the largest difference was about 9 × 10⁻¹³. SciPy is not a
runtime dependency: the code is short enough to read and check line by line.
Unit tests in `backend/tests/unit/test_linkage_stats.py` pin known values.

## The correlation score

For each linkage, TraceHealth also computes a Spearman rank correlation, across
all clinic periods in both windows, between the number of verified reports of
that category near the clinic and the clinic's visits per day for the
condition. It needs at least 4 periods, otherwise it is left empty.

It is **descriptive only** and never decides the status, for two reasons:

- **Lag.** Health effects usually follow exposure by days or weeks, while the
  report falls in a single period. A real rise that comes *after* the reports
  can therefore produce a small or even negative same-period correlation.
- **Few points.** With a handful of periods, correlations swing widely.

## What the results cannot tell you

- **Causation.** Other things change at the same time: seasons (rains bring
  malaria and diarrhoeal illness), outbreaks, clinic opening hours, stock-outs,
  health campaigns, people choosing a different clinic.
- **Who was affected.** Data are aggregated counts per clinic, condition and
  period. There is no patient-level data, by design (data-protection.md).
- **Small numbers.** A rise from 3 to 7 visits can be "significant" while
  meaning little for planning. The dashboard hides counts under 5.
- **Many tests at once.** Every report × clinic × condition is a separate test.
  At p < 0.05, about 1 in 20 tests on unchanged data will show a SIGNAL by
  chance. Treat a single SIGNAL as a prompt to look closer. Clusters (several
  verified reports near one clinic with signals for the same condition) are
  more informative, which is why the dashboard lists them separately.
- **Overlapping evidence.** Reports close together in place and time share the
  same clinic data, so their results are not independent.

## Reproducibility

Every linkage row stores:

- `params_snapshot`: the method version (`poisson_rate_ratio_v1`) and every
  setting used;
- the counts, days, rate ratio, p-value and correlation;
- links to the exact clinic summary rows used (`health_linkage_evidence`,
  marked BASELINE or FOLLOWUP).

Results are recalculated automatically after a clinic import, after each
verification, and when an administrator changes a linkage setting, so the
dashboard always reflects the current data and settings. The old rows are
replaced, not kept side by side.

## Suggested review with the partner clinic before the pilot

1. Confirm the category → condition mapping (D9).
2. Agree the radius for the pilot area (dense informal settlements may need
   less than 3 km).
3. Agree the baseline and follow-up windows, considering seasonal patterns.
4. Decide who looks at SIGNALs and what they do next.
