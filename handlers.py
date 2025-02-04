from aiogram import Router, types, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import Form
from users import user_profiles, user_water_log
import utils
from utils import calculate_water_goal, get_temperature, get_food_info, log_workout, check_progress, send_progress_charts
import logging
import asyncio

router = Router()  # Создаём роутер для изоляции группы хэндлеров


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать! Я ваш бот. Введите /help для списка команд.")

# Главное меню клавиатуры
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/set_profile"), KeyboardButton(text="/log_water")],
        [KeyboardButton(text="/log_food"), KeyboardButton(text="/log_workout")],
        [KeyboardButton(text="/check_progress"), KeyboardButton(text="/help")],
    ],
    resize_keyboard=True
)


@router.message(Command("help"))
async def cmd_help(message: types.Message):
    help_text = (
        "Cписок доступных команд:\n"
        "/set_profile - Настроить профиль\n"
        "/log_water  - Записать количество воды\n"
        "/log_food  - Записать потребление пищи\n"
        "/log_workout <тип тренировки> <время в минутах> - Записать тренировку\n"
        "/check_progress - Проверить прогресс\n"
    )
    await message.reply(help_text, reply_markup=main_keyboard)

# FSM: диалог с пользователем для настройки профиля
@router.message(Command("set_profile"))
async def start_form(message: Message, state: FSMContext):
    await message.reply("Введите ваш вес (в кг):")
    await state.set_state(Form.weight)

@router.message(Form.weight)
async def weight_form(message: Message, state: FSMContext):
    await state.update_data(weight=message.text)
    await message.reply("Введите ваш рост (в см):")
    await state.set_state(Form.height)

@router.message(Form.height)
async def height_form(message: Message, state: FSMContext):
    await state.update_data(height=message.text)
    await message.reply("Введите ваш возраст:")
    await state.set_state(Form.age)

@router.message(Form.age)
async def age_form(message: Message, state: FSMContext):
    await state.update_data(age=message.text)
    await message.reply("Сколько минут активности у вас в день?")
    await state.set_state(Form.activity)

@router.message(Form.activity)
async def activity_form(message: Message, state: FSMContext):
    await state.update_data(activity=message.text)
    await message.reply("В каком городе Вы проживаете?")
    await state.set_state(Form.city)

@router.message(Form.city)
async def city_form(message: Message, state: FSMContext):
    await state.update_data(city=message.text)

    data = await state.get_data()

    user_profiles[message.from_user.id] = {
        "weight": data["weight"],
        "height": data["height"],
        "age": data["age"],
        "activity": data["activity"],
        "city": data["city"],
        "water_intake": 0
    }

    try:
        temperature = await get_temperature(message.from_user.id)
        water_goal = calculate_water_goal(float(data["weight"]), int(data["activity"]), temperature)

        profile_info = (
            f"*Ваш профиль настроен:*\n\n"
            f"Вес: {data['weight']} кг\n"
            f"Рост: {data['height']} см\n"
            f"Возраст: {data['age']} лет\n"
            f"Активность: {data['activity']} минут в день\n"
            f"Город: {data['city']}\n\n"
            f"*Температура: {temperature}°C*\n"
            f"*Рекомендуемая норма воды: {water_goal} мл в день*\n"
            f"*Выпито: {user_profiles[message.from_user.id]['water_intake']} мл*"
        )

        await message.reply(profile_info, parse_mode="Markdown")
    except ValueError as e:
        await message.reply(f"Ошибка: {str(e)}")

    await state.clear()


@router.message(Command("log_water"))
async def log_water(message: Message):
    try:
        water_amount = int(message.text.split()[1])
        user_id = message.from_user.id


        if user_id in user_profiles:
            user_data = user_profiles[user_id]


            user_data['water_intake'] += water_amount


            temperature = await get_temperature(user_id)
            water_goal = calculate_water_goal(
                float(user_data["weight"]),
                int(user_data["activity"]),
                temperature,
            )


            total_intake = user_data['water_intake']
            remaining_water = max(0, water_goal - total_intake)

            reply_text = (
                f"Записано {water_amount} мл воды.\n"
                f"Всего выпито: {total_intake} мл.\n"
                f"Осталось до нормы: {remaining_water} мл.\n"
                f"Рекомендуемая норма воды: {water_goal} мл."
            )

            await message.reply(reply_text)

        else:
            await message.reply("Сначала настройте профиль с помощью команды /set_profile.")
    except (IndexError, ValueError):
        await message.reply("Пожалуйста, укажите количество воды в миллилитрах. Пример: /log_water 250.")



