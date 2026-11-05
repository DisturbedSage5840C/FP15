Read CLAUDE.md first. We are starting work package 0 and 1 of the FP15 project.

Step 0 (safety check, do this first): run `git check-ignore -v data/raw/Company_Data.xlsx data/raw/Linkdln_posts_data_1.zip` and confirm both are ignored. If either is not, stop and tell me. Do not scrape or download anything at any point; scraping is not approved.

Step 1 (set up): create the Python project (pyproject or requirements, src/, tests/), a verify step that writes data/raw/MANIFEST.sha256 on first run and checks it afterwards, and a loader that logs every sheet it skips. Do not touch the files in data/raw.

Step 2 (look before building): list every file in data/raw, open the zip, and write reports/data_inventory.md with: each file, its sheets, the header layout of each sheet, row counts, and the 4 odd sheets that do not follow the main layout. For each workbook also report which of these columns are present and how many are non-empty: leader_name, company_name, current_title, role_start_year, ceo_type, platform, post_date, post_date_text (I expect role_start_year and post_date to be empty). Show me the inventory before you write the harmonising code.

Step 3 (Company_Data): load data/raw/Company_Data.xlsx, drop all email and phone columns immediately, treat "." and "-" as blank, parse values like "186.6M" and "2.5B", and write reports/company_data_profile.md (rows, columns, blanks per column, duplicate names, duplicate profile links). Do not decode the Gender column; just report its counts.

Step 4 (IDs): propose leader_id matches across the three people lists (the five All_500 roster files, the wordcount summaries, Company_Data) using sorted-token name matching. Output a table of matched, ambiguous and unmatched names for me to resolve by hand. Do not auto-resolve ambiguous ones.

Rules: log surprises in docs/decisions.md under Findings. Stop and ask before anything that changes what a variable means. Commit after each step.
