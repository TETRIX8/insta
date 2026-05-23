import argparse
import asyncio
import json
import logging
from pathlib import Path
from typing import Tuple

from aiogram import Bot
from instagrapi import Client


logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# HARD-CODED CONFIG (as requested)
INSTAGRAM_USERNAME = "evloeww_1"
INSTAGRAM_PASSWORD = "7Qi%e@hvfehbb#syej"
TARGET_USERNAME = "mkk.dzv"
TELEGRAM_BOT_TOKEN = "8683233882:AAG0f2U_tzVwqzPgvtKMx10qSZOKC8nQyxY"
TELEGRAM_USER_ID = 8051344127
CHECK_EVERY_SECONDS = 1800
STATE_FILE = Path("monitor_state.json")


def load_state() -> dict:
    if STATE_FILE.exists():
        try:
            return json.loads(STATE_FILE.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning("State file is corrupted, recreating it.")
    return {"followers": [], "following": []}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def diff_lists(old_items: list[str], new_items: list[str]) -> Tuple[list[str], list[str]]:
    old_set = set(old_items)
    new_set = set(new_items)
    added = sorted(new_set - old_set)
    removed = sorted(old_set - new_set)
    return added, removed


def fetch_subscriptions_and_followers() -> Tuple[list[str], list[str]]:
    cl = Client()
    cl.login(INSTAGRAM_USERNAME, INSTAGRAM_PASSWORD)

    user_id = cl.user_id_from_username(TARGET_USERNAME)
    followers_data = cl.user_followers(user_id)
    following_data = cl.user_following(user_id)

    followers = sorted(user.username for user in followers_data.values())
    following = sorted(user.username for user in following_data.values())

    return followers, following


async def send_telegram_message(bot: Bot, text: str) -> None:
    await bot.send_message(chat_id=TELEGRAM_USER_ID, text=text)


async def run_check(bot: Bot, state: dict) -> bool:
    followers, following = await asyncio.to_thread(fetch_subscriptions_and_followers)

    first_run = not state["followers"] and not state["following"]
    if first_run:
        state["followers"] = followers
        state["following"] = following
        save_state(state)
        await send_telegram_message(
            bot,
            f"📌 База сохранена для @{TARGET_USERNAME}.\n"
            f"Подписчики: {len(followers)}\n"
            f"Подписки: {len(following)}",
        )
        return True

    new_followers, lost_followers = diff_lists(state["followers"], followers)
    new_following, unfollowed = diff_lists(state["following"], following)

    messages = []
    if new_followers:
        messages.append("🟢 Новые подписчики:\n" + "\n".join(f"+ @{u}" for u in new_followers))
    if lost_followers:
        messages.append("🔴 Отписались:\n" + "\n".join(f"- @{u}" for u in lost_followers))
    if new_following:
        messages.append("🟦 Новые подписки:\n" + "\n".join(f"+ @{u}" for u in new_following))
    if unfollowed:
        messages.append("🟧 Удалены из подписок:\n" + "\n".join(f"- @{u}" for u in unfollowed))

    if messages:
        await send_telegram_message(bot, "\n\n".join(messages))
        state["followers"] = followers
        state["following"] = following
        save_state(state)
        return True

    logger.info("No changes detected.")
    return False


async def monitor(run_once: bool) -> None:
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    state = load_state()

    await send_telegram_message(
        bot,
        f"✅ Мониторинг Instagram запущен для @{TARGET_USERNAME}.\n"
        f"Интервал проверки: {CHECK_EVERY_SECONDS // 60} минут.",
    )

    while True:
        try:
            await run_check(bot, state)
        except Exception as exc:
            logger.exception("Check failed: %s", exc)
            await send_telegram_message(bot, f"⚠️ Ошибка проверки: {exc}")

        if run_once:
            break
        await asyncio.sleep(CHECK_EVERY_SECONDS)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram followers/following monitor")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    args = parser.parse_args()
    asyncio.run(monitor(run_once=args.once))
