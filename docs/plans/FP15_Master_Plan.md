# FP15 Leaders and Social Media: Master Plan

Written 3 November 2026. Final update 17 November 2026.

**Team.** Marutey Mani, Janhavi, Shaurya and Murtaza. Mentors: Prof. Prakarsh Singh, Prof. Rajesh Sharma and Rana Amanat Singh.

The strongest version of FP15 is a measurement study of how about 500 Indian corporate leaders present themselves on LinkedIn, built on roughly 20,000 leader-authored posts, scored mainly with transparent dictionaries that are checked against human coding, and with LLMs used only as a validated add-on.

**Update, 5 November.** Three things arrived: a second data file (Company\_Data.xlsx), six studies on leadership traits from the mentors, and an update mail from Rana Amanat Singh to Prof Singh. The file fills most of the leader details we planned to collect by hand, so section 6 gets shorter and section 7 gets a power check. The six studies change how we word the trait measures and give the I-rate a published precedent. The mail says the team asked to scrape likes, reposts and followers and to add foreign leaders. Neither is in the database, and Prof Singh has to decide, so nothing is scraped and the study stays on Indian leaders until then (sections 9 and 14). Each change is marked 'Update' in sections 2, 3, 4, 6, 9, 14, 15 and 16, and the hypothesis table and the power paragraph were edited in place.

**Final update, 17 November.** Where this page and the repo disagree on a number, the repo wins; the figures in the opening paragraph above are the early estimates and are superseded by these.

- **Research question, locked (Assignment 3).** On LinkedIn, is the way Indian corporate leaders present themselves explained more by who they are (their gender, whether they are a founder-CEO or a professional CEO, and their title) or by the firm they lead (its sector and size)? It is answered by comparing two blocks of explanations, leader profile and firm profile, with posts nested in leaders. Claims stay about the image projected in public posts.
- **Scraping.** The question needs only post text and Company\_Data, so it does not need new data. Nothing is scraped until Prof Singh approves in writing. Likes and comments matter only if the project moves to an engagement question, which is a different question.
- **Build state.** Claude Code has built the ingest, ID table, conservative de-duplication and post-cleaning stages. The repo is public and holds no data, names, post text, links or reversible ids; the leader, match and cell counts below come from committed reports in reports/. The ceo\_type and gender counts are not committed yet and are marked below.
- **Counts.** 564 leaders with posts (554 matched to Company\_Data, 2 ambiguous, 8 none); 26,945 raw text cells; about 325 leaders with 15 or more cells (cells stand in for posts until segmentation). Not yet in a committed report (to be added): where ceo\_type is coded, 442 professional CEOs and 74 founder-CEOs; gender in Company\_Data, 602 coded 1, 58 coded 0, 192 blank, meaning unconfirmed. role\_start\_year and post\_date are almost empty, so there is no tenure or trend analysis.
- **Course deliverables.** A five-slide deck for the next mentor meeting; the Literature Review first draft goes to the tutor at the Monday tutorial and the final is due 29 November, 11:59 PM. Both are drafted in the project chat.
- **Still open.** Gates G1 to G4 have no sign-off yet. Mentor answers are pending on the scraping route, the gender coding, the collection date and the fiscal years. The human jobs are the 200-cell segmentation sample, the 50-post reaction check, the 29 Hinglish rows and the Company\_Data name hand-check.

## 1. The project in one page

**Working title.** *Voice at the top: how Indian corporate leaders project themselves on LinkedIn, and what that varies with.*

