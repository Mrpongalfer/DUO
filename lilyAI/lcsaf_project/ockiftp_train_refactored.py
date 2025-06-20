import argparse
import os
import json
from transformers import (
    LlamaForCausalLM,
    LlamaTokenizer,
    Trainer,
    TrainingArguments,
    DataCollatorForLanguageModeling,
)
from torch.utils.data import Dataset


class JSONLDataset(Dataset):
    def __init__(self, file_path, tokenizer, block_size=512):
        self.samples = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                prompt = f"Instruction: {obj.get('instruction', '')}\nInput: {obj.get('input', '')}\nOutput: {obj.get('output', '')}"
                self.samples.append(prompt)
        self.tokenizer = tokenizer
        self.block_size = block_size

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.tokenizer(
            self.samples[idx],
            truncation=True,
            max_length=self.block_size,
            padding="max_length",
            return_tensors="pt",
        )


def get_dataset(file_path, tokenizer, block_size=512):
    if file_path.endswith(".jsonl"):
        return JSONLDataset(file_path, tokenizer, block_size)
    else:
        from transformers import TextDataset

        return TextDataset(
            tokenizer=tokenizer, file_path=file_path, block_size=block_size
        )


def main():
    parser = argparse.ArgumentParser(description="Fine-tune Llama 3 on custom data.")
    parser.add_argument(
        "--data", required=True, help="Path to training data (txt or jsonl)"
    )
    parser.add_argument("--output", required=True, help="Output directory for model")
    parser.add_argument("--epochs", type=int, default=1, help="Number of epochs")
    args = parser.parse_args()

    model_name = os.environ.get("LLAMA3_MODEL", "meta-llama/Meta-Llama-3-8B")
    tokenizer = LlamaTokenizer.from_pretrained(model_name)
    model = LlamaForCausalLM.from_pretrained(model_name)

    dataset = get_dataset(args.data, tokenizer)
    data_collator = DataCollatorForLanguageModeling(tokenizer=tokenizer, mlm=False)

    training_args = TrainingArguments(
        output_dir=args.output,
        overwrite_output_dir=True,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=2,
        save_steps=500,
        save_total_limit=2,
        logging_dir=os.path.join(args.output, "logs"),
        logging_steps=100,
        # Placeholder for adversarial training logic
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=dataset,
        # Placeholder: callbacks for adversarial training
    )

    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)


if __name__ == "__main__":
    main()
