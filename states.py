from aiogram.fsm.state import State, StatesGroup

# Определение состояний для FSM (конечного автомата)
class TelethonAuth(StatesGroup):
    waiting_for_api_id = State()
    waiting_for_api_hash = State()
    waiting_for_phone = State()
    waiting_for_code = State()
    waiting_for_2fa = State()