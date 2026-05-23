import argparse
import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Tuple

from aiogram import Bot
from instagrapi import Client

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

STATE_FILE = Path(os.getenv("STATE_FILE", "monitor_state.json"))


def get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def load_config() -> dict:
    return {
        "instagram_username": get_required_env("INSTAGRAM_USERNAME"),
        "instagram_password": get_required_env("INSTAGRAM_PASSWORD"),
        "target_username": get_required_env("TARGET_USERNAME"),
        "telegram_bot_token": get_required_env("TELEGRAM_BOT_TOKEN"),
        "telegram_user_id": int(get_required_env("TELEGRAM_USER_ID")),
        "check_every_seconds": int(os.getenv("CHECK_EVERY_SECONDS", "1800")),
    }


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


def fetch_subscriptions_and_followers(username: str, password: str, target_username: str) -> Tuple[list[str], list[str]]:
    cl = Client()
    cl.login(username, password)

    user_id = cl.user_id_from_username(target_username)
    followers_data = cl.user_followers(user_id)
    following_data = cl.user_following(user_id)

    followers = sorted(user.username for user in followers_data.values())
    following = sorted(user.username for user in following_data.values())

    return followers, following


async def send_telegram_message(bot: Bot, user_id: int, text: str) -> None:
    await bot.send_message(chat_id=user_id, text=text)


async def run_check(bot: Bot, config: dict, state: dict) -> bool:
    followers, following = await asyncio.to_thread(
        fetch_subscriptions_and_followers,
        config["instagram_username"],
        config["instagram_password"],
        config["target_username"],
    )

    first_run = not state["followers"] and not state["following"]
    if first_run:
        state["followers"] = followers
        state["following"] = following
        save_state(state)
        await send_telegram_message(
            bot,
            config["telegram_user_id"],
            f"📌 База сохранена для @{config['target_username']}.\n"
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
        await send_telegram_message(bot, config["telegram_user_id"], "\n\n".join(messages))
        state["followers"] = followers
        state["following"] = following
        save_state(state)
        return True

    logger.info("No changes detected.")
    return False


async def monitor(run_once: bool) -> None:
    config = load_config()
    bot = Bot(token=config["telegram_bot_token"])
    state = load_state()

    await send_telegram_message(
        bot,
        config["telegram_user_id"],
        f"✅ Мониторинг Instagram запущен для @{config['target_username']}.\n"
        f"Интервал проверки: {config['check_every_seconds'] // 60} минут.",
    )

    while True:
        try:
            await run_check(bot, config, state)
        except Exception as exc:
            logger.exception("Check failed: %s", exc)
            await send_telegram_message(bot, config["telegram_user_id"], f"⚠️ Ошибка проверки: {exc}")

        if run_once:
            break
        await asyncio.sleep(config["check_every_seconds"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Instagram followers/following monitor")
    parser.add_argument("--once", action="store_true", help="Run one check and exit")
    args = parser.parse_args()
    asyncio.run(monitor(run_once=args.once))
