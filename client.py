import os
import json
import argparse
import asyncio
import time
import logging
import traceback
from getpass import getpass
import httpx
import websockets
import uuid

# Импортируем наши модули
from websocket_handler import WebSocketHandler
from ollama_client import OllamaClient
from stream_handler import StreamHandler
from config import (
    logger, CONFIG_DIR, CONFIG_FILE, LOGS_DIR, LOG_FILE, 
    DEFAULT_HOST, DEFAULT_PORT, DEFAULT_PATH, RECONNECT_TIMEOUT, 
    DEFAULT_MODEL, DEFAULT_OLLAMA_HOST, DEFAULT_OLLAMA_PORT, DEFAULT_STREAM_MODE,
    setup_logging, set_console_log_level, debug_json_error
)

class OllamaProxyClient:
    """Главный класс приложения Ollama Proxy Client"""
    
    def __init__(self, port=5050, host='bober.app', path='auth-proxy', debug=False):
        """
        Инициализация основного клиента
        
        :param port: Порт WebSocket сервера
        :param host: Хост WebSocket сервера
        :param path: Путь WebSocket подключения
        :param debug: Режим отладки
        """
        # Устанавливаем базовые параметры
        self.port = port
        self.host = host
        self.path = path
        
        # Устанавливаем уровень логирования
        if debug:
            set_console_log_level(logging.DEBUG)
            logger.info("Включен режим отладки")
        
        # Загружаем настройки из конфигурационного файла
        self.config = self.load_config()
        
        # Инициализируем параметры из конфигурации или значений по умолчанию
        self.token = self.config.get('token', None)
        self.model = self.config.get('model', DEFAULT_MODEL)
        self.ollama_host = self.config.get('ollama_host', DEFAULT_OLLAMA_HOST)
        self.ollama_port = self.config.get('ollama_port', DEFAULT_OLLAMA_PORT)
        
        # Устанавливаем компоненты как None - будут инициализированы позже
        self.websocket_handler = None
        self.ollama_client = None
        self.stream_handler = None
        
        logger.info("Инициализирован клиент OllamaProxyClient")
        
    def load_config(self):
        """Загрузка конфигурации из файла"""
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_config(self):
        """Сохранение конфигурации в файл"""
        # Создаем директорию для конфигурации, если она не существует
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(self.config, f)
            
    def setup_components(self):
        """Инициализация компонентов приложения"""
        # Создаем обработчик WebSocket
        if not self.websocket_handler:
            self.websocket_handler = WebSocketHandler(
                port=self.port,
                token=self.token,
                message_processor=self.process_incoming_message
            )
            
        # Создаем клиент Ollama API
        if not self.ollama_client:
            self.ollama_client = OllamaClient(
                host=self.ollama_host,
                port=self.ollama_port,
                model=self.model
            )
            
        # Создаем обработчик потоковых данных
        if not self.stream_handler:
            self.stream_handler = StreamHandler(
                websocket_handler=self.websocket_handler
            )
    
    async def process_incoming_message(self, message):
        """
        Обработка входящего сообщения от сервера
        
        :param message: Полученное сообщение
        """
        try:
            # Проверяем тип сообщения
            if message["type"] == "buyer_message":
                # Обработка запроса от покупателя
                prompt = message["content"]
                message_id = message.get("messageId", -1)  # Получаем messageId из входящего сообщения
                stream = message.get("stream", False)  # Получаем параметр stream из входящего сообщения
                
                logger.info(f"Получен запрос от покупателя (messageId: {message_id}, stream: {stream}): {prompt}")
                print(f"Получен запрос от покупателя (messageId: {message_id}, stream: {stream}): {prompt[:50]}..." if len(prompt) > 50 else prompt)
                
                # Обрабатываем запрос в зависимости от режима
                logger.info(f"Начинаем обработку запроса в режиме {'потоковом' if stream else 'непотоковом'}")
                print(f"Режим обработки: {'потоковый' if stream else 'обычный'}")
                
                if stream:
                    # В потоковом режиме используем обработчик потоковых данных
                    logger.debug(f"Отправляем потоковый запрос в Ollama (messageId: {message_id})")
                    ollama_response = await self.ollama_client.prepare_stream_request(
                        prompt=prompt,
                        stream_handler=self.stream_handler,
                        message_id=message_id
                    )
                    logger.info(f"Ответ отправлен покупателю в потоковом режиме (messageId: {message_id})")
                    print(f"Ответ успешно отправлен в потоковом режиме (messageId: {message_id})")
                else:
                    # В непотоковом режиме получаем полный ответ и отправляем его
                    logger.debug(f"Отправляем обычный запрос в Ollama (messageId: {message_id})")
                    ollama_response = await self.ollama_client.generate(
                        prompt=prompt,
                        stream_mode=False,
                        message_id=message_id
                    )
                    
                    # Отправляем ответ обратно на сервер
                    logger.info(f"Отправляем ответ покупателю (messageId: {message_id}): {ollama_response[:100]}...")
                    await self.websocket_handler.send_response(ollama_response, message_id)
                    print(f"Ответ успешно отправлен (messageId: {message_id})")
            else:
                # Другие типы сообщений (например, system)
                logger.debug(f"Получено сообщение типа {message['type']}")
                
        except Exception as e:
            error_msg = f"Ошибка при обработке входящего сообщения: {str(e)}"
            logger.error(error_msg)
            print(f"❌ {error_msg}")
            # Выводим трассировку для отладки
            logger.debug(f"Трассировка ошибки:\n{traceback.format_exc()}")
    
    def setup_auth(self, force_token=None, force_model=None, force_ollama_host=None, force_ollama_port=None):
        """
        Настройка аутентификации и параметров
        
        :param force_token: Принудительно установить токен аутентификации
        :param force_model: Принудительно установить модель
        :param force_ollama_host: Принудительно установить хост Ollama API
        :param force_ollama_port: Принудительно установить порт Ollama API
        """
        config_updated = False
        
        # Настройка токена
        if force_token or 'token' not in self.config:
            if force_token:
                self.config['token'] = force_token
                logger.info("Токен аутентификации установлен принудительно")
            else:
                print("First-time setup:")
                self.config['token'] = getpass("Enter auth token: ")
                logger.info("Токен аутентификации получен от пользователя")
            config_updated = True
        
        # Настройка модели Ollama
        if force_model or 'model' not in self.config:
            if force_model:
                self.config['model'] = force_model
                logger.info(f"Модель Ollama установлена принудительно: {force_model}")
            else:
                default = DEFAULT_MODEL
                model_name = input(f"Введите название модели Ollama (по умолчанию: {default}): ")
                self.config['model'] = model_name if model_name.strip() else default
                logger.info(f"Модель Ollama установлена пользователем: {self.config['model']}")
            self.model = self.config['model']
            config_updated = True
            
        # Настройка хоста Ollama API
        if force_ollama_host or 'ollama_host' not in self.config:
            if force_ollama_host:
                self.config['ollama_host'] = force_ollama_host
                logger.info(f"Хост Ollama API установлен принудительно: {force_ollama_host}")
            else:
                default = DEFAULT_OLLAMA_HOST
                host = input(f"Введите хост Ollama API (по умолчанию: {default}): ")
                self.config['ollama_host'] = host if host.strip() else default
                logger.info(f"Хост Ollama API установлен пользователем: {self.config['ollama_host']}")
            self.ollama_host = self.config['ollama_host']
            config_updated = True
            
        # Настройка порта Ollama API
        if force_ollama_port or 'ollama_port' not in self.config:
            if force_ollama_port:
                self.config['ollama_port'] = force_ollama_port
                logger.info(f"Порт Ollama API установлен принудительно: {force_ollama_port}")
            else:
                default = DEFAULT_OLLAMA_PORT
                try:
                    port_str = input(f"Введите порт Ollama API (по умолчанию: {default}): ")
                    port = int(port_str) if port_str.strip() else default
                    self.config['ollama_port'] = port
                    logger.info(f"Порт Ollama API установлен пользователем: {self.config['ollama_port']}")
                except ValueError:
                    self.config['ollama_port'] = default
                    logger.warning(f"Введен некорректный порт, установлен порт по умолчанию: {default}")
                    print(f"Введен некорректный порт, установлен порт по умолчанию: {default}")
            self.ollama_port = self.config['ollama_port']
            config_updated = True
            
        # Сохраняем конфигурацию, если были изменения
        if config_updated:
            # Инициализируем компоненты с новыми настройками
            if hasattr(self, 'ollama_client') and self.ollama_client:
                # Если клиент уже существует, обновляем его параметры
                self.ollama_client.host = self.ollama_host
                self.ollama_client.port = self.ollama_port
                self.ollama_client.model = self.model
            
            # Выводим информацию о настройках
            logger.info(f"Настроено подключение к серверу: wss://bober.app:{self.port}/auth-proxy")
            logger.info(f"Настроено подключение к Ollama API: http://{self.ollama_host}:{self.ollama_port}/api/generate")
            
            print(f"Настроено подключение к серверу: wss://bober.app:{self.port}/auth-proxy")
            print(f"Используемая модель Ollama: {self.model}")
            print(f"Сервер Ollama API: http://{self.ollama_host}:{self.ollama_port}")
            
            self.save_config()
    
    def show_config(self):
        """Отображает текущую конфигурацию"""
        print("\nТекущая конфигурация:")
        print(f"Токен аутентификации: {'*' * 8}{self.token[-4:] if self.token else 'Не установлен'}")
        print(f"Модель Ollama: {self.model}")
        print(f"Сервер: wss://{self.host}:{self.port}/{self.path}")
        print(f"Сервер Ollama API: http://{self.ollama_host}:{self.ollama_port}")
        print()
            
    async def run(self):
        """Запуск клиента"""
        try:
            # Инициализируем компоненты
            self.setup_components()
            
            # Подключаемся к серверу
            logger.info("Попытка подключения к серверу...")
            print("Попытка подключения к серверу...")
            
            await self.websocket_handler.connect()
            logger.info("Успешно подключено к серверу WebSocket")
            print("Успешно подключено к серверу WebSocket")
            
            # Запускаем прослушивание сообщений
            await self.websocket_handler.listen()
                
        except websockets.InvalidURI as e:
            error_msg = f"Ошибка: Неверный формат URI для WebSocket: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            print("Пожалуйста, убедитесь, что URL начинается с ws:// или wss://")
            print("Используйте --reset-config для сброса настроек и повторной настройки")
            
        except ConnectionRefusedError as e:
            error_msg = f"Ошибка подключения: Не удалось подключиться к серверу: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            print(f"Проверьте, что сервер запущен и доступен")
            
        except Exception as e:
            error_msg = f"Ошибка: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            
        finally:
            # Корректное закрытие соединений
            try:
                if self.websocket_handler:
                    await self.websocket_handler.disconnect()
                if self.ollama_client:
                    await self.ollama_client.close()
            except Exception as e:
                logger.error(f"Ошибка при закрытии соединений: {str(e)}")

