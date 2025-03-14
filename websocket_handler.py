import json
import time
import asyncio
import websockets
from config import logger, DEFAULT_HOST, DEFAULT_PATH, RECONNECT_TIMEOUT

class WebSocketHandler:
    """Класс для работы с WebSocket соединениями"""
    
    def __init__(self, port, token, message_processor=None):
        """
        Инициализация обработчика WebSocket
        
        :param port: Порт для подключения
        :param token: Токен аутентификации
        :param message_processor: Функция для обработки входящих сообщений
        """
        self.port = port
        self.token = token
        self.websocket = None
        self.message_processor = message_processor
        self.is_connected = False
        
    async def connect(self):
        """Установка соединения с WebSocket"""
        # Формируем URL с учетом порта
        websocket_url = f"wss://{DEFAULT_HOST}:{self.port}{DEFAULT_PATH}?token={self.token}"
        logger.info(f"Подключение к: {websocket_url}")
        
        try:
            self.websocket = await websockets.connect(websocket_url)
            self.is_connected = True
            logger.info("Соединение установлено успешно")
            return True
        except ConnectionRefusedError as e:
            error_msg = f"Ошибка: Сервер отказал в подключении. Убедитесь, что сервер запущен на {DEFAULT_HOST}:{self.port}"
            logger.error(error_msg)
            print(error_msg)
            raise
        except Exception as e:
            error_msg = f"Ошибка при подключении: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            raise
    
    async def disconnect(self):
        """Закрытие соединения с WebSocket"""
        if self.websocket:
            await self.websocket.close()
            self.is_connected = False
            logger.info("Соединение WebSocket закрыто")
    
    async def send_response(self, content, message_id=-1):
        """
        Отправка ответа на сервер
        
        :param content: Содержимое ответа
        :param message_id: ID сообщения, на которое отвечаем
        """
        if not self.websocket:
            logger.error("Попытка отправить сообщение без установленного соединения")
            return False
            
        response_data = {
            "type": "from_owner",
            "content": content,
            "messageId": message_id,
            "timestamp": int(time.time() * 1000)
        }
        
        try:
            await self.websocket.send(json.dumps(response_data))
            logger.debug(f"Отправлено сообщение на сервер: {json.dumps(response_data)}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке сообщения: {e}")
            return False
    
    async def send_stream_chunk(self, text, message_id, is_final=False):
        """
        Отправка фрагмента потокового ответа на сервер
        
        :param text: Текст фрагмента
        :param message_id: ID сообщения
        :param is_final: Флаг завершения потока
        """
        # Проверяем, не пустой ли чанк
        if not text or not text.strip():
            return
            
        try:
            # Используем тот же формат, что и для обычных сообщений
            response_data = {
                "type": "from_owner",
                "content": text,
                "messageId": message_id,
                "timestamp": int(time.time() * 1000)
            }
            
            await self.websocket.send(json.dumps(response_data))
            logger.debug(f"Отправлен чанк длиной {len(text)} символов на сервер")
            return True
        except Exception as e:
            logger.error(f"Ошибка при отправке потокового чанка: {e}")
            return False
    
    async def listen(self):
        """Прослушивание сообщений от сервера"""
        reconnect_attempts = 0
        
        while True:
            try:
                if not self.websocket:
                    await self.connect()
                
                message = await self.websocket.recv()
                reconnect_attempts = 0  # Сбрасываем счетчик при успешном получении сообщения
                
                logger.debug(f"Получено сообщение от сервера: {message}")
                data = json.loads(message)
                
                # Если есть обработчик сообщений, передаем сообщение ему
                if self.message_processor and callable(self.message_processor):
                    await self.message_processor(data)
                else:
                    logger.debug(f"Получено сообщение без обработчика: {data['type']}")
                
            except websockets.ConnectionClosed:
                self.is_connected = False
                reconnect_attempts += 1
                backoff_time = min(RECONNECT_TIMEOUT * reconnect_attempts, 60)  # Максимальная задержка 60 секунд
                
                logger.warning(f"Соединение закрыто. Попытка переподключения через {backoff_time} секунд (попытка {reconnect_attempts})...")
                print(f"Соединение закрыто. Попытка переподключения через {backoff_time} секунд...")
                
                await asyncio.sleep(backoff_time)  # Ждем перед повторным подключением
                
                try:
                    await self.connect()
                    logger.info("Успешно переподключились к серверу")
                except Exception as e:
                    logger.error(f"Не удалось переподключиться: {str(e)}")
                    
            except json.JSONDecodeError as e:
                logger.error(f"Ошибка при разборе JSON: {str(e)}, сообщение: {message}")
                
            except Exception as e:
                logger.error(f"Ошибка в цикле прослушивания: {str(e)}")
                
    async def listen_with_test_output(self):
        """Прослушивание сообщений от сервера с выводом для тестового режима"""
        reconnect_attempts = 0
        
        while True:
            try:
                if not self.websocket:
                    await self.connect()
                    
                message = await self.websocket.recv()
                reconnect_attempts = 0  # Сбрасываем счетчик при успешном получении сообщения
                
                logger.debug(f"Получено сообщение от сервера: {message}")
                data = json.loads(message)
                
                # Выводим сообщение на экран для наглядности
                print(f"\n>>> Получено сообщение от сервера: {data['type']}")
                if data["type"] == "buyer_message":
                    print(f">>> Запрос от покупателя: {data['content']}")
                    
                    # Если есть обработчик сообщений, передаем сообщение ему
                    if self.message_processor and callable(self.message_processor):
                        await self.message_processor(data)
                    else:
                        print(">>> Запрос будет обработан в основном цикле тестового режима")
                
            except websockets.ConnectionClosed:
                self.is_connected = False
                reconnect_attempts += 1
                backoff_time = min(RECONNECT_TIMEOUT * reconnect_attempts, 60)
                
                print(f"\n>>> Соединение закрыто. Попытка переподключения через {backoff_time} секунд...")
                logger.warning(f"Соединение закрыто в тестовом режиме. Попытка переподключения через {backoff_time} секунд...")
                
                await asyncio.sleep(backoff_time)
                
                try:
                    await self.connect()
                    print(">>> Успешно переподключились к серверу")
                    logger.info("Успешно переподключились к серверу в тестовом режиме")
                except Exception as e:
                    logger.error(f"Не удалось переподключиться в тестовом режиме: {str(e)}")
                    print(f">>> Ошибка при переподключении: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Ошибка при прослушивании сообщений в тестовом режиме: {str(e)}")
                print(f">>> Ошибка при прослушивании сообщений: {str(e)}") 