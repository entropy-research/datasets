from ..TreeNode import TreeNode


class CodeNode(TreeNode):

    def __init__(self,
                 name,
                 params,
                 body,
                 def_type,
                 short_repr=None,
                 prediction_repr=None
    ):
        super().__init__()
        self.body = body
        self.name = name
        self.params = params
        self.type = def_type
        self._short_repr = short_repr
        self._pred_repr = prediction_repr
        self.depth = 0

    def short_repr(self):
        if self._short_repr == None:
            self._short_repr = self.name + (" | " + ", ".join(self.params) if self.params is not None and len(self.params) > 0 else "")

        return self._short_repr

    def prediction_repr(self):
        return self._pred_repr

