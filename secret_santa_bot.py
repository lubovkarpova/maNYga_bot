import os
import random
import logging
from typing import Dict, List, Set
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
REGISTERING_ADULT, REGISTERING_CHILD, WAITING_FOR_CHILD_GUARDIAN = range(3)

# Хранилище данных
class SecretSantaData:
    def __init__(self):
        self.adults: Dict[int, str] = {}  # user_id -> name
        self.children: List[Dict] = []  # [{"name": str, "guardian_id": int}]
        self.assignments: Dict[int, Dict] = {}  # user_id -> {"gives_to": str, "type": "adult"/"child"}
        self.assigned = False
    
    def add_adult(self, user_id: int, name: str):
        self.adults[user_id] = name
    
    def add_child(self, name: str, guardian_id: int):
        self.children.append({"name": name, "guardian_id": guardian_id})
    
    def get_all_participants(self) -> List[str]:
        """Возвращает список всех участников (взрослые + дети)"""
        participants = list(self.adults.values())
        participants.extend([child["name"] for child in self.children])
        return participants
    
    def make_assignments(self):
        """Создает назначения Secret Santa"""
        if self.assigned:
            return False
        
        all_participants = self.get_all_participants()
        if len(all_participants) < 2:
            return False
        
        # Создаем циклические назначения
        shuffled = all_participants.copy()
        random.shuffle(shuffled)
        
        # Создаем пары: каждый дарит следующему в списке
        for i, giver in enumerate(all_participants):
            receiver = shuffled[(shuffled.index(giver) + 1) % len(shuffled)]
            
            # Находим user_id для взрослого или guardian_id для ребенка
            giver_user_id = None
            for uid, name in self.adults.items():
                if name == giver:
                    giver_user_id = uid
                    break
            
            if giver_user_id is None:
                # Это ребенок, находим его guardian
                for child in self.children:
                    if child["name"] == giver:
                        giver_user_id = child["guardian_id"]
                        break
            
            if giver_user_id:
                # Определяем тип получателя
                receiver_type = "adult" if receiver in self.adults.values() else "child"
                self.assignments[giver_user_id] = {
                    "gives_to": receiver,
                    "type": receiver_type,
                    "giver_name": giver
                }
        
        self.assigned = True
        return True

# Глобальное хранилище (в реальном приложении лучше использовать БД)
data = SecretSantaData()

# ID администратора (можно установить через переменную окружения)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start"""
    user_id = update.effective_user.id
    name = update.effective_user.first_name
    
    welcome_text = (
        f"Привет, {name}! 🎅\n\n"
        "Я бот для организации Secret Santa!\n\n"
        "Доступные команды:\n"
        "/register - Зарегистрироваться как участник\n"
        "/add_child - Добавить ребенка (без Telegram)\n"
        "/list - Показать всех участников\n"
        "/assign - Создать назначения (только админ)\n"
        "/my_assignment - Узнать, кому ты даришь подарок\n"
        "/help - Показать эту справку"
    )
    
    await update.message.reply_text(welcome_text)


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Регистрация взрослого участника"""
    user_id = update.effective_user.id
    
    if data.assigned:
        await update.message.reply_text(
            "❌ Регистрация закрыта! Назначения уже созданы."
        )
        return ConversationHandler.END
    
    if user_id in data.adults:
        await update.message.reply_text(
            f"✅ Вы уже зарегистрированы как: {data.adults[user_id]}"
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "📝 Пожалуйста, отправьте ваше имя для регистрации:"
    )
    return REGISTERING_ADULT


async def register_adult_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка имени взрослого участника"""
    user_id = update.effective_user.id
    name = update.message.text.strip()
    
    if len(name) < 2:
        await update.message.reply_text(
            "❌ Имя слишком короткое. Попробуйте еще раз:"
        )
        return REGISTERING_ADULT
    
    data.add_adult(user_id, name)
    await update.message.reply_text(
        f"✅ Вы успешно зарегистрированы как: {name}\n\n"
        f"Всего участников: {len(data.adults)} взрослых, {len(data.children)} детей"
    )
    return ConversationHandler.END


async def add_child_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Начало добавления ребенка"""
    user_id = update.effective_user.id
    
    if data.assigned:
        await update.message.reply_text(
            "❌ Регистрация закрыта! Назначения уже созданы."
        )
        return ConversationHandler.END
    
    await update.message.reply_text(
        "👶 Пожалуйста, отправьте имя ребенка:"
    )
    return REGISTERING_CHILD


async def register_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка имени ребенка"""
    name = update.message.text.strip()
    
    if len(name) < 2:
        await update.message.reply_text(
            "❌ Имя слишком короткое. Попробуйте еще раз:"
        )
        return REGISTERING_CHILD
    
    context.user_data['child_name'] = name
    await update.message.reply_text(
        f"✅ Имя ребенка сохранено: {name}\n\n"
        "Ребенок будет участвовать в Secret Santa, но его назначение получит взрослый, "
        "который его зарегистрировал."
    )
    
    # Автоматически назначаем текущего пользователя как опекуна
    user_id = update.effective_user.id
    data.add_child(name, user_id)
    
    await update.message.reply_text(
        f"✅ Ребенок {name} добавлен! Вы будете получать его назначение.\n\n"
        f"Всего участников: {len(data.adults)} взрослых, {len(data.children)} детей"
    )
    
    return ConversationHandler.END


