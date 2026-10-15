import pandas as pd
import plotly.express as px

def follower_chart(df):
    if df.empty:
        return px.line(title="Belum ada data followers mingguan")

    chart_df = df.copy()
    chart_df["followers"] = pd.to_numeric(
        chart_df["followers"], errors="coerce"
    ).fillna(0)
    chart_df["week"] = chart_df["week"].astype(str)

    return px.line(
        chart_df,
        x="week",
        y="followers",
        color="platform" if chart_df["platform"].nunique() > 1 else None,
        markers=True,
        labels={"week": "Minggu", "followers": "Followers"},
    )

def top_posts_chart(df):
    if df.empty:
        return px.bar(title="Belum ada data postingan")

    chart_df = df.copy()
    chart_df["likes"] = pd.to_numeric(
        chart_df["likes"], errors="coerce"
    ).fillna(0)
    chart_df["title"] = chart_df["title"].astype(str)

    chart_df = chart_df.sort_values("likes", ascending=False).head(10)
    chart_df = chart_df.sort_values("likes", ascending=True)

    return px.bar(
        chart_df,
        x="likes",
        y="title",
        color="platform",
        orientation="h",
        labels={"likes": "Likes", "title": "Postingan"},
    )

def demographics_chart(df):
    if df.empty:
        return px.pie(title="Belum ada data demografi")

    chart_df = df.copy()
    chart_df["viewers"] = pd.to_numeric(
        chart_df["viewers"], errors="coerce"
    ).fillna(0)

    chart_df = (
        chart_df.groupby("age_group", as_index=False)["viewers"]
        .sum()
    )

    return px.pie(
        chart_df,
        names="age_group",
        values="viewers",
        hole=0.35,
    )
