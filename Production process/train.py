import torch
from datasets import load_dataset
from unsloth import FastLanguageModel
from trl import SFTTrainer
from transformers import TrainingArguments

torch._dynamo.config.disable = True


def main():

    # ==========================================================
    # 1. 모델 로드
    # ==========================================================

    MODEL_NAME = "unsloth/gemma-2-2b-it"

    MAX_SEQ_LENGTH = 2048
    LOAD_IN_4BIT = True
    DTYPE = None

    print(f"\n[INFO] Loading model : {MODEL_NAME}")

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=MODEL_NAME,
        max_seq_length=MAX_SEQ_LENGTH,
        dtype=DTYPE,
        load_in_4bit=LOAD_IN_4BIT,
    )

    tokenizer.pad_token = tokenizer.eos_token

    # ==========================================================
    # 2. LoRA
    # ==========================================================

    print("[INFO] Applying LoRA...")

    model = FastLanguageModel.get_peft_model(
        model,

        r=8,

        target_modules=[
            "q_proj",
            "k_proj",
            "v_proj",
            "o_proj",
            "gate_proj",
            "up_proj",
            "down_proj",
        ],

        lora_alpha=16,
        lora_dropout=0.15,
        bias="none",

        use_gradient_checkpointing="unsloth",

        random_state=3407,

        use_rslora=False,

        loftq_config=None,
    )

    # ==========================================================
    # 3. Dataset
    # ==========================================================

    print("[INFO] Loading Dataset...")

    dataset = load_dataset(
        "json",
        data_files=r"D:\code\F1_Team_Radio\LoRA\gemma_training_data.jsonl",
        split="train",
    )

    print(dataset)

    # ==========================================================
    # 4. Trainer
    # ==========================================================

    trainer = SFTTrainer(

        model=model,

        tokenizer=tokenizer,

        train_dataset=dataset,

        dataset_text_field="text",

        max_seq_length=MAX_SEQ_LENGTH,

        dataset_num_proc=2,

        packing=False,

        args=TrainingArguments(

            output_dir="outputs",

            num_train_epochs=2,

            per_device_train_batch_size=2,

            gradient_accumulation_steps=4,

            learning_rate=1e-4,

            warmup_ratio=0.1,

            logging_steps=1,

            save_strategy="epoch",

            save_total_limit=2,

            optim="adamw_8bit",

            weight_decay=0.05,

            lr_scheduler_type="linear",

            seed=3407,

            fp16=not torch.cuda.is_bf16_supported(),

            bf16=torch.cuda.is_bf16_supported(),

            report_to="none",

        ),
    )

    # ==========================================================
    # 5. Train
    # ==========================================================

    print("\n==============================")
    print(" Start Training ")
    print("==============================\n")

    trainer.train()

    # ==========================================================
    # 6. Save
    # ==========================================================

    SAVE_PATH = "gemma_medical_lora"

    print(f"\nSaving LoRA -> {SAVE_PATH}")

    model.save_pretrained(SAVE_PATH)

    tokenizer.save_pretrained(SAVE_PATH)

    print("\nDone.")


if __name__ == "__main__":
    main()