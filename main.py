import streamlit as st
import pandas as pd
import altair as alt  # comes with Streamlit, used for the chart

st.set_page_config(page_title="Employee of the Week", page_icon="🏆", layout="wide")
st.title("🏆 Employee of the Week")

# Sidebar: page menu and file uploader (shared by both pages)
page = st.sidebar.radio("Go to", ["Leaderboard", "Employee Page"])
uploaded_files = st.sidebar.file_uploader(
    "Upload weekly sales files", type=["xlsx"], accept_multiple_files=True
)

# If no files yet, show a message and stop the app here
if not uploaded_files:
    st.info("Upload one or more Excel files in the sidebar to get started.")
    st.stop()

# ---------- Load and combine all files ----------
all_weeks = []
for file in uploaded_files:
    data = pd.read_excel(file)
    if "Week" not in data.columns:
        data["Week"] = file.name.replace(".xlsx", "")
    all_weeks.append(data)

df = pd.concat(all_weeks, ignore_index=True)
df["Week"] = df["Week"].astype(str)
df["Ratio"] = df["Drink Sales"] / df["Hours Worked"]

week_list = sorted(df["Week"].unique())

# ---------- Page 1: Leaderboard ----------
if page == "Leaderboard":
    selected_week = st.selectbox("Choose a week", week_list, index=len(week_list) - 1)

    weekly = df[df["Week"] == selected_week].copy()
    weekly = weekly.sort_values("Ratio", ascending=False).reset_index(drop=True)

    # Medals for the top 3, plain numbers for everyone else
    medals = ["🥇", "🥈", "🥉"]
    weekly["Rank"] = [medals[i] if i < 3 else str(i + 1) for i in range(len(weekly))]

    # Winner banner
    winner = weekly.iloc[0]
    st.subheader(f"🏆 Employee of the Week ({selected_week})")

    col1, col2, col3 = st.columns(3)
    col1.metric("Winner", winner["Employee"])
    col2.metric("Sales per hour", f"{winner['Ratio']:.2f}")
    col3.metric("Drink sales", f"{winner['Drink Sales']}")

    st.divider()

    # Full leaderboard with a bar inside the Ratio column
    st.dataframe(
        weekly[["Rank", "Employee", "Drink Sales", "Hours Worked", "Ratio"]],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Ratio": st.column_config.ProgressColumn(
                "Sales per hour",
                format="%.2f",
                min_value=0,
                max_value=float(weekly["Ratio"].max()),
            ),
        },
    )

# ---------- Page 2: Employee Page ----------
else:
    pick1, pick2 = st.columns(2)
    employee = pick1.selectbox("Choose an employee", sorted(df["Employee"].unique()))
    metric = pick2.radio("Show", ["Drink Sales", "Ratio"], horizontal=True)

    # Get this employee's rows and put the weeks in the right order
    emp_df = df[df["Employee"] == employee].copy()
    emp_df["Order"] = emp_df["Week"].map({w: i for i, w in enumerate(week_list)})
    emp_df = emp_df.sort_values("Order").reset_index(drop=True)

    # Change compared with the previous week (calculated on the full history)
    emp_df["Change"] = emp_df[metric].diff()

    def trend(change):
        if pd.isna(change):
            return "First week"
        if change > 0:
            return "Increase"
        if change < 0:
            return "Decrease"
        return "No change"

    emp_df["Trend"] = emp_df["Change"].apply(trend)

    # Sliding bar: pick the first and last week to show
    if len(week_list) > 1:
        start_week, end_week = st.select_slider(
            "Weeks to show", options=week_list, value=(week_list[0], week_list[-1])
        )
    else:
        start_week = end_week = week_list[0]

    shown = emp_df[
        (emp_df["Order"] >= week_list.index(start_week))
        & (emp_df["Order"] <= week_list.index(end_week))
    ]

    if shown.empty:
        st.warning("This employee has no data in the selected weeks.")
        st.stop()

    # Latest week in the range: value shown green (up) or red (down)
    latest = shown.iloc[-1]
    delta = None if pd.isna(latest["Change"]) else f"{latest['Change']:+.2f}"
    st.metric(f"{employee}, {latest['Week']}: {metric}", f"{latest[metric]:.2f}", delta)

    # Build one short line for each pair of neighbouring weeks
    segments = []
    for i in range(1, len(shown)):
        before = shown.iloc[i - 1]
        after = shown.iloc[i]
        for row in (before, after):
            segments.append(
                {"Segment": i, "Week": row["Week"], metric: row[metric], "Trend": after["Trend"]}
            )
    seg_df = pd.DataFrame(segments)

    # Colours for each type of change
    colours = alt.Color(
        "Trend",
        type="nominal",
        scale=alt.Scale(
            domain=["Increase", "Decrease", "No change", "First week"],
            range=["#2ca02c", "#d62728", "#888888", "#888888"],
        ),
        legend=alt.Legend(title="Change vs previous week"),
    )
    x_axis = alt.X("Week", type="nominal", sort=week_list)
    y_axis = alt.Y(metric, type="quantitative", scale=alt.Scale(zero=False))

    points = (
        alt.Chart(shown)
        .mark_point(filled=True, size=90)
        .encode(x=x_axis, y=y_axis, color=colours)
    )

    if len(seg_df) > 0:
        lines = (
            alt.Chart(seg_df)
            .mark_line(strokeWidth=3)
            .encode(x=x_axis, y=y_axis, color=colours, detail="Segment:N")
        )
        chart = lines + points
    else:
        chart = points

    st.subheader(f"{employee}: {metric} per week")
    st.altair_chart(chart, use_container_width=True)

    st.dataframe(
        shown[["Week", "Drink Sales", "Hours Worked", "Ratio", "Change"]],
        use_container_width=True,
    )