# camp-program

Сервис учёта баллов команд лагерной смены. Разовый проект на одну смену.

## Домен и сервер

- **Домен:** `camp.rasti24.ru` (DNS A → 201.51.5.119)
- **Сервер (с 2026-06-12):** `ssh root@201.51.5.119` (VPS msk-1-vm-lm3b), Ubuntu 24.04, nginx 1.24, gunicorn на `127.0.0.1:8091`
- **Старый сервер:** `grushenkov@84.22.133.11` — сервис остановлен, копия оставлена как резерв
- **Путь на сервере:** `/home/grushenkov/projects/camp-program`
- **Локальный путь:** `/Users/romangrusenkov/Projects/camp-program`
- **Git:** локально `git init`, удалённый репозиторий заведём позже. Деплой — `deploy.sh` (rsync + restart).

## Стек

- Python 3.12 + Flask + SQLAlchemy + Jinja2
- Flask-Login + bcrypt — авторизация админки
- Postgres 16 (уже на сервере, `127.0.0.1:5432`)
- gunicorn (2 воркера) под systemd
- nginx 1.29 + certbot 2.9 (webroot ACME через `/var/www/certbot`, как у других сайтов)
- Локальный порт бэкенда: **`127.0.0.1:8090`**

## БД

- БД: `camp_rasti`, пользователь: `camp_rasti` (отдельный, только на эту БД)
- Таймзона ролей БД: `Europe/Moscow` (все «дни» — `DATE` по МСК)
- Схема `public` (отдельная БД, без namespace-схем)

Таблицы:
- `teams (id UUID PK, name, color, sort_order, created_at)`
- `team_members (id, team_id FK, name, role ENUM 'member'|'mentor', sort_order)`
- `score_events (id, team_id FK, points INT, reason TEXT, event_date DATE, created_at, created_by)`
- `daily_tasks (event_date DATE PK, content TEXT, updated_at, updated_by)`
- `admin_users (id, login UNIQUE, password_hash)`

## Маршруты

**Публично:**
- `GET /<team_uuid>` — страница команды (по умолчанию сегодня по МСК); сверху блок «Рейтинг»: место команды по сумме баллов за всю смену («N из 17»), равные суммы делят место, другие команды не показываются
- `GET /<team_uuid>?date=YYYY-MM-DD` — конкретный день; стрелки «← / →» по доступным датам, лимитов диапазона нет
- `GET /<team_uuid>/ustav` — вкладка «Устав»: «Кодекс базы 4:12» (HTML-вёрстка по мотивам `kodeks_bazy_412.pdf`, генератор — `tools/gen_kodeks.py`), без строки подписи

**Админка (требует login):**
- `GET/POST /admin/login`, `POST /admin/logout`
- `GET /admin/` — дашборд: команды + быстрая форма «начислить»
- `/admin/teams` — CRUD команд (имя, цвет, участники, наставники)
- `/admin/scores` — добавить/удалить начисление (команда, дата, ±баллы, причина)
- `/admin/daily-task` — задание на дату (для всех)

## Дизайн

Яркий технологичный неоновый стиль, фон/акценты — под цвет команды. Имя команды крупно сверху, под ним «задание дня», далее список начислений и итоги (за день / за смену). Тёмный фон, светящиеся рамки, моноширинный/гротеск.

## Сидинг

Скрипт `manage.py init`:
- создаёт таблицы, админа `admin/admin`
- засевает 16 команд `Команда 1..16` с разными неоновыми цветами

## Деплой

- Локально: `./deploy.sh` → `rsync -av --exclude '.venv' --exclude '__pycache__' ./ grushenkov@84.22.133.11:/home/grushenkov/projects/camp-program/`
- На сервере: `pip install -r requirements.txt` (в .venv), `python manage.py migrate`, `sudo systemctl restart camp-rasti`
- systemd unit: `/etc/systemd/system/camp-rasti.service`
- nginx site: `/etc/nginx/sites-available/camp.rasti24.ru.conf` (+ симлинк в sites-enabled)

## Решения / контекст

- **Один сервер с другими проектами** (koinon.*, gitlab) — порт 8090 свободен, конфиг nginx в стиле существующих
- **certbot --webroot -w /var/www/certbot** — путь уже используется другими сайтами, авторенью у certbot уже работает
- **Email Let's Encrypt:** `roman@grushenkov.ru`
- **Учётка админа:** `admin / admin` (поменять после смены не требуется — проект разовый)
