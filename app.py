"""
app.py
------
Entry point. Two tabs:
  Tab 1 — About & Methodology: project title/credit, dataset details,
          cleaning steps, data model, DAX measures. All from content.py.
  Tab 2 — Report Pages: every page in content.REPORT_PAGES rendered one
          after another in a single continuous scroll — title, purpose,
          filters, KPI cards, then every chart with its brief note.

Nothing here is hard-coded per report page: the whole of Tab 2 is one
loop over content.REPORT_PAGES, so adding/removing/reordering a page (or
a KPI, or a chart) means editing content.py only.

Run locally with:
    pip install -r requirements.txt
    python -m streamlit run app.py
"""

import streamlit as st
import content
import data
import charts


def inject_css():
    st.markdown(
        """
        <style>
        .block-container {padding-top: 2rem; max-width: 1100px;}
        .credit-line {color: var(--text-color, #888); font-size: 0.95rem;
                      margin-top: -0.6rem; margin-bottom: 1.2rem;}
        .visual-chip {display:inline-block; background:rgba(120,120,120,0.12);
                      border-radius:8px; padding:6px 12px; margin:4px 6px 4px 0;
                      font-size:0.88rem;}
        .measure-name {font-weight:600;}
        .measure-formula {color: var(--text-color,#888); font-size:0.85rem;}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_about_tab(df, missing):
    # ---- Title block (edit content.py: SITE_TITLE / SITE_SUBTITLE / MADE_BY) ----
    st.title(content.SITE_TITLE)
    st.subheader(content.SITE_SUBTITLE)
    st.markdown(f'<div class="credit-line">{content.MADE_BY}</div>', unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    c1.metric("Dataset source", content.DATASET_SOURCE)
    c2.metric("Dataset size", content.DATASET_SIZE)

    st.write(
        "This site walks through a Power BI report built on this dataset: "
        "what was cleaned, how the model was shaped, which DAX measures "
        "drive the numbers, and — page by page, in the **Report Pages** "
        "tab — what each part of the report shows, with the charts rebuilt "
        "live from the data so every filter actually updates the numbers."
    )

    if df is None:
        st.error(
            "medical_insurance.csv wasn't found next to app.py, so the "
            "Report Pages tab won't have any charts yet. Drop the CSV in "
            "this folder and reload the page."
        )
    elif missing:
        with st.expander(f"⚠️ {len(missing)} expected column(s) not found in your CSV — click to see which"):
            st.write(sorted(missing))
            st.caption("Actual columns found in your CSV:")
            st.write(sorted(df.columns.tolist()))

    st.divider()

    # ---- About the data ----
    st.header("About the Data")
    for group_name, cols in content.DATASET_COLUMN_GROUPS:
        if df is not None:
            cols_display = [f"`{c}`" if c in df.columns else f"~~`{c}`~~" for c in cols]
        else:
            cols_display = [f"`{c}`" for c in cols]
        st.markdown(f"**{group_name}** — " + ", ".join(cols_display))

    st.subheader("Data quality")
    for note in content.DATA_QUALITY_NOTES:
        st.write(f"- {note}")

    st.divider()

    # ---- Cleaning ----
    st.header("1 · Cleaning (Power Query)")
    for step in content.CLEANING_STEPS:
        with st.expander(step["title"], expanded=False):
            st.write(step["detail"])

    st.divider()

    # ---- Data model ----
    st.header("2 · Data Model — Light Star Schema")
    st.write(content.STAR_SCHEMA["why"])

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown(f"**🔷 Fact table — `{content.STAR_SCHEMA['fact']}`**")
        st.write(content.STAR_SCHEMA["fact_desc"])
    with col2:
        for dim in content.STAR_SCHEMA["dims"]:
            st.markdown(f"**🔹 Dimension — `{dim['name']}`**")
            st.write(dim["desc"])

    st.graphviz_chart(
        """
        digraph {
            rankdir=LR;
            node [shape=box, style="rounded,filled", fillcolor="#eef2ff", fontname="Helvetica"];
            Dim_Location [fillcolor="#dbeafe"];
            Dim_Policy [fillcolor="#dbeafe"];
            FactInsurance [fillcolor="#fde68a"];
            Dim_Location -> FactInsurance [label="LocationKey  1:*"];
            Dim_Policy -> FactInsurance [label="PolicyKey  1:*"];
        }
        """
    )

    st.divider()

    # ---- DAX measures ----
    st.header("3 · DAX Measures")
    st.write(content.MEASURE_NOTE)
    for group in content.MEASURE_GROUPS:
        with st.expander(f"{group['group']} measures", expanded=False):
            for name, formula in group["measures"]:
                st.markdown(f'<span class="measure-name">{name}</span>', unsafe_allow_html=True)
                st.markdown(f'<div class="measure-formula">{formula}</div>', unsafe_allow_html=True)
                st.write("")

def render_key_takeaways_tab():
    st.title("Key Takeaways & Business Insights")
    st.write(
        "The Loss Ratio (~237%) is high across every risk band, region, and plan type — " \
        "this is a portfolio-wide pattern, not a single bad segment. The risk-scoring system checks out: " \
        "risk score, cost, loss ratio, and procedure volume all rise together consistently (Pages 1, 3, 5), " \
        "driven mainly by chronic condition count (correlation 0.67) rather than age, smoking, alcohol, or BMI. " \
        "Geography, education, and plan type barely move cost or loss ratio at all — network tier is the one lever that clearly does "
        "(Bronze vs. Platinum, Page 3), making it the most promising place to focus."
    )
    st.divider()

    for group in content.KEY_TAKEAWAYS:
        st.header(group["page"])
        for item in group["items"]:
            st.markdown(f"**📊 {item['chart']}**")
            st.markdown(f"> {item['insight']}")
            st.write("")
        st.divider()


def render_report_pages_tab(df):
    if df is None:
        st.warning("Charts need medical_insurance.csv in this folder — see the About tab.")
        return

    for i, page in enumerate(content.REPORT_PAGES):
        st.header(f"{page['icon']} {page['title']}")
        st.caption(page["purpose"])

        if page.get("filters"):
            filtered = charts.apply_filters(df, page["filters"], key_prefix=page["id"])
        else:
            filtered = df

        if page.get("kpis"):
            charts.render_kpis(filtered, page["kpis"])

        for spec in page.get("charts", []):
            charts.render_chart(filtered, spec, key_prefix=page["id"])

        if i < len(content.REPORT_PAGES) - 1:
            st.divider()


def main():
    st.set_page_config(page_title=content.SITE_TITLE, page_icon="📊", layout="wide")
    inject_css()

    df, missing = data.load_data()

    tab_about, tab_pages, tab_insights = st.tabs(["📘 About & Methodology", "📊 Report Pages", "🔑 Key Takeaways"])

    with tab_about:
        render_about_tab(df, missing)
    with tab_pages:
        render_report_pages_tab(df)
    with tab_insights:
        render_key_takeaways_tab()


if __name__ == "__main__":
    main()