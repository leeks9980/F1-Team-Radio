import requests
import json

# 1. 텍스트를 전달할 FastAPI 서버의 주소
url = "http://127.0.0.1:8000/speak"

# 2. 서버가 요구하는 JSON 형식에 맞게 데이터 준비
payload = {
    "text": "니 뒤에 아무도 없어 제발 이대로 끝가지 달려서 피원으로 마무리하자 슈마허."
}

# 3. POST 방식으로 서버에 데이터 전송
response = requests.post(url, json=payload)

# 4. 서버의 응답 결과 확인
if response.status_code == 200:
    print("✅ 전송 성공:", response.json())
else:
    print("❌ 전송 실패:", response.status_code)