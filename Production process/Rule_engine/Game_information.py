import socket
import time
import json
import threading
import ctypes
import os

target_dir = os.path.abspath("F1_Team_Radio\Production process\Operating part_test\Data_output_test")

# 1. 기존 파서 모듈에서 구조체 로드
from Data_output_test import f1_pasing

# 2. 인메모리 저장소 로드
from Data_output_test import f1_memory

from Data_output_test import lm_context_builder 
from Data_output_test import tyre_predictor 

HISTORY_FILE = "race_history.jsonl"
RULE_ENGINE_FILE = "Rule engine.json"
SYSTEM_MEMORY = {"last_radio_lap": 0, "last_radio_intent": "None"}

tyre_predictor = tyre_predictor.TyrePredictor(learning_laps=3, target_future_laps=3)
previous_delta_front = None
rules_cache = []

# ---------------------------------------------------------
# [룰 엔진 로드 및 평가 함수 추가]
# ---------------------------------------------------------
def load_rules():
    global rules_cache
    if os.path.exists(RULE_ENGINE_FILE):
        try:
            with open(RULE_ENGINE_FILE, "r", encoding="utf-8") as f:
                rules_cache = json.load(f)
            print(f"✅ 룰 엔진({RULE_ENGINE_FILE}) 로드 완료.")
        except Exception as e:
            print(f"⚠️ 룰 엔진 로드 실패: {e}")
    else:
        print(f"⚠️ {RULE_ENGINE_FILE} 파일을 찾을 수 없습니다.")

# 부팅 시 룰 엔진 로드
load_rules()

def evaluate_rules(context):
    triggered_terms = []
    for rule in rules_cache:
        term = rule.get("term")
        conditions = rule.get("condition", {})
        logic = rule.get("logic", "AND").upper()
        
        match_results = []
        for key, expected_val_str in conditions.items():
            actual_val = context.get(key)
            if actual_val is None:
                match_results.append(False)
                continue
            
            expected_val_str = str(expected_val_str).strip()
            
            try:
                if expected_val_str.lower() == "true":
                    match_results.append(bool(actual_val) == True)
                elif expected_val_str.lower() == "false":
                    match_results.append(bool(actual_val) == False)
                elif expected_val_str.startswith(">="):
                    match_results.append(float(actual_val) >= float(expected_val_str[2:]))
                elif expected_val_str.startswith("<="):
                    match_results.append(float(actual_val) <= float(expected_val_str[2:]))
                elif expected_val_str.startswith(">"):
                    match_results.append(float(actual_val) > float(expected_val_str[1:]))
                elif expected_val_str.startswith("<"):
                    match_results.append(float(actual_val) < float(expected_val_str[1:]))
                else:
                    # 일치 여부 확인 (문자열 포함)
                    match_results.append(str(actual_val).lower() == expected_val_str.lower())
            except ValueError:
                match_results.append(False)
                
        if logic == "OR":
            rule_matched = any(match_results) if match_results else False
        else: # 기본값 AND
            rule_matched = all(match_results) if match_results else False
            
        if rule_matched:
            triggered_terms.append(term)
            
    return triggered_terms

# ---------------------------------------------------------
# [파일 기반 복구 로직]
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
                    
                    # 하위 호환성을 위해 표면 온도 추출 확인
                    surf_temp = raw_telemetry.get('tyre_surface_temp', raw_telemetry.get('temp', [0,0,0,0]))
                    
                    tyre_predictor.update_lap_data(
                        lap_num=lap_num,
                        w_fl=raw_wear[0], w_fr=raw_wear[1], w_rl=raw_wear[2], w_rr=raw_wear[3],
                        t_fl=surf_temp[0], t_fr=surf_temp[1], t_rl=surf_temp[2], t_rr=surf_temp[3],
                        speed=raw_telemetry['speed'], brake=raw_telemetry['brake'], steer=raw_telemetry['steer'],
                        g_lat=raw_motion['g_lat'], g_lon=raw_motion['g_lon'], g_vert=raw_motion['g_vert']
                    )
                    loaded_count += 1
                        
        print(f"✅ 초기화 완료. {loaded_count}개의 다차원 스냅샷 복구 성공.")
    except Exception as e:
        print(f"⚠️ 기존 기록 로드 중 오류 발생: {e}")