async def list_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать список всех участников"""
    if not data.adults and not data.children:
        await update.message.reply_text("📋 Пока нет зарегистрированных участников.")
        return
    
    text = "📋 Список участников:\n\n"
    
    if data.adults:
        text += "👨‍💼 Взрослые:\n"
        for i, (uid, name) in enumerate(data.adults.items(), 1):
            text += f"{i}. {name}\n"
        text += "\n"
    
    if data.children:
        text += "👶 Дети:\n"
        for i, child in enumerate(data.children, 1):
            guardian_name = data.adults.get(child["guardian_id"], "Неизвестно")
            text += f"{i}. {child['name']} (опекун: {guardian_name})\n"
    
    text += f"\nВсего: {len(data.adults)} взрослых, {len(data.children)} детей"
    
    await update.message.reply_text(text)


async def assign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создание назначений Secret Santa (только для админа)"""
    user_id = update.effective_user.id
    
    # Проверка прав администратора
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды."
        )
        return
    
    if data.assigned:
        await update.message.reply_text(
            "⚠️ Назначения уже созданы! Используйте /reset для сброса (только админ)."
        )
        return
    
    total_participants = len(data.adults) + len(data.children)
    if total_participants < 2:
        await update.message.reply_text(
            "❌ Недостаточно участников! Нужно минимум 2 человека."
        )
        return
    
    if data.make_assignments():
        # Отправляем назначения всем участникам
        for uid, assignment in data.assignments.items():
            try:
                giver_name = assignment["giver_name"]
                receiver_name = assignment["gives_to"]
                receiver_type = assignment["type"]
                
                message = (
                    f"🎅🎁 Secret Santa назначение!\n\n"
                    f"Вы ({giver_name}) дарите подарок:\n"
                    f"👤 {receiver_name}"
                )
                
                if receiver_type == "child":
                    message += "\n\n(Это ребенок, у которого нет Telegram)"
                
                await context.bot.send_message(chat_id=uid, text=message)
            except Exception as e:
                logger.error(f"Ошибка при отправке сообщения пользователю {uid}: {e}")
        
        await update.message.reply_text(
            f"✅ Назначения созданы и отправлены всем участникам!\n\n"
            f"Всего участников: {total_participants}"
        )
    else:
        await update.message.reply_text("❌ Ошибка при создании назначений.")


async def my_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать свое назначение"""
    user_id = update.effective_user.id
    
    if not data.assigned:
        await update.message.reply_text(
            "⏳ Назначения еще не созданы. Дождитесь команды от администратора."
        )
        return
    
    # Проверяем, есть ли назначение для этого пользователя
    if user_id in data.assignments:
        assignment = data.assignments[user_id]
        receiver_name = assignment["gives_to"]
        receiver_type = assignment["type"]
        giver_name = assignment["giver_name"]
        
        message = (
            f"🎅🎁 Ваше назначение Secret Santa:\n\n"
            f"Вы ({giver_name}) дарите подарок:\n"
            f"👤 {receiver_name}"
        )
        
        if receiver_type == "child":
            message += "\n\n(Это ребенок, у которого нет Telegram)"
        
        await update.message.reply_text(message)
    else:
        # Проверяем, может быть пользователь опекун ребенка
        child_assignments = []
        for child in data.children:
            if child["guardian_id"] == user_id:
                # Ищем назначение для этого ребенка
                for uid, assignment in data.assignments.items():
                    if assignment["giver_name"] == child["name"]:
                        child_assignments.append({
                            "child_name": child["name"],
                            "receiver": assignment["gives_to"]
                        })
        
        if child_assignments:
            message = "🎅🎁 Назначения для детей, которых вы зарегистрировали:\n\n"
            for ca in child_assignments:
                message += f"👶 {ca['child_name']} дарит подарок:\n👤 {ca['receiver']}\n\n"
            await update.message.reply_text(message)
        else:
            await update.message.reply_text(
                "❌ У вас нет назначения. Возможно, вы не зарегистрированы."
            )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Сброс всех данных (только для админа)"""
    user_id = update.effective_user.id
    
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ У вас нет прав для выполнения этой команды."
        )
        return
    
    data.adults.clear()
    data.children.clear()
    data.assignments.clear()
    data.assigned = False
    
    await update.message.reply_text(
        "✅ Все данные сброшены. Можно начинать заново!"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена текущей операции"""
    await update.message.reply_text("❌ Операция отменена.")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Справка по командам"""
    help_text = (
        "📖 Справка по командам:\n\n"
        "/start - Начать работу с ботом\n"
        "/register - Зарегистрироваться как участник\n"
        "/add_child - Добавить ребенка (без Telegram)\n"
        "/list - Показать всех участников\n"
        "/assign - Создать назначения Secret Santa (только админ)\n"
        "/my_assignment - Узнать, кому ты даришь подарок\n"
        "/reset - Сбросить все данные (только админ)\n"
        "/help - Показать эту справку\n\n"
        "💡 Совет: Дети без Telegram могут участвовать через взрослых, "
        "которые их зарегистрируют. Взрослый получит назначение для ребенка."
    )
    await update.message.reply_text(help_text)


def main():
    """Запуск бота"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не установлен в переменных окружения!")
        return
    
    # Создаем приложение
    application = Application.builder().token(token).build()
    
    # Регистрация взрослого
    register_handler = ConversationHandler(
        entry_points=[CommandHandler("register", register)],
        states={
            REGISTERING_ADULT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_adult_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Добавление ребенка
    add_child_handler = ConversationHandler(
        entry_points=[CommandHandler("add_child", add_child_start)],
        states={
            REGISTERING_CHILD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_child_name)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(register_handler)
    application.add_handler(add_child_handler)
    application.add_handler(CommandHandler("list", list_participants))
    application.add_handler(CommandHandler("assign", assign))
    application.add_handler(CommandHandler("my_assignment", my_assignment))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("help", help_command))
    
    # Запускаем бота
    logger.info("Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

