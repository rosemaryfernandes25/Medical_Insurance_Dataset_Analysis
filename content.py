"""
content.py
----------
All text/data content for the site lives here as plain Python data.
app.py never hard-codes a page's content — Tab 1 loops over
DATASET_COLUMN_GROUPS / CLEANING_STEPS / MEASURE_GROUPS, and Tab 2 loops
over REPORT_PAGES, rendering each page's KPI cards and charts in order.
To add, remove, or reorder anything, edit the data below — app.py doesn't
change.

------------------------------------------------------------------------
EDIT HERE for the title block on Tab 1:
    SITE_TITLE, SITE_SUBTITLE, MADE_BY   (just below)
------------------------------------------------------------------------

Each REPORT_PAGES entry carries:
  "filters": logical column names -> multiselect slicers at the top of
             that page's section (see charts.apply_filters).
  "kpis":    KPI card specs -> rendered as st.metric cards
             (see charts.render_kpis for the supported spec keys).
  "charts":  chart spec dicts -> rendered as real Plotly charts driven by
             medical_insurance.csv. Every chart spec may include a "note"
             key: a short, one-or-two sentence interpretation shown right
             under that chart (see charts.render_chart for chart types).
"""

from data import CHRONIC_CONDITIONS, PROCEDURE_COUNTS

# ----------------------------------------------------------------------
# Title block — Tab 1
# ----------------------------------------------------------------------
SITE_TITLE = "Risk & Cost Insights: Medical Insurance Analytics"
SITE_SUBTITLE = "A Power BI Analysis, Explained"
MADE_BY = "Made by Rosemary Fernandes and Angela Rodrigues"  # <-- EDIT THIS LINE with your names

DATASET_SOURCE = "Kaggle — mohankrishnathalla/medical-insurance-cost-prediction"
DATASET_SIZE = "100,000 rows × 54 columns"

# ----------------------------------------------------------------------
# Dataset column groups (Tab 1 — "About the data"), verified against the
# real CSV header.
# ----------------------------------------------------------------------
DATASET_COLUMN_GROUPS = [
    ("ID", ["person_id"]),
    ("Demographics", ["age", "sex", "region", "urban_rural", "income", "education",
                       "marital_status", "employment_status", "household_size", "dependents"]),
    ("Lifestyle", ["bmi", "smoker", "alcohol_freq"]),
    ("Utilization", ["visits_last_year", "hospitalizations_last_3yrs",
                      "days_hospitalized_last_3yrs", "medication_count"]),
    ("Clinical vitals", ["systolic_bp", "diastolic_bp", "ldl", "hba1c"]),
    ("Policy", ["plan_type", "network_tier", "deductible", "copay",
                "policy_term_years", "policy_changes_last_2yrs", "provider_quality"]),
    ("Risk / target", ["risk_score", "annual_medical_cost", "annual_premium", "monthly_premium"]),
    ("Claims", ["claims_count", "avg_claim_amount", "total_claims_paid"]),
    ("Chronic conditions (0/1 flags)", ["chronic_count"] + CHRONIC_CONDITIONS),
    ("Procedures", PROCEDURE_COUNTS),
    ("Flags", ["is_high_risk", "had_major_procedure"]),
]

DATA_QUALITY_NOTES = [
    "No duplicate person_id values in the file.",
    "alcohol_freq has 30,083 rows with the literal text \"None\" — a real "
    "category meaning 'no alcohol use', not a missing value. (pandas' "
    "default CSV reader mistakes this text for null; Power Query reads it "
    "correctly as text — that's a pandas quirk, not a data issue, and "
    "this site's own loader reads it with na_values=[\"\"] so \"None\" stays text.)",
    "Everything else is fully populated — no true nulls found.",
]

