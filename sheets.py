import json
import os
from pathlib import Path

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials
import dotenv
from dotenv import load_dotenv

load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

WORKSHEETS = {
    "platforms": ["platform", "followers", "total_views", "likes", "comments", "shares"],
    "followers_weekly": ["week", "platform", "followers"],
    "posts": ["post_id", "platform", "title", "likes", "views"],
    "demographics": ["platform", "age_group", "viewers"],
}

def _get_credentials():
    # Streamlit Cloud: st.secrets["gcp_service_account"]
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            return Credentials.from_service_account_info(
                dict(st.secrets["gcp_service_account"]),
                scopes=SCOPES,
            )
    except Exception:
        pass

    # Generic cloud secret: GOOGLE_CREDS='{"type": ...}'
    google_creds = os.getenv("GOOGLE_CREDS")
    if google_creds:
        return Credentials.from_service_account_info(
            json.loads(google_creds),
            scopes=SCOPES,
        )

    # Local development
    credentials_file = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    path = Path(credentials_file)
    if not path.exists():
        raise FileNotFoundError(
            f"Credential file tidak ditemukan: {path.resolve()}"
        )

    return Credentials.from_service_account_file(
        str(path),
        scopes=SCOPES,
    )

def get_client():
    return gspread.authorize(_get_credentials())

def get_spreadsheet():
    sheet_name = os.getenv("SHEET_NAME")
    if not sheet_name:
        try:
            import streamlit as st
            sheet_name = st.secrets["SHEET_NAME"]
        except Exception:
            pass

    if not sheet_name:
        raise RuntimeError("SHEET_NAME belum diatur.")

    return get_client().open(sheet_name)

def get_worksheet(name):
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
    if value is None or value == "":
        return 0
    try:
        number = float(str(value).replace(",", "").strip())
        return int(number) if integer else number
    except ValueError:
        raise ValueError(f"Nilai angka tidak valid: {value}")

def update_platform(platform, followers, total_views, likes, comments, shares):
    ws = get_worksheet("platforms")
    records = ws.get_all_records()

    row_index = None
    for i, row in enumerate(records, start=2):
        if str(row.get("platform", "")).strip().lower() == platform.lower():
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
            f"A{row_index}:F{row_index}",
            [values],
            value_input_option="USER_ENTERED",
        )
    else:
        ws.append_row(values, value_input_option="USER_ENTERED")

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
    ws = get_worksheet(sheet_name)
    records = ws.get_all_records()
    target = str(value).strip().lower()

    for i, row in enumerate(records, start=2):
        first_key = WORKSHEETS[sheet_name][0]
        if str(row.get(first_key, "")).strip().lower() == target:
            ws.delete_rows(i)
            return True

    return False
