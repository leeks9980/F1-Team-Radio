import os
# [가장 중요] C++ 가속 라이브러리(OpenMP 등) 중복 충돌로 인한 묵언 강제 종료 방지
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

import time
import threading
import requests
import sys

from AI_Agent import call_agent
from Game_information import initialize_predictor_from_history, udp_listener_thread, get_telemetry_data
from stt_engine import WhisperSTTEngine

# 백그라운드에 켜져 있을 TTS 서버의 주소
TTS_SERVER_URL = "http://127.0.0.1:8000/speak"

def main():
    print("🏁 [시스템 부팅] Sleipnir 메인 시스템 초기화 중...")
    
    # ---------------------------------------------------------
    # 1. STT 모듈 초기화 (VRAM 초과 방지를 위해 small 모델 권장)
    # ---------------------------------------------------------
    try:
        print("🎙️ [1/3] 음성 인식(STT) 엔진 로드 중...")
        stt = WhisperSTTEngine(model_dir="small", lang="ko") 
        stt.start()
        print("✅ STT 엔진 로드 및 마이크 스레드 시작 완료!")
    except Exception as e:
        print(f"🛑 STT 초기화 중 치명적 에러 발생: {e}")
        sys.exit(1)
        
    # ---------------------------------------------------------
    # 2. 게임 데이터 예측기 초기화 
    # ---------------------------------------------------------
    try:
        print("🧠 [2/3] 주행 기록 로드 및 예측기 초기화 중...")
        initialize_predictor_from_history()
        print("✅ 게임 예측기 초기화 완료!")
    except Exception as e:
        print(f"🛑 예측기 초기화 중 에러 발생: {e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # 3. 게임 텔레메트리 수신 스레드 시작
    # ---------------------------------------------------------
    try:
        print("📡 [3/3] UDP 텔레메트리 수신 스레드 가동 중...")
        listener = threading.Thread(target=udp_listener_thread, daemon=True)
        listener.start()
        print("✅ UDP 수신 스레드 가동 완료!")
    except Exception as e:
        print(f"🛑 UDP 스레드 시작 중 에러 발생: {e}")
        sys.exit(1)

    # ---------------------------------------------------------
    # 가동 완료 메시지 (여기까지 모두 통과해야 튕기지 않은 것임)
    # ---------------------------------------------------------
    print("\n" + "="*60)
    print("🚀 메인 시스템 가동 준비 완료.")
    print("💡 주의: 음성이 출력되려면 별도의 터미널에서 TTS 서버가 켜져 있어야 합니다.")
    print("💬 마이크에 대고 무전하십시오. (강제 종료: Ctrl+C)")
    print("="*60 + "\n")

    # ---------------------------------------------------------
    # 4. 메인 루프 (마이크 수신 -> LLM 추론 -> TTS 전송)
    # ---------------------------------------------------------
    try:
        while True:
            # 큐에서 음성 인식 결과를 가져옴 (기다리지 않고 즉시 반환)
            user_input = stt.get_text()
            
            if user_input:
                print(f"\n[음성 캡처] 드라이버: {user_input}")
                
                # 종료 커맨드 처리
                if any(cmd in user_input.lower() for cmd in ['시스템 종료', '엔지니어 종료', 'quit', 'exit']):
                    print("\n🛑 명령에 따라 엔지니어 시스템을 종료합니다.")
                    break
                
                # 질문 시점의 최신 텔레메트리 데이터 추출
                current_telemetry = get_telemetry_data()
                
                print("🧠 엔지니어 판단 중...")
                # AI 호출 (텍스트 반환)
                llm_response = call_agent(context_data=current_telemetry, user=user_input)
                
                if llm_response:
                    print(f"엔지니어: {llm_response}")
                    
                    # ---------------------------------------------------------
                    # 핵심: LLM의 텍스트를 백그라운드 TTS 서버로 쏘아 보냄
                    # ---------------------------------------------------------
                    try:
                        requests.post(TTS_SERVER_URL, json={"text": llm_response}, timeout=2)
                    except requests.exceptions.RequestException:
                        print("⚠️ [오류] TTS 서버에 연결할 수 없습니다. 다른 터미널에서 tts_server.py가 실행 중인지 확인하세요.")
                
            # 메인 루프 CPU 점유율 조절 (10ms 대기)
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        print("\n\n🛑 강제 종료 신호 감지. 시스템을 중단합니다.")
    except Exception as e:
        print(f"\n⚠️ 메인 루프 실행 중 예상치 못한 오류 발생: {e}")
    finally:
        print("자원 해제 및 종료 절차 진행 중...")
        stt.stop()

if __name__ == "__main__":
    main()
