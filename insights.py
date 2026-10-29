"""Automatic, data-driven insights for the SocialPulse Streamlit dashboard.

Expected input: the dictionary returned by get_all_data() or filter_data_safely(),
with DataFrames named platforms, followers_weekly, posts, and demographics.
"""
from __future__ import annotations

import pandas as pd


def _frame(data, key, columns=()):
    value = data.get(key) if isinstance(data, dict) else None
    if not isinstance(value, pd.DataFrame):
        return pd.DataFrame(columns=list(columns))
    return value.copy()


def _numeric(df, column):
    if column not in df.columns or df.empty:
        return pd.Series(dtype="float64")
    # Accept values stored as numbers or strings with commas.
    return pd.to_numeric(
        df[column].astype(str).str.replace(",", "", regex=False).str.strip(),
        errors="coerce",
    ).fillna(0)


def _sum(df, column):
    return float(_numeric(df, column).sum())


def _platform_name(value):
    text = str(value).strip()
    key = text.casefold().replace(" ", "")
    aliases = {
        "ig": "Instagram", "instagram": "Instagram",
        "yt": "YouTube", "youtube": "YouTube", "you tube": "YouTube",
        "tt": "TikTok", "tiktok": "TikTok", "tik tok": "TikTok",
    }
    return aliases.get(key, text or "Platform tidak diketahui")


def _number(value):
    return f"{value:,.0f}".replace(",", ".")


def _percentage(value):
    return f"{value:.2f}%".replace(".", ",")


def build_insights(data):
    """Return concise Indonesian insights grounded in the currently filtered data."""
    platforms = _frame(data, "platforms", ["platform", "followers", "total_views", "likes", "comments", "shares"])
    weekly = _frame(data, "followers_weekly", ["week", "platform", "followers"])
    posts = _frame(data, "posts", ["title", "platform", "likes", "views"])
    demographics = _frame(data, "demographics", ["age_group", "viewers"])
    insights = []

    if platforms.empty and weekly.empty and posts.empty and demographics.empty:
        return ["Belum ada data untuk dianalisis. Isi data platform, followers mingguan, postingan, atau demografi di Google Sheets."]

    # Summary and engagement rate.
    followers = _sum(platforms, "followers")
    views = _sum(platforms, "total_views")
    engagements = sum(_sum(platforms, col) for col in ("likes", "comments", "shares"))
    if not platforms.empty:
        insights.append(
            f"Ringkasan pilihan saat ini: {_number(followers)} followers dan {_number(views)} total views dari {len(platforms)} baris data platform."
        )
        if views > 0:
            rate = engagements / views * 100
            insights.append(
                f"Engagement rate gabungan adalah {_percentage(rate)} berdasarkan (likes + komentar + shares) ÷ views."
            )
        else:
            insights.append("Engagement rate belum bisa dihitung karena total views masih 0 atau belum diisi.")

        # Strongest platform by followers / views when there is more than one.
        platform_rows = platforms.copy()
        if "platform" in platform_rows.columns:
            platform_rows["platform_label"] = platform_rows["platform"].map(_platform_name)
            platform_rows["followers_num"] = _numeric(platform_rows, "followers")
            platform_rows["views_num"] = _numeric(platform_rows, "total_views")
            if len(platform_rows) > 1:
                by_followers = platform_rows.groupby("platform_label", as_index=False)["followers_num"].sum()
                best = by_followers.sort_values("followers_num", ascending=False).iloc[0]
                insights.append(f"Platform dengan followers terbanyak adalah {best['platform_label']} ({_number(best['followers_num'])} followers).")
                by_views = platform_rows.groupby("platform_label", as_index=False)["views_num"].sum()
                best_views = by_views.sort_values("views_num", ascending=False).iloc[0]
                insights.append(f"Platform dengan total views tertinggi adalah {best_views['platform_label']} ({_number(best_views['views_num'])} views).")

    # Weekly follower change: compare the last two rows per platform in sheet order.
    if not weekly.empty and {"platform", "followers"}.issubset(weekly.columns):
        w = weekly.copy()
        w["followers_num"] = _numeric(w, "followers")
        w["platform_label"] = w["platform"].map(_platform_name)
        changes = []
        for platform, group in w.groupby("platform_label", sort=False):
            if len(group) >= 2:
                previous = float(group.iloc[-2]["followers_num"])
                latest = float(group.iloc[-1]["followers_num"])
                delta = latest - previous
                pct = (delta / previous * 100) if previous > 0 else None
                changes.append((platform, delta, pct))
        if changes:
            platform, delta, pct = max(changes, key=lambda item: item[1])
            if delta > 0:
                pct_text = f" ({_percentage(pct)})" if pct is not None else ""
                insights.append(f"Pertumbuhan mingguan terbesar yang tercatat ada pada {platform}: naik {_number(delta)} followers{pct_text} dibanding titik sebelumnya.")
            elif delta < 0:
                platform, delta, pct = min(changes, key=lambda item: item[1])
                insights.append(f"Perubahan mingguan yang perlu dipantau: {platform} turun {_number(abs(delta))} followers dibanding titik sebelumnya.")
            else:
                insights.append("Data followers mingguan terakhir tidak menunjukkan perubahan pada platform yang tersedia.")
        elif len(w) == 1:
            insights.append("Data followers mingguan baru memiliki satu titik; tambahkan minggu berikutnya untuk membaca pertumbuhan.")

    # Top post.
    if not posts.empty and "likes" in posts.columns:
        p = posts.copy()
        p["likes_num"] = _numeric(p, "likes")
        if p["likes_num"].sum() > 0:
            top = p.loc[p["likes_num"].idxmax()]
            title = str(top.get("title", "Postingan tanpa judul")).strip() or "Postingan tanpa judul"
            if len(title) > 75:
                title = title[:72].rstrip() + "..."
            platform = _platform_name(top.get("platform", "Platform tidak diketahui"))
            insights.append(f"Konten dengan likes terbanyak adalah ‘{title}’ di {platform}, dengan {_number(float(top['likes_num']))} likes.")
        else:
            insights.append("Belum ada likes bernilai lebih dari 0 untuk menentukan konten teratas.")

        if "views" in p.columns:
            p["views_num"] = _numeric(p, "views")
            p["post_er"] = p.apply(lambda row: row["likes_num"] / row["views_num"] * 100 if row["views_num"] > 0 else 0, axis=1)
            eligible = p[p["views_num"] > 0]
            if not eligible.empty:
                best = eligible.loc[eligible["post_er"].idxmax()]
                title = str(best.get("title", "Postingan tanpa judul")).strip() or "Postingan tanpa judul"
                if len(title) > 60:
                    title = title[:57].rstrip() + "..."
                insights.append(f"Berdasarkan likes ÷ views (bukan engagement lengkap), ‘{title}’ memiliki rasio likes/views tertinggi: {_percentage(float(best['post_er']))}.")

    # Audience age group.
    if not demographics.empty and {"age_group", "viewers"}.issubset(demographics.columns):
        d = demographics.copy()
        d["viewers_num"] = _numeric(d, "viewers")
        grouped = d.groupby("age_group", dropna=False)["viewers_num"].sum().sort_values(ascending=False)
        total_audience = float(grouped.sum())
        if total_audience > 0 and not grouped.empty:
            age = str(grouped.index[0]).strip()
            share = float(grouped.iloc[0]) / total_audience * 100
            insights.append(f"Kelompok usia dengan penonton terbanyak adalah {age} ({_number(float(grouped.iloc[0]))} penonton, {_percentage(share)} dari data demografi).")
        else:
            insights.append("Data demografi tersedia, tetapi jumlah penontonnya masih 0 atau belum terisi.")

    return insights or ["Data sudah terbaca, tetapi belum cukup untuk menghasilkan insight. Tambahkan angka pada kolom yang relevan."]


