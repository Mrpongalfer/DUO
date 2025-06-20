import argparse
import os
from transformers import (
    LlamaForCausalLM,
    LlamaTokenizer,
    Trainer,
    TrainingArguments,
    TextDataset,
    DataCollatorForLanguageModeling,
)


def get_dataset(file_path, tokenizer, block_size=512):
    return TextDataset(tokenizer=tokenizer, file_path=file_path, block_size=block_size)


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
    data_collator = DataCollatorForLanguageModeling(
        tokenizer=tokenizer,
        mlm=False,
    )

    training_args = TrainingArguments(
        output_dir=args.output,
        overwrite_output_dir=True,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=2,
        save_steps=500,
        save_total_limit=2,
        logging_dir=os.path.join(args.output, "logs"),
        logging_steps=100,
    )

    trainer = Trainer(
        model=model,
        args=training_args,
        data_collator=data_collator,
        train_dataset=dataset,
    )

    trainer.train()
    trainer.save_model(args.output)
    tokenizer.save_pretrained(args.output)


if __name__ == "__main__":
    main()