# ---------------------------------------------------------
# [수신 스레드] 타 차량 정보 및 확장 필드 저장을 위한 파싱 보완
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
            data, _ = sock.recvfrom(4096)
            if len(data) < 29: continue

            header = f1_pasing.PacketHeader.from_buffer_copy(data[0:29])
            packet_id = header.m_packetId
            player_idx = header.m_playerCarIndex

            if packet_id == 1: # Session
                f1_memory.update_session_state(ctype_to_dict(f1_pasing.PacketSessionData.from_buffer_copy(data)))
                
            elif packet_id == 2: # Lap Data
                packet = f1_pasing.PacketLapData.from_buffer_copy(data)
                f1_memory.update_lap_state([ctype_to_dict(packet.m_lapData[i]) for i in range(22)], player_idx)
                
            elif packet_id == 7: # Car Status
                packet = f1_pasing.PacketCarStatusData.from_buffer_copy(data)
                status_dict = ctype_to_dict(packet.m_carStatusData[player_idx])
                status_dict["all_status"] = [ctype_to_dict(packet.m_carStatusData[i]) for i in range(22)]
                f1_memory.update_status_state(status_dict)
                
            elif packet_id == 10: # Damage
                packet = f1_pasing.PacketCarDamageData.from_buffer_copy(data)
                f1_memory.update_damage_state(ctype_to_dict(packet.m_carDamageData[player_idx]))
                
            elif packet_id == 6:  # Telemetry 데이터 확장
                packet = f1_pasing.PacketCarTelemetryData.from_buffer_copy(data)
                f1_memory.update_telemetry_state(ctype_to_dict(packet.m_carTelemetryData[player_idx]))
                
            elif packet_id == 0:  # Motion 데이터
                packet = f1_pasing.PacketMotionData.from_buffer_copy(data)
                f1_memory.update_motion_state(ctype_to_dict(packet.m_carMotionData[player_idx]))

        except Exception as e:
            continue

