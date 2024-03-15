from datetime import datetime
from git import Repo
import ast
import os
import networkx as nx
from networkx import DiGraph
import tempfile
import shutil
from urllib.parse import urlparse
import re

def clone_repository(repo_url, dest_folder):
    Repo.clone_from(repo_url, dest_folder)

def build_local_import_map(root_dir):
    """
    Build a map of importable module names to their file paths.
    """
    import_map = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):

        for file in filenames:

            if file.endswith('.py'):
                file_path = os.path.join(dirpath, file)
                relpath = os.path.relpath(file_path, root_dir)
                module_file = relpath.replace(os.path.sep, '.')
                module_path = module_file.rstrip(".py").lstrip("lib.")

                if module_path.endswith('.__init__'):
                    module_path = module_path[:-9]  # Strip out .__init__ to handle package imports

                # print(module_path)
                import_map[module_path] = file_path

    # print(len(list(import_map.items())))

    return import_map

def is_local_import(import_name, import_map):
    """
    Check if an import name corresponds to a local module.
    """

    # if "platform" in import_name and not import_name in import_map:
    #     print(import_name)

    return import_name in import_map

def scan_for_imports_filtered(root_dir):
    """
    Scan for Python files and filter imports to only include those that are local.
    """
    local_files = {}
    import_map = build_local_import_map(root_dir)
    
    for import_path, file_path in import_map.items():
        try:
            with open(file_path, 'r') as file:
                tree = ast.parse(file.read(), filename=file_path)
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if is_local_import(alias.name, import_map):
                            imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module if node.module else ''
                    for alias in node.names:
                        # Construct full import path
                        full_import = f"{module}" if module else alias.name
                        # Check if the full import or the base module is local
                        # print(full_import)
                        # if full_import == "ansible.errors":
                        #     print("ansible.errors" in import_map)
                        if is_local_import(full_import, import_map) or is_local_import(module, import_map):
                            imports.append(full_import)

            local_files[file_path] = imports
        except:
            continue
    
    return local_files

def parse_python_file(file_path):
    with open(file_path, 'r') as file:
        return ast.parse(file.read(), filename=file_path)

def build_import_map(root_dir):
    import_map = {}
    for root, dirs, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                module_path = os.path.relpath(file_path, root_dir).replace(os.path.sep, '.').rstrip('.py').lstrip('lib.')
                if file == '__init__.py':
                    module_path = module_path.rsplit('.', 1)[0]  # Use package name for __init__.py
                import_map[module_path] = file_path
    return import_map

def is_relative_import(level):
    return level > 0

def resolve_module_path(base_path, relative_path):
    base_parts = base_path.split('.')[:-1]  # Remove the last segment if it's a file
    relative_parts = relative_path.split('.')
    return '.'.join(base_parts + relative_parts)

def resolve_exports_from_init(import_map, root_dir):
    resolved_map = {}
    for module_path, file_path in import_map.items():
        if file_path.endswith('__init__.py'):
            try:
                tree = parse_python_file(file_path)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ImportFrom):
                        relative_path = node.module if node.module else ''
                        if is_relative_import(node.level):
                            full_import_path = resolve_module_path(module_path, '.' * (node.level - 1) + relative_path)
                        else:
                            full_import_path = relative_path

                        # Handle the case where an import in __init__.py refers to another module within the same package
                        if full_import_path in import_map:
                            resolved_path = import_map[full_import_path]
                            for alias in node.names:
                                # Generate the alias path if necessary
                                alias_import_path = module_path + '.' + alias.name if alias.asname else full_import_path
                                resolved_map[alias_import_path] = resolved_path
            except:
                continue
    # Update the original import map with resolved paths
    import_map.update(resolved_map)

def build_exhaustive_import_list(root_dir):
    import_map = build_import_map(root_dir)
    resolve_exports_from_init(import_map, root_dir)
    return import_map

def map_local_imports_to_paths(local_imports, import_map):

    new_file_map = {}
    for file, imports in local_imports.items():
        new_import_list = []

        for imp in imports:
            if imp in import_map:
                new_import_list.append(import_map[imp])
        
        if len(new_import_list) > 0:
            new_file_map[file] = new_import_list
    
    return new_file_map

