"""
Oбработчики сообщений и колбэков бота.
Содержит все обработчики для команд, callback-запросов и сообщений пользователей.
"""

from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from datetime import datetime
from states import BookingStates, AdminStates
from keyboards import (
    get_main_menu_keyboard, get_prices_keyboard, get_portfolio_keyboard,
    get_subscription_keyboard, create_calendar_keyboard, create_time_keyboard,
    get_booking_confirmation_keyboard, get_cancel_confirmation_keyboard,
    get_admin_keyboard, get_admin_dates_keyboard, get_admin_slots_keyboard,
    get_admin_bookings_keybook
)
from database import db
from utils import check_subscription, schedule_reminder, cancel_reminder, format_date_russian
import config

# Планировщик будет установлен при инициализации бота
scheduler = None

def set_scheduler(s):
    global scheduler
    scheduler = s


router = Router()


@router.message(F.text == "/start")
async def cmd_start(message: Message, bot: Bot):
    """Обработчик команды /start."""
    user_id = message.from_user.id
    has_booking = await db.has_active_booking(user_id)
    
    await message.answer(
        f"Добро пожаловать к мастеру маникюра {config.MASTER_NAME}! \n\n"
        f"Выберите действие из меню ниже:",
        reply_markup=get_main_menu_keyboard(has_booking)
    )


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery, bot: Bot):
    """Возврат в главное меню."""
    user_id = callback.from_user.id
    has_booking = await db.has_active_booking(user_id)
    
    await callback.message.edit_text(
        f"Добро пожаловать к мастеру маникюра {config.MASTER_NAME}! \n\n"
        f"Выберите действие из меню ниже:",
        reply_markup=get_main_menu_keyboard(has_booking)
    )
    await callback.answer()


@router.callback_query(F.data == "prices")
async def show_prices(callback: CallbackQuery, bot: Bot):
    """Показ прайсов."""
    await callback.message.edit_text(
        "<b>ПРАЙС-ЛИСТ</b> \n\n"
        "- <b>Френч</b> - 1000 \n"
        "- <b>Квадрат</b> - 500",
        reply_markup=get_prices_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "portfolio")
async def show_portfolio(callback: CallbackQuery, bot: Bot):
    """Показ портфолио."""
    await callback.message.edit_text(
        "<b>Портфолио работ</b>\n\n"
        "Нажмите на кнопку ниже, чтобы посмотреть наши работы:",
        reply_markup=get_portfolio_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "check_subscription")
