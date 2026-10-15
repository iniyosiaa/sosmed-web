import os
import pandas as pd
import streamlit as st
from sheets import get_all_data
from calculations import calculate_kpis, filter_platform_data
from charts import follower_chart, top_posts_chart, demographics_chart

st.set_page_config(
    page_title="Social Media Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
[data-testid="stMetric"] {
    border: 1px solid rgba(128,128,128,.18);
    border-radius: 12px;
    padding: 14px;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=15)
def load_data():
    return get_all_data()

def main():
    st.title("📊 Social Media Dashboard")
    st.caption("Dashboard analitik Instagram, YouTube, dan TikTok")

    try:
        data = load_data()
    except Exception as exc:
        st.error("Gagal mengambil data dari Google Sheets.")
        st.code(str(exc))
        st.info("Pastikan credentials Google, SHEET_NAME, dan nama worksheet sudah benar.")
        st.stop()

    platforms = sorted(data["platforms"]["platform"].dropna().astype(str).unique().tolist())
    options = ["Semua Platform"] + platforms

    with st.sidebar:
        st.header("🔎 Filter")
        selected = st.selectbox("Platform", options)
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        st.caption("Admin mengubah data melalui Telegram Bot.")

    filtered = filter_platform_data(data, selected)
    kpi = calculate_kpis(filtered)

    c1, c2, c3 = st.columns(3)
    c1.metric("👥 Total Followers", f"{kpi['followers']:,.0f}")
    c2.metric("📈 Engagement Rate", f"{kpi['engagement_rate']:.2f}%")
    c3.metric("👀 Total Views", f"{kpi['views']:,.0f}")

    st.divider()

    left, right = st.columns(2)
    with left:
        st.subheader("📈 Pertumbuhan Followers")
        st.plotly_chart(
            follower_chart(filtered["followers_weekly"]),
            use_container_width=True,
        )

    with right:
        st.subheader("📊 Postingan dengan Likes Terbanyak")
        st.plotly_chart(
            top_posts_chart(filtered["posts"]),
            use_container_width=True,
        )

    st.subheader("🥧 Demografi Penonton")
    st.plotly_chart(
        demographics_chart(filtered["demographics"]),
        use_container_width=True,
    )

    with st.expander("🗃️ Data Mentah"):
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

if __name__ == "__main__":
    main()