def build_dependency_graph(local_files):
    graph = nx.DiGraph()

    # Add nodes and edges based on dependencies
    for module, deps in local_files.items():
        if not graph.has_node(module):
            graph.add_node(module)  # Ensure the module is added as a node

        for dep in deps:
            if not graph.has_node(dep):
                graph.add_node(dep)  # Ensure the dependency is also added as a node

            # Temporarily add edge to check for cycles
            graph.add_edge(module, dep)

            # Check if the current edge creates a cycle
            try:
                # This will raise an exception if a cycle is found
                nx.find_cycle(graph, source=module)

                # If a cycle is found, remove the edge
                graph.remove_edge(module, dep)
                print(f"Cycle detected! Edge from {module} to {dep} was not added.")
            except nx.NetworkXNoCycle:
                # No cycle was found, edge remains in the graph
                continue

    return graph

# def find_subgraphs(graph):

#     # Find strongly connected components
#     scc = list(nx.strongly_connected_components(graph))

#     # This will store the topologically sorted lists of nodes for each subgraph
#     sorted_subgraphs = []

#     for component in scc:
#         subgraph = graph.subgraph(component)
        
#         # Check if the subgraph is a DAG (has no cycles)
#         if nx.is_directed_acyclic_graph(subgraph):
#             # Topologically sort the subgraph
#             sorted_nodes = list(nx.topological_sort(subgraph))
#             if len(sorted_nodes) > 1:
#                 sorted_subgraphs.append(sorted_nodes)
#         else:
#             # Handle non-DAG components, e.g., by breaking cycles or ignoring
#             print("Found a non-DAG component, handling needed:", component)

#     return sorted_subgraphs


def calculate_character_count(imps):
    total_chars = 0
    for imp in imps:
        if os.path.isfile(imp):
            with open(imp, 'r', encoding='utf-8') as file:
                total_chars += len(file.read())
        
    return total_chars

def extract_subgraphs_within_char_limit(G: DiGraph, min_char_count):
    subgraphs = []

    for node in  G.copy().nodes:
        if node in G:
            reachable_nodes = nx.descendants(G, node) | {node}  # Include the start node itself
            reachable_subgraph = G.subgraph(reachable_nodes).copy()

            char_count = calculate_character_count(reachable_subgraph.nodes)
            nodes_sorted = list(nx.topological_sort(reachable_subgraph))

            # Calculate character count for the subgraph
            if min_char_count <= char_count and len(nodes_sorted) >= 1:
                # print(char_count)
                # Convert subgraph nodes to a list and store
                subgraphs.append(nodes_sorted)
                # Remove the nodes of this subgraph from the main graph
                for node in reachable_nodes:
                    try:
                        G.remove_node(node)
                    except Exception as e:
                        continue

    return subgraphs


def serialize_file(file_path):
        """Serialize code from a file, skipping leading comments before the first and trailing comments after the last function/class definition."""
        with open(file_path, 'r') as f:
            content = f.read()

        # Parse the AST tree to find the first and last function or class definition
        tree = ast.parse(content)
        first_def_pos = None
        last_def_end_pos = None
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if first_def_pos is None:
                    first_def_pos = node.lineno - 1  # lineno is 1-indexed, convert to 0-indexed
                # Update last_def_end_pos to the latest function/class definition
                last_def_end_pos = node.end_lineno  # end_lineno is inclusive and 1-indexed

        # Adjust content based on the positions of the first and last definitions
        if first_def_pos is not None and last_def_end_pos is not None:
            lines = content.splitlines()
            trimmed_content = '\n'.join(lines[first_def_pos:last_def_end_pos])
            return trimmed_content
        else:
            # If there's no function or class definition, return the whole content
            return content

