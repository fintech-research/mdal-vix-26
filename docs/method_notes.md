# Method Notes

## Event-Time Indexing

Event time is measured in **trading days** relative to the FOMC announcement date (t0).

- t0 is the calendar day of the announcement.
- Trading-day positions are determined from the VIX price series (days where the market is open and VIX has a closing price).
- The event window spans t = -10 to t = +10 trading days around t0.

## VIX Log Change (r_t)

Daily VIX returns are computed as close-to-close log changes:

```
r_t = log(VIX_t) - log(VIX_{t-1})
```

This uses the daily closing level of the CBOE VIX index.

## Cumulative Abnormal Returns (CARs)

CARs are cumulative sums of daily log changes over specified horizons:

```
CAR(a, b) = sum of r_t for t = a to t = b
```

Primary horizons:
- **CAR(0,1)** — announcement day plus one day
- **CAR(0,2)** — announcement day plus two days
- **CAR(0,5)** — announcement day plus one week

## Press-Conference Split

Events are split by whether the FOMC meeting included a press conference (`has_press_conf = 1`) or not (`has_press_conf = 0`). The effect is tested via:

1. Difference in mean CARs between the two groups.
2. OLS regression: `CAR_i(a,b) = alpha + beta * PressConf_i + epsilon_i`
