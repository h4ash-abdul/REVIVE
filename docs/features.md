# Feature Dictionary

| Feature Name | Type | Definition | Source | Point-in-Time Status | Missingness | Leakage Risk |
|--------------|------|------------|--------|----------------------|-------------|--------------|
| `candidate_hour` | int | The hour of the day the candidate action is scheduled for. | Candidate | Available at decision | None | Low |
| `candidate_weekday` | int | The day of the week (0-6). | Candidate | Available at decision | None | Low |
| `candidate_day_of_month` | int | The day of the month (1-31). | Candidate | Available at decision | None | Low |
| `time_until_candidate_hours` | float | Hours between cutoff timestamp and candidate time. | Candidate | Available at decision | None | Low |
| `hist_payment_count` | int | Total payment attempts before cutoff. | Observable History | Strict past | None | High (Requires strict cutoff filter) |
| `hist_success_count` | int | Total successful payment attempts before cutoff. | Observable History | Strict past | None | High |
| `hist_failure_count` | int | Total failed payment attempts before cutoff. | Observable History | Strict past | None | High |
| `hist_success_rate` | float | Ratio of successes to total attempts. | Observable History | Strict past | 0.0 if no history | High |
| `hist_amount_mean` | float | Mean of historical attempt amounts. | Observable History | Strict past | 0.0 if no history | Low |
| `hist_amount_std` | float | Stddev of historical attempt amounts. | Observable History | Strict past | 0.0 if <2 attempts | Low |
| `history_depth_days` | float | Days since first observed attempt. | Observable History | Strict past | 0.0 if no history | Low |
| `time_since_prev_success_hours` | float | Hours since last success. | Observable History | Strict past | Null if no success | High |
| `time_since_prev_failure_hours` | float | Hours since last failure. | Observable History | Strict past | Null if no failure | High |
| `hist_success_rate_hour_bucket` | float | Success rate historically in this candidate's specific hour bucket. | Observable History | Strict past | Null if no attempts in hour | High |
| `hist_success_rate_day_bucket` | float | Success rate historically in this candidate's specific day-of-month bucket. | Observable History | Strict past | Null if no attempts in day | High |
| `amount` | float | Obligation amount to collect. | Mandate | Available at creation | None | Low |
| `mandate_age_days` | float | Days since mandate creation. | Mandate | Available at creation | None | Low |
| `current_attempt_number` | int | Which attempt number this candidate would be (historical count + 1). | Observable History | Strict past | None | High |
| `merchant_hist_payment_count` | int | Total attempts for this merchant across all mandates. | Observable History | Strict past | None | High |
| `merchant_success_count` | int | Successful attempts for this merchant. | Observable History | Strict past | None | High |
| `merchant_success_rate` | float | Success rate for this merchant. | Observable History | Strict past | 0.0 if no history | High |
| `merchant_history_depth_days` | float | Days since first observed attempt for this merchant. | Observable History | Strict past | 0.0 if no history | Low |
| `merchant_success_rate_hour_bucket` | float | Merchant success rate for the candidate's specific hour. | Observable History | Strict past | Null if no attempts in hour | High |
| `failure_category` | str | Standardized failure reason of the previous attempt. | Classifier | Strict past | UNKNOWN if no failure | High |
| `raw_network_return_code` | str | The raw error code from the payment network. | Observable History | Strict past | Null if no failure | High |
| `prediction_mode` | str | Indicates the fallback level of data available (CUSTOMER, MERCHANT, POPULATION, DEFAULT) | Metadata | Strict past | None | Low |

## Leakage Prevention
All historical aggregates strictly enforce `timestamp < cutoff_timestamp`. No latent simulator variables (e.g. true payday, behavioral drift) are accessed or extracted during the feature building process.
