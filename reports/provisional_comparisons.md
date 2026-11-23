> PROVISIONAL. G1 unsigned so raw cells stand in for posts; English-only pronoun counts; no gold-set check; exploratory, not pre-registered. Claims are about the image projected in public posts, never personality. The I-rate is one signal, not a narcissism score.

# Provisional group comparisons

Every result below is exploratory. Nothing is pre-registered, no gate is signed, and a p-value says nothing about causes.

- Gender, sector and firm size come from the leader master (data/interim/leader_master.csv). ceo_type and title family come from the post sheets, because the master carries neither. Gender words come from configs/gender_coding.yaml; a blank stays missing and nothing is inferred from a name. Leaders with no usable company match are labelled as such.
- A count under 5 shows as "<5". A hidden group is paired with a partner group that is hidden too (an unknown-value group where there is one), so no hidden count can be worked out by subtraction. Groups with fewer than 20 leaders are marked "too small to model".
- Models: one random intercept per leader, fitted by REML. The first model has ceo_type, title family, gender and firm size band, and takes every leader in the analysis sample with a known gender, a Founder-CEO or Professional CEO ceo_type and a size band. The second adds sector for the leaders whose sector is known, with sectors under 20 leaders pooled into one "other sectors" group instead of dropped. The leader-level share of variance is leader variance over leader plus cell variance. Tests are joint Wald tests per factor from one fit.
- Benjamini-Hochberg is applied once across every comparison in the last table: both models, both measures and both cell sets together.
- A factor column that repeats an earlier factor is dropped, and the lost degrees of freedom are in the note.

## Leaders and shrunk rates per group (exploratory)

### Founder vs professional CEO

| group | measure | cell set | leaders | min | q1 | median | q3 | max | modelling |
|---|---|---|---|---|---|---|---|---|---|
| Founder-CEO | first-person singular (I-rate) | all cells | 53 | 0.03 | 0.36 | 0.62 | 1.17 | 8.39 |  |
| Founder-CEO | first-person singular (I-rate) | without possible-Hinglish cells | 53 | 0.03 | 0.36 | 0.62 | 1.17 | 8.39 |  |
| Founder-CEO | first-person plural (we-rate) | all cells | 53 | 0.32 | 0.99 | 1.25 | 1.69 | 2.93 |  |
| Founder-CEO | first-person plural (we-rate) | without possible-Hinglish cells | 53 | 0.32 | 0.99 | 1.25 | 1.69 | 2.94 |  |
| Professional CEO | first-person singular (I-rate) | all cells | 263 | 0.04 | 0.33 | 0.63 | 1.11 | 11.90 |  |
| Professional CEO | first-person singular (I-rate) | without possible-Hinglish cells | 263 | 0.04 | 0.33 | 0.63 | 1.11 | 11.90 |  |
| Professional CEO | first-person plural (we-rate) | all cells | 263 | 0.23 | 0.73 | 1.15 | 1.63 | 3.67 |  |
| Professional CEO | first-person plural (we-rate) | without possible-Hinglish cells | 263 | 0.23 | 0.73 | 1.15 | 1.63 | 3.67 |  |
| no value | first-person singular (I-rate) | all cells | 11 | 0.20 | 0.39 | 0.64 | 1.27 | 6.88 | too small to model |
| no value | first-person singular (I-rate) | without possible-Hinglish cells | 11 | 0.20 | 0.39 | 0.64 | 1.27 | 6.88 | too small to model |
| no value | first-person plural (we-rate) | all cells | 11 | 0.41 | 0.94 | 1.29 | 1.64 | 5.43 | too small to model |
| no value | first-person plural (we-rate) | without possible-Hinglish cells | 11 | 0.41 | 0.94 | 1.29 | 1.65 | 5.43 | too small to model |

### Title family

