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
9. Which list of people is the base (All_500 roster files, summaries, Company_Data).
10. Company_Data.xlsx came from Anshika via the data owner. Still open: when it was built and who coded Gender.
11. Trait list: Northouse's five plus three exploratory measures?
12. Scraping likes, reposts and followers: allowed or not, under what approval? Nothing is scraped until the course mentors decides.
13. Are role_start_year and post_date filled in another version of the data? Both are empty in the workbooks seen so far.

## Findings
(Claude Code: log surprises here.)

- 2026-11-05: The two files added to the project root (Company_Data.xlsx, Linkdln_posts_data_1.zip) were byte-identical to the copies in data/raw (same sha256 as MANIFEST.sha256). The root copies were deleted on request; data/raw is unchanged and its manifest still verifies.
- 2026-11-05: Inside Linkdln_posts_data_1.zip, Linkdln_posts_data/Third_100_leaders/All_500.xlsx and Linkdln_posts_data/Fourth_100_leaders/All_500.xlsx are byte-identical (same sha256). data/raw is read-only, so nothing was removed. Open for the team: which folder is the true owner of this roster, and whether a wrong file was copied in. Ingest must not count both, or those leaders would be double-counted.
