# Decisions and sign-offs

Format: date, who decided, what, why. Gate sign-offs need a human name.

## Gates
- [ ] G1 segmentation (95% on 200 cells): not signed
- [ ] G2 measures vs gold set: not signed
- [ ] G3 pre-registration: not signed
- [ ] G4 clean rebuild: not signed

## Decisions
- 2026-11-05: Company_Data.xlsx added (852 people, 533 companies). Contact columns are dropped at load. the data owner got it from Anshika.
- 2026-11-05: the data owner's update to the course mentors: the team narrowed to key leadership traits (Northouse and similar), asked to scrape likes, reposts, followers and to add foreign leaders. Anshika confirmed none of these is in the database. the course mentors has not decided. Until he does: no scraping, Indian leaders only. A meeting with him is planned for next week.

## Open questions for the mentors
1. Date the posts were collected.
2. Who scraped the data, under what approval; does the ethics route cover analysis and publication.
3. Scope: Indian corporate leaders on LinkedIn only, or also foreign leaders (the team asked). the course mentors decides.
4. Success variable: voice as headline, firm performance as secondary layer.
5. Gender coding policy, or drop H2. What do 1 and 0 mean in Company_Data's Gender column.
6. LIWC-22 licence, or open dictionaries only.
7. Which LLMs and budget; no-training settings available?
8. Target venue.
9. SETTLED 2026-11-05 (project owner): the base roster is seventh_100_leaders/All_500.xlsx, loaded once (see Findings). Matching the wordcount summaries and Company_Data against it is still Step 4, to be resolved by hand.
10. Company_Data.xlsx came from Anshika via the data owner. Still open: when it was built and who coded Gender.
11. Trait list: Northouse's five plus three exploratory measures?
12. Scraping likes, reposts and followers: allowed or not, under what approval? Nothing is scraped until the course mentors decides.
13. Are role_start_year and post_date filled in another version of the data? Both are empty in the workbooks seen so far.

## Findings
(Claude Code: log surprises here.)

- 2026-11-05: The two files added to the project root (Company_Data.xlsx, Linkdln_posts_data_1.zip) were byte-identical to the copies in data/raw (same sha256 as MANIFEST.sha256). The root copies were deleted on request; data/raw is unchanged and its manifest still verifies.
- 2026-11-05: There are five All_500.xlsx roster files in Linkdln_posts_data_1.zip (Third, Fourth, Fifth, Sixth, seventh folders). Third and Fourth are byte-identical. All five hold the same 653 people: columns CompanyName, Person_Name, Current_Title, LinkedIn_Profile_Link and person_id are identical in every copy (checked by Claude Code: 653 unique person_id, none blank). They differ only in free-text collector notes in stray cells beyond column E (2 to 6 non-empty cells per file; the Sixth and seventh files tie at 6). The notes look like scrape-depth hints. data/raw is read-only, so nothing was removed. Rule for ingest (project owner, 2026-11-05): load the roster ONCE from seventh_100_leaders/All_500.xlsx, never concatenate the five copies, keep the stray-cell notes as metadata.
- 2026-11-05 (Step 2 inventory, numbers in reports/data_inventory.md, nothing fixed or filled): `role_start_year` and `post_date` are NOT empty everywhere, which answers part of open question 13. In the 700 standard 14-column sheets, `post_date` has 9 of 32,266 values and `role_start_year` 1. A separate extra column headed `Post date` (not `post_date`) is filled in the wordcount sheets: 29,256 of 30,994 rows in the 541 standard wordcount sheets, plus 390 of 617 in off-layout sheets. What that column means, and whether it is the post date, is a construct decision for the project owner. Not touched.
- 2026-11-05 (Step 2): FIRST_PROMPT names "4 odd sheets", but the survey finds 25 of 1,285 sheets with some oddity: 14 off-layout, 2 with no header row (first row is data), 1 blank, 8 on a known layout with stray cells or blank columns. Which four were meant is for the project owner to say.
- 2026-11-05 (Step 2): Off-layout variants seen: 13-column sheets without `post_date_text`; 11-column wordcount sheets without `post_date_text`; a sheet without `post_text`; 5-column sheets headed `Link to the post (if available)`; an 18-column and a 16,382-column wordcount sheet padded with `Unnamed:` columns; a 9-column sheet with `scraped_date` instead of the summary layout. Stray non-empty cells beyond the header also occur (16,370 on one 16,384-column sheet in 600_file2.xlsx, 1 to 6 elsewhere, including all five All_500 roster files).
- 2026-11-05 (Step 2): `leader_name`, `company_name`, `current_title`, `ceo_type` and `platform` are filled on only 14,474 of 32,266 rows in the standard sheets (14,236 of 30,994 in the wordcount sheets), and 274 sheets have no leader value at all. Not forward-filled: whether blank means "same leader as the row above" is for the project owner to confirm. Author blocks per sheet are counts of runs of the exact leader text; 11 sheets have more blocks than distinct keys.
- 2026-11-05 (Step 2): Company_Data.xlsx has 852 data rows and 129 columns. Contact columns by header name: Email, KeyPeopleEmailIds, CompanyEmails, CompanyPhoneNumbers (dropped at load in Step 3). Single-letter headers Q, V and Z have unknown meaning.
