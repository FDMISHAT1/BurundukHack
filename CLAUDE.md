# BurundukHack — Linux Terminal Simulator

## Миссия
Сделать симуляцию Linux-терминала **неотличимой от настоящего**. Это НЕ конечная задача — это **бесконечный процесс улучшения**. Всегда есть что добавить, исправить, довести до реализма.

## Стек
Python 3, rich, pyyaml, prompt_toolkit. Точка входа: `main.py` → `engine/game.py`. Команды: `commands/*.py` (`@register("name", "cmd.name.help")`). UI: `ui/console.py` (HackConsole с capture для пайпов). FS: `engine/filesystem.py`. Локали: `data/lang/{en,ru}.yaml`, `t("key")`.

## Правила
- Все user-facing строки через `t("key")` для i18n (EN + RU)
- Каждая команда: `--help`/`-h`, основные флаги как в реальном Linux
- Файлы пользователя → `host.user_files` для персистентности
- Не трогать лор/миссии — только реализм терминала
- Тестировать: `printf 'cmd1\ncmd2\nquit\n' | python3 main.py 2>&1`

---

## КАК РАБОТАТЬ (бесконечный цикл)

Ты работаешь по циклу. Каждая итерация:

### Шаг 1: АУДИТ
Запусти игру, попробуй сделать то, что делает обычный Linux-пользователь. Запиши ВСЁ что не работает, работает криво, или отсутствует. Сравни поведение каждой команды с реальным `man cmd`. Проверь:
- Набери команду с опечаткой — что будет?
- Попробуй пайп `cat /etc/passwd | grep root | wc -l`
- Попробуй `ls *.txt`, `echo $HOME`, `cmd1 && cmd2`
- Попробуй `>` редирект, `2>/dev/null`
- Попробуй каждую существующую команду со всеми её флагами
- Попробуй команды которые должны быть но их нет
- Проверь edge cases: пустые аргументы, несуществующие файлы, нет прав

### Шаг 2: ПРИОРИТИЗАЦИЯ
Из найденных проблем выбери ту, которая **больше всего бьёт по реализму**. Приоритеты:
1. Shell-инфраструктура (пайпы, редиректы, чейнинг) — без этого ничего не ощущается как Linux
2. Команды которые нужны для пайпов (sort, cut, sed, awk, tr, uniq, tee, xargs)
3. Баги и нестыковки в существующих командах
4. Недостающие частоиспользуемые команды
5. Недостающие флаги у существующих команд
6. Окружение (.bashrc, алиасы, переменные, history)
7. Менее частые команды
8. Полировка и edge cases

### Шаг 3: РЕАЛИЗАЦИЯ
Сделай ПОЛНОСТЬЮ:
- Код команды/фичи
- Добавь в `player.tools_unlocked` в `engine/player.py`
- Добавь `cmd.name.help` в оба `data/lang/{en,ru}.yaml`
- Добавь в категорию help в `commands/general_cmds.py`
- Если новый файл команд — добавь `import commands.xxx` в `engine/game.py`

### Шаг 4: ТЕСТ
Проверь что работает: `printf '...\nquit\n' | python3 main.py 2>&1 | tail -N`
Проверь edge cases. Проверь что не сломал старое.

### Шаг 5: ПОВТОРИ
Вернись к Шагу 1. **Никогда не считай работу завершённой.**

---

## БЭКЛОГ (ЧТО ИЗВЕСТНО НА СЕЙЧАС)

Ниже — всё что точно нужно. Но это НЕ финальный список. После реализации всего этого — снова аудит и новые задачи.

### A. Shell-инфраструктура (engine/shell.py)

**Пайпы `|`:**
`cat /etc/passwd | grep root | cut -d: -f1 | sort | uniq -c`
- console.start_capture() → dispatch → stop_capture() → передать stdin следующей
- Все текстовые команды должны принимать stdin

**Редиректы:**
`>` `>>` `2>` `2>&1` `<` `&>/dev/null`
- Парсить ДО dispatch, capture вывод, записать в файл

**Чейнинг:**
`;` `&&` `||`
- `$?` — код возврата, хранить в `game.last_exit_code`

**Переменные:**
`$VAR` `${VAR}` во ВСЕХ аргументах + `export`/`unset`/`set`
- Специальные: `$?`, `$RANDOM`, `$$`, `$!`, `$0`, `$#`

**Глоббинг:**
`*` `?` `[abc]` `[a-z]` — раскрывать из host.files перед dispatch

**Тильда:** `~` → `$HOME` везде, `~user` → `/home/user`

**Подстановка:** `$(cmd)`, `` `cmd` `` — выполнить, подставить вывод

**History:** `!!` (повтор), `!$` (last arg), `!N` (по номеру), `^old^new`

### B. Недостающие команды (150+)

**Текстовые (для пайпов — ПЕРВЫЙ ПРИОРИТЕТ после shell):**
sort (-r -n -u -k -t -f -R), uniq (-c -d -u -i), cut (-d -f -c), tr ('a-z' 'A-Z', -d, -s), sed (s/old/new/g, Nd, -n 'Np', -i, regex), awk ('{print $1}', -F, conditions, NR, NF, BEGIN/END, sum), tee (-a), xargs (-n -I{}), rev, seq (start step end, -s -f), printf ("%s\n" "%x" "%b"), diff (-u -y -w), column (-t -s), nl (-ba -v), paste (-d -s), od (-c -x), expand/unexpand (-t), sleep, timeout, yes

