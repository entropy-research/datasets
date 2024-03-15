import functools

from transformers import LlamaConfig, LlamaTokenizer, LlamaForCausalLM
from datasets import load_dataset, IterableDataset
from .CodeTreeParser import parse_code
from .RecursiveShardIterator import ShardIterator
from .recursive import CodeNode
from .TreeShard import TreeShardV2
from typing import Dict
from libcst import ParserSyntaxError
import pprint
import json

def house():
    config = LlamaConfig(vocab_size=32008)
    tokenizer = LlamaTokenizer().from_pretrained()
    model = LlamaForCausalLM(config=config)
    # 1. get element from dataset

    tokenizer.add_special_tokens([
        "<pad>",
        "<mask>",
        "<node>",
        "</node>",
        "#<call>",
        "</call>",
        "<emb>"
    ])

    """
        TODO:
            1.  preprocessing
                1. []  Get function
                2. [x] Split into cst -> store the parsed cst for the dataset
                3. [] tree preprocess
                4  [x] <goal>Doc String</goal><art><n>____</n><n><emb>func_name</n></art><output>...</output>
                    1. [x] How do you go from linear output back to tree space? How do you add that next node? Where do you add that node?
                    2. tree of ideas in components???
                5. [x] Embed sub functions -> put in hash table
                6. predict next token based on the input task and tree
                    1. Do we do full function prediction based on the subtrees?
            2.  [x] Feed into tokenizer
            3.  [] Replace <emb> tokens with target embeddings
            4.  [x] Feed into model
            5.  [x] use raw outputs[0] as embedding -> store in hash table
            6.  Rinse and repeat
    """

    model.train()

def getTreeDepthIterator(shard_iterator, depth):

    def depth_filter_generator(shard_iterator):
        def filterShardByDepth(shard):
            return shard.init_depth(depth)
        return filterShardByDepth

    shard_iterator.set_filtered_shards(depth_filter_generator)

    return shard_iterator

def load_shard(nodelist):
    return TreeShardV2(nodelist)

def load_shards(shardlist):
    shards = []
    for shard in shardlist:
        shards.append(load_shard(shard))

    return shards

def convert_nodeSet(nodeSet, callTree, num_emb_tokens):

    def convert_node(node):
        return CodeNode(node["name"], node["params"], node["body"], node["type"], embedding_repr=node["emb_repr"], prediction_repr=node["body"])

    nodemap = {}

    for k, v in nodeSet.items():
        if k in callTree:
            nodemap[k] = convert_node(v)

    return nodemap


def buildTree(func, nodes, callTree, bfslist, root, depth, ancestors):
    tree = {}

    #MAX RECURSION DEPTH EXCEEDED, need to make sure no cycles exist from children to ancestors?? need to examine raw code element as well.

    if root.depth < depth:
        root.depth = depth

    tree["__data__"] = nodes[func]
    tree["__children__"] = []
    keys = callTree[func].keys()
    bfslist += [nodes[k] for k in keys]
    for child in keys:
        if child != func and ancestors.count(child) != 0:
            tree["__children__"].append(buildTree(child, nodes, callTree, bfslist, root, depth + 1, ancestors.append(child)))

    return tree

def compare_nodes(item_a, item_b):
    return len(item_b.get_children()) - len(item_a.get_children())

def create_code_shard(item:Dict, num_emb_tokens=1):
    #Parse nodes to component tree
    try:
        if "files" in item:
            parsed = json.loads(item["files"])
        elif "code" in item:
            parsed = parse_code(item["code"])
        elif "text" in item:
            parsed = parse_code(item["text"])
    except:
        raise RuntimeError

    #Convert Real Nodes to node classes
    nodeset = convert_nodeSet(parsed["node_set"], parsed["call_tree"], num_emb_tokens)

    #Convert set to iterable list
    dictlist = []
    for key in nodeset.keys():
        dictlist.append(nodeset[key])

    #Build trees with each node as root
    for i, func in enumerate(dictlist):
        bfslist = []
        tree = buildTree(func.name, nodeset, parsed["call_tree"], bfslist, func, 0, [])
        dictlist[i].set_children(bfslist)

    dictlist.sort(key=functools.cmp_to_key(compare_nodes))

    return dictlist


def gen_from_iterator(shard_iterator):
    for s in shard_iterator:
        yield s


def get_data():

    ds = iter(load_dataset("codeparrot/github-code", streaming=True, split="train", licenses=["mit", "isc"], languages=["Python"]))
    sharded = ShardIterator()
    iterable_dataset = IterableDataset.from_generator(gen_from_iterator, gen_kwargs={"shard_iterator": sharded})

    while True:
        try:
            item = next(iter(iterable_dataset))
            pprint.pprint(item)
        except StopIteration:
            try:
                while sharded.filtered_len < 4:
                    item = next(ds)
                    sharded.add_shard(load_shard(create_code_shard(item, 2)))
            except StopIteration:
                break
            except Exception:
                continue