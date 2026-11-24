# FP15 pre-registration DRAFT

Status: **DRAFT, AI-assisted, PROVISIONAL, pending human confirmation.** This is not the G3 lock. No gate is signed by this document.

## Research question and claim limit

How do Indian corporate leaders present themselves in LinkedIn posts, and does the presentation differ by leader profile: Founder-CEO versus Professional CEO, title family, gender as coded, sector and firm size?

Every claim is about the image projected in public posts. The study does not measure or label a leader's personality. The I-rate is one signal only, not a narcissism score. No causal claim is planned.

## Data and analysis population

- The study remains limited to the Indian corporate leaders already in the supplied data; scraping, new post-data downloads and any expansion remain unapproved.
- The retained leader master is the union of post sheets, roster, summaries and Company_Data. Nothing about leaders without posts changes the post-based analysis population.
- The post-based analysis uses leaders represented in post sheets. Until G1 is human-confirmed, cleaned raw cells stand in for posts.
- The main leader minimum is 15 raw post cells, read from `configs/thresholds.yaml`. Missing values stay missing; no label or firm value is inferred.
- Founder-CEO and Professional CEO are the only ceo_type groups in their two-group contrast. Blank, conflicting and unrecognised ceo_type values are not placed in either group.

## Measures

The currently implemented provisional measures are English-only first-person singular and plural rates per 100 words (I-rate and we-rate). Zero-word cells are missing, not zero. Results are shown for all cells and without possible-Hinglish cells; the possible-Hinglish mark is not yet human-validated.

No trait dictionary for the five Northouse traits is currently an implemented measure. No new trait dictionary or word list is specified here.

OPEN: needs mentor decision on the final pronoun counter, any trait dictionaries, embeddings, topics, classifiers, and all additional exploratory constructs.

## DRAFT hypotheses and planned tests

This draft records the current Step 14C comparison structure; it does not turn exploratory results already run into confirmatory findings.

1. **Founder-CEO versus Professional CEO.** For each provisional rate, fit the two-group contrast as Professional CEO minus Founder-CEO. The without-sector model adjusts for ceo_type, title family, gender as coded and firm-size band. A second model adds sector, pooling sectors below the existing model-size rule and omitting leaders whose sector is unavailable for that model.
2. **Title family and firm size.** For each provisional rate, use joint Wald tests for title family and firm-size band in the same models. These are exploratory unless a human locks them before a future confirmatory run.
3. **Other factors.** Gender as coded and sector are included as model factors under the existing Step 14C rules. No directional hypothesis for them is locked in this draft.

The models use REML random intercepts for leader, with cells nested in leaders. The report gives two-group estimates and normal-approximation intervals; joint tests have no signed estimate.

## Multiple testing and robustness

- Benjamini-Hochberg is the configured correction method. The configured FDR level is 0.05.
- For this DRAFT, a result meets the statistical threshold only when its BH-adjusted p is at or below the configured FDR level. A result above that threshold is reported as not meeting the threshold, not as evidence of no difference.
- The Step 14D multiverse is exploratory: 3 post minimums (10, 15 and 16), 3 outcome scales (raw rate, `log(1 + rate)`, and raw rate after trimming the highest 1% of leader means), and 3 cell sets (all, without possible-Hinglish, and without repost or embedded-post cells), for 27 variants. It does not replace the main analysis or this future lock.

## Validation and support criteria

No score or model result is confirmatory before the required human checks.

- G1 requires a human segmentation sign-off.
- G2 requires human coding of the gold set, Krippendorff alpha at or above 0.67 where defined, and the planned dictionary-to-human correlation check of about 0.4. A single AI coder cannot satisfy either requirement.
- Any final measure that does not meet its validation rule is not used as confirmatory support.
- The provisional AI outputs and the existing Step 14 analyses can guide documentation and implementation checks only; they cannot support a human gate decision.

## OPEN: needs mentor decision before G3

- Whether and when to lock the final hypotheses, directional expectations and confirmatory outcome set.
- Whether the current provisional I-rate and we-rate counter is the final measure.
- The final construct definitions, trait dictionaries and any embedding, topic, classifier or LLM measure.
- The human coding protocol, coder training, adjudication process and rubric revision procedure.
- Whether the AI-assisted gold-set workflow may be used after human coding, and the model/provider and budget for any future judge run.
- Treatment of possible-Hinglish, Hindi and other non-English content after human review.
- Whether the provisional model-size rule and the sector-pooling rule become confirmatory rules.
- Any expansion of data scope, which remains subject to the unresolved scraping decision.

## Lock status

G3 is **PENDING (human)**. This file's hash is explicitly a DRAFT hash, not a G3 lock.
