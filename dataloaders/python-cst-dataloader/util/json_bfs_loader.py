from collections import deque

# Sample JSON tree structure. This is a Dict with nodes specified as follows
# a node is defined by

"""
    This BFS traversal is designed to work with the TreeShard class.
    It takes a tree defined by nodes that look like: 
        { 
            __data__: (data), 
            __children__: [{child}]
        }
    
    It returns:
    - data_list: a list in bfs order of the data elements in the tree 
    - depth_list: a bfs ordered list of the depths of the respective nodes
    - subtrees: 
        a bfs ordered list of subtrees where the subtrees are a 
        list of global bfs node numbers up to a certain node count
    - max_depth: the max depth in the list
    
    The fact that we are not using a node class may look stupid. It probably is.
    There is some memory efficiency to it though. Management may be harder.
    
    May be better to just do a bfs pass first and then do data extraction via dfs
    
"""

def bfs_traversal(tree, node_limit):
    data_list = []
    depth_list = []
    subtrees = []
    max_depth = -1
    queue = deque([(tree, 0)])

    tree["depth"] = 0

    while queue:
        current_node, bfs_number = queue.popleft()
        data_list.append(current_node["__data__"])
        depth = current_node["depth"]
        depth_list.append(depth)
        if depth > max_depth:
            max_depth = depth
        current_node["bfs_number"] = len(data_list) - 1

        for child in current_node["__children__"]:
            child["depth"] = depth + 1
            new_bfs_number = len(data_list)
            queue.append((child, new_bfs_number))

    queue = deque([(tree, -1)])

    while queue:
        current_node, bfs_number = queue.popleft()
        subtrees.append(capped_bfs(current_node, node_limit))

        for child in current_node["__children__"]:
            new_bfs_number = len(data_list)
            queue.append((child, new_bfs_number))

    return data_list, depth_list, subtrees, max_depth

def capped_bfs(tree, node_limit):
    bfs_list = []
    queue = deque([tree])

    while queue and len(bfs_list) < node_limit:
        current_node = queue.popleft()
        bfs_list.append(current_node["bfs_number"])

        for child in current_node["__children__"]:
            queue.append(child)

    return bfs_list