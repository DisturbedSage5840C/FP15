# Segmentation sample for gate G1

Counts only: no cell references, no ids, no post text. The sample itself is `data/derived/segmentation_check_200.csv` (git-ignored, it holds post text).

| Item | Value |
|---|---|
| Raw cells with a leader and some text | 26,945 |
| Leaders with at least one such cell | 563 |
| Cells required for the check | 200 |
| Seed | 20261107 |
| Cells in the sample file | 200 |
| Leaders in the sample file | 200 |
| Cells with a human count filled in | 200 |
| Sample matches a fresh draw from the seed | yes |

The draw takes one cell per leader where it can, from sorted cells with the seed above, so the same seed gives the same sample. The sample holds no machine count, so the human count is blind.

G1 is not signed. A person counts the posts in each cell, then `make segmentation-score` compares those counts with the segmenter. The sign-off line goes in `docs/decisions.md` and is a human job.
