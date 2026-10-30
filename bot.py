import logging
import os
import re
from io import BytesIO
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, KeepTogether
)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler, ContextTypes,
    ConversationHandler, MessageHandler, filters,
)

from sheets import (
    add_demographic, add_post, add_weekly_followers,
    get_all_data, update_platform,
)

load_dotenv()
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("socialpulse_bot")

# Conversation states
PLATFORM, PF_FOLLOWERS, PF_VIEWS, PF_LIKES, PF_COMMENTS, PF_SHARES = range(6)
WK_LABEL, WK_PLATFORM, WK_FOLLOWERS = range(6, 9)
POST_ID, POST_PLATFORM, POST_TITLE, POST_LIKES, POST_VIEWS = range(9, 14)
DEM_PLATFORM, DEM_AGE, DEM_VIEWERS = range(14, 17)

NAVY = colors.HexColor("#101B2D")
NAVY_LIGHT = colors.HexColor("#1D2B42")
BLUE = colors.HexColor("#3978C6")
PALE = colors.HexColor("#EEF3F9")
INK = colors.HexColor("#243247")
MUTED = colors.HexColor("#68778D")
GREEN = colors.HexColor("#16865B")
BORDER = colors.HexColor("#DCE4EE")

PLATFORMS = ["Instagram", "YouTube", "TikTok"]
NUMERIC_SUGGESTIONS = [
    ("1K", "1000"), ("5K", "5000"), ("10K", "10000"),
    ("25K", "25000"), ("50K", "50000"), ("100K", "100000"),
]

def admin_ids():
    return {x.strip() for x in os.getenv("ADMIN_TELEGRAM_IDS", "").split(",") if x.strip()}

def is_admin(update: Update):
    user = update.effective_user
    return bool(user and str(user.id) in admin_ids())

async def deny(update: Update):
    if update.callback_query:
        await update.callback_query.answer("Akses admin diperlukan.", show_alert=True)
    elif update.effective_message:
        await update.effective_message.reply_text("⛔ Fitur ini khusus admin.")

def main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 Perbarui data platform", callback_data="menu_platform")],
        [InlineKeyboardButton("📈 Tambah followers mingguan", callback_data="menu_weekly")],
        [InlineKeyboardButton("📝 Tambah postingan", callback_data="menu_post")],
        [InlineKeyboardButton("👥 Tambah demografi", callback_data="menu_dem")],
        [InlineKeyboardButton("📊 Ringkasan dashboard", callback_data="summary"),
         InlineKeyboardButton("📄 Unduh laporan PDF", callback_data="pdf")],
    ])

def cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("✖ Batalkan operasi", callback_data="cancel")]])