@router.message(Command('log_food'))
async def log_food_handler(message: Message):
    user_id = message.from_user.id


    if user_id not in user_profiles:
        await message.reply("Сначала настройте профиль с помощью команды /set_profile.")
        return


    await message.reply("🍎 Введите название продукта для поиска.")
    user_profiles[user_id]['state'] = 'waiting_for_food_name'


@router.message(lambda message: user_profiles.get(message.from_user.id, {}).get('state') == 'waiting_for_food_name')
async def handle_food_name(message: Message):
    user_id = message.from_user.id
    food_name = message.text.strip()
    food_data = await get_food_info(food_name)

    if food_data:
        calories_per_100g = food_data['calories']
        user_profiles[user_id]['food_name'] = food_data['name']
        user_profiles[user_id]['calories_per_100g'] = calories_per_100g
        user_profiles[user_id]['state'] = 'waiting_for_food_amount'

        await message.reply(
            f"🍎 {food_data['name']} — {calories_per_100g} ккал на 100 г. Сколько грамм вы съели?"
        )
    else:
        await message.reply("🙁 Информация о продукте не найдена. Попробуйте ввести другой продукт.")



@router.message(lambda message: user_profiles.get(message.from_user.id, {}).get('state') == 'waiting_for_food_amount')
async def handle_food_amount(message: Message):
    user_id = message.from_user.id

    try:

        grams = float(message.text.strip())
        calories_per_100g = user_profiles[user_id].get('calories_per_100g', 0)
        total_calories = (grams / 100) * calories_per_100g


        if 'calories_consumed' not in user_profiles[user_id]:
            user_profiles[user_id]['calories_consumed'] = 0
        user_profiles[user_id]['calories_consumed'] += total_calories

        await message.reply(
            f"✅ Записано: {total_calories:.1f} ккал ({grams} г {user_profiles[user_id]['food_name']}).\n"
            f"Общее количество потребленных калорий: {user_profiles[user_id]['calories_consumed']:.1f} ккал."
        )
        user_profiles[user_id]['state'] = None

    except ValueError:
        await message.reply("⚠️ Пожалуйста, введите количество граммов в виде числа.")


@router.message(Command('log_workout'))
async def log_workout_handler(message: Message):
    user_id = message.from_user.id

    if user_id not in user_profiles:
        await message.reply("Сначала настройте профиль с помощью команды /set_profile.")
        return

    try:
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            raise IndexError

        workout_type = args[1].lower()
        duration = int(args[2])  # Продолжительность в минутах

        if duration <= 0:
            await message.reply("Продолжительность тренировки должна быть положительным числом. Пример:\n"
                                "/log_workout бег 30")
            return


        calories_burned, water_additional = log_workout(user_id, workout_type, duration)

        await message.reply(
            f"🏋️‍♂️ Тренировка: {workout_type.capitalize()} на {duration} минут.\n"
            f"🔥 Сожжено калорий: {calories_burned:.0f} ккал.\n"
            f"💧 Дополнительно выпейте воды: {water_additional:.2f} л."
        )
    except IndexError:
        await message.reply("⚠️ Пожалуйста, укажите тип тренировки и продолжительность в минутах. Пример:\n"
                            "/log_workout бег 30")
    except ValueError:
        await message.reply("⚠️ Продолжительность тренировки должна быть числом. Пример:\n"
                            "/log_workout бег 30")


@router.message(Command('check_progress'))
async def check_progress_handler(message: Message):
    user_id = message.from_user.id
    if user_id not in user_profiles:
        await message.reply("Сначала настройте профиль с помощью команды /set_profile.")
        return

    water_consumed_ml, _, calories_consumed, calories_burned = check_progress(user_id)

    user_data = user_profiles[user_id]
    temperature = await get_temperature(user_id)
    water_goal_ml = calculate_water_goal(
        float(user_data["weight"]),
        int(user_data["activity"]),
        temperature,
    )

    water_consumed_l = water_consumed_ml / 1000.0
    water_goal_l = water_goal_ml / 1000.0
    water_remaining_l = max(0, water_goal_l - water_consumed_l)

    await message.reply(
        f"📊 Ваш прогресс:\n"
        f"💧 Вода:\n"
        f"    - Выпито: {water_consumed_l:.2f} л из {water_goal_l:.2f} л.\n"
        f"    - Осталось: {water_remaining_l:.2f} л.\n\n"
        f"🔥 Калории:\n"
        f"    - Потреблено: {calories_consumed:.0f} ккал.\n"
        f"    - Сожжено: {calories_burned:.0f} ккал.\n"
    )

    await send_progress_charts(message, water_consumed_l, water_remaining_l, calories_consumed, calories_burned, water_goal_l)













