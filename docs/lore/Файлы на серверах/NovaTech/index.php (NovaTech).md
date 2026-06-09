---
aliases: [index.php, NovaTech portal, клиентский портал]
tags: [файл, novatech, миссия-1, сторителлинг, код]
location: /var/www/html/index.php
server: NovaTech (192.168.1.10)
mission: "[[Миссия 1 — Первый контакт]]"
---

# index.php (NovaTech)

> Главная страница клиентского портала [[NovaTech Solutions]]. PHP-файл с комментарием о нефиксированной SQL-инъекции.

## Расположение

`/var/www/html/index.php` на рабочей станции dev-workstation (192.168.1.10)

## Содержимое файла

```php
<?php
// NovaTech Solutions — Client Portal v2.1
// TODO: fix SQL injection in login form (какой уже год...)
require_once 'config.php';
echo "<h1>Welcome to NovaTech Solutions</h1>";
echo "<p>Quality web solutions since 2019</p>";
?>
```

## Нарративная функция

- **Характеризация компании**: [[NovaTech Solutions]] -- маленькая веб-студия, работающая с 2019 года. "Quality web solutions" -- ирония, учитывая SQL-инъекцию в формe логина
- **TODO-комментарий**: "какой уже год..." -- разработчик знает об уязвимости, но никто не чинит. Типичная картина в небольших компаниях
- **SQL-инъекция**: потенциальный вектор атаки, который [[Полог (The Canopy)|Полог]] мог использовать для первоначальной компрометации серверов NovaTech
- **Реализм**: настоящие PHP-файлы мелких студий часто выглядят именно так -- минимум кода, TODO-комментарии, забытые уязвимости

## Связанные файлы

- [[config.ini]] -- файл `config.php` (подключаемый в index.php) ссылается на ту же конфигурацию БД
- [[notes.txt (developer)]] -- developer упоминает работу над CSS страницы логина
- [[bash_history (developer)]] -- `nano /var/www/html/index.php` в истории
