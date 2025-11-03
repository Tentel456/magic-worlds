import os
from dotenv import load_dotenv
from telegram.ext import Updater, CommandHandler
from backend import create_app
from backend.extensions import db
from backend.models import TelegramVerification
from datetime import datetime

# Load .env before reading token
load_dotenv()
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    raise SystemExit("TELEGRAM_BOT_TOKEN is not set")

app = create_app(os.environ.get("FLASK_ENV", "development"))


def start(update, context):
    args = context.args
    if not args:
        update.message.reply_text("Здравствуйте! Отправьте ссылку из сайта с параметром, чтобы подтвердить регистрацию.")
        return
    token = args[0]
    with app.app_context():
        tv = TelegramVerification.query.filter_by(token=token).first()
        if not tv:
            update.message.reply_text("Ссылка недействительна или устарела. Начните регистрацию заново на сайте.")
            return
        # Derive username from Telegram
        eff = update.effective_user
        tg_username = (eff.username or "").strip()
        if tg_username:
            candidate = tg_username
        else:
            # fallback: first+last or user<id>
            first = (eff.first_name or "").strip()
            last = (eff.last_name or "").strip()
            candidate = (first + last).strip() or f"user{eff.id}"
        # sanitize spaces
        candidate = candidate.replace(" ", "_")
        tv.username = candidate
        tv.tg_user_id = str(eff.id)
        # Try to fetch avatar
        try:
            photos = context.bot.get_user_profile_photos(eff.id, limit=1)
            if photos.total_count > 0:
                file_id = photos.photos[0][-1].file_id  # largest size
                tg_file = context.bot.get_file(file_id)
                # Construct public URL to the file
                tv.avatar_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{tg_file.file_path}"
        except Exception:
            pass
        tv.verified_at = datetime.utcnow()
        db.session.commit()
        # send code
        update.message.reply_text(
            f"Ваш код подтверждения: <b>{tv.code}</b>\nВведите его на сайте, чтобы завершить регистрацию.",
            parse_mode='HTML'
        )


def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start, pass_args=True))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
