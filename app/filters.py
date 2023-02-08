import ast


def tolist(input):
    """convert string representation of list to a list"""
    return ast.literal_eval(input)
