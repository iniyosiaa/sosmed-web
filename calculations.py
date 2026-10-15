import pandas as pd

def filter_platform_data(data, selected):
    if selected == "Semua Platform":
        return data

    result = {}
    for name, df in data.items():
        if "platform" in df.columns:
            result[name] = df[
                df["platform"].astype(str).str.strip().str.lower()
                == selected.strip().lower()
            ].copy()
        else:
            result[name] = df.copy()
    return result

def _num(df, column):
    if df.empty or column not in df.columns:
        return 0.0
    return pd.to_numeric(df[column], errors="coerce").fillna(0).sum()

def calculate_kpis(data):
    platforms = data["platforms"]

    followers = _num(platforms, "followers")
    views = _num(platforms, "total_views")

    likes = _num(platforms, "likes")
    comments = _num(platforms, "comments")
    shares = _num(platforms, "shares")
    total_engagement = likes + comments + shares

    # ER yang digunakan project:
    # total engagement / total views * 100.
    # Followers tetap menjadi KPI utama dan basis data platform.
    engagement_rate = (
        (total_engagement / views) * 100
        if views > 0 else 0
    )

    return {
        "followers": followers,
        "views": views,
        "likes": likes,
        "comments": comments,
        "shares": shares,
        "engagement_rate": engagement_rate,
    }