| group | measure | cell set | leaders | min | q1 | median | q3 | max | modelling |
|---|---|---|---|---|---|---|---|---|---|
| CEO | first-person singular (I-rate) | all cells | 122 | 0.05 | 0.35 | 0.62 | 1.19 | 4.12 |  |
| CEO | first-person singular (I-rate) | without possible-Hinglish cells | 122 | 0.05 | 0.35 | 0.62 | 1.19 | 4.12 |  |
| CEO | first-person plural (we-rate) | all cells | 122 | 0.23 | 0.99 | 1.41 | 1.79 | 3.67 |  |
| CEO | first-person plural (we-rate) | without possible-Hinglish cells | 122 | 0.23 | 0.99 | 1.41 | 1.79 | 3.67 |  |
| Chair | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Chair | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Chair | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Chair | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Founder | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Founder | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Founder | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Founder | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Managing director | first-person singular (I-rate) | all cells | 60 | 0.03 | 0.34 | 0.56 | 1.05 | 8.39 |  |
| Managing director | first-person singular (I-rate) | without possible-Hinglish cells | 60 | 0.03 | 0.34 | 0.56 | 1.05 | 8.39 |  |
| Managing director | first-person plural (we-rate) | all cells | 60 | 0.31 | 0.73 | 1.17 | 1.57 | 2.91 |  |
| Managing director | first-person plural (we-rate) | without possible-Hinglish cells | 60 | 0.31 | 0.73 | 1.17 | 1.57 | 2.91 |  |
| Other chief officer | first-person singular (I-rate) | all cells | 112 | 0.04 | 0.30 | 0.71 | 1.13 | 11.90 |  |
| Other chief officer | first-person singular (I-rate) | without possible-Hinglish cells | 112 | 0.04 | 0.30 | 0.71 | 1.13 | 11.90 |  |
| Other chief officer | first-person plural (we-rate) | all cells | 112 | 0.28 | 0.68 | 0.94 | 1.32 | 3.61 |  |
| Other chief officer | first-person plural (we-rate) | without possible-Hinglish cells | 112 | 0.28 | 0.69 | 0.94 | 1.32 | 3.61 |  |
| Other title | first-person singular (I-rate) | all cells | 17 | 0.19 | 0.24 | 0.54 | 1.01 | 2.37 | too small to model |
| Other title | first-person singular (I-rate) | without possible-Hinglish cells | 17 | 0.19 | 0.24 | 0.54 | 1.01 | 2.37 | too small to model |
| Other title | first-person plural (we-rate) | all cells | 17 | 0.55 | 0.70 | 0.87 | 1.83 | 2.16 | too small to model |
| Other title | first-person plural (we-rate) | without possible-Hinglish cells | 17 | 0.55 | 0.70 | 0.87 | 1.83 | 2.16 | too small to model |
| President | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| President | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| President | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| President | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no title | first-person singular (I-rate) | all cells | 11 | 0.20 | 0.39 | 0.64 | 1.27 | 6.88 | too small to model |
| no title | first-person singular (I-rate) | without possible-Hinglish cells | 11 | 0.20 | 0.39 | 0.64 | 1.27 | 6.88 | too small to model |
| no title | first-person plural (we-rate) | all cells | 11 | 0.41 | 0.94 | 1.29 | 1.64 | 5.43 | too small to model |
| no title | first-person plural (we-rate) | without possible-Hinglish cells | 11 | 0.41 | 0.94 | 1.29 | 1.65 | 5.43 | too small to model |

### Gender (as coded)

| group | measure | cell set | leaders | min | q1 | median | q3 | max | modelling |
|---|---|---|---|---|---|---|---|---|---|
| man | first-person singular (I-rate) | all cells | 228 | 0.03 | 0.33 | 0.61 | 1.10 | 11.90 |  |
| man | first-person singular (I-rate) | without possible-Hinglish cells | 228 | 0.03 | 0.33 | 0.61 | 1.11 | 11.90 |  |
| man | first-person plural (we-rate) | all cells | 228 | 0.23 | 0.71 | 1.12 | 1.58 | 5.43 |  |
| man | first-person plural (we-rate) | without possible-Hinglish cells | 228 | 0.23 | 0.71 | 1.12 | 1.59 | 5.43 |  |
| no usable company match | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no value | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| no value | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| no value | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| no value | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| woman | first-person singular (I-rate) | all cells | 30 | 0.04 | 0.53 | 0.77 | 1.39 | 6.88 |  |
| woman | first-person singular (I-rate) | without possible-Hinglish cells | 30 | 0.04 | 0.53 | 0.77 | 1.39 | 6.88 |  |
| woman | first-person plural (we-rate) | all cells | 30 | 0.28 | 0.75 | 1.15 | 1.53 | 3.02 |  |
| woman | first-person plural (we-rate) | without possible-Hinglish cells | 30 | 0.28 | 0.75 | 1.15 | 1.53 | 3.02 |  |

