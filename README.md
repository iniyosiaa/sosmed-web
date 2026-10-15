# Social Media Dashboard

Project dashboard media sosial dengan:

- Streamlit sebagai dashboard
- Telegram Bot sebagai admin control panel
- Google Sheets sebagai database
- Google Sheets API / gspread
- Plotly untuk chart

## Struktur

- `app.py` -> dashboard Streamlit
- `bot.py` -> Telegram admin bot
- `sheets.py` -> akses Google Sheets
- `calculations.py` -> KPI dan perhitungan
- `charts.py` -> visualisasi
- `setup_sheet.py` -> membuat worksheet + data contoh

## 1. Buat Google Sheet

Buat spreadsheet bernama sesuai `SHEET_NAME`.

Buat Google Service Account dan download JSON sebagai:

```text
credentials.json
```

Share Google Sheet ke email service account tersebut sebagai Editor.

## 2. Setup lokal

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

Install:

```bash
pip install -r requirements.txt
```

Salin `.env.example` menjadi `.env`, lalu isi token Telegram, ID Telegram admin, dan nama spreadsheet.

Siapkan database:

```bash
python setup_sheet.py
```

## 3. Jalankan dashboard

```bash
streamlit run app.py
```

## 4. Jalankan bot

Terminal kedua:

```bash
python bot.py
```

Dashboard dan bot menggunakan Google Sheets yang sama.

## 5. Deployment

Jangan upload:

- `.env`
- `credentials.json`

ke GitHub.

Untuk Streamlit Cloud, masukkan credentials sebagai Streamlit Secrets.

Contoh:

```toml
SHEET_NAME = "Social Media Database"

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "..."
```

Telegram bot sebaiknya dijalankan sebagai service/process terpisah dari Streamlit jika ingin berjalan terus-menerus.

## Catatan KPI

Project ini menggunakan:

```text
Engagement Rate =
(Likes + Comments + Shares) / Total Views × 100
```

Jika sekolah/guru menentukan formula ER yang berbeda, cukup ubah fungsi `calculate_kpis()` di `calculations.py`.
