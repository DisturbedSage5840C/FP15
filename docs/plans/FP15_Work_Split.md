# FP15 Work Split: Claude Code, Claude Chat, the Team and the Mentors

Written 3 November 2026. Final update 17 November 2026.

**Team.** Marutey Mani, Janhavi, Shaurya and Murtaza. Mentors: Prof. Prakarsh Singh, Prof. Rajesh Sharma and Rana Amanat Singh.

This is the companion to the Master Plan (docs/plans/FP15_Master_Plan.md). The plan says what to do; this page says who does which part now that the build moves into Claude Code. Nobody on the team is assigned to a work package here. "The team" means the four of you as people, because some jobs only a person can do.

**Update, 5 November.** The mentors sent a second data file (Company_Data.xlsx), six studies on leadership traits, and Rana Amanat Singh's update mail to Prof Singh. The file covers most leader details we planned to collect by hand, so work packages 1 and 3 change. The mail says the team asked to scrape likes, reposts and followers and to add foreign leaders; Prof Singh decides, so nothing is scraped and the study stays on Indian leaders until he answers. Two new questions go to the mentors in section 4, and three studies still need a person to open them. The Master Plan has the full reasoning.

**Final update, 17 November.** Status of each lane, with nobody assigned to a task by name.

- **Claude Code (done).** Repo layout, Makefile, thresholds file and hash manifest; sheet harmonising; Company_Data loaded without contact columns; keyed leader ids; conservative de-duplication; post cleaning; committed count reports. The repo is public and carries no data, names, post text, links or reversible ids.
- **Claude Code (next).** Segmentation into author blocks with tests, then the 200-cell sample file for gate G1; after sign-off, Layer 1 dictionary measures. No scraping until Prof Singh approves in writing.
- **Claude chat (done).** Research question for Assignment 3, the five-slide mentor deck, the Literature Review first draft, mentor emails, and the updated plan pages.
- **Claude chat (next).** Revise the Literature Review after the tutor review, draft the codebook and the 300-post gold sample brief, and keep this plan and the Master Plan in step with the repo.
- **Jobs only people can do.** The 200-cell segmentation check, the 50-post reaction check on LinkedIn, the 29 Hinglish rows, the Company_Data name hand-check, coding the gold set, and signing off gates G1 to G4.
- **Mentors.** Prof Singh decides on scraping and foreign leaders. Open questions: scraping route, what 1 and 0 mean in Gender, the collection date, and the fiscal years behind the 2021 to 2024 figures.
- **Deadlines.** Five-slide deck for the next mentor meeting; Literature Review first draft at the Monday tutorial, final on 29 November, 11:59 PM.

## 1. The four lanes

| Lane | Where it lives | Good at | Should not be left to it |
| --- | --- | --- | --- |
| Claude Code | The project repo on your computer, opened in Claude Code | Writing and running the pipeline, tests, tables and figures from scripts; long runs over all posts; keeping everything reproducible | Deciding what a construct means, coding gold-set posts, verifying facts about leaders, ethics calls |
| Claude chat | This project chat, plus the Docs, decks and weekly reports | Planning, reading papers and reports, drafting the codebook, weekly reports, slides, mentor emails, checking the plan against new findings | Running the full pipeline, or being the only copy of any decision |
| The team | You four, as people | Judgment: coding the gold set, reading raw posts, verifying leader details, writing the claims, signing off every gate | Nothing here is automatic, and nobody should skip reading real posts |
| Mentors | Meetings, email and the weekly report | Decisions the data cannot make: scope, success variable, scrape date, ethics route, venue | Day-to-day coding questions |

## 2. Split by work package

Work package numbers are the same as in section 11 of the Master Plan.

