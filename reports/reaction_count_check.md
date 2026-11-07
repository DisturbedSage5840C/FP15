# Reaction-count check

Counts from raw post cells already in data/interim. Nothing was downloaded.

| Measure | Count |
|---|---|
| Raw cells | 22,023 |
| End in a number | 7,048 |
| Number alone on its own line | 6,685 |
| Number inside a hashtag | 12 |
| Number after a space on the same line | 70 |
| Number glued to a word | 261 |
| Number after punctuation | 20 |
| Year-like (4 digits, 1900 to 2035) | 169 |
| Year-like and alone on its own line | 0 |
| Relative-age line right before the number (like 5yr) | 0 |
| Text ends in a relative-age token (like 5yr) | 1 |
| Number with a K or M suffix | 4 |
| Cleaned cells that end in a number | 0 of 26,088 |

## Sampling frame

| Measure | Count |
|---|---|
| Own-line cells with a link | 2,754 |
| Leaders with such a cell | 378 |
| Cells with a link that do not end in a number | 241 |
| Leaders with such a cell (control) | 85 |
| Drawn: number alone on its own line | 40 |
| Drawn: control | 10 |

## Pairing rules

- A cell is one raw post cell (text_kind = raw). Cleaned cells are only counted for comparison.
- Ends in a number: the text, after trimming blanks, ends in a digit-led token (digits, thousand commas, one decimal part, optional K or M).
- Alone on its own line: the last line holds only that token.
- In a hashtag: the last word starts with #.
- After a space, glued to a word, after punctuation: what sits right before the token.
- Year-like: exactly 4 plain digits between 1900 and 2035.
- Relative-age line: the nearest non-blank line above the number is a token like 5yr, 3mo, 2w, 1d or 4h.
- Relative-age token at the end: the text itself ends in such a token.

## Sample

- Eligible: has a post link and a leader name (sample only; the counts above use all raw cells).
- Groups: 40 with the number alone on its own line, 10 that do not end in a number (control).
- Sample: one cell per leader; each leader appears once.
- Seed: 20261107
- The sample file is git-ignored. It holds leader ids, links and refs, and no parsed number.
- This report does not decide what the number means. A human compares the sample with LinkedIn.
