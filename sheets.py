import json
import os
from pathlib import Path

import gspread
import pandas as pd
from dotenv import load_dotenv
from google.oauth2.service_account import Credentials

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WORKSHEETS = {
    "platforms": [
        "platform", "followers", "total_views",
        "likes", "comments", "shares",
    ],
    "followers_weekly": ["week", "platform", "followers"],
    "posts": ["post_id", "platform", "title", "likes", "views"],
    "demographics": ["platform", "age_group", "viewers"],
}


def _get_streamlit_secret(key, default=None):
    """Ambil secret dari Streamlit Cloud jika tersedia."""
    try:
        import streamlit as st
        return st.secrets.get(key, default)
    except Exception:
        # Secrets mungkin tidak tersedia saat dijalankan secara lokal.
        return default


def _get_credentials():
    # 1. Streamlit Cloud: gunakan service account dari Secrets.
    service_account_info = _get_streamlit_secret("gcp_service_account")

    if service_account_info:
        return Credentials.from_service_account_info(
            dict(service_account_info),
            scopes=SCOPES,
        )

    # 2. Cloud lain: GOOGLE_CREDS berisi JSON credentials.
    google_creds = os.getenv("GOOGLE_CREDS")

    if google_creds:
        return Credentials.from_service_account_info(
            json.loads(google_creds),
            scopes=SCOPES,
        )

    # 3. Lokal: gunakan file credentials.json.
    credentials_file = os.getenv(
        "GOOGLE_CREDENTIALS_FILE",
        "credentials.json",
    )
    path = Path(credentials_file)

    if not path.exists():
        raise FileNotFoundError(
            f"Credential file tidak ditemukan: {path.resolve()}. "
            "Pastikan credentials.json tersedia secara lokal "
            "atau konfigurasi gcp_service_account di Streamlit Secrets."
        )

    return Credentials.from_service_account_file(
        str(path),
        scopes=SCOPES,
    )


def get_client():
    return gspread.authorize(_get_credentials())


def get_spreadsheet():
    # Prioritas pertama: variabel lingkungan dari .env atau hosting.
    sheet_name = os.getenv("SHEET_NAME")

    # Jika belum ada, coba ambil dari Streamlit Cloud Secrets.
    if not sheet_name:
        sheet_name = _get_streamlit_secret("SHEET_NAME")

    if not sheet_name or not str(sheet_name).strip():
        raise RuntimeError(
            "SHEET_NAME belum diatur. "
            "Tambahkan SHEET_NAME di file .env untuk lokal "
            "atau di Streamlit Cloud > Settings > Secrets."
        )

    return get_client().open(str(sheet_name).strip())


def get_worksheet(name):
    if name not in WORKSHEETS:
        raise ValueError(f"Nama worksheet tidak dikenal: {name}")

    return get_spreadsheet().worksheet(name)


def worksheet_to_df(name):
    ws = get_worksheet(name)
    records = ws.get_all_records()
    columns = WORKSHEETS[name]

    if not records:
        return pd.DataFrame(columns=columns)

    return pd.DataFrame(records, columns=columns)


def get_all_data():
    return {
        name: worksheet_to_df(name)
        for name in WORKSHEETS
    }


def _normalize_number(value, integer=True):
    if value is None or str(value).strip() == "":
        return 0

    try:
        number = float(str(value).replace(",", "").strip())
        return int(number) if integer else number
    except (ValueError, TypeError):
        raise ValueError(f"Nilai angka tidak valid: {value}")


def update_platform(
    platform,
    followers,
    total_views,
    likes,
    comments,
    shares,
):
    ws = get_worksheet("platforms")
    records = ws.get_all_records()

    row_index = None

    for i, row in enumerate(records, start=2):
        if (
            str(row.get("platform", "")).strip().lower()
            == str(platform).strip().lower()
        ):
            row_index = i
            break

    values = [
        platform,
        _normalize_number(followers),
        _normalize_number(total_views),
        _normalize_number(likes),
        _normalize_number(comments),
        _normalize_number(shares),
    ]

    if row_index:
        ws.update(
            range_name=f"A{row_index}:F{row_index}",
            values=[values],
            value_input_option="USER_ENTERED",
        )
    else:
        ws.append_row(
            values,
            value_input_option="USER_ENTERED",
        )


def add_weekly_followers(week, platform, followers):
    get_worksheet("followers_weekly").append_row(
        [week, platform, _normalize_number(followers)],
        value_input_option="USER_ENTERED",
    )


def add_post(post_id, platform, title, likes, views):
    ws = get_worksheet("posts")

    existing = {
        str(row.get("post_id", "")).strip()
        for row in ws.get_all_records()
    }

    if str(post_id).strip() in existing:
        raise ValueError(f"Post ID {post_id} sudah digunakan.")

    ws.append_row(
        [
            str(post_id).strip(),
            platform,
            title,
            _normalize_number(likes),
            _normalize_number(views),
        ],
        value_input_option="USER_ENTERED",
    )


def add_demographic(platform, age_group, viewers):
    get_worksheet("demographics").append_row(
        [platform, age_group, _normalize_number(viewers)],
        value_input_option="USER_ENTERED",
    )


def delete_by_first_column(sheet_name, value):
    if sheet_name not in WORKSHEETS:
        raise ValueError(f"Nama worksheet tidak dikenal: {sheet_name}")

    ws = get_worksheet(sheet_name)
    records = ws.get_all_records()
    target = str(value).strip().lower()
    first_key = WORKSHEETS[sheet_name][0]

    for i, row in enumerate(records, start=2):
        if str(row.get(first_key, "")).strip().lower() == target:
            ws.delete_rows(i)
            return True

    return False
                         
