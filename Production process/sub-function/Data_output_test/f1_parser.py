# f1_parser.py
import threading

# 메모리 폭발을 방지하는 핵심: 리스트에 쌓지 않고 '현재 상태'만 덮어쓰는 글로벌 변수
LATEST_PACKET_STATE = {
    "session": {},
    "lap": {},
    "damage": {},
    "status": {}
}

# 스레드 충돌 방지 락
state_lock = threading.Lock()

def update_session_state(packet_data):
    """Session 패킷 수신 시 호출"""
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["session"] = packet_data

def update_lap_state(lap_data_list, player_idx):
    """Lap 패킷 수신 시 호출"""
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["lap"] = {
            "my_data": lap_data_list[player_idx],
            "all_cars": lap_data_list # 델타 타임 계산을 위해 전체 차량 정보 유지
        }

def update_damage_state(damage_dict):
    """Damage 패킷 수신 시 호출"""
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["damage"] = damage_dict

def update_status_state(status_dict):
    """Status 패킷 수신 시 호출"""
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["status"] = status_dict

def get_latest_state_snapshot():
    """다른 모듈(context_builder)에서 현재 상태를 안전하게 복사해 갈 때 사용"""
    with state_lock:
        return LATEST_PACKET_STATE.copy()