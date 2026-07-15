import re
import pandas as pd
import json
from transformers import AutoTokenizer

# -------------------------------
# Gemma Tokenizer
# -------------------------------
tokenizer = AutoTokenizer.from_pretrained("unsloth/gemma-2-2b-it")

# -------------------------------
# 원본 CSV
# -------------------------------
INPUT_FILE = r"C:\Users\lijih\Downloads\prepared_generated_data_for_nhs_uk_conversations.csv"

# -------------------------------
# 저장될 jsonl
# -------------------------------
OUTPUT_FILE = "gemma_training_data.jsonl"

df = pd.read_csv(INPUT_FILE)

output = []

for _, row in df.iterrows():

    text = row["text"]

    # 마지막 <|eod|> 제거
    text = text.replace("<|eod|>", "")

    # user-ai 쌍 추출
    pattern = r"<\|user\|>(.*?)<\|eos\|>\s*<\|ai\|>(.*?)<\|eos\|>"

    pairs = re.findall(pattern, text, flags=re.S)

    for user, assistant in pairs:

        user = user.strip()
        assistant = assistant.strip()

        messages = [
            {
                "role": "user",
                "content": user,
            },
            {
                "role": "assistant",
                "content": assistant,
            },
        ]

        # Gemma Chat Template 적용
        formatted = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=False,
        )

        output.append(
            {
                "text": formatted
            }
        )

print("생성 샘플 :", len(output))

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    for item in output:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

print("완료 :", OUTPUT_FILE)