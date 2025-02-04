import aiohttp
from users import user_profiles
from config import API_KEY
from aiogram import types
import matplotlib.pyplot as plt
import os


async def get_temperature(user_id):
    user_data = user_profiles.get(user_id)
    if not user_data or 'city' not in user_data:
        raise ValueError("Город пользователя не найден или не настроен.")

    city = user_data['city']

    url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric"

    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            data = await response.json()
            if response.status == 200:
                return data['main']['temp']
            else:
                raise ValueError("Не удалось получить температуру: " + data.get("message", "Unknown error"))


def calculate_water_goal(weight, activity, temperature):
    water_base = weight * 30
    water_activity = (activity // 30) * 500
    water_temperature = 500 if temperature > 25 else 0

    return water_base + water_activity + water_temperature


def calculate_calorie_goal(weight, height, age, activity_level):
    # Удостоверяемся, что уровень активности находится в допустимом диапазоне
    if activity_level < 1.2:
        activity_level = 1.2
    if activity_level > 2.0:
        activity_level = 2.0

    calorie_base = 10 * weight + 6.25 * height - 5 * age
    calorie_activity = calorie_base * activity_level

    return calorie_activity


async def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                data = await response.json()
                products = data.get('products', [])
                if products:
                    first_product = products[0]
                    return {
                        'name': first_product.get('product_name', 'Неизвестно'),
                        'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
                    }
    except aiohttp.ClientError:
        print("Ошибка при запросе данных о продукте.")
    return None


def log_workout(user_id, workout_type, duration):
    # Расход калорий на разные виды тренировок (ккал/мин)
    workout_calories = {
        'бег': 10,
        'ходьба': 2,
        'катание на велосипеде': 9,
        'плавание': 12,
        'теннис': 12,
        'йога': 4,
    }

    workout_water = {
        'бег': 0.3,
        'ходьба': 0.2,
        'катание на велосипеде': 0.25,
        'плавание': 0.35,
        'теннис': 0.35,
        'йога': 0.15
    }

    calories_burned = workout_calories.get(workout_type, 6) * duration  # По умолчанию 6 ккал/мин
    water_additional = (duration / 30) * workout_water.get(workout_type, 0.2)  # По умолчанию 200 мл за 30 минут


    if 'calories_burned' not in user_profiles[user_id]:
        user_profiles[user_id]['calories_burned'] = 0
    user_profiles[user_id]['calories_burned'] += calories_burned


    if 'water_consumed' not in user_profiles[user_id]:
        user_profiles[user_id]['water_consumed'] = 0
    user_profiles[user_id]['water_consumed'] += water_additional

    return calories_burned, water_additional




def check_progress(user_id):
    user_data = user_profiles[user_id]
    water_consumed = user_data['water_intake']
    calories_consumed = user_data.get('calories_consumed', 0)
    calories_burned = user_data.get('calories_burned', 0)
    return water_consumed, 0, calories_consumed, calories_burned


async def send_progress_charts(message: types.Message, water_consumed, water_remaining, calories_consumed,
                               calories_burned, water_goal):
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5))


    water_labels = ['Выпито', 'Осталось']
    water_values = [water_consumed, water_remaining]
    ax1.pie(water_values, labels=water_labels, autopct='%1.1f%%', startangle=90)
    ax1.set_title('Потребление воды')


    calorie_labels = ['Потреблено', 'Сожжено']
    calorie_values = [calories_consumed, -calories_burned]
    ax2.bar(calorie_labels, calorie_values, color=['blue', 'red'])
    ax2.set_title('Потребление и сжигание калорий')
    ax2.set_ylabel('ккал')


    plt.tight_layout()


    file_path = 'progress_chart.png'


    plt.savefig(file_path)


    with open(file_path, 'rb') as photo:
        await message.answer_photo(photo=types.InputFile(photo, filename=file_path))


    plt.close(fig)


    os.remove(file_path)