# ----------------------------------------------------------------------
# Data pipeline & model summary (Tab 1 — Sections 1-3 of the project plan)
# ----------------------------------------------------------------------
CLEANING_STEPS = [
    {
        "title": "Load & inspect",
        "detail": (
            "Loaded medical_insurance.csv via Get Data → Text/CSV → Transform Data, "
            "so cleaning happens in Power Query before anything hits the model."
        ),
    },
    {
        "title": "The 'None' string in alcohol_freq",
        "detail": (
            "30,083 rows store alcohol_freq as the literal text \"None\", meaning "
            "'no alcohol use' — a real category, not a missing value. Power Query "
            "reads this correctly as text."
        ),
    },
    {
        "title": "Data types, locked explicitly",
        "detail": (
            "Every column was explicitly typed rather than left as 'Any': whole "
            "numbers for IDs/counts/flags, decimals for money/clinical values, "
            "text for categoricals. Text columns were also run through "
            "Trim + Clean as cheap insurance against stray whitespace."
        ),
    },
    {
        "title": "Derived banding columns",
        "detail": (
            "Five custom columns were added for slicers and axis grouping: "
            "Age Band (6 buckets), BMI Category (WHO bands, 5 buckets), Risk Band "
            "(quartile cuts of the existing risk_score at 0.3297 / 0.5055 / 0.7033), "
            "Cost Band (quartile cuts of annual_medical_cost at $1,175.12 / "
            "$2,082.58 / $3,707.96), and Out-of-Pocket Estimate "
            "(annual_medical_cost − total_claims_paid). Nothing about risk or "
            "cost was invented — the source file already ships risk_score, "
            "chronic_count, is_high_risk and the cost/claims fields directly."
        ),
    },
]

STAR_SCHEMA = {
    "fact": "FactInsurance",
    "fact_desc": (
        "One row per policyholder (person_id). Holds every numeric/behavioral "
        "field: demographics, lifestyle, utilization, clinical vitals, policy "
        "terms, risk & cost, claims, chronic-condition flags, and procedure counts."
    ),
    "dims": [
        {
            "name": "Dim_Location",
            "desc": (
                "region + urban_rural, deduplicated to their 15 real combinations "
                "and joined back on a LocationKey."
            ),
        },
        {
            "name": "Dim_Policy",
            "desc": (
                "plan_type + network_tier, deduplicated to 16 combinations and "
                "joined back on a PolicyKey."
            ),
        },
    ],
    "why": (
        "There's no date column in this dataset, so there's no calendar table "
        "to build. Most other categorical combinations (e.g. sex × education × "
        "marital_status × employment_status) turned out to be 283 of 288 "
        "possible combinations — essentially independent — so splitting them "
        "into dimensions would add relationship overhead for no real row "
        "reduction. Two combinations only were genuinely small and reusable, "
        "which is why the model is a light star (one fact + two dimensions) "
        "rather than a fully snowflaked schema."
    ),
}

MEASURE_GROUPS = [
    {
        "group": "Volume",
        "measures": [
            ("Total Policyholders", "COUNTROWS(FactInsurance)"),
            ("Total High-Risk Members", "SUM(is_high_risk)"),
            ("% High-Risk Members", "DIVIDE(High-Risk, Total Policyholders)"),
        ],
    },
    {
        "group": "Cost & Premium",
        "measures": [
            ("Total / Avg Annual Medical Cost", "SUM / AVERAGE(annual_medical_cost)"),
            ("Total Premium Revenue", "SUM(annual_premium)"),
            ("Avg Out-of-Pocket", "AVERAGE(Out-of-Pocket Estimate)"),
            ("Premium-to-Income Ratio", "AVERAGEX over annual_premium / income"),
        ],
    },
    {
        "group": "Claims & Loss",
        "measures": [
            ("Total Claims Paid / Count", "SUM(total_claims_paid) / SUM(claims_count)"),
            ("Loss Ratio", "DIVIDE(Total Claims Paid, Total Premium Revenue)"),
            ("Claims Frequency", "DIVIDE(Total Claims Count, Total Policyholders)"),
            (
                "Avg Claim Amount (Weighted)",
                "DIVIDE(Total Claims Paid, Total Claims Count) — deliberately "
                "not AVERAGE(avg_claim_amount), since that column is already a "
                "per-person average and re-averaging it would understate "
                "high-claim members.",
            ),
        ],
    },
    {
        "group": "Risk & Health",
        "measures": [
            ("Avg Risk Score / Chronic Conditions / BMI", "AVERAGE(...)"),
            ("% Current Smokers", "DIVIDE(CALCULATE(..., smoker=\"Current\"), Total Policyholders)"),
            ("Avg Hospitalizations / Medication Count / Provider Quality", "AVERAGE(...)"),
        ],
    },
    {
        "group": "Efficiency",
        "measures": [
            ("Cost per Claim", "DIVIDE(Total Annual Medical Cost, Total Claims Count)"),
        ],
    },
]

