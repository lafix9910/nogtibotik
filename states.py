"""
FSM (Finite State Machine) состояния для бота.
Используются для управления процессом записи клиента.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния для процесса записи."""
    # Выбор даты
    waiting_for_date = State()
    
    # Выбор времени
    waiting_for_time = State()
    
    # Ввод имени
    waiting_for_name = State()
    
    # Ввод номера телефона
    waiting_for_phone = State()
    
    # Подтверждение записи
    waiting_for_confirmation = State()


class AdminStates(StatesGroup):
    """Состояния для админ-панели."""
    # Главное меню админа
    admin_menu = State()
    
    # Добавление рабочего дня
    waiting_for_date_to_add = State()
    
    # Добавление временного слота
    waiting_for_slot_date = State()
    waiting_for_slot_time = State()
    
    # Удаление временного слота
    waiting_for_slot_to_remove = State()
    
    # Закрытие дня
    waiting_for_date_to_close = State()
    
    # Открытие дня
    waiting_for_date_to_open = State()
    
    # Просмотр расписания
    waiting_for_schedule_date = State()
    
    # Отмена записи клиента
    waiting_for_booking_to_cancel = State()
    waiting_for_cancel_confirmation = State()


class SubscriptionCheck(StatesGroup):
    """Состояния для проверки подписки."""
    checking = State()
    verified = State()
