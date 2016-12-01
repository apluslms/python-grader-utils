"""
Adapted from:
https://github.com/acos-server/acos-python-parser/blob/master/parser.py
"""

import ast

def simpleTraverse(node, nodes):
    """Traverse node, recording its name and line number into nodes dictionary.
    If the set of forbidden names in importvalidator is expanded,
    they should be included here.
    """

    name = node.__class__.__name__

    # Representations of 'name' as they will appear in nodes
    name_keys = []

    if name == 'Call':
        function_type = node.func.__class__.__name__
        if function_type == 'Attribute':
            name_keys.append('Call::' + node.func.attr)
        elif function_type == 'Name':
            name_keys.append('Call:' + node.func.id)

    elif name == 'Import':
        # Iterate in case there are comma separated imports
        for alias in node.names:
            name_keys.append('Import:' + alias.name)

    elif name == 'ImportFrom':
        name_keys.append('ImportFrom:' + node.module)

    # TODO: reversing by slicing (lst[::-1]) is currently not detected
    # This should be fixed by traversing the children of Subscript searching
    # for Slice nodes. Slice is Slice(lower, upper, step).
    # For lst[::-1], Slice(lower=None, upper=None, step=UnaryOp(USub, Num)),
    # i.e. Slice.step.op.__class__.__name__ == "USub" means operator - has been used
    # as step.
    #elif name == 'Subscript':
    #    name_keys.append('Subscript')
    #    childTraverse(node, nodes, lineno)

    else:
        name_keys.append(name)


    if hasattr(node, "lineno"):
        # Record all linenumbers this node corresponds to as a set of line numbers
        # e.g. line containing "2+2+2" is recorded as having only one '+' operator
        for key in name_keys:
            nodes.setdefault(key, set()).add(node.lineno)
    else:
        for key in name_keys:
            if key not in nodes:
                nodes[key] = None

    for child in ast.iter_child_nodes(node):
        simpleTraverse(child, nodes)


def traverse_source_string(source):
    """Return a dictionary where keys are names used in source and values
    are sets of line numbers where name was used in source."""

    tree = ast.parse(source)
    found = dict()

    for node in ast.iter_child_nodes(tree):
        simpleTraverse(node, found)

    return found

