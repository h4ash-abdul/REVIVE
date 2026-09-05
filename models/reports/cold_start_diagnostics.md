# Cold-Start Forensic Diagnostics

## 1. Evaluation Verification & Baselines
|                   |   count |   success_rate |   mean_prob |    brier |   log_loss |   roc_auc |
|:------------------|--------:|---------------:|------------:|---------:|-----------:|----------:|
| Masked (Current)  |     102 |       0.480392 |    0.325812 | 0.288625 |   0.779134 |  0.338082 |
| Unmasked (Full)   |     102 |       0.480392 |    0.463258 | 0.228295 |   0.648021 |  0.663458 |
| Global Baseline   |     102 |       0.480392 |    0.364255 | 0.263103 |   0.720509 |  0.5      |
| Merchant Baseline |     102 |       0.480392 |    0.528132 | 0.257808 |   0.708954 |  0.438005 |

## 2. Root Cause of AUC < 0.5
The AUC < 0.5 is genuine and is caused by a massive **inference-time distribution shift**.
In Phase 5, the model was trained on the entire dataset *without* any masking for cold-start customers. Therefore, the model learned that `hist_payment_count=1` means a new customer, and adjusted weights accordingly.
In Phase 6, the hierarchical predictor masks `hist_payment_count` and other customer features to `NaN` for cold-start examples. The `SimpleImputer(strategy='median')` inside the scikit-learn pipeline replaces these NaNs with the global median (e.g., `hist_payment_count` = 6.0, `hist_success_rate` = 0.15).
As a result, a 1-event customer is being scored as if they are a mature customer with 6 past events and a poor 15% success rate. This systematically punishes promising new customers and randomly rewards poor ones, completely inverting the ranking (AUC < 0.5).

## 3. Alternative Architectures
### OPTION A: One Global Model with Explicit Missingness
- **Training Data:** Mask the customer features (set to NaN) *during feature generation or training* for examples below the history threshold, forcing the model to learn a unified representation where `NaN` directly implies 'fallback to merchant/population'.
- **Features:** Uses the same 32 features, but requires an imputer strategy that preserves the missingness signal (e.g., `IterativeImputer` or `SimpleImputer` with `add_indicator=True`, or using a tree-based model that natively handles NaNs).
- **Leakage Risks:** Low, as long as masking relies only on observable count.
- **Artifact Complexity:** Low (one model artifact).
- **Implementation Cost:** Medium (requires rewriting `TrainingDatasetBuilder` or pipeline to mask before `fit()`).

### OPTION B: Separate Fallback Models
- **Training Data:** Split the training dataset into 3 disjoint sets: Customer (`count >= 3`), Merchant (`count < 3 & merchant_count >= 50`), and Population.
- **Features:** Train three separate models. The Merchant model completely drops customer features from its `X` matrix. The Population model drops both customer and merchant features.
- **Leakage Risks:** Low.
- **Artifact Complexity:** High (three separate model artifacts, three manifests).
- **Implementation Cost:** High (requires routing logic during training, evaluation, and inference).

## 4. Recommendation
**Recommend OPTION A (Global Model with Explicit Missingness Indicator).**
Training a single model where we deliberately mask the features for cold-start rows *during training* and use `add_indicator=True` in the `SimpleImputer` allows the logistic regression to learn a specific coefficient for 'is_customer_history_missing'. This perfectly mimics the inference-time hierarchy without maintaining 3 separate artifacts. It keeps the model registry simple while explicitly solving the distribution shift.
