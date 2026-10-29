import os
import pandas as pd
import streamlit as st
from sheets import get_all_data
from calculations import calculate_kpis, filter_platform_data
from charts import follower_chart, top_posts_chart, demographics_chart

st.set_page_config(
    page_title="SocialPulse | Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Navy solid theme — no gradients. Existing data and chart logic are preserved.
st.markdown("""
<style>
:root {
    --navy: #0B1220;
    --panel: #121D2E;
    --panel-hover: #18263A;
    --border: #26364D;
    --text: #F1F5F9;
    --muted: #94A3B8;
    --blue: #60A5FA;
    --green: #4ADE80;
}
.stApp { background: var(--navy); color: var(--text); }
[data-testid="stHeader"] { background: rgba(11,18,32,0.96); }
[data-testid="stSidebar"] {
    background: #0E1727;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { color: #CBD5E1; }
.block-container { padding-top: 2rem; padding-bottom: 3rem; max-width: 1500px; }
h1, h2, h3 { color: var(--text) !important; letter-spacing: -0.025em; }
p, label, .stCaption { color: var(--muted); }
div[data-testid="stMetric"] {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 19px 20px;
    transition: transform .18s ease, border-color .18s ease, background .18s ease;
    min-height: 125px;
}
div[data-testid="stMetric"]:hover {
    transform: translateY(-3px);
    border-color: #4775A8;
    background: var(--panel-hover);
}
div[data-testid="stMetricLabel"] { color: #A9B8CC; font-size: .9rem; }
div[data-testid="stMetricValue"] { color: #F8FAFC; font-weight: 750; }
div[data-testid="stMetricDelta"] { font-size: .82rem; }
div[data-testid="stPlotlyChart"] {
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 8px 8px 0 8px;
    transition: border-color .18s ease;
}
div[data-testid="stPlotlyChart"]:hover { border-color: #3A5578; }
.stButton > button {
    border: 1px solid #31445F;
    border-radius: 10px;
    background: #17253A;
    color: #E2E8F0;
    transition: all .18s ease;
}
.stButton > button:hover {
    border-color: #60A5FA;
    color: white;
    background: #20344F;
}
div[data-baseweb="select"] > div {
    background: #172338;
    border-color: #31445F;
    border-radius: 10px;
}
hr { border-color: var(--border); }
[data-testid="stExpander"] {
    background: #111C2C;
    border: 1px solid var(--border);
    border-radius: 14px;
}
[data-testid="stDataFrame"] { border: 1px solid var(--border); border-radius: 10px; }
.sp-hero {
    background: #111C2C;
    border: 1px solid #26364D;
    border-radius: 20px;
    padding: 25px 28px;
    margin: 0 0 24px 0;
}
.sp-eyebrow {
    color: #7DB8FF;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 2px;
    text-transform: uppercase;
    margin-bottom: 8px;
}
.sp-title { color: #F8FAFC; font-size: 32px; font-weight: 800; letter-spacing: -1px; line-height: 1.15; }
.sp-subtitle { color: #94A3B8; font-size: 14px; margin-top: 8px; }
.sp-status {
    display: inline-block; background: #132C2A; color: #86EFAC;
    border: 1px solid #22594B; border-radius: 999px;
    padding: 7px 11px; font-size: 11px; font-weight: 700;
}
.sp-section {
    color: #E2E8F0; font-size: 19px; font-weight: 750;
    letter-spacing: -.3px; margin: 8px 0 4px 0;
}
.sp-platforms { display:flex; flex-wrap:wrap; gap:8px; margin-top:16px; }
.sp-platform {
    display:inline-flex; align-items:center; gap:8px;
    padding:8px 12px; border-radius:10px; border:1px solid #2A3B53;
    background:#172338; color:#DCE6F4; font-size:12px; font-weight:650;
}
.sp-logo {
    display:inline-flex; width:25px; height:25px; border-radius:7px;
    align-items:center; justify-content:center; color:white;
    font-size:12px; font-weight:900;
}
.sp-logo.ig { background:#A33DD1; }
.sp-logo.yt { background:#E53945; }
.sp-logo.tt { background:#263744; border:1px solid #506579; }
.sp-footer { color:#64748B; font-size:11px; text-align:center; padding-top:18px; }
@media (max-width: 700px) {
    .block-container { padding-top: 1rem; }
    .sp-hero { padding: 19px; }
    .sp-title { font-size: 25px; }
}
</style>
""", unsafe_allow_html=True)


@st.cache_data(ttl=15)
def load_data():
    return get_all_data()


def render_platform_badges(platforms):
    """Show recognizable compact platform marks for platforms present in the data."""
    known = {
        "instagram": ("IG", "ig", "Instagram"),
        "youtube": ("▶", "yt", "YouTube"),
        "tiktok": ("♪", "tt", "TikTok"),
    }
    badges = []
    for platform in platforms:
        key = str(platform).strip().lower()
        if key in known:
            symbol, css_class, label = known[key]
            badges.append(
                f'<span class="sp-platform"><span class="sp-logo {css_class}">{symbol}</span>{label}</span>'
            )
        else:
            badges.append(
                f'<span class="sp-platform"><span class="sp-logo tt">#</span>{platform}</span>'
            )
    st.markdown('<div class="sp-platforms">' + "".join(badges) + "</div>", unsafe_allow_html=True)


def main():
    with st.sidebar:
        st.markdown("""
        <div style="padding:8px 0 18px 0;">
          <div style="display:flex;align-items:center;gap:10px;">
            <div style="background:#1D3552;border:1px solid #345579;border-radius:12px;width:42px;height:42px;display:flex;align-items:center;justify-content:center;font-size:21px;">📊</div>
            <div>
              <div style="font-size:17px;font-weight:800;color:#F8FAFC;">SocialPulse</div>
              <div style="font-size:10px;letter-spacing:1.5px;color:#7F93AE;">ANALYTICS</div>
            </div>
          </div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### Dashboard")
        st.caption("Pantau performa konten dalam satu tempat.")
        st.divider()
        st.markdown("#### 🔎 Filter data")
        selected = st.selectbox(
            "Pilih platform",
            ["Semua Platform", "Instagram", "YouTube", "TikTok"],
            label_visibility="collapsed",
        )
        if st.button("↻  Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
        st.divider()
        st.markdown("#### Platform")
        st.markdown(
            '<div class="sp-platform"><span class="sp-logo ig">IG</span>Instagram</div>'
            '<div style="height:7px"></div>'
            '<div class="sp-platform"><span class="sp-logo yt">▶</span>YouTube</div>'
            '<div style="height:7px"></div>'
            '<div class="sp-platform"><span class="sp-logo tt">♪</span>TikTok</div>',
            unsafe_allow_html=True,
        )
        st.divider()
        st.caption("Data terhubung ke Google Sheets.")
        st.caption("Admin dapat memperbarui data melalui Telegram Bot.")

    st.markdown("""
    <div class="sp-hero">
      <div class="sp-eyebrow">CREATOR INTELLIGENCE</div>
      <div class="sp-title">Social Media Analytics</div>
      <div class="sp-subtitle">Pantau pertumbuhan audiens, performa konten, dan demografi dalam satu dashboard.</div>
      <div class="sp-platforms">
        <span class="sp-platform"><span class="sp-logo ig">IG</span>Instagram</span>
        <span class="sp-platform"><span class="sp-logo yt">▶</span>YouTube</span>
        <span class="sp-platform"><span class="sp-logo tt">♪</span>TikTok</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    try:
        data = load_data()
    except Exception as exc:
        st.error("Gagal mengambil data dari Google Sheets.")
        st.code(str(exc))
        st.info("Pastikan credentials Google, SHEET_NAME, dan nama worksheet sudah benar.")
        st.stop()

    available_platforms = (
        data["platforms"]["platform"].dropna().astype(str).unique().tolist()
        if "platform" in data["platforms"].columns else []
    )
    # Keep the sidebar options aligned with actual data, while retaining the requested platform filter.
    options = ["Semua Platform"] + [
        p for p in ["Instagram", "YouTube", "TikTok"]
        if any(p.lower() == str(item).strip().lower() for item in available_platforms)
    ]
    options += [
        p for p in sorted(available_platforms, key=str.lower)
        if p.lower() not in {item.lower() for item in options}
    ]
    # Sidebar selectbox may have an old value if the available platform list changed.
    selected = st.session_state.get("Pilih platform", "Semua Platform")
    if selected not in options:
        selected = "Semua Platform"

    filtered = filter_platform_data(data, selected)
    kpi = calculate_kpis(filtered)

    st.markdown('<div class="sp-section">Overview</div>', unsafe_allow_html=True)
    st.caption("Ringkasan performa dari platform yang dipilih.")
    c1, c2, c3 = st.columns(3)
    c1.metric("👥  Total Followers", f"{kpi['followers']:,.0f}")
    c2.metric("📈  Engagement Rate", f"{kpi['engagement_rate']:.2f}%")
    c3.metric("▶  Total Views", f"{kpi['views']:,.0f}")

    st.markdown('<div class="sp-section">Performa Konten</div>', unsafe_allow_html=True)
    left, right = st.columns(2, gap="large")
    with left:
        st.markdown("##### 📈 Pertumbuhan Followers")
        st.plotly_chart(
            follower_chart(filtered["followers_weekly"]),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )
    with right:
        st.markdown("##### 🏆 Postingan dengan Likes Terbanyak")
        st.plotly_chart(
            top_posts_chart(filtered["posts"]),
            use_container_width=True,
            config={"displayModeBar": False, "responsive": True},
        )

    st.markdown('<div class="sp-section">Analisis Audiens</div>', unsafe_allow_html=True)
    st.caption("Distribusi kelompok usia penonton berdasarkan data yang tersedia.")
    st.plotly_chart(
        demographics_chart(filtered["demographics"]),
        use_container_width=True,
        config={"displayModeBar": False, "responsive": True},
    )

    with st.expander("🗃️ Lihat Data Mentah"):
        tab1, tab2, tab3, tab4 = st.tabs(
            ["Platforms", "Followers Weekly", "Posts", "Demographics"]
        )
        with tab1:
            st.dataframe(filtered["platforms"], use_container_width=True, hide_index=True)
        with tab2:
            st.dataframe(filtered["followers_weekly"], use_container_width=True, hide_index=True)
        with tab3:
            st.dataframe(filtered["posts"], use_container_width=True, hide_index=True)
        with tab4:
            st.dataframe(filtered["demographics"], use_container_width=True, hide_index=True)

    st.markdown(
        '<div class="sp-footer">SOCIALPULSE • SOCIAL MEDIA PERFORMANCE DASHBOARD</div>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
