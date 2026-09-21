# CI/CD Pipeline Monitor & Dispatcher

Веб-приложение для централизованного мониторинга статусов сборки и диспетчеризации пайплайнов GitHub Actions. Проект разработан в рамках курсовой работы и представляет собой микросервисную архитектуру, объединяющую REST API на FastAPI, реляционную СУБД PostgreSQL и SPA-клиент на React.

---

## Основные возможности

* **Агрегация статусов в реальном времени:** сбор данных о прогонах пайплайнов, коммитах, авторах и длительности выполнения шагов через GitHub Actions REST API.
* **Ручная диспетчеризация (Re-run):** повторный запуск упавших или завершенных сборок непосредственно из веб-интерфейса в один клик.
* **Аналитическая панель:** автоматический расчет метрик надежности (общий объем сборок, процент успешности `Success Rate`, количество сбоев).
* **Сквозная безопасность:** аутентификация пользователей по стандарту OAuth2 с генерацией JWT-токенов (`HS256`, пароли хешируются через `bcrypt`), симметричное шифрование персональных токенов доступа GitHub PAT алгоритмом `Fernet` (AES-128-CBC + HMAC-SHA256).
* **Управление проектами:** гибкое включение и отключение мониторинга для конкретных репозиториев пользователя.

---

## Архитектурный стек

| Слой | Технологии |
| :--- | :--- |
| **Backend** | Python 3.12+, FastAPI, SQLAlchemy 2.0 (AsyncIO), Asyncpg, Pydantic v2, HTTPX |
| **Frontend** | React 18, TypeScript, Vite, Tailwind CSS, Lucide React, Axios |
| **База данных** | PostgreSQL 16 |
| **Инфраструктура** | Docker, Docker Compose, Nginx (Alpine) |

---

## Структура проекта

```text
coursework-web-app-ci-cd/
├── backend/
│   ├── app/
│   │   ├── api/          # Маршруты API (auth, providers, pipelines)
│   │   ├── core/         # Конфигурация, безопасность, подключение к БД
│   │   ├── models/       # ORM-модели SQLAlchemy
│   │   ├── schemas/      # Схемы валидации Pydantic
│   │   ├── services/     # Асинхронный клиент GitHub Actions API
│   │   └── main.py       # Точка входа FastAPI
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # Навигация, защищенные маршруты
│   │   ├── context/      # AuthContext (управление JWT-сессией)
│   │   ├── pages/        # Login, Dashboard, Settings
│   │   └── services/     # Инстанс Axios с интерцепторами
│   ├── Dockerfile
│   └── nginx.conf
├── docker-compose.yml
└── README.md
```

---

## Быстрый запуск (Docker Compose)

### 1. Предварительные требования
* Установленный Docker Desktop (с поддержкой Docker Compose v2).
* Токен доступа GitHub PAT (Personal Access Token) с областями видимости: `repo`, `workflow`.

### 2. Клонирование и запуск

Склонируйте репозиторий:

```bash
git clone [https://github.com/your-username/coursework-web-app-ci-cd.git](https://github.com/your-username/coursework-web-app-ci-cd.git)
cd coursework-web-app-ci-cd
```

Запустите контейнеры в фоновом режиме:

```bash
docker compose up -d --build
```

Откройте сервис в браузере:
* **Клиентский веб-интерфейс:** http://localhost
* **Интерактивная спецификация API (Swagger UI):** http://localhost:8000/docs
* **PostgreSQL:** доступен снаружи на порту `5433` (внутри сети Docker — на `5432`).

---

## Локальная разработка без Docker

### Backend

1. Перейдите в директорию бэкенда и создайте виртуальное окружение:

   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # На Windows: .\venv\Scripts\Activate.ps1
   ```

2. Установите зависимости:

   ```bash
   pip install -r requirements.txt
   ```

3. Создайте файл `backend/.env`:

   ```env
   PROJECT_NAME="CI/CD Monitor API"
   DATABASE_URL="postgresql+asyncpg://cicd_user:cicd_password@127.0.0.1:5433/cicd_monitor"
   SECRET_KEY="your-jwt-secret-key"
   ALGORITHM="HS256"
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ENCRYPTION_KEY="your-fernet-key="
   ```

4. Запустите сервер разработки:

   ```bash
   uvicorn app.main:app --reload
   ```

### Frontend

1. Перейдите в директорию фронтенда и установите зависимости:

   ```bash
   cd frontend
   npm install
   ```

2. Запустите dev-сервер:

   ```bash
   npm run dev
   ```

Клиент запустится по адресу: http://localhost:5173.

---

## Ключевые эндпоинты API

* `POST /api/v1/auth/register` — регистрация нового пользователя.
* `POST /api/v1/auth/login` — получение JWT-токена (OAuth2 password flow).
* `GET /api/v1/auth/me` — проверка текущей сессии.
* `POST /api/v1/providers` — привязка аккаунта GitHub и шифрование PAT.
* `POST /api/v1/providers/{id}/sync` — импорт репозиториев из GitHub.
* `GET /api/v1/pipelines` — список сборок с фильтрами по статусу и репозиторию.
* `POST /api/v1/pipelines/sync` — опрос GitHub API и обновление состояний.
* `POST /api/v1/pipelines/{id}/rerun` — отправка команды перезапуска workflow.
* `GET /api/v1/metrics/summary` — получение агрегированных метрик стабильности.