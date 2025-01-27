import discord
from discord.ext import commands
from discord.ext import tasks
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import asyncio
import time
import os
from datetime import datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
import requests
import threading
#from PIL import Image
#from io import BytesIO
import aiohttp
import re
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--no-sandbox')
options.add_argument('--headless')
options.add_argument('--disable-dev-shm-usage')

options.add_argument("start-maximized"); 
options.add_argument("disable-infobars"); 
options.add_argument("--disable-extensions"); 
options.add_argument("--disable-gpu"); 
options.add_argument("--disable-dev-shm-usage"); 

driver = webdriver.Chrome(options=options)

DISCORD_TOKEN = os.getenv("TOKEN")

ROBLOX_COOKIE = os.getenv("COOKIE")




# Функция для извлечения ID канала и сообщения из ссылки
def extract_ids_from_link(link):
    match = re.search(r'channels/(\d+)/(\d+)/(\d+)', link)
    if match:
        guild_id = int(match.group(1))
        channel_id = int(match.group(2))
        message_id = int(match.group(3))
        return channel_id, message_id
    return None, None


# Функция для получения user_ids из сообщения по ссылке
async def get_user_ids_from_message(link):
    channel_id, message_id = extract_ids_from_link(link)
    if not channel_id or not message_id:
        return []

    channel = bot.get_channel(channel_id)
    if not channel:
        return []

    message = await channel.fetch_message(message_id)
    # Преобразуем содержимое сообщения в список user_ids (ожидается, что они будут разделены запятыми)
    user_ids = [int(user_id.strip()) for user_id in message.content.split(',') if user_id.strip().isdigit()]
    return user_ids


def get_player_avatar(user_id):
    url = f'https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=150x150&format=Png&isCircular=false'
    response = requests.get(url)
    
    if response.status_code == 200:
        avatar_data = response.json().get('data', [])
        if avatar_data and 'imageUrl' in avatar_data[0]:
            image_url = avatar_data[0]['imageUrl']
            print(f"[DEBUG] Получена аватарка игрока {user_id}: {image_url}")
            return image_url
        else:
            print(f"[ERROR] Нет данных об аватарке для игрока {user_id}")
    else:
        print(f"[ERROR] Ошибка при получении аватарки игрока {user_id}. Статус: {response.status_code}")
    
    return None



# Функция для получения аватарок игроков по их токенам
def get_avatars_by_player_tokens(player_tokens):
    players_data = [
        {
            "token": token,
            "type": "AvatarHeadshot",
            "size": "150x150"
        }
        for token in player_tokens
    ]
    
    url = 'https://thumbnails.roblox.com/v1/batch'
    headers = {'User-agent': 'application/json'}
    response = requests.post(url, json=players_data, headers=headers)

    if response.status_code == 200:
        avatar_data = response.json().get('data', [])
        if avatar_data:
            #print(f"[DEBUG] Получено {len(avatar_data)} аватарок по токенам")
            return avatar_data
    else:
        print(f"[ERROR] Ошибка при получении аватарок по токенам. Статус: {response.status_code}")
    
    return None


def fetch_servers(place_id, cursor='', attempts=0, max_attempts=60):
    url = f'https://games.roblox.com/v1/games/{place_id}/servers/Public?limit=100&cursor={cursor}'
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Ошибка при получении серверов: {e}")
        if attempts < max_attempts:
            time.sleep(1)  # Пауза перед повторной попыткой
            return fetch_servers(place_id, cursor, attempts + 1)
        else:
            return None, None

    data = response.json()
    next_page_cursor = data.get('nextPageCursor')
    servers = data.get('data', [])
    return servers, next_page_cursor