def platform_keyboard(prefix):
    rows = [[InlineKeyboardButton(p, callback_data=f"{prefix}_{p}")] for p in PLATFORMS]
    rows.append([InlineKeyboardButton("✖ Batalkan operasi", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def number_keyboard():
    rows = []
    for i in range(0, len(NUMERIC_SUGGESTIONS), 3):
        rows.append([
            InlineKeyboardButton(label, callback_data=f"num:{value}")
            for label, value in NUMERIC_SUGGESTIONS[i:i+3]
        ])
    rows.append([InlineKeyboardButton("✍️ Isi angka sendiri", callback_data="num:custom")])
    rows.append([InlineKeyboardButton("✖ Batalkan operasi", callback_data="cancel")])
    return InlineKeyboardMarkup(rows)

def number_value(raw):
    """Accepts 5k, 1.5k, 5.000, 5000, and plain numbers."""
    text = str(raw).strip().lower().replace(" ", "")
    if not text:
        raise ValueError("Angka tidak boleh kosong.")
    multiplier = 1
    if text.endswith("k"):
        multiplier, text = 1000, text[:-1].replace(",", ".")
    elif text.endswith("m"):
        multiplier, text = 1_000_000, text[:-1].replace(",", ".")
    else:
        text = text.replace(".", "").replace(",", "")
    try:
        value = float(text) * multiplier
    except ValueError:
        raise ValueError("Format angka belum dikenali. Contoh: 5000, 5k, atau 1.5k.")
    if value < 0 or value != int(value):
        raise ValueError("Masukkan angka bulat positif atau nol.")
    return int(value)

async def ask(update, context, text, suggestions=False):
    markup = number_keyboard() if suggestions else cancel_keyboard()
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup)
    else:
        await update.effective_message.reply_text(text, reply_markup=markup)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    await update.effective_message.reply_text(
        "✨ *SOCIALPULSE · ADMIN STUDIO*\n"
        "Kelola data media sosial dengan lebih praktis.\n\n"
        "Pilih aktivitas di bawah. Kamu bisa membatalkan proses kapan saja dengan tombol ✖ atau /cancel.",
        reply_markup=main_menu_keyboard(), parse_mode="Markdown",
    )

async def menu_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        return await deny(update)
    action = q.data
    context.user_data.clear()
    if action == "menu_platform":
        await q.edit_message_text("📱 *Perbarui data platform*\nPilih akun yang ingin diperbarui:", reply_markup=platform_keyboard("pf"), parse_mode="Markdown")
        return PLATFORM
    if action == "menu_weekly":
        await ask(update, context, "📈 *Tambah data mingguan*\nMasukkan label minggu, misalnya `Minggu 1` atau `2026-W10`.")
        return WK_LABEL
    if action == "menu_post":
        await ask(update, context, "📝 *Tambah postingan*\nMasukkan ID unik postingan, misalnya `IG-001`.")
        return POST_ID
    if action == "menu_dem":
        await q.edit_message_text("👥 *Tambah demografi audiens*\nPilih platform:", reply_markup=platform_keyboard("dem"), parse_mode="Markdown")
        return DEM_PLATFORM
    if action == "summary":
        await send_summary(update, context, edit=True)
        return ConversationHandler.END
    if action == "pdf":
        await send_pdf(update, context)
        return ConversationHandler.END
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer("Operasi dibatalkan.")
        await update.callback_query.edit_message_text(
            "↩️ *Operasi dibatalkan.* Tidak ada data yang diubah.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 Kembali ke menu", callback_data="back")]]),
            parse_mode="Markdown",
        )
    elif update.effective_message:
        await update.effective_message.reply_text(
            "↩️ Operasi dibatalkan. Tidak ada data yang diubah.",
            reply_markup=main_menu_keyboard(),
        )
    return ConversationHandler.END

async def back_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not is_admin(update):
        return await deny(update)
    context.user_data.clear()
    await q.edit_message_text("🏠 *ADMIN STUDIO*\nPilih aktivitas:", reply_markup=main_menu_keyboard(), parse_mode="Markdown")

