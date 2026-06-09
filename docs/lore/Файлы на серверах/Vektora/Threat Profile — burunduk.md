---
aliases: [threat profile burunduk, досье на burunduk, burunduk.md на Vektora]
tags: [файл, vektora, миссия-4, лор, крот, burunduk, полог, досье]
location: /opt/canopy/internal/threat_profiles/burunduk.md
server: Vektora Analytics (10.99.0.x)
mission: "[[Миссия 4 — Крот]]"
---

# Threat Profile -- burunduk

> Досье [[Полог (The Canopy)|Полога]] на [[Burunduk|burunduk'а]], составленное [[КРОТ (Виктор)|КРОТ'ом]]. Содержит известные техники, паттерны, контрмеры. Ключевая ошибка: КРОТ не допускает, что burunduk обучил нового ученика.

## Расположение

`/opt/canopy/internal/threat_profiles/burunduk.md` на сервере [[Vektora Analytics]]

## Содержимое файла

```
# THREAT PROFILE: BURUNDUK

Priority: HIGH (currently DORMANT)
Last known activity: 2020-03
Status: Presumed medical incapacitation

## Known Techniques
- SSH tunneling chains (signature: 3+ hops, always
  exits through university networks)
- Prefers Linux-based toolchains
- Never uses automated scanners without manual
  follow-up
- Characteristic: always covers tracks with custom
  log cleaner ("clean_b.sh")
- Social engineering: NEVER uses. Considers it
  "dishonorable" (confirmed by former associate)

## Known Associates
- Sinitsа (RETIRED — confirmed, NZ)
- Yozh (RETIRED — confirmed, location unknown)
- Filin (DECEASED — Istanbul, 2017)

## Countermeasures
- All Canopy systems run modified IDS trained on
  burunduk's toolchain signatures
- SSH honeypots deployed on all external-facing nodes
- Custom firewall rules targeting known exit nodes

## Assessment (by V./KROT)
If burunduk returns to activity, existing countermeasures
should contain 90%+ of his approaches. His methods are
known. His patterns are predictable.

The only unknown variable: whether he has trained
someone new.

Probability assessment: LOW. After Burrow dissolution,
no evidence of new recruitment.

Last updated: 2024-06-15
```

## Нарративная функция

### КРОТ знает burunduk'а изнутри
- **SSH tunneling chains, 3+ hops, university networks** -- конкретные паттерны, которые может знать только бывший соратник
- **"clean_b.sh"** -- даже имя скрипта для заметания следов. Уровень интимного знания
- **Social engineering: NEVER** -- burunduk считает социальную инженерию "бесчестной". Это характеризует его как человека с жёсткими принципами, даже в хакерстве
- **"confirmed by former associate"** -- "бывший сотрудник". КРОТ пишет о себе в третьем лице в официальном документе

### Known Associates -- [[Нора (The Burrow)|Нора]]
- **[[Синица]]** -- RETIRED, NZ (Новая Зеландия). Полог знает, где она
- **[[Ёж]]** -- RETIRED, location unknown. Ёж сумел скрыться
- **[[Филин]]** -- DECEASED, Istanbul, 2017. Сухая запись. КРОТ не упоминает, что Полог причастен (см. [[Гибель Филина (отчёт)]])
- **Игрок отсутствует** в списке -- КРОТ не знает о новом ученике. Это главное преимущество

### Критическая ошибка КРОТ'а
- **"Probability assessment: LOW"** -- КРОТ не верит, что burunduk кого-то нового обучает
- **"His patterns are predictable"** -- но паттерны [[Игрок|игрока]] **неизвестны**. Именно об этом говорит [[Burunduk]]:

```
[burunduk]: Он знает, как я работаю.
            Но он не знает, как работаешь ты.
            В этом наше преимущество.
```

### Геймплейное значение
- IDS обучена на паттернах burunduk'а -- объясняет, почему на серверах [[Vektora Analytics]] стоит серьёзная защита
- SSH honeypots -- если игрок действует как burunduk, его обнаружат. Нужно действовать по-своему

## Связанные файлы

- [[Project Acorn Status]] -- burunduk указан как "primary threat"
- [[Гибель Филина (отчёт)]] -- "Filin (DECEASED)" в контексте приказа Полога
- [[SSH authorized_keys (КРОТ)]] -- при всём досье, КРОТ не удалил ключ burunduk'а
- [[Переписка 2017]] -- "ты научил меня всему" -- и теперь использует эти знания против учителя
- [[Дневник КРОТ'а]] -- "Я его знаю. Он не из тех, кто умирает тихо"
- [[Burunduk#Досье Полога на Burunduk'а]] -- ссылка в профиле персонажа
