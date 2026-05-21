import threading
import copy

LATEST_PACKET_STATE = {
    "session": {},
    "lap": {},
    "damage": {},
    "status": {}
}

state_lock = threading.Lock()

def update_session_state(session_dict):
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["session"] = session_dict

def update_lap_state(lap_data_list, player_idx):
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["lap"] = {
            "my_data": lap_data_list[player_idx],
            "all_cars": lap_data_list
        }

def update_damage_state(damage_dict):
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["damage"] = damage_dict

def update_status_state(status_dict):
    global LATEST_PACKET_STATE
    with state_lock:
        LATEST_PACKET_STATE["status"] = status_dict

def get_latest_state_snapshot():
    with state_lock:
        return copy.deepcopy(LATEST_PACKET_STATE)