MEASURE_NOTE = (
    "Every ratio measure uses DIVIDE(...) instead of the / operator on purpose — "
    "it returns BLANK() instead of an error when the denominator is 0, which "
    "matters here since about 25% of policyholders have claims_count = 0. All "
    "measures live in a dedicated Measures table rather than being buried "
    "inside FactInsurance, purely to keep the field list tidy."
)

# ----------------------------------------------------------------------
# One entry per report page — Tab 2. Rendered continuously, in this
# order: title, purpose, filters, KPI cards, then every chart with its
# brief note.
# ----------------------------------------------------------------------
REPORT_PAGES = [
    {
        "id": "overview",
        "icon": "🏠",
        "title": "Page 1 — Executive Overview",
        "purpose": (
            "Headline KPIs plus three charts that show, at a "
            "glance, whether cost is being driven by geography, age, or risk."
        ),
        "visuals": [
            "KPI cards — Total Policyholders, Avg Annual Medical Cost, "
            "% High-Risk Members, Total Premium Revenue, Loss Ratio",
            "Clustered bar — Avg Annual Medical Cost by Region",
            "Donut — Avg Annual Medical Cost by Risk Band",
            "Clustered column — Avg Annual Medical Cost by Age Band",
            "Slicers — Age Band, Region, Plan Type, Risk Band",
        ],
        "filters": ["age_band", "region", "plan_type", "risk_band"],
        "kpis": [
            {"label": "Total Policyholders", "type": "count", "format": "int"},
            {"label": "Avg Annual Medical Cost", "type": "mean", "col": "annual_medical_cost", "format": "currency"},
            {"label": "% High-Risk Members", "type": "mean", "col": "is_high_risk", "format": "percent"},
            {"label": "Total Premium Revenue", "type": "sum", "col": "annual_premium", "format": "currency"},
            {"label": "Loss Ratio", "type": "ratio_sum", "numerator": "total_claims_paid",
             "denominator": "annual_premium", "format": "ratio"},
        ],
        "charts": [
            {"type": "bar", "x": "region", "y": "annual_medical_cost", "agg": "mean",
             "title": "Avg Annual Medical Cost by Region",
             "note": "Checks whether cost is a geography story before looking anywhere else."},
            {"type": "donut", "names": "risk_band", "values": "annual_medical_cost", "agg": "mean",
             "title": "Avg Annual Medical Cost by Risk Band",
             "note": "The page's thesis chart — cost climbs cleanly Low → Critical showing that risk_score is accurate."},
            {"type": "bar", "x": "age_band", "y": "annual_medical_cost", "agg": "mean",
             "title": "Avg Annual Medical Cost by Age Band",
             "note": "Catches the other common confounder in insurance data: older members have more medical requirements as compared to younger policy holiders."},
        ],
    },
    {
        "id": "cost_premium",
        "icon": "💰",
        "title": "Page 2 — Cost, Premium & Plan Structure",
        "purpose": (
            "Where the money goes and how it's structured: plan mix, cost by "
            "plan/network tier, premium affordability, and deductible design."
        ),
        "visuals": [
            "KPI cards — Premium-to-Income Ratio, Total & Avg Annual Medical "
            "Cost, Total Policyholders, Avg Out-of-Pocket",
            "Clustered column — Policyholder count by Cost Band × Plan Type",
            "Donut — Policyholder mix by Plan Type, and by Network Tier",
            "Clustered column — Total Annual Medical Cost by Network Tier × Plan Type",
            "Clustered column — Total Premium Revenue by Policy Term (years)",
            "Clustered column — Avg Deductible by Network Tier × Plan Type",
            "Scatter — Annual Premium vs. Income",
            "Slicers — Plan Type, Network Tier, Age Band",
        ],
        "filters": ["plan_type", "network_tier", "age_band"],
        "kpis": [
            {"label": "Premium-to-Income Ratio", "type": "row_ratio_mean", "numerator": "annual_premium",
             "denominator": "income", "format": "percent"},
            {"label": "Total Annual Medical Cost", "type": "sum", "col": "annual_medical_cost", "format": "currency"},
            {"label": "Avg Annual Medical Cost", "type": "mean", "col": "annual_medical_cost", "format": "currency"},
            {"label": "Total Policyholders", "type": "count", "format": "int"},
            {"label": "Avg Out-of-Pocket", "type": "mean", "col": "out_of_pocket_estimate", "format": "currency"},
        ],
        "charts": [
            {"type": "bar", "x": "cost_band", "color": "plan_type", "agg": "count",
             "title": "Policyholder Count by Cost Band × Plan Type",
             "note": "Checks for adverse selection — are cheaper plans quietly attracting the highest-cost members?"},
            {"type": "donut", "names": "plan_type", "title": "Policyholder Mix by Plan Type",
             "note": "Establishes plan mix so every other chart on the page has context."},
            {"type": "donut", "names": "network_tier", "title": "Policyholder Mix by Network Tier",
             "note": "Same context check, for network tier."},
            {"type": "bar", "x": "network_tier", "y": "annual_medical_cost", "color": "plan_type", "agg": "sum",
             "title": "Total Annual Medical Cost by Network Tier × Plan Type",
             "note": "A high-average-cost tier matters more once you see it also holds most of the members."},
            {"type": "bar", "x": "policy_term_years", "y": "annual_premium", "agg": "sum",
             "title": "Total Premium Revenue by Policy Term",
             "note": "Shows which policy-term lengths bring in the most revenue."},
            {"type": "bar", "x": "network_tier", "y": "deductible", "color": "plan_type", "agg": "mean",
             "title": "Avg Deductible by Network Tier × Plan Type",
             "note": "Explains why a plan might look cheap on premium — it may just push more risk onto deductibles."},
            {"type": "scatter", "x": "income", "y": "annual_premium", "title": "Annual Premium vs. Income",
             "note": "The affordability check — do premiums scale sensibly with income, or are lower earners paying a bigger share?"},
        ],
    },
    {
        "id": "claims_loss",
        "icon": "📉",
        "title": "Page 3 — Claims & Loss Ratio",
        "purpose": (
            "The profitability page: is the premium being collected enough to "
            "cover what's being paid out, overall and by segment?"
        ),
        "visuals": [
            "KPI cards — Total Claims Paid, Claims Frequency, Total Premium "
            "Revenue, Loss Ratio",
            "Clustered bar — Loss Ratio by Risk Band",
            "Clustered bar — Loss Ratio by Region",
            "Clustered column — Claims Frequency by Age Band",
            "Pivot table — Loss Ratio by Network Tier × Plan Type",
            "Slicers — Risk Band, Plan Type, Region",
        ],
        "filters": ["risk_band", "plan_type", "region"],
        "kpis": [
            {"label": "Total Claims Paid", "type": "sum", "col": "total_claims_paid", "format": "currency"},
            {"label": "Claims Frequency", "type": "mean", "col": "claims_count", "format": "number"},
            {"label": "Total Premium Revenue", "type": "sum", "col": "annual_premium", "format": "currency"},
            {"label": "Loss Ratio", "type": "ratio_sum", "numerator": "total_claims_paid",
             "denominator": "annual_premium", "format": "ratio"},
        ],
        "charts": [
            {"type": "ratio_bar", "x": "risk_band", "numerator": "total_claims_paid",
             "denominator": "annual_premium", "title": "Loss Ratio by Risk Band",
             "note": "Loss Ratio should rise with risk — if it doesn't, pricing isn't compensating for risk correctly."},
            {"type": "ratio_bar", "x": "region", "numerator": "total_claims_paid",
             "denominator": "annual_premium", "title": "Loss Ratio by Region",
             "note": "The same check geographically — regional cost-of-care gaps can erode margin even when the book looks healthy overall."},
            {"type": "bar", "x": "age_band", "y": "claims_count", "agg": "mean", "y_label": "Avg Claims per Policyholder",
             "title": "Claims Frequency by Age Band",
             "note": "A volume lens, not a dollar one — separates 'claims often' from 'claims are expensive'."},
            {"type": "ratio_table", "index": ["network_tier"], "columns": "plan_type",
             "numerator": "total_claims_paid", "denominator": "annual_premium",
             "title": "Loss Ratio by Network Tier × Plan Type",
             "note": "The drill-down — once the KPI flags an issue, this table shows which plan/tier combo is actually underwater."},
        ],
    },
    {
        "id": "risk_health",
        "icon": "🩺",
        "title": "Page 4 — Risk & Health Overview",
        "purpose": (
            "The analytical core of the report: what's actually driving "
            "risk_score, and how prevalent are the underlying health and "
            "lifestyle factors?"
        ),
        "visuals": [
            "KPI cards — Avg Chronic Conditions, % High-Risk Members, Avg Risk "
            "Score, Avg BMI, % Current Smokers",
            "Key Influencers visual — explains risk_score using alcohol_freq, "
            "bmi, chronic_count, smoker",
            "Clustered column — Avg Risk Score & Policyholder count by Risk Band",
            "Pie — Policyholder count by Smoker status",
            "Pie + field-parameter slicer ('Medical History') — Policyholder "
            "count by any single chronic-condition flag, chosen at view time",
            "Clustered column — Policyholder count by Alcohol Frequency",
            "Slicers — Region, Age Band, Risk Band",
        ],
        "filters": ["region", "age_band", "risk_band"],
        "kpis": [
            {"label": "Avg Chronic Conditions", "type": "mean", "col": "chronic_count", "format": "number"},
            {"label": "% High-Risk Members", "type": "mean", "col": "is_high_risk", "format": "percent"},
            {"label": "Avg Risk Score", "type": "mean", "col": "risk_score", "format": "ratio"},
            {"label": "Avg BMI", "type": "mean", "col": "bmi", "format": "number"},
            {"label": "% Current Smokers", "type": "frac_where", "col": "smoker", "value": "Current", "format": "percent"},
        ],
        "charts": [
            {"type": "influencer_bar", "target": "risk_score",
             "candidates": ["alcohol_freq", "bmi", "chronic_count", "smoker"],
             "title": "What Drives Risk Score? (correlation strength)",
             "note": "A transparent correlation ranking standing in for Power BI's Key Influencers AI visual (no open equivalent exists)."},
            {"type": "bar", "x": "risk_band", "agg": "count", "title": "Policyholder Count by Risk Band",
             "note": "How the book splits across risk tiers."},
            {"type": "bar", "x": "risk_band", "y": "risk_score", "agg": "mean", "title": "Avg Risk Score by Risk Band",
             "note": "Confirms the bands are internally consistent — average score should step up cleanly band to band."},
            {"type": "pie", "names": "smoker", "title": "Policyholder Count by Smoker Status",
             "note": "Quantifies how much of the population the smoking-related risk actually applies to."},
            {"type": "condition_picker_pie", "options": CHRONIC_CONDITIONS,
             "label": "Medical History — choose a condition",
             "title": "Policyholder Count by Chronic Condition",
             "note": "One picker standing in for 10 near-identical pie charts — pick a condition to inspect its prevalence."},
            {"type": "bar", "x": "alcohol_freq", "agg": "count", "title": "Policyholder Count by Alcohol Frequency",
             "note": "Lifestyle-factor prevalence, for context against the influencer chart above."},
        ],
    },
    {
        "id": "clinical_utilization",
        "icon": "🏥",
        "title": "Page 5 — Clinical Vitals, Utilization & Procedures",
        "purpose": (
            "Connects health risk to actual cost by looking at what members "
            "consume: hospital stays, medications, and specific procedure types."
        ),
        "visuals": [
            "KPI cards — Total Claims Count, Avg Medication Count, Avg "
            "Hospitalizations (3yr), Avg Provider Quality",
            "Key Influencers visual — explains annual_medical_cost using Age "
            "Band, hospitalizations, medication count, and all five procedure counts",
            "Clustered column — all five procedure counts by Risk Band",
            "Scatter — Risk Score vs. Avg Annual Medical Cost, colored by Risk Band",
            "Clustered column — Avg Hospitalizations & Avg Medication Count by Age Band",
        ],
        "filters": ["risk_band", "age_band"],
        "kpis": [
            {"label": "Total Claims Count", "type": "sum", "col": "claims_count", "format": "int"},
            {"label": "Avg Medication Count", "type": "mean", "col": "medication_count", "format": "number"},
            {"label": "Avg Hospitalizations (3yr)", "type": "mean", "col": "hospitalizations_last_3yrs", "format": "number"},
            {"label": "Avg Provider Quality", "type": "mean", "col": "provider_quality", "format": "number"},
        ],
        "charts": [
            {"type": "influencer_bar", "target": "annual_medical_cost",
             "candidates": ["hospitalizations_last_3yrs", "medication_count"] + PROCEDURE_COUNTS,
             "title": "What Drives Annual Medical Cost? (correlation strength)",
             "note": "Paired with Page 4's influencer chart — shows whether the same factors driving risk also drive cost, or whether utilization intensity pushes cost up separately."},
            {"type": "multi_bar", "group_col": "risk_band", "value_cols": PROCEDURE_COUNTS, "agg": "sum",
             "title": "Procedure Counts by Risk Band",
             "note": "If Critical-risk members have disproportionately more surgery/imaging, it confirms risk_score tracks real clinical activity, not just demographics."},
            {"type": "binned_trend", "x": "risk_score", "y": "annual_medical_cost", "color": "risk_band",
             "bins": 30, "title": "Risk Score vs. Avg Annual Medical Cost",
             "note": "The page's summary visual — average cost climbs steadily with risk score, from ~$1.5k to ~$5.5k, the strongest evidence the risk-scoring approach is sound."},
            {"type": "multi_bar", "group_col": "age_band",
             "value_cols": ["hospitalizations_last_3yrs", "medication_count"], "agg": "mean",
             "title": "Avg Hospitalizations & Medication Count by Age Band",
             "note": "Ties utilization intensity directly to age rather than to risk score."},
        ],
    },
    {
        "id": "demographics_location",
        "icon": "🗺️",
        "title": "Page 6 — Demographics & Location",
        "purpose": (
            "Who the members are and where they live — the segmentation "
            "context every cost and risk number on the earlier pages sits on top of."
        ),
        "visuals": [
            "Treemap — Policyholder count by Region",
            "Map — Policyholder count by Full Region (geographic)",
            "Pie — Policyholder count by Household Size",
            "Ribbon chart — Policyholder count by Education, ranked across Cost Band",
            "Pivot table — Avg Annual Medical Cost, Loss Ratio, Policyholder "
            "count by Marital Status × Sex × Area Type (urban/rural)",
            "Slicers — Employment Status, Age Band, Education",
        ],
        "filters": ["employment_status", "age_band", "education"],
        "charts": [
            {"type": "treemap", "path": ["region"], "title": "Policyholder Count by Region",
             "note": "A proportional read of the same geography the Power BI Map visual covers (no lat/long in this data, so the map itself isn't reproduced here)."},
            {"type": "pie", "names": "household_size", "title": "Policyholder Count by Household Size",
             "note": "Household-size distribution across the book."},
            {"type": "stacked_bar", "x": "education", "color": "cost_band",
             "title": "Cost Band Mix by Education Level",
             "note": "A 100%-stacked substitute for the Power BI ribbon chart — spot whether more education tracks a healthier (lower) cost-band mix."},
            {"type": "table", "index": ["marital_status", "sex", "area_type"],
             "values": "annual_medical_cost", "agg": "mean",
             "title": "Avg Annual Medical Cost by Marital Status × Sex × Area Type",
             "note": "Left as a table — three dimensions at once is more honest here than forcing it into a chart."},
            {"type": "ratio_table", "index": ["marital_status", "sex", "area_type"],
             "numerator": "total_claims_paid", "denominator": "annual_premium",
             "title": "Loss Ratio by Marital Status × Sex × Area Type",
             "note": "Checks whether patterns seen elsewhere (e.g. cost by region) hold once you control for who lives there."},
        ],
    },
    {
        "id": "member_detail",
        "icon": "🔍",
        "title": "Page 7 — Member Detail (Drillthrough)",
        "purpose": (
            "A row-level case file for a single person_id — every other page "
            "is aggregated; this is the one place a single member shows up as "
            "a single member."
        ),
        "visuals": [
            "Identity cards — person_id, Age, Sex, Smoker status, Risk Band",
            "Gauges — BMI, Risk Score",
            "Financial cards — Annual Medical Cost, Annual Premium, Claims "
            "Count, Copay, Total Claims Paid",
            "Clinical cards — Chronic Count, Hospitalizations (3yr), "
            "Medication Count, Procedure counts (lab, surgery)",
            "Decomposition Tree — explores person_id down through Age Band, "
            "Cost Band, Risk Band, Chronic Count, and Smoker status",
            "Text slicer — jump to any person_id directly",
        ],
        "charts": [
            {
                "type": "person_lookup",
                "id_col": "person_id",
                "identity_cols": ["age", "sex", "smoker", "risk_band"],
                "financial_cols": ["annual_medical_cost", "annual_premium", "claims_count",
                                    "copay", "total_claims_paid"],
                "clinical_cols": ["chronic_count", "hospitalizations_last_3yrs", "medication_count",
                                   "proc_lab_count", "proc_surgery_count"],
                "gauge_cols": [
                    {"col": "bmi", "min": 10, "max": 50},
                    {"col": "risk_score", "min": 0, "max": 1},
                ],
                "condition_cols": CHRONIC_CONDITIONS,
                "note": "Type or scroll to any person_id to pull up their full profile — the closest live equivalent to right-clicking into a Power BI drillthrough.",
            },
        ],
    },
]

