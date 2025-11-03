import os
import re
import json
import pathlib
from datetime import datetime

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

# Flask app imports
import sys
sys.path.append(str(pathlib.Path(__file__).resolve().parents[1]))  # add project root
from backend import create_app  # noqa
from backend.extensions import db  # noqa
from backend.models import TgPost  # noqa

SUPPORTED_COUNTRIES = [
    'Австрия','Армения','Бахрейн','Великобритания','Вьетнам','Германия','Гондурас',
    'Греция','Грузия','Доминикана','Египет','Индия','Индонезия','Исландия','Испания'
]
COUNTRY_INDEX = {c.lower(): c for c in SUPPORTED_COUNTRIES}

# Simple normalizer: remove leading '#', lower, replace latin variants where obvious
RE_TAG = re.compile(r"#([A-Za-zА-Яа-яЁё0-9_]+)")


def normalize_hashtag(tag: str) -> str:
    t = tag.lstrip('#').strip()
    # map common latin names to russian if needed (extend as necessary)
    repl = {
        'spain': 'Испания', 'greece': 'Греция', 'austria': 'Австрия', 'germany': 'Германия',
        'armenia': 'Армения', 'bahrain': 'Бахрейн', 'uk': 'Великобритания', 'greatbritain': 'Великобритания',
        'vietnam': 'Вьетнам', 'honduras': 'Гондурас', 'georgia': 'Грузия', 'dominicana': 'Доминикана',
        'egypt': 'Египет', 'india': 'Индия', 'indonesia': 'Индонезия', 'iceland': 'Исландия',
    }
    low = t.lower()
    if low in repl:
        return repl[low]
    return COUNTRY_INDEX.get(low, t)


def extract_countries(text: str):
    if not text:
        return []
    tags = RE_TAG.findall(text)
    res = []
    for raw in tags:
        name = normalize_hashtag(raw)
        if name in SUPPORTED_COUNTRIES and name not in res:
            res.append(name)
    return res


def ensure_upload_dir() -> pathlib.Path:
    project_root = pathlib.Path(__file__).resolve().parents[1]
    upload_dir = project_root / 'uploads' / 'tg'
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def local_url_for(file_path: pathlib.Path) -> str:
    # Given absolute path in uploads, return URL starting with /uploads/
    project_root = pathlib.Path(__file__).resolve().parents[1]
    rel = file_path.relative_to(project_root)
    return '/' + str(rel).replace('\\', '/')


def main():
    load_dotenv()
    api_id = int(os.environ.get('TELEGRAM_API_ID', '0') or '0')
    api_hash = os.environ.get('TELEGRAM_API_HASH', '')
    channel = os.environ.get('TELEGRAM_CHANNEL', 'Magic_Worlds_Travels')
    session = os.environ.get('TELEGRAM_SESSION_NAME', 'mw_import')

    if not api_id or not api_hash:
        print('ERROR: TELEGRAM_API_ID and TELEGRAM_API_HASH must be set in .env')
        return 1

    app = create_app()
    upload_base = ensure_upload_dir()

    client = TelegramClient(session, api_id, api_hash)
    client.parse_mode = 'html'

    async def run():
        await client.start()
        entity = await client.get_entity(channel)

        count = 0
        async for msg in client.iter_messages(entity, limit=None):
            if not (msg and (msg.message or msg.text)):
                continue
            text = msg.message or msg.text or ''
            countries = extract_countries(text)
            if not countries:
                # skip posts without supported country tags
                continue

            # Try get first photo
            image_urls = []
            if isinstance(msg.media, MessageMediaPhoto) or getattr(msg, 'photo', None):
                ts = datetime.fromtimestamp(msg.date.timestamp())
                subdir = upload_base / ts.strftime('%Y/%m')
                subdir.mkdir(parents=True, exist_ok=True)
                filename = f"{msg.id}.jpg"
                target = subdir / filename
                try:
                    await client.download_media(msg, file=str(target))
                    image_urls.append(local_url_for(target))
                except Exception as e:
                    print('download failed:', e)

            # Upsert into DB
            with app.app_context():
                existing = TgPost.query.filter_by(tg_message_id=msg.id).first()
                if not existing:
                    existing = TgPost(tg_message_id=msg.id)
                    db.session.add(existing)
                existing.date = msg.date
                existing.text = text
                existing.countries_json = json.dumps(countries, ensure_ascii=False)
                existing.image_urls_json = json.dumps(image_urls, ensure_ascii=False)
                existing.source_link = f"https://t.me/{channel}/{msg.id}"
                try:
                    db.session.commit()
                    count += 1
                except Exception as e:
                    db.session.rollback()
                    print('DB error:', e)

        print(f'Imported/updated posts: {count}')

    client.loop.run_until_complete(run())


if __name__ == '__main__':
    raise SystemExit(main())
