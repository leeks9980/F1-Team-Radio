import sys
import time
import queue
import threading
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import sounddevice as sd
import webrtcvad
from faster_whisper import WhisperModel

class WhisperSTTEngine:
    def __init__(self, model_dir="large-v3", lang="ko"):
        # 오디오 및 STT 설정
        self.SAMPLE_RATE = 16000
        self.FRAME_MS = 20
        self.CHUNK_SECONDS = 1.0
        self.OVERLAP_SECONDS = 0.30
        self.SILENCE_TIMEOUT = 0.28
        self.MAX_ACTIVE_SECONDS = 10.0
        self.LANG = lang

        self.MODEL_DIR = model_dir
        self.PREFER_FLOAT16 = True
        self.BEAM_SIZE = 2
        self.INITIAL_GUIDE = "한국어로 자연스럽게 띄어쓰고 구두점을 사용해 주세요."
        self.CONTEXT_CHARS = 160

        # 파생 변수
        self.FRAME_SAMPLES = self.SAMPLE_RATE * self.FRAME_MS // 1000
        self.OVERLAP_SAMPLES = int(self.OVERLAP_SECONDS * self.SAMPLE_RATE)
        self.MIN_FLUSH_SAMPLES = int(0.60 * self.SAMPLE_RATE)
        self.MAX_ACTIVE_SAMPLES = int(self.MAX_ACTIVE_SECONDS * self.SAMPLE_RATE)

        # 큐 및 상태 관리
        self.audio_q = queue.Queue(maxsize=64)
        self.decode_q = queue.Queue(maxsize=12)
        self.text_out_q = queue.Queue(maxsize=30)  # 최종 텍스트가 담길 큐
        self._stop_flag = False
        self.prev_context = ""

        # 자원 초기화
        self.model = self._load_model()
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.stream = None
        self.t_vad = None

    def _load_model(self):
        device = "cuda" if self._is_cuda_available() else "cpu"
        compute_type = "float16" if device == "cuda" and self.PREFER_FLOAT16 else "int8"
        print(f"[STT INFO] Device={device}, compute_type={compute_type}")
        
        # 로컬 폴더(large-v3)에서 오프라인으로 불러오기 강제
        kwargs = dict(device=device, compute_type=compute_type, local_files_only=True)
        model = WhisperModel(self.MODEL_DIR, **kwargs)
        
        # 웜업 (Warm-up)
        _warm = np.zeros(int(self.SAMPLE_RATE * 0.3), dtype=np.float32)
        list(model.transcribe(_warm, language=self.LANG, beam_size=1))
        return model

    def _is_cuda_available(self):
        try:
            import torch
            return torch.cuda.is_available()
        except ImportError:
            return False

    def _audio_callback(self, indata, frames, time_info, status):
        try:
            self.audio_q.put_nowait(indata[:, 0].copy())
        except queue.Full:
            pass

    def _decode_worker(self):
        while not self._stop_flag:
            try:
                item = self.decode_q.get(timeout=0.1)
            except queue.Empty:
                continue

            segment, t0 = item if isinstance(item, tuple) else (item, None)

            try:
                seg = np.asarray(segment, dtype=np.float32)
                if not seg.flags['C_CONTIGUOUS']:
                    seg = np.ascontiguousarray(seg)
                seg = np.nan_to_num(seg, copy=False)

                # 볼륨 스레시홀드 조정 (잡음 무시 강도 높임)
                if seg.size < int(0.3 * self.SAMPLE_RATE) or np.sqrt(np.mean(seg**2)) < 1e-3:
                    self.decode_q.task_done()
                    continue

                segments, info = self.model.transcribe(
                    seg, language=self.LANG, task="transcribe", beam_size=self.BEAM_SIZE,
                    temperature=0.0, vad_filter=False, condition_on_previous_text=True,
                    initial_prompt=(self.prev_context + " " + self.INITIAL_GUIDE).strip(),
                    word_timestamps=False,
                )

                text = "".join([s.text for s in segments]).strip()

                # 환각 필터링
                if "한국어로 자연스럽게" in text or "시청해주셔서 감사합니다" in text.replace(" ", ""):
                    self.decode_q.task_done()
                    continue

                if text:
                    self.text_out_q.put(text) # 외부로 보낼 큐에 텍스트 삽입
                    
                    joined = (self.prev_context + " " + text).strip()
                    self.prev_context = joined[-self.CONTEXT_CHARS:] if self.CONTEXT_CHARS > 0 else ""
            except Exception as e:
                print(f"[STT ERROR] decode_worker exception: {e}")
            finally:
                self.decode_q.task_done()

    def _vad_streamer(self):
        vad = webrtcvad.Vad(3) # 강도 3으로 상향 (소음 필터링)
        pending = active = tail = np.zeros(0, dtype=np.float32)
        last_speech_ts, silence_armed = 0.0, False

        def is_speech(frame):
            f = np.clip(frame * 32768.0, -32768.0, 32767.0).astype(np.int16)
            return vad.is_speech(f.tobytes(), self.SAMPLE_RATE)

        while not self._stop_flag:
            try:
                block = self.audio_q.get(timeout=0.1)
                pending = np.concatenate((pending, block)) if pending.size else block
            except queue.Empty:
                pass

            while pending.size >= self.FRAME_SAMPLES:
                frame = pending[:self.FRAME_SAMPLES]
                pending = pending[self.FRAME_SAMPLES:]
                speech_flag = is_speech(frame)
                now = time.time()

                if speech_flag:
                    silence_armed, last_speech_ts = True, now
                    active = frame if active.size == 0 else np.concatenate((active, frame))
                    if active.size > self.MAX_ACTIVE_SAMPLES:
                        segment = np.concatenate((tail, active)) if tail.size else active.copy()
                        try: self.decode_q.put_nowait((segment, time.time()))
                        except queue.Full: pass
                        tail = segment[-self.OVERLAP_SAMPLES:] if segment.size >= self.OVERLAP_SAMPLES else segment.copy()
                        active, silence_armed = np.zeros(0, dtype=np.float32), False
                else:
                    if silence_armed and (now - last_speech_ts) >= self.SILENCE_TIMEOUT:
                        if active.size >= self.MIN_FLUSH_SAMPLES:
                            segment = np.concatenate((tail, active)) if tail.size else active.copy()
                            try: self.decode_q.put_nowait((segment, time.time()))
                            except queue.Full: pass
                            tail = segment[-self.OVERLAP_SAMPLES:] if segment.size >= self.OVERLAP_SAMPLES else segment.copy()
                        active, silence_armed = np.zeros(0, dtype=np.float32), False

    # =============== 외부 공개 API ===============
    def start(self):
        """STT 엔진(마이크 캡처 및 추론 스레드)을 백그라운드에서 시작합니다."""
        self._stop_flag = False
        self.executor.submit(self._decode_worker)
        
        self.stream = sd.InputStream(samplerate=self.SAMPLE_RATE, channels=1, dtype="float32",
                                     blocksize=self.FRAME_SAMPLES, callback=self._audio_callback)
        self.stream.start()
        
        self.t_vad = threading.Thread(target=self._vad_streamer, daemon=True)
        self.t_vad.start()
        print("[STT INFO] 엔진이 백그라운드에서 시작되었습니다.")

    def get_text(self):
        """인식된 텍스트가 있다면 문자열을 반환하고, 없으면 None을 반환합니다. (Non-blocking)"""
        try:
            return self.text_out_q.get_nowait()
        except queue.Empty:
            return None

    def stop(self):
        """STT 엔진의 모든 스레드와 자원을 안전하게 종료합니다."""
        self._stop_flag = True
        time.sleep(0.2)
        if self.stream:
            self.stream.stop()
            self.stream.close()
        self.executor.shutdown(wait=False)
        print("[STT INFO] 엔진 종료 완료.")