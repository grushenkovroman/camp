-- Создание БД и пользователя для проекта camp.rasti24.ru
-- Запускать из-под postgres: sudo -u postgres psql -f init.sql
-- Подставь нужный пароль вместо :PASSWORD

\set ON_ERROR_STOP on

CREATE USER camp_rasti WITH PASSWORD :'PASSWORD';
CREATE DATABASE camp_rasti OWNER camp_rasti ENCODING 'UTF8';
ALTER ROLE camp_rasti SET timezone TO 'Europe/Moscow';
GRANT ALL PRIVILEGES ON DATABASE camp_rasti TO camp_rasti;
