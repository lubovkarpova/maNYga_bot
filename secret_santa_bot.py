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

# Загружаем переменные окружения из .env (для локального запуска)
# На Railway переменные окружения доступны напрямую через os.getenv()
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния для ConversationHandler
REGISTERING_ADULT, ASKING_RECOMMENDATIONS, REGISTERING_CHILD, ASKING_CHILD_RECOMMENDATIONS, WAITING_FOR_CHILD_GUARDIAN = range(5)

# Хранилище данных
class SecretSantaData:
    def __init__(self):
        self.adults: Dict[int, Dict] = {}  # user_id -> {"name": str, "recommendations": str}
        self.children: List[Dict] = []  # [{"name": str, "guardian_id": int}]
        self.assignments: Dict[int, List[Dict]] = {}  # user_id -> [{"gives_to": str, "type": "adult"/"child", "giver_name": str}]
        self.assigned = False
    
    def add_adult(self, user_id: int, name: str, recommendations: str = ""):
        self.adults[user_id] = {"name": name, "recommendations": recommendations}
    
    def get_adult_name(self, user_id: int) -> str:
        """Get adult name by user_id"""
        return self.adults.get(user_id, {}).get("name", "")
    
    def add_child(self, name: str, guardian_id: int, recommendations: str = ""):
        self.children.append({"name": name, "guardian_id": guardian_id, "recommendations": recommendations})
    
    def get_all_participants(self) -> List[str]:
        """Возвращает список всех участников (взрослые + дети)"""
        participants = [adult["name"] for adult in self.adults.values()]
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
            for uid, adult_data in self.adults.items():
                if adult_data["name"] == giver:
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
                adult_names = [adult["name"] for adult in self.adults.values()]
                receiver_type = "adult" if receiver in adult_names else "child"
                # Инициализируем список назначений, если его еще нет
                if giver_user_id not in self.assignments:
                    self.assignments[giver_user_id] = []
                # Добавляем назначение в список
                self.assignments[giver_user_id].append({
                    "gives_to": receiver,
                    "type": receiver_type,
                    "giver_name": giver
                })
        
        self.assigned = True
        return True

# Глобальное хранилище (в реальном приложении лучше использовать БД)
data = SecretSantaData()

# ID администратора (можно установить через переменную окружения)
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Command /start"""
    try:
        user_id = update.effective_user.id
        name = update.effective_user.first_name or "there"
        
        welcome_text = (
            f"Hey, {name}! 🎁🎄✨\n\n"
            "This is MaNYGA — Secret Santa for people who love giving gifts... and pretending it's anonymous. 🎅🎁\n\n"
            "Here's how it works:\n\n"
            "/im_in – I'm playing 🎄\n"
            "/add_small_human – Add a kid without Telegram 🎅\n"
            "/who_are_we – See who's in the game ⛄\n"
            "/make_it_random – Assign gift pairs (admin only) 🎁\n"
            "/my_mission – Who you're gifting to 🎀\n"
            "/help – In case you forgot what's going on 🦌\n\n"
            "🎁 Budget: up to 150₪\n"
            "🎄 Goal: no stress, just good surprises ✨\n"
            "🎅 Rule: give something you'd smile at (or explain later) 🎉"
        )
        
        await update.message.reply_text(welcome_text)
    except Exception as e:
        logger.error(f"Error in start command: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try again. 🎄")
        except:
            pass


async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Register adult participant"""
    try:
        user_id = update.effective_user.id
        
        if data.assigned:
            await update.message.reply_text(
                "❌ Sorry, registration's closed — names have already been matched. 🎄🎁"
            )
            return ConversationHandler.END
        
        if user_id in data.adults:
            await update.message.reply_text(
                f"✅ You're already in — registered as: {data.get_adult_name(user_id)} 🎉"
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            "🎄 What name should we use? Nicknames are fine. 🎅✨"
        )
        return REGISTERING_ADULT
    except Exception as e:
        logger.error(f"Error in register command: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try again. 🎄")
        except:
            pass
        return ConversationHandler.END


