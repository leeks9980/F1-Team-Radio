import threading
import sys
import time
from AI_Agent import call_agent
from Game_information import initialize_predictor_from_history, udp_listener_thread, get_telemetry_data
from stt_engine import WhisperSTTEngine

def main():
    print("🏁 [시스템 부팅] Sleipnir AI 치프 엔지니어 시스템 초기화 중...")
    
    # 1. STT 모듈 초기화 및 백그라운드 스레드 시작
    print("🎙️ 음성 인식(STT) 엔진 로드 중...")
    stt = WhisperSTTEngine(model_dir="large-v3", lang="ko")
    stt.start()
    
    # 2. 이전 주행 기록 로드 및 타이어 예측기 초기화
    initialize_predictor_from_history()
    
    # 3. UDP 텔레메트리 수신 스레드를 백그라운드(데몬)로 실행
    listener = threading.Thread(target=udp_listener_thread, daemon=True)
    listener.start()

    print("\n✅ 시스템 가동 준비 완료.")
    print("📡 포트 20777에서 텔레메트리 데이터를 백그라운드 수신 중입니다.")
    print("💬 마이크에 대고 질문이나 상황을 말씀하세요. (강제 종료: Ctrl+C)")
    print("-" * 60)

    # 4. 실시간 유저 입력 대기 및 AI 호출 루프 (Non-blocking)
    try:
        while True:
            # 큐에서 음성 인식 결과를 가져옴 (기다리지 않고 즉시 반환)
            user_input = stt.get_text()
            
            # 음성 인식이 완료된 텍스트가 있을 경우에만 내부 로직 실행
            if user_input:
                print(f"\n[음성 캡처] 드라이버: {user_input}")
                
                # 종료 커맨드 처리 (음성으로 종료를 명령할 경우)
                if any(cmd in user_input.lower() for cmd in ['시스템 종료', '엔지니어 종료', 'quit', 'exit']):
                    print("\n🛑 명령에 따라 엔지니어 시스템을 종료합니다.")
                    break
                
                # 질문 시점의 최신 텔레메트리 데이터(JSON) 추출
                current_telemetry = get_telemetry_data()
                
                # AI 호출 및 스트리밍 답변 출력
                print("엔지니어: ", end="", flush=True)
                call_agent(context_data=current_telemetry, user=user_input)
                print() # 스트리밍 답변 종료 후 줄바꿈
                
            # 메인 루프가 CPU를 100% 점유하는 것을 방지하기 위한 대기 (10ms)
            time.sleep(0.01)
            
    except KeyboardInterrupt:
        # Ctrl+C 입력 시 강제 종료 처리
        print("\n\n🛑 강제 종료 신호 감지. 시스템을 중단합니다.")
    except Exception as e:
        print(f"\n⚠️ 예상치 못한 오류 발생: {e}")
    finally:
        # 메인 프로그램 종료 시 STT 마이크 및 자원 안전 해제
        print("자원 해제 및 종료 절차 진행 중...")
        stt.stop()

if __name__ == "__main__":
    main()