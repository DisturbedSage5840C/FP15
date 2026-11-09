# Post cleaning (counts only)

| Measure | Value |
|---|---|
| Raw cells after removing exact duplicates | 26945 |
| Exact duplicate cells removed within a leader | 0 |
| Cells with a relative age parsed to months | 25157 |
| Frequent lines no rule covers (see the git-ignored candidates file) | 23 |

Exact means the same text for the same leader. The harmonise step already collapsed certain duplicates
(identical, prefix, same post URL with a trailing number) and kept every other row flagged, so the count
here is a lower bound on repeated content.

## Interface-line rules

Applied rules write the new column `post_text_clean` only. Proposed rules are counted, not applied.

| Rule | Status | Lines | Cells |
|---|---|---|---|
| connection_marker | applied | 26236 | 24886 |
| follow | applied | 17279 | 16814 |
| see_more | applied | 6369 | 5528 |
| image_prompt | applied | 6904 | 3741 |
| age_line | applied | 28620 | 25157 |
| like_comment_repost_send | applied | 1879 | 190 |
| document_loading | applied | 214 | 214 |
| join | proposed | 172 | 169 |
| view_job | proposed | 257 | 125 |
| lone_dot | proposed | 1067 | 434 |
| bare_digits | proposed | 7660 | 7340 |
| bare_host | proposed | 2395 | 2383 |

## Age

Relative age (for example 5yr, 3mo) is turned into months as a number. It is not turned into a date: the
scrape date is unknown.

## Language flag

Method: script-based. Devanagari and Latin letters are counted; fewer than 20
letters gives `other`; a minor script above 20% of letters gives `mixed`.

Possible Hinglish (Hindi written in Latin letters): a cell that is mostly Latin letters is flagged
`Hinglish` when at least 3 of its Latin-letter words, and at least 10% of them, are on a list of common romanised Hindi function words
(src/hinglish.py). The list holds pronouns, particles, postpositions, auxiliaries, conjunctions and question
words only, no names and no post text. Words that are also common English words are left off, so some
Hinglish is missed. The flag is a counting rule, not a reading of the text.

| Flag | Cells |
|---|---|
| English | 26837 |
| Hinglish | 29 |
| mixed | 69 |
| Hindi | 1 |
| other | 9 |

## Reaction count

| Measure | Cells |
|---|---|
| Cells ending in a number | 7733 |
| Of those, shape eligible (number alone on its own line, not year-like, no suffix, no age line) | 7269 |

The Step A human comparison is not confirmed (`reaction_check_confirmed` in configs/thresholds.yaml). Until it is confirmed every row is marked `unverified` and no count is read.

## Segmentation

The segmenter is written and tested but was not run on all cells. It waits for the human to confirm the 200-cell sample.
