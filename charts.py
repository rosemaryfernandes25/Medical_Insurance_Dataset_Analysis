"""
charts.py
---------
Two generic renderers, both driven entirely by small "spec" dicts that
live in content.py's REPORT_PAGES:

  render_kpis(df, kpi_specs)   -> a row of st.metric cards
  render_chart(df, spec)       -> one Plotly chart / table, plus its
                                   one-line "note" (brief interpretation)

Adding, removing, or changing a KPI or a chart on any page is editing one
dict in content.py — nothing here changes.

KPI spec keys:
    label, format ("currency"/"percent"/"ratio"/"int"/"number"), and one of:
      type "count"                                    (no col needed)
      type "mean" / "sum"           col
      type "ratio_sum"              numerator, denominator  (sum/sum)
      type "row_ratio_mean"         numerator, denominator  (mean of per-row ratio)
      type "frac_where"             col, value               (fraction of rows matching)

Chart spec "type" values and their keys:
    "bar"          x, y, color(optional), agg("mean"/"sum"/"count"), title, orientation("v"/"h")
    "donut"/"pie"  names, values(optional -> count), agg, title
    "scatter"      x, y, color(optional), title
    "treemap"      path (list), values(optional -> count), agg, title
    "stacked_bar"  x, color, title   (100%-stacked; ribbon-chart substitute)
    "table"        index (list), columns(optional), values, agg, title
    "gauge"        value_col, agg("mean"), min, max, title
    "condition_picker_pie"  options (list of flag cols), label, title
    "ratio_bar"    x, color(optional), numerator, denominator, title
    "ratio_table"  index (list), columns(optional), numerator, denominator, title
    "multi_bar"    group_col, value_cols (list), agg("sum"/"mean"), title
    "influencer_bar"  target, candidates (list; categorical cols are
                   one-hot encoded), top_n, title
                   -- ranks |correlation| with target as a simplified,
                      transparent stand-in for Power BI's Key Influencers
                      AI visual (which has no open equivalent).
    "person_lookup" id_col, identity_cols, financial_cols, clinical_cols,
                     gauge_cols (list of {col, min, max}), condition_cols

Every chart spec may also carry a "note" key — a short (1-2 sentence)
interpretation shown as a caption right under that chart.

If a spec references a column that isn't in the dataframe, the chart (or
KPI) is skipped with a small inline note instead of crashing the page.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


# ----------------------------------------------------------------------
# KPI cards
# ----------------------------------------------------------------------
def _compute_kpi(df, spec):
    t = spec["type"]
    if t == "count":
        return len(df)
    if t == "mean":
        return df[spec["col"]].mean()
    if t == "sum":
        return df[spec["col"]].sum()
    if t == "ratio_sum":
        return df[spec["numerator"]].sum() / df[spec["denominator"]].sum()
    if t == "row_ratio_mean":
        return (df[spec["numerator"]] / df[spec["denominator"]]).mean()
    if t == "frac_where":
        return (df[spec["col"]] == spec["value"]).mean()
    raise KeyError(spec.get("col") or spec.get("numerator") or t)


def _format_kpi(value, fmt):
    if fmt == "currency":
        return f"${value:,.0f}"
    if fmt == "percent":
        return f"{value * 100:.1f}%"
    if fmt == "ratio":
        return f"{value:.2f}"
    if fmt == "int":
        return f"{value:,.0f}"
    return f"{value:,.1f}"


def render_kpis(df, kpi_specs):
    if df is None or not kpi_specs:
        return
    cols = st.columns(len(kpi_specs))
    for c, spec in zip(cols, kpi_specs):
        needed = [v for k, v in spec.items() if k in ("col", "numerator", "denominator") and v]
        if any(n not in df.columns for n in needed):
            c.metric(spec["label"], "—")
            continue
        try:
            value = _compute_kpi(df, spec)
            c.metric(spec["label"], _format_kpi(value, spec.get("format", "number")))
        except Exception:
            c.metric(spec["label"], "—")


# ----------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------
def _missing_note(*cols):
    missing = [c for c in cols if c]
    st.caption(f"⚠️ Chart skipped — column(s) not found: {', '.join(missing)}.")


def _agg_series(df, group_cols, value_col, agg):
    if agg == "count" or value_col is None:
        return df.groupby(group_cols, observed=True).size().reset_index(name="value")
    return df.groupby(group_cols, observed=True)[value_col].agg(agg).reset_index(name="value")


def render_chart(df, spec, key_prefix=""):
    ctype = spec.get("type")
    try:
        if ctype == "bar":
            _render_bar(df, spec)
        elif ctype in ("donut", "pie"):
            _render_pie(df, spec, hole=0.5 if ctype == "donut" else 0.0)
        elif ctype == "scatter":
            _render_scatter(df, spec)
        elif ctype == "binned_trend":
            _render_binned_trend(df, spec)
        elif ctype == "treemap":
            _render_treemap(df, spec)
        elif ctype == "stacked_bar":
            _render_stacked_bar(df, spec)
        elif ctype == "table":
            _render_table(df, spec)
        elif ctype == "gauge":
            _render_gauge(df, spec)
        elif ctype == "condition_picker_pie":
            _render_condition_picker(df, spec, key_prefix)
        elif ctype == "ratio_bar":
            _render_ratio_bar(df, spec)
        elif ctype == "ratio_table":
            _render_ratio_table(df, spec)
        elif ctype == "multi_bar":
            _render_multi_bar(df, spec)
        elif ctype == "influencer_bar":
            _render_influencer(df, spec)
        elif ctype == "person_lookup":
            _render_person_lookup(df, spec, key_prefix)
            return  # person_lookup has its own note-free layout
        else:
            st.caption(f"⚠️ Unknown chart type in content.py: {ctype!r}")
    except KeyError as e:
        _missing_note(str(e).strip("'"))
        return
    if spec.get("note"):
        st.caption(spec["note"])


def _render_bar(df, spec):
    x, y, color = spec.get("x"), spec.get("y"), spec.get("color")
    for col in [x, color]:
        if col and col not in df.columns:
            return _missing_note(col)
    if y and y not in df.columns:
        return _missing_note(y)
    agg = spec.get("agg", "mean" if y else "count")
    group_cols = [c for c in [x, color] if c]
    grouped = _agg_series(df, group_cols, y, agg)
    orientation = spec.get("orientation", "v")
    if orientation == "h":
        fig = px.bar(grouped, x="value", y=x, color=color, orientation="h", title=spec.get("title"))
    else:
        fig = px.bar(grouped, x=x, y="value", color=color, title=spec.get("title"))
    fig.update_layout(yaxis_title=spec.get("y_label", y or "count"), margin=dict(t=40))
    st.plotly_chart(fig, width='stretch')


def _render_pie(df, spec, hole):
    names, values = spec.get("names"), spec.get("values")
    if names not in df.columns:
        return _missing_note(names)
    if values and values not in df.columns:
        return _missing_note(values)
    agg = spec.get("agg", "mean" if values else "count")
    grouped = _agg_series(df, [names], values, agg)
    fig = px.pie(grouped, names=names, values="value", hole=hole, title=spec.get("title"))
    st.plotly_chart(fig, width='stretch')


def _render_scatter(df, spec):
    x, y, color = spec.get("x"), spec.get("y"), spec.get("color")
    for col in [x, y, color]:
        if col and col not in df.columns:
            return _missing_note(col)
    sample = df if len(df) <= 5000 else df.sample(5000, random_state=0)
    fig = px.scatter(sample, x=x, y=y, color=color, title=spec.get("title"), opacity=0.5)
    st.plotly_chart(fig, width='stretch')


def _render_binned_trend(df, spec):
    """Bins a continuous x into N buckets and plots the AVERAGE y per
    bucket (optionally colored by the majority value of `color` in that
    bucket), connected by a trend line. Use this instead of a raw
    "scatter" whenever the title says "Avg ..." — a scatter of every raw
    row hides the average trend under noise; this surfaces it."""
    x, y, color = spec.get("x"), spec.get("y"), spec.get("color")
    for col in [x, y, color]:
        if col and col not in df.columns:
            return _missing_note(col)
    bins = spec.get("bins", 30)
    working = df[[x, y]].copy()
    if color:
        working[color] = df[color]
    working["_bin"] = pd.cut(working[x], bins=bins)

    agg_dict = {"x_mid": (x, "mean"), "y_mean": (y, "mean")}
    grouped = working.groupby("_bin", observed=True).agg(**agg_dict)
    if color:
        mode_series = working.groupby("_bin", observed=True)[color].agg(
            lambda s: s.mode().iat[0] if not s.mode().empty else None
        )
        grouped[color] = mode_series
    grouped = grouped.dropna(subset=["x_mid", "y_mean"]).reset_index(drop=True)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=grouped["x_mid"], y=grouped["y_mean"], mode="lines",
        line=dict(color="rgba(150,150,150,0.5)", width=2), showlegend=False, hoverinfo="skip",
    ))
    if color and color in grouped.columns:
        for band_value in grouped[color].dropna().unique():
            sub = grouped[grouped[color] == band_value]
            fig.add_trace(go.Scatter(
                x=sub["x_mid"], y=sub["y_mean"], mode="markers",
                name=str(band_value), marker=dict(size=9),
            ))
    else:
        fig.add_trace(go.Scatter(x=grouped["x_mid"], y=grouped["y_mean"], mode="markers", showlegend=False))

    fig.update_layout(
        title=spec.get("title"),
        xaxis_title=spec.get("x_label", x),
        yaxis_title=spec.get("y_label", f"Avg {y}"),
        margin=dict(t=40),
        legend_title=color.replace("_", " ").title() if color else None,
    )
    st.plotly_chart(fig, width='stretch')


def _render_treemap(df, spec):
    path, values = spec.get("path", []), spec.get("values")
    for col in path:
        if col not in df.columns:
            return _missing_note(col)
    if values and values not in df.columns:
        return _missing_note(values)
    agg = spec.get("agg", "mean" if values else "count")
    grouped = _agg_series(df, path, values, agg)
    fig = px.treemap(grouped, path=path, values="value", title=spec.get("title"))
    st.plotly_chart(fig, width='stretch')


def _render_stacked_bar(df, spec):
    x, color = spec.get("x"), spec.get("color")
    for col in [x, color]:
        if col not in df.columns:
            return _missing_note(col)
    grouped = df.groupby([x, color], observed=True).size().reset_index(name="value")
    totals = grouped.groupby(x, observed=True)["value"].transform("sum")
    grouped["pct"] = grouped["value"] / totals * 100
    fig = px.bar(grouped, x=x, y="pct", color=color, title=spec.get("title"), labels={"pct": "% of group"})
    fig.update_layout(barmode="stack", margin=dict(t=40))
    st.plotly_chart(fig, width='stretch')


def _render_table(df, spec):
    index, columns, values = spec.get("index", []), spec.get("columns"), spec.get("values")
    for col in index + ([columns] if columns else []) + ([values] if values else []):
        if col and col not in df.columns:
            return _missing_note(col)
    agg = spec.get("agg", "mean")
    pivot = pd.pivot_table(df, index=index, columns=columns, values=values, aggfunc=agg, observed=True)
    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")
    st.dataframe(pivot.style.format(precision=2), width='stretch')


def _render_gauge(df, spec):
    value_col = spec.get("value_col")
    if value_col not in df.columns:
        return _missing_note(value_col)
    agg = spec.get("agg", "mean")
    value = df[value_col].agg(agg)
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=float(value), title={"text": spec.get("title", value_col)},
        gauge={"axis": {"range": [spec.get("min", 0), spec.get("max", df[value_col].max())]}},
    ))
    fig.update_layout(height=250, margin=dict(t=40, b=10))
    st.plotly_chart(fig, width='stretch')


def _render_condition_picker(df, spec, key_prefix=""):
    options = [c for c in spec.get("options", []) if c in df.columns]
    if not options:
        return _missing_note(*spec.get("options", []))
    label = spec.get("label", "Choose a condition")
    choice = st.selectbox(label, options, key=f"{key_prefix}_picker_{'_'.join(options)[:20]}")
    grouped = df[choice].value_counts(dropna=False).reset_index()
    grouped.columns = [choice, "value"]
    grouped[choice] = grouped[choice].map({1: "Has condition", 0: "No condition"}).fillna(grouped[choice])
    fig = px.pie(grouped, names=choice, values="value",
                 title=spec.get("title", f"Policyholder count — {choice.replace('_', ' ').title()}"), hole=0.4)
    st.plotly_chart(fig, width='stretch')


def _render_ratio_bar(df, spec):
    x, color = spec.get("x"), spec.get("color")
    num, den = spec.get("numerator"), spec.get("denominator")
    for col in [x, color, num, den]:
        if col and col not in df.columns:
            return _missing_note(col)
    group_cols = [c for c in [x, color] if c]
    grouped = df.groupby(group_cols, observed=True)[[num, den]].sum().reset_index()
    grouped["value"] = grouped[num] / grouped[den]
    fig = px.bar(grouped, x=x, y="value", color=color, title=spec.get("title"))
    fig.update_layout(yaxis_title="Loss Ratio", margin=dict(t=40))
    st.plotly_chart(fig, width='stretch')


def _render_ratio_table(df, spec):
    index, columns = spec.get("index", []), spec.get("columns")
    num, den = spec.get("numerator"), spec.get("denominator")
    for col in index + ([columns] if columns else []) + [num, den]:
        if col and col not in df.columns:
            return _missing_note(col)
    group_cols = index + ([columns] if columns else [])
    grouped = df.groupby(group_cols, observed=True)[[num, den]].sum().reset_index()
    grouped["Loss Ratio"] = grouped[num] / grouped[den]
    if columns:
        pivot = grouped.pivot_table(index=index, columns=columns, values="Loss Ratio")
    else:
        pivot = grouped.set_index(index)[["Loss Ratio"]]
    if spec.get("title"):
        st.markdown(f"**{spec['title']}**")
    st.dataframe(pivot.style.format(precision=3), width='stretch')


def _render_multi_bar(df, spec):
    group_col, value_cols = spec.get("group_col"), spec.get("value_cols", [])
    value_cols = [c for c in value_cols if c in df.columns]
    if group_col not in df.columns or not value_cols:
        return _missing_note(group_col, *spec.get("value_cols", []))
    melted = df.melt(id_vars=[group_col], value_vars=value_cols, var_name="metric", value_name="value")
    agg = spec.get("agg", "sum")
    grouped = melted.groupby([group_col, "metric"], observed=True)["value"].agg(agg).reset_index()
    fig = px.bar(grouped, x=group_col, y="value", color="metric", barmode="group", title=spec.get("title"))
    st.plotly_chart(fig, width='stretch')


def _render_influencer(df, spec):
    target = spec.get("target")
    candidates = spec.get("candidates", [])
    if target not in df.columns:
        return _missing_note(target)
    working = pd.DataFrame({target: df[target]})
    labels = []
    for c in candidates:
        if c not in df.columns:
            continue
        if pd.api.types.is_numeric_dtype(df[c]):
            working[c] = df[c]
            labels.append(c)
        else:
            dummies = pd.get_dummies(df[c], prefix=c)
            for dc in dummies.columns:
                working[dc] = dummies[dc]
                labels.append(dc)
    if not labels:
        return _missing_note(*candidates)
    corr = working[labels].corrwith(working[target]).abs().sort_values(ascending=False)
    corr = corr.head(spec.get("top_n", 8)).reset_index()
    corr.columns = ["factor", "correlation"]
    corr["factor"] = corr["factor"].str.replace("_", " ").str.title()
    fig = px.bar(corr, x="correlation", y="factor", orientation="h", title=spec.get("title"))
    fig.update_layout(yaxis={"categoryorder": "total ascending"}, margin=dict(t=40))
    st.plotly_chart(fig, width='stretch')


def _render_person_lookup(df, spec, key_prefix=""):
    id_col = spec.get("id_col", "person_id")
    if id_col not in df.columns:
        return _missing_note(id_col)

    ids = df[id_col].tolist()
    selected = st.selectbox("Jump to a specific person_id", ids, key=f"{key_prefix}_person_lookup_id")
    row = df[df[id_col] == selected].iloc[0]

    identity_cols = [c for c in spec.get("identity_cols", []) if c in df.columns]
    financial_cols = [c for c in spec.get("financial_cols", []) if c in df.columns]
    clinical_cols = [c for c in spec.get("clinical_cols", []) if c in df.columns]
    gauge_cols = [g for g in spec.get("gauge_cols", []) if g.get("col") in df.columns]
    condition_cols = [c for c in spec.get("condition_cols", []) if c in df.columns]

    def _metric_row(cols, columns_per_row=5):
        if not cols:
            return
        row_cols = st.columns(min(len(cols), columns_per_row))
        for i, c in enumerate(cols):
            row_cols[i % len(row_cols)].metric(c.replace("_", " ").title(), row[c])

    if identity_cols:
        st.markdown("**Identity**")
        _metric_row(identity_cols)
    if financial_cols:
        st.markdown("**Financial**")
        _metric_row(financial_cols)
    if clinical_cols:
        st.markdown("**Clinical**")
        _metric_row(clinical_cols)

    if gauge_cols:
        gcols = st.columns(len(gauge_cols))
        for gc, g in zip(gcols, gauge_cols):
            with gc:
                fig = go.Figure(go.Indicator(
                    mode="gauge+number", value=float(row[g["col"]]),
                    title={"text": g["col"].replace("_", " ").title()},
                    gauge={"axis": {"range": [g.get("min", 0), g.get("max", 100)]}},
                ))
                fig.update_layout(height=220, margin=dict(t=40, b=10))
                st.plotly_chart(fig, width='stretch')

    if condition_cols:
        st.markdown("**Chronic conditions on record**")
        present = [c.replace("_", " ").title() for c in condition_cols if bool(row.get(c))]
        st.write(", ".join(present) if present else "None on record")


def apply_filters(df, filter_cols, key_prefix=""):
    """One multiselect per column, applied inline (not a sidebar)."""
    if df is None or not filter_cols:
        return df
    active_cols = [c for c in filter_cols if c in df.columns]
    if not active_cols:
        return df
    cols = st.columns(len(active_cols))
    filtered = df
    for c, widget_col in zip(active_cols, cols):
        options = sorted(df[c].dropna().unique().tolist(), key=str)
        chosen = widget_col.multiselect(c.replace("_", " ").title(), options, key=f"{key_prefix}_filter_{c}")
        if chosen:
            filtered = filtered[filtered[c].isin(chosen)]
    return filtered