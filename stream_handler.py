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
        
    async def process_stream(self, ollama_url, request_data, message_id=-1):
        """
        Обработка потокового запроса к Ollama API
        
        :param ollama_url: URL для запроса к Ollama API
        :param request_data: Данные запроса
        :param message_id: ID сообщения для отслеживания
        :return: Полный ответ от Ollama API
        """
        try:
            start_time = time.time()
            full_response = ""
            bytes_received = 0
            raw_chunks = 0
            json_chunks = 0
            text_chunks = 0
            
            logger.info(f"Начало потоковой передачи (messageId: {message_id})")
            print(f"Начало потоковой передачи (messageId: {message_id})")
            
            async with httpx.AsyncClient() as client:
                async with client.stream('POST', ollama_url, json=request_data, timeout=30.0) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.strip():
                            bytes_received += len(line.encode('utf-8'))
                            raw_chunks += 1
                            
                            try:
                                data = json.loads(line)
                                json_chunks += 1
                                
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
                                        
                                        # Отправляем чанк через WebSocket
                                        await self.websocket_handler.send_stream_chunk(response_text, message_id)
                                        
                                        # Логируем каждый чанк
                                        logger.debug(f"Отправлен чанк (messageId: {message_id}): {response_text[:50]}...")
                                        
                            except json.JSONDecodeError:
                                # Если не JSON, но имеет текст, отправляем как есть
                                if line.strip():
                                    logger.debug(f"Отправка не-JSON строки: {line[:30]}...")
                                    await self.websocket_handler.send_stream_chunk(line, message_id)
                    
            # Финальная статистика
            elapsed_time = time.time() - start_time
            logger.info(f"Поток завершен за {elapsed_time:.2f} сек. Получено {bytes_received} байт в {raw_chunks} сырых чанках")
            logger.info(f"Обработано {json_chunks} JSON-объектов, отправлено {text_chunks} текстовых фрагментов")
            print(f"\n✅ Потоковая передача завершена ({text_chunks} фрагментов за {elapsed_time:.2f} сек)")
            
            # Отправляем сигнал о завершении потока
            await self.websocket_handler.send_stream_chunk("\n\n[Генерация завершена]", message_id, is_final=True)
            
            # Отправляем сообщение о завершении потока
            finished_data = {
                "type": "finished_message_stream",
                "content": "",
                "messageId": message_id,
                "timestamp": int(time.time() * 1000)
            }
            await self.websocket_handler.websocket.send(json.dumps(finished_data))
            logger.info(f"Отправлено сообщение о завершении потока (messageId: {message_id})")
            
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