# ----------------------------------------------------------------------
# Key Takeaways — Tab 3. One group per report page; each item names the
# exact chart it was read off so it's traceable back to Tab 2. Every
# number below was computed directly from medical_insurance.csv —
# nothing here is invented.
# ----------------------------------------------------------------------
KEY_TAKEAWAYS = [
    {
        "page": "Page 1 — Executive Overview",
        "items": [
            {"chart": "Avg Annual Medical Cost by Region",
             "insight": "Regional average cost only ranges from $2,968 (Central) to $3,044 (South) — "
                        "a spread of under 3%. Cost is not a geography story."},
            {"chart": "Avg Annual Medical Cost by Risk Band",
             "insight": "Cost climbs cleanly and monotonically with risk: $1,989 (Low) → $2,544 (Medium) "
                        "→ $3,176 (High) → $4,422 (Critical), a 2.2x gap top to bottom. This is the "
                        "strongest single relationship on the page — risk_score is doing real work."},
            {"chart": "Avg Annual Medical Cost by Age Band",
             "insight": "Cost rises steadily with age too, from $2,337 (<25) to $3,709 (65+), a 59% "
                        "increase — a real but secondary driver that sits alongside, not instead of, risk."},
            {"chart": "KPI cards (Loss Ratio)",
             "insight": "The headline Loss Ratio KPI sits around 237% — the book pays out well over "
                        "double what it collects in premium. That's a pricing-level problem, not a "
                        "one-segment problem, as the rest of the takeaways below confirm."},
        ],
    },
    {
        "page": "Page 2 — Cost, Premium & Plan Structure",
        "items": [
            {"chart": "Policyholder Count by Cost Band × Plan Type",
             "insight": "Cost-band mix is nearly identical across all four plan types (each split roughly "
                        "44-47% the same way across Low/Medium/High/Very High) — no sign that expensive "
                        "members are clustering into any one plan (no obvious adverse selection)."},
            {"chart": "Avg Deductible by Network Tier × Plan Type",
             "insight": "Avg deductible is essentially flat everywhere ($1,170-$1,260) regardless of "
                        "network tier or plan type — tier/plan naming (Bronze/Gold/Platinum, HMO/PPO, etc.) "
                        "doesn't correspond to meaningfully different deductible design in this data."},
            {"chart": "Annual Premium vs. Income",
             "insight": "Premium and income are essentially uncorrelated (r ≈ -0.006) — premiums are priced "
                        "flat, independent of income. Combined with an average premium-to-income ratio of "
                        "just 2.2%, affordability isn't where the book's problem lives."},
        ],
    },
    {
        "page": "Page 3 — Claims & Loss Ratio",
        "items": [
            {"chart": "Loss Ratio by Risk Band",
             "insight": "Loss ratio scales cleanly with risk band (145% Low → 192% Medium → 242% High → "
                        "324% Critical), which validates the risk score — but note even the Low band is "
                        "well above 100%, so nothing in the book is actually profitable as priced."},
            {"chart": "Loss Ratio by Region",
             "insight": "Regional loss ratio is essentially flat (233%-240% everywhere) — the losses are "
                        "systemic across the whole book, not concentrated in one region."},
            {"chart": "Claims Frequency by Age Band",
             "insight": "Claims frequency rises only modestly with age (1.49/yr under 25 → 1.85/yr at 65+) "
                        "— a much smaller effect than the cost gap by age on Page 1, meaning older members "
                        "cost more mainly because each claim costs more, not because they claim far more often."},
            {"chart": "Loss Ratio by Network Tier × Plan Type (table)",
             "insight": "Bronze is the worst-performing tier across every plan type (~270-274% loss ratio), "
                        "while Platinum is comparatively the best (~181-194%) — network tier is a stronger "
                        "lever on profitability here than plan type is."},
        ],
    },
    {
        "page": "Page 4 — Risk & Health Overview",
        "items": [
            {"chart": "What Drives Risk Score? (correlation strength)",
             "insight": "chronic_count is by far the strongest driver of risk_score (correlation 0.67) — "
                        "current-smoker status is a distant second (0.32), and alcohol frequency is "
                        "essentially uncorrelated (<0.01 for every category). Alcohol frequency is noise "
                        "in this model despite being one of the four candidate factors."},
            {"chart": "Policyholder Count by Smoker Status",
             "insight": "69.7% of members have never smoked, 18.2% are former smokers, and 12.1% are "
                        "current smokers — the smoking-linked share of risk applies to roughly 3 in 10 members."},
            {"chart": "Policyholder Count by Chronic Condition",
             "insight": "Hypertension is the single most common condition on the book (20.3% of members), "
                        "ahead of mental health (13.0%) and arthritis (10.8%) — these three should be the "
                        "priority targets for any risk-reduction or care-management program."},
            {"chart": "Avg Risk Score by Risk Band",
             "insight": "Avg risk score steps up cleanly band to band (0.21 → 0.42 → 0.60 → 0.86) confirming "
                        "the bands are internally consistent, not overlapping buckets."},
        ],
    },
    {
        "page": "Page 5 — Clinical Vitals, Utilization & Procedures",
        "items": [
            {"chart": "What Drives Annual Medical Cost? (correlation strength)",
             "insight": "hospitalizations_last_3yrs is the strongest individual cost driver (correlation "
                        "0.21) — clearly ahead of medication_count (0.11) and every procedure count "
                        "individually (0.04-0.08). Inpatient stays move cost more than procedure volume does."},
            {"chart": "Procedure Counts by Risk Band",
             "insight": "Every procedure type rises with risk band — e.g. imaging procedures go from "
                        "10,894 (Low) to 15,139 (Critical), a 39% increase — confirming Critical-risk "
                        "members are genuinely consuming more care, not just carrying a label."},
            {"chart": "Risk Score vs. Avg Annual Medical Cost",
             "insight": "Average cost climbs smoothly with risk score across the entire range with no "
                        "discontinuities or reversals — the single strongest piece of evidence in the "
                        "whole report that the risk-scoring approach is sound."},
            {"chart": "Avg Hospitalizations & Medication Count by Age Band",
             "insight": "Medication count rises meaningfully with age (1.17 <25 → 1.36 65+, +16%) while "
                        "hospitalization count is nearly flat across every age band (~0.09-0.10) — aging "
                        "drives prescription load much more than it drives inpatient admissions."},
        ],
    },
    {
        "page": "Page 6 — Demographics & Location",
        "items": [
            {"chart": "Total Policyholders by Full Region (Map) / by Region (Treemap)",
             "insight": "South carries the largest share of the book (28,029 members, ~28%) and Central "
                        "the smallest (12,081, ~12%) — more than double. Exposure is concentrated by "
                        "region even though average cost by region (Page 1) is not."},
            {"chart": "Total Policyholders by Education and Cost Band",
             "insight": "Cost-band mix is nearly flat within every education level — each group from "
                        "'No HS' to 'Doctorate' splits roughly 24-26% Low/Medium/High/Very High. There's "
                        "no evidence in this data that higher education tracks a healthier cost profile."},
            {"chart": "Policyholder Count by Household Size",
             "insight": "2-person households are the largest single segment (38.8% of the book), followed "
                        "by 3-person households (27.0%); single-person households are only 19.1% — most "
                        "policies cover small family units, not singles."},
            {"chart": "Avg Annual Medical Cost / Loss Ratio by Marital Status × Sex × Area Type",
             "insight": "Both cost and loss ratio vary relatively little across this three-way cross-tab "
                        "(loss ratio mostly 224%-280%), and urban/suburban/rural loss ratios are almost "
                        "identical overall (236.1%-237.4%) — no single demographic or geographic pocket "
                        "stands out as the driver of the book's loss problem; it's structural, per Page 1/3."},
        ],
    },
]