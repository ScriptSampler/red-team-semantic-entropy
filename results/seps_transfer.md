> Campaign: `attacks/wk9_defb`. The clean-set probe AUROC below is campaign-independent (Week-4 pool, n=2000) and is the quotable result. The TRANSFER figures depend on this campaign's outcomes and inherit its n; quote them only with that n stated, and never from a superseded tag.

# SE -> SEP transfer experiment

clean set: 2000 questions, train high-entropy rate 0.50, threshold 1.643
extracting TBG features for clean set...
SEP probe AUROC (predicting binarized SE on held-out): 0.766

## Transfer from SE attacks to the SEP score
hide: 72 attacks; SEP score moved in intended direction for 47% (mean delta -0.063)
false_alarm: 69 attacks; SEP score moved in intended direction for 67% (mean delta +0.074)

Interpretation: a high transfer rate means the input paraphrase tuned
against sampling-SE also fools the hidden-state probe -> the weakness is
in the representation. Differentiate CORVUS (model-side, suppression-only).
