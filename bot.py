import logging
import os
import dotenv

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)

from sheets import (
    add_demographic,
    add_post,
    add_weekly_followers,
    get_all_data,
    update_platform,
)

load_dotenv()

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

PLATFORM, FOLLOWERS, VIEWS, LIKES, COMMENTS, SHARES = range(6)
WEEK, WEEK_PLATFORM, WEEK_FOLLOWERS = range(6, 9)
POST_ID, POST_PLATFORM, POST_TITLE, POST_LIKES, POST_VIEWS = range(9, 14)
DEM_PLATFORM, AGE_GROUP, DEM_VIEWERS = range(14, 17)

def admin_ids():
    raw = os.getenv("ADMIN_TELEGRAM_IDS", "")
    return {x.strip() for x in raw.split(",") if x.strip()}

def is_admin(update: Update):
    user = update.effective_user
    return user and str(user.id) in admin_ids()

async def reject_non_admin(update: Update):
    if update.callback_query:
        await update.callback_query.answer("Akses ditolak.", show_alert=True)
    elif update.message:
        await update.message.reply_text("⛔ Kamu tidak memiliki akses admin.")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await reject_non_admin(update)
        return

    keyboard = [
        [InlineKeyboardButton("📊 Kelola Platform", callback_data="menu_platform")],
        [InlineKeyboardButton("📈 Tambah Followers Mingguan", callback_data="menu_weekly")],
        [InlineKeyboardButton("📝 Tambah Postingan", callback_data="menu_post")],
        [InlineKeyboardButton("👥 Tambah Demografi", callback_data="menu_dem")],
        [InlineKeyboardButton("🔄 Lihat Ringkasan", callback_data="summary")],
    ]

    await update.message.reply_text(
        "👑 *ADMIN PANEL*\n\nPilih data yang ingin dikelola:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if not is_admin(update):
        await reject_non_admin(update)
        return ConversationHandler.END

    action = query.data

    if action == "menu_platform":
        await query.edit_message_text(
            "📱 Pilih platform yang ingin diperbarui:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Instagram", callback_data="platform_Instagram")],
                [InlineKeyboardButton("YouTube", callback_data="platform_YouTube")],
                [InlineKeyboardButton("TikTok", callback_data="platform_TikTok")],
                [InlineKeyboardButton("❌ Batal", callback_data="cancel")],
            ]),
        )
        return PLATFORM

    if action == "menu_weekly":
        await query.edit_message_text("📅 Masukkan minggu, contoh: Minggu 1")
        return WEEK

    if action == "menu_post":
        await query.edit_message_text("🆔 Masukkan Post ID, contoh: P001")
        return POST_ID

    if action == "menu_dem":
        await query.edit_message_text(
            "📱 Pilih platform:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Instagram", callback_data="dem_Instagram")],
                [InlineKeyboardButton("YouTube", callback_data="dem_YouTube")],
                [InlineKeyboardButton("TikTok", callback_data="dem_TikTok")],
                [InlineKeyboardButton("❌ Batal", callback_data="cancel")],
            ]),
        )
        return DEM_PLATFORM

    if action == "summary":
        data = get_all_data()
        lines = ["📊 *RINGKASAN DATA*\n"]
        for _, row in data["platforms"].iterrows():
            lines.append(
                f"• {row['platform']}: "
                f"{row['followers']} followers | "
                f"{row['total_views']} views"
            )
        await query.edit_message_text(
            "\n".join(lines),
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("⬅️ Menu", callback_data="back_menu")]
            ]),
        )

    return ConversationHandler.END

async def platform_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    platform = query.data.replace("platform_", "")
    context.user_data["platform"] = platform
    await query.edit_message_text(
        f"📱 {platform}\n\nMasukkan jumlah *followers* terbaru:",
        parse_mode="Markdown",
    )
    return FOLLOWERS

async def followers_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["followers"] = update.message.text.strip()
    await update.message.reply_text("Masukkan *total views* terbaru:", parse_mode="Markdown")
    return VIEWS

async def views_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["views"] = update.message.text.strip()
    await update.message.reply_text("Masukkan *total likes*:")
    return LIKES

async def likes_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["likes"] = update.message.text.strip()
    await update.message.reply_text("Masukkan *total comments*:")
    return COMMENTS

async def comments_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["comments"] = update.message.text.strip()
    await update.message.reply_text("Masukkan *total shares*:")
    return SHARES

async def shares_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        update_platform(
            context.user_data["platform"],
            context.user_data["followers"],
            context.user_data["views"],
            context.user_data["likes"],
            context.user_data["comments"],
            update.message.text.strip(),
        )
        await update.message.reply_text(
            f"✅ Data {context.user_data['platform']} berhasil diperbarui."
        )
    except Exception as exc:
        logger.exception("Update platform gagal")
        await update.message.reply_text(f"❌ Gagal menyimpan data: {exc}")

    context.user_data.clear()
    return ConversationHandler.END

