"""
data.py
-------
Loads medical_insurance.csv once (cached), re-creates the derived banding
columns from the project plan PDF (Age Band, BMI Category, Risk Band,
Cost Band, Out-of-Pocket Estimate) and exposes the chronic-condition /
procedure-count column lists used across the report pages.

All raw column names below were verified directly against the real
medical_insurance.csv (100,000 rows x 54 columns) — nothing here is
guessed. If you ever swap in a different export of the dataset and a
header changed, fix it in RAW_COLUMNS below; nothing else needs to change.
"""

import os
import pandas as pd
import streamlit as st

CSV_PATH = os.path.join(os.path.dirname(__file__), "medical_insurance.csv")

# logical name -> real CSV header (identity for this dataset; kept as a
# dict so a future header rename only needs an edit here).
RAW_COLUMNS = {
    "person_id": "person_id",
    "age": "age",
    "sex": "sex",
    "region": "region",
    "urban_rural": "urban_rural",
    "income": "income",
    "education": "education",
    "marital_status": "marital_status",
    "employment_status": "employment_status",
    "household_size": "household_size",
    "dependents": "dependents",
    "bmi": "bmi",
    "smoker": "smoker",
    "alcohol_freq": "alcohol_freq",
    "visits_last_year": "visits_last_year",
    "hospitalizations_last_3yrs": "hospitalizations_last_3yrs",
    "days_hospitalized_last_3yrs": "days_hospitalized_last_3yrs",
    "medication_count": "medication_count",
    "systolic_bp": "systolic_bp",
    "diastolic_bp": "diastolic_bp",
    "ldl": "ldl",
    "hba1c": "hba1c",
    "plan_type": "plan_type",
    "network_tier": "network_tier",
    "deductible": "deductible",
    "copay": "copay",
    "policy_term_years": "policy_term_years",
    "policy_changes_last_2yrs": "policy_changes_last_2yrs",
    "provider_quality": "provider_quality",
    "risk_score": "risk_score",
    "annual_medical_cost": "annual_medical_cost",
    "annual_premium": "annual_premium",
    "monthly_premium": "monthly_premium",
    "claims_count": "claims_count",
    "avg_claim_amount": "avg_claim_amount",
    "total_claims_paid": "total_claims_paid",
    "chronic_count": "chronic_count",
    "is_high_risk": "is_high_risk",
    "had_major_procedure": "had_major_procedure",
}

# The 10 chronic-condition 0/1 flag columns (confirmed real names) behind
# Page 4's "Medical History" field-parameter pie chart.
CHRONIC_CONDITIONS = [
    "hypertension",
    "diabetes",
    "asthma",
    "copd",
    "cardiovascular_disease",
    "cancer_history",
    "kidney_disease",
    "liver_disease",
    "arthritis",
    "mental_health",
]

# The 5 procedure-count columns (confirmed real names) behind Page 5.
PROCEDURE_COUNTS = [
    "proc_imaging_count",
    "proc_surgery_count",
    "proc_physio_count",
    "proc_consult_count",
    "proc_lab_count",
]

# --- Derived-column definitions, exactly as specified in the project plan ---
AGE_BAND_BINS = [0, 24, 34, 44, 54, 64, 200]
AGE_BAND_LABELS = ["<25", "25-34", "35-44", "45-54", "55-64", "65+"]

BMI_BINS = [0, 18.5, 24.9, 29.9, 34.9, 100]
BMI_LABELS = ["Underweight", "Normal", "Overweight", "Obese", "Severely Obese"]

RISK_BAND_BINS = [-1, 0.3297, 0.5055, 0.7033, 2]
RISK_BAND_LABELS = ["Low", "Medium", "High", "Critical"]

COST_BAND_BINS = [-1, 1175.12, 2082.58, 3707.96, 10_000_000]
COST_BAND_LABELS = ["Low", "Medium", "High", "Very High"]


def _available(df, logical_name):
    return logical_name in df.columns


@st.cache_data(show_spinner="Loading dataset...")
def load_data():
    """Load the CSV, rename to logical names, add derived columns.

    Returns (df, missing) where `missing` is a list of expected logical
    column names not found in the CSV header — surfaced on the About tab
    instead of crashing the app.
    """
    if not os.path.exists(CSV_PATH):
        return None, [f"medical_insurance.csv not found at {CSV_PATH}"]

    raw = pd.read_csv(CSV_PATH, keep_default_na=False, na_values=[""])

    rename_map = {}
    missing = []
    for logical, real in RAW_COLUMNS.items():
        if real in raw.columns:
            rename_map[real] = logical
        else:
            missing.append(logical)

    df = raw.rename(columns=rename_map)

    for col in CHRONIC_CONDITIONS + PROCEDURE_COUNTS:
        if col not in df.columns:
            missing.append(col)

    if _available(df, "age"):
        df["age_band"] = pd.cut(df["age"], bins=AGE_BAND_BINS, labels=AGE_BAND_LABELS)
    if _available(df, "bmi"):
        df["bmi_category"] = pd.cut(df["bmi"], bins=BMI_BINS, labels=BMI_LABELS)
    if _available(df, "risk_score"):
        df["risk_band"] = pd.cut(df["risk_score"], bins=RISK_BAND_BINS, labels=RISK_BAND_LABELS)
    if _available(df, "annual_medical_cost"):
        df["cost_band"] = pd.cut(df["annual_medical_cost"], bins=COST_BAND_BINS, labels=COST_BAND_LABELS)
    if _available(df, "annual_medical_cost") and _available(df, "total_claims_paid"):
        df["out_of_pocket_estimate"] = df["annual_medical_cost"] - df["total_claims_paid"]
    if _available(df, "urban_rural"):
        df["area_type"] = df["urban_rural"]

    return df, missing


def existing_conditions(df):
    if df is None:
        return []
    return [c for c in CHRONIC_CONDITIONS if c in df.columns]


def existing_procedures(df):
    if df is None:
        return []
    return [c for c in PROCEDURE_COUNTS if c in df.columns]
