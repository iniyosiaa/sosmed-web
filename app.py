import html
import pandas as pd
import streamlit as st
import plotly.graph_objects as go

from sheets import get_all_data
from calculations import calculate_kpis
from charts import follower_chart, top_posts_chart, demographics_chart

try:
    from insights import build_alerts, build_insights
except Exception:
    build_alerts = build_insights = None

st.set_page_config(
    page_title="SocialPulse | Social Media Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

NAVY = "#0B1220"
PANEL = "#121D2E"
PANEL_2 = "#172338"
BORDER = "#26364D"
TEXT = "#F1F5F9"
MUTED = "#94A3B8"
BLUE = "#60A5FA"
GREEN = "#4ADE80"

st.markdown(f"""
<style>
:root {{ color-scheme: dark; }}
.stApp {{ background:{NAVY}; color:{TEXT}; }}
[data-testid="stHeader"] {{ background:{NAVY}; }}
[data-testid="stSidebar"] {{ background:#0E1727; border-right:1px solid {BORDER}; }}
.block-container {{ max-width:1500px; padding-top:1.6rem; padding-bottom:3rem; }}
h1,h2,h3 {{ color:{TEXT} !important; letter-spacing:-.035em; }}
p, label, [data-testid="stCaptionContainer"] {{ color:{MUTED}; }}
hr {{ border-color:{BORDER}; }}
.sp-hero {{ background:#111C2C; border:1px solid {BORDER}; border-radius:22px; padding:28px 30px; margin:0 0 22px 0; }}
.sp-eyebrow {{ color:{BLUE}; font-size:11px; font-weight:850; letter-spacing:2.4px; text-transform:uppercase; margin-bottom:9px; }}
.sp-title {{ color:#F8FAFC; font-size:clamp(27px,3vw,39px); line-height:1.12; font-weight:850; letter-spacing:-1.5px; }}
.sp-subtitle {{ color:#A5B4C8; font-size:14px; line-height:1.6; margin-top:9px; max-width:760px; }}
.sp-platforms {{ display:flex; flex-wrap:wrap; gap:9px; margin-top:18px; }}
.sp-platform {{ display:inline-flex; align-items:center; gap:8px; padding:7px 11px; border-radius:11px; border:1px solid #2A3B53; background:#172338; color:#DCE6F4; font-size:12px; font-weight:700; }}
.sp-logo {{ display:inline-flex; width:25px; height:25px; border-radius:8px; align-items:center; justify-content:center; color:white; font-size:12px; font-weight:900; flex-shrink:0; }}
.sp-logo.ig {{ background:#A33DD1; }} .sp-logo.yt {{ background:#E53945; }} .sp-logo.tt {{ background:#263744; border:1px solid #506579; }}
.sp-kicker {{ font-size:11px; color:#8295AF; font-weight:800; letter-spacing:1.7px; text-transform:uppercase; margin:5px 0 10px; }}
div[data-testid="stMetric"] {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:17px; padding:19px 20px; min-height:125px; transition:transform .18s ease,border-color .18s ease,background .18s ease; }}
div[data-testid="stMetric"]:hover {{ transform:translateY(-3px); border-color:#4775A8; background:{PANEL_2}; }}
div[data-testid="stMetricLabel"] {{ color:#A9B8CC; font-size:.9rem; }} div[data-testid="stMetricValue"] {{ color:#F8FAFC; font-weight:800; }}
div[data-testid="stPlotlyChart"] {{ background:{PANEL}; border:1px solid {BORDER}; border-radius:17px; padding:8px 8px 0; transition:border-color .18s ease; }}
div[data-testid="stPlotlyChart"]:hover {{ border-color:#3A5578; }}
.stButton>button {{ background:#17253A; border:1px solid #31445F; color:#E2E8F0; border-radius:11px; min-height:42px; font-weight:700; transition:all .18s ease; }}
.stButton>button:hover {{ border-color:{BLUE}; background:#20344F; color:white; transform:translateY(-1px); }}
div[data-baseweb="select"]>div {{ background:#172338; border-color:#31445F; border-radius:11px; }}
[data-testid="stExpander"] {{ background:#111C2C; border:1px solid {BORDER}; border-radius:14px; }}
[data-testid="stDataFrame"] {{ border:1px solid {BORDER}; border-radius:12px; }}
.sp-note {{ border:1px solid #26364D; background:#111C2C; border-radius:14px; padding:13px 15px; color:#B9C6D8; font-size:13px; }}
.sp-foot {{ text-align:center; color:#64748B; font-size:11px; padding-top:22px; }}
@media(max-width:700px) {{ .block-container{{padding-top:1rem}} .sp-hero{{padding:20px}} }}
</style>
""", unsafe_allow_html=True)

EXPECTED_COLUMNS = {
    "platforms": ["platform", "followers", "total_views", "likes", "comments", "shares"],
    "followers_weekly": ["week", "platform", "followers"],
    "posts": ["post_id", "platform", "title", "likes", "views"],
    "demographics": ["platform", "age_group", "viewers"],
}

@st.cache_data(ttl=20, show_spinner=False)
def load_data():
    raw = get_all_data()
    cleaned = {}
    for key, cols in EXPECTED_COLUMNS.items():
        df = raw.get(key) if isinstance(raw, dict) else None
        if not isinstance(df, pd.DataFrame):
            df = pd.DataFrame(columns=cols)
        else:
            df = df.copy()
            for col in cols:
                if col not in df.columns:
                    df[col] = pd.NA
        cleaned[key] = df
    return cleaned


def norm(value):
    return " ".join(str(value).strip().casefold().split())


def filter_data_safely(data, selected):
    """Filter all platform-specific sheets safely, including inconsistent casing/spaces."""
    if selected == "Semua Platform":
        return {key: df.copy() for key, df in data.items()}
    target = norm(selected)
    filtered = {}
    for key, df in data.items():
        if "platform" not in df.columns:
            filtered[key] = df.copy()
            continue
        mask = df["platform"].fillna("").map(norm).eq(target)
        filtered[key] = df.loc[mask].copy().reset_index(drop=True)
    return filtered


def platform_mark(platform):
    p = norm(platform)
    if "insta" in p or p == "ig":
        return ("IG", "ig", "Instagram")
    if "youtube" in p or p in {"yt", "you tube"}:
        return ("▶", "yt", "YouTube")
    if "tiktok" in p or p in {"tik tok", "tt"}:
        return ("♪", "tt", "TikTok")
    return ("#", "tt", str(platform))


def render_platforms(platforms):
    bits = []
    for platform in platforms:
        symbol, css, label = platform_mark(platform)
        bits.append(f'<span class="sp-platform"><span class="sp-logo {css}">{html.escape(symbol)}</span>{html.escape(label)}</span>')
    st.markdown('<div class="sp-platforms">' + "".join(bits) + '</div>', unsafe_allow_html=True)


def style_figure(fig, height=350):
    if fig is None:
        fig = go.Figure()
    fig.update_layout(
        template="plotly_dark", paper_bgcolor=PANEL, plot_bgcolor=PANEL,
        font=dict(family="Inter, Segoe UI, sans-serif", color="#CBD5E1", size=12),
        title=dict(font=dict(size=15, color="#F8FAFC")),
        margin=dict(l=18, r=18, t=35, b=22), height=height,
        legend=dict(bgcolor="rgba(0,0,0,0)", orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
        hoverlabel=dict(bgcolor="#172338", bordercolor="#334155", font_color="#F8FAFC"),
    )
    fig.update_xaxes(showgrid=True, gridcolor="#263449", zerolinecolor="#263449", linecolor="#263449")
    fig.update_yaxes(showgrid=True, gridcolor="#263449", zerolinecolor="#263449", linecolor="#263449")
    return fig


def render_chart(chart_fn, df, title, height=350):
    try:
        fig = chart_fn(df)
        st.plotly_chart(style_figure(fig, height), use_container_width=True, config={"displaylogo": False, "responsive": True})
    except Exception as exc:
        st.info(f"{title}: data belum cukup atau format kolom belum sesuai.")
        with st.expander("Detail teknis grafik"):
            st.code(str(exc))


def reset_platform_filter():
    st.session_state["platform_filter"] = "Semua Platform"


def main():
    with st.sidebar:
        st.markdown('''<div style="display:flex;align-items:center;gap:11px;padding:8px 0 18px"><div style="width:43px;height:43px;border-radius:13px;background:#1D3552;border:1px solid #345579;display:flex;align-items:center;justify-content:center;font-size:22px">◈</div><div><div style="font-size:18px;font-weight:850;color:#F8FAFC">SocialPulse</div><div style="font-size:10px;letter-spacing:1.8px;color:#7F93AE">CREATOR ANALYTICS</div></div></div>''', unsafe_allow_html=True)
        st.markdown("### Dashboard")
        st.caption("Pantau performa konten dalam satu tempat.")
        st.divider()
        st.markdown("#### 🔎 Filter data")
        # Filter choices are derived from actual Google Sheets values to avoid fake/no-match options.
        try:
            data = load_data()
        except Exception as exc:
            st.error("Gagal mengambil data dari Google Sheets.")
            st.caption("Periksa kredensial, SHEET_NAME, dan nama worksheet.")
            st.code(str(exc))
            st.stop()
        actual_platforms = data["platforms"]["platform"].dropna().astype(str).str.strip()
        actual_platforms = [p for p in actual_platforms.unique().tolist() if p]
        preferred = {"instagram": 0, "youtube": 1, "tiktok": 2}
        actual_platforms.sort(key=lambda p: (preferred.get(norm(p), 99), norm(p)))
        options = ["Semua Platform"] + actual_platforms
        selected = st.selectbox("Pilih platform", options, key="platform_filter", help="Filter KPI dan semua grafik berdasarkan platform.")
        a, b = st.columns(2)
        with a:
            if st.button("↻ Refresh", use_container_width=True):
                st.cache_data.clear()
                st.rerun()
        with b:
            st.button("Reset filter", use_container_width=True, on_click=reset_platform_filter)
        st.divider()
        st.markdown("#### Platform")
        render_platforms(actual_platforms or ["Instagram", "YouTube", "TikTok"])
        st.divider()
        st.caption("Sumber data: Google Sheets")
        st.caption("Admin memperbarui data melalui Telegram Bot.")

    st.markdown('''<div class="sp-hero"><div class="sp-eyebrow">CREATOR INTELLIGENCE · OVERVIEW</div><div class="sp-title">Social Media Analytics</div><div class="sp-subtitle">Satu ruang untuk membaca pertumbuhan audiens, menemukan konten unggulan, dan memahami siapa yang menonton.</div></div>''', unsafe_allow_html=True)
    render_platforms(actual_platforms or ["Instagram", "YouTube", "TikTok"])
    st.markdown('<div style="height:10px"></div>', unsafe_allow_html=True)

    filtered = filter_data_safely(data, selected)
    try:
        kpi = calculate_kpis(filtered)
    except Exception:
        kpi = {"followers": 0, "engagement_rate": 0, "views": 0}

    st.markdown('<div class="sp-kicker">Performance at a glance</div>', unsafe_allow_html=True)
    k1, k2, k3 = st.columns(3, gap="medium")
    k1.metric("👥 Total Followers", f"{float(kpi.get('followers', 0) or 0):,.0f}", help="Jumlah followers pada platform yang dipilih.")
    k2.metric("⚡ Engagement Rate", f"{float(kpi.get('engagement_rate', 0) or 0):.2f}%", help="Total likes + comments + shares dibandingkan total views.")
    k3.metric("▶ Total Views", f"{float(kpi.get('views', 0) or 0):,.0f}", help="Total views pada platform yang dipilih.")

    st.markdown('<div style="height:12px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sp-kicker">Explore your performance</div>', unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.subheader("📈 Pertumbuhan Followers")
        st.caption("Pantau perubahan jumlah followers dari minggu ke minggu.")
        render_chart(follower_chart, filtered["followers_weekly"], "Pertumbuhan followers", 360)
    with right:
        st.subheader("🏆 Konten dengan Likes Terbanyak")
        st.caption("Temukan postingan yang paling banyak menarik interaksi.")
        render_chart(top_posts_chart, filtered["posts"], "Postingan dengan likes terbanyak", 360)

    left2, right2 = st.columns([1.05, 1], gap="large")
    with left2:
        st.subheader("🍩 Demografi Penonton")
        st.caption("Distribusi audiens berdasarkan kelompok usia.")
        render_chart(demographics_chart, filtered["demographics"], "Demografi penonton", 370)
    with right2:
        st.subheader("💡 Insight Otomatis")
        st.caption("Ringkasan yang dihitung dari data yang sedang dipilih.")
        if build_insights:
            try:
                for insight in build_insights(filtered):
                    st.markdown(f'<div class="sp-note" style="margin-bottom:8px">✦ {html.escape(str(insight))}</div>', unsafe_allow_html=True)
            except Exception:
                st.info("Insight belum tersedia karena format data belum lengkap.")
        else:
            st.info("Modul insight belum tersedia di project ini.")
        if build_alerts:
            try:
                alerts = build_alerts(filtered)
                if alerts and not (len(alerts) == 1 and str(alerts[0]).startswith("Tidak ada alert")):
                    with st.expander("🚨 Perlu diperhatikan", expanded=False):
                        for alert in alerts:
                            st.write("•", alert)
            except Exception:
                pass

    with st.expander("🗂️ Lihat data tabel", expanded=False):
        tab1, tab2, tab3, tab4 = st.tabs(["Platform", "Followers mingguan", "Postingan", "Demografi"])
        for tab, key in zip((tab1, tab2, tab3, tab4), EXPECTED_COLUMNS.keys()):
            with tab:
                st.dataframe(filtered[key], use_container_width=True, hide_index=True)

    st.markdown('<div class="sp-foot">SOCIALPULSE · SOCIAL MEDIA ANALYTICS</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
