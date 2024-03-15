import numpy as np
import torch.utils.data
import pickle
import glob

def read_pickle_file(filename):
    with open(filename, 'rb') as f:
        data = pickle.load(f)
    return data

class TreeDataset():
    """A dataset that provides helpers for batching."""

    def __init__(self, file_path=None, dictionary=None, MAX_DIM=768):

        # if dictionary, we know we are loading the token values
        if dictionary is not None:
            pass
        else:
            # If no dictionary supplied, we know that the values are already processed
            pass

        self.MAX_DIM = MAX_DIM

        self.sequences = []
        self.matrices = []
        self.embeddings = []

        self.dictionary = dictionary

        self.data_path = file_path
        file_list = glob.glob(self.data_path + "/*")  # self.epoch

        # TODO
        # Embeddings should just be a long list of one value per item
        # These will be used in real time to build the desired embeddings

        for file in file_list:
            if "recursive_children" in file:
                l = read_pickle_file(file)
                self.sequences = l
            if "matrices" in file:
                l = read_pickle_file(file)
                self.matrices = l

            if "ad_matrix" in file:
                pass

            if "embedding" in file:
                l = read_pickle_file(file)
                self.embeddings = [np.pad(np.array([e[0]]), pad_width=(0, 767)) for e in l]

        self.sequences.reverse()
        self.matrices.reverse()
        self.model_embeddings = self.embeddings

        self.sizes = np.array([len(seq) for seq in self.sequences])  # hack seq len to handle fixed len padded input

    # Return an array based on the sequence
    def __getitem__(self, index):
        seq = self.sequences[index]
        embedding = []
        # embedding_list = self.model_embeddings if len(self.model_embeddings) == len(
        #     self.embeddings) else self.embeddings
        for node in seq:
            embedding.append(self.model_embeddings[node])

        res = torch.from_numpy(np.array(embedding))
        # print("getitem",res)
        # print(res.shape)
        return res

    def __len__(self):
        return len(self.sequences)

    # This should never return more than 1 sample
    def collater(self, samples):
        """Merge a list of samples to form a mini-batch.

        Args:
            samples (List[dict]): samples to collate

        Returns:
            dict: a mini-batch suitable for forwarding with a Model
        """
        return samples

    def num_tokens(self, index):
        """Return the number of tokens in a sample. This value is used to
        enforce ``--max-tokens`` during batching."""

        return self.size(index)

    # TODO confused by this, is it eggregate or individual/vector
    def num_tokens_vec(self, indices):
        """Return the number of tokens for a set of positions defined by indices.
        This value is used to enforce ``--max-tokens`` during batching."""
        return [self.size(index) for index in indices]

    def size(self, index):
        """Return an example's size as a float or tuple. This value is used when
        filtering a dataset with ``--max-positions``."""
        return len(self.sequences[index])

    # TODO Maintain given order OR reverse for bottom up? Which one?
    def ordered_indices(self):
        """Return an ordered list of indices. Batches will be constructed based
        on this order."""
        return np.arange(len(self), dtype=np.int64)

    def update_embedding(self, index, tensor):
        # print("inserted tensor of shape: " + str(tensor.shape))
        self.model_embeddings[index] = tensor[:1, :].squeeze(0)
        # print("increased size of self.model_embeddings to: " + str(len(self.model_embeddings)))
        # print(self.model_embeddings)

    @property
    def supports_prefetch(self):
        """Whether this dataset supports prefetching."""
        return False

    @property
    def can_reuse_epoch_itr_across_epochs(self):
        return True

    @classmethod
    def exists(cls, path):
        sublist = ["recursive_children", "matrices", "embedding"]
        file_list = glob.glob(path + "/*")
        x = False
        for s in sublist:
            for f in file_list:
                x = s in f
                if x == True: break
            if x == False: break
        return x

    def prefetch(self, indices):
        """Prefetch the data required for this epoch."""

        return np.array([self.__getitem__(index) for index in indices])

    # def get_batch_shapes(self):
    #     """
    #     Return a list of valid batch shapes, for example::
    #
    #         [(8, 512), (16, 256), (32, 128)]
    #
    #     The first dimension of each tuple is the batch size and can be ``None``
    #     to automatically infer the max batch size based on ``--max-tokens``.
    #     The second dimension of each tuple is the max supported length as given
    #     by :func:`fairseq.data.FairseqDataset.num_tokens`.
    #
    #     This will be used by :func:`fairseq.data.FairseqDataset.batch_by_size`
    #     to restrict batch shapes. This is useful on TPUs to avoid too many
    #     dynamic shapes (and recompilations).
    #     """
    #     return None
    #
    # def filter_indices_by_size(self, indices, max_sizes):
    #     """
    #     Filter a list of sample indices. Remove those that are longer than
    #     specified in *max_sizes*.
    #
    #     WARNING: don't update, override method in child classes
    #
    #     Args:
    #         indices (np.array): original array of sample indices
    #         max_sizes (int or list[int] or tuple[int]): max sample size,
    #             can be defined separately for src and tgt (then list or tuple)
    #
    #     Returns:
    #         np.array: filtered sample array
    #         list: list of removed indices
    #     """
    #     if isinstance(max_sizes, float) or isinstance(max_sizes, int):
    #         if hasattr(self, "sizes") and isinstance(self.sizes, np.ndarray):
    #             ignored = indices[self.sizes[indices] > max_sizes].tolist()
    #             indices = indices[self.sizes[indices] <= max_sizes]
    #         elif (
    #             hasattr(self, "sizes")
    #             and isinstance(self.sizes, list)
    #             and len(self.sizes) == 1
    #         ):
    #             ignored = indices[self.sizes[0][indices] > max_sizes].tolist()
    #             indices = indices[self.sizes[0][indices] <= max_sizes]
    #         else:
    #             indices, ignored = data_utils._filter_by_size_dynamic(
    #                 indices, self.size, max_sizes
    #             )
    #     else:
    #         indices, ignored = data_utils._filter_by_size_dynamic(
    #             indices, self.size, max_sizes
    #         )
    #     return indices, ignored

    @property
    def supports_fetch_outside_dataloader(self):
        """Whether this dataset supports fetching outside the workers of the dataloader."""
        return False

    # When this is called, the value be ready to be masked already
    # Only use the dict value on the embeddings
    @classmethod
    def mask_tree_item(cls, item, mask, mask_idx):
        """apply mask of length n to sequences of length n and adjacency matrix of size n x n, padded to size MAX_DIM x MAX_DIM"""

        converted_mask = (~torch.from_numpy(mask.astype(bool))).to(dtype=torch.float32).unsqueeze(1)
        tensor_item = torch.from_numpy(item).to(dtype=torch.float32)

        tensor_item *= converted_mask

        indices = [i for i in range(len(tensor_item)) if tensor_item[i][0] == 0]

        tensor_item[indices] += torch.full([1, 768], mask_idx)

        return tensor_item

    def pad_2d(self, x):
        # x = x + 1
        result = np.zeros((self.MAX_DIM, self.MAX_DIM))
        result[:x.shape[0], :x.shape[1]] = x
        return result

    def pad_1d(self, x):
        x = x + 1
        result = np.full(self.MAX_DIM, self.dictionary.pad())
        # print(x.shape)
        # print(result.shape)
        result[:len(x)] = x
        return result

# class FairseqIterableDataset(torch.utils.data.IterableDataset, EpochListening):
#     """
#     For datasets that need to be read sequentially, usually because the data is
#     being streamed or otherwise can't be manipulated on a single machine.
#     """
#
#     def __iter__(self):
#         raise NotImplementedError