async def platform_selected(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["platform"] = q.data.replace("pf_", "")
    await ask(update, context, f"📱 *{context.user_data['platform']}*\nMasukkan total followers terbaru.\n\nContoh: `24500`, `24.5k`.", True)
    return PF_FOLLOWERS

async def save_numeric_step(update, context, key, prompt, next_state, next_key=None):
    try:
        raw = update.callback_query.data.split(":", 1)[1] if update.callback_query else update.effective_message.text
        if raw == "custom":
            await ask(update, context, prompt, True)
            return next_state
        context.user_data[key] = number_value(raw)
        await ask(update, context, prompt, True)
        return next_state
    except ValueError as exc:
        await ask(update, context, f"⚠️ {exc}\n\n{prompt}", True)
        return next_state

async def pf_followers(update, context):
    try:
        raw = update.callback_query.data.split(":",1)[1] if update.callback_query else update.effective_message.text
        if raw == "custom":
            await ask(update, context, "Ketik jumlah followers secara manual, contoh `24500` atau `24.5k`.", False)
            context.user_data["await_custom"] = "followers"
            return PF_FOLLOWERS
        context.user_data["followers"] = number_value(raw)
        await ask(update, context, "Masukkan total views terbaru:", True)
        return PF_VIEWS
    except ValueError as e:
        await ask(update, context, f"⚠️ {e}\nMasukkan total followers:", True)
        return PF_FOLLOWERS

async def pf_views(update, context):
    return await numeric_handler(update, context, "views", "Masukkan total likes:", PF_LIKES)
async def pf_likes(update, context):
    return await numeric_handler(update, context, "likes", "Masukkan total comments:", PF_COMMENTS)
async def pf_comments(update, context):
    return await numeric_handler(update, context, "comments", "Masukkan total shares:", PF_SHARES)

async def numeric_handler(update, context, key, prompt, next_state):
    try:
        raw = update.callback_query.data.split(":",1)[1] if update.callback_query else update.effective_message.text
        if raw == "custom":
            await ask(update, context, f"Ketik angka untuk {key} (contoh 25000 atau 25k).", False)
            context.user_data["await_custom"] = key
            return next_state - 1 if next_state == PF_VIEWS else next_state
        if context.user_data.get("await_custom") == key:
            context.user_data.pop("await_custom", None)
        context.user_data[key] = number_value(raw)
        await ask(update, context, prompt, True)
        return next_state
    except ValueError as e:
        await ask(update, context, f"⚠️ {e}\n{prompt}", True)
        return next_state - 1

async def pf_shares(update, context):
    try:
        raw = update.callback_query.data.split(":",1)[1] if update.callback_query else update.effective_message.text
        if raw == "custom":
            await ask(update, context, "Ketik jumlah shares secara manual.", False)
            context.user_data["await_custom"] = "shares"
            return PF_SHARES
        shares = number_value(raw)
        update_platform(
            context.user_data["platform"], context.user_data["followers"],
            context.user_data["views"], context.user_data["likes"],
            context.user_data["comments"], shares,
        )
        await finish(update, context, f"✅ Data *{context.user_data['platform']}* berhasil diperbarui.")
    except Exception as exc:
        logger.exception("Update platform gagal")
        await finish(update, context, f"❌ Data belum tersimpan: {exc}")
    return ConversationHandler.END

async def finish(update, context, message):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.edit_message_text(message, reply_markup=main_menu_keyboard(), parse_mode="Markdown")
    else:
        await update.effective_message.reply_text(message, reply_markup=main_menu_keyboard(), parse_mode="Markdown")

async def weekly_label(update, context):
    context.user_data["week"] = update.effective_message.text.strip()
    await ask(update, context, "Pilih platform untuk data minggu tersebut:", False)
    await update.effective_message.reply_text("Pilih platform:", reply_markup=platform_keyboard("wk"))
    return WK_PLATFORM

async def weekly_platform(update, context):
    q=update.callback_query; await q.answer()
    context.user_data["platform"]=q.data.replace("wk_","")
    await ask(update, context, "Masukkan jumlah followers pada minggu ini:", True)
    return WK_FOLLOWERS

async def weekly_followers(update, context):
    try:
        raw=update.callback_query.data.split(":",1)[1] if update.callback_query else update.effective_message.text
        if raw=="custom":
            await ask(update,context,"Ketik jumlah followers secara manual:",False); return WK_FOLLOWERS
        add_weekly_followers(context.user_data["week"],context.user_data["platform"],number_value(raw))
        await finish(update,context,"✅ Data followers mingguan berhasil ditambahkan.")
    except Exception as exc:
        await finish(update,context,f"❌ Gagal menyimpan data: {exc}")
    return ConversationHandler.END

async def post_id(update, context):
    context.user_data["post_id"]=update.effective_message.text.strip()
    await update.effective_message.reply_text("Pilih platform:",reply_markup=platform_keyboard("post"))
    return POST_PLATFORM
async def post_platform(update, context):
    q=update.callback_query; await q.answer()
    context.user_data["platform"]=q.data.replace("post_","")
    await ask(update,context,"Masukkan judul atau nama postingan:",False)
    return POST_TITLE
async def post_title(update, context):
    context.user_data["title"]=update.effective_message.text.strip()
    await ask(update,context,"Masukkan jumlah likes:",True)
    return POST_LIKES
async def post_likes(update, context):
    try:
        raw=update.callback_query.data.split(":",1)[1] if update.callback_query else update.effective_message.text
        if raw=="custom":
            await ask(update,context,"Ketik jumlah likes:",False); return POST_LIKES
        context.user_data["likes"]=number_value(raw)
        await ask(update,context,"Masukkan jumlah views:",True)
        return POST_VIEWS
    except ValueError as e:
        await ask(update,context,f"⚠️ {e}\nMasukkan jumlah likes:",True); return POST_LIKES
async def post_views(update, context):
    try:
        raw=update.callback_query.data.split(":",1)[1] if update.callback_query else update.effective_message.text
        if raw=="custom":
            await ask(update,context,"Ketik jumlah views:",False); return POST_VIEWS
        add_post(context.user_data["post_id"],context.user_data["platform"],context.user_data["title"],context.user_data["likes"],number_value(raw))
        await finish(update,context,"✅ Postingan berhasil ditambahkan.")
    except Exception as exc:
        await finish(update,context,f"❌ Gagal menyimpan postingan: {exc}")
    return ConversationHandler.END

async def dem_platform(update, context):
    q=update.callback_query; await q.answer()
    context.user_data["platform"]=q.data.replace("dem_","")
    await ask(update,context,"Masukkan kelompok umur, misalnya `18-24`.",False)
    return DEM_AGE
async def dem_age(update, context):
    context.user_data["age_group"]=update.effective_message.text.strip()
    await ask(update,context,"Masukkan jumlah penonton pada kelompok umur ini:",True)
    return DEM_VIEWERS
async def dem_viewers(update, context):
    try:
        raw=update.callback_query.data.split(":",1)[1] if update.callback_query else update.effective_message.text
        if raw=="custom":
            await ask(update,context,"Ketik jumlah penonton:",False); return DEM_VIEWERS
        add_demographic(context.user_data["platform"],context.user_data["age_group"],number_value(raw))
        await finish(update,context,"✅ Data demografi berhasil ditambahkan.")
    except Exception as exc:
        await finish(update,context,f"❌ Gagal menyimpan demografi: {exc}")
    return ConversationHandler.END

def fmt(value):
    try: return f"{float(value):,.0f}".replace(",", ".")
    except (TypeError, ValueError): return "0"

def make_pdf(data):
    buffer=BytesIO()
    doc=SimpleDocTemplate(buffer,pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=19*mm,bottomMargin=18*mm,title="SocialPulse - Laporan Analitik")
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Hero",parent=styles["Title"],fontName="Helvetica-Bold",fontSize=23,leading=27,textColor=colors.white,alignment=TA_LEFT,spaceAfter=5))
    styles.add(ParagraphStyle(name="HeroSub",parent=styles["Normal"],fontSize=9,leading=13,textColor=colors.HexColor("#D9E6F5")))
    styles.add(ParagraphStyle(name="SectionX",parent=styles["Heading2"],fontSize=13,leading=17,textColor=NAVY,spaceBefore=13,spaceAfter=7))
    styles.add(ParagraphStyle(name="SmallX",parent=styles["Normal"],fontSize=8,leading=11,textColor=MUTED))
    styles.add(ParagraphStyle(name="BodyX",parent=styles["BodyText"],fontSize=9,leading=13,textColor=INK))
    story=[]
    now=datetime.now().strftime("%d %B %Y · %H:%M")
    hero=Table([[[
        Paragraph("SOCIALPULSE",styles["Hero"]),
        Paragraph("LAPORAN ANALITIK MEDIA SOSIAL",styles["HeroSub"]),
        Paragraph(f"Dibuat pada {now}",styles["HeroSub"]),
    ]]],colWidths=[174*mm])
    hero.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,-1),NAVY),("BOX",(0,0),(-1,-1),0,NAVY),("LEFTPADDING",(0,0),(-1,-1),12),("RIGHTPADDING",(0,0),(-1,-1),12),("TOPPADDING",(0,0),(-1,-1),12),("BOTTOMPADDING",(0,0),(-1,-1),12)]))
    story += [hero,Spacer(1,10)]
    platforms=data.get("platforms",pd.DataFrame()).copy()
    posts=data.get("posts",pd.DataFrame()).copy()
    weekly=data.get("followers_weekly",pd.DataFrame()).copy()
    demos=data.get("demographics",pd.DataFrame()).copy()
    total_followers=pd.to_numeric(platforms.get("followers",pd.Series(dtype=float)),errors="coerce").fillna(0).sum()
    total_views=pd.to_numeric(platforms.get("total_views",pd.Series(dtype=float)),errors="coerce").fillna(0).sum()
    interactions=sum(pd.to_numeric(platforms.get(c,pd.Series(dtype=float)),errors="coerce").fillna(0).sum() for c in ["likes","comments","shares"])
    er=(interactions/total_views*100) if total_views else 0
    kpi=Table([
        ["TOTAL FOLLOWERS","TOTAL VIEWS","ENGAGEMENT RATE"],
        [fmt(total_followers),fmt(total_views),f"{er:.2f}%"]
    ],colWidths=[58*mm]*3,rowHeights=[8*mm,14*mm])
    kpi.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,-1),PALE),("TEXTCOLOR",(0,0),(-1,0),MUTED),
        ("TEXTCOLOR",(0,1),(-1,1),NAVY),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("FONTNAME",(0,1),(-1,1),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,0),7),
        ("FONTSIZE",(0,1),(-1,1),17),("ALIGN",(0,0),(-1,-1),"CENTER"),
        ("VALIGN",(0,0),(-1,-1),"MIDDLE"),("BOX",(0,0),(-1,-1),.5,BORDER),
        ("INNERGRID",(0,0),(-1,-1),.5,BORDER),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)
    ]))
    story += [kpi,Paragraph("Ringkasan Performa Platform",styles["SectionX"])]
    rows=[["Platform","Followers","Views","Likes","Comments","Shares"]]
    for _,r in platforms.iterrows():
        rows.append([str(r.get("platform","-")),fmt(r.get("followers")),fmt(r.get("total_views")),fmt(r.get("likes")),fmt(r.get("comments")),fmt(r.get("shares"))])
    if len(rows)==1: rows.append(["Belum ada data","-","-","-","-","-"])
    t=Table(rows,colWidths=[35*mm,27*mm,27*mm,25*mm,27*mm,25*mm],repeatRows=1)
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY_LIGHT),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("TEXTCOLOR",(0,1),(-1,-1),INK),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),("GRID",(0,0),(-1,-1),.35,BORDER),("ALIGN",(1,1),(-1,-1),"RIGHT"),("TOPPADDING",(0,0),(-1,-1),7),("BOTTOMPADDING",(0,0),(-1,-1),7)]))
    story.append(t)
    story.append(Paragraph("Konten dengan Performa Terbaik",styles["SectionX"]))
    if not posts.empty and "likes" in posts:
        posts["_likes"]=pd.to_numeric(posts["likes"],errors="coerce").fillna(0)
        top=posts.sort_values("_likes",ascending=False).head(7)
        prows=[["Postingan","Platform","Likes","Views"]]
        for _,r in top.iterrows(): prows.append([Paragraph(str(r.get("title","-"))[:75],styles["BodyX"]),str(r.get("platform","-")),fmt(r.get("likes")),fmt(r.get("views"))])
        pt=Table(prows,colWidths=[85*mm,30*mm,27*mm,24*mm],repeatRows=1)
        pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY_LIGHT),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),("GRID",(0,0),(-1,-1),.35,BORDER),("VALIGN",(0,0),(-1,-1),"MIDDLE"),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        story.append(pt)
    else: story.append(Paragraph("Belum ada data postingan.",styles["SmallX"]))
    story.append(Paragraph("Demografi Audiens",styles["SectionX"]))
    if not demos.empty:
        d=demos.copy(); d["_viewers"]=pd.to_numeric(d.get("viewers"),errors="coerce").fillna(0)
        d=d.groupby("age_group",as_index=False)["_viewers"].sum().sort_values("_viewers",ascending=False)
        drows=[["Kelompok umur","Jumlah penonton","Proporsi"]]
        total=d["_viewers"].sum()
        for _,r in d.iterrows(): drows.append([str(r["age_group"]),fmt(r["_viewers"]),f"{(r['_viewers']/total*100 if total else 0):.1f}%"])
        dt=Table(drows,colWidths=[58*mm,58*mm,50*mm],repeatRows=1)
        dt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),NAVY_LIGHT),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,PALE]),("GRID",(0,0),(-1,-1),.35,BORDER),("TOPPADDING",(0,0),(-1,-1),6),("BOTTOMPADDING",(0,0),(-1,-1),6)]))
        story.append(dt)
    else: story.append(Paragraph("Belum ada data demografi.",styles["SmallX"]))
    story.append(Spacer(1,12))
    story.append(Paragraph("Catatan: Engagement rate pada laporan ini dihitung dari (likes + comments + shares) ÷ total views × 100%. Laporan dibuat otomatis berdasarkan data Google Sheets saat diunduh.",styles["SmallX"]))
    def footer(canvas, doc_):
        canvas.saveState()
        w,h=A4
        canvas.setStrokeColor(BORDER); canvas.line(18*mm,13*mm,w-18*mm,13*mm)
        canvas.setFont("Helvetica",7); canvas.setFillColor(MUTED)
        canvas.drawString(18*mm,8*mm,"SOCIALPULSE · INTERNAL ANALYTICS REPORT")
        canvas.drawRightString(w-18*mm,8*mm,f"Halaman {doc_.page}")
        canvas.restoreState()
    doc.build(story,onFirstPage=footer,onLaterPages=footer)
    buffer.seek(0)
    return buffer

