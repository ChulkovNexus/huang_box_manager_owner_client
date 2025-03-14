#!/bin/bash

# Путь к виртуальному окружению (если используется)
VENV_PATH=".venv"

# Проверка наличия виртуального окружения
if [ -d "$VENV_PATH" ]; then
    echo "Активация виртуального окружения..."
    source "$VENV_PATH/bin/activate"
fi

# Установка зависимостей (если требуется)
if [ -f "requirements.txt" ]; then
    echo "Проверка зависимостей..."
    pip install -r requirements.txt >/dev/null 2>&1
fi

# Запуск основного скрипта с передачей всех аргументов
echo "Запуск Ollama Proxy Client..."
python client.py "$@"

# Если был активирован venv, деактивируем его
if [ -d "$VENV_PATH" ]; then
    deactivate >/dev/null 2>&1
fi