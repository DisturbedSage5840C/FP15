# Extra text features

Computed from raw post cells already in data/interim. Nothing was downloaded or scraped.
The counts describe the text in a cell, not the person; any claim built on them is about the image projected in public posts.
They are cell-level: a cell can still hold page chrome and several author blocks until segmentation exists.

## Rules

| Feature | Rule | Verdict | Caveat |
|---|---|---|---|
| Length (characters, words) | Count of characters and whitespace-separated words after trimming. | Computable now, but cell-level | Reliable per post only after segmentation. |
| Hashtags | A # followed by letters or digits, not glued to a word or inside a web address. | Reliable now | Digit-only tags are counted apart. |
| Mentions | An at-sign followed directly by a name, outside web addresses and email addresses. | Undercount | Copied text often drops the at-sign; stray at-signs are counted apart. |
| Links | A scheme address, a www address, or a known short-link host; bare domains are a rough extra count. | Reliable for the first group | Bare domains can match file names. |
| Question marks | Count of the question mark outside web addresses; runs such as ?? are counted apart. | Reliable now | Does not separate questions from emphasis. |
| Emoji | Pictographic characters, with flags, keycaps and joined sequences counted once each. | Reliable for the pictographic core | Arrows, ticks and similar symbols are reported apart. |
| Hinglish share | Devanagari word tokens, plus romanised Hindi markers from a fixed word list. | Devanagari reliable; romanised list unvalidated | The word list needs mentor approval. |
| Repost vs own text | Flags only: a line that is exactly Repost, an engagement phrase line, the word reposted. | Not computable before segmentation | Which part of a cell is the leader's own needs segmentation. |

## How common each feature is

| Measure | Count |
|---|---|
| Raw cells analysed | 26,945 |

| Feature | Cells with at least one | Share of raw cells | Median among those |
|---|---|---|---|
| hashtags | 1,974 | 7.3% | 2 |
| numeric_hashtags | 136 | 0.5% | 1 |
| mentions | 518 | 1.9% | 1 |
| stray_at | 3,491 | 13.0% | 1 |
| urls | 2,682 | 10.0% | 1 |
| bare_domains | 2,625 | 9.7% | 1 |
| question_marks | 3,052 | 11.3% | 1 |
| question_runs | 63 | 0.2% | 1 |
| emoji | 3,859 | 14.3% | 2 |
| symbols | 270 | 1.0% | 3 |
| devanagari_tokens | 317 | 1.2% | 13 |
| roman_markers | 455 | 1.7% | 1 |
| follow_lines | 16,814 | 62.4% | 1 |
| repost_line | 188 | 0.7% |  |
| repost_phrase | 10 | 0.0% |  |
| repost_word_in_text | 19 | 0.1% |  |

| Length | Median | 90th percentile | Maximum |
|---|---|---|---|
| chars | 466 | 1,512 | 32,766 |
| words | 72 | 232 | 5,228 |

## Where the rules handle text badly

Up to 10 example cells per kind, drawn with seed 20261107. The cell refs and leader ids are in data/derived/extra_features_examples.csv, which is git-ignored because the repository is public.

### length_several_blocks

Two or more Follow lines mean the cell holds several author blocks, so its length is not one post's length.

| Measure | Count |
|---|---|
| Cells matching | 124 |
| Examples written | 10 |

### hashtag_numeric_only

A hashtag made only of digits (for example a ranking) is not a topic tag and is counted apart.

| Measure | Count |
|---|---|
| Cells matching | 136 |
| Examples written | 10 |

### mention_stray_at

An at-sign not followed by a name (a time, a place) is not a mention; mentions are also undercounted because copied text often drops the at-sign.

| Measure | Count |
|---|---|
| Cells matching | 3,491 |
| Examples written | 10 |

### url_bare_domain

A web address written without a scheme or www is only caught by the rough bare-domain rule, and the rule can also match a file name or an abbreviation.

| Measure | Count |
|---|---|
| Cells matching | 2,625 |
| Examples written | 10 |

### question_runs

Runs such as ?? or ?! are counted as one run each, so the plain question-mark count mixes questions and emphasis.

| Measure | Count |
|---|---|
| Cells matching | 63 |
| Examples written | 10 |

### emoji_symbol_only

Arrows, ticks and similar text-style symbols are counted apart from emoji; whether they count as emoji is a choice.

| Measure | Count |
|---|---|
| Cells matching | 128 |
| Examples written | 10 |

### hinglish_borderline

One or two romanised Hindi marker words and no Devanagari: some are English words too, so the share is unreliable.

| Measure | Count |
|---|---|
| Cells matching | 310 |
| Examples written | 10 |

### repost_word_in_running_text

The word reposted appears inside a sentence without a repost line, so it may be the writer's own wording.

| Measure | Count |
|---|---|
| Cells matching | 9 |
| Examples written | 9 |

## Needs a human decision

- Approve, change or drop the romanised Hindi word list. It is an unvalidated proposal.
- Decide whether text-style symbols (arrows, ticks) count as emoji.
- Decide whether bare domains count as links.
- Decide whether to wait for segmentation before using length or repost features in any analysis.