async def send_summary(update, context, edit=False):
    try:
        data=get_all_data()
        p=data["platforms"]
        lines=["📊 *RINGKASAN SOCIALPULSE*",""]
        if p.empty: lines.append("Belum ada data platform.")
        for _,r in p.iterrows():
            lines.append(f"• *{r['platform']}*: {fmt(r.get('followers'))} followers · {fmt(r.get('total_views'))} views")
        text="\n".join(lines)
        markup=main_menu_keyboard()
        if update.callback_query: await update.callback_query.edit_message_text(text,reply_markup=markup,parse_mode="Markdown")
        else: await update.effective_message.reply_text(text,reply_markup=markup,parse_mode="Markdown")
    except Exception as exc:
        logger.exception("Ringkasan gagal")
        if update.callback_query: await update.callback_query.edit_message_text(f"❌ Gagal membaca data: {exc}",reply_markup=main_menu_keyboard())
        else: await update.effective_message.reply_text(f"❌ Gagal membaca data: {exc}",reply_markup=main_menu_keyboard())

async def send_pdf(update, context):
    q=update.callback_query
    await q.answer("Menyiapkan laporan PDF…")
    try:
        data=get_all_data()
        pdf=make_pdf(data)
        filename=f"SocialPulse_Report_{datetime.now():%Y%m%d_%H%M}.pdf"
        await q.message.reply_document(
            document=pdf,filename=filename,
            caption="📄 *Laporan SocialPulse siap!*\n\nRingkasan platform, performa konten, dan demografi audiens dalam format PDF yang nyaman dibaca.",
            parse_mode="Markdown",
        )
    except Exception as exc:
        logger.exception("PDF export gagal")
        await q.message.reply_text(f"❌ Gagal membuat PDF: {exc}",reply_markup=main_menu_keyboard())

