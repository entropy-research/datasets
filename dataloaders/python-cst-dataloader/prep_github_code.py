import json

from datasets import load_dataset, Dataset
from CodeTreeParser import parse_code

from libcst import ParserSyntaxError

def py3Filter(batch):
    files = []
    for example in batch:
        try:
            out = parse_code(example)
            if len(out["node_set"]) == 0:
                continue
            files.append(json.dumps(out))
        except Exception:
            continue

    return {"files": files}


def main():
    train_data = load_dataset("codeparrot/github-code", streaming=True, split="train", licenses=["mit", "isc"], languages=["Python"])
    train_data = train_data.map(lambda batch: py3Filter(batch["code"]), batched=True, remove_columns=train_data.column_names)
    def gen():
        i = 0
        for item in train_data:
            i += 1
            if i == 500000:
                raise StopIteration

            yield item

    data = Dataset.from_generator(gen)
    print(data.dataset_size)
    data.save_to_disk("codeparrot-github_code-python-mit_isc")

if __name__ == "__main__":
    main()

