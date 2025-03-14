import json
import httpx
import traceback
from config import logger, DEFAULT_MODEL, debug_json_error

class OllamaClient:
    """Класс для работы с Ollama API"""
    
    def __init__(self, host, port, model=DEFAULT_MODEL):
        """
        Инициализация клиента Ollama
        
        :param host: Хост API Ollama
        :param port: Порт API Ollama
        :param model: Модель по умолчанию
        """
        self.host = host
        self.port = port
        self.model = model
        self.client = httpx.AsyncClient()
        self.base_url = f"http://{self.host}:{self.port}/api"
    
    async def close(self):
        """Закрытие клиента"""
        if self.client:
            await self.client.aclose()
            logger.info("Соединение с Ollama API закрыто")
    
    def get_api_url(self, endpoint="generate"):
        """
        Получение URL API для запроса
        
        :param endpoint: API эндпоинт
        :return: Полный URL API
        """
        return f"{self.base_url}/{endpoint}"
    
    def prepare_request_data(self, prompt, stream_mode=False, model=None):
        """
        Подготовка данных для запроса к Ollama API
        
        :param prompt: Текст запроса
        :param stream_mode: Режим потоковой передачи
        :param model: Модель (если отличается от установленной по умолчанию)
        :return: Словарь с данными запроса
        """
        # Базовые параметры запроса
        request_data = {
            "model": model or self.model,
            "prompt": prompt,
            "stream": stream_mode,
            "raw": False,                   # Не используем raw-режим для обработки маркеров
            "keep_alive": "5m",             # Держим модель в памяти для быстрых ответов
            "keep_alive_timeout": 300       # Увеличиваем таймаут для загрузки модели
        }
        
        # Добавляем опции для улучшения генерации текста
        options = {
            # Основные параметры качества генерации
            "num_predict": 2048,           # Максимальное количество токенов для генерации
            "temperature": 0.7,            # Температура (креативность) генерации
            "top_k": 40,                   # Количество лучших токенов для выборки
            "top_p": 0.9,                  # Вероятность следующего токена (nucleus sampling)
            "repeat_penalty": 1.1,         # Штраф за повторения
            
            # Специальные токены для остановки генерации
            "stop": ["<end>", "<stop>"]
        }
        
        # Настройки для потокового режима
        if stream_mode:
            # Оптимизируем для быстрой потоковой передачи в режиме стриминга
            streaming_options = {
                "num_ctx": 4096,           # Максимальный размер контекста
                "num_gpu": 1,              # Использовать GPU для ускорения
                "tfs_z": 1.0,              # Параметр tail free sampling
                "seed": -1,                # Случайный seed для воспроизводимости
                "ignore_eos": False        # Не игнорировать токен конца последовательности
            }
            # Обновляем основные настройки
            options.update(streaming_options)
        
        # Добавляем опции в запрос
        request_data.update(options)
        
        return request_data
        
    async def generate(self, prompt, stream_mode=False, message_id=-1):
        """
        Запрос к Ollama API без потоковой передачи
        
        :param prompt: Текст запроса
        :param stream_mode: Режим потоковой передачи
        :param message_id: ID сообщения для отслеживания
        :return: Ответ от API или сообщение об ошибке
        """
        if stream_mode:
            logger.error("Для потоковой передачи используйте метод stream_generate")
            return "Ошибка: неверный метод для потоковой передачи"
            
        try:
            # Получаем URL и подготавливаем данные запроса
            ollama_url = self.get_api_url("generate")
            request_data = self.prepare_request_data(prompt, stream_mode=False)
            
            logger.info(f"Отправка запроса к Ollama API ({self.model}): {prompt[:100]}...")
            logger.debug(f"Параметры запроса: {json.dumps(request_data)}")
            
            # Отправляем запрос
            async with httpx.AsyncClient() as client:
                # Увеличиваем таймаут для длинных запросов
                response = await client.post(ollama_url, json=request_data, timeout=180.0)
                
                if response.status_code != 200:
                    error_msg = f"Ollama API вернул ошибку {response.status_code}: {response.text}"
                    logger.error(error_msg)
                    return f"Ошибка API: {response.status_code} - {response.text}"
                
                # Обрабатываем ответ
                try:
                    # Получаем текстовый ответ
                    text_response = response.text
                    logger.debug(f"Сырой ответ от Ollama API: {text_response}")
                    
                    # Пытаемся разобрать JSON
                    data = json.loads(text_response)
                    response_text = data.get("response", "")
                    
                    if not response_text:
                        error_msg = "Пустой ответ от Ollama API"
                        logger.error(error_msg)
                        return error_msg
                        
                    logger.info(f"Получен ответ от Ollama API, длина: {len(response_text)} символов")
                    
                    return response_text
                    
                except json.JSONDecodeError as e:
                    error_details = debug_json_error(text_response, e)
                    error_msg = f"Ошибка декодирования JSON в ответе Ollama: {e}\n{error_details}"
                    logger.error(error_msg)
                    return f"Ошибка обработки ответа: {error_details}"
                
        except httpx.TimeoutException:
            error_msg = "Время ожидания ответа от Ollama API истекло"
            logger.error(error_msg)
            return "Ошибка: таймаут при ожидании ответа от Ollama. Проверьте работу сервера и повторите запрос."
        
        except httpx.ConnectError:
            error_msg = f"Не удалось подключиться к Ollama API по адресу http://{self.host}:{self.port}"
            logger.error(error_msg)
            return f"Ошибка подключения к Ollama API. Убедитесь, что сервер Ollama запущен по адресу {self.host}:{self.port}."
        
        except Exception as e:
            error_msg = f"Неожиданная ошибка при обработке запроса к Ollama API: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Трассировка ошибки:\n{traceback.format_exc()}")
            return f"Произошла ошибка при обработке запроса: {str(e)}"
            
    async def prepare_stream_request(self, prompt, stream_handler, message_id=-1, test_mode=False):
        """
        Подготовка и отправка потокового запроса к Ollama API
        
        :param prompt: Текст запроса
        :param stream_handler: Обработчик потокового режима для обработки данных
        :param message_id: ID сообщения для отслеживания
        :param test_mode: Режим тестирования
        :return: Полный собранный ответ
        """
        try:
            # Получаем URL API и подготавливаем запрос для потокового режима
            ollama_url = self.get_api_url("generate")
            request_data = self.prepare_request_data(prompt, stream_mode=True)
            
            logger.info(f"Отправка потокового запроса к Ollama API ({self.model}): {prompt[:100]}...")
            logger.debug(f"Параметры запроса: {json.dumps(request_data)}")
            
            # Вызываем обработчик потокового режима
            return await stream_handler.process_stream(
                ollama_url=ollama_url,
                request_data=request_data,
                message_id=message_id,
                test_mode=test_mode
            )
            
        except Exception as e:
            error_msg = f"Ошибка при подготовке потокового запроса: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Трассировка ошибки:\n{traceback.format_exc()}")
            return f"Ошибка подготовки потокового запроса: {str(e)}" 