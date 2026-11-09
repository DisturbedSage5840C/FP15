# Post cleaning (counts only)

| Measure | Value |
|---|---|
| Raw cells after removing exact duplicates | 22023 |
| Exact duplicate cells removed within a leader | 0 |
| Cells with a relative age parsed to months | 20235 |
| Frequent lines no rule covers (see the git-ignored candidates file) | 20 |

Exact means the same text for the same leader. The earlier harmonise step used a looser key, so the count
here is a lower bound on repeated content.

## Interface-line rules

Applied rules write the new column `post_text_clean` only. Proposed rules are counted, not applied.

| Rule | Status | Lines | Cells |
|---|---|---|---|
| connection_marker | applied | 21386 | 20052 |
| follow | applied | 13064 | 12621 |
| see_more | applied | 5934 | 5099 |
| image_prompt | applied | 6563 | 3552 |
| age_line | applied | 23623 | 20235 |
| like_comment_repost_send | applied | 1870 | 187 |
| document_loading | applied | 197 | 197 |
| join | proposed | 169 | 166 |
| view_job | proposed | 239 | 116 |
| lone_dot | proposed | 773 | 354 |
| bare_digits | proposed | 7064 | 6748 |
| bare_host | proposed | 2298 | 2286 |

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
| English | 21926 |
| Hinglish | 25 |
| mixed | 62 |
| Hindi | 1 |
| other | 9 |

## Reaction count

| Measure | Cells |
|---|---|
| Cells ending in a number | 7048 |
| Of those, shape eligible (number alone on its own line, not year-like, no suffix, no age line) | 6685 |

The Step A human comparison is not confirmed (`reaction_check_confirmed` in configs/thresholds.yaml). Until it is confirmed every row is marked `unverified` and no count is read.

## Segmentation

The segmenter is written and tested but was not run on all cells. It waits for the human to confirm the 200-cell sample.