async def register_adult_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process adult participant name"""
    try:
        user_id = update.effective_user.id
        name = update.message.text.strip()
        
        if len(name) < 2:
            await update.message.reply_text(
                "❌ That name's a bit too short. Try again? 🎄"
            )
            return REGISTERING_ADULT
        
        # Сохраняем имя во временные данные
        context.user_data['adult_name'] = name
        
        await update.message.reply_text(
            "🎅 Any recommendations for your Secret Santa? 🎁\n"
            "(What would you like? Hobbies, interests, favorite things... or just say 'surprise me!') ✨"
        )
        return ASKING_RECOMMENDATIONS
    except Exception as e:
        logger.error(f"Error in register_adult_name: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try /im_in again. 🎄")
        except:
            pass
        return ConversationHandler.END


async def process_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process recommendations for Secret Santa"""
    try:
        user_id = update.effective_user.id
        recommendations = update.message.text.strip()
        name = context.user_data.get('adult_name', '')
        
        if not name:
            await update.message.reply_text(
                "❌ Something went wrong. Please try /im_in again. 🎄"
            )
            return ConversationHandler.END
        
        # Сохраняем взрослого с рекомендациями
        data.add_adult(user_id, name, recommendations)
        
        await update.message.reply_text(
            f"✅ Welcome, {name}! You're in. 🎉🎄\n"
            f"Current tally: {len(data.adults)} adults 🎅, {len(data.children)} kids 🎁"
        )
        
        # Очищаем временные данные
        context.user_data.pop('adult_name', None)
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in process_recommendations: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try /im_in again. 🎄")
        except:
            pass
        return ConversationHandler.END


async def add_child_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start adding a child"""
    try:
        user_id = update.effective_user.id
        
        if data.assigned:
            await update.message.reply_text(
                "❌ Too late — the game's already started. 🎄🎁"
            )
            return ConversationHandler.END
        
        await update.message.reply_text(
            "🎁 What's the kid's name? We'll handle the rest. 🎅✨"
        )
        return REGISTERING_CHILD
    except Exception as e:
        logger.error(f"Error in add_child_start: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try again. 🎄")
        except:
            pass
        return ConversationHandler.END


async def register_child_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process child name"""
    try:
        name = update.message.text.strip()
        
        if len(name) < 2:
            await update.message.reply_text(
                "❌ That name's too short. Give it another shot. 🎄"
            )
            return REGISTERING_CHILD
        
        # Сохраняем имя во временные данные
        context.user_data['child_name'] = name
        
        await update.message.reply_text(
            "🎅 Any recommendations for this kid's Secret Santa? 🎁\n"
            "(What would they like? Toys, books, interests... or just say 'surprise me!') ✨"
        )
        return ASKING_CHILD_RECOMMENDATIONS
    except Exception as e:
        logger.error(f"Error in register_child_name: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try /add_small_human again. 🎄")
        except:
            pass
        return ConversationHandler.END


