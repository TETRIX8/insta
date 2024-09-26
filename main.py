import asyncio
import logging
import re
from config import config
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

from downloader import downloader  # Импортируем модуль с функцией скачивания

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.bot_token.get_secret_value())
dp = Dispatcher()

@dp.message(Command('start'))
async def send_welcome(message: types.Message):
    await message.reply("Send me a URL!")

@dp.message()
async def download_content(message: types.Message):
    url = message.text
    reg_ins = r'https:\/\/www\.instagram\.com\/(p|reel)\/([A-Za-z0-9-_]+)\/'
    reg_tt = r'https://(vm\.tiktok\.com/\w+|www\.tiktok\.com/@[\w.-]+/(photo|video)/\d+|www\.tiktok\.com/video/\d+|www\.tiktok\.com/@\w+/video/\d+|vm\.tiktok\.com/\d+|www\.tiktok\.com/t/\w+|m\.tiktok\.com/v/\d+|www\.tiktok\.com/[\w.-]+/video/\d+|vt\.tiktok\.com/\w+)'
    instagram = re.search(reg_ins, url)
    tiktok = re.search(reg_tt, url)

    try:
        if instagram or tiktok:
            msg = await message.answer('⏳ Please wait...')
            content = await downloader(urls=url)

            if content['error'] == False:
                media = content['medias'][0]
                if media['type'] == 'image':
                    await bot.send_photo(chat_id=message.chat.id, photo=media['url'])
                elif media['type'] == 'video':
                    await bot.send_video(chat_id=message.chat.id, video=media['url'])
                if tiktok and 'medias' in content and len(content['medias']) > 1:
                    await bot.send_audio(chat_id=message.chat.id, audio=content['medias'][-1]['url'])
            else:
                # Provide fallback link if content isn't available
                dd = url.replace('www.', 'dd')
                await message.answer(dd)

            await msg.delete()
        else:
            await message.answer("Invalid URL. Please send a valid Instagram or TikTok link.")
    except Exception as e:
        logger.error(f"Failed to send media: {e}")
        await message.answer("Failed to process the media.")

async def main():
    print("Ваш бот запущен")
    print("████████╗███████╗████████╗██████╗░██╗██╗░░██╗")
    print("╚══██╔══╝██╔════╝╚══██╔══╝██╔══██╗██║╚██╗██╔╝")
    print("░░░██║░░░█████╗░░░░░██║░░░██████╔╝██║░╚███╔╝░")
    print("░░░██║░░░██╔══╝░░░░░██║░░░██╔══██╗██║░██╔██╗░")
    print("░░░██║░░░███████╗░░░██║░░░██║░░██║██║██╔╝╚██╗")
    print("░░░╚═╝░░░╚══════╝░░░╚═╝░░░╚═╝░░╚═╝╚═╝╚═╝░░╚═╝")
    print("GitHub репозиторий: https://github.com/TETRIX8/insta.git")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

