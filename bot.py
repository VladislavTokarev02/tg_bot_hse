from aiogram import Bot, Dispatcher
import asyncio
from handlers import router
import logging
from config import TOKEN



bot = Bot(token = TOKEN)
dp = Dispatcher()
dp.include_router(router)




async def main():
    logging.info("Инициализация бота...")

    try:
        logging.info("Запуск бота...")
        await dp.start_polling(bot)
    except Exception as e:
        logging.error(f"Ошибка при запуске: {e}")

if __name__ == "__main__":
    asyncio.run(main())