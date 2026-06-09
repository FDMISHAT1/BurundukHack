---
aliases: [motd hex, motd NovaTech, We noticed too]
tags: [файл, novatech, миссия-1, пасхалка, hex, burunduk, уровень-3]
location: /etc/motd
server: NovaTech (192.168.1.10)
mission: "[[Миссия 1 — Первый контакт]]"
easter_egg_level: 3
---

# motd (hex)

> Message of the Day на рабочей станции [[NovaTech Solutions]]. Содержит скрытую hex-строку -- послание [[Burunduk|burunduk'а]].

## Расположение

`/etc/motd` на рабочей станции dev-workstation (192.168.1.10)

Показывается при логине через SSH, но мало кто отдельно делает `cat /etc/motd`.

## Содержимое файла

```
Welcome to Ubuntu 20.04 LTS (GNU/Linux 5.4.0-42-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com

System information as of Thu Nov 14 09:15:23 UTC 2024

System load:  0.47        Processes:           142
Memory usage: 34%         Users logged in:     1
Disk usage:   67%         IPv4 address:        192.168.1.10

5765206e6f746963656420746f6f2e202d2d42
```

## Скрытое послание

Последняя строка -- hex-кодированная строка. Декодирование:

```bash
echo "5765206e6f746963656420746f6f2e202d2d42" | xxd -r -p
```

Результат:

```
We noticed too. --B
```

**"Мы тоже заметили. --Б"** -- [[Burunduk]] оставил метку, подтверждая, что он уже побывал на серверах [[NovaTech Solutions]] до того, как отправил туда [[Игрок|игрока]].

## Нарративная функция

- **Burunduk был здесь первым**: он провёл разведку серверов NovaTech заранее. Подтверждается также в [[flag.txt (NovaTech)]] и [[logo.png (стего)]]
- **"We noticed too"**: "тоже" -- значит, burunduk знает, что developer тоже заметил аномалию (см. [[notes.txt (developer)]], [[bash_history (developer)]]). Но developer не стал копать. Burunduk -- стал.
- **Подпись --B**: латинская "B" вместо кириллической "Б" -- burunduk подписывается на языке системы
- **Hex-кодирование**: уровень 3 пасхалок ([[Уровень 3 — CTF секреты]]). Требует знания инструментов (xxd, Python, CyberChef)

## Связанные файлы

- [[flag.txt (NovaTech)]] -- ещё одна метка burunduk'а
- [[logo.png (стего)]] -- стеганография с подробным таймлайном
- [[Уровень 3 — CTF секреты]] -- этот hex входит в систему крипто-пасхалок
- [[notes.txt (developer)]] -- developer тоже "заметил" ночную активность
