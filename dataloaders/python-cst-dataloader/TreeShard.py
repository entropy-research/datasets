from .util import _treeBFS
from typing import Dict

class TreeShard():
    def __init__(
            self,
            shard_type=None,
            json_file_path=None,
            embed_dim=None,
            flatten_content=None,
            ):
        #should support arbitrary db reads/writes
        pass

        #If shard type == json
        #   self.tree = load_json_tree
        #else if shard type == <arbitrary_shard_type>
        #   self.tree = load_arbitrary_tree

        self.content = []
        self.lengths = []
        self.subtrees = []
        self.depths = []
        self.filtered = []
        self.filtered_len = 0
        self.max_depth = -1
        self._flatten_content = None

    def load_json(self, json, max_seq_len):
        tree = json
        if not isinstance(tree, dict):
            tree = json.parse(tree)

        data_list, depth_list, subtrees, max_bfs = _treeBFS(tree, max_seq_len)

        print(subtrees)
        print(depth_list)

        self.content = data_list
        self.subtrees = subtrees
        self.depths = depth_list
        self.lengths = map(lambda x: len(x),  self.content)
        self.max_depth = max_bfs

    def __getitem__(self, idx):
        subtree = self.subtrees[idx]
        node_content = []

        length = 0

        for i in subtree:
            sig_flag = i == idx
            c, l = self.get_content(i, flag=sig_flag)
            node_content.append(c)
            length += l

        return {
            "depth": self.depths[idx],
            "sub_node_content": node_content,
            "local_node_content": self.content[idx],
            "length": length,
            "node_seq": subtree,
            "node_number": idx
        }

    def set_flattener(self, func):
        self._flatten_content = func

    def init_depth(self, depth):
        has_depth = depth <= self.max_depth
        if has_depth:
            self.filtered = [i for i in range(len(self.depths)) if self.depths[i] == depth]

        self.filtered_len = len(self.filtered)

        return has_depth

    def __iter__(self):
        return self

    def __next__(self):
        try:
            example = self.filtered.pop()
        except IndexError:
            raise StopIteration()

        return example

    def get_content(self, idx, **kwargs):

        flat_content = self._flatten_content(self.content[idx], flag=kwargs["flag"]) if self._flatten_content is not None else self.content[idx]
        s = "<n>" + str(idx) + ":" + str(self.depths[idx]) + ":" + flat_content + "</n>"
        return s, len(s)

    def _collate(self, data1, data2):
        return data1 + data2

    def _add_node_tokens(self):
        data_list = []
        for data in self.content:
            data_list.append(self._add_node_tokens_to_data(data))

        self.content = data_list

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


def flatten_content(content: Dict, flag=True):

    signature = content["name"] + ("|" + ", ".join(content["params"]) if "params" in content else "")
    body = (" Body:" + content["body"] if "body" in content else "")
    return signature + body if (flag is True) else signature

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


class TreeShardV2:

    def __init__(
            self,
            nodes,
            tree_generator=None
    ):

        self.nodes = nodes
        self.tree_generator = tree_generator
        self.all_nodes = nodes


    def __getitem__(self, idx):
        return self._prep_node(self.all_nodes[idx])

    def _prep_node(self, node):
        root = node
        node_content = ""

        for child in root.get_children():
            sub_node = child
            node_content += "<node>" + sub_node.short_repr() + "</node>"

        node_content = "<artifacts>" + node_content + "</artifacts>"

        return {
            "target": root.prediction_repr(),
            "input": {
                "text": "<begin_code>" + node_content + root.prediction_repr() + "<end_code>",
                "node_content": node_content
            },
            "root": node
        }

    def init_depth(self, depth):
        self.nodes = [val for val in self.all_nodes if val.depth <= depth]
        return True

    def __iter__(self):
        return self

    def __next__(self):
        try:
            example = self._prep_node(self.nodes.pop())
        except IndexError:
            raise StopIteration()

        return example

    def _collate(self, data1, data2):
        return data1 + data2

class TreeShardXL:

    def __init__(
            self,
            nodes,
            tree_generator=None
    ):

        self.nodes = nodes
        self.tree_generator = tree_generator
        self.all_nodes = nodes


    def __getitem__(self, idx):
        return self._prep_node(self.all_nodes[idx])

    def _prep_node(self, node):
        root = node
        node_content = []

        for child in root.get_children():
            sub_node = child
            node_content.append(sub_node.short_repr())


        return {
            "input": {
                "text": root.prediction_repr(),
                "nodes": node_content,
                "contrastive": root.prediction_repr()
            },
            "root": node
        }

    def init_depth(self, depth):
        self.nodes = [val for val in self.all_nodes if val.depth <= depth]
        return True

    def __iter__(self):
        return self

    def __next__(self):
        try:
            example = self._prep_node(self.nodes.pop())
        except IndexError:
            raise StopIteration()

        return example

    def _collate(self, data1, data2):
        return data1 + data2