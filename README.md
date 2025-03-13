# Ollama Proxy Client

Клиент для подключения к серверу Ollama Proxy и обработки запросов от покупателей.

## Установка

1. Клонируйте репозиторий:
```bash
git clone <url-репозитория>
cd huang_box_manager_owner_client
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

## Использование

### Первый запуск

При первом запуске вам будет предложено ввести только токен аутентификации:

```bash
python client.py
```

### Сброс конфигурации

Если вам нужно сбросить настройки и заново ввести токен:

```bash
python client.py --reset-config
```

### Принудительная установка токена

Вы можете принудительно установить новый токен аутентификации:

```bash
python client.py --force-token ваш_новый_токен
```

### Указание другого порта

По умолчанию клиент подключается к серверу на порту 5050, но вы можете указать другой порт:

```bash
python client.py --port 8080
```

## Устранение неполадок

### Проблемы с подключением

1. Убедитесь, что сервер запущен и доступен по адресу `localhost:5050` (или на порту, который вы указали)
2. Убедитесь, что токен аутентификации верный

### Сброс настроек

Если у вас возникли проблемы с конфигурацией, вы можете сбросить настройки:

```bash
python client.py --reset-config
```

## Примечание

Клиент настроен на подключение к серверу по адресу `ws://localhost:5050/auth-proxy`. Хост (`localhost`) и путь (`/auth-proxy`) захардкожены в коде, но порт можно изменить через параметр командной строки `--port`.

## Требования

- Python 3.7+
- websockets
- httpx 