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

При первом запуске вам будет предложено ввести:
- Токен аутентификации для подключения к серверу
- Название модели Ollama для обработки запросов
- Хост и порт Ollama API
- Режим потоковой передачи (stream) для Ollama API

```bash
python client.py
```

### Просмотр текущей конфигурации

Вы можете просмотреть текущую конфигурацию клиента без подключения к серверу:

```bash
python client.py --show-config
```

### Сброс конфигурации

Если вам нужно сбросить настройки и заново ввести все параметры:

```bash
python client.py --reset-config
```

### Принудительная установка токена

Вы можете принудительно установить новый токен аутентификации:

```bash
python client.py --force-token ваш_новый_токен
```

### Указание модели Ollama

Вы можете указать какую модель Ollama использовать (по умолчанию: llama2):

```bash
python client.py --force-model mistral
```

### Настройка подключения к Ollama API

Вы можете указать хост и порт Ollama API (по умолчанию: localhost:11434):

```bash
python client.py --ollama-host 192.168.1.100 --ollama-port 11434
```

### Настройка режима потоковой передачи

Вы можете включить или выключить потоковый режим (stream) для Ollama API:

```bash
# Включить потоковый режим
python client.py --stream

# Выключить потоковый режим
python client.py --no-stream
```

В потоковом режиме:
- Клиент обрабатывает каждый фрагмент ответа от Ollama API по мере его получения
- Частичные ответы немедленно отправляются на сервер с исходным messageId
- Пользователь видит ответ в режиме реального времени

В непотоковом режиме:
- Клиент ожидает полного ответа от Ollama API
- Отправляет полный ответ на сервер только после завершения генерации
- Подходит для случаев, когда важна целостность ответа

### Указание другого порта для сервера

По умолчанию клиент подключается к серверу на порту 5050, но вы можете указать другой порт:

```bash
python client.py --port 8080
```

### Тестовый режим

Тестовый режим позволяет вводить запросы к Ollama с клавиатуры и видеть ответы непосредственно в консоли. При этом все запросы и ответы также отправляются на сервер, как при обычной работе:

```bash
python client.py --test
```

В тестовом режиме:
- Все отладочные сообщения (уровня DEBUG) выводятся в консоль
- Отображается подробная информация о запросах к Ollama API
- Показывается информация о потоковом режиме
- Показывается время выполнения запроса
- Выводится полный ответ от Ollama
- При ошибках показывается детальная отладочная информация
- При отправке ответов на сервер используется messageId = -1

### Режим отладки

Вы можете включить вывод отладочных сообщений в консоль в любом режиме работы:

```bash
python client.py --debug
```

### Комбинирование параметров

Вы можете комбинировать различные параметры, например:

```bash
python client.py --test --force-model mistral
python client.py --debug --port 8080 --ollama-host 192.168.1.100
python client.py --stream --test
python client.py --no-stream --debug
```

В тестовом режиме вы можете:
- Вводить запросы к Ollama и получать ответы в консоли
- Видеть сообщения, приходящие от сервера
- Видеть все отладочные сообщения в консоли
- Видеть подробную информацию об ошибках в формате ответов Ollama API
- Выйти из режима, введя 'exit' или нажав Ctrl+C

## Функциональность

### Обработка messageId

Клиент поддерживает обработку идентификаторов сообщений (messageId):
- При получении запроса от сервера, клиент извлекает messageId
- В потоковом режиме частичные ответы отправляются с тем же messageId
- В непотоковом режиме полный ответ отправляется с тем же messageId
- В тестовом режиме, когда запросы вводятся пользователем, используется messageId = -1

### Режимы работы с Ollama API

Клиент поддерживает два режима работы с Ollama API:

#### Потоковый режим (по умолчанию)
- Позволяет получать и отправлять ответы по мере их генерации
- Обеспечивает более быстрый первый отклик
- Подходит для интерактивных диалогов, где важна скорость реакции

#### Непотоковый режим
- Ожидает завершения генерации ответа перед отправкой на сервер
- Обеспечивает целостность ответа
- Подходит для случаев, когда важна точность и полнота ответа

Режим можно указать при запуске с помощью параметров `--stream` и `--no-stream`.

### Автоматическое переподключение

