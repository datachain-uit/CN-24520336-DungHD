# APTOS split audit
Status: ready_for_archive
All automated checks passed: True
Source=3662; readable=3662; eligible=3583; excluded(unique)=79.
Eligible unique pixel images=3488 (not independent patients).
S0 clusters=3484.
Candidates=320639 incl exact; residual unverified nonexact=319305; bounded-reviewed=1200/1200; label decisions=0.
Unresolved unique cross-partition pairs S0=290433.

## Interpretation
S0 is the sole split protocol. Review thresholds do not create automatic group edges.
Grade x acquisition balancing does not eliminate metadata shortcuts or acquisition confounding.
Exact duplicates with consistent labels remain as multiple IDs; report image-level and unique-pixel counts.
No reliable patient IDs. This is NOT a patient-level split; no guarantee against unknown duplicate/same-eye relations.
Only a completed 1,200-row human review journal plus advisor sign-off and archive may yield approved_frozen.
QĐ22: only A/exact same-image label conflicts excluded; B remains together even if Grade differs.

## Files / next steps
Review contact_sheet_index.csv and use show_pair(pair_id) for candidates outside the rendering budget.
Fill near_duplicate_review_v1_template.csv, save a separate completed copy, set bounded_review_log_csv, and rerun.
Review grade availability, metadata missing groups and max deviations in split_report.json.
Keep dataset/config/review/library versions fixed for exact split reproducibility.

## Fold counts
```
scenario  fold  partition  n_images  n_clusters  fraction  grade_0  grade_1  grade_2  grade_3  grade_4  max_grade_deviation  max_acquisition_deviation  max_joint_deviation  grade_dev_pp  acquisition_dev_pp
      S0     0      train      2508        2439  0.699972     1262      251      682      121      192             0.000538                   0.001195             0.000957      0.053838            0.119539
      S0     0 validation       358         348  0.099916      180       37       97       17       27             0.002877                   0.002810             0.005031      0.287749            0.280967
      S0     0       test       717         697  0.200112      359       72      196       34       56             0.001954                   0.002779             0.002231      0.195406            0.277850
      S0     1      train      2508        2439  0.699972     1260      251      682      121      194             0.000601                   0.000678             0.000558      0.060115            0.067815
      S0     1 validation       358         348  0.099916      180       36       98       17       27             0.001625                   0.002507             0.002791      0.162468            0.250718
      S0     1       test       717         697  0.200112      361       73      195       34       54             0.001438                   0.002489             0.002231      0.143752            0.248851
      S0     2      train      2507        2438  0.699693     1259      253      684      119      192             0.000718                   0.000763             0.000717      0.071772            0.076314
      S0     2 validation       359         349  0.100195      181       35       98       18       27             0.002981                   0.004986             0.002501      0.298143            0.498563
      S0     2       test       717         697  0.200112      361       72      193       35       56             0.002941                   0.002449             0.002231      0.294121            0.244880
      S0     3      train      2509        2440  0.700251     1261      252      682      120      194             0.000570                   0.001185             0.001157      0.057032            0.118457
      S0     3 validation       358         348  0.099916      181       36       97       17       27             0.002935                   0.003698             0.004191      0.293518            0.369841
      S0     3       test       716         696  0.199833      359       72      196       35       54             0.001625                   0.002669             0.002236      0.162468            0.266934
      S0     4      train      2508        2438  0.699972     1260      254      681      120      193             0.000801                   0.000956             0.000598      0.080145            0.095647
      S0     4 validation       359         349  0.100195      180       35       99       18       27             0.003648                   0.002523             0.002506      0.364768            0.252275
      S0     4       test       716         697  0.199833      361       71      195       34       55             0.001539                   0.003079             0.001398      0.153853            0.307941
```

## Exclusions (reason counts overlap)
{"A_identity_conflict:exclude_cluster": 19, "exact_conflict:exclude_cluster": 63}

## Method references
https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.StratifiedGroupKFold.html
https://scikit-image.org/docs/stable/api/skimage.metrics.html#skimage.metrics.structural_similarity