def build_alerts(data):
    """Return data-quality and performance alerts without assuming missing data is zero performance."""
    platforms = _frame(data, "platforms", ["platform", "followers", "total_views", "likes", "comments", "shares"])
    weekly = _frame(data, "followers_weekly", ["week", "platform", "followers"])
    posts = _frame(data, "posts", ["title", "platform", "likes", "views"])
    demographics = _frame(data, "demographics", ["age_group", "viewers"])
    alerts = []

    if platforms.empty:
        alerts.append("Data platform kosong; periksa worksheet platforms di Google Sheets.")
    elif "total_views" in platforms.columns and _sum(platforms, "total_views") <= 0:
        alerts.append("Total views masih 0. Engagement rate belum dapat dihitung dengan rumus berbasis views.")

    if not weekly.empty and "followers" in weekly.columns:
        w = weekly.copy()
        w["followers_num"] = _numeric(w, "followers")
        if (w["followers_num"] < 0).any():
            alerts.append("Ada nilai followers mingguan negatif. Periksa kembali input datanya.")
        if "platform" in w.columns:
            for platform, group in w.groupby(w["platform"].astype(str).str.strip().str.casefold()):
                if len(group) >= 2 and float(group.iloc[-1]["followers_num"]) < float(group.iloc[-2]["followers_num"]):
                    alerts.append(f"Followers mingguan pada {group.iloc[-1]['platform']} lebih rendah dari titik sebelumnya; cek apakah ini penurunan aktual atau salah input.")

    if not posts.empty:
        if "likes" in posts.columns and (_numeric(posts, "likes") < 0).any():
            alerts.append("Ada jumlah likes negatif pada data postingan.")
        if "views" in posts.columns and (_numeric(posts, "views") < 0).any():
            alerts.append("Ada jumlah views negatif pada data postingan.")
        if {"likes", "views"}.issubset(posts.columns):
            likes = _numeric(posts, "likes")
            views = _numeric(posts, "views")
            if ((views == 0) & (likes > 0)).any():
                alerts.append("Ada postingan dengan likes tetapi views 0; periksa kelengkapan data.")

    if not demographics.empty and "viewers" in demographics.columns and (_numeric(demographics, "viewers") < 0).any():
        alerts.append("Ada jumlah penonton demografi negatif. Periksa kembali input datanya.")

    return alerts or ["Tidak ada alert penting yang terdeteksi dari data saat ini."]
