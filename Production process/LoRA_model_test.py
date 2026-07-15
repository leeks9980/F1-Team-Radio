import torch
from unsloth import FastLanguageModel

# ==========================================================
# 모델 로드
# ==========================================================

MODEL_PATH = "gemma_medical_lora"

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name=MODEL_PATH,
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=True,
)

FastLanguageModel.for_inference(model)

messages = []

print("Gemma LoRA Chat")
print("exit 입력 시 종료\n")

while True:

    user_input = input("User : ")

    if user_input.lower() == "exit":
        break

    messages.append(
        {
            "role": "user",
            "content": user_input,
        }
    )

    inputs = tokenizer.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_tensors="pt",
    ).to(model.device)

    with torch.no_grad():

        outputs = model.generate(
            input_ids=inputs,

            max_new_tokens=256,

            temperature=0.2,

            do_sample=True,

            top_p=0.9,

            use_cache=True,

            pad_token_id=tokenizer.eos_token_id,
        )

    answer = tokenizer.decode(
        outputs[0][inputs.shape[-1]:],
        skip_special_tokens=True,
    ).strip()

    print(f"\nAssistant : {answer}\n")

    messages.append(
        {
            "role": "assistant",
            "content": answer,
        }
    )