# Event Table Specification

## File

`data/events/fomc_events_2011_2018.csv`

## Required Columns

| Column           | Type       | Description                                      |
|------------------|------------|--------------------------------------------------|
| `date`           | YYYY-MM-DD | Calendar date of the FOMC announcement            |
| `has_press_conf` | 0 or 1     | 1 if the meeting included a press conference      |
| `year`           | integer    | Year of the announcement (convenience column)     |

## Notes

- All dates must be valid US trading days (the VIX market was open).
- The file covers FOMC meetings from January 2011 through December 2018.
- Each row represents one FOMC announcement; there are 8 meetings per year (64 total).