def main():
    """Основная функция запуска приложения"""
    parser = argparse.ArgumentParser(description='Ollama Proxy Client')
    parser.add_argument('--port', type=int, default=5050, help='Порт WebSocket сервера')
    parser.add_argument('--host', type=str, default='bober.app', help='Хост WebSocket сервера')
    parser.add_argument('--path', type=str, default='auth-proxy', help='Путь WebSocket подключения')
    parser.add_argument('--test', action='store_true', help='Включить расширенное логирование')
    parser.add_argument('--debug', action='store_true', help='Включить отладочные сообщения')
    parser.add_argument('--setup', action='store_true', help='Принудительно запустить настройку')
    parser.add_argument('--token', type=str, help='Токен аутентификации для WebSocket')
    parser.add_argument('--model', type=str, help='Модель Ollama для использования')
    parser.add_argument('--ollama-host', type=str, help='Хост Ollama API')
    parser.add_argument('--ollama-port', type=int, help='Порт Ollama API')
    parser.add_argument('--show-config', action='store_true', help='Показать текущую конфигурацию')
    
    args = parser.parse_args()
    
    # Инициализация клиента с параметрами из командной строки
    client = OllamaProxyClient(
        port=args.port,
        host=args.host,
        path=args.path,
        debug=args.test or args.debug  # Включаем отладку если указан --test или --debug
    )
    
    # Показать конфигурацию, если запрошено
    if args.show_config:
        client.show_config()
        return

    # Настройка аутентификации и параметров
    client.setup_auth(
        force_token=args.token if args.setup or args.token else None,
        force_model=args.model if args.setup or args.model else None,
        force_ollama_host=args.ollama_host if args.setup or args.ollama_host else None,
        force_ollama_port=args.ollama_port if args.setup or args.ollama_port else None
    )
    
    # Инициализация компонентов
    client.setup_components()
    
    # Запуск клиента
    try:
        asyncio.run(client.run())
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем (Ctrl+C)")
    finally:
        logger.info("Завершение работы приложения")
        # Закрываем все обработчики логов перед выходом
        logging.shutdown()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Программа остановлена пользователем")
        print("\nПрограмма остановлена пользователем")
    except Exception as e:
        logger.critical(f"Необработанная ошибка: {str(e)}")
        print(f"Критическая ошибка: {str(e)}")
    finally:
        # Очищаем все обработчики логов перед выходом
        for handler in logger.handlers[:]:
            handler.close()
            logger.removeHandler(handler)