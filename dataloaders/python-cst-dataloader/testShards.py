import unittest
import json


from typing import Dict

from datasets import IterableDataset

from RecursiveShardIterator import ShardIterator
from TreeShard import TreeShard

treeA = {
    "__data__": "A",
    "__children__": [
        {
            "__data__": "B",
            "__children__": [
                {"__data__": "D", "__children__": []},
                {"__data__": "E", "__children__": []}
            ]
        },
        {
            "__data__": "C",
            "__children__": [
                {"__data__": "F", "__children__": []},
                {"__data__": "G", "__children__": []}
            ]
        }
    ]
}

treeB = {
    "__data__": "A",
    "__children__": [
        {
            "__data__": "B",
            "__children__": [
                {"__data__": "D", "__children__": []},
                {"__data__": "E", "__children__": [
                    {"__data__": "F", "__children__": []},
                    {"__data__": "G", "__children__": []}
                ]}
            ]
        },
        {
            "__data__": "C",
            "__children__": []
        }
    ]
}

treeC = {
    "__data__": "A",
    "__children__": [
        {
            "__data__": "B",
            "__children__": [
                {"__data__": "D", "__children__": []},
                {"__data__": "E", "__children__": []},
                {"__data__": "F", "__children__": []},
                {"__data__": "G", "__children__": []}
            ]
        },
        {
            "__data__": "C",
            "__children__": []
        }
    ]
}

def getTreeDepthIterator(shard_iterator, depth):

    def depth_filter_generator(shard_iterator):
        def filterShardByDepth(shard):
            return shard.init_depth(depth)
        return filterShardByDepth

    shard_iterator.set_filtered_shards(depth_filter_generator)

    return shard_iterator

def load_shards(tree_list):
    shards = []
    for tree in tree_list:
        shard = TreeShard()
        shard.load_json(tree, 3)
        shards.append(shard)

    return shards


def flatten_content(content: Dict, embedding=None, flag=True):

    signature = content["name"] + ("|" + ", ".join(content["params"]) if "params" in content else "")
    body = (" Body:" + content["body"] if "body" in content else "")
    return signature + body if (embedding is None) and (flag is True) else signature

def load_test_shard(file_name):
    shards = []
    with open("./test.json", "r") as f:
        shard = TreeShard()
        tree = json.load(f)
        shard.load_json(tree, 3)
        shard.set_flattener(flatten_content)
        shards.append(shard)
        print(shard)

    return shards

class TestMethods(unittest.TestCase):

    def begin(self):
        self.si = ShardIterator()
        self.trees = [treeA, treeB, treeC]
        self.shards = load_shards(self.trees)

    def test_LoadShards_depth(self):
        self.begin()
        self.assertEqual(self.shards[0].depths, [0, 1, 1, 2, 2, 2, 2])
        self.assertEqual(self.shards[1].depths, [0, 1, 1, 2, 2, 3, 3])
        self.assertEqual(self.shards[2].depths, [0, 1, 1, 2, 2, 2, 2])

        self.assertEqual(self.shards[0].subtrees, [[0, 1, 2], [1, 3, 4], [2, 5, 6], [3], [4], [5], [6]])
        self.assertEqual(self.shards[1].subtrees, [[0, 1, 2], [1, 3, 4], [2], [3], [4, 5, 6], [5], [6]])
        self.assertEqual(self.shards[2].subtrees, [[0, 1, 2], [1, 3, 4], [2], [3], [4], [5], [6]])

    def test_shard_generator(self):
        self.begin()
        def gen(shards, d):
            for s in shards:
                s.init_depth(d)
                for idx in s.filtered:
                    yield s[idx]

        for d in range(3):
            my_iterable_dataset = IterableDataset.from_generator(gen, gen_kwargs={"shards": self.shards, "d": d})
            for i, example in enumerate(my_iterable_dataset):
                self.assertEqual(example["depth"], d)

    def test_shard_iterator(self):

        def gen_from_iterator(shard_iterator):
            for s in shard_iterator:
                yield s

        self.begin()
        self.si.load_shards(load_shards, self.trees)

        for d in range(4):
            si = getTreeDepthIterator(self.si, d)
            iterable_dataset = IterableDataset.from_generator(gen_from_iterator, gen_kwargs={"shard_iterator": si})
            for i, example in enumerate(iterable_dataset):
                self.assertEqual(example["depth"], d)

    def test_shard_iterator_on_data(self):

        def gen_from_iterator(shard_iterator):
            for s in shard_iterator:
                yield s

        self.begin()
        self.si.load_shards(load_test_shard, self.trees)

        for d in range(3):
            si = getTreeDepthIterator(self.si, d)
            iterable_dataset = IterableDataset.from_generator(gen_from_iterator, gen_kwargs={"shard_iterator": si})
            for i, example in enumerate(iterable_dataset):
                self.assertEqual(example["depth"], d)
                print(example)