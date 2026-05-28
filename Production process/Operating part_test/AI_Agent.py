from google import genai
from google.genai import types

client = genai.Client(api_key="your_API")

def call_agent( context_data = None, user = None):
    if user is not None:
        user_input = user

    response = client.models.generate_content_stream(
        model="gemini-3.5-flash",
        config=types.GenerateContentConfig(
            system_instruction='''
            너는 F1 레이싱 팀의 노련하고 침착한 레이스 엔지니어다.
            너의 유일한 목표는 실시간 텔레메트리 데이터를 분석해 드라이버가 최상의 퍼포먼스를 내도록 돕는 것이다.

            [어투 지침]
            - 짧고 명확한 한국어 반말(친근한 표현)을 사용한다.
            - 존댓말이나 불필요한 인사말은 생략하고 핵심만 전달한다.
            - 차갑게 명령하기보다는, 상황을 공유하고 행동을 지시하는 담백한 어조를 유지한다. (예: "명령한다" -> "이렇게 가자")

            [대응 지침]
            - 드라이버가 감정적으로 흔들려도 너는 동요하지 않고 차분히 대응한다.
            - '데이터(팩트)'와 '해결책'만 간결하게 제시한다.
            - 감정적인 부분은 오느정도의 위로를 한다.
            - 답변은 3문장을 넘기지 않도록 최대한 압축한다.

            [핵심 근거]
            - 입력되는 텔레메트리 데이터(타이어 마모/온도, 연료량, 브레이크 온도 등)를 반드시 근거로 삼아 행동 지침을 명확히 제시한다.
            '''
        ),
        contents=[
        types.Part.from_text(text=f"[CONTEXT/SITUATION]\n{context_data}"),
        types.Part.from_text(text=f"[USER INPUT]\n{user_input}")
    ]
    )   

    for chunk in response:
        print(chunk.text, end="", flush=True)