def build_application():
    token=os.getenv("TELEGRAM_TOKEN")
    if not token: raise RuntimeError("TELEGRAM_TOKEN belum diatur.")
    app=Application.builder().token(token).build()
    # All conversations share a global cancel fallback.
    common_fallbacks=[CommandHandler("cancel",cancel),CallbackQueryHandler(cancel,pattern="^cancel$")]
    conv=ConversationHandler(
        entry_points=[CallbackQueryHandler(menu_router,pattern="^menu_(platform|weekly|post|dem)$")],
        states={
            PLATFORM:[CallbackQueryHandler(platform_selected,pattern="^pf_")],
            PF_FOLLOWERS:[MessageHandler(filters.TEXT & ~filters.COMMAND,pf_followers),CallbackQueryHandler(pf_followers,pattern="^num:")],
            PF_VIEWS:[MessageHandler(filters.TEXT & ~filters.COMMAND,pf_views),CallbackQueryHandler(pf_views,pattern="^num:")],
            PF_LIKES:[MessageHandler(filters.TEXT & ~filters.COMMAND,pf_likes),CallbackQueryHandler(pf_likes,pattern="^num:")],
            PF_COMMENTS:[MessageHandler(filters.TEXT & ~filters.COMMAND,pf_comments),CallbackQueryHandler(pf_comments,pattern="^num:")],
            PF_SHARES:[MessageHandler(filters.TEXT & ~filters.COMMAND,pf_shares),CallbackQueryHandler(pf_shares,pattern="^num:")],
            WK_LABEL:[MessageHandler(filters.TEXT & ~filters.COMMAND,weekly_label)],
            WK_PLATFORM:[CallbackQueryHandler(weekly_platform,pattern="^wk_")],
            WK_FOLLOWERS:[MessageHandler(filters.TEXT & ~filters.COMMAND,weekly_followers),CallbackQueryHandler(weekly_followers,pattern="^num:")],
            POST_ID:[MessageHandler(filters.TEXT & ~filters.COMMAND,post_id)],
            POST_PLATFORM:[CallbackQueryHandler(post_platform,pattern="^post_")],
            POST_TITLE:[MessageHandler(filters.TEXT & ~filters.COMMAND,post_title)],
            POST_LIKES:[MessageHandler(filters.TEXT & ~filters.COMMAND,post_likes),CallbackQueryHandler(post_likes,pattern="^num:")],
            POST_VIEWS:[MessageHandler(filters.TEXT & ~filters.COMMAND,post_views),CallbackQueryHandler(post_views,pattern="^num:")],
            DEM_PLATFORM:[CallbackQueryHandler(dem_platform,pattern="^dem_")],
            DEM_AGE:[MessageHandler(filters.TEXT & ~filters.COMMAND,dem_age)],
            DEM_VIEWERS:[MessageHandler(filters.TEXT & ~filters.COMMAND,dem_viewers),CallbackQueryHandler(dem_viewers,pattern="^num:")],
        },
        fallbacks=common_fallbacks,
        per_user=True,per_chat=True,
    )
    app.add_handler(CommandHandler("start",start))
    app.add_handler(conv)
    app.add_handler(CallbackQueryHandler(back_menu,pattern="^back$"))
    app.add_handler(CallbackQueryHandler(menu_router,pattern="^(summary|pdf)$"))
    app.add_handler(CommandHandler("pdf",lambda u,c: send_pdf_command(u,c)))
    app.add_handler(CommandHandler("menu",start))
    app.add_handler(CommandHandler("cancel",cancel))
    return app

async def send_pdf_command(update, context):
    if not is_admin(update): return await deny(update)
    try:
        pdf=make_pdf(get_all_data())
        await update.effective_message.reply_document(pdf,filename=f"SocialPulse_Report_{datetime.now():%Y%m%d_%H%M}.pdf",caption="📄 Laporan SocialPulse kamu siap dibaca.")
    except Exception as exc:
        logger.exception("PDF command gagal")
        await update.effective_message.reply_text(f"❌ Gagal membuat PDF: {exc}")

if __name__=="__main__":
    build_application().run_polling(drop_pending_updates=True)
