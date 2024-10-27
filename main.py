import discord
from discord.ext import commands
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
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
    response = requests.get(url)

    if response.status_code != 200 or attempts >= max_attempts:
        #print(f"[ERROR] Ошибка при получении серверов. Попытка: {attempts}")
        return None, None  # Либо ошибка, либо превышено количество попыток

    data = response.json()
    next_page_cursor = data.get('nextPageCursor')
    servers = data.get('data', [])

    print(f"[DEBUG] Получено {len(servers)} серверов на попытке {attempts}. Следующий курсор: {next_page_cursor}")

    if not servers:  # Если серверов нет, делаем паузу и пытаемся снова
        time.sleep(1)
        return fetch_servers(place_id, cursor, attempts + 1)

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
    driver.get(url)
    time.sleep(5)

    try:
        name_element = driver.find_element(By.CSS_SELECTOR, 'h1.profile-name.text-overflow')
        player_name = name_element.text

        status_element = driver.find_element(By.CSS_SELECTOR, 'a.avatar-status span')
        status_class = status_element.get_attribute('class')

        if 'icon-game' in status_class:
            player_status = 'играет в игру'
            avatar_url = get_player_avatar(user_id)
            return player_name, player_status, avatar_url
        elif 'icon-online' in status_class:
            player_status = 'онлайн'
            return player_name, player_status, None
        else:
            player_status = 'не в сети'
            return player_name, player_status, None
    except Exception as e:
        print(f"Не удалось получить информацию о игроке с ID {user_id}:")
        return player_name, 'не в сети', None

def check_players_status(driver, user_ids):
    players_status = {}  # Теперь ключом будет user_id
    playing_players = {}  # Словарь для хранения ID игроков, которые играют и их аватарок

    for user_id in user_ids:
        player_name, player_status, avatar_url = get_player_info(driver, user_id)
        if player_name:
            players_status[user_id] = {
                'name': player_name,
                'status': player_status
            }
            if player_status == 'играет в игру' and avatar_url:
                playing_players[user_id] = avatar_url
        else:
            print(f"Не удалось получить статус игрока с ID {user_id}.")

    # Если есть играющие игроки, запускаем единый поиск по серверам
    if playing_players:
        found_players = find_players_on_servers(playing_players)
        for user_id, server_id in found_players.items():
            if user_id in players_status:
                players_status[user_id]['status'] = f'играет в lbb\n├ID сервера: {server_id}\n' + \
                                                    f'└https://www.roblox.com/games/start?placeId=16302670534&launchData=662417684/{server_id}'
                print(f'Игрок {players_status[user_id]["name"]} найден на сервере {server_id}')

    return players_status

def format_players_status(players_status):
    formatted_output = ""
    for player_info in players_status.values():
        if 'играет в lbb' in player_info['status']:
            emoji = ":white_check_mark:"
        elif 'играет в игру' in player_info['status']:
            emoji = ":green_square:"
        elif 'онлайн' in player_info['status']:
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
            async with session.get('http://0.0.0.0:10000') as response:
                print(f"Keep-alive response status: {response.status}")
            await asyncio.sleep(60)  # Периодичность запросов (в секундах)

# Запускаем keep_alive в отдельном потоке
#keep_alive_task = asyncio.create_task(keep_alive())


# Создание экземпляра бота
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'{bot.user.name} запущен!')
    bot.loop.create_task(keep_alive())



# Асинхронная функция для постоянного обновления статусов игроков
async def update_status_loop(message, user_ids):
    while True:
        # Обновляем статусы игроков
        formatted_message = await asyncio.to_thread(check_players_status, driver, user_ids)

        players_status = format_players_status(formatted_message)
        
    
        response = players_status
        current_datetime = datetime.now().time()
        response += f"\nвремя последнего обновления: {current_datetime}\n"
        # Редактируем сообщение
        await message.edit(content=response)

        # Ждем 60 секунд перед следующим обновлением
        #await asyncio.sleep(3)




firstStart = True

# Команда для проверки статуса игроков и запуска цикла обновления
@bot.command(name='check_status')
async def check_status(ctx):
    global firstStart
    if firstStart:
        user_ids = [1248106058, 3386355217, 1412644104, 2962499573, 248600459, 2860360977, 3444324397, 2282801779, 3866560929, 332963803, 870691959, 1387326452]  # Пример списка игроков
        await ctx.send('проверка запущена')
        firstStart = False
        formatted_message = await asyncio.to_thread(check_players_status, driver, user_ids)

        players_status = format_players_status(formatted_message)

        response = players_status

        # Отправляем ответ в канал и сохраняем сообщение
        sent_message = await ctx.send(response)

        # Запускаем цикл для обновления статусов
        await update_status_loop(sent_message, user_ids)

# Запуск бота
bot.run(DISCORD_TOKEN)

# Закрываем браузер после завершения программы
driver.quit()
