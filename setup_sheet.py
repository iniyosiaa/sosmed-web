from sheets import get_spreadsheet, WORKSHEETS

def main():
    spreadsheet = get_spreadsheet()

    for name, headers in WORKSHEETS.items():
        try:
            ws = spreadsheet.worksheet(name)
            ws.clear()
        except Exception:
            ws = spreadsheet.add_worksheet(
                title=name,
                rows=100,
                cols=len(headers),
            )

        ws.update("A1", [headers])

    # Initial example data
    spreadsheet.worksheet("platforms").append_rows([
        ["Instagram", 12500, 850000, 42000, 2300, 1200],
        ["YouTube", 8200, 620000, 28000, 1700, 900],
        ["TikTok", 15300, 1250000, 65000, 4200, 3100],
    ])

    spreadsheet.worksheet("followers_weekly").append_rows([
        ["Minggu 1", "Instagram", 10000],
        ["Minggu 2", "Instagram", 10800],
        ["Minggu 3", "Instagram", 11600],
        ["Minggu 4", "Instagram", 12500],
        ["Minggu 1", "YouTube", 6500],
        ["Minggu 2", "YouTube", 7100],
        ["Minggu 3", "YouTube", 7700],
        ["Minggu 4", "YouTube", 8200],
        ["Minggu 1", "TikTok", 12000],
        ["Minggu 2", "TikTok", 13200],
        ["Minggu 3", "TikTok", 14300],
        ["Minggu 4", "TikTok", 15300],
    ])

    spreadsheet.worksheet("posts").append_rows([
        ["P001", "Instagram", "Konten Edukasi", 4200, 35000],
        ["P002", "Instagram", "Behind The Scene", 6800, 52000],
        ["P003", "YouTube", "Video Tutorial", 9200, 85000],
        ["P004", "TikTok", "Tips Singkat", 15000, 160000],
        ["P005", "TikTok", "Trend Challenge", 12000, 140000],
    ])

    spreadsheet.worksheet("demographics").append_rows([
        ["Instagram", "13-17", 1200],
        ["Instagram", "18-24", 4200],
        ["Instagram", "25-34", 2800],
        ["Instagram", "35-44", 1100],
        ["YouTube", "13-17", 900],
        ["YouTube", "18-24", 2800],
        ["YouTube", "25-34", 2400],
        ["YouTube", "35-44", 1000],
        ["TikTok", "13-17", 4500],
        ["TikTok", "18-24", 6200],
        ["TikTok", "25-34", 3000],
        ["TikTok", "35-44", 900],
    ])

    print("Google Sheets berhasil disiapkan.")

if __name__ == "__main__":
    main()
