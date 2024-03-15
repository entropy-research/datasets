Learnings:
1. Call tree != def tree
2. Scoped References are hard (even when limited to local scope)
3. Need both a compositional vectorDB/hashtable that manages the Nodes themselves AND something that dynamically builds inputs based on the call tree
4. There are multiple parts of the process
    1. (Specific) Split input into a local reference tree on some boundary (e.g. function defs, expressions etc.), determine global data
    2. (Specific) Capture child node references (i.e. call tree but only one level treating it as root)
    2. (Interface) Assign each node its own entry in a data structure
        1. Each node needs a short representation
        2. Each node needs a prediction/loss representation
        3. Each node needs an embedding representation
        4. Each node needs an Embedding
        5. Each node needs child references
    3. (Generic) Build table based on reference/call trees for each one -> these are the instances that you compose to/ are tree data that is composed
    4. (Generic) Need this to determine dynamically the calls etc.
    5. (Generic) once the trees are built, iterate through sorted list. This is a stateless system., this runs for each table element
        1. start from shallowest reference trees and build to deepest (cant guarantee correct order but can guarantee priority)
        2. each tree is an input, use the node references to generate node shortnames in bfs order.