A group is hidden when it is under the disclosure minimum, and a group with at least the minimum is shown, so the woman group is shown when it has enough leaders. A group may still be hidden for another reason: when one group is under the minimum, the printed total would give its count away by subtraction, so a partner group is hidden with it. The partner is a group of unknown gender where there is one, otherwise the next smallest group, and the hidden groups together always reach the minimum.

### Sector

| group | measure | cell set | leaders | min | q1 | median | q3 | max | modelling |
|---|---|---|---|---|---|---|---|---|---|
| Aerospace, Maritime and Defense | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense Tech | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense Tech | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense Tech | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Aerospace, Maritime and Defense Tech | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto Tech | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto Tech | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto Tech | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Auto Tech | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Business Services | first-person singular (I-rate) | all cells | 33 | 0.03 | 0.30 | 0.60 | 1.25 | 2.86 |  |
| Business Services | first-person singular (I-rate) | without possible-Hinglish cells | 33 | 0.03 | 0.30 | 0.60 | 1.25 | 2.86 |  |
| Business Services | first-person plural (we-rate) | all cells | 33 | 0.32 | 0.78 | 1.01 | 1.42 | 2.75 |  |
| Business Services | first-person plural (we-rate) | without possible-Hinglish cells | 33 | 0.32 | 0.78 | 1.01 | 1.42 | 2.75 |  |
| Chemicals and Materials | first-person singular (I-rate) | all cells | 11 | 0.26 | 0.50 | 0.82 | 1.22 | 2.05 | too small to model |
| Chemicals and Materials | first-person singular (I-rate) | without possible-Hinglish cells | 11 | 0.26 | 0.50 | 0.82 | 1.22 | 2.05 | too small to model |
| Chemicals and Materials | first-person plural (we-rate) | all cells | 11 | 0.28 | 1.03 | 1.33 | 1.62 | 2.19 | too small to model |
| Chemicals and Materials | first-person plural (we-rate) | without possible-Hinglish cells | 11 | 0.28 | 1.03 | 1.33 | 1.62 | 2.19 | too small to model |
| Conglomerates | first-person singular (I-rate) | all cells | 7 | 0.16 | 0.92 | 1.05 | 1.43 | 2.24 | too small to model |
| Conglomerates | first-person singular (I-rate) | without possible-Hinglish cells | 7 | 0.16 | 0.92 | 1.05 | 1.43 | 2.24 | too small to model |
| Conglomerates | first-person plural (we-rate) | all cells | 7 | 0.30 | 0.98 | 1.73 | 2.11 | 2.61 | too small to model |
| Conglomerates | first-person plural (we-rate) | without possible-Hinglish cells | 7 | 0.30 | 0.98 | 1.73 | 2.11 | 2.61 | too small to model |
| Consumer | first-person singular (I-rate) | all cells | 10 | 0.09 | 0.44 | 0.54 | 0.98 | 1.78 | too small to model |
| Consumer | first-person singular (I-rate) | without possible-Hinglish cells | 10 | 0.09 | 0.45 | 0.54 | 0.98 | 1.78 | too small to model |
| Consumer | first-person plural (we-rate) | all cells | 10 | 0.37 | 0.77 | 1.26 | 1.73 | 2.35 | too small to model |
| Consumer | first-person plural (we-rate) | without possible-Hinglish cells | 10 | 0.37 | 0.77 | 1.26 | 1.73 | 2.35 | too small to model |
| Consumer Goods | first-person singular (I-rate) | all cells | 22 | 0.06 | 0.64 | 0.85 | 1.25 | 1.67 |  |
| Consumer Goods | first-person singular (I-rate) | without possible-Hinglish cells | 22 | 0.06 | 0.64 | 0.85 | 1.25 | 1.67 |  |
| Consumer Goods | first-person plural (we-rate) | all cells | 22 | 0.32 | 0.73 | 1.25 | 1.53 | 2.93 |  |
| Consumer Goods | first-person plural (we-rate) | without possible-Hinglish cells | 22 | 0.32 | 0.73 | 1.25 | 1.53 | 2.94 |  |
| EdTech | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| EdTech | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| EdTech | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| EdTech | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Education | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Education | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Education | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Education | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Energy | first-person singular (I-rate) | all cells | 14 | 0.15 | 0.48 | 0.73 | 1.12 | 1.45 | too small to model |
| Energy | first-person singular (I-rate) | without possible-Hinglish cells | 14 | 0.15 | 0.48 | 0.73 | 1.12 | 1.45 | too small to model |
| Energy | first-person plural (we-rate) | all cells | 14 | 0.32 | 0.67 | 0.99 | 1.22 | 2.01 | too small to model |
| Energy | first-person plural (we-rate) | without possible-Hinglish cells | 14 | 0.32 | 0.67 | 0.99 | 1.22 | 2.01 | too small to model |
| Energy Tech | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Energy Tech | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Energy Tech | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Energy Tech | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Enterprise Applications | first-person singular (I-rate) | all cells | 6 | 0.05 | 0.15 | 0.41 | 0.67 | 1.89 | too small to model |
| Enterprise Applications | first-person singular (I-rate) | without possible-Hinglish cells | 6 | 0.05 | 0.15 | 0.41 | 0.67 | 1.89 | too small to model |
| Enterprise Applications | first-person plural (we-rate) | all cells | 6 | 0.36 | 0.49 | 0.61 | 0.71 | 0.84 | too small to model |
| Enterprise Applications | first-person plural (we-rate) | without possible-Hinglish cells | 6 | 0.36 | 0.49 | 0.61 | 0.71 | 0.85 | too small to model |
| Environment | first-person singular (I-rate) | all cells | 5 | 0.19 | 0.60 | 1.59 | 2.14 | 2.37 | too small to model |
| Environment | first-person singular (I-rate) | without possible-Hinglish cells | 5 | 0.19 | 0.60 | 1.59 | 2.14 | 2.37 | too small to model |
| Environment | first-person plural (we-rate) | all cells | 5 | 0.55 | 1.16 | 1.73 | 1.80 | 2.26 | too small to model |
| Environment | first-person plural (we-rate) | without possible-Hinglish cells | 5 | 0.55 | 1.16 | 1.73 | 1.80 | 2.26 | too small to model |
| FinTech | first-person singular (I-rate) | all cells | 25 | 0.04 | 0.43 | 0.61 | 1.05 | 4.49 |  |
| FinTech | first-person singular (I-rate) | without possible-Hinglish cells | 25 | 0.04 | 0.43 | 0.61 | 1.05 | 4.49 |  |
| FinTech | first-person plural (we-rate) | all cells | 25 | 0.38 | 0.71 | 1.17 | 1.66 | 3.02 |  |
| FinTech | first-person plural (we-rate) | without possible-Hinglish cells | 25 | 0.38 | 0.71 | 1.17 | 1.66 | 3.02 |  |
| Financial Services | first-person singular (I-rate) | all cells | 51 | 0.05 | 0.32 | 0.55 | 0.91 | 6.88 |  |
| Financial Services | first-person singular (I-rate) | without possible-Hinglish cells | 51 | 0.05 | 0.32 | 0.55 | 0.91 | 6.88 |  |
| Financial Services | first-person plural (we-rate) | all cells | 51 | 0.43 | 0.79 | 1.18 | 1.69 | 5.43 |  |
| Financial Services | first-person plural (we-rate) | without possible-Hinglish cells | 51 | 0.43 | 0.79 | 1.18 | 1.69 | 5.43 |  |
| Food and Agriculture | first-person singular (I-rate) | all cells | 16 | 0.09 | 0.27 | 0.86 | 1.25 | 2.28 | too small to model |
| Food and Agriculture | first-person singular (I-rate) | without possible-Hinglish cells | 16 | 0.09 | 0.27 | 0.86 | 1.25 | 2.28 | too small to model |
| Food and Agriculture | first-person plural (we-rate) | all cells | 16 | 0.42 | 0.98 | 1.17 | 1.73 | 2.07 | too small to model |
| Food and Agriculture | first-person plural (we-rate) | without possible-Hinglish cells | 16 | 0.42 | 0.98 | 1.17 | 1.73 | 2.07 | too small to model |
| HealthTech | first-person singular (I-rate) | all cells | 8 | 0.23 | 0.46 | 1.09 | 1.31 | 1.62 | too small to model |
| HealthTech | first-person singular (I-rate) | without possible-Hinglish cells | 8 | 0.23 | 0.46 | 1.09 | 1.31 | 1.62 | too small to model |
| HealthTech | first-person plural (we-rate) | all cells | 8 | 0.40 | 0.83 | 1.05 | 1.27 | 2.04 | too small to model |
| HealthTech | first-person plural (we-rate) | without possible-Hinglish cells | 8 | 0.40 | 0.83 | 1.05 | 1.27 | 2.04 | too small to model |
| Healthcare | first-person singular (I-rate) | all cells | 23 | 0.08 | 0.52 | 0.68 | 0.86 | 1.80 |  |
| Healthcare | first-person singular (I-rate) | without possible-Hinglish cells | 23 | 0.08 | 0.52 | 0.68 | 0.86 | 1.80 |  |
| Healthcare | first-person plural (we-rate) | all cells | 23 | 0.30 | 0.64 | 0.85 | 1.22 | 2.39 |  |
| Healthcare | first-person plural (we-rate) | without possible-Hinglish cells | 23 | 0.30 | 0.64 | 0.85 | 1.22 | 2.39 |  |
| High Tech | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| High Tech | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| High Tech | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| High Tech | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Industrial Goods and Manufacturing | first-person singular (I-rate) | all cells | 8 | 0.19 | 0.31 | 0.48 | 1.64 | 4.12 | too small to model |
| Industrial Goods and Manufacturing | first-person singular (I-rate) | without possible-Hinglish cells | 8 | 0.19 | 0.31 | 0.48 | 1.62 | 4.12 | too small to model |
| Industrial Goods and Manufacturing | first-person plural (we-rate) | all cells | 8 | 1.08 | 1.18 | 1.43 | 1.53 | 1.86 | too small to model |
| Industrial Goods and Manufacturing | first-person plural (we-rate) | without possible-Hinglish cells | 8 | 1.08 | 1.18 | 1.43 | 1.55 | 1.86 | too small to model |
| Investment Industry | first-person singular (I-rate) | all cells | 7 | 0.10 | 0.25 | 0.34 | 0.39 | 0.53 | too small to model |
| Investment Industry | first-person singular (I-rate) | without possible-Hinglish cells | 7 | 0.10 | 0.25 | 0.34 | 0.39 | 0.53 | too small to model |
| Investment Industry | first-person plural (we-rate) | all cells | 7 | 0.55 | 1.06 | 1.27 | 1.72 | 2.14 | too small to model |
| Investment Industry | first-person plural (we-rate) | without possible-Hinglish cells | 7 | 0.55 | 1.06 | 1.27 | 1.72 | 2.14 | too small to model |
| Media & Entertainment | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Media & Entertainment | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Media & Entertainment | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Media & Entertainment | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Mobile | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Mobile | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Mobile | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Mobile | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Real Estate and Construction | first-person singular (I-rate) | all cells | 12 | 0.15 | 0.33 | 0.46 | 1.23 | 2.55 | too small to model |
| Real Estate and Construction | first-person singular (I-rate) | without possible-Hinglish cells | 12 | 0.15 | 0.33 | 0.46 | 1.23 | 2.55 | too small to model |
| Real Estate and Construction | first-person plural (we-rate) | all cells | 12 | 0.39 | 1.01 | 1.50 | 1.82 | 2.62 | too small to model |
| Real Estate and Construction | first-person plural (we-rate) | without possible-Hinglish cells | 12 | 0.39 | 1.01 | 1.50 | 1.82 | 2.62 | too small to model |
| Real Estate and Construction Tech | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Real Estate and Construction Tech | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Real Estate and Construction Tech | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Real Estate and Construction Tech | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Retail | first-person singular (I-rate) | all cells | 14 | 0.08 | 0.29 | 0.63 | 1.16 | 8.39 | too small to model |
| Retail | first-person singular (I-rate) | without possible-Hinglish cells | 14 | 0.08 | 0.29 | 0.63 | 1.16 | 8.39 | too small to model |
| Retail | first-person plural (we-rate) | all cells | 14 | 0.42 | 0.81 | 1.31 | 1.69 | 2.32 | too small to model |
| Retail | first-person plural (we-rate) | without possible-Hinglish cells | 14 | 0.43 | 0.81 | 1.31 | 1.69 | 2.32 | too small to model |
| Telecom | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Telecom | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Telecom | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Telecom | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Transportation and Logistics | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Transportation and Logistics | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Transportation and Logistics | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Transportation and Logistics | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality Tech | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality Tech | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality Tech | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| Travel and Hospitality Tech | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no value | first-person singular (I-rate) | all cells | 13 | 0.15 | 0.36 | 0.62 | 1.60 | 1.78 | too small to model |
| no value | first-person singular (I-rate) | without possible-Hinglish cells | 13 | 0.15 | 0.36 | 0.62 | 1.60 | 1.78 | too small to model |
| no value | first-person plural (we-rate) | all cells | 13 | 0.31 | 0.51 | 0.96 | 1.25 | 2.91 | too small to model |
| no value | first-person plural (we-rate) | without possible-Hinglish cells | 13 | 0.31 | 0.51 | 0.96 | 1.25 | 2.91 | too small to model |

