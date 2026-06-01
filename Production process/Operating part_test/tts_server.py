# tts_server.py
import os
from fastapi import FastAPI
from pydantic import BaseModel
import uvicorn

# TTS 엔진 로드 (사전 세팅된 클래스)
from tts_engine import LocalTTSEngine

app = FastAPI()
tts_engine = None

class SpeechRequest(BaseModel):
    text: str

@app.on_event("startup")
def startup_event():
    global tts_engine
    print("🔊 [TTS 서버] 엔진 로드 및 VRAM 적재 중...")
    DUMMY_SPEAKER_PATH = r"D:\code\F1_Team_Radio\Production process\TTS\cloning voice_1.wav" 
    tts_engine = LocalTTSEngine(speaker_wav_path=DUMMY_SPEAKER_PATH)
    print("🔊 [TTS 서버] 가동 준비 완료. 포트 8000에서 대기 중.")

@app.post("/speak")
def speak_endpoint(request: SpeechRequest):
    print(f"🎙️ [요청 수신] 출력 중: {request.text}")
    tts_engine.speak(request.text)
    return {"status": "success"}

if __name__ == "__main__":
    # 포트 8000번으로 서버 실행
    uvicorn.run(app, host="127.0.0.1", port=8000)