"""
FSM (Finite State Machine) состояния для бота.
"""

from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    """Состояния для процесса записи."""
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_name = State()
    waiting_for_phone = State()
    waiting_for_confirmation = State()


class AdminStates(StatesGroup):
    """Состояния для админ-панели."""
    admin_menu = State()
    waiting_for_date_to_add = State()
    waiting_for_day_to_remove = State()
    waiting_for_slot_date = State()
    waiting_for_slot_time = State()
    waiting_for_slot_to_remove = State()
    waiting_for_date_to_close = State()
    waiting_for_date_to_open = State()
    waiting_for_schedule_date = State()
    waiting_for_booking_to_cancel = State()
    waiting_for_cancel_confirmation = State()


class SubscriptionCheck(StatesGroup):
    """Состояния для проверки подписки."""
    checking = State()
    verified = State()
