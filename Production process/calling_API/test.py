from AI_Agent import  call_agent
import requests
import json

url = "http://127.0.0.1:8000/speak"
user = "너의 이름과 너가 할수 있는 일을 설명해봐 길게 아주 상세히 설명해봐"
a = call_agent(user)
payload = {
    "text": a
}

response = requests.post(url, json=payload)

# 4. 서버의 응답 결과 확인
if response.status_code == 200:
    print("✅ 전송 성공:", response.json())
else:
    print("❌ 전송 실패:", response.status_code)