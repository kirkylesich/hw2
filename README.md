# Генератор конспектов лекций

Serverless веб-приложение для автоматической генерации PDF-конспектов из видеозаписей лекций, размещенных на Яндекс Диске.

### Компоненты

1. **API Gateway** - единая точка входа, маршрутизация HTTPS запросов
2. **Cloud Functions** (Python 3.12):
   - `create_task` - создание задания на генерацию конспекта
   - `list_tasks` - получение списка всех заданий
   - `static_pages` - отдача HTML страниц
3. **Serverless Container** (Python 3.12) - Worker для асинхронной обработки:
   - Валидация ссылки на видео
   - Загрузка видео с Яндекс Диска
   - Извлечение аудио (ffmpeg)
   - Распознавание речи (SpeechKit)
   - Генерация конспекта (YandexGPT)
   - Создание PDF (ReportLab)
4. **YDB** - хранение метаданных заданий (статусы, ошибки)
5. **Message Queue** - очередь заданий для асинхронной обработки
6. **Object Storage** - хранение временных файлов и готовых PDF
7. **Container Registry** - хранение Docker образа Worker

## Требования

- [Terraform](https://www.terraform.io/downloads.html) >= 1.0
- [Docker](https://docs.docker.com/get-docker/)
- [Yandex Cloud CLI](https://cloud.yandex.ru/docs/cli/quickstart)
- Аккаунт в Yandex Cloud с активным платежным аккаунтом

## Быстрый старт

### 1. Подготовка

Клонируйте репозиторий и перейдите в директорию:

```bash
git clone <repository-url>
cd lecture-notes-generator
```

### 2. Настройка Yandex Cloud

Авторизуйтесь в Yandex Cloud CLI:

```bash
yc init
```

### 3. Настройка Terraform

Скопируйте пример конфигурации:

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Получите OAuth токен для Terraform:

```bash
yc iam create-token
```

Отредактируйте `terraform.tfvars` и добавьте все необходимые параметры:

```hcl
cloud_id  = "b1g..."  # ID вашего облака
folder_id = "b1g..."  # ID вашей папки
prefix    = "lecture-notes"  # Префикс для имен ресурсов
zone      = "ru-central1-a"  # Зона доступности
yc_token  = "y0_..."  # OAuth токен из команды выше
```

Получить `cloud_id` и `folder_id` можно командами:

```bash
yc config list
```

**Важно**: Файл `terraform.tfvars` содержит секретные данные и не должен попадать в git (он уже добавлен в `.gitignore`)

### 4. Инициализация Terraform

```bash
terraform init
```

### 5. Развертывание инфраструктуры

Terraform автоматически соберет и загрузит Docker образ worker'а:

```bash
terraform apply
```

Terraform выполнит следующие действия:
- Создаст все облачные ресурсы (YDB, Message Queue, S3, VPC, Container Registry и т.д.)
- Соберет Docker образ worker'а для платформы linux/amd64
- Загрузит образ в Container Registry
- Развернет Serverless Container с worker'ом
- Настроит API Gateway и Cloud Functions

**Примечание**: Сборка Docker образа может занять несколько минут при первом запуске.

### 6. Получение URL приложения

После успешного развертывания Terraform выведет URL:

```bash
terraform output api_gateway_url
```

Откройте этот URL в браузере - вы увидите веб-форму для создания заданий.

## Использование

### Создание задания

1. Откройте веб-интерфейс по URL из `api_gateway_url`
2. Введите название лекции
3. Вставьте публичную ссылку на видео с Яндекс Диска
4. Нажмите "Создать задание"

### Получение публичной ссылки на видео

1. Откройте [Яндекс Диск](https://disk.yandex.ru)
2. Выберите видеофайл
3. Нажмите "Поделиться" → "Скопировать публичную ссылку"
4. Используйте эту ссылку в форме

### Отслеживание статуса

После создания задания вы будете перенаправлены на страницу со списком всех заданий. Статусы:

- **В очереди** - задание ожидает обработки
- **В обработке** - Worker обрабатывает задание
- **Успешно завершено** - PDF готов, доступна ссылка для скачивания
- **Ошибка** - произошла ошибка, отображается сообщение

### Скачивание PDF

Когда статус задания станет "Успешно завершено", появится ссылка "Скачать PDF". Нажмите на нее, чтобы загрузить готовый конспект.

## Технологический стек

- **Язык**: Python 3.12
- **Инфраструктура**: Terraform
- **Облако**: Yandex Cloud
- **Serverless**: Cloud Functions, Serverless Containers
- **База данных**: YDB (serverless)
- **Очереди**: Yandex Message Queue (SQS-compatible)
- **Хранилище**: Object Storage (S3-compatible)
- **AI**: YandexGPT, Yandex SpeechKit
- **Обработка видео**: ffmpeg
- **PDF**: ReportLab
- **HTTP сервер**: Flask

## Используемые сервисы Yandex Cloud

1. **API Gateway** - маршрутизация HTTP запросов
2. **Cloud Functions** - serverless функции для HTTP обработчиков
3. **Serverless Containers** - контейнеры для длительных операций
4. **YDB** - serverless база данных
5. **Message Queue** - очереди сообщений
6. **Object Storage** - хранилище файлов
7. **Container Registry** - реестр Docker образов
8. **SpeechKit** - распознавание речи
9. **YandexGPT** - генерация текста
10. **IAM** - управление доступом
11. **VPC** - виртуальная сеть
12. **Resource Manager** - управление ресурсами