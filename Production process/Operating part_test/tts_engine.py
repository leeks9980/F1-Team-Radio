import os
import re
import time
import torch

_original_load = torch.load
def _patched_load(*args, **kwargs):
    kwargs['weights_only'] = False
    return _original_load(*args, **kwargs)
torch.load = _patched_load

import sounddevice as sd
import numpy as np

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

    def speak(self, text: str):
        if not text.strip():
            return

        sentences = self.split_text(text)
        
        for sentence in sentences:
            start_tts = time.time()
            with torch.inference_mode():
                out = self.model.inference(
                    text=sentence,
                    language="ko",
                    gpt_cond_latent=self.gpt_cond_latent,
                    speaker_embedding=self.speaker_embedding,
                    enable_text_splitting=False,
                    temperature=0.65
                )

            wav = np.array(out["wav"], dtype=np.float32)
            sd.play(wav, samplerate=self.sample_rate)
            sd.wait()