| WP | Claude Code | The team (as people) | Mentors and Claude chat |
| --- | --- | --- | --- |
| 0 Setup | Creates the repo layout, Makefile, thresholds.yaml and a hash manifest of the raw zip | Sends the open questions; agrees the ethics request | Mentors answer scope, success variable, scrape date, provenance. Prof Singh decides on scraping and foreign leaders. Chat drafts the questions and the ethics request |
| 1 Ingest and ID table | Loads the 5 header layouts, recovers the 4 odd sheets, logs skipped sheets, loads Company_Data.xlsx without its contact columns, and proposes name matches across All_500, the summaries and Company_Data | Resolves the 265 roster-only and 148 summary-only names by hand, plus the 5 repeated names and about 41 company mismatches in Company_Data | Mentors say which list decides who is in the study (All_500, the summaries or Company_Data). Chat reviews the matching rules |
| 2 Segment and clean | Splits each cell into author blocks, cleans text, parses ages, flags quality, removes duplicates, writes tests | Hand-checks 200 random cells and signs off gate G1 | Mentors confirm the scrape date |
| 3 Enrich leader table | Takes gender, sector, firm size, firm age and followers from Company_Data, parses the text values, flags blanks and mismatches. Builds a sheet with source links only for what is still missing (tenure, education, ownership) | Spot-checks about 20% of the Company_Data values and verifies every value that enters the analysis. Codes gender from public self-presentation, with an 'unclear' option, only if the file's coding is not confirmed | Mentors say who built Company_Data, when, and what 1 and 0 mean in its Gender column, and settle the gender coding policy. Chat drafts the coding rules |
| 4 Codebook and gold set | Draws the stratified 300-post sample, computes Krippendorff's alpha | Two people code every post; the codebook is revised until alpha is 0.67 or higher | Chat drafts the first codebook from section 4 of the plan, with business knowledge, desire to lead and a task-versus-relational pair as exploratory measures if the mentors approve |
| 5 Measures | Dictionaries, embeddings, topics, style and templating scores; checks them against the gold set | Reads the top and bottom 20 posts of each measure; each of us reads at least 100 posts from 20 or more leaders | Mentors answer the LIWC licence question. Chat finds and reads the lexicon papers |
| 6 LLM judge | Prompt runner, repeat runs, agreement report | Approves the prompts; decides whether the judge is kept or dropped | Mentors say which models and budget are allowed |
| 7 Pre-registration | Locks the hypothesis and analysis files with a dated hash | Writes and signs off the pre-registration text | Chat drafts it. Mentors review |
| 8 and 9 Analysis | Runs the models, false discovery rate control, the robustness runs and all figures from scripts | Reads results critically, decides what is a finding and what is noise | Chat reviews interpretation against the literature |
| 10 Writing | Writes the table and figure scripts | Writes the paper and the claims | Chat drafts text, slides and weekly reports. Mentors review |
| 11 Release | Tags the repo and exports the derived tables and data dictionary | Final check of what leaves the project | Mentors confirm ethics clearance covers release |

## 3. Jobs only people should do

- Coding the gold set, and revising the codebook after the first 50 posts.
- Reading raw posts. Dictionaries miss sarcasm, quotation and Hinglish, and only reading shows it.
- Verifying every leader detail that enters the analysis (gender, sector, firm size, tenure). Company_Data supplies most of them, so check a sample of about 20% instead of collecting. Every firm in it is listed. Missing stays missing; nothing is guessed from names.
- Signing off each gate: G1 segmentation, G2 measures against the gold set, G3 pre-registration, G4 clean rebuild.
- Deciding what the results mean, and writing the claims. Every claim says 'projected in public posts', never 'personality'.
- Asking for ethics clearance and handling any removal request from a leader or company.
- Opening the three studies Claude chat could not read in full (Stogdill 1948, Kirkpatrick and Locke 1991, Judge and colleagues 2002) before any number from them is quoted. Chat read only abstracts or summaries of the other three.
- Confirming that the copy of Company_Data used by the team has no email addresses or phone numbers.

## 4. Questions only the mentors can answer

