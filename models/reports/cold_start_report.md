# Cold-Start Hierarchical Prediction Performance

This report details prediction performance across different levels of historical depth and prediction modes.

| segment                        |   count |   success_rate |   brier_score |   log_loss |   roc_auc |
|:-------------------------------|--------:|---------------:|--------------:|-----------:|----------:|
| 0 Events (Merchant Fallback)   |      67 |       0.492537 |      0.289886 |   0.781199 |  0.535651 |
| 1-2 Events (Merchant Fallback) |     102 |       0.480392 |      0.288625 |   0.779134 |  0.338082 |
| 3+ Events (Customer Mode)      |    1006 |       0.343936 |      0.173068 |   0.51918  |  0.786964 |