import ast
import collections


BlacklistMatch = collections.namedtuple("BlacklistMatch", ["filename", "linenumber", "line_content", "description"])

# TODO: in debug mode, show warning when supplying a blacklist with no check_files, use an assert for now
def get_blacklist_matches(blacklist):
    """
    Search all files in blacklist["check_files"] for blacklisted node names defined in blacklist["node_names"] and blacklisted node dumps in blacklist["node_dumps"].
    See the settings.yaml for examples and format.

    Matches are returned in a list of BlacklistMatch objects/namedtuples.
    If linenumbers are not valid for some node (e.g. function arguments node), -1 is used as the linenumber.
    """
    assert blacklist["check_files"] # TODO

    matches = []
    blacklisted_names = blacklist["node_names"].keys()
    blacklisted_dumps = blacklist["node_dumps"].keys()

    for filename in blacklist["check_files"]:
        # TODO: OSErrors not catched
        with open(filename, encoding="utf-8") as submitted_file:
            source = submitted_file.read()

        # TODO: SyntaxErrors not catched
        submitted_ast = ast.parse(source)
        submitted_lines = source.splitlines()

        # Walk once through the ast of the source of the submitted file, searching for blacklisted stuff.
        for node in ast.walk(submitted_ast):
            node_name = node.__class__.__name__
            node_dump = ast.dump(node)
            linenumber = getattr(node, "lineno", -1)
            line_content = submitted_lines[linenumber-1] if linenumber > 0 else ""
            if node_name in blacklisted_names:
                matches.append(BlacklistMatch(
                        filename=filename,
                        linenumber=linenumber,
                        line_content=line_content,
                        description=blacklist["node_names"][node_name]))
            if node_dump in blacklisted_dumps:
                matches.append(BlacklistMatch(
                        filename=filename,
                        linenumber=linenumber,
                        line_content=line_content,
                        description=blacklist["node_dumps"][node_dump]))

    return matches

