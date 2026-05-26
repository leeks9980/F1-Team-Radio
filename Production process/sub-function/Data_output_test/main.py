import socket
import time
import json
import threading
import ctypes
import os

# 1. 기존 파서 모듈에서 구조체 로드 (모션과 텔레메트리 구조체가 f1_pasing.py에 존재해야 함)
from f1_pasing import (
    PacketHeader, 
    PacketSessionData, 
    PacketLapData, 
    PacketCarDamageData, 
    PacketCarStatusData,
    PacketCarTelemetryData,  # 추가됨
    PacketMotionData     # 추가됨
)

# 2. 인메모리 저장소 로드 (확장된 상태 반영)
from f1_memory import (
    update_session_state, update_lap_state, 
    update_damage_state, update_status_state, 
    update_telemetry_state, update_motion_state,
    get_latest_state_snapshot
)

from lm_context_builder import build_lm_context
from tyre_predictor import TyrePredictor

HISTORY_FILE = "race_history.jsonl"
SYSTEM_MEMORY = {"last_radio_lap": 0, "last_radio_intent": "None"}

tyre_predictor = TyrePredictor(learning_laps=3, target_future_laps=3)

# ---------------------------------------------------------
# [파일 기반 복구 로직] (기존과 유사하나 변수 확장됨)
# ---------------------------------------------------------
def initialize_predictor_from_history():
    global tyre_predictor
    if not os.path.exists(HISTORY_FILE):
        return

    print(f"📂 [시스템 부팅] 기존 주행 기록({HISTORY_FILE})을 로드하여 다차원 타이어 예측기를 초기화합니다...")
    last_read_lap = 0
    loaded_count = 0
    
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                
                payload = json.loads(line)
                lap_num = payload.get("race_context", {}).get("progress", {}).get("current_lap", 0)
                raw_wear = payload.get("raw_tyres_wear")
                raw_telemetry = payload.get("raw_telemetry")
                raw_motion = payload.get("raw_motion")
                
                if lap_num > 0 and raw_wear and raw_telemetry and raw_motion:
                    if lap_num < last_read_lap:
                        tyre_predictor.history = []
                        loaded_count = 0
                    
                    last_read_lap = lap_num
                    
                    tyre_predictor.update_lap_data(
                        lap_num=lap_num,
                        w_fl=raw_wear[0], w_fr=raw_wear[1], w_rl=raw_wear[2], w_rr=raw_wear[3],
                        t_fl=raw_telemetry['temp'][0], t_fr=raw_telemetry['temp'][1], 
                        t_rl=raw_telemetry['temp'][2], t_rr=raw_telemetry['temp'][3],
                        speed=raw_telemetry['speed'], brake=raw_telemetry['brake'], steer=raw_telemetry['steer'],
                        g_lat=raw_motion['g_lat'], g_lon=raw_motion['g_lon'], g_vert=raw_motion['g_vert']
                    )
                    loaded_count += 1
                        
        print(f"✅ 초기화 완료. {loaded_count}개의 다차원 스냅샷 복구 성공.")
    except Exception as e:
        print(f"⚠️ 기존 기록 로드 중 오류 발생: {e}")

# ---------------------------------------------------------
# [수신 스레드] 추가 패킷 해독
# ---------------------------------------------------------
def udp_listener_thread():
    UDP_IP = "127.0.0.1"
    UDP_PORT = 20777
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"📡 [수신 스레드] 포트 {UDP_PORT} 데이터 대기 중...")

    def ctype_to_dict(obj):
        if hasattr(obj, "_fields_"): return {field[0]: ctype_to_dict(getattr(obj, field[0])) for field in obj._fields_}
        elif hasattr(obj, "__len__") and not isinstance(obj, (str, bytes)): return [ctype_to_dict(item) for item in obj]
        else: return obj

    while True:
        try:
            data, _ = sock.recvfrom(2048)
            if len(data) < 29: continue

            header = PacketHeader.from_buffer_copy(data[0:29])
            packet_id = header.m_packetId
            player_idx = header.m_playerCarIndex

            if packet_id == 1:
                update_session_state(ctype_to_dict(PacketSessionData.from_buffer_copy(data)))
            elif packet_id == 2:
                packet = PacketLapData.from_buffer_copy(data)
                update_lap_state([ctype_to_dict(packet.m_lapData[i]) for i in range(22)], player_idx)
            elif packet_id == 7:
                packet = PacketCarStatusData.from_buffer_copy(data)
                update_status_state(ctype_to_dict(packet.m_carStatusData[player_idx]))
            elif packet_id == 10:
                packet = PacketCarDamageData.from_buffer_copy(data)
                update_damage_state(ctype_to_dict(packet.m_carDamageData[player_idx]))
            elif packet_id == 6:  # Telemetry 데이터
                packet = PacketCarTelemetryData.from_buffer_copy(data)
                update_telemetry_state(ctype_to_dict(packet.m_carTelemetryData[player_idx]))
            elif packet_id == 0:  # Motion 데이터
                packet = PacketMotionData.from_buffer_copy(data)
                update_motion_state(ctype_to_dict(packet.m_carMotionData[player_idx]))

        except Exception as e:
            continue

