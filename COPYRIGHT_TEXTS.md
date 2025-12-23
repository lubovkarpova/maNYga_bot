# 📝 Все текстовые сообщения бота MaNYGA

## 🎁 Команда /start

```
Hey, {name}! 🎁

This is MaNYGA — Secret Santa for people who love giving gifts... and pretending it's anonymous.

Here's how it works:

/im_in – I'm playing
/add_small_human – Add a kid without Telegram
/who_are_we – See who's in the game
/make_it_random – Assign gift pairs (admin only)
/my_mission – Who you're gifting to
/help – In case you forgot what's going on

🧦 Budget: up to 150₪
🎯 Goal: no stress, just good surprises
📦 Rule: give something you'd smile at (or explain later)
```

---

## 📝 Команда /im_in (регистрация взрослого)

### Запрос имени:
```
📝 What name should we use? Nicknames are fine. 🤫
```

### Регистрация закрыта:
```
❌ Sorry, registration's closed — names have already been matched.
```

### Уже зарегистрирован:
```
✅ You're already in — registered as: {name}
```

### Имя слишком короткое:
```
❌ That name's a bit too short. Try again?
```

### Успешная регистрация:
```
✅ Welcome, {name}! You're in.
Current tally: {count} adults, {count} kids
```

---

## 👶 Команда /add_small_human (добавление ребенка)

### Запрос имени:
```
👶 What's the kid's name? We'll handle the rest.
```

### Регистрация закрыта:
```
❌ Too late — the game's already started.
```

### Имя слишком короткое:
```
❌ That name's too short. Give it another shot.
```

### Успешное добавление:
```
✅ Got it! {name} is in.
We'll send you their assignment.

Current tally: {count} adults, {count} kids
```

---

## 📋 Команда /who_are_we (список участников)

### Нет участников:
```
📋 No one's joined yet. Just us, the silence, and a bot.
```

### Список участников:
```
📋 Here's who's playing:

👨‍💼 Adults:
1. {name}
2. {name}
...

👶 Kids:
1. {name} (added by {guardian_name})
2. {name} (added by {guardian_name})
...

Total: {count} adults, {count} kids
```

---

## 🎲 Команда /make_it_random (создание назначений, админ)

### Нет прав:
```
❌ This one's for the admin. You know who you are.
```

### Уже создано:
```
⚠️ Assignments are already done.
Need a reset? Use /reset (admin only).
```

### Недостаточно участников:
```
❌ Need at least 2 people to make this work.
Otherwise, it's just... gifting to yourself.
```

### Назначение (один взрослый):
```
🎅🎁 Your Secret Santa assignment:

You ({giver_name}) are gifting to:
👤 {receiver_name}

(This is a kid without Telegram)  [if receiver is child]
```

### Несколько назначений (взрослый + ребёнок):
```
🎅🎁 Your Secret Santa assignments:

👤 You ({giver_name}) are gifting to:
   {receiver_name}

👶 {kid_name} is gifting to:
   {receiver_name}
```

### Успешное создание (для админа):
```
✅ Assignments sent out!
Let the mysterious generosity begin.

Total participants: {count}
```

### Ошибка:
```
❌ Something went wrong during assignments.
Try again? Or try tea first.
```

---

## 🎯 Команда /my_mission (моё назначение)

### Назначения не созданы:
```
⏳ Assignments aren't ready yet.
Waiting on the admin to hit the button.
```

### Нет назначения:
```
❌ You don't seem to be in the game.
Try /im_in first.
```

### Одно назначение:
```
🎅🎁 Your Secret Santa assignment:

You ({giver_name}) are gifting to:
👤 {receiver_name}

(This is a kid without Telegram)  [if receiver is child]
```

### Несколько назначений:
```
🎅🎁 Your Secret Santa assignments:

👤 You ({giver_name}) are gifting to:
   {receiver_name}

👶 {kid_name} is gifting to:
   {receiver_name}
```

---

## 🔄 Команда /reset (сброс данных, админ)

### Нет прав:
```
❌ Only admins can do this. Democracy is limited here.
```

### Успешный сброс:
```
✅ Everything's been wiped.
Fresh start, clean slate, empty list.
```

---

## ❌ Команда /cancel (отмена)

```
❌ Got it. Canceled.
Sometimes giving up is also a choice.
```

---

## 📖 Команда /help (справка)

```
📖 Commands overview:

/start – Start the bot
/im_in – Join the game
/add_small_human – Add a child (no Telegram needed)
/who_are_we – View all participants
/make_it_random – Assign gift pairs (admin only)
/my_mission – See who you're buying for
/reset – Reset everything (admin only)
/help – You're here

💡 Note: Kids without Telegram can still play — just register them, and their assignment will go to the adult who added them.
```

---

## 📝 Примечания

- `{name}` - имя пользователя (из Telegram)
- `{giver_name}` - имя того, кто дарит подарок
- `{receiver_name}` - имя того, кому дарят подарок
- `{count}` - количество участников
- `{guardian_name}` - имя опекуна ребенка

---

## 🎨 Стиль сообщений

- Используются эмодзи для визуального разделения
- Тон: дружелюбный, неформальный, с юмором
- Форматирование: Markdown (для /start используется parse_mode='Markdown')
