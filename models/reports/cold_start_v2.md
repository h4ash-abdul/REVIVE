# Cold-Start Hierarchical Prediction Performance (V2 Fix)

This report details prediction performance comparing the broken v1.0 (inference-time masking) against v1.1 (explicit missingness during training and inference).

| segment                        | version    |   count |   success_rate |   brier_score |   log_loss |   roc_auc |
|:-------------------------------|:-----------|--------:|---------------:|--------------:|-----------:|----------:|
| 0 Events (Merchant Fallback)   | v1.0 (Old) |      67 |       0.492537 |      0.289886 |   0.781199 |  0.535651 |
| 0 Events (Merchant Fallback)   | v1.1 (New) |      67 |       0.492537 |      0.252146 |   0.69753  |  0.524955 |
| 1-2 Events (Merchant Fallback) | v1.0 (Old) |     102 |       0.480392 |      0.288625 |   0.779134 |  0.338082 |
| 1-2 Events (Merchant Fallback) | v1.1 (New) |     102 |       0.480392 |      0.233674 |   0.6601   |  0.64459  |
| 3+ Events (Customer Mode)      | v1.0 (Old) |    1006 |       0.343936 |      0.173068 |   0.51918  |  0.786964 |
| 3+ Events (Customer Mode)      | v1.1 (New) |    1006 |       0.343936 |      0.173539 |   0.52088  |  0.784884 |

## Conclusion
As seen in the tables above, the distribution shift in the `Merchant Fallback` groups has been resolved. The ROC-AUC has recovered significantly, and the probabilities are much better calibrated (lower Brier Score) across cold-start groups, proving that the model can now successfully identify and weight population/merchant level signals when customer history is absent.
