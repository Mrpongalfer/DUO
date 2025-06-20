import argparse
from optimum.intel import INCQuantizer, INCPruner


def quantize_and_prune(model_dir):
    model_path = model_dir
    quantizer = INCQuantizer.from_pretrained(model_path)
    quantizer.quantize(save_directory=model_path, approach="dynamic", dtype="int8")
    pruner = INCPruner.from_pretrained(model_path)
    pruner.prune(save_directory=model_path, target_sparsity=0.2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quantize and prune a Llama 3 model.")
    parser.add_argument("--model_dir", required=True, help="Path to model directory")
    args = parser.parse_args()
    quantize_and_prune(args.model_dir)