1. On what date were the posts collected? Without it, ages like 5yr cannot become dates.
2. Who scraped the data, under what approval, and does Plaksha's ethics route cover analysis and publication?
3. Scope: Indian corporate leaders on LinkedIn only, or also foreign leaders? The team asked for foreign leaders. Prof Singh decides, at a meeting being set up for next week.
4. Success variable: keep the headline about voice, with firm performance as a secondary layer? Company_Data now has 2021 to 2024 revenue and profit, so this layer is practical.
5. Gender coding policy, or drop H2. Company_Data has a Gender column (1 for 602 people, 0 for 58, blank for 192) with no stated meaning or source.
6. LIWC-22 licence, or open dictionaries only.
7. Which LLMs and budget, and whether no-training settings are available.
8. Target venue: course report only, or a workshop or conference paper.
9. Which list of people is the base: the All_500 roster (653 people; its five copies are the same list), the summaries (532) or Company_Data (852).
10. Who built Company_Data.xlsx, when, and from what source?
11. Trait list: keep Northouse's five as the main measures and add business knowledge, desire to lead and a task-versus-relational pair as exploratory?
12. Scraping likes, reposts and followers from LinkedIn: allowed or not, and under what approval? Until Prof Singh decides, nothing is scraped.
13. Are role_start_year and post_date filled in another version of the data? Both are empty in the workbooks we have.

One item is on Marutey, not the mentors: the 80-parameter catalog from the Week 13 report.

## 5. Handoff rules between Claude chat and Claude Code

- The repo is the source of truth for code and numbers. Every decision that changes results is written in docs/decisions.md with a date; the chat copy is only a summary.
- Claude Code reads CLAUDE.md at the start of every session, so the pass marks and rules live there and nowhere else.
- Numbers move from the repo to the chat as committed reports, not as pasted screenshots.
- Analysis files that leave the repo carry leader IDs only, never names. Raw post text is not pasted into public places.
- Any LLM call sends only the post text and an ID, with no-training settings on where the provider offers them.
- The gold set stays closed while dictionaries are built, so the validation is honest.
- Every gate needs a human sign-off line in docs/decisions.md before work moves past it.
- Company_Data.xlsx holds personal emails and phone numbers. The load script drops them, and the original file stays out of the repo and out of anything shared.

## 6. What goes in CLAUDE.md

- The research question and the claim limit: image projected in public posts, not real personality.
- The data rules: data/raw is read-only, never edited; no scraping or network downloads of new post data.
- Thresholds: 15 posts minimum for the main analysis, 95% segmentation accuracy, alpha 0.67, dictionary-to-human correlation about 0.4. All of them live in configs/thresholds.yaml.
- The four gates and what each one needs.
- The ethics rules from section 9 of the plan.
- How to run things: one make command per stage, and one that rebuilds every table and figure from the raw files.
- Company_Data rules: contact columns dropped at load; '.' and '-' count as blank; gender used exactly as coded in the file until the mentors confirm what 1 and 0 mean; text values such as '186.6M' parsed in one place.
- Study scope: Indian corporate leaders only, and no scraping of anything, until Prof Singh approves in writing.

## 7. First steps in Claude Code, in order

1. [Mentors] Receive the open questions from section 4.
2. [Claude Code] Create the repo layout and freeze the raw zip with a hash manifest.
3. [Claude Code] Harmonise the sheets and write the sheet-skip log.
4. [Claude Code, then the team] Load Company_Data.xlsx without its contact columns and propose leader name matches across the three people lists; the team resolves what is left by hand, including the 5 repeated names.
5. [Claude Code, then the team] Segmentation rules with tests; the team hand-checks 200 cells for gate G1.
6. [Claude chat and the team] Write the codebook and draw the 300-post gold sample.
7. [The team] Code the first 50 gold posts in pairs and revise the codebook.
8. [Claude Code] Build Layer 1 measures and validate them against the gold set.

## 8. Still open

- The 80-parameter catalog from the Week 13 report.
- The scrape date and the thirteen mentor questions in section 4.
- Who on the team has write access to the public repo.
- Whether 1 means male and 0 female in the Company_Data Gender column, and why 192 values are blank.
- Whether firm performance becomes a secondary layer, now that Company_Data has the figures.
