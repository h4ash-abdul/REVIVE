import json
import statistics

seeds = [42, 123, 999]
strats = ["ImmediateRetryStrategy", "FixedScheduleStrategy", "SmartHistoricalHeuristicStrategy"]
metrics = {}

table_md = "| Seed | Rev At Risk | Imm Recov | Fix Recov | Smart Recov | Imm Rate | Fix Rate | Smart Rate | Smart-Imm Diff | Smart Lift | Imm Att | Fix Att | Smart Att | Imm Exh | Fix Exh | Smart Exh | Violations |\n"
table_md += "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|\n"

revs = {s: [] for s in strats}

for seed in seeds:
    with open(f"data/evaluation/benchmark_seed_{seed}/benchmark_summary.json") as f:
        data = json.load(f)["metrics"]
        
    risk = data["ImmediateRetryStrategy"]["BUSINESS"]["total_revenue_at_risk"]
    
    imm_rec = data["ImmediateRetryStrategy"]["BUSINESS"]["total_recovered_revenue"]
    fix_rec = data["FixedScheduleStrategy"]["BUSINESS"]["total_recovered_revenue"]
    smart_rec = data["SmartHistoricalHeuristicStrategy"]["BUSINESS"]["total_recovered_revenue"]
    
    revs["ImmediateRetryStrategy"].append(imm_rec)
    revs["FixedScheduleStrategy"].append(fix_rec)
    revs["SmartHistoricalHeuristicStrategy"].append(smart_rec)
    
    imm_rate = data["ImmediateRetryStrategy"]["BUSINESS"]["recovery_rate"]
    fix_rate = data["FixedScheduleStrategy"]["BUSINESS"]["recovery_rate"]
    smart_rate = data["SmartHistoricalHeuristicStrategy"]["BUSINESS"]["recovery_rate"]
    
    diff = smart_rec - imm_rec
    lift = data["SmartHistoricalHeuristicStrategy"]["BUSINESS"]["lift_vs_Immediate"]
    
    imm_att = data["ImmediateRetryStrategy"]["EFFICIENCY"]["average_attempts_per_mandate"]
    fix_att = data["FixedScheduleStrategy"]["EFFICIENCY"]["average_attempts_per_mandate"]
    smart_att = data["SmartHistoricalHeuristicStrategy"]["EFFICIENCY"]["average_attempts_per_mandate"]
    
    imm_exh = data["ImmediateRetryStrategy"]["EFFICIENCY"]["retry_budget_exhaustion_rate"]
    fix_exh = data["FixedScheduleStrategy"]["EFFICIENCY"]["retry_budget_exhaustion_rate"]
    smart_exh = data["SmartHistoricalHeuristicStrategy"]["EFFICIENCY"]["retry_budget_exhaustion_rate"]
    
    v = sum(data[s]["SAFETY"]["policy_violations"] for s in strats)
    
    table_md += f"| {seed} | ${risk:.2f} | ${imm_rec:.2f} | ${fix_rec:.2f} | ${smart_rec:.2f} | {imm_rate*100:.1f}% | {fix_rate*100:.1f}% | {smart_rate*100:.1f}% | ${diff:.2f} | {lift*100:.2f}% | {imm_att:.2f} | {fix_att:.2f} | {smart_att:.2f} | {imm_exh*100:.1f}% | {fix_exh*100:.1f}% | {smart_exh*100:.1f}% | {v} |\n"

out_md = "# Consolidated Benchmark Summary\n\n"
out_md += "## Per-Seed Results\n\n"
out_md += table_md

out_md += "\n## Aggregate Statistics (Revenue)\n\n"
for s in strats:
    r = revs[s]
    out_md += f"### {s}\n"
    out_md += f"- **Mean**: ${statistics.mean(r):.2f}\n"
    out_md += f"- **Std Dev**: ${statistics.stdev(r):.2f}\n"
    out_md += f"- **Min**: ${min(r):.2f}\n"
    out_md += f"- **Max**: ${max(r):.2f}\n\n"

with open("data/evaluation/three_seed_summary.md", "w") as f:
    f.write(out_md)

print("Success")
