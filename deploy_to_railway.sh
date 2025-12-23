#!/bin/bash

# Скрипт для подготовки и деплоя Secret Santa бота на Railway

echo "🚀 Подготовка к деплою на Railway..."
echo ""

# Проверяем, есть ли git репозиторий
if [ ! -d ".git" ]; then
    echo "📦 Инициализация git репозитория..."
    git init
    echo "✅ Git репозиторий создан"
else
    echo "✅ Git репозиторий уже существует"
fi

# Добавляем все файлы
echo ""
echo "📝 Добавление файлов..."
git add .

# Проверяем статус
echo ""
echo "📊 Статус репозитория:"
git status

echo ""
echo "✅ Файлы готовы к коммиту!"
echo ""
echo "📋 Следующие шаги:"
echo ""
echo "1. Закоммитьте изменения:"
echo "   git commit -m 'Add Secret Santa bot for Railway'"
echo ""
echo "2. Создайте репозиторий на GitHub (если еще нет):"
echo "   - Зайдите на github.com"
echo "   - Создайте новый репозиторий (например: secret-santa-bot)"
echo ""
echo "3. Подключите к GitHub:"
echo "   git remote add origin https://github.com/ВАШ_USERNAME/secret-santa-bot.git"
echo "   git branch -M main"
echo "   git push -u origin main"
echo ""
echo "4. На Railway:"
echo "   - Зайдите на railway.app"
echo "   - New Project → Deploy from GitHub repo"
echo "   - Выберите ваш репозиторий"
echo "   - Добавьте переменные окружения:"
echo "     TELEGRAM_BOT_TOKEN=8433291588:AAE1YyEPFrbwWK8Db1Gy2xhiOdrRHimXvMc"
echo "     ADMIN_ID=47509867"
echo ""
echo "🎉 Готово! Бот будет работать 24/7!"