Клиент автоматически пытается переподключиться к серверу в случае разрыва соединения. При этом используется экспоненциальная задержка между попытками:
- Первая попытка: через 5 секунд
- Вторая попытка: через 10 секунд
- Третья попытка: через 15 секунд
- ...и так далее, до максимальной задержки в 60 секунд

### Логирование

Клиент ведет подробный журнал всех действий и сообщений:
- Все сообщения логируются в файл `~/.config/ollama_proxy/logs/client.log`
- По умолчанию в консоль выводятся только сообщения уровня INFO и выше
- В тестовом режиме или с параметром `--debug` в консоль выводятся все сообщения, включая DEBUG

### Обработка ошибок

Клиент тщательно обрабатывает ошибки, в том числе:
- Ошибки подключения к WebSocket серверу
- Ошибки подключения к Ollama API
- Ошибки формата JSON в ответах от Ollama
- Ошибки при обработке потоковых данных от Ollama API
- Таймауты при запросах к Ollama API

При возникновении ошибок в тестовом режиме выводится подробная диагностическая информация.

## Конфигурация

Клиент хранит конфигурацию в файле `~/.config/ollama_proxy/config.json`, который содержит следующие параметры:
- `token` - токен аутентификации для подключения к серверу
- `model` - название модели Ollama, используемой для обработки запросов
- `ollama_host` - хост, на котором запущено Ollama API (по умолчанию: localhost)
- `ollama_port` - порт, на котором доступно Ollama API (по умолчанию: 11434)
- `stream_mode` - режим потоковой передачи для Ollama API (по умолчанию: true)

Для просмотра текущей конфигурации используйте команду:
```bash
python client.py --show-config
```

## Устранение неполадок

### Проблемы с подключением к серверу

1. Убедитесь, что сервер запущен и доступен по адресу `bober.app:5050` (или на порту, который вы указали)
2. Убедитесь, что токен аутентификации верный
3. Используйте параметр `--debug` для получения подробной отладочной информации
4. Проверьте журнал для получения подробной информации об ошибках: `~/.config/ollama_proxy/logs/client.log`

### Проблемы с подключением к Ollama API

1. Убедитесь, что Ollama запущена и доступна по указанному адресу (по умолчанию: http://localhost:11434)
2. Проверьте, что порт Ollama API не заблокирован брандмауэром
3. Если Ollama запущена на другом компьютере, укажите правильный хост с помощью параметра `--ollama-host`
4. Используйте параметр `--debug` для получения подробной отладочной информации

### Проблемы с потоковым режимом

Если у вас возникают проблемы с потоковым режимом (stream):

1. Убедитесь, что вы используете актуальную версию Ollama, которая поддерживает потоковый режим
2. Попробуйте отключить потоковый режим с помощью параметра `--no-stream`
3. Проверьте журнал для получения подробной информации об ошибках: `~/.config/ollama_proxy/logs/client.log`
4. В тестовом режиме с параметром `--debug` вы можете увидеть фактический ответ от Ollama API и понять причину проблемы

### Проблемы с моделью Ollama

1. Убедитесь, что указанная модель установлена в вашем экземпляре Ollama
2. Если модель не найдена, вы можете установить её командой `ollama pull имя_модели`
3. Вы можете изменить модель, используя параметр `--force-model новая_модель`

### Ошибки JSON при запросах к Ollama

Если вы видите ошибки разбора JSON в ответах от Ollama API:
1. Запустите клиент в тестовом режиме с параметром `--test --debug` для получения подробной информации об ошибке
2. Проверьте, что используемая версия Ollama поддерживает указанную модель
3. Попробуйте отключить потоковый режим с помощью параметра `--no-stream`, если проблема связана с обработкой потоковых данных
4. Попробуйте обновить Ollama до последней версии

### Сброс настроек

Если у вас возникли проблемы с конфигурацией, вы можете сбросить настройки:

```bash
python client.py --reset-config
```

## Примечание

Клиент настроен на подключение к серверу по адресу `wss://bober.app:5050/auth-proxy`. Хост (`bober.app`) и путь (`/auth-proxy`) захардкожены в коде, но порт можно изменить через параметр командной строки `--port`.

## Требования

- Python 3.7+
- websockets
- httpx
- Установленный и запущенный Ollama с нужными моделями 