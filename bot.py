import io
import re
import requests
from datetime import datetime, timedelta
from PIL import Image, ImageDraw

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    ChatPermissions,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = "7612739574:AAFB6UU73m-mEpTMuFAFW_UU22cpq8ZQHsY"
BAD_WORDS = ['badword1', 'badword2']
ALLOW_LINKS = False
WELCOME_BG_URL = "https://firebasestorage.googleapis.com/v0/b/loss-28250.appspot.com/o/fstore1%2F1aab435b-acc1-4075-aad7-a8d3012ab3b8.jpeg?alt=media&token=57a633eb-3dea-4e21-b1f6-e8a9137b0baf"

# How long since last message to count as "online"
ONLINE_THRESHOLD = timedelta(minutes=5)
# user_id -> (display_name, last_message_datetime)
last_active = {}

app = ApplicationBuilder().token(BOT_TOKEN).build()

def is_admin(member):
    return member.status in ('administrator', 'creator')

# --- WELCOME IMAGE ---
async def welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for member in update.message.new_chat_members:
        try:
            photos = await context.bot.get_user_profile_photos(member.id, limit=1)
            if photos.total_count > 0:
                f = await context.bot.get_file(photos.photos[0][-1].file_id)
                user_img = Image.open(io.BytesIO(await f.download_as_bytearray())).convert("RGBA")
            else:
                user_img = Image.new("RGBA", (200,200), (255,255,255,0))

            bg = Image.open(io.BytesIO(requests.get(WELCOME_BG_URL).content)).convert("RGBA").resize((800,400))
            user_img = user_img.resize((200,200))
            mask = Image.new("L", (200,200), 0)
            ImageDraw.Draw(mask).ellipse((0,0,200,200), fill=255)
            user_img.putalpha(mask)
            bg.paste(user_img, (580,180), user_img)

            buf = io.BytesIO()
            bg.save(buf, format='PNG')
            buf.seek(0)

            kb = [[InlineKeyboardButton("Group Rules", callback_data="rules")]]
            await update.message.reply_photo(
                photo=buf,
                caption=f"ကြိုဆိုပါတယ် {member.mention_html()}!",
                parse_mode='HTML',
                reply_markup=InlineKeyboardMarkup(kb)
            )
        except:
            await update.message.reply_text(
                f"ကြိုဆိုပါတယ် {member.mention_html()}!",
                parse_mode='HTML'
            )

# --- RULES BUTTON ---
async def rules_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.message.reply_text(
        "Group Rules:\n"
        "1. Spam မလုပ်ပါ\n"
        "2. မဆိုးမရွားပါနဲ့\n"
        "3. Admin နားထောင်ပါ"
    )

# --- ADMIN CHECK ---
async def admin_only(update: Update, context: ContextTypes.DEFAULT_TYPE):
    m = await context.bot.get_chat_member(update.effective_chat.id, update.effective_user.id)
    return is_admin(m)

# --- MODERATION ---
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return await update.message.reply_text("Admin မဟုတ်လို့ mute မလုပ်နိုင်ပါ")
    if not update.message.reply_to_message:
        return await update.message.reply_text("reply to a user to mute them")
    target = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(update.effective_chat.id, target, ChatPermissions())
    kb = [[InlineKeyboardButton("Unmute", callback_data=f"unmute:{target}")]]
    await update.message.reply_text("Muted.", reply_markup=InlineKeyboardMarkup(kb))

async def unmute_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    # only admins can click
    caller = await context.bot.get_chat_member(q.message.chat.id, q.from_user.id)
    if not is_admin(caller):
        return await q.answer("Admin မဟုတ်လို့ မဖြစ်နိုင်ပါ။", show_alert=True)
    target = int(q.data.split(":",1)[1])
    await context.bot.restrict_chat_member(q.message.chat.id, target, ChatPermissions(can_send_messages=True))
    await q.message.reply_text("Unmuted.")

