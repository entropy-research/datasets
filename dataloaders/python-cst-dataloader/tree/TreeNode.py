

class TreeNode:

    """

    """

    def __init__(self):
        self._embedding = None
        self._children = []

    def get_embedding(self):
        return self._embedding

    def set_embedding(self, embedding):
        self._embedding = embedding

    def set_children(self, arr):
        self._children = arr

    def get_children(self):
        return self._children

    def short_repr(self):
        pass

    def prediction_repr(self):
        pass

    def embedding_repr(self):
        pass
