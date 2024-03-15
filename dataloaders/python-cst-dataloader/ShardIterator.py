from typing import Dict
import json
from .TreeShard import TreeShardV2, TreeShardXL
from libcst import ParserSyntaxError
import libcst

class ShardIterator():
    def __init__(self, ds, shard_func, batch_size=4, num_examples=0):
        self.shards = []
        self.filtered_shards = []
        self.used_shards = []
        self.iter_index = 0
        self.filtered_len = 0
        self.len_shards = 0
        self.batch_size = batch_size
        self.ds = ds
        self.shard_func = shard_func
        self.num_examples = num_examples

        self.iterator = iter(ds)
        self.init_shards()


    """
        ShardIterator.load_shards(dataloader_func, function_input)
        
        params:
            dataloader_func: a function that loads data given function_input and returns a list of loaded shards
            function_input: input for the dataloader_func to load the list of shards
        
        returns: self
    """
    def load_shards(self, dataloader_func, function_input):
        self.shards = dataloader_func(function_input)
        self.filtered_shards = self.shards
        return self

    def init_shards(self):
        while len(self.filtered_shards) < self.batch_size:
            item = next(self.iterator)
            try:
                self.add_shard(TreeShardV2(self.shard_func(item)))
            except (RuntimeError, StopIteration):
                continue

    """
        ShardedIterator.set_filtered_shards(filter_gen_function)
        
        params:
            filter_gen_function: 
                a function that takes the sharded dataset 
                class and returns a function that acts as a filter
        
        set_filtered_shards uses the filter_gen_function to generate a filter used to filter self.shards
            
        returns: self
    """
    def set_filtered_shards(self, filter_gen_function):
        filter = filter_gen_function(self)
        self.filtered_shards = [val for val in self.shards if filter(val)]
        self.iter_index = 0
        self.filtered_len = len(self.filtered_shards)

        return self

    def add_shard(self, shard):
        self.shards.append(shard)
        self.filtered_shards.append(shard)
        self.filtered_len += 1
        self.num_examples += 1

    def __len__(self):
        return self.len_shards

    def __iter__(self):
        return self

    def __next__(self):
        example = None
        while example == None:
            if self.filtered_len == 0:
                #There are no more shards to get data from
                raise StopIteration()
            else:
                self.iter_index = self.iter_index % self.filtered_len
            try:
                shard = self.filtered_shards[self.iter_index]
                example = next(shard)
                self.iter_index += 1
                break
            except StopIteration:
                self.filtered_len -= 1
                self.filtered_shards.pop(self.iter_index)
                # self.used_shards.append()
                while True:
                    try:
                        item = next(self.iterator)
                        shard = self.shard_func(item)
                        self.add_shard(TreeShardV2(shard))
                        break
                    except RuntimeError:
                        continue

        return example


class ShardIteratorXL():
    def __init__(self, ds, shard_func, batch_size=4, num_examples=0, num_emb_tokens=1):
        self.shards = []
        self.filtered_shards = []
        self.used_shards = []
        self.iter_index = 0
        self.filtered_len = 0
        self.len_shards = 0
        self.batch_size = batch_size
        self.ds = ds
        self.shard_func = shard_func
        self.num_examples = num_examples
        self.num_emb_tokens = num_emb_tokens

        self.iterator = iter(ds)
        self.init_shards()

    """
        ShardIterator.load_shards(dataloader_func, function_input)

        params:
            dataloader_func: a function that loads data given function_input and returns a list of loaded shards
            function_input: input for the dataloader_func to load the list of shards

        returns: self
    """

    def load_shards(self, dataloader_func, function_input):
        self.shards = dataloader_func(function_input)
        self.filtered_shards = self.shards
        return self

    def init_shards(self):
        while len(self.filtered_shards) < self.batch_size:
            item = next(self.iterator)
            try:
                self.add_shard(TreeShardXL(self.shard_func(item, self.num_emb_tokens)))
            except (RuntimeError, StopIteration):
                continue

    """
        ShardedIterator.set_filtered_shards(filter_gen_function)

        params:
            filter_gen_function: 
                a function that takes the sharded dataset 
                class and returns a function that acts as a filter

        set_filtered_shards uses the filter_gen_function to generate a filter used to filter self.shards

        returns: self
    """

    def set_filtered_shards(self, filter_gen_function):
        filter = filter_gen_function(self)
        self.filtered_shards = [val for val in self.shards if filter(val)]
        self.iter_index = 0
        self.filtered_len = len(self.filtered_shards)

        return self

    def add_shard(self, shard):
        self.shards.append(shard)
        self.filtered_shards.append(shard)
        self.filtered_len += 1
        self.num_examples += 1

    def __len__(self):
        return self.len_shards

    def __iter__(self):
        return self

    def __next__(self):
        example = None
        while example == None:
            if self.filtered_len == 0:
                # There are no more shards to get data from
                raise StopIteration()
            else:
                self.iter_index = self.iter_index % self.filtered_len
            try:
                shard = self.filtered_shards[self.iter_index]
                example = next(shard)
                self.iter_index += 1
                break
            except StopIteration:
                self.filtered_len -= 1
                self.filtered_shards.pop(self.iter_index)
                # self.used_shards.append()
                while True:
                    try:
                        item = next(self.iterator)
                        shard = self.shard_func(item, self.num_emb_tokens)
                        self.add_shard(TreeShardXL(shard))
                        break
                    except RuntimeError:
                        continue

        return example