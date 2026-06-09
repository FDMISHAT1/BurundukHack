---
aliases: [уровень 3, CTF секреты, крипто стего hex]
tags: [пасхалки, уровень-3, список, ctf]
---

# Уровень 3 -- CTF секреты

> Крипто, стего, hex -- секреты, требующие технических навыков и знания инструментов. Формат [[Burunduk|burunduk'а]]: каждый секрет -- загадка, которую нужно расшифровать.

---

## Hex-кодирование

### [[motd (hex)]] -- `/etc/motd` на NovaTech
В конце стандартного MOTD -- hex-строка:
```
5765206e6f746963656420746f6f2e202d2d42
```

Декодирование: `echo "5765..." | xxd -r -p`

Результат: **"We noticed too. --B"**

[[Burunduk]] побывал на серверах [[NovaTech Solutions]] раньше [[Игрок|игрока]].

### Бинарный код в MOTD localhost
При логине:
```
BurundukOS v1.0 | Secure Operations Environment
01000010 00101110
```
`01000010` = 'B', `00101110` = '.'
Расшифровка: **Б.** -- подпись burunduk'а в двоичном коде.

---

## Стеганография

### [[logo.png (стего)]] -- `/var/www/html/logo.png` на NovaTech
```bash
steghide extract -sf logo.png
# Пароль: 4471
```
Внутри -- таймлайн компрометации NovaTech:
```
TIMELINE:
- NovaTech compromised: 2024-03-12
- Relay installed: 2024-03-15
- Installer signature: matches Canopy toolkit v4.x
- Operator: unknown (не КРОТ — другой почерк)

Я оставил это здесь на случай, если кто-то найдёт.
     --Б
```
Пароль **[[Тикет 4471|4471]]** -- номер тикета игрока.

---

## SSH и сетевые артефакты

### [[known_hosts (developer)]] -- `.ssh/known_hosts` на NovaTech
```
# 10.99.0.1 — DO NOT CONNECT — V. will know
```
**V.** = [[КРОТ (Виктор)|Виктор/КРОТ]]. `10.99.0.1` -- шлюз сети [[Vektora Analytics]] из [[Миссия 4 — Крот|миссии 4]]. Хлебная крошка, которая обретает смысл позже.

### [[auth.log (DB)]] -- `/var/log/auth.log` на DB-сервере
```
Nov 10 03:00:01 db-server sshd[4471]: Connection from 10.99.0.77
Nov 10 03:14:07 db-server sshd[4471]: session closed for root
```
Фантомные логины: IP из сети Vektora, PID [[Тикет 4471|4471]], сессии 03:00-[[Число 3-14|03:14]].

---

## Бинарные артефакты

### /tmp/.Xauthority на DB-сервере
```bash
xxd /tmp/.Xauthority
```
```
Filin. 2017. Istanbul. Not an accident.
```
"[[Филин]]. 2017. Стамбул. Не случайность." -- зашито в бинарный файл. Предвестие открытия в [[Миссия 4 — Крот|миссии 4]].

### `strings` на customers.db ([[Миссия 1 — Первый контакт|миссия 1]])
```bash
strings /var/lib/mysql/customers.db
```
```
CREATE TABLE relay_config (
  node_id TEXT, upstream TEXT, encryption_key TEXT
);
INSERT INTO relay_config VALUES(
  'NT-7', '10.20.30.15:4443', 'c4n0py-r3lay-k3y-2024'
);
```
Внутри "базы клиентов" -- таблица конфигурации ретранслятора [[Полог (The Canopy)|Полога]].

---

## Пароли-пазлы

### [[.vault README]] -- `/opt/.vault/README` на localhost
Пароль: первые буквы имён участников [[Нора (The Burrow)|Норы]] в порядке вступления.
**С**иница, **Ф**илин, **Ё**ж, **К**РОТ, {буква игрока} = `сфёк{x}`

Невозможно разгадать до [[Миссия 4 — Крот|миссии 4]].

### [[grub hidden menu]] -- `/boot/grub/.hidden_menu` на localhost
Пароль: **anomaly** (содержание [[Тикет 4471|тикета]], не его номер).

---

## CTF-флаги

### [[flag.txt (NovaTech)]] -- `/root/flag.txt` на NovaTech
```
CTF{n0v4t3ch_w4s_just_th3_b3g1nn1ng}
```
"NovaTech was just the beginning." Требует root-доступа.

---

## Связано

- [[Уровень 2 — Скрытые команды]] -- предыдущий уровень
- [[Уровень 4 — Временные секреты]] -- следующий уровень
- [[Число 3-14]] -- навязчивый мотив во всех CTF-секретах
- [[Тикет 4471]] -- номер пронизывает всю систему
