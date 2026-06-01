import os
import re
import time
import torch
import sounddevice as sd
import numpy as np
import threading
import queue # ✅ 비동기 창고 역할

_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

os.environ["COQUI_TOS_AGREED"] = "1"
from TTS.api import TTS

class LocalTTSEngine:
    def __init__(self, speaker_wav_path: str):
        self.speaker_path = speaker_wav_path
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = None
        self.sample_rate = None
        self.gpt_cond_latent = None
        self.speaker_embedding = None
        
        self._initialize_engine()

    def _initialize_engine(self):
        print(f"\n[TTS 엔진] 사용 장치: {self.device}")
        
        if not os.path.exists(self.speaker_path):
            print(f"[오류] 화자 파일({self.speaker_path})이 없습니다.")
            return

        print("[TTS 엔진] XTTS_v2 모델을 VRAM에 로드 중...")
        tts = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(self.device)
        
        if self.device == "cuda":
            torch.backends.cudnn.enabled = False
            torch.backends.cudnn.benchmark = False
            torch.set_float32_matmul_precision("high")
            
        self.model = tts.synthesizer.tts_model
        self.sample_rate = tts.synthesizer.output_sample_rate
        
        print("[TTS 엔진] 화자 음성 특징 추출 및 고정 중...")
        self.gpt_cond_latent, self.speaker_embedding = self.model.get_conditioning_latents(
            audio_path=[self.speaker_path]
        )
        print("[TTS 엔진] 온보드 완료. 대기 중.\n")

    def split_text(self, text: str):
        parts = re.split(r'(?<=[.!?。！？])\s+', text.strip())
        return [p.strip() for p in parts if p.strip()]

    # ---------------------------------------------------------
    # ✅ [배달부 역할] 창고(Queue)에서 소리를 꺼내 재생하는 백그라운드 스레드
    # ---------------------------------------------------------
    def _audio_player_worker(self, audio_queue: queue.Queue):
        # 0.4초 분량의 프리-버퍼 (GPU 연산 지연을 커버하기 위한 최소한의 방파제)
        PREFETCH_SECONDS = 0.4
        min_buffer_frames = int(self.sample_rate * PREFETCH_SECONDS)
        
        buffer = np.array([], dtype=np.float32)
        stream_opened = False
        stream = None

        try:
            while True:
                # 창고에서 데이터 대기 및 수신
                chunk = audio_queue.get()

                # None 신호 수신 시 (문장 끝남)
                if chunk is None:
                    if stream_opened and len(buffer) > 0:
                        stream.write(np.expand_dims(buffer, axis=1)) # 남은 소리 재생
                    break

                # 텐서를 넘파이로 변환 후 버퍼에 누적
                if isinstance(chunk, torch.Tensor):
                    wav_chunk = chunk.cpu().numpy()
                else:
                    wav_chunk = np.array(chunk, dtype=np.float32)
                    
                buffer = np.concatenate((buffer, wav_chunk))

                # 버퍼가 설정치를 넘으면 스피커 송출 시작
                if len(buffer) >= min_buffer_frames:
                    if not stream_opened:
                        stream = sd.OutputStream(samplerate=self.sample_rate, channels=1, dtype='float32')
                        stream.start()
                        stream_opened = True
                        
                    stream.write(np.expand_dims(buffer, axis=1))
                    buffer = np.array([], dtype=np.float32) # 버퍼 초기화

        finally:
            if stream_opened and stream is not None:
                stream.stop()
                stream.close()

    # ---------------------------------------------------------
    # ✅ [공장 역할] GPU 연산에만 집중하는 메인 스레드
    # ---------------------------------------------------------
    def speak(self, text: str):
        if not text.strip():
            return

        sentences = self.split_text(text)
        
        for sentence in sentences:
            if not sentence.strip():
                continue
                
            print(f"🎙️ [멀티 스레드 스트리밍 시작]: {sentence}")
            
            # 두 스레드가 데이터를 주고받을 창고(Queue) 생성
            audio_queue = queue.Queue()
            
            # 재생 전담 스레드 생성 및 출발
            player_thread = threading.Thread(target=self._audio_player_worker, args=(audio_queue,))
            player_thread.start()
            
            start_tts = time.time()
            with torch.inference_mode():
                chunks = self.model.inference_stream(
                    text=sentence,
                    language="ko",
                    gpt_cond_latent=self.gpt_cond_latent,
                    speaker_embedding=self.speaker_embedding,
                    enable_text_splitting=False,
                    temperature=0.6,
                    speed=1.0,
                    repetition_penalty=8.0
                )
                
                # GPU는 재생을 기다리지 않고 연산되는 즉시 창고에 던져넣음
                for chunk in chunks:
                    audio_queue.put(chunk)
            
            # 해당 문장의 연산이 완전히 끝났음을 배달부에게 알림
            audio_queue.put(None)
            
            # 스피커가 마지막 소리를 다 재생할 때까지 메인 흐름 대기
            player_thread.join()
            print(f"✅ 재생 완료 (총 소요시간: {time.time() - start_tts:.2f}초)\n")