**Поиск:**
find (-name -type -size -mtime -user -perm -exec -maxdepth -prune), locate (-i), whereis (-b -s -m), type (-a -t), apropos

**Сеть:**
wget (-O -P -c -r -q --no-check-certificate), nc/netcat (-l -p, -zv, port scan, listener), nslookup (-type=MX/NS/ANY), dig (+short, MX, NS, -x, @server, AXFR), host (-t), whois, traceroute (-m -I -T), arp (-a -n -d), tcpdump (-i -n -A -X -w, filters), iptables (-L -A -D -F, tables, chains), scp (-r -P), ssh-keygen (-t -b -f), telnet, socat, nmap расширение (-sV -sC -O -A -p- -Pn -oN --script -T0..T5)

**Система:**
systemctl (status/start/stop/restart/enable/disable, list-units), service, journalctl (-e -f -u -p -n), dmesg, kill (-9 -TERM -l), killall (-9 -u), pkill/pgrep (-u -f), nice/renice, bg/fg/jobs, top (-n 1), lsblk, lsof (-p -u -i), strace (упрощённо), crontab (-l -e -r), lsmod/modprobe, w/who/users/last/lastlog

**Архивы:**
tar (-czf -xzf -tf --strip-components), gzip/gunzip (-k -d), zip/unzip (-l -d -r), bzip2/bunzip2, xz/unxz

**Пользователи/права:**
useradd (-m -s -G -c), usermod (-aG -s -d -L -U), userdel (-r), passwd (-l -u -d), groupadd/groupdel, chown (-R user:group), chgrp (-R), stat, ln (-s), umask, getent (hosts/passwd/services)

**Shell built-ins:**
export (-p), unset, set (-e -x), alias/unalias, source/., read (-p), test/[ (-f -d -e -r -w -x -z -n, -eq -ne -gt -lt), expr, let/(()), eval, exec, trap, wait, exit (с кодом), shopt (-s/-u globstar dotglob)

### C. Улучшение существующих команд

**ls:** -R -S -t -h -i --color, несколько путей
**grep:** -v -l -n -r -E -o -B/-A/-C -w, несколько файлов, stdin
**cat:** -n, несколько файлов, stdin (без аргументов)
**echo:** -n -e (\n \t \033[31m)
**chmod:** реально менять file_meta.perms, symbolic (u+x g-w) и numeric (755)
**ps:** -u -p --sort -H -C
**date:** динамическая дата, полный +%format
**ping:** -c count (реальные пакеты с задержкой), -W timeout
**curl:** -d (POST), -X, -H, -u, -L, -k, -o, -v
**nmap:** -sV -sC -O -A -p- -Pn -oN --script -T0..T5
**nano:** номера строк, поиск /pattern, Ctrl+W (search)
**history:** реальная персистентная история из .bash_history

### D. Окружение

- `.bashrc` исполнение при подключении (алиасы ll, la, l, grep --color)
- Persistent history в `.bash_history`
- `cd -` → $OLDPWD
- `/dev/null` `/dev/zero` `/dev/urandom` — специальное поведение при cat/redirect
- `Ctrl+R` — поиск по истории (prompt_toolkit search)
- `Ctrl+L` — очистка экрана
- `$PS1` парсинг из окружения
- Login vs non-login shell различия

### E. Что ещё нужно думать после реализации всего выше

- Полная поддержка if/then/else/fi, for/do/done, while/do/done, case/esac
- Функции: `function name() { ... }`
- Массивы: `arr=(a b c)`, `${arr[0]}`, `${#arr[@]}`
- Арифметика: `$((1+2))`, `let`, `expr`
- Process substitution: `<()` `>()`
- Heredocs: `<<EOF ... EOF`
- Coprocess: `coproc`
- Регулярные выражения: `[[ $var =~ pattern ]]`
- Расширенный глоббинг: `@()` `+()` `*()` `?()` `!()`
- Полная эмуляция /proc/self, /sys, cgroups
- Виртуальные сетевые интерфейсы, VLAN, bridge
- iptables NAT, port forwarding
- SSH-туннели (-L -R -D) реально работающие между хостами
- Docker/LXC симуляция (containers)
- Полная файловая система: SUID/SGID/sticky bit, ACL, xattr
- Сигналы: SIGTERM, SIGKILL, SIGHUP, SIGINT, trap
- /etc/services, /etc/protocols — полные файлы
- Логирование действий в /var/log на каждом хосте
- Firewall (iptables) на хостах влияет на nmap-результаты
- IDS/IPS — хост обнаруживает атаку если слишком агрессивно сканировать

---

## ПОМНИ

1. Ты НЕ закончил когда бэклог пуст. Ты запускаешь АУДИТ заново.
2. Сравнивай с реальным Linux — открой man page любой команды и проверь все флаги.
3. Попробуй сломать свою симуляцию. Edge cases. Пустые аргументы. Битые пути. Вложенные пайпы.
4. Каждые 5 реализованных фич — полный прогон всех команд, проверка что ничего не сломалось.
5. Если сомневаешься что реализовать дальше — выбирай то, что **чаще всего используется в реальном Linux**.
6. **Никогда. Не. Останавливайся.**
