import json
import time
import httpx
import traceback
from config import logger

class StreamHandler:
    """Класс для обработки потоковых запросов к Ollama API"""
    
    def __init__(self, websocket_handler):
        """
        Инициализация обработчика потокового режима
        
        :param websocket_handler: Объект WebSocketHandler для отправки потоковых данных
        """
        self.websocket_handler = websocket_handler
        
    async def process_stream(self, ollama_url, request_data, message_id=-1, test_mode=False):
        """
        Обработка запроса к Ollama API в потоковом режиме с мгновенной передачей данных
        
        :param ollama_url: URL API Ollama
        :param request_data: Данные запроса
        :param message_id: ID сообщения для отслеживания
        :param test_mode: Флаг тестового режима
        :return: Полный собранный ответ
        """
        try:
            full_response = ""
            async with httpx.AsyncClient() as client:
                # Увеличиваем таймаут для длинных запросов
                async with client.stream("POST", ollama_url, json=request_data, timeout=180.0) as response:
                    # Проверяем статус ответа
                    if response.status_code != 200:
                        text_response = await response.text()
                        error_msg = f"Ollama API вернул код ошибки: {response.status_code}, ответ: {text_response}"
                        logger.error(error_msg)
                        return f"Ошибка API Ollama: {response.status_code} - {text_response}"
                    
                    # Информируем о начале получения потоковых данных
                    logger.debug("Начато получение потоковых данных от Ollama API с мгновенной передачей")
                    in_test_mode = test_mode and message_id == -1
                    
                    # Счетчики для статистики
                    raw_chunks = 0
                    json_chunks = 0
                    text_chunks = 0
                    bytes_received = 0
                    start_time = time.time()
                    
                    # Визуальный индикатор в тестовом режиме
                    if in_test_mode:
                        print("\n[", end="", flush=True)
                    
                    # ОПТИМИЗАЦИЯ: Используем прямой доступ к сырым данным для максимальной скорости
                    async for raw_chunk in response.aiter_raw():
                        if not raw_chunk:
                            continue
                            
                        raw_chunks += 1
                        bytes_received += len(raw_chunk)
                        
                        try:
                            # Сразу декодируем текст из байтов
                            chunk_text = raw_chunk.decode('utf-8')
                            
                            # Обрабатываем каждую строку отдельно
                            for line in chunk_text.splitlines():
                                if not line.strip():
                                    continue
                                    
                                # Пытаемся распарсить JSON
                                try:
                                    data = json.loads(line)
                                    json_chunks += 1
                                    
                                    # Извлекаем текст из ответа
                                    if "response" in data:
                                        response_text = data["response"]
                                        
                                        # Фильтруем специальные токены
                                        if response_text in ["<think>", "</think>"]:
                                            continue
                                            
                                        # Добавляем в полный ответ
                                        full_response += response_text
                                        
                                        # Обрабатываем только непустой текст
                                        if response_text.strip():
                                            text_chunks += 1
                                            
                                            # НЕМЕДЛЕННАЯ ОТПРАВКА: Ключевой момент для ускорения
                                            await self.websocket_handler.send_stream_chunk(response_text, message_id)
                                            
                                            # Визуализация в тестовом режиме
                                            if in_test_mode:
                                                print(response_text, end="", flush=True)
                                                # Обновляем индикатор прогресса
                                                if raw_chunks % 5 == 0:
                                                    print(".", end="", flush=True)
                                                    
                                except json.JSONDecodeError:
                                    # Если не JSON, но имеет текст, отправляем как есть
                                    if line.strip():
                                        logger.debug(f"Отправка не-JSON строки: {line[:30]}...")
                                        await self.websocket_handler.send_stream_chunk(line, message_id)
                                        if in_test_mode:
                                            print(line, end="", flush=True)
                        
                        except UnicodeDecodeError as e:
                            logger.error(f"Ошибка декодирования UTF-8: {e}")
                    
                    # Финальная статистика
                    elapsed_time = time.time() - start_time
                    logger.info(f"Поток завершен за {elapsed_time:.2f} сек. Получено {bytes_received} байт в {raw_chunks} сырых чанках")
                    logger.info(f"Обработано {json_chunks} JSON-объектов, отправлено {text_chunks} текстовых фрагментов")
                    
                    # Финальная отметка в тестовом режиме
                    if in_test_mode:
                        print("]")
                        print(f"\n✅ Потоковая передача завершена ({text_chunks} фрагментов за {elapsed_time:.2f} сек)")
                    
                    # Отправляем сигнал о завершении потока
                    await self.websocket_handler.send_stream_chunk("\n\n[Генерация завершена]", message_id, is_final=True)
                    
            return full_response
            
        except httpx.TimeoutException:
            error_msg = "Таймаут при ожидании ответа от Ollama API в потоковом режиме"
            logger.error(error_msg)
            return "Ошибка: время ожидания ответа от Ollama истекло. Возможно, запрос слишком сложный или модель недоступна."
            
        except httpx.ConnectError:
            error_msg = "Не удалось подключиться к Ollama API"
            logger.error(error_msg)
            return "Ошибка подключения к Ollama. Убедитесь, что Ollama запущена и доступна."
            
        except Exception as e:
            error_msg = f"Ошибка при обработке потокового ответа от Ollama API: {str(e)}"
            logger.error(error_msg)
            logger.debug(f"Трассировка ошибки:\n{traceback.format_exc()}")
            return f"Ошибка обработки потокового ответа: {str(e)}" 