# Функция для поиска игрока на сервере через сравнение аватарок с использованием токенов
# Функция для поиска игроков на серверах через сравнение аватарок
def find_players_on_servers(target_players_avatars, place_id=662417684):
    cursor = ''
    attempts = 0
    found_players = {}  # Словарь для хранения найденных игроков и их серверов

    while True:
        servers, cursor = fetch_servers(place_id, cursor, attempts)
        if not servers:
            #print("[DEBUG] Серверы не найдены или исчерпаны все попытки")
            break  # Если не удалось найти серверы или попытки закончились

        for server in servers:
            #print(f"[DEBUG] Обработка сервера с ID: {server['id']}")

            # Собираем токены игроков с сервера (из поля playerTokens)
            player_tokens = server.get('playerTokens', [])
            if not player_tokens:
                #print(f"[DEBUG] Нет токенов игроков на сервере {server['id']}")
                continue

            # Получаем аватарки игроков на сервере
            avatars = get_avatars_by_player_tokens(player_tokens)

            if avatars:
                for avatar in avatars:
                    for user_id, target_avatar_url in target_players_avatars.items():
                        # Сравниваем аватарки каждого игрока, который играет, с аватарками на сервере
                        if avatar['imageUrl'] == target_avatar_url:
                            #print(f"[SUCCESS] Найден игрок {user_id} на сервере {server['id']}")
                            found_players[user_id] = server['id']
            else:
                print(f"[ERROR] Ошибка при получении аватарок на сервере {server['id']}")

        attempts += 1
        if not cursor:  # Если нет следующей страницы
            #print("[DEBUG] Нет следующей страницы для серверов")
            break

    return found_players  # Возвращаем список найденных игроков и их серверов








# Функция для установки cookies в браузере
def set_roblox_cookie(driver):
    driver.get("https://www.roblox.com")
    time.sleep(4)
    driver.add_cookie({
        'name': '.ROBLOSECURITY',
        'value': os.getenv("COOKIE"),
        'domain': 'roblox.com',
        'path': '/'
    })
    print("Cookie установлены!")

time.sleep(6)
set_roblox_cookie(driver)

# Функция для получения информации о игроке
def get_player_info(driver, user_id):
    url = f'https://www.roblox.com/users/{user_id}/profile'
    
    try:
        # Устанавливаем тайм-аут загрузки страницы
        driver.set_page_load_timeout(60)
        driver.get(url)

        # Инициализируем переменные
        player_name = None
        player_status = 'offline'
        avatar_url = None

        wait = WebDriverWait(driver, 15)  # Максимальное ожидание в 15 секунд

        # Получаем имя игрока
        try:
            name_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1.profile-name.text-overflow'))
            )
            player_name = name_element.text.strip()  # Убираем лишние пробелы
        except TimeoutException:
            print(f"Не удалось найти имя игрока с ID {user_id}.")

        # Проверяем статус игрока
        try:
            status_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'a.avatar-status span'))
            )
            status_class = status_element.get_attribute('class')
            
            if 'icon-game' in status_class:
                player_status = 'playing'
                avatar_url = get_player_avatar(user_id)  # Предполагается, что эта функция существует
            elif 'icon-online' in status_class:
                player_status = 'online'
        except TimeoutException:
            print(f"Статус игрока с ID {user_id} не найден. Устанавливаю 'offline'.")

        return player_name, player_status, avatar_url

    except TimeoutException:
        print(f"Ошибка: превышен тайм-аут при загрузке страницы {url}.")
        return None, 'offline', None
    except Exception as e:
        print(f"Произошла ошибка при обработке игрока с ID {user_id}: {e}")
        return None, 'offline', None

def check_players_status(driver, user_ids):
    players_status = {}  # Теперь ключом будет user_id
    playing_players = {}  # Словарь для хранения ID игроков, которые играют и их аватарок
    found_players_message = ""  # Сообщение для найденных игроков

    for user_id in user_ids:
        player_name, player_status, avatar_url = get_player_info(driver, user_id)
        if player_name:
            players_status[user_id] = {
                'name': player_name,
                'status': player_status
            }
            if player_status == 'playing' and avatar_url:
                playing_players[user_id] = avatar_url
        else:
            print(f"Не удалось получить статус игрока с ID {user_id}.")

    # Если есть играющие игроки, запускаем единый поиск по серверам
    if playing_players:
        found_players = find_players_on_servers(playing_players)
        for user_id, server_id in found_players.items():
            if user_id in players_status:
                players_status[user_id]['status'] = f'playing lbb\n├server ID: `{server_id}`\n' + \
                                                    f'└https://www.roblox.com/games/start?placeId=16302670534&launchData=662417684/{server_id}'
                print(f'Игрок {players_status[user_id]["name"]} found on the server {server_id}')
                # Добавляем игрока в сообщение
                found_players_message += f'**{players_status[user_id]["name"]}** playing lbb on the server `{server_id}`\n'

    return players_status, found_players_message