async def unmute_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return await update.message.reply_text("Admin မဟုတ်လို့ unmute မလုပ်နိုင်ပါ")
    if not update.message.reply_to_message:
        return await update.message.reply_text("reply to a user to unmute them")
    target = update.message.reply_to_message.from_user.id
    await context.bot.restrict_chat_member(update.effective_chat.id, target, ChatPermissions(can_send_messages=True))
    await update.message.reply_text("Unmuted.")

async def kick(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return await update.message.reply_text("Admin မဟုတ်လို့ kick မလုပ်နိုင်ပါ")
    if not update.message.reply_to_message:
        return await update.message.reply_text("reply to a user to kick them")
    target = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(update.effective_chat.id, target)
    await context.bot.unban_chat_member(update.effective_chat.id, target)
    await update.message.reply_text("User kicked.")

async def ban(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return await update.message.reply_text("Admin မဟုတ်လို့ ban မလုပ်နိုင်ပါ")
    if not update.message.reply_to_message:
        return await update.message.reply_text("reply to a user to ban them")
    target = update.message.reply_to_message.from_user.id
    await context.bot.ban_chat_member(update.effective_chat.id, target)
    await update.message.reply_text("User banned.")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await admin_only(update, context):
        return await update.message.reply_text("Admin မဟုတ်လို့ warn မလုပ်နိုင်ပါ")
    if not update.message.reply_to_message:
        return await update.message.reply_text("reply to a user to warn them")
    await update.message.reply_text(
        f"{update.message.reply_to_message.from_user.mention_html()} ကို သတိပေးပြီးပါပြီ။",
        parse_mode="HTML"
    )

# --- FILTERS (bad words + links) ---
link_re = re.compile(r'https?://|t\.me|telegram\.me|www\.')

async def message_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    text = msg.text or ""
    user = msg.from_user

    # track activity
    if not user.is_bot:
        last_active[user.id] = (
            f"@{user.username}" if user.username else user.first_name,
            datetime.now()
        )

    # bad words
    if any(w in text.lower() for w in BAD_WORDS):
        return await msg.delete()

    # links
    if not ALLOW_LINKS and link_re.search(text):
        member = await context.bot.get_chat_member(msg.chat.id, user.id)
        if not is_admin(member) and not user.is_bot:
            return await msg.delete()

# block other bots posting t.me links
async def block_other_bots(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.message
    user = msg.from_user
    if user.is_bot and user.id != context.bot.id:
        if link_re.search(msg.text or ""):
            return await msg.delete()

# --- ONLINE COMMAND ---
async def online(update: Update, context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now()
    thresh = now - ONLINE_THRESHOLD
    names = [
        name for name, ts in last_active.values()
        if ts > thresh
    ]
    if not names:
        await update.message.reply_text("အခု online ဖြစ်နေလို့ သိနိုင်တဲ့ user မရှိသေးပါ။")
    else:
        text = "ယခု လူတွေ နီးကပ် active ဖြစ်နေလို့ 'online' စဆောင်ထားနိုင်ပါတယ်:\n\n"
        text += "\n".join(f"• {n}" for n in names)
        await update.message.reply_text(text)

# --- HANDLER REGISTRATION ---
app.add_handler(CommandHandler("rules", rules_callback))
app.add_handler(CallbackQueryHandler(rules_callback, pattern="^rules$"))

app.add_handler(CommandHandler("mute", mute))
app.add_handler(CallbackQueryHandler(unmute_button, pattern=r"^unmute:\d+$"))
app.add_handler(CommandHandler("unmute", unmute_cmd))
app.add_handler(CommandHandler("kick", kick))
app.add_handler(CommandHandler("ban", ban))
app.add_handler(CommandHandler("warn", warn))

app.add_handler(CommandHandler("online", online))

app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_filter))
app.add_handler(MessageHandler(filters.TEXT, block_other_bots))

# --- START ---
if __name__ == "__main__":
    app.run_polling()