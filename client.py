import os
import json
import argparse
import websockets
import asyncio
import time
from getpass import getpass
import httpx

CONFIG_DIR = os.path.expanduser("~/.config/ollama_proxy")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
# Захардкоженный базовый URL для WebSocket подключения
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 5050
DEFAULT_PATH = "/auth-proxy"

class OllamaProxyClient:
    def __init__(self, port=DEFAULT_PORT):
        self.config = self.load_config()
        self.websocket = None
        self.ollama_client = httpx.AsyncClient()
        self.port = port

    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_config(self):
        """Сохранение конфигурации в файл"""
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)

    async def connect_websocket(self):
        """Установка соединения с WebSocket"""
        # Формируем URL с учетом порта
        websocket_url = f"ws://{DEFAULT_HOST}:{self.port}{DEFAULT_PATH}?token={self.config['token']}"
        print(f"Подключение к: {websocket_url}")
        try:
            self.websocket = await websockets.connect(websocket_url)
            print("Соединение установлено успешно")
        except ConnectionRefusedError as e:
            print(f"Ошибка: Сервер отказал в подключении. Убедитесь, что сервер запущен на {DEFAULT_HOST}:{self.port}")
            raise
        except Exception as e:
            print(f"Ошибка при подключении: {str(e)}")
            raise

    async def send_response_to_server(self, content):
        """Отправка ответа на сервер"""
        response_data = {
            "type": "from_owner",
            "content": content,
            "timestamp": int(time.time() * 1000)
        }
        await self.websocket.send(json.dumps(response_data))

    async def process_ollama_request(self, prompt):
        """Отправка запроса к Ollama API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:11434/api/generate",
                json={"model": "llama2", "prompt": prompt}
            )
            return response.json()["response"]

    async def main_loop(self):
        """Основной цикл обработки сообщений"""
        while True:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                
                if data["type"] == "from_buyer":
                    # Обработка запроса от покупателя
                    prompt = data["content"]
                    
                    # Получаем ответ от Ollama
                    ollama_response = await self.process_ollama_request(prompt)
                    
                    # Отправляем ответ обратно на сервер
                    await self.send_response_to_server(ollama_response)
                
                # Игнорируем остальные типы сообщений
                
            except websockets.exceptions.ConnectionClosed:
                print("Connection closed. Attempting to reconnect...")
                await self.connect_websocket()
            except Exception as e:
                print(f"Error in main loop: {str(e)}")

    def setup_auth(self, force_token=None):
        """Настройка аутентификации"""
        if force_token or 'token' not in self.config:
            if force_token:
                self.config['token'] = force_token
            else:
                print("First-time setup:")
                self.config['token'] = getpass("Enter auth token: ")
            
            # Больше не запрашиваем URL сервера, используем константу
            print(f"Настроено подключение к: ws://{DEFAULT_HOST}:{self.port}{DEFAULT_PATH}")
            self.save_config()

async def main():
    parser = argparse.ArgumentParser(description="Ollama Proxy Client")
    parser.add_argument('--reset-config', action='store_true', help="Reset configuration")
    parser.add_argument('--force-token', type=str, help="Force set new authentication token")
    parser.add_argument('--port', type=int, default=DEFAULT_PORT, help=f"Server port (default: {DEFAULT_PORT})")
    args = parser.parse_args()

    if args.reset_config and os.path.exists(CONFIG_FILE):
        os.remove(CONFIG_FILE)
        print("Configuration reset successfully")

    client = OllamaProxyClient(port=args.port)
    client.setup_auth(args.force_token)

    try:
        print("Попытка подключения к серверу...")
        await client.connect_websocket()
        print("Успешно подключено к серверу WebSocket")
        await client.main_loop()
    except websockets.exceptions.InvalidURI as e:
        print(f"Ошибка: Неверный формат URI для WebSocket: {str(e)}")
        print("Пожалуйста, убедитесь, что URL начинается с ws:// или wss://")
        print("Используйте --reset-config для сброса настроек и повторной настройки")
    except ConnectionRefusedError as e:
        print(f"Ошибка подключения: Не удалось подключиться к серверу: {str(e)}")
        print(f"Проверьте, что сервер запущен и доступен по адресу {DEFAULT_HOST}:{args.port}")
    except Exception as e:
        print(f"Ошибка: {str(e)}")
    finally:
        if client.websocket:
            await client.websocket.close()

if __name__ == "__main__":
    asyncio.run(main())