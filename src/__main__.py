import numpy as np

from llm_sdk import Small_LLM_Model
from src.arguments import Args


def main() -> None:
    args = Args.parse_arguments()

    model = Small_LLM_Model()

    text = "[{\n\t"
    for _ in range(20):
        tensors = model.encode(text)

        logit = np.array(model.get_logits_from_input_ids(tensors[0].tolist()))
        tokens = np.argsort(logit)[::-1]

        text = model.decode(tensors[0].tolist() + [tokens[0]])
        print(text)


if __name__ == "__main__":
    main()
