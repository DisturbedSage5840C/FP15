# Segmentation check (counts only)

Machine post count per raw cell versus the human count, on the hand-checked sample. Row detail is in a git-ignored file, by sample row number.

| Measure | Value |
|---|---|
| Rows in the sample file | 200 |
| Cells with a human count | 200 |
| Rows without a human count | 0 |
| Exact matches | 200 |
| Accuracy (exact matches / cells with a human count) | 1.000 |
| Threshold (configs/thresholds.yaml) | 0.95 |
| At or above threshold | yes |
| Machine found lower count than human | 0 |
| Machine found higher count than human | 0 |

## By the machine's post count

| Machine posts | Cells | Exact matches |
|---|---|---|
| 1 | 200 | 200 |

This report does not sign off G1. G1 needs a human sign-off line in docs/decisions.md.
