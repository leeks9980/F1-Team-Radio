import socket
import time
import json
import threading
import sys
import os

ORIGINAL_PARSER_PATH = r"D:\code\F1_Team_Radio\Production process\telemeter"
sys.path.append(ORIGINAL_PARSER_PATH)
# 1. 기존 파서 모듈 (에러가 발생했던 부분. 원본 파일에서 구조체를 가져옴)
from f1_pasing import (
    PacketHeader, 
    PacketSessionData, 
    PacketLapData, 
    PacketCarDamageData, 
    PacketCarStatusData
)

# 2. 인메모리 저장소 모듈
from f1_memory import (
    update_session_state, update_lap_state, 
    update_damage_state, update_status_state, get_latest_state_snapshot
)

# 3. 컨텍스트 빌더 모듈
from lm_context_builder import build_lm_context

SYSTEM_MEMORY = {
    "last_radio_lap": 0,
    "last_radio_intent": "None"
}

def udp_listener_thread():
    UDP_IP = "127.0.0.1"
    UDP_PORT = 20777

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"📡 [수신 스레드] F1 25 UDP 포트 {UDP_PORT} 연결 완료. 데이터 대기 중...")

    def ctype_to_dict(obj):
        # 1. 객체가 구조체(Structure)인 경우
        if hasattr(obj, "_fields_"):
            return {field[0]: ctype_to_dict(getattr(obj, field[0])) for field in obj._fields_}
        # 2. 객체가 배열(Array)이나 리스트인 경우 (내부 요소까지 모두 변환)
        elif hasattr(obj, "__len__") and not isinstance(obj, (str, bytes)):
            return [ctype_to_dict(item) for item in obj]
        # 3. 일반 숫자나 문자열인 경우
        else:
            return obj

    while True:
        try:
            data, _ = sock.recvfrom(2048)
            if len(data) < 29: continue

            header = PacketHeader.from_buffer_copy(data[0:29])
            packet_id = header.m_packetId
            player_idx = header.m_playerCarIndex

            if packet_id == 1:
                packet = PacketSessionData.from_buffer_copy(data)
                update_session_state(ctype_to_dict(packet))
                
            elif packet_id == 2:
                packet = PacketLapData.from_buffer_copy(data)
                lap_list = [ctype_to_dict(packet.m_lapData[i]) for i in range(22)]
                update_lap_state(lap_list, player_idx)
                
            elif packet_id == 7:
                packet = PacketCarStatusData.from_buffer_copy(data)
                status_dict = ctype_to_dict(packet.m_carStatusData[player_idx])
                update_status_state(status_dict)
                
            elif packet_id == 10:
                packet = PacketCarDamageData.from_buffer_copy(data)
                damage_dict = ctype_to_dict(packet.m_carDamageData[player_idx])
                update_damage_state(damage_dict)

        except Exception as e:
            continue


def monitor_and_call_llm(interval_seconds=10):
    global SYSTEM_MEMORY
    previous_delta_front = None
    loop_count = 0

    print("🏁 [메인 스레드] Sleipnir LLM 시스템 가동. 상황 분석 시작...")

    while True:
        time.sleep(interval_seconds)
        loop_count += 1
        
        snapshot = get_latest_state_snapshot()
        
        if not snapshot.get("session"):
            print(f"[{loop_count}] ⏳ 패킷 수집 대기 중...")
            continue

        base_context = build_lm_context(snapshot)
        current_lap = base_context["race_context"]["progress"]["current_lap"]
        
        if current_lap == 0:
            continue

        print(f"\n--- ⏱️ [모니터링 Heartbeat] Loop {loop_count} ---")
        print(f"📍 Lap {current_lap} | P{base_context['gaps']['position']} | 앞차: {base_context['gaps']['delta_to_front']}s | 뒤차: {base_context['gaps']['delta_to_behind']}s")
        print(f"🔋 배터리: {base_context['race_context']['car_status']['ers_energy_joules']}J | ☁️ 날씨: {base_context['weather_forecast']['current_condition']}")
        print("----------------------------------------")

        trend = {}
        current_delta = base_context["gaps"]["delta_to_front"]
        if isinstance(current_delta, float) and previous_delta_front is not None:
            trend["gap_to_front_change"] = round(current_delta - previous_delta_front, 3)
        else:
            trend["gap_to_front_change"] = 0.0
        previous_delta_front = current_delta if isinstance(current_delta, float) else None

        llm_payload = base_context
        llm_payload["trend"] = trend
        llm_payload["system_memory"] = SYSTEM_MEMORY

        print(f"✅ [LLM 프롬프트 준비 완료]\n{json.dumps(llm_payload, ensure_ascii=False, indent=2)}")

if __name__ == "__main__":
    listener = threading.Thread(target=udp_listener_thread, daemon=True)
    listener.start()

    try:
        monitor_and_call_llm(interval_seconds=10)
    except KeyboardInterrupt:
        print("\n🛑 시스템 종료.")