# ---------------------------------------------------------
# [데이터 추출 함수] 유저 입력 시점에 호출되어 현재 상태 반환
# ---------------------------------------------------------
def get_telemetry_data():
    global SYSTEM_MEMORY, tyre_predictor, previous_delta_front, rules_cache
    
    snapshot = f1_memory.get_latest_state_snapshot()
    
    # 필수 패킷 수집 상태 체크
    if not snapshot.get("session") or not snapshot.get("telemetry") or not snapshot.get("motion") or not snapshot.get("status"):
        return "아직 충분한 텔레메트리 데이터가 수집되지 않았습니다."

    base_context = lm_context_builder.build_lm_context(snapshot)
    current_lap = base_context["race_context"]["progress"]["current_lap"]
    
    if current_lap == 0: 
        return "레이스가 아직 시작되지 않았습니다."

    trend = {}
    current_delta = base_context.get("gaps", {}).get("delta_to_front", 999.0)
    delta_to_behind = base_context.get("gaps", {}).get("delta_to_behind", 999.0)

    if isinstance(current_delta, float) and previous_delta_front is not None:
        trend["gap_to_front_change"] = round(current_delta - previous_delta_front, 3)
    else: 
        trend["gap_to_front_change"] = 0.0
    previous_delta_front = current_delta if isinstance(current_delta, float) else None

    # 확장 패킷 데이터 추출 및 머신러닝 데이터 주입
    session = snapshot.get("session", {})
    dmg = snapshot.get("damage", {})
    tele = snapshot.get("telemetry", {})
    motion = snapshot.get("motion", {})
    status = snapshot.get("status", {})

    tyres_wear = dmg.get('m_tyresWear', [0, 0, 0, 0])
    surface_temp = tele.get('m_tyresSurfaceTemperature', [0, 0, 0, 0])
    inner_temp = tele.get('m_tyresInnerTemperature', [0, 0, 0, 0])
    brake_temp = tele.get('m_brakesTemperature', [0, 0, 0, 0])
    
    speed = tele.get('m_speed', 0)
    throttle = tele.get('m_throttle', 0.0)
    brake = tele.get('m_brake', 0.0)
    gear = tele.get('m_gear', 0)
    steer = tele.get('m_steer', 0.0)
    
    g_lat = abs(motion.get('m_gForceLateral', 0))
    g_lon = abs(motion.get('m_gForceLongitudinal', 0))
    g_vert = abs(motion.get('m_gForceVertical', 0))
    
    # 타이어 예측 모델 업데이트
    tyre_predictor.update_lap_data(
        lap_num=current_lap,
        w_fl=tyres_wear[0], w_fr=tyres_wear[1], w_rl=tyres_wear[2], w_rr=tyres_wear[3],
        t_fl=surface_temp[0], t_fr=surface_temp[1], t_rl=surface_temp[2], t_rr=surface_temp[3],
        speed=speed, brake=brake, steer=steer,
        g_lat=g_lat, g_lon=g_lon, g_vert=g_vert
    )
    
    prediction_result = tyre_predictor.predict(current_lap)

    # =========================================================
    # [룰 엔진 평가를 위한 평탄화된 Context 구성]
    # =========================================================
    fia_flag_val = status.get("m_vehicleFIAFlags", 0)
    flag_str = "none"
    if fia_flag_val == 3: flag_str = "yellow" # 명확한 플래그 매핑 번호를 모름. 3과 4는 임시값.
    elif fia_flag_val == 4: flag_str = "blue"

    weather_samples = session.get("m_weatherForecastSamples", [{}])
    rain_pct = weather_samples[0].get("m_rainPercentage", 0) if len(weather_samples) > 0 else 0

    rule_eval_context = {
        "fuel_delta": status.get("m_fuelRemainingLaps", 0), 
        "raw_tyres_wear": max(tyres_wear) if tyres_wear else 0,
        "delta_to_front": current_delta,
        "delta_to_behind": delta_to_behind,
        "front_left_wing_wear_percent": dmg.get("m_frontLeftWingDamage", 0),
        "front_right_wing_wear_percent": dmg.get("m_frontRightWingDamage", 0),
        "track_limits_warnings": 0, # 필요 시 lap 데이터에서 매핑 필요
        "drs_allowed": status.get("m_drsAllowed") == 1,
        "ers_energy_joules": status.get("m_ersStoreEnergy", 0),
        "fia_flag": flag_str,
        "safety_car_status": str(session.get("m_safetyCarStatus", 0)),
        "rain_percentage": rain_pct,
        "tyres_surface_temperature": max(surface_temp) if surface_temp else 0,
        "current_lap": current_lap,
        "pit_stop_window_ideal_lap": session.get("m_pitStopWindowIdealLap", -1),
        "engine_damage": dmg.get("m_engineDamage", 0),
        "rear_temp": max(surface_temp[2:4]) if surface_temp else 0 # 후륜 온도
    }

    # 룰 엔진 실행 (json 조건과 비교)
    active_strategies = evaluate_rules(rule_eval_context)

    # JSON 페이로드 구조 통합
    llm_payload = base_context
    llm_payload["trend"] = trend
    if prediction_result: llm_payload["tyre_wear_prediction"] = prediction_result
    llm_payload["system_memory"] = SYSTEM_MEMORY
    
    # 평가된 전략(용어) 추가
    llm_payload["suggested_strategy"] = active_strategies
    
    # 히스토리 파일 보관용 구조 최적화
    llm_payload["raw_tyres_wear"] = tyres_wear
    llm_payload["raw_telemetry"] = {
        "tyre_surface_temp": surface_temp,
        "tyre_inner_temp": inner_temp,
        "brake_temp": brake_temp,
        "speed": speed,
        "throttle": throttle,
        "brake": brake,
        "gear": gear,
        "steer": steer
    }
    llm_payload["raw_motion"] = {"g_lat": g_lat, "g_lon": g_lon, "g_vert": g_vert}

    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(llm_payload, ensure_ascii=False) + "\n")
    except Exception: pass

    # 문자열 형태로 즉시 반환
    return json.dumps(llm_payload, ensure_ascii=False)