**Core question.** When leaders write in public, what image do they project (agentic or communal, personal or institutional, which of Northouse's five traits), and how does that image vary with who they are (founder or professional CEO, gender, function, firm and sector) and where they lead?

**What we claim and what we do not.** We measure the *projected image in public posts*. We do not measure real personality, leadership quality or firm outcomes causally. This matters because LLMs recover real personality from text only weakly (best Big Five correlation about 0.25 in one 2025 test on 518 people; see Sources), and because posts may be ghostwritten or edited by communications teams.

**Why this is the best version of the project.**

1. It fits the mentors' framing (DV = what leaders post, IV = who they are) and your Assignment 2 table (impression management, agentic versus communal wording, personal versus institutional focus, the five Northouse traits).
2. It uses what the data can actually support. The audit in section 2 shows about 20,000 usable leader-authored posts across 544 leaders, with 280 leaders having at least 15 posts. That is enough for leader-level comparisons, not for fine causal claims.
3. It makes measurement the contribution. The LEO interns showed that LLM scores of leaders disagree most on exactly the subjective traits we care about. A transparent, validated measurement layer is therefore the part that is new and defensible.
4. It is honest about selection. Leaders who post on LinkedIn are not all leaders, and posts are not private beliefs. The design states this up front instead of hiding it.

**Five decisions that change the current plan.**

| # | Decision | Why |
| --- | --- | --- |
| 1 | Re-extract posts so each row is written by the leader only | Each scraped cell is raw feed text: author header, headline, age, body, '…more', reaction count, and sometimes other people's posts. 89% of cells start with the leader's own post, 9% have no author header (shared article cards) and about 5% contain other authors' blocks (section 2) |
| 2 | Do not reuse the existing word-count outputs | Pronouns (I, we, our, my) are removed as stopwords and the 'important words' are mostly job titles and scraper text |
| 3 | Main measures are dictionaries and counts; LLMs are a checked second opinion | Transparent, reproducible, cheap; LLM validity on personality is weak |
| 4 | Unit of analysis is the leader, with posts nested inside leaders | Median leader has only 15 posts; posts from one person are not independent |
| 5 | Add outside variables (gender, sector, listing status, firm size, function, tenure) | The dataset itself only has founder versus professional CEO, title and company |

**One-line answer to 'what is the success variable?'** Do not make it the headline outcome. Use firm-level success measures (market capitalisation, return on capital, awards) only as a secondary, clearly associational layer for listed firms; keep the main study about voice. Section 14 lists this as a decision for the mentors.

## 2. What the dataset really contains

The zip holds 7 batch folders of leader workbooks, `All_500` roster files, `wordcount_*` summary files, one word-count script and 4 PDFs on the LEO trait-scoring work. I audited every workbook locally with scripts (counts, segmentation, sampling); I did not read the 20,000 posts one by one.

**Headline numbers (after de-duplication and author segmentation)**

| Item | Value |
| --- | --- |
| Leader sheets with data, in 5 header layouts | 547 (a further 158 sheets are empty and 4 have shifted or missing headers that look recoverable) |
| Raw post cells | 22,083 |
| Cells whose first block is written by the leader | 19,690 (89%) |
| Cells with no author header (shared article or link cards) | 1,969 (9%) |
| Cells with more than one author block | 1,059 (5%) |
| Leader-authored posts | 19,966 |
| Leaders with at least 1 / 5 / 15 / 30 / 60 / 100 posts | 544 / 420 / 280 / 192 / 112 / 59 |
| Posts per leader | median 15, mean 37, middle half 5 to 49, maximum 230 |
| Words per leader-authored post | median 47 |
| Posts cut off by LinkedIn's '…more' | 23% (so only the preview text was captured) |
| Posts ending in a bare number after '…more' | 29% (likely reaction counts; not yet verified) |
| Posts with Devanagari script | 1.3% (Hinglish in Roman script is not counted and needs a separate check) |
| Founder-CEO versus Professional CEO label | 74 versus 426 leaders (500 of 544 labelled) |
| Leaders with 15+ posts by type | 45 Founder-CEO, 226 Professional CEO |

**Time coverage.** Every post carries a relative age such as 3mo or 5yr instead of a date. 79% are in whole years (1 year to 12 years back), 20% in months, under 2% in weeks, days or hours. A '1yr' post can be 12 to 23 months old. The scrape date is not stated in the files (the summary sheet only says '15 TH July (first 50)'), so absolute dates need that date confirmed.

**Roster versus posts.** `All_500` lists 653 people across 404 companies (98% with a profile link). The five copies in the zip hold the same 653 people: names, companies, titles, links and person IDs are identical in all five. They differ only in free-text collector notes in stray cells (for example 'scrolled till year 2', 'checked till 8th year'), and the Third and Fourth copies are byte-identical. The `wordcount` summaries list 532 distinct founders across 341 companies. Only 383 names match exactly between the two, with 265 roster-only and 148 summary-only. A proper ID table is needed before any join.

**Problems found, in order of damage**

1. **Raw cells are feed text, not clean posts.** A cell looks like: author name, connection degree ('• 3rd+'), headline, age ('3mo •'), body, '…more', reaction number. Up to 14% of cells (9% with no author header, 5% with extra author blocks) hold no leader text or include another author. Without segmentation, other people's words get counted as the leader's.
2. **The existing word counts are unsafe.** `wordcount_2.py` treats we, our, us, I, me, my as stopwords, so the I-versus-we analysis cannot be rebuilt from its outputs. The 'important words' lists are dominated by titles and scraper text: 'managing' appears in 114 leaders' lists, 'chairman' 45, 'executive' 43, plus 'larger' (from 'Activate to view larger image'), 'visit' and 'website'.
3. **Truncation bias.** Long posts are cut at the preview, so measures that depend on length or on late-in-post content (thanks, calls to action) are biased.
4. **No dates, no demographics.** `post_date` and `role_start_year` are empty in the workbooks; there is no gender, age, education, sector, firm size or tenure column.
5. **Name and ID mess.** The same person can appear under different spellings across roster, summaries and sheet names; 9 founders are duplicated in the summaries.
6. **Uneven activity.** A leader with 3 posts and one with 230 cannot be compared without shrinkage.
7. **Selection.** Only leaders with a findable LinkedIn profile are included, and 'Professional CEO' versus 'Founder-CEO' leaves out promoter-family leaders, a major Indian category.

**A first look, to size the analysis (exploratory, unadjusted).** Across all leader-authored text, first-person singular words run about 1.0 per 100 words and first-person plural about 2.0 per 100 words. Of the 271 leaders with 15+ posts, 79% use 'we' more than 'I'. Founder-CEOs (n=45) and Professional CEOs (n=226) did not differ clearly on I-rate (median 0.64 versus 0.85 per 100 words, p=0.19), we-rate (2.14 versus 1.78, p=0.21), you-rate (1.11 versus 0.80, p=0.10), gratitude and pride words (0.38 versus 0.44, p=0.86) or words per post (60 versus 65, p=0.62). With these group sizes a two-sided test at 80% power only detects a standardised difference of about 0.46, so small real differences would be missed. Treat these as a smoke test, not findings.

**Update: a second file, Company\_Data.xlsx (added 5 November).**

| Item | What it holds |
| --- | --- |
| Size | 852 people at 533 companies and 129 columns. Three columns are empty (2025 revenue, profit and EBITDA). |
| Who is in it | Every company is listed on NSE or BSE. Titles include CEOs, managing directors, CFOs, CTOs and HR heads. |
| Overlap with our posts | 541 of our 544 leaders match a name in the file exactly (5 names appear twice and need a company check), and 543 match when names are compared loosely. All 280 leaders with 15+ posts are found. Where the post sheets name a company it agrees with the file for 495 of 536 unique matches; the other 41 need a hand check, and most of them have no company in the post sheets. |
| People with no posts | 313 people in the file have no posts in our data, 184 of them CEOs or managing directors. That group lets us check who posts and who does not (selection). |
| Gender | A Gender column with 1 for 602 people, 0 for 58 and blank for 192. The file does not say what 0 and 1 mean (probably 1 is male and 0 is female) or who coded it. Among the 279 uniquely matched leaders with 15+ posts: 194 coded 1, 25 coded 0, 60 blank. |
| LinkedIn fields | Followers (present for about 70% of the 15+ group), connections (capped at '500+', so not useful), honors and awards count, recommendations, publications, patents, languages and skills. |
| Firm fields | Revenue, profit and EBITDA for 2021 to 2024 with growth rates, employee counts, founded year, sector, funding, valuation and stock ticker. Values are text such as '186.6M' and '2.5B' and need parsing. For the 15+ group, 2024 revenue is filled for 205 of 279 leaders and employee counts for 226. |
| Personal contact data | Email addresses and phone numbers for people and companies. These are dropped at ingest (section 9). |
| Cleaning needed | '.' and '-' mean blank. 834 distinct profile links across 852 rows, so some links repeat and must be checked. Fiscal years are not labelled. |

**What this changes.** Gender, firm size, sector, firm age and follower counts no longer need to be collected by hand for most leaders; they need spot checks. Every firm is listed, so listed versus unlisted cannot be tested for these leaders, and H4 now compares size, sector, age and funding inside listed firms. The success layer in section 6 (option b) becomes practical, since 2021 to 2024 revenue and profit are in the file. There are now three lists of people (All\_500 with 653, the wordcount summaries with 532, Company\_Data with 852), and the ID table in step 3 of section 5 has to reconcile all three.

**Where the file came from.** Rana Amanat Singh got the company data from Anshika and is passing it to the team. Her note to Prof Singh lists the original variables as leader\_name, company\_name, current\_title, role\_start\_year, ceo\_type, platform, post\_date and post\_date\_text. In the workbooks we have, post\_date and role\_start\_year are empty, and Company\_Data has no tenure column, so tenure in role is still a gap.

## 3. Research questions and hypotheses

**Descriptive questions (answered first, no hypothesis needed)**

- D1. What does a typical leader post about (topic mix), how long, how often, in what language?
- D2. How much of the voice is personal ('I') versus collective ('we') versus audience-directed ('you')?
- D3. How much is agentic (achievement, drive, control) versus communal (people, care, thanks)?
- D4. How are the five Northouse traits (intelligence, self-confidence, determination, integrity, sociability) expressed in words?
- D5. How much do leaders differ from one another compared with how much one leader varies from post to post? (intraclass correlation; tells us whether 'leader style' exists at all)

**Confirmatory hypotheses (written down before looking at outcomes)**

| ID | Hypothesis | Theory | Outcome measure | Predictor | Expected direction |
| --- | --- | --- | --- | --- | --- |
| H1 | Founder-CEOs write more personally than professional CEOs | Upper echelons; narcissism and hubris language work (Hambrick and colleagues) | I-rate, own-name and own-story mentions, personal-anecdote share | Founder-CEO vs Professional CEO | Founder higher |
| H2 | Women leaders use more communal and less self-promotional wording | Role congruity (Eagly); impression management by gender (Ahuja 2024 on Indian men) | Communal minus agentic score; achievement and award claims | Gender (Company\_Data column, coding to confirm) | Women more communal, fewer self-claims |
| H3 | Functional background shapes voice | Upper echelons (functional tracks) | Domain vocabulary, numbers and technical terms (CFO, CTO) vs people vocabulary (CHRO) | Title family (CEO, CFO, CTO, CHRO, MD, Chair) | CHRO more communal, CFO more numeric, CTO more technical |
| H4 | Larger firms produce more institutional, controlled language | Impression management; communications-team mediation | We-rate, company-name density, template score, lexical diversity | Revenue, employees, sector, firm age (all firms in Company\_Data are listed) | More institutional, more templated |
| H5 | Self-confidence and determination words co-occur with agentic style, integrity and sociability with communal style | Northouse trait approach; Big Two | Trait scores vs agency and communion scores | Within-post correlations | Positive within pair, weak across |
| H6 | Leaders thank and credit others more than they claim credit | Servant and transformational leadership; impression management | Credit-to-team vs credit-to-self ratio | Leader level | Team credit higher on average |
| H7 | Posting voice has shifted over time, especially around 2020 to 2021 | Context effects on impression management | Trait, agentic and communal scores by post-year band | Approximate post year (from relative age) | More personal and communal after 2020 (exploratory) |
| H8 | Personal and communal posts draw more reactions than institutional ones | Audience response to authenticity | Reaction count (only for posts where a count exists) | Post-level measures | Positive, after controls (exploratory; follower counts come from Company\_Data for about 70%) |
| H9 | Some leaders sound like their company's voice (low variation, high templating) | Goffman front-stage; ghostwriting concern | Within-leader variance, near-duplicate share, boilerplate score | Leader level | A visible group of 'institutional voice' leaders |

**How they map to Assignment 2.** DV family = projected image (agentic, communal, personal, institutional, trait words). IV family = leader profile (type, gender, function, firm, sector, tenure) plus the success layer (firm outcomes, awards) used only in secondary models.

**Pre-registration.** H1 to H4 and H6 are confirmatory. H5, H7 to H9 and all topic and clustering results are exploratory and labelled that way. Register the plan (OSF or a dated, hashed file in the repository) before the confirmatory models are run.

**Update: what the six shared studies change.** The mentors sent these for the review of leadership traits. Reading status for each is in section 16.

- **Stogdill (1948)** reviewed the early trait literature and concluded that traits alone do not explain who leads, because the situation matters. For us, trait words are reported as language leaders choose, and compared across settings (sector, firm type) instead of read as a fixed trait profile.
- **Kirkpatrick and Locke (1991)** argued that traits do matter and named drive, desire to lead, honesty and integrity, self-confidence, cognitive ability and knowledge of the business. Several map onto Northouse's five; two do not (section 4).
- **Judge, Bono, Ilies and Gerhardt (2002)** is a meta-analysis of the Big Five and leadership, with extraversion the most consistent correlate. It is the link between our sociability measure and the Big Five. I could not open the full text, so no numbers are quoted here.
- **DeRue and colleagues (2011)** found that leader behaviours explained more of leader effectiveness than traits, and that behaviours may carry the effect of traits. Our data are language about what leaders do, so we add a task-versus-relational pair next to agentic versus communal (section 4) and treat trait words as a second lens.
- **Chatterjee and Hambrick (2007)** built a CEO narcissism index from five unobtrusive signs: the size of the CEO's photo in the annual report, mentions of the CEO's name in press releases, first-person singular pronouns in interviews, and cash and non-cash pay relative to the second-highest executive. That gives H1 a published precedent for using the I-rate. Two cautions: pronouns were one part of a five-part index, and the study tied narcissism to bold, extreme strategy, not to better or worse performance on average. Our I-rate alone is not a narcissism score and we will not call it one.
- **Nadkarni and Herrmann (2010)** studied 195 small and medium Indian business process outsourcing firms and found that CEO personality shapes strategic flexibility, which in turn carries the effect on firm performance. It is an Indian-setting precedent for linking leader traits to firm outcomes, and supports using firm performance only as a secondary layer. Our design differs: we measure the image projected in posts, not personality.

## 4. Measures: how words become constructs

**Principle.** Three layers, each checked against the one below. Layer 1 is transparent counts and dictionaries (main results). Layer 2 is embedding-based classifiers and topics (richer, still reproducible). Layer 3 is an LLM judge on a sample (a second opinion, kept only if it agrees with humans). A construct enters the paper only if its measure passes the validation in the last column.

**Layer 1 and 2: the measure set**

| Construct | Measure | How | Validation before use |
| --- | --- | --- | --- |
| Personal vs collective voice | I-rate, we-rate, you-rate per 100 words; share of posts with no first person | Regex on cleaned, case-folded text, handling contractions (I'm, we're) | Hand-check 200 posts; counts must match to within 2% |
| Agentic wording | Agency dictionary rate (achievement, drive, control, competence) | Big Two agency lexicon if obtainable; otherwise own seed lexicon expanded with embeddings and reviewed by hand | Face validity on top and bottom 100 posts; correlation with human 1 to 5 ratings of 300 posts |
| Communal wording | Communion dictionary rate (care, support, people, thanks, community) | Same approach | Same |
| Five Northouse traits | Per-trait dictionary rate, built from Northouse's definitions plus synonyms | Intelligence: insight, analysis, expertise, learning. Self-confidence: certainty, conviction, 'I am sure'. Determination: persist, drive, commit, relentless. Integrity: honest, ethics, trust, accountable. Sociability: warm greetings, congratulations, gratitude, relational words | Human rating of 300 posts per trait; keep a trait only if dictionary and humans correlate at r of about 0.4 or higher |
| Self-promotion | Achievement and award claims, superlatives, rankings, numbers about own results, 'honoured', 'humbled' | Pattern list plus classifier on hand-labelled posts | Precision of at least 85% on the labelled set |
| Credit direction | Thanks and credit to team or others vs to self | Rules plus named-entity and pronoun context | Hand-check 200 posts |
| Institutional focus | Company-name density, organisation and product mentions, corporate-announcement phrases | spaCy named entities, company name from roster | Compare against human 'institutional vs personal' label |
| Topic mix | Share of posts per topic (launches, results, hiring, ESG, thought leadership, events, festivals, personal) | Multilingual sentence embeddings, then BERTopic with names checked by hand | Coherence score plus hand review of every topic |
| Sentiment and emotion | Positive and negative tone, emotion words | NRC lexicons or VADER on English text; compare two lexicons because single lexicons can mislead | Agreement between two lexicons on the sample |
| Style | Words per post, readability, lexical diversity (MTLD), question marks, exclamations, emoji, hashtags, tagging density, links | Plain code | None needed beyond unit tests |
| Templating or ghostwriting signal | Near-duplicate share, boilerplate openers and closers, low within-leader variance | Embedding similarity within leader | Hand review of the 30 highest-scoring leaders |
| Engagement | Reaction count where a trailing number exists (29% of posts) | Parse and verify | Check 50 posts against LinkedIn before use |

**Layer 3: the LLM judge.** Score a stratified sample (for example 10 posts for each leader with 15+ posts, about 2,800 posts) on the five traits, agentic and communal, personal and institutional, with a 1 to 5 rubric and a one-line justification, using at least three different models and fixed prompts stored in the repository. Report agreement between models, agreement with the 300-post human gold set, and bias by leader group (the LEO report found large model-to-model gaps on self-confidence and the authentic-leadership items). If an LLM measure correlates with humans below about 0.4 it stays in an appendix.

**The human gold set.** 300 posts, stratified by leader type and length, coded by two people on every construct above with a written codebook. Report Krippendorff's alpha; aim for 0.67 or higher and refine the codebook until it is reached. This set is the yardstick for every other measure and is the single most valuable asset in the project.

**Handling language.** About 1.3% of posts contain Devanagari and an unknown share is Hinglish in Roman script. Run language identification, flag mixed posts, and run all dictionary results with and without them. For topics use a multilingual embedding model; HingBERT-type models exist for Hinglish if the flagged share turns out to matter.

**From post to leader.** Compute each measure per post, then aggregate to the leader with shrinkage toward the group mean (empirical Bayes) so a leader with 5 posts is not treated like one with 100. Also keep per-leader variance, because 'how consistent is the voice' is itself a finding (H9).

**Update: where the five traits come from, and three additions.** Northouse's five traits (intelligence, self-confidence, determination, integrity, sociability) come from the same trait tradition as Stogdill (1948) and Kirkpatrick and Locke (1991). Against Kirkpatrick and Locke's six: self-confidence matches self-confidence, integrity matches honesty and integrity, determination matches drive, and intelligence matches cognitive ability. Sociability has no counterpart there, and knowledge of the business and desire to lead are not in the Northouse five.

Proposal for the mentors to approve: keep the five as the main trait measures, since they match the mentors' framing, and add three exploratory ones. Business knowledge covers domain terms, figures and specifics about the firm and its market. Desire to lead covers ambition and vision language. A task-versus-relational pair covers setting direction and goals against supporting and developing people, which is the language version of the behaviour categories in DeRue and colleagues (2011). All three are built and checked the same way as the other measures, against the 300-post gold set, and the task and relational pair is tested for overlap with agentic versus communal before either is reported separately.

## 5. Data pipeline, step by step

Every step reads one versioned file and writes the next, so any result can be traced back to the raw sheets. Raw files are never edited.

1. **Freeze the raw data.** Copy the zip contents to a read-only `data/raw/` folder, record file hashes and sizes, and write a manifest. Acceptance: re-running the manifest reproduces the same hashes.
2. **Harmonise sheets.** Map the 5 header layouts to one schema (leader, company, title, ceo\_type, platform, post\_text, link, age\_text, profile\_url, batch, sheet). Recover the 4 shifted-header sheets by re-reading without headers and checking against the roster. Keep a log of every sheet skipped and why (158 empty sheets). Acceptance: every non-empty sheet is either loaded or listed with a reason.
3. **Build the leader ID table.** One row per person with a permanent `leader_id`. Join `All_500` (person\_id), sheet names, `wordcount` summaries and profile URLs by normalised name, company and URL; resolve the 265 roster-only and 148 summary-only names by hand. Acceptance: 0 unresolved names, every leader with posts has exactly one ID, duplicates (9 in the summaries) merged.
4. **Segment each cell into blocks.** Split on the author header pattern (name line, then '• 1st', '• 2nd', '• 3rd+' or 'Following'), peel off headline, age token and body. Label each block as leader, other author, or no-author card. Acceptance: on 200 random cells checked by hand, at least 95% of blocks are labelled correctly (a first version of this logic already ran on all 22,083 cells).
5. **Attribute authorship.** Keep leader-authored blocks as posts. Keep no-author cards in a separate table as 'shared link' activity (a measure of sharing behaviour), not as the leader's words. Treat repost markers as their own flag.
6. **Clean the text.** Remove the scraper artefacts ('hashtag#', '…more', trailing reaction numbers, 'Follow', 'Edited', 'Activate to view larger image'), normalise whitespace and unicode, keep case, punctuation, emoji and pronouns. Store both the raw block and the cleaned body.
7. **Parse dates and engagement.** Convert age tokens (5yr, 3mo, 2w) to an approximate date and an uncertainty band relative to the scrape date. Parse trailing numbers as reaction counts only after the 50-post check against LinkedIn. Acceptance: scrape date confirmed in writing by the mentors or the data owner.
8. **Flag quality.** Per post: truncated, language (English, Devanagari, mixed), length bucket, near-duplicate, repost, very short. Per leader: posts kept, share truncated, date span.
9. **Deduplicate.** Exact duplicates by link or text; near-duplicates by embedding similarity above a threshold chosen on a hand-labelled sample.
10. **Enrich the leader table** (section 6) and lock it.
11. **Compute measures** (section 4) into a post-level table and a leader-level table, each with a data dictionary.
12. **Freeze analysis tables.** Write `posts.parquet`, `leaders.parquet`, `measures_post.parquet`, `measures_leader.parquet` with version tags. All later figures and tables are produced by scripts from these files.

**Minimum-data rules (set before analysis).** Main analyses use leaders with at least 15 leader-authored posts (280 leaders now, about 271 with a type label). Sensitivity analyses repeat with at least 5, 30 and 60. Posts under 10 words are excluded from rate measures but kept for activity counts.

## 6. Enriching the leader table (the independent variables)

The data holds founder versus professional CEO, job title, company and profile URL. Everything else the hypotheses need must be added at leader level. About 500 leaders makes hand-checked enrichment realistic, and each source below is public.

**Update: Company\_Data.xlsx now covers most of this table.** Gender, listing, sector, firm size, firm age, follower counts and several performance figures are columns in the new file (section 2), matched to 541 of our 544 leaders. For these the job changes from collecting to checking: spot-check about 20% of values against public pages, leave blanks blank, and record where each column came from and who coded it. Still to collect by hand: tenure in role, education, and the ownership category (promoter family, MNC subsidiary, PE-backed). The 'Must' and 'Should' priorities below apply to what is still missing after the match.

| Variable | Why it matters | Source | Method | Priority |
| --- | --- | --- | --- | --- |
| CEO type (have) | H1 | Dataset | Re-check 50 labels by hand; add 'promoter family' and 'professional, ex-founder' categories where clear | Must |
| Title family | H3 | Dataset title text | Parse into CEO, MD, Chair, CFO, CTO, CHRO, CMO, other; hand-fix ambiguous titles (the 'cto' string also matches 'director', so use word boundaries) | Must |
| Gender | H2 | Public profile photo, pronouns in profile, company bios | Coded by a person from public information, second person checks 20%; record 'unclear' rather than guess | Must |
| Listed status, exchange, sector | H4 | NSE and BSE listings, company website | Match company to listing; use a fixed sector scheme (for example NSE industry) | Must |
| Firm size | H4 | Market capitalisation, revenue, employees from exchange filings or company pages | Log-transform; record the as-of date | Must for listed firms |
| Firm age and ownership (promoter, MNC subsidiary, PE-backed) | Context | Company pages, annual reports | Hand-coded categories | Should |
| Tenure in role | Controls | LinkedIn profile, annual reports (the workbook field is empty) | Hand-fill; leave missing if not public | Should |
| Education tier (for example IIT, IIM, foreign MBA) | Upper echelons | Public profile | Binary or three-level code | Could |
| Leader age or cohort | Generational voice | Estimate from graduation year only if public | Treat as approximate | Could |
| Follower count | H8 control | Public profile page | Hand-collect for a subset, or leave as a stated limitation | Could |
| Success layer (secondary) | Associational only | Listed-firm return on capital, 3-year market-cap change, awards and lists such as Fortune India or Forbes India rankings | Pull from filings and public lists; record dates | Could |

**How to do it responsibly and fast.** Build a spreadsheet with one row per `leader_id` and one column per variable, a source URL column and a 'checked by' column. An LLM can propose values with citations, but a person verifies every one that enters the analysis. Missing values stay missing; do not impute demographics from names.

**Reconcile with the 80-parameter catalog.** Your Week 13 report says you narrowed an earlier 80-parameter catalog to high-feasibility variables. That list is not in the files shared so far. Once it is pasted in, every variable above should map to a catalog entry (kept, dropped with a reason, or added), so the plan and the reports stay consistent.

**On 'leadership success'.** The mentors have not defined it. Three workable options: (a) skip it and keep the study about voice (simplest and safest); (b) use firm-level performance for listed companies as an associational layer; (c) use reputation signals such as awards and ranking lists. Recommended: (a) as the headline, (b) as a clearly labelled secondary analysis, never a causal claim, because firm performance is driven by far more than a leader's posts and because the reverse direction (successful leaders post more) is as plausible.

## 7. Analysis plan

**Unit and structure.** Posts are nested in leaders, and leaders in firms. Every inferential model must respect that: ignoring it overstates certainty, because 50 posts from one leader are not 50 independent observations.

**Stage A: descriptives (Table 1 and figures).** Counts per leader, per type and per batch; distributions of every measure; correlation matrix of the measures; topic shares; language mix. Show the intraclass correlation (ICC) for each measure: the share of variance that sits between leaders. A low ICC means 'leader voice' hardly exists for that measure and leader-level claims should be dropped.

**Stage B: leader-level comparisons (confirmatory).** For each hypothesis compare groups on shrunk leader-level scores. Use Mann-Whitney or Kruskal-Wallis tests with effect sizes (Cliff's delta, or Cohen's d on transformed scores) and bootstrapped 95% confidence intervals. Report the effect size first, the p-value second.

**Stage C: multilevel models (main inferential results).**

- Post-level outcomes that are rates (I-rate, trait rate): negative binomial or Poisson mixed model on word counts with log(words) as offset and a random intercept for leader.
- Proportions and scores (agency share, LLM scores): linear mixed model on a suitably transformed score, or beta regression with a leader random effect.
- Fixed effects: CEO type, gender, title family, listed status, log firm size, sector, post-year band; interaction terms only for pre-registered ones (for example type by firm size).
- Report variance components, effect sizes with confidence intervals, and the model's fit; use cluster-robust standard errors as a cross-check. Tools: `statsmodels` MixedLM in Python, or `lme4` and `glmmTMB` in R if the team prefers.

**Stage D: multiple testing and honesty rules.** Control the false discovery rate (Benjamini-Hochberg) within each hypothesis family. Label every exploratory result as exploratory. Keep an analysis log of every model run, including ones that were dropped.

**Stage E: structure discovery (exploratory).** Cluster leaders on their measure profiles (Gaussian mixture or k-means with silhouette and stability checks) to find voice archetypes (for example 'institutional broadcaster', 'personal storyteller', 'people-first thanker'). Then test whether archetypes line up with type, gender, function and firm. Report cluster stability across resamples; discard clusters that do not replicate.

**Stage F: time analysis (exploratory).** Use post-year bands from relative ages (accept the up-to-one-year blur). Fit leader-specific slopes only for leaders with posts in at least three bands. Check for survivor bias: older posts that still exist are those leaders did not delete, and the scraper only reaches back a limited way for very active people.

**Stage G: engagement (exploratory).** Where a reaction count exists, model it with negative binomial regression, controls for post length, age band and leader random effect. State that posting time is missing and that follower count exists for only about 70% of leaders, so this is association only.

**Power and sample size.** With 45 Founder-CEOs and 226 Professional CEOs (leaders with 15+ posts), a two-sided test at 80% power detects a standardised difference of about 0.46. For gender, Company\_Data codes 25 leaders as 0 and 194 as 1 among the 279 uniquely matched leaders with 15+ posts (60 blank). If 0 means woman, that detects a difference of about 0.6, not 0.46, and only one of the 25 is a Founder-CEO, so a gender-by-type interaction cannot be tested. The coding needs confirming first; if the minority group has fewer than 40 leaders, report estimates with intervals and avoid null-result claims. Lowering the post threshold to 5 posts raises leader counts to 420 and increases the groups, at the cost of noisier leader scores; the shrinkage handles part of that.

**Robustness (the 'multiverse').** Repeat the main results with: minimum posts of 5, 15, 30; truncated posts excluded; Devanagari and mixed-language posts excluded; reposts excluded; each dictionary swapped for its alternative; posts under 10 words excluded; leaders with the highest template score removed. Show all results in one summary figure so readers see how stable the conclusion is.

**Confirmatory versus exploratory split.** Lock the hypotheses and code first. If the sample allows, split leaders at random 50/50: develop and tune on one half, confirm on the other. If it does not, state that all results are in-sample.

## 8. Validation and quality control

Four kinds of checks, each with a pass mark written down before it is run.

| Check | What is tested | Pass mark | If it fails |
| --- | --- | --- | --- |
| Segmentation audit | 200 random cells hand-checked for correct author, body and age | 95% or more of blocks correct | Fix rules, re-run, re-audit |
| Measurement audit | Pronoun counts and dictionary hits on 200 posts checked by hand | Counts within 2%; dictionary precision 85% or more | Edit dictionary, re-test |
| Human gold set | 300 posts coded by two people on every construct | Krippendorff's alpha 0.67 or more per construct | Revise codebook; drop the construct if it stays low |
| Convergent validity | Dictionary score vs human rating vs LLM score | Correlation about 0.4 or more between dictionary and human | Report as weak or move to appendix |
| Known-groups validity | Do groups differ where theory says they must (CHRO more communal than CFO; CFO more numeric)? | Direction matches in at least 2 of 3 checks | Question the measure before the hypotheses |
| Face validity | Read the 20 highest and 20 lowest posts for each measure | No obvious mis-scoring pattern | Fix and re-run |
| Stability | Same results across the 'multiverse' of choices (section 7) | Main signs unchanged | Report the instability itself |
| Reproducibility | A fresh clone of the repository rebuilds every table and figure from raw data | One command, same outputs | Fix before writing |

**LLM-specific checks.** Fixed prompts and model versions stored in the repository; temperature set low; each post scored at least twice to measure test-retest consistency (consistency alone is not validity, since a 2025 study found high test-retest agreement but low accuracy); at least three different models; report model-to-model agreement and bias by leader group; keep a log of refusals and out-of-range outputs (the LEO interns found these were a real source of missing data, with name mismatches in one model's file causing nearly half of all their missing values).

**Reading the data yourselves.** Besides the numbers, each team member reads at least 100 posts from at least 20 different leaders, writes down what the measures miss, and shares the notes. Dictionary methods fail quietly on sarcasm, quotation, announcements and borrowed text; reading is how these failures are found.

## 9. Ethics, legal and data handling

The data are public posts by named, identifiable business leaders. You have confirmed the dataset can be shared and used freely, so the earlier restriction on uploading it is lifted. The questions below are about how we treat the people in it, and they still need answers.

**What is known.**

- A US appeals court held that scraping publicly accessible LinkedIn profile data is not likely to violate the federal anti-hacking law (reported in 2022). That does not remove contract risk under LinkedIn's terms. As far as I know, the same dispute later ended with a finding that the scraper had breached those terms; I did not verify that here.
- In India, commentary says scraping public data is not explicitly illegal, but the Digital Personal Data Protection Act 2023 sets a consent-based regime with large penalties, and other laws (the IT Act, copyright) may apply. I believe the Act carves out personal data that a person has made public themselves, but the article I opened did not cite the section, so this must be checked with Plaksha's ethics office or a lawyer before publication.
- We did not collect the data ourselves, so provenance matters: who scraped it, when, and under what approval.

**What we commit to.**

1. **Ask for an ethics review or written clearance** from Plaksha (the mentors know the route) before any external release of results.
2. **Pseudonymise in outputs.** Papers, slides and figures show groups and aggregate patterns, not rankings or labels of named leaders. Leader IDs, not names, appear in analysis files that leave the working repository.
3. **No sensitive inference.** We do not infer health, religion, politics, caste or similar traits from posts or names. Gender is coded only from public self-presentation, with 'unclear' allowed, and is reported with the limits of a binary code stated.
4. **No claims about real personality or quality.** Wording in every output says 'projected in public posts'.
5. **Do not redistribute raw posts.** Share code and derived, aggregated tables; share raw text only inside the project, and not in public repositories or public artifacts.
6. **Sending posts to third-party LLM APIs.** Use settings that disable training on inputs where the provider offers them, send only the post text and an ID, and keep the sample to what the validation needs.
7. **Right to object.** Keep a plain process for removing a leader if they or their company asks, and record it.
8. **Ghostwriting and PR.** State that posts may be written by staff; the study is of the public image, not of private authorship.
9. **Student data.** Weekly reports and the plan stay in the course's approved space; no personal data of team members beyond what the course requires.
10. **Contact fields in Company\_Data.** The file holds email addresses and phone numbers for people and companies. We drop them at ingest, keep only the fields the analysis uses, and keep the original file out of any shared copy.
11. **No new scraping without approval.** The team asked to scrape likes, reposts and followers from LinkedIn and to add foreign leaders. Until Prof Singh decides and an approval route is confirmed, nobody scrapes anything, and the Claude Code instructions say so.

## 10. Tools, compute and repository layout

**Stack.** Python 3.11 with `pandas` or `polars`, `pyarrow` (parquet), `rapidfuzz` (name matching), `spaCy` (entities, tokens), `scikit-learn`, `sentence-transformers` with a multilingual model, `BERTopic` with `UMAP` and `HDBSCAN`, `statsmodels` and `scipy`, `matplotlib`. Optional R with `lme4` and `glmmTMB` for mixed models. LIWC-22 is a paid tool; check whether Plaksha holds a licence, and otherwise use open lexicons so results are reproducible by anyone. Git for versioning; `pytest` for the segmentation and pronoun rules; a `Makefile` so one command rebuilds everything.

**Compute.** About 20,000 posts of roughly 50 words each fit on a laptop CPU. Embeddings with a small multilingual model take minutes. The LLM judge is the only costly part: about 2,800 sampled posts, three models and two runs each is roughly 17,000 short calls, which is modest; scoring all 20,000 posts is possible later if the validation looks good.

**Repository layout.**

```
fp15/
  README.md                 how to rebuild everything
  Makefile                  make data, make measures, make models, make report
  data/raw/                 read-only copy of the zip, with MANIFEST.sha256
  data/interim/             harmonised sheets, blocks, ID table
  data/processed/           posts.parquet, leaders.parquet, measures_*.parquet
  docs/                     codebook.md, data_dictionary.md, prereg.md, ethics.md, decisions.md
  configs/                  thresholds.yaml, prompts/*.txt, lexicons/*.csv
  src/fp15/
    ingest.py  ids.py  segment.py  clean.py  dates.py  enrich.py
    measures/  pronouns.py  lexicons.py  northouse.py  style.py  topics.py  llm_judge.py
    models/    descriptives.py  mixed.py  cluster.py  robustness.py
  notebooks/                exploration only; nothing the paper depends on lives here
  tests/                    segmentation, dates, pronoun counts
  reports/                  figures/, tables/, paper/, slides/
```

**Working rules.** Every table or figure in the paper is produced by a script from `data/processed/`. Every threshold lives in `configs/thresholds.yaml`. Every decision that changes results is written in `docs/decisions.md` with a date. Raw files are never edited.

## 11. Work packages and gates in dependency order

Ordered by what must exist before what, not by dates. Four gates stop the work from moving on before the foundation is sound.

| WP | Work | Needs | Produces | Gate |
| --- | --- | --- | --- | --- |
| 0 | Setup: repository, ethics clearance request, scrape date, 80-parameter catalog, success decision | Section 14 answers | `decisions.md`, empty repo with Makefile | None |
| 1 | Ingest, harmonise, recover odd sheets, build leader ID table | WP0 | `leaders_ids.csv`, harmonised sheets | Every non-empty sheet loaded or logged; 0 unresolved names |
| 2 | Segment, attribute authorship, clean, parse ages, flag quality | WP1 | `posts.parquet` | G1: 95% segmentation accuracy on 200 hand-checked cells; data frozen |
| 3 | Enrich leader table (gender, sector, listing, size, function, tenure) | WP1 | `leaders.parquet` | Every analysis variable has a source URL or is marked missing |
| 4 | Codebook and human gold set (300 posts, two coders) | WP2 sample | `codebook.md`, `gold.csv` | Alpha of 0.67 or more per construct or the construct is dropped |
| 5 | Layer 1 and 2 measures: pronouns, dictionaries, Northouse traits, style, topics, templating | WP2, WP4 | `measures_post.parquet` | G2: measures pass validation against the gold set |
| 6 | Layer 3 LLM judge on the stratified sample | WP2, WP4 | `llm_scores.parquet`, agreement report | Kept only if correlation with humans is about 0.4 or higher |
| 7 | Pre-register hypotheses and analysis code | WP3, WP5 | `prereg.md` (dated, hashed) | G3: plan locked before confirmatory models run |
| 8 | Confirmatory analysis (stages A to D) | WP7 | Tables 1 to 5, main figures | None |
| 9 | Exploratory analysis (stages E to G) and the robustness multiverse | WP8 | Exploratory tables, robustness figure | G4: results frozen and reproducible from a clean clone |
| 10 | Writing: paper, deck, poster, short public summary | WP8, WP9 | Drafts and final | Mentor review |
| 11 | Release: code, derived data, data dictionary, limitations statement | WP9 | Tagged repository | Ethics clearance covers release |

**Critical path.** WP1, then WP2, then WP4 and WP5, then WP7, then WP8. WP3 (enrichment) runs beside WP4 and WP5 and is the longest manual job. Do WP4's codebook early, because poor construct definitions are the most common reason text-measurement projects fail.

## 12. Risks and fallbacks

| Risk | Why it matters | Likelihood | Mitigation or fallback |
| --- | --- | --- | --- |
| Segmentation errors put other people's words in leaders' posts | Corrupts every measure | Medium | 200-cell audit, unit tests, no-author cards kept separate; if accuracy stays under 95%, hand-correct the worst sheets |
| Dictionaries miss how Indian business English and Hinglish are used | Weak construct validity | Medium to high | Gold set decides; add India-specific terms; run with and without mixed-language posts |
| LLM scores disagree with humans or with each other | Unreliable add-on | High (documented in LEO report and a 2025 study) | LLMs stay secondary; appendix only if below the pass mark |
| Too few posts per leader | Noisy leader scores | High (median 15) | Shrinkage, minimum-post sweeps, leader-level and post-level models side by side |
| Few Founder-CEOs or women in the 15+ post group | Low power; fragile tests | High | Report effect sizes with intervals; lower threshold in sensitivity; do not claim 'no difference' |
| Truncated posts bias length and call-to-action measures | Systematic bias | Certain (23%) | Flag, exclude in robustness, use only the preview-safe measures for the headline results |
| No absolute dates | Time analysis blurred | Certain | Use bands; confirm scrape date; present time results as exploratory |
| Ghostwriting and communications-team editing | Voice is not the leader's own | Likely | State as limitation; templating score; do not talk about personality |
| Selection into LinkedIn | Results describe posting leaders only | Certain | Compare roster leaders with and without posts on type, sector and size |
| Confusing 'Professional CEO' with the wider group (promoter family, MNC heads) | Misread type effect | Medium | Add categories during enrichment; describe the label as given |
| Over-claiming from many tests | False findings | Medium | Pre-registration, FDR control, exploratory labels |
| Privacy or terms-of-service complaint | Project or release blocked | Low to medium | Section 9 commitments; ethics clearance; pseudonymised outputs; removal process |
| Scope creep (other platforms, political leaders) | Dilutes the design | Medium | Out of scope unless mentors say otherwise; keep a 'future work' list |
| Time sink in manual enrichment | Delays the analysis | Medium | Prioritise Must variables; keep Could variables optional |

**Fallback design if the 15+ post group proves too thin or the gold set fails.** Shift the headline from leader-level hypotheses to a purely descriptive and methodological paper: the audited dataset, the measurement pipeline and its validation, and a first map of voice by role, with the hypotheses framed as hypotheses for the next stage. That is still a real contribution.

## 13. Deliverables

| Deliverable | Content | For |
| --- | --- | --- |
| Research paper (about 6,000 to 8,000 words) | Introduction and gap; theory and hypotheses; data and the audit; measurement and validation; results; robustness; limitations and ethics; discussion | Mentors, ILGC-3 assessment, possible submission |
| Methods appendix | Codebook, dictionaries, prompts, segmentation rules, validation tables, multiverse results | Reviewers, future students |
| Slide deck | Question, data, pipeline in one picture, 5 to 6 key results, limits | Final presentation |
| Poster or one-pager | One figure per hypothesis family, headline numbers | Showcase |
| Code repository | Pipeline, tests, Makefile, tagged release | Reproducibility; portfolio |
| Derived data and data dictionary | Aggregated, pseudonymised tables only | Team, mentors, later cohorts |
| Gold set and codebook | 300 coded posts and the written rules | Validation; reuse |
| Weekly reports and assignments | Each aligned to a work package; fix the date and citation slips noted earlier | ILGC-3 requirements |

**Paper skeleton and where each section's content comes from.** Introduction and gap come from your Assignments 1 and 2. Theory comes from the history and contemporary tables in Assignment 2 plus the sources in section 16. Data and audit come from section 2. Measurement comes from sections 4 and 8. Results come from WP8 and WP9. Limits come from sections 9 and 12.

**The contribution statement (draft).** (1) A cleaned, audited dataset of about 20,000 leader-authored posts by about 500 Indian corporate leaders, with a documented extraction method; (2) a validated, transparent measurement set for projected leadership image, benchmarked against human coding and LLM scoring; (3) evidence on how the projected image varies with leader type, gender, function and firm context, with effect sizes and honest uncertainty; (4) open code that others can apply to other leader groups.

## 14. Decisions needed from you and the mentors

1. **Success variable.** Keep the headline about voice, with firm performance and awards as a secondary associational layer (recommended), or make success the main outcome?
2. **Scope.** Indian corporate leaders on LinkedIn only (recommended), or add foreign leaders, political leaders or other platforms? The team asked to add foreign leaders. Prof Singh is deciding, and a meeting of the team with him is being set up for next week. Until he answers, the study stays on the Indian leaders already in the data.
3. **Scrape date.** On what date were the posts collected? Without it, relative ages (5yr, 3mo) cannot become dates.
4. **Provenance and approval.** Who scraped the data, under what process, and does Plaksha's ethics route cover analysis and publication?
5. **The 80-parameter catalog** from your Week 13 report. Please paste it so the variable list in section 6 can be reconciled.
6. **Gender coding policy.** Code from public self-presentation with an 'unclear' option, with a second person checking a sample, or skip gender and drop H2?
7. **LIWC-22 licence.** Does Plaksha hold one, or do we stay with open dictionaries?
8. **LLM budget and tools.** Which models and API access can the team use, and are provider no-training settings available?
9. **Team and roles.** The team is Marutey Mani, Janhavi, Shaurya and Murtaza. Nobody is assigned to a work package yet; that is decided later. Surnames for the three teammates are needed for the title page.
10. **Target venue.** A course report only, or a workshop or conference paper? This sets the pre-registration and release rules.
11. **Duplicate roster files.** The five `All_500` copies hold the same 653 people and differ only in collector notes, so the roster itself is not in doubt. Load it once, never add the copies together. The seventh\_100\_leaders copy has the most notes, so keep that one for them. Settled unless the mentors object.
12. **YouTube short.** The link you shared is a Starship video by Everyday Astronaut, which does not seem related to the project. Was it meant as something else?
13. **Company\_Data provenance and gender coding.** Rana Amanat Singh got this file from Anshika, so the source is known. Still open: when was it built, what do 1 and 0 mean in the Gender column, who coded it, and why are 192 values blank?
14. **Which list of people is the base.** All\_500 (653 people), the wordcount summaries (532) and Company\_Data (852) overlap only partly. Which one decides who is in the study?
15. **Trait list.** Keep Northouse's five as the main measures and add business knowledge, desire to lead and a task-versus-relational pair as exploratory (section 4)?
16. **Success layer.** With 2021 to 2024 revenue and profit in Company\_Data, do the mentors want firm performance as a secondary layer (option b in section 6)?
17. **Scraping and foreign leaders.** The team asked to scrape likes, reposts and followers and to add foreign leaders. Rana Amanat Singh has confirmed with Anshika that none of these is in the database. Does Prof Singh allow the scraping, under what approval, and for which of the three? Until he answers, nothing is scraped. Followers already exist in Company\_Data for about 70% of leaders with 15+ posts, and reaction counts may be recoverable from the trailing numbers in the raw post text, which the 50-post check in section 5 tests.
18. **Empty original columns.** The mail lists role\_start\_year and post\_date among the original variables. In the workbooks we have, both are empty, so tenure and exact post dates are missing. Is there another version of the data where they are filled?

## 15. First ten actions

- [ ] Send the section 14 questions to the mentors; paste the 80-parameter catalog into this chat.
- [ ] Create the repository with the layout in section 10; freeze the raw zip with a hash manifest.
- [ ] Build the leader ID table and resolve the roster-only and summary-only names.
- [ ] Load Company\_Data.xlsx, drop the contact columns, and match its 852 people to leader IDs (541 of our 544 leaders already match by name). Check the 5 repeated names and the 41 company mismatches by hand.
- [ ] Write down which of the original columns (leader\_name, company\_name, current\_title, role\_start\_year, ceo\_type, platform, post\_date, post\_date\_text) are filled in each workbook. role\_start\_year and post\_date are empty in the ones seen so far.
- [ ] Finalise the segmentation rules; hand-check 200 random cells and record the accuracy.
- [ ] Recover the 4 shifted-header sheets and write the sheet-skip log.
- [ ] Write the codebook for the constructs in section 4 and draw the 300-post gold sample.
- [ ] Two people code 50 gold posts, compare, and revise the codebook before coding the rest.
- [ ] Start the enrichment spreadsheet with the Must variables for the 271 leaders who have 15+ posts and a type label.
- [ ] Confirm the reaction-count format on 50 posts against LinkedIn.
- [ ] Request Plaksha ethics clearance and write `docs/ethics.md`.

## 16. Sources

**Opened and read for this plan**

- [Can LLMs Infer Personality from Real-World Conversations? (arXiv 2507.14355)](https://arxiv.org/pdf/2507.14355): 518 people, best Big Five correlation about 0.25, high test-retest but low accuracy, central-tendency bias.
- [The Big Two dictionaries (Pietraszkiewicz et al., 2019, Lancaster repository record)](https://eprints.lancs.ac.uk/id/eprint/134821): agency and communion dictionaries built in the LIWC style and validated; the record does not say whether they are openly available.
- [L3Cube-HingCorpus and HingBERT (arXiv 2204.08398)](https://arxiv.org/pdf/2204.08398): Hindi-English code-mixed corpus and public models.
- [Gilbert, Selling the Self: Personal Branding and Impression Management on LinkedIn](https://digitalcommons.georgiasouthern.edu/amtp-proceedings_2026/79/): qualitative content analysis of 250 posts by 50 professionals, Goffman framing.
- [Web Scraping and Personal Data: Legal and Ethical Boundaries in AI (Mondaq, India)](https://www.mondaq.com/india/new-technology/1625590/web-scraping-and-personal-data-legal-and-ethical-boundaries-in-ai): scraping not explicitly illegal in India; consent regime under the 2023 Act.

**Found in search, not opened (check before citing)**

- [Large language models can infer psychological dispositions of social media users (PNAS Nexus, 2024)](https://academic.oup.com/pnasnexus/article-pdf/3/6/pgae231/58356613/pgae231.pdf)
- [Linguistic Markers of Destructive Leadership (British Journal of Management)](https://onlinelibrary.wiley.com/doi/10.1111/1467-8551.70100)
- [CEO personality and firm policies (NBER working paper, Gow and coauthors)](https://www.nber.org/system/files/working_papers/w22435/w22435.pdf)
- [Making CEO narcissism research great: a review and meta-analysis](https://www.researchgate.net/publication/338281105_Making_CEO_Narcissism_Research_Great_A_Review_and_Meta-Analysis_of_CEO_Narcissism)
- [Appearing competent: impression management in US and European CEO profiles](https://www.researchgate.net/publication/254117712_Appearing_Competent_A_Study_of_Impression_Management_in_US_and_European_CEO_Profiles)
- [Gender differences in approaching sustainability: multinational CEOs on LinkedIn (thesis record)](https://door.donau-uni.ac.at/o:5741)
- [Grimmer and Stewart, Text as data (2013)](https://is.muni.cz/el/fss/podzim2017/MEB421/um/Grimmer_Stewart_2013.txt?lang=en)
- [Empath: topic signals in large-scale text](https://arxiv.org/pdf/1602.06979)
- [US appeals court says web scraping is legal (TechSpot, 2022)](https://www.techspot.com/news/94264-us-appeals-court-web-scraping-linkedin-profiles-legal.html)

**Your own materials used**

- Project handbook entry for FP15; Assignment 1 and Assignment 2; weekly reports for Weeks 11 and 13; Week 2 reading notes and meeting notes; the slides deck and the good-versus-bad leader PDF.
- The LEO Internship Report and the PPT\_Traits deck, plus the ChatGPT and Claude trait-scoring PDFs.
- The dataset zip: 7 batch folders, `All_500` roster files, `wordcount_*` summaries, `wordcount_2.py`.

**Method notes.** All counts in sections 2 and 7 come from scripts I ran on the zip (author segmentation, de-duplication, pronoun rates, group tests). The group comparisons are exploratory and unadjusted. The reaction-count reading, the date interpretation and the DPDP point are unverified and flagged as such.

**Update: shared by the mentors on 5 November (leadership traits)**

- Stogdill, R. M. (1948). Personal factors associated with leadership: A survey of the literature. Journal of Psychology, 25, 35 to 71. Not opened; the summary in section 3 is the standard account.
- Kirkpatrick, S. A. and Locke, E. A. (1991). Leadership: Do traits matter? Academy of Management Executive, 5(2), 48 to 60. Not opened.
- Judge, T. A., Bono, J. E., Ilies, R. and Gerhardt, M. W. (2002). Personality and leadership: A qualitative and quantitative review. Journal of Applied Psychology, 87(4), 765 to 780. Full text would not load; not opened.
- DeRue, D. S., Nahrgang, J. D., Wellman, N. and Humphrey, S. E. (2011). Trait and behavioral theories of leadership: An integration and meta-analytic test of their relative validity. Personnel Psychology, 64(1), 7 to 52. Abstract read ([Penn State record](https://pure.psu.edu/en/publications/trait-and-behavioral-theories-of-leadership-an-integration-and-me/)); paper not opened.
- Chatterjee, A. and Hambrick, D. C. (2007). It's all about me: Narcissistic CEOs and their effects on company strategy and performance. Administrative Science Quarterly, 52(3), 351 to 386. Read a [summary of the study](https://phys.org/news/2007-07-narcissistic-ceos-effect-corporate-strategy.html); paper not opened.
- Nadkarni, S. and Herrmann, P. (2010). CEO personality, strategic flexibility, and firm performance: The case of the Indian business process outsourcing industry. Academy of Management Journal, 53(5), 1050 to 1073. Abstract only; the abstract does not say how personality was measured. Paper not opened.
- Related and recent, found while checking, not read in full: Aabo and colleagues (2024), CEO personality traits, strategic flexibility, and firm dynamics (Journal of Corporate Finance).

Open each paper before quoting any number from it.

**Update mail.** Rana Amanat Singh's update to Prof Singh (shared 5 November) says the team met her twice in a week, narrowed to key leadership traits using frameworks such as Northouse's, asked to scrape extra variables and add foreign leaders, and that she obtained the company data from Anshika. Prof Singh's answer is awaited, and a meeting is being set up for next week.