### Firm size band

| group | measure | cell set | leaders | min | q1 | median | q3 | max | modelling |
|---|---|---|---|---|---|---|---|---|---|
| no usable company match | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no usable company match | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 | too small to model |
| no value | first-person singular (I-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| no value | first-person singular (I-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| no value | first-person plural (we-rate) | all cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| no value | first-person plural (we-rate) | without possible-Hinglish cells | <5 | <5 | <5 | <5 | <5 | <5 |  |
| size band 1 (smallest) | first-person singular (I-rate) | all cells | 76 | 0.05 | 0.37 | 0.75 | 1.29 | 11.90 |  |
| size band 1 (smallest) | first-person singular (I-rate) | without possible-Hinglish cells | 76 | 0.05 | 0.37 | 0.75 | 1.29 | 11.90 |  |
| size band 1 (smallest) | first-person plural (we-rate) | all cells | 76 | 0.30 | 0.70 | 1.17 | 1.61 | 5.43 |  |
| size band 1 (smallest) | first-person plural (we-rate) | without possible-Hinglish cells | 76 | 0.30 | 0.70 | 1.17 | 1.61 | 5.43 |  |
| size band 2 | first-person singular (I-rate) | all cells | 62 | 0.03 | 0.34 | 0.54 | 1.15 | 2.86 |  |
| size band 2 | first-person singular (I-rate) | without possible-Hinglish cells | 62 | 0.03 | 0.34 | 0.54 | 1.15 | 2.86 |  |
| size band 2 | first-person plural (we-rate) | all cells | 62 | 0.23 | 0.76 | 1.24 | 1.59 | 3.67 |  |
| size band 2 | first-person plural (we-rate) | without possible-Hinglish cells | 62 | 0.23 | 0.76 | 1.24 | 1.59 | 3.67 |  |
| size band 3 | first-person singular (I-rate) | all cells | 77 | 0.04 | 0.51 | 0.74 | 1.18 | 4.49 |  |
| size band 3 | first-person singular (I-rate) | without possible-Hinglish cells | 77 | 0.04 | 0.51 | 0.74 | 1.18 | 4.49 |  |
| size band 3 | first-person plural (we-rate) | all cells | 77 | 0.28 | 0.87 | 1.27 | 1.72 | 2.93 |  |
| size band 3 | first-person plural (we-rate) | without possible-Hinglish cells | 77 | 0.28 | 0.87 | 1.27 | 1.72 | 2.94 |  |
| size band 4 (largest) | first-person singular (I-rate) | all cells | 82 | 0.04 | 0.29 | 0.54 | 0.85 | 6.88 |  |
| size band 4 (largest) | first-person singular (I-rate) | without possible-Hinglish cells | 82 | 0.04 | 0.29 | 0.54 | 0.85 | 6.88 |  |
| size band 4 (largest) | first-person plural (we-rate) | all cells | 82 | 0.30 | 0.69 | 0.98 | 1.68 | 3.02 |  |
| size band 4 (largest) | first-person plural (we-rate) | without possible-Hinglish cells | 82 | 0.30 | 0.69 | 0.98 | 1.68 | 3.02 |  |

## Random-intercept models (exploratory)

"leaders fitted" is the number of leaders in the model. A count under the minimum shows as "<5". A count within the minimum of another printed count (the analysis sample or another model's count) shows as a lower bound, so no small difference between two printed numbers is a hidden count.

| model | measure | cell set | leaders fitted | analysis sample | cells | leader-level share, no factors | leader-level share, with factors | note |
|---|---|---|---|---|---|---|---|---|
| without sector | first-person singular (I-rate) | all cells | 237 | 327 | 18,119 | 0.37 | 0.37 |  |
| without sector | first-person singular (I-rate) | without possible-Hinglish cells | 237 | 327 | 18,101 | 0.37 | 0.37 |  |
| without sector | first-person plural (we-rate) | all cells | 237 | 327 | 18,119 | 0.12 | 0.11 |  |
| without sector | first-person plural (we-rate) | without possible-Hinglish cells | 237 | 327 | 18,101 | 0.12 | 0.11 |  |
| with sector, small sectors pooled | first-person singular (I-rate) | all cells | 228 | 327 | 17,156 | 0.38 | 0.38 |  |
| with sector, small sectors pooled | first-person singular (I-rate) | without possible-Hinglish cells | 228 | 327 | 17,139 | 0.38 | 0.38 |  |
| with sector, small sectors pooled | first-person plural (we-rate) | all cells | 228 | 327 | 17,156 | 0.11 | 0.11 |  |
| with sector, small sectors pooled | first-person plural (we-rate) | without possible-Hinglish cells | 228 | 327 | 17,139 | 0.11 | 0.11 |  |

## Founder-CEO and Professional CEO (exploratory)

Founder-CEO against Professional CEO only, so the test has 1 degree of freedom: leaders whose ceo_type is blank or conflicting are left out of the models. Each row is the Professional CEO group's rate minus the Founder-CEO group's rate, adjusted for the other factors in that model. The interval is a normal-approximation interval on the estimate; its level is one minus the Benjamini-Hochberg FDR level in configs/thresholds.yaml, so no new cut is introduced. Estimates are in pronoun uses per 100 words.

| model | measure | cell set | factor | df | contrast | estimate | interval | p | BH-adjusted p | within the FDR level | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| without sector | first-person singular (I-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.47 | -0.99 to +0.05 | 0.0752 | 0.227 | no |  |
| without sector | first-person singular (I-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.47 | -0.99 to +0.05 | 0.0757 | 0.227 | no |  |
| without sector | first-person plural (we-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.09 | -0.22 to +0.39 | 0.58 | 0.931 | no |  |
| without sector | first-person plural (we-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.08 | -0.22 to +0.39 | 0.587 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.55 | -1.10 to -0.01 | 0.0479 | 0.174 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.55 | -1.10 to -0.00 | 0.0482 | 0.174 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.02 | -0.29 to +0.33 | 0.886 | 0.931 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.02 | -0.29 to +0.33 | 0.895 | 0.931 | no |  |

## Joint tests per factor (exploratory)

| model | measure | cell set | factor | df | contrast | estimate | interval | p | BH-adjusted p | within the FDR level | note |
|---|---|---|---|---|---|---|---|---|---|---|---|
| without sector | first-person singular (I-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.47 | -0.99 to +0.05 | 0.0752 | 0.227 | no |  |
| without sector | first-person singular (I-rate) | all cells | Title family | 5 | n/a | n/a | n/a | 0.841 | 0.931 | no |  |
| without sector | first-person singular (I-rate) | all cells | Gender (as coded) | 1 | woman minus man | +0.07 | -0.43 to +0.58 | 0.775 | 0.931 | no |  |
| without sector | first-person singular (I-rate) | all cells | Firm size band | 3 | n/a | n/a | n/a | 0.0392 | 0.174 | no |  |
| without sector | first-person singular (I-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.47 | -0.99 to +0.05 | 0.0757 | 0.227 | no |  |
| without sector | first-person singular (I-rate) | without possible-Hinglish cells | Title family | 5 | n/a | n/a | n/a | 0.84 | 0.931 | no |  |
| without sector | first-person singular (I-rate) | without possible-Hinglish cells | Gender (as coded) | 1 | woman minus man | +0.07 | -0.43 to +0.58 | 0.776 | 0.931 | no |  |
| without sector | first-person singular (I-rate) | without possible-Hinglish cells | Firm size band | 3 | n/a | n/a | n/a | 0.0396 | 0.174 | no |  |
| without sector | first-person plural (we-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.09 | -0.22 to +0.39 | 0.58 | 0.931 | no |  |
| without sector | first-person plural (we-rate) | all cells | Title family | 5 | n/a | n/a | n/a | 0.0123 | 0.111 | no |  |
| without sector | first-person plural (we-rate) | all cells | Gender (as coded) | 1 | woman minus man | +0.15 | -0.15 to +0.45 | 0.315 | 0.724 | no |  |
| without sector | first-person plural (we-rate) | all cells | Firm size band | 3 | n/a | n/a | n/a | 0.522 | 0.931 | no |  |
| without sector | first-person plural (we-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.08 | -0.22 to +0.39 | 0.587 | 0.931 | no |  |
| without sector | first-person plural (we-rate) | without possible-Hinglish cells | Title family | 5 | n/a | n/a | n/a | 0.0122 | 0.111 | no |  |
| without sector | first-person plural (we-rate) | without possible-Hinglish cells | Gender (as coded) | 1 | woman minus man | +0.15 | -0.15 to +0.45 | 0.317 | 0.724 | no |  |
| without sector | first-person plural (we-rate) | without possible-Hinglish cells | Firm size band | 3 | n/a | n/a | n/a | 0.524 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.55 | -1.10 to -0.01 | 0.0479 | 0.174 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | all cells | Title family | 5 | n/a | n/a | n/a | 0.851 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | all cells | Gender (as coded) | 1 | woman minus man | +0.07 | -0.45 to +0.59 | 0.799 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | all cells | Sector | 3 | n/a | n/a | n/a | 0.756 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | all cells | Firm size band | 3 | n/a | n/a | n/a | 0.0325 | 0.174 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | -0.55 | -1.10 to -0.00 | 0.0482 | 0.174 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | without possible-Hinglish cells | Title family | 5 | n/a | n/a | n/a | 0.85 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | without possible-Hinglish cells | Gender (as coded) | 1 | woman minus man | +0.07 | -0.45 to +0.59 | 0.8 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | without possible-Hinglish cells | Sector | 3 | n/a | n/a | n/a | 0.754 | 0.931 | no |  |
| with sector, small sectors pooled | first-person singular (I-rate) | without possible-Hinglish cells | Firm size band | 3 | n/a | n/a | n/a | 0.0329 | 0.174 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | all cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.02 | -0.29 to +0.33 | 0.886 | 0.931 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | all cells | Title family | 5 | n/a | n/a | n/a | 0.0116 | 0.111 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | all cells | Gender (as coded) | 1 | woman minus man | +0.15 | -0.15 to +0.45 | 0.321 | 0.724 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | all cells | Sector | 3 | n/a | n/a | n/a | 0.931 | 0.931 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | all cells | Firm size band | 3 | n/a | n/a | n/a | 0.411 | 0.826 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | without possible-Hinglish cells | Founder vs professional CEO | 1 | Professional CEO minus Founder-CEO | +0.02 | -0.29 to +0.33 | 0.895 | 0.931 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | without possible-Hinglish cells | Title family | 5 | n/a | n/a | n/a | 0.0115 | 0.111 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | without possible-Hinglish cells | Gender (as coded) | 1 | woman minus man | +0.15 | -0.15 to +0.45 | 0.322 | 0.724 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | without possible-Hinglish cells | Sector | 3 | n/a | n/a | n/a | 0.93 | 0.931 | no |  |
| with sector, small sectors pooled | first-person plural (we-rate) | without possible-Hinglish cells | Firm size band | 3 | n/a | n/a | n/a | 0.413 | 0.826 | no |  |