async def weekly_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["week"] = update.message.text.strip()
    await update.message.reply_text(
        "Pilih platform:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Instagram", callback_data="weekly_Instagram")],
            [InlineKeyboardButton("YouTube", callback_data="weekly_YouTube")],
            [InlineKeyboardButton("TikTok", callback_data="weekly_TikTok")],
        ]),
    )
    return WEEK_PLATFORM

async def weekly_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["platform"] = query.data.replace("weekly_", "")
    await query.edit_message_text("Masukkan jumlah followers pada minggu tersebut:")
    return WEEK_FOLLOWERS

async def weekly_followers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        add_weekly_followers(
            context.user_data["week"],
            context.user_data["platform"],
            update.message.text.strip(),
        )
        await update.message.reply_text("✅ Data followers mingguan berhasil ditambahkan.")
    except Exception as exc:
        await update.message.reply_text(f"❌ Gagal menyimpan data: {exc}")
    context.user_data.clear()
    return ConversationHandler.END

async def post_id_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["post_id"] = update.message.text.strip()
    await update.message.reply_text(
        "Pilih platform:",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Instagram", callback_data="post_Instagram")],
            [InlineKeyboardButton("YouTube", callback_data="post_YouTube")],
            [InlineKeyboardButton("TikTok", callback_data="post_TikTok")],
        ]),
    )
    return POST_PLATFORM

async def post_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["platform"] = query.data.replace("post_", "")
    await query.edit_message_text("Masukkan judul/nama postingan:")
    return POST_TITLE

async def post_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text.strip()
    await update.message.reply_text("Masukkan jumlah likes:")
    return POST_LIKES

async def post_likes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["likes"] = update.message.text.strip()
    await update.message.reply_text("Masukkan jumlah views:")
    return POST_VIEWS

async def post_views(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        add_post(
            context.user_data["post_id"],
            context.user_data["platform"],
            context.user_data["title"],
            context.user_data["likes"],
            update.message.text.strip(),
        )
        await update.message.reply_text("✅ Postingan berhasil ditambahkan.")
    except Exception as exc:
        await update.message.reply_text(f"❌ Gagal menyimpan data: {exc}")
    context.user_data.clear()
    return ConversationHandler.END

async def demographic_platform(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    context.user_data["platform"] = query.data.replace("dem_", "")
    await query.edit_message_text("Masukkan kelompok umur, contoh: 18-24")
    return AGE_GROUP

async def age_group_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age_group"] = update.message.text.strip()
    await update.message.reply_text("Masukkan jumlah penonton:")
    return DEM_VIEWERS

async def demographic_viewers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        add_demographic(
            context.user_data["platform"],
            context.user_data["age_group"],
            update.message.text.strip(),
        )
        await update.message.reply_text("✅ Data demografi berhasil ditambahkan.")
    except Exception as exc:
        await update.message.reply_text(f"❌ Gagal menyimpan data: {exc}")
    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text("❌ Operasi dibatalkan.")
    else:
        await update.message.reply_text("❌ Operasi dibatalkan.")
    return ConversationHandler.END

def build_application():
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_TOKEN belum diatur.")

    app = Application.builder().token(token).build()

    conv_platform = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu, pattern="^menu_platform$")],
        states={
            PLATFORM: [CallbackQueryHandler(platform_selected, pattern="^platform_")],
            FOLLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, followers_input)],
            VIEWS: [MessageHandler(filters.TEXT & ~filters.COMMAND, views_input)],
            LIKES: [MessageHandler(filters.TEXT & ~filters.COMMAND, likes_input)],
            COMMENTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, comments_input)],
            SHARES: [MessageHandler(filters.TEXT & ~filters.COMMAND, shares_input)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern="^cancel$"),
            CommandHandler("cancel", cancel),
        ],
        per_user=True,
    )

    conv_weekly = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu, pattern="^menu_weekly$")],
        states={
            WEEK: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_input)],
            WEEK_PLATFORM: [CallbackQueryHandler(weekly_platform, pattern="^weekly_")],
            WEEK_FOLLOWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, weekly_followers)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    conv_post = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu, pattern="^menu_post$")],
        states={
            POST_ID: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_id_input)],
            POST_PLATFORM: [CallbackQueryHandler(post_platform, pattern="^post_")],
            POST_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_title)],
            POST_LIKES: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_likes)],
            POST_VIEWS: [MessageHandler(filters.TEXT & ~filters.COMMAND, post_views)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    conv_dem = ConversationHandler(
        entry_points=[CallbackQueryHandler(menu, pattern="^menu_dem$")],
        states={
            DEM_PLATFORM: [CallbackQueryHandler(demographic_platform, pattern="^dem_")],
            AGE_GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, age_group_input)],
            DEM_VIEWERS: [MessageHandler(filters.TEXT & ~filters.COMMAND, demographic_viewers)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_user=True,
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_platform)
    app.add_handler(conv_weekly)
    app.add_handler(conv_post)
    app.add_handler(conv_dem)
    app.add_handler(CallbackQueryHandler(menu, pattern="^(summary|back_menu)$"))
    app.add_handler(CallbackQueryHandler(cancel, pattern="^cancel$"))

    return app

if __name__ == "__main__":
    application = build_application()
    application.run_polling(drop_pending_updates=True)
