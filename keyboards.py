"""
Модуль клавиатур бота.
Содержит все клавиатуры: inline-кнопки и reply-кнопки.
"""

from datetime import datetime
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from typing import List, Tuple
import config


def get_main_menu_keyboard(has_booking: bool = False) -> InlineKeyboardMarkup:
    """Главное меню бота."""
    buttons = [
        [InlineKeyboardButton(text="📅 Записаться", callback_data="booking")],
    ]
    
    if has_booking:
        buttons.append([InlineKeyboardButton(text="❌ Отменить запись", callback_data="cancel_booking")])
    
    buttons.extend([
        [InlineKeyboardButton(text="💰 Прайсы", callback_data="prices")],
        [InlineKeyboardButton(text="🖼️ Портфолио", callback_data="portfolio")],
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_prices_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для прайсов."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])


def get_portfolio_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура для портфолио."""
    portfolio_url = config.PORTFOLIO_LINK if hasattr(config, 'PORTFOLIO_LINK') else "https://t.me/your_portfolio_channel"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Смотреть портфолио", url=portfolio_url)],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])


def get_subscription_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура проверки подписки."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Подписаться", url=config.CHANNEL_LINK)],
        [InlineKeyboardButton(text="🔄 Проверить подписку", callback_data="check_subscription")]
    ])


def create_calendar_keyboard(dates: List[str], month_year: str = None) -> InlineKeyboardMarkup:
    """Создание календаря из доступных дат."""
    if not dates:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    
    for i, date in enumerate(dates):
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        btn = InlineKeyboardButton(
            text=f"{date_obj.day}",
            callback_data=f"date_{date}"
        )
        row.append(btn)

        if (i + 1) % 7 == 0:
            keyboard.inline_keyboard.append(row)
            row = []

    if row:
        keyboard.inline_keyboard.append(row)

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
    ])

    return keyboard


def create_time_keyboard(times: List[str], date: str) -> InlineKeyboardMarkup:
    """Создание клавиатуры с временными слотами."""
    if not times:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад к датам", callback_data="back_to_dates")]
        ])

    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    row = []
    
    for i, time in enumerate(times):
        btn = InlineKeyboardButton(
            text=time,
            callback_data=f"time_{date}_{time}"
        )
        row.append(btn)

        if (i + 1) % 2 == 0:
            keyboard.inline_keyboard.append(row)
            row = []

    if row:
        keyboard.inline_keyboard.append(row)

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад к датам", callback_data="back_to_dates")
    ])

    return keyboard


def get_booking_confirmation_keyboard(date: str, time: str) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения записи."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_{date}_{time}"),
            InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_booking")
        ]
    ])


def get_cancel_confirmation_keyboard(booking_id: int) -> InlineKeyboardMarkup:
    """Клавиатура подтверждения отмены."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Да, отменить", callback_data=f"confirm_cancel_{booking_id}"),
            InlineKeyboardButton(text="❌ Нет", callback_data="back_to_menu")
        ]
    ])


def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Админ-панель."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 Добавить рабочий день", callback_data="admin_add_date")],
        [InlineKeyboardButton(text="⏰ Добавить временной слот", callback_data="admin_add_slot")],
        [InlineKeyboardButton(text="🗑️ Удалить временной слот", callback_data="admin_remove_slot")],
        [InlineKeyboardButton(text="🔒 Закрыть день", callback_data="admin_close_day")],
        [InlineKeyboardButton(text="🔓 Открыть день", callback_data="admin_open_day")],
        [InlineKeyboardButton(text="📋 Просмотреть расписание", callback_data="admin_view_schedule")],
        [InlineKeyboardButton(text="❌ Отменить запись клиента", callback_data="admin_cancel_booking")],
        [InlineKeyboardButton(text="🔙 Выход", callback_data="back_to_menu")]
    ])


def get_admin_dates_keyboard(dates: List[str], action: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора даты для админа."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for date in dates:
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        btn = InlineKeyboardButton(
            text=f"{date_obj.strftime('%d.%m.%Y')}",
            callback_data=f"{action}_{date}"
        )
        keyboard.inline_keyboard.append([btn])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    ])

    return keyboard


def get_admin_slots_keyboard(slots: List[Tuple[str, int]], date: str, action: str) -> InlineKeyboardMarkup:
    """Клавиатура выбора временного слота для админа."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for time, is_available in slots:
        status = "✅" if is_available else "❌"
        btn = InlineKeyboardButton(
            text=f"{time} {status}",
            callback_data=f"{action}_{date}_{time}"
        )
        keyboard.inline_keyboard.append([btn])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    ])

    return keyboard


def get_time_input_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура ввода времени."""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_menu")]
    ])


def get_admin_bookings_keybook(bookings: List[Tuple], action: str = "admin_cancel_booking") -> InlineKeyboardMarkup:
    """Клавиатура выбора записи для админа."""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])

    for booking in bookings:
        booking_id, user_id, user_name, phone, date, time, _ = booking
        btn_text = f"{date} {time} - {user_name}"
        btn = InlineKeyboardButton(
            text=btn_text,
            callback_data=f"{action}_{booking_id}"
        )
        keyboard.inline_keyboard.append([btn])

    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="admin_menu")
    ])

    return keyboard