def serialize_code_from_subgraphs(subgraphs):
    examples = []

    for subgraph in subgraphs:
        serialized_code = ""
        for import_name in subgraph:
            if os.path.isfile(import_name):
                file_path = import_name
                # print(file_path)

                with open(file_path, 'r') as f:
                    content = f.read()

                # Parse the AST tree to find the first and last function or class definition
                tree = ast.parse(content)
                first_def_pos = None
                last_def_end_pos = None
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        if first_def_pos is None:
                            first_def_pos = node.lineno - 1  # lineno is 1-indexed, convert to 0-indexed
                        # Update last_def_end_pos to the latest function/class definition
                        last_def_end_pos = node.end_lineno  # end_lineno is inclusive and 1-indexed

                # Adjust content based on the positions of the first and last definitions
                if first_def_pos is not None and last_def_end_pos is not None:
                    lines = content.splitlines()
                    trimmed_content = '\n'.join(lines[first_def_pos:last_def_end_pos])

                    serialized_code += trimmed_content + "\n\n"
                else:
                    continue
        
        examples.append(serialized_code)

    return examples

def create_output_files(output_files, output_dir, base_filename="omegacode"):
    """
    Concatenates the content of multiple Python files and writes the result to a uniquely named file in an output directory.

    Parameters:
    - sorted_files: A list of absolute file paths to Python files.
    - output_dir: The directory where the output file will be saved.
    - base_filename: (Optional) Base name for the output files. A timestamp will be appended to make each filename unique.
    """
    # Ensure the output directory exists, create if necessary
    os.makedirs(output_dir, exist_ok=True)

    i = 0

    for file in output_files:
        # Generate a unique filename for this run
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        output_file_path = os.path.join(output_dir, f"{base_filename}_{i}.py")

        # Write the serialized code to the generated output file
        try:
            with open(output_file_path, 'w', encoding='utf-8') as output_file:
                output_file.write(file)
            print(f"Serialized code successfully written to {output_file_path}")
            i += 1

        except IOError as e:
            print(f"Error writing to file {output_file_path}: {e}")

def generate_code_from_repo(link, char_range_min, output_folder, base_filename):

    # Use a temporary directory for the clone
    with tempfile.TemporaryDirectory() as temp_dir:
        dest_folder = temp_dir

        clone_repository(link, dest_folder)
        
        local_imports = scan_for_imports_filtered(dest_folder)
        
        import_map = build_exhaustive_import_list(dest_folder)

        resolved_map = map_local_imports_to_paths(local_imports, import_map)

        dependency_graph = build_dependency_graph(resolved_map)

        subgraphs = extract_subgraphs_within_char_limit(dependency_graph, char_range_min)

        serialized_code = serialize_code_from_subgraphs(subgraphs)

        print(len(serialized_code))

        # Ensure output_folder exists
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)

        create_output_files(serialized_code, output_dir=output_folder, base_filename=base_filename)


def get_repo_basename(repo_url):
    # Parse the given URL
    parsed_url = urlparse(repo_url)
    # Split the path on '/' and get the last part, which should be the repository name
    repo_name = parsed_url.path.rstrip('/').split('/')[-1].split(".")[0]
    return repo_name

# Function to convert URLs to .git format by matching from the beginning
def convert_urls_to_git(urls):
    git_urls = set()
    for url in urls:
        # Use regular expression to extract the relevant part of the URL
        match = re.match(r'https://github\.com/([^/]+/[^/]+)', url)
        if match:
            # Construct the .git URL
            # print(match)
            git_url = f"https://github.com/{match.group(1).strip()}.git"
        else:
            # If URL does not match expected pattern, keep it as is
            git_url = url
        
        git_urls.add(git_url)

    return git_urls

def convert_markdown_to_git_links(markdown_text):
    git_links = set()
    urls = re.findall(r'\(https://github.com/[^\s)]+\)', markdown_text)
    for url in urls:
        clean_url = url[1:-1]  # Remove parentheses
        if not clean_url.endswith('.git'):
            clean_url += '.git'
        git_links.add(clean_url)
    return git_links

if __name__ == "__main__":

    with open("./awesome_repos.txt", "r") as f:
        lines = f.read()
        converted_urls2 = convert_markdown_to_git_links(lines)

    with open("./github_repos.txt", "r") as f:
        lines = f.readlines()
        converted_urls = convert_urls_to_git(lines)

    repos = converted_urls2.union(converted_urls)

    char_range_min = 12000
    base_output_path = "./output/"

    for repo_url in converted_urls:
        basename = get_repo_basename(repo_url)
        generate_code_from_repo(repo_url, char_range_min, base_output_path + basename, base_filename=basename)