# ---------------------------------------------------------
# [메인 스레드] 복합 데이터 추출 및 파일 동기화
# ---------------------------------------------------------
def monitor_and_call_llm(interval_seconds=10):
    global SYSTEM_MEMORY, tyre_predictor
    previous_delta_front = None
    loop_count = 0
    print("🏁 [메인 스레드] Sleipnir 다차원 예측 시스템 가동 시작...")

    while True:
        time.sleep(interval_seconds)
        loop_count += 1
        snapshot = get_latest_state_snapshot()
        
        if not snapshot.get("session") or not snapshot.get("telemetry") or not snapshot.get("motion"):
            continue

        base_context = build_lm_context(snapshot)
        current_lap = base_context["race_context"]["progress"]["current_lap"]
        if current_lap == 0: continue

        trend = {}
        current_delta = base_context["gaps"]["delta_to_front"]
        if isinstance(current_delta, float) and previous_delta_front is not None:
            trend["gap_to_front_change"] = round(current_delta - previous_delta_front, 3)
        else: trend["gap_to_front_change"] = 0.0
        previous_delta_front = current_delta if isinstance(current_delta, float) else None

        # ---------------------------------------------------------
        # 14개의 복합 데이터 추출 및 주입
        # ---------------------------------------------------------
        dmg = snapshot.get("damage", {})
        tele = snapshot.get("telemetry", {})
        motion = snapshot.get("motion", {})

        tyres_wear = dmg.get('m_tyresWear', [0, 0, 0, 0])
        surface_temp = tele.get('m_tyresSurfaceTemperature', [0, 0, 0, 0])
        speed = tele.get('m_speed', 0)
        brake = tele.get('m_brake', 0)
        steer = tele.get('m_steer', 0)
        g_lat = abs(motion.get('m_gForceLateral', 0))
        g_lon = abs(motion.get('m_gForceLongitudinal', 0))
        g_vert = abs(motion.get('m_gForceVertical', 0))
        
        tyre_predictor.update_lap_data(
            lap_num=current_lap,
            w_fl=tyres_wear[0], w_fr=tyres_wear[1], w_rl=tyres_wear[2], w_rr=tyres_wear[3],
            t_fl=surface_temp[0], t_fr=surface_temp[1], t_rl=surface_temp[2], t_rr=surface_temp[3],
            speed=speed, brake=brake, steer=steer,
            g_lat=g_lat, g_lon=g_lon, g_vert=g_vert
        )
        
        prediction_result = tyre_predictor.predict(current_lap)

        llm_payload = base_context
        llm_payload["trend"] = trend
        if prediction_result: llm_payload["tyre_wear_prediction"] = prediction_result
        llm_payload["system_memory"] = SYSTEM_MEMORY
        
        # 히스토리 복구를 위한 원본 데이터 은닉 저장
        llm_payload["raw_tyres_wear"] = tyres_wear
        llm_payload["raw_telemetry"] = {"temp": surface_temp, "speed": speed, "brake": brake, "steer": steer}
        llm_payload["raw_motion"] = {"g_lat": g_lat, "g_lon": g_lon, "g_vert": g_vert}

        try:
            with open(HISTORY_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(llm_payload, ensure_ascii=False) + "\n")
        except Exception: pass

        print(f"\n--- ⏱️ [다차원 모니터링] Loop {loop_count} ---")
        print(f"📍 Lap {current_lap} | 속도: {speed}km/h | G-Force: {round(g_lat,2)}G")
        print(f"🧠 [타이어 스냅샷 누적량]: {len(tyre_predictor.history)} 데이터 수집됨")
        print("----------------------------------------")
        print(f"✅ [LLM 프롬프트 준비 완료]\n{json.dumps(llm_payload, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    initialize_predictor_from_history()
    listener = threading.Thread(target=udp_listener_thread, daemon=True)
    listener.start()
    try: monitor_and_call_llm(interval_seconds=10)
    except KeyboardInterrupt: print("\n🛑 종료.")