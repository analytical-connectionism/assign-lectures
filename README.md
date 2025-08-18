# Scribe Assignment Tool

Assigns scribes to lecturers using stable matching (Gale-Shapley algorithm).

## Usage

```bash
uv run --script assign_lectures.py scribe_preferences.csv -q lecturer_quotas.csv
```

## CSV Formats

**scribe_preferences.csv**
```
scribe_name,1st_choice,2nd_choice,3rd_choice
Alice,Prof_A,Prof_B,Prof_C
Bob,Prof_B,Prof_A
```

**lecturer_quotas.csv**
```
lecturer_name,quota
Prof_A,2
Prof_B,3
```

## Options

- `--quiet`: Show only final results
- `--lecturer-preferences FILE`: Optional lecturer preference rankings, similar to scribe preferences.