def format_players_status(players_status):
    formatted_output = ""
    for player_info in players_status.values():
        if 'playing lbb' in player_info['status']:
            emoji = ":white_check_mark:"
        elif 'playing' in player_info['status']:
            emoji = ":green_square:"
        elif 'online' in player_info['status']:
            emoji = ":blue_square:"    
        else:
            emoji = ":red_square:"

        formatted_output += f'{emoji}{player_info["name"]}: {player_info["status"]}\n'

    return formatted_output.strip()  # Удалим лишние переводы строк в конце



# HTTP-сервер для обработки запросов
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Discord Bot is running!")

def run_server():
    server_address = ('0.0.0.0', int(os.environ.get("PORT", 10000)))
    httpd = HTTPServer(server_address, SimpleHTTPRequestHandler)
    httpd.serve_forever()

# Запускаем HTTP-сервер в отдельном потоке
server_thread = threading.Thread(target=run_server)
server_thread.start()


async def keep_alive():
    async with aiohttp.ClientSession() as session:
        while True:
            async with session.get('https://idad.onrender.com') as response:
                print(f"Keep-alive response status: {response.status}")
            await asyncio.sleep(60)  # Периодичность запросов (в секундах)

# Запускаем keep_alive в отдельном потоке
#keep_alive_task = asyncio.create_task(keep_alive())


# Создание экземпляра бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

firstStart = True
# Переменные для сохранения параметров
saved_message = None
saved_user_ids = None
saved_link = None
saved_author = None
saved_channelmsg = None

@bot.event
async def on_ready():
    print(f'{bot.user.name} запущен!')
    bot.loop.create_task(keep_alive())
    
    # Проверяем, сохранены ли параметры для перезапуска цикла
    if saved_message and saved_user_ids and saved_link and saved_author and saved_channelmsg:
        bot.loop.create_task(update_status_loop(saved_message, saved_user_ids, saved_link, saved_author, saved_channelmsg))


# Асинхронная функция для постоянного обновления статусов игроков
async def update_status_loop(message, user_ids, link, author, channelmsg):
    global saved_message, saved_user_ids, saved_link, saved_author, saved_channelmsg

    # Сохраняем параметры для возможного перезапуска
    saved_message = message
    saved_user_ids = user_ids
    saved_link = link
    saved_author = author
    saved_channelmsg = channelmsg
    
    while True:
        # Обновляем статусы игроков
        formatted_message, found_players_message = await asyncio.to_thread(check_players_status, driver, user_ids)

        players_status = format_players_status(formatted_message)
        response = players_status
        
        # Получаем текущее время в Unix timestamp
        current_timestamp = int(datetime.utcnow().timestamp())
        response += f"\nLast update time: <t:{current_timestamp}:R>\n"
        
        # Редактируем сообщение
        await message.edit(content=response)
        
        # Если найдены игроки, отправляем сообщение с упоминанием автора команды
        if found_players_message:
            channel_id = int(channelmsg)  # Преобразование строки в число
            channel = bot.get_channel(channel_id)
            
            if channel is not None:
                await channel.send(f"{author.mention}\n{found_players_message}")
            else:
                await message.channel.send(f"{author.mention}\n{found_players_message}")

        # Обновляем user_ids из сообщения
        user_ids = await get_user_ids_from_message(link)


@bot.command(name='check_status')
async def check_status(ctx, link: str, channelmsg: str):
    global firstStart, saved_message, saved_user_ids, saved_link, saved_author, saved_channelmsg

    if firstStart:
        # Получаем user_ids из указанного сообщения
        user_ids = await get_user_ids_from_message(link)
        if not user_ids:
            await ctx.send("Не удалось получить список пользователей из сообщения.")
            return

        await ctx.send('start')
        firstStart = False
        formatted_message, found_players_message = await asyncio.to_thread(check_players_status, driver, user_ids)

        players_status = format_players_status(formatted_message)
        response = players_status

        # Отправляем ответ в канал и сохраняем сообщение
        sent_message = await ctx.send(response)

        # Сохраняем параметры для перезапуска
        saved_message = sent_message
        saved_user_ids = user_ids
        saved_link = link
        saved_author = ctx.author
        saved_channelmsg = channelmsg

        # Запускаем цикл для обновления статусов
        await update_status_loop(sent_message, user_ids, link, ctx.author, channelmsg)


# Запуск бота
bot.run(DISCORD_TOKEN)

# Закрываем браузер после завершения программы
#driver.quit()
