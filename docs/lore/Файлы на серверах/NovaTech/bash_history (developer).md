---
aliases: [bash_history developer, .bash_history, история команд developer]
tags: [файл, novatech, миссия-1, подсказка, сторителлинг]
location: /home/developer/.bash_history
server: NovaTech (192.168.1.10)
mission: "[[Миссия 1 — Первый контакт]]"
---

# bash_history (developer)

> История команд разработчика на рабочей станции [[NovaTech Solutions]]. Содержит подсказки к [[config.ini]] и свидетельства обнаружения ночной активности.

## Расположение

`/home/developer/.bash_history` на рабочей станции dev-workstation (192.168.1.10)

## Содержимое файла

```bash
cd /opt
cat config.ini
mysql -h 192.168.1.20 -u dbadmin -p
nano /var/www/html/index.php
top
# почему load average 4.0 в 3 часа ночи???
ps aux | grep -v grep | grep python
# какой-то скрипт в /tmp крутится... странно
# ладно, завтра разберусь
```

## Нарративная функция

### Подсказки для игрока
- `cat config.ini` в `/opt` -- прямой путь к [[config.ini]] с паролем от БД
- `mysql -h 192.168.1.20 -u dbadmin -p` -- показывает, что developer подключался к DB-серверу с этими credentials
- [[Burunduk]] специально обращает внимание на .bash_history в подсказке 4:

```
[burunduk]: ...Подсказка внутри подсказки: .bash_history
            рассказывает, что человек делал. Всегда читай историю.
```

### Экологический сторителлинг
- **load average 4.0 в 3 часа ночи** -- ретранслятор [[Полог (The Canopy)|Полога]] работает ночью (см. [[relay.conf]])
- **python-скрипт в /tmp** -- процесс, обслуживающий ретранслятор. Developer заметил, но не стал разбираться ("ладно, завтра разберусь")
- **Контраст с [[Игрок|игроком]]**: developer увидел аномалию и забил. Игрок увидел аномалию и создал [[Тикет 4471]]. В этом вся разница.

## Связанные файлы

- [[config.ini]] -- файл, к которому обращался developer
- [[relay.conf]] -- скрытый конфиг в /tmp, вызывающий ночную нагрузку
- [[notes.txt (developer)]] -- те же наблюдения, но в формате TODO
- [[email developer]] -- admin отговаривает от исследования /tmp
- [[index.php (NovaTech)]] -- developer редактировал этот файл