async def process_child_recommendations(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Process recommendations for child's Secret Santa"""
    try:
        recommendations = update.message.text.strip()
        name = context.user_data.get('child_name', '')
        
        if not name:
            await update.message.reply_text(
                "❌ Something went wrong. Please try /add_small_human again. 🎄"
            )
            return ConversationHandler.END
        
        # Автоматически назначаем текущего пользователя как опекуна
        user_id = update.effective_user.id
        data.add_child(name, user_id, recommendations)
        
        await update.message.reply_text(
            f"✅ Got it! {name} is in. 🎁🎉\n"
            f"We'll send you their assignment. 🎅\n\n"
            f"Current tally: {len(data.adults)} adults 🎄, {len(data.children)} kids 🎁"
        )
        
        # Очищаем временные данные
        context.user_data.pop('child_name', None)
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in process_child_recommendations: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try /add_small_human again. 🎄")
        except:
            pass
        return ConversationHandler.END


async def list_participants(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show list of all participants"""
    try:
        if not data.adults and not data.children:
            await update.message.reply_text("🎄 No one's joined yet. Just us, the silence, and a bot. 🎄✨")
            return
        
        text = "🎄 Here's who's playing:\n\n"
        
        if data.adults:
            text += "🎅 Adults:\n"
            for i, (uid, adult_data) in enumerate(data.adults.items(), 1):
                text += f"{i}. {adult_data['name']} 🎄\n"
            text += "\n"
        
        if data.children:
            text += "🎁 Kids:\n"
            for i, child in enumerate(data.children, 1):
                guardian_data = data.adults.get(child["guardian_id"], {})
                guardian_name = guardian_data.get("name", "Unknown") if isinstance(guardian_data, dict) else "Unknown"
                text += f"{i}. {child['name']} (added by {guardian_name}) 🎅\n"
        
        text += f"\nTotal: {len(data.adults)} adults 🎅, {len(data.children)} kids 🎁"
        
        await update.message.reply_text(text)
    except Exception as e:
        logger.error(f"Error in list_participants: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try again. 🎄")
        except:
            pass


async def assign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create Secret Santa assignments (admin only)"""
    user_id = update.effective_user.id
    
    # Check admin rights
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ This one's for the admin. You know who you are. 🎅🎄"
        )
        return
    
    if data.assigned:
        await update.message.reply_text(
            "⚠️ Assignments are already done. 🎁\n"
            "Need a reset? Use /reset (admin only). 🎄"
        )
        return
    
    total_participants = len(data.adults) + len(data.children)
    if total_participants < 2:
        await update.message.reply_text(
            "❌ Need at least 2 people to make this work. 🎅\n"
            "Otherwise, it's just... gifting to yourself. 🎁➡️🎁"
        )
        return
    
    if data.make_assignments():
        # Send assignments to all participants
        for uid, assignments_list in data.assignments.items():
            try:
                if len(assignments_list) == 1:
                    # Single assignment
                    assignment = assignments_list[0]
                    message = (
                        f"🎅🎁✨ Your Secret Santa assignment:\n\n"
                        f"You ({assignment['giver_name']}) are gifting to:\n"
                        f"🎅 {assignment['gives_to']} 🎄"
                    )
                    # Добавляем рекомендации, если получатель - взрослый
                    if assignment['type'] == "adult":
                        for adult_uid, adult_data in data.adults.items():
                            if adult_data["name"] == assignment['gives_to']:
                                recommendations = adult_data.get("recommendations", "")
                                if recommendations:
                                    message += f"\n\n💡 Tips: {recommendations}"
                                break
                    if assignment['type'] == "child":
                        # Добавляем рекомендации, если получатель - ребенок
                        for child in data.children:
                            if child["name"] == assignment['gives_to']:
                                recommendations = child.get("recommendations", "")
                                if recommendations:
                                    message += f"\n\n💡 Tips: {recommendations}"
                                break
                        message += "\n\n(This is a kid without Telegram) 🎁"
                else:
                    # Multiple assignments (adult + kid/kids)
                    message = "🎅🎁✨ Your Secret Santa assignments:\n\n"
                    for assignment in assignments_list:
                        adult_names = [adult["name"] for adult in data.adults.values()]
                        if assignment['giver_name'] in adult_names:
                            # This is an adult assignment
                            # Находим рекомендации получателя
                            receiver_recommendations = ""
                            if assignment['type'] == "adult":
                                for adult_uid, adult_data in data.adults.items():
                                    if adult_data["name"] == assignment['gives_to']:
                                        receiver_recommendations = adult_data.get("recommendations", "")
                                        break
                            
                            message += f"🎅 You ({assignment['giver_name']}) are gifting to:\n   {assignment['gives_to']} 🎄\n"
                            if receiver_recommendations:
                                message += f"   💡 Tips: {receiver_recommendations}\n"
                            message += "\n"
                        else:
                            # This is a kid assignment
                            message += f"🎁 {assignment['giver_name']} is gifting to:\n   {assignment['gives_to']} 🎁\n"
                            # Добавляем рекомендации, если получатель - ребенок
                            for child in data.children:
                                if child["name"] == assignment['gives_to']:
                                    recommendations = child.get("recommendations", "")
                                    if recommendations:
                                        message += f"   💡 Tips: {recommendations}\n"
                                    break
                            message += "\n"
                
                await context.bot.send_message(chat_id=uid, text=message)
            except Exception as e:
                logger.error(f"Error sending message to user {uid}: {e}")
        
        await update.message.reply_text(
            f"✅ Assignments sent out! 🎁🎉\n"
            f"Let the mysterious generosity begin. 🎅🎄✨\n\n"
            f"Total participants: {total_participants} 🎁"
        )
    else:
        await update.message.reply_text(
            "❌ Something went wrong during assignments. 🎄\n"
            "Try again? Or try tea first. 🎅"
        )


async def my_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's assignment"""
    try:
        user_id = update.effective_user.id
        
        if not data.assigned:
            await update.message.reply_text(
                "⏳ Assignments aren't ready yet. 🎄\n"
                "Waiting on the admin to hit the button. 🎅"
            )
            return
        
        # Get all assignments for this user
        if user_id not in data.assignments or not data.assignments[user_id]:
            await update.message.reply_text(
                "❌ You don't seem to be in the game. 🎁\n"
                "Try /im_in first. ✨"
            )
            return
        
        assignments_list = data.assignments[user_id]
        
        # Form message
        if len(assignments_list) == 1:
            # Single assignment
            assignment = assignments_list[0]
            message = (
                f"🎅🎁✨ Your Secret Santa assignment:\n\n"
                f"You ({assignment['giver_name']}) are gifting to:\n"
                f"🎅 {assignment['gives_to']} 🎄"
            )
            # Добавляем рекомендации, если получатель - взрослый
            if assignment['type'] == "adult":
                for adult_uid, adult_data in data.adults.items():
                    if adult_data["name"] == assignment['gives_to']:
                        recommendations = adult_data.get("recommendations", "")
                        if recommendations:
                            message += f"\n\n💡 Tips: {recommendations}"
                        break
            if assignment['type'] == "child":
                # Добавляем рекомендации, если получатель - ребенок
                for child in data.children:
                    if child["name"] == assignment['gives_to']:
                        recommendations = child.get("recommendations", "")
                        if recommendations:
                            message += f"\n\n💡 Tips: {recommendations}"
                        break
                message += "\n\n(This is a kid without Telegram) 🎁"
        else:
            # Multiple assignments (adult + kid/kids)
            message = "🎅🎁✨ Your Secret Santa assignments:\n\n"
            for assignment in assignments_list:
                adult_names = [adult["name"] for adult in data.adults.values()]
                if assignment['giver_name'] in adult_names:
                    # This is an adult assignment
                    message += f"🎅 You ({assignment['giver_name']}) are gifting to:\n   {assignment['gives_to']} 🎄\n"
                    # Добавляем рекомендации, если получатель - взрослый
                    if assignment['type'] == "adult":
                        for adult_uid, adult_data in data.adults.items():
                            if adult_data["name"] == assignment['gives_to']:
                                recommendations = adult_data.get("recommendations", "")
                                if recommendations:
                                    message += f"   💡 Tips: {recommendations}\n"
                                break
                    message += "\n"
                else:
                    # This is a kid assignment
                    message += f"🎁 {assignment['giver_name']} is gifting to:\n   {assignment['gives_to']} 🎁\n"
                    # Добавляем рекомендации, если получатель - ребенок
                    for child in data.children:
                        if child["name"] == assignment['gives_to']:
                            recommendations = child.get("recommendations", "")
                            if recommendations:
                                message += f"   💡 Tips: {recommendations}\n"
                            break
                    message += "\n"
        
        await update.message.reply_text(message)
    except Exception as e:
        logger.error(f"Error in my_assignment: {e}", exc_info=True)
        try:
            await update.message.reply_text("❌ Something went wrong. Please try again. 🎄")
        except:
            pass


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reset all data (admin only)"""
    user_id = update.effective_user.id
    
    if ADMIN_ID and user_id != ADMIN_ID:
        await update.message.reply_text(
            "❌ Only admins can do this. Democracy is limited here. 🎅🎄"
        )
        return
    
    data.adults.clear()
    data.children.clear()
    data.assignments.clear()
    data.assigned = False
    
    await update.message.reply_text(
        "✅ Everything's been wiped. 🎁\n"
        "Fresh start, clean slate, empty list. ✨🎄"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    await update.message.reply_text("❌ Got it. Canceled. 🎄\nSometimes giving up is also a choice. 🎅")
    return ConversationHandler.END


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    help_text = (
        "📖 Commands overview:\n\n"
        "/start – Start the bot 🎄\n"
        "/im_in – Join the game 🎅\n"
        "/add_small_human – Add a child (no Telegram needed) 🎁\n"
        "/who_are_we – View all participants ⛄\n"
        "/make_it_random – Assign gift pairs (admin only) 🎀\n"
        "/my_mission – See who you're buying for 🦌\n"
        "/reset – Reset everything (admin only) 🎄\n"
        "/help – You're here 🎅\n\n"
        "💡 Note: Kids without Telegram can still play — just register them, and their assignment will go to the adult who added them. 🎁➡️🎅"
    )
    await update.message.reply_text(help_text)


def main():
    """Start the bot"""
    # Try to get token from environment variables
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is not set in environment variables!")
        logger.error("For local run: create .env file with TELEGRAM_BOT_TOKEN=your_token")
        logger.error("For Railway: add TELEGRAM_BOT_TOKEN variable in project settings")
        return
    
    # Create application
    application = Application.builder().token(token).build()
    
    # Register adult participant
    register_handler = ConversationHandler(
        entry_points=[CommandHandler("im_in", register)],
        states={
            REGISTERING_ADULT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_adult_name)
            ],
            ASKING_RECOMMENDATIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_recommendations)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Add child
    add_child_handler = ConversationHandler(
        entry_points=[CommandHandler("add_small_human", add_child_start)],
        states={
            REGISTERING_CHILD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, register_child_name)
            ],
            ASKING_CHILD_RECOMMENDATIONS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_child_recommendations)
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Register handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(register_handler)
    application.add_handler(add_child_handler)
    application.add_handler(CommandHandler("who_are_we", list_participants))
    application.add_handler(CommandHandler("make_it_random", assign))
    application.add_handler(CommandHandler("my_mission", my_assignment))
    application.add_handler(CommandHandler("reset", reset))
    application.add_handler(CommandHandler("help", help_command))
    
    # Start the bot
    logger.info("Bot started!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

