import os
import logging

# Директории и файлы конфигурации
CONFIG_DIR = os.path.expanduser("~/.config/ollama_proxy")
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
LOGS_DIR = os.path.join(CONFIG_DIR, "logs")
LOG_FILE = os.path.join(LOGS_DIR, "client.log")

# Настройки WebSocket подключения
DEFAULT_HOST = "bober.app"
DEFAULT_PORT = 5050
DEFAULT_PATH = "/auth-proxy"

# Таймауты и настройки
RECONNECT_TIMEOUT = 5  # Таймаут для переподключения в секундах

# Настройки Ollama
DEFAULT_MODEL = "llama2"
DEFAULT_OLLAMA_HOST = "localhost"
DEFAULT_OLLAMA_PORT = 11434
DEFAULT_STREAM_MODE = True

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    os.makedirs(LOGS_DIR, exist_ok=True)
    
    # Настройка форматирования логов
    log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    
    # Создаем логгер
    logger = logging.getLogger("ollama_proxy")
    logger.setLevel(logging.DEBUG)
    
    # Обработчик для файла
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(log_format)
    file_handler.setLevel(logging.DEBUG)
    
    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_format)
    console_handler.setLevel(logging.INFO)
    
    # Добавляем обработчики к логгеру
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Создаем логгер
logger = setup_logging()

def set_console_log_level(level):
    """Изменение уровня логирования консольного вывода"""
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler) and not isinstance(handler, logging.FileHandler):
            handler.setLevel(level)
            logger.info(f"Уровень логирования консоли изменен на {logging.getLevelName(level)}")

def debug_json_error(text, error):
    """Функция для отладки ошибок при разборе JSON"""
    try:
        # Находим позицию ошибки
        line_no = error.lineno
        col_no = error.colno
        
        # Получаем строки из текста
        lines = text.split('\n')
        
        result = [f"Ошибка при разборе JSON: {str(error)}"]
        result.append("Подробности:")
        
        # Выводим строку с ошибкой и несколько строк до и после
        start_line = max(0, line_no - 2)
        end_line = min(len(lines), line_no + 2)
        
        for i in range(start_line, end_line):
            line_prefix = f"{i+1}: " if i+1 != line_no else f"{i+1}:>"
            result.append(f"{line_prefix} {lines[i]}")
            
            # Добавляем указатель на точное место ошибки
            if i+1 == line_no:
                pointer = " " * (len(line_prefix) + col_no) + "^"
                result.append(pointer)
        
        return "\n".join(result)
    except Exception as e:
        return f"Ошибка при анализе JSON: {str(error)}\nНе удалось предоставить подробности: {str(e)}" 