async def check_user_subscription(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Проверка подписки пользователя."""
    user_id = callback.from_user.id
    
    is_subscribed = await check_subscription(bot, user_id)
    user_has_booking = await db.has_active_booking(user_id)
    
    if is_subscribed:
        await state.update_data(subscription_verified=True)
        await callback.message.edit_text(
            "<b>Подписка подтверждена!</b>\n\n"
            "Теперь вы можете записаться на приём.",
            reply_markup=get_main_menu_keyboard(user_has_booking),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "<b>Вы не подписаны на канал</b>\n\n"
            "Для записи необходимо подписаться на канал.",
            reply_markup=get_subscription_keyboard(),
            parse_mode="HTML"
        )
    
    await callback.answer()


@router.callback_query(F.data == "booking")
async def start_booking(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начало процесса записи."""
    user_id = callback.from_user.id
    
    # Проверка подписки (если канал настроен)
    is_subscribed = True
    if config.CHANNEL_ID:
        is_subscribed = await check_subscription(bot, user_id)
        if not is_subscribed:
            await callback.message.edit_text(
                "<b>Вы не подписаны на канал</b>\n\n"
                "Для записи необходимо подписаться на канал.",
                reply_markup=get_subscription_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer()
            return
    
    has_booking = await db.has_active_booking(user_id)
    if has_booking:
        await callback.message.edit_text(
            "<b>У вас уже есть активная запись!</b>\n\n"
            "Вы можете отменить её и создать новую.",
            reply_markup=get_main_menu_keyboard(True),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    dates = await db.get_available_dates()
    
    await callback.message.edit_text(
        "<b>Выберите дату</b>\n\n"
        "Доступные даты на ближайший месяц:",
        reply_markup=create_calendar_keyboard(dates),
        parse_mode="HTML"
    )
    
    await state.set_state(BookingStates.waiting_for_date)
    await callback.answer()


@router.callback_query(F.data == "back_to_dates")
async def back_to_dates(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Возврат к выбору даты."""
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_time:
        await callback.answer()
        return
    
    dates = await db.get_available_dates()
    
    await callback.message.edit_text(
        "<b>Выберите дату</b>\n\n"
        "Доступные даты на ближайший месяц:",
        reply_markup=create_calendar_keyboard(dates),
        parse_mode="HTML"
    )
    
    await state.set_state(BookingStates.waiting_for_date)
    await callback.answer()


@router.callback_query(F.data.startswith("date_"))
async def select_date(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Выбор даты."""
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_date:
        await callback.answer()
        return
    
    date = callback.data.replace("date_", "")
    
    is_closed = await db.is_date_closed(date)
    if is_closed:
        await callback.answer("Этот день закрыт для записи", show_alert=True)
        return
    
    slots = await db.get_available_slots(date)
    if not slots:
        await callback.answer("Нет доступных слотов на этот день", show_alert=True)
        return
    
    await state.update_data(selected_date=date)
    
    await callback.message.edit_text(
        f"<b>Выбрана дата:</b> {format_date_russian(date)}\n\n"
        f"<b>Выберите время</b>:",
        reply_markup=create_time_keyboard(slots, date),
        parse_mode="HTML"
    )
    
    await state.set_state(BookingStates.waiting_for_time)
    await callback.answer()


@router.callback_query(F.data.startswith("time_"))
async def select_time(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Выбор времени."""
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_time:
        await callback.answer()
        return
    
    data = callback.data.replace("time_", "")
    parts = data.split("_")
    date = parts[0]
    time = parts[1]
    
    await state.update_data(selected_time=time)
    
    await callback.message.edit_text(
        f"<b>Дата:</b> {format_date_russian(date)}\n"
        f"<b>Время:</b> {time}\n\n"
        f"Пожалуйста, введите ваше <b>имя</b>:",
        parse_mode="HTML"
    )
    
    await state.set_state(BookingStates.waiting_for_name)
    await callback.answer()


@router.message(BookingStates.waiting_for_name)
async def get_name(message: Message, state: FSMContext):
    """Получение имени."""
    name = message.text.strip()
    
    if len(name) < 2:
        await message.answer("Имя слишком короткое. Пожалуйста, введите корректное имя:")
        return
    
    await state.update_data(user_name=name)
    
    await message.answer(
        f"<b>Имя:</b> {name}\n\n"
        f"Теперь введите ваш <b>номер телефона</b>:",
        parse_mode="HTML"
    )
    
    await state.set_state(BookingStates.waiting_for_phone)


@router.message(BookingStates.waiting_for_phone)
async def get_phone(message: Message, state: FSMContext):
    """Получение номера телефона."""
    phone = message.text.strip()
    
    if len(phone) < 5:
        await message.answer("Номер телефона слишком короткий. Пожалуйста, введите корректный номер:")
        return
    
    await state.update_data(user_phone=phone)
    
    data = await state.get_data()
    date = data["selected_date"]
    time = data["selected_time"]
    name = data["user_name"]
    
    await message.answer(
        f"<b>Проверьте данные записи:</b>\n\n"
        f"<b>Дата:</b> {format_date_russian(date)}\n"
        f"<b>Время:</b> {time}\n"
        f"<b>Имя:</b> {name}\n"
        f"<b>Телефон:</b> {phone}\n\n"
        f"Подтвердите запись:",
        reply_markup=get_booking_confirmation_keyboard(date, time),
        parse_mode="HTML"
    )
    
    await state.set_state(BookingStates.waiting_for_confirmation)


@router.callback_query(F.data.startswith("confirm_"))
async def confirm_booking(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждение записи."""
    current_state = await state.get_state()
    if current_state != BookingStates.waiting_for_confirmation:
        await callback.answer()
        return
    
    data = callback.data.replace("confirm_", "")
    parts = data.split("_")
    date = parts[0]
    time = parts[1]
    
    user_data = await state.get_data()
    user_id = callback.from_user.id
    user_name = user_data["user_name"]
    phone = user_data["user_phone"]
    
    success = await db.create_booking(user_id, user_name, phone, date, time)
    
    if not success:
        await callback.message.edit_text(
            "<b>Ошибка!</b>\n\n"
            "Это время уже занято. Пожалуйста, выберите другое.",
            reply_markup=get_main_menu_keyboard(True),
            parse_mode="HTML"
        )
        await state.clear()
        await callback.answer()
        return
    
    booking = await db.get_booking(user_id)
    if booking:
        booking_id = booking[0]
        if scheduler:
            await schedule_reminder(bot, user_id, date, time, booking_id, scheduler)
    
    admin_message = (
        f"<b>Новая запись!</b>\n\n"
        f"<b>Клиент:</b> {user_name}\n"
        f"<b>Телефон:</b> {phone}\n"
        f"<b>Дата:</b> {format_date_russian(date)}\n"
        f"<b>Время:</b> {time}\n"
        f"<b>TG ID:</b> {user_id}"
    )
    await bot.send_message(config.ADMIN_ID, admin_message, parse_mode="HTML")
    
    channel_message = (
        f"<b>Расписание</b>\n\n"
        f"<b>Дата:</b> {format_date_russian(date)}\n"
        f"<b>Время:</b> {time}\n"
        f"<b>Клиент:</b> {user_name}"
    )
    try:
        await bot.send_message(config.SCHEDULE_CHANNEL_ID, channel_message, parse_mode="HTML")
    except Exception:
        pass
    
    await callback.message.edit_text(
        f"<b>Запись подтверждена!</b>\n\n"
        f"<b>Дата:</b> {format_date_russian(date)}\n"
        f"<b>Время:</b> {time}\n"
        f"<b>Имя:</b> {user_name}\n"
        f"<b>Телефон:</b> {phone}\n\n"
        f"Мы ждём вас! ",
        reply_markup=get_main_menu_keyboard(True),
        parse_mode="HTML"
    )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "cancel_booking")
async def cancel_booking_start(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Начало отмены записи."""
    user_id = callback.from_user.id
    
    booking = await db.get_booking(user_id)
    
    if not booking:
        await callback.message.edit_text(
            "<b>У вас нет активной записи!</b>",
            reply_markup=get_main_menu_keyboard(True),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    booking_id, user_name, phone, date, time, created_at = booking
    
    await callback.message.edit_text(
        f"<b>Вы уверены, что хотите отменить запись?</b>\n\n"
        f"<b>Дата:</b> {format_date_russian(date)}\n"
        f"<b>Время:</b> {time}\n"
        f"<b>Имя:</b> {user_name}",
        reply_markup=get_cancel_confirmation_keyboard(booking_id),
        parse_mode="HTML"
    )
    
    await state.update_data(cancel_booking_id=booking_id)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_cancel_"))
async def confirm_cancel_booking(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждение отмены записи."""
    booking_id = int(callback.data.replace("confirm_cancel_", ""))
    user_id = callback.from_user.id
    
    success = await db.cancel_booking(user_id, booking_id)
    
    if success:
        job_id = f"reminder_{booking_id}_{user_id}"
        if scheduler:
            await cancel_reminder(job_id, scheduler)
        
        await callback.message.edit_text(
            "<b>Запись отменена!</b>\n\n"
            "Вы можете создать новую запись.",
            reply_markup=get_main_menu_keyboard(True),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "<b>Ошибка при отмене записи.</b>",
            reply_markup=get_main_menu_keyboard(True),
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()


@router.message(F.text == "/admin")
async def cmd_admin(message: Message, bot: Bot, state: FSMContext):
    """Команда админ-панели."""
    if message.from_user.id != config.ADMIN_ID:
        await message.answer("У вас нет доступа к админ-панели.")
        return
    
    await message.answer(
        "<b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "admin_menu")
async def admin_menu(callback: CallbackQuery, bot: Bot):
    """Меню админ-панели."""
    await callback.message.edit_text(
        "<b>Админ-панель</b>\n\n"
        "Выберите действие:",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "admin_add_date")
async def admin_add_date(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Добавление рабочего дня."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Добавление рабочего дня</b>\n\n"
        "Введите дату в формате ГГГГ-ММ-ДД (например, 2024-12-31):",
        parse_mode="HTML"
    )
    await state.set_state(AdminStates.waiting_for_date_to_add)
    await callback.answer()


@router.message()
async def process_add_date(message: Message, state: FSMContext, bot: Bot):
    """Обработка добавления рабочего дня."""
    current_state = await state.get_state()
    if current_state != AdminStates.waiting_for_date_to_add:
        return
    
    date_str = message.text.strip()
    
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        date = date_obj.date().isoformat()
    except ValueError:
        await message.answer(
            "Неверный формат даты. Введите дату в формате ГГГГ-ММ-ДД:",
            reply_markup=get_admin_keyboard()
        )
        return
    
    await db.add_single_work_day(date)
    
    await message.answer(
        f"<b>Рабочий день добавлен!</b>\n\n"
        f"Дата: {format_date_russian(date)}\n"
        f"Добавлены слоты: 9:00 - 18:00",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "admin_remove_day")
async def admin_remove_day(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Удаление рабочего дня."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    dates = await db.get_all_dates()
    
    if not dates:
        await callback.message.edit_text(
            "Нет рабочих дней.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Удаление рабочего дня</b>\n\n"
        "Выберите дату для удаления:",
        reply_markup=get_admin_dates_keyboard(dates, "confirm_remove_day"),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_day_to_remove)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_remove_day_"))
async def confirm_remove_day(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждение удаления рабочего дня."""
    date = callback.data.replace("confirm_remove_day_", "")
    
    await db.remove_single_work_day(date)
    
    await callback.message.edit_text(
        f"<b>Рабочий день удалён!</b>\n\n"
        f"Дата: {format_date_russian(date)}",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()


@router.callback_query(F.data == "admin_add_slot")
async def admin_add_slot(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Добавление временного слота."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    dates = await db.get_all_dates()
    
    if not dates:
        await callback.message.edit_text(
            "Нет рабочих дней.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Добавление временного слота</b>\n\n"
        "Выберите дату:",
        reply_markup=get_admin_dates_keyboard(dates, "admin_slot_date"),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_slot_date)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_slot_date_"))
async def admin_select_slot_date(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Выбор даты для добавления слота."""
    current_state = await state.get_state()
    if current_state != AdminStates.waiting_for_slot_date:
        await callback.answer("Сначала выберите действие в админ-панели", show_alert=True)
        return
    
    date = callback.data.replace("admin_slot_date_", "")
    
    await state.update_data(slot_date=date)
    
    await callback.message.edit_text(
        f"<b>Дата:</b> {format_date_russian(date)}\n\n"
        f"Введите время в формате ЧЧ:ММ (например, 14:30):",
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_slot_time)
    await callback.answer()


@router.message()
async def process_add_slot(message: Message, state: FSMContext, bot: Bot):
    """Обработка добавления временного слота."""
    current_state = await state.get_state()
    if current_state != AdminStates.waiting_for_slot_time:
        return
    
    time = message.text.strip()
    
    try:
        datetime.strptime(time, "%H:%M")
    except ValueError:
        await message.answer(
            "Неверный формат времени. Введите время в формате ЧЧ:ММ:",
            reply_markup=get_admin_keyboard()
        )
        return
    
    data = await state.get_data()
    date = data["slot_date"]
    
    success = await db.add_time_slot(date, time)
    
    if success:
        await message.answer(
            f"<b>Временной слот добавлен!</b>\n\n"
            f"Дата: {format_date_russian(date)}\n"
            f"Время: {time}",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await message.answer(
            "<b>Этот слот уже существует.</b>",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    
    await state.set_state(AdminStates.admin_menu)


@router.callback_query(F.data == "admin_remove_slot")
async def admin_remove_slot(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Удаление временного слота."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    dates = await db.get_available_dates()
    
    if not dates:
        await callback.message.edit_text(
            "Нет доступных дат.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Удаление временного слота</b>\n\n"
        "Выберите дату:",
        reply_markup=get_admin_dates_keyboard(dates, "admin_remove_slot_date"),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_slot_to_remove)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_remove_slot_date_"))
async def admin_select_remove_slot_date(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Выбор даты для удаления слота."""
    current_state = await state.get_state()
    if current_state != AdminStates.waiting_for_slot_to_remove:
        await callback.answer()
        return
    
    date = callback.data.replace("admin_remove_slot_date_", "")
    
    slots = await db.get_all_slots(date)
    
    if not slots:
        await callback.message.edit_text(
            "Нет слотов на эту дату.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await state.update_data(remove_slot_date=date)
    
    await callback.message.edit_text(
        f"<b>Дата:</b> {format_date_russian(date)}\n\n"
        f"<b>Выберите слот для удаления</b>:",
        reply_markup=get_admin_slots_keyboard(slots, date, "confirm_remove_slot"),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_remove_slot_"))
async def confirm_remove_slot(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждение удаления слота."""
    data = callback.data.replace("confirm_remove_slot_", "")
    parts = data.split("_")
    date = parts[0]
    time = parts[1]
    
    success = await db.remove_time_slot(date, time)
    
    if success:
        await callback.message.edit_text(
            f"<b>Слот удалён!</b>\n\n"
            f"Дата: {format_date_russian(date)}\n"
            f"Время: {time}",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    else:
        await callback.message.edit_text(
            "Не удалось удалить слот.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
    
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()


@router.callback_query(F.data == "admin_close_day")
async def admin_close_day(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Закрытие дня."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    dates = await db.get_available_dates()
    
    if not dates:
        await callback.message.edit_text(
            "Нет доступных дат.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Закрытие дня</b>\n\n"
        "Выберите дату для закрытия:",
        reply_markup=get_admin_dates_keyboard(dates, "confirm_close_day"),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_date_to_close)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_close_day_"))
async def confirm_close_day(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждение закрытия дня."""
    date = callback.data.replace("confirm_close_day_", "")
    
    await db.close_day(date)
    
    await callback.message.edit_text(
        f"<b>День закрыт!</b>\n\n"
        f"Дата: {format_date_russian(date)}",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()


@router.callback_query(F.data == "admin_open_day")
async def admin_open_day(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Открытие дня."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    dates = await db.get_available_dates()
    
    if not dates:
        await callback.message.edit_text(
            "Нет доступных дат.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Открытие дня</b>\n\n"
        "Выберите дату для открытия:",
        reply_markup=get_admin_dates_keyboard(dates, "confirm_open_day"),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_date_to_open)
    await callback.answer()


@router.callback_query(F.data.startswith("confirm_open_day_"))
async def confirm_open_day(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждение открытия дня."""
    date = callback.data.replace("confirm_open_day_", "")
    
    await db.open_day(date)
    
    await callback.message.edit_text(
        f"<b>День открыт!</b>\n\n"
        f"Дата: {format_date_russian(date)}",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()


@router.callback_query(F.data == "admin_view_schedule")
async def admin_view_schedule(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Просмотр расписания."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    dates = await db.get_available_dates()
    
    if not dates:
        await callback.message.edit_text(
            "Нет доступных дат.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Просмотр расписания</b>\n\n"
        "Выберите дату:",
        reply_markup=get_admin_dates_keyboard(dates, "view_schedule_date"),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_schedule_date)
    await callback.answer()


@router.callback_query(F.data.startswith("view_schedule_date_"))
async def view_schedule(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Просмотр расписания на дату."""
    date = callback.data.replace("view_schedule_date_", "")
    
    bookings = await db.get_all_bookings(date)
    slots = await db.get_all_slots(date)
    
    message = f"<b>Расписание на {format_date_russian(date)}</b>\n\n"
    
    if slots:
        message += "<b>Все слоты:</b>\n"
        for time, is_available in slots:
            status = "Свободно" if is_available else "Занято"
            message += f"- {time} - {status}\n"
    
    if bookings:
        message += "\n<b>Записи:</b>\n"
        for booking in bookings:
            _, _, user_name, phone, _, time, _ = booking
            message += f"- {time} - {user_name} ({phone})\n"
    else:
        message += "\n<b>Записей пока нет.</b>"
    
    await callback.message.edit_text(
        message,
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()


@router.callback_query(F.data == "admin_cancel_booking")
async def admin_cancel_booking(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Отмена записи клиента."""
    current_state = await state.get_state()
    if current_state != AdminStates.admin_menu:
        await callback.answer()
        return
    
    bookings = await db.get_all_bookings()
    
    if not bookings:
        await callback.message.edit_text(
            "Нет активных записей.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    await callback.message.edit_text(
        "<b>Отмена записи клиента</b>\n\n"
        "Выберите запись для отмены:",
        reply_markup=get_admin_bookings_keybook(bookings, "admin_confirm_cancel"),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.waiting_for_booking_to_cancel)
    await callback.answer()


@router.callback_query(F.data.startswith("admin_confirm_cancel_"))
async def admin_confirm_cancel(callback: CallbackQuery, bot: Bot, state: FSMContext):
    """Подтверждение отмены записи админом."""
    booking_id = int(callback.data.replace("admin_confirm_cancel_", ""))
    
    bookings = await db.get_all_bookings()
    booking = next((b for b in bookings if b[0] == booking_id), None)
    
    if not booking:
        await callback.message.edit_text(
            "Запись не найдена.",
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        return
    
    _, user_id, user_name, phone, date, time, _ = booking
    
    await db.cancel_booking(user_id, booking_id)
    
    job_id = f"reminder_{booking_id}_{user_id}"
    if scheduler:
        await cancel_reminder(job_id, scheduler)
    
    try:
        await bot.send_message(
            user_id,
            f"<b>Ваша запись была отменена администратором.</b>\n\n"
            f"Дата: {format_date_russian(date)}\n"
            f"Время: {time}",
            parse_mode="HTML"
        )
    except Exception:
        pass
    
    await callback.message.edit_text(
        f"<b>Запись отменена!</b>\n\n"
        f"Клиент: {user_name}\n"
        f"Дата: {format_date_russian(date)}\n"
        f"Время: {time}",
        reply_markup=get_admin_keyboard(),
        parse_mode="HTML"
    )
    
    await state.set_state(AdminStates.admin_menu)
    await callback.answer()
