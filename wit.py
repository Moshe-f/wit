# A project that allows version control, backup and 
# tracking of projects(similar to GIT).
# Supports the following commands:
# init, add, commit, status, checkout, graph, branch and merge.
# An exercise from Yam Mesica Python course.


from datetime import datetime
import filecmp
import os
import random
import shutil
import sys
import time
from typing import Iterator

import graphviz


BASE_FOLDER_NAME: str = ".wit"
SUB_FOLDER_NAMES: dict[str, str] = {"images": "images", 
                                    "staging_area": "staging_area"}


def find_wit_folder() -> None:
    """Find `.wit` folder."""
    while BASE_FOLDER_NAME not in os.listdir():
        os.chdir("..")
        if os.getcwd() == os.path.abspath(os.sep):
            raise FileNotFoundError("not a wit repository (or any of the parent directories): .wit")


def update_activated_branch_file(branch: str) -> None:
    """Update activated branch file."""
    with open(os.path.join(BASE_FOLDER_NAME, "activated.txt"), "w") as f:
        f.write(branch)


def init() -> None:
    """Initializing wit in current folder."""
    os.mkdir(BASE_FOLDER_NAME)
    for folder in SUB_FOLDER_NAMES.values():
        os.mkdir(os.path.join(BASE_FOLDER_NAME, folder))
    update_activated_branch_file("master")
    print(f"Initialized empty wit repository in {os.getcwd()}")


def get_new_folder_name() -> str:
    """Return new folder image name."""
    characters: str = "1234567890abcdef"
    folder_name_len: int = 40
    while True:
        folder_name: str = "".join(random.choices(characters, k=folder_name_len))
        if folder_name not in os.listdir():
            return folder_name
        

def add(path: str) -> None:
    """Adding the tree folders of the path to the `staging_area`."""
    if path == ".":
        path = os.getcwd()
    source_path: str = os.path.abspath(path)
    base: str = os.path.basename(source_path)
    if base == BASE_FOLDER_NAME:
        raise ValueError(f"Do not back up the `{BASE_FOLDER_NAME}` folder itself.")
    # To search `.wit` folder from the folder source path.
    if os.path.isfile(source_path):
        os.chdir(source_path.removesuffix(base))
    else:
        os.chdir(source_path)
    find_wit_folder()
    destination_path: str = os.path.join(os.getcwd(), ".wit", "staging_area", os.path.relpath(source_path))
    if os.path.isdir(source_path):
        shutil.copytree(source_path, destination_path, ignore=lambda x, y : BASE_FOLDER_NAME, dirs_exist_ok=True)
    else:
        os.makedirs(destination_path.removesuffix(base), exist_ok=True)
        shutil.copy2(source_path, destination_path)


def get_activated_branch() -> str:
    """Return the activated branch."""
    try:
        with open(os.path.join(BASE_FOLDER_NAME, "activated.txt"), "r") as f:
            return f.read().strip()
    except FileNotFoundError:
        return ""


def get_references_data() -> dict[str, str | None]:
    """Return the data from references file."""
    references_data: dict[str, str | None] = {"HEAD": None, 
                                              "master": None}
    try:
        with open(os.path.join(BASE_FOLDER_NAME, "references.txt"), "r") as file:
            file_data: list[str] = file.read().strip().split("\n")
            for line in file_data:
                line: list[str, str] = line.split("=")
                references_data[line[0]] = line[1]
    except FileNotFoundError:
        pass
    return references_data


def update_references_file(references_data: dict[str, str]) -> None:
    """Update references file.

    Args:
        references_data (dict): All data: HEAD, master and branches.
    """
    with open(os.path.join(BASE_FOLDER_NAME, "references.txt"), "w") as file:
        for key, value in references_data.items():
            file.write(f"{key}={value}\n")


def check_for_commits() -> None:
    """Raise error if no commits have been made yet."""
    references_data: dict[str, str | None] = get_references_data()
    parent: str = references_data["HEAD"]
    if parent is None:
        raise FileNotFoundError("No commits have been made yet.")


def create_files_list(folder: str, ignore: str = None) -> list[str]:
    """Return list with all sub files in the folder."""
    result: list[str] = []
    for dir, _, files in os.walk(folder):
        if ignore is None or not dir.startswith(ignore):
            for file in files:
                result.append(os.path.relpath(os.path.join(dir, file), folder))
    return result


def get_short_commit_name(commit_name: str) -> str:
    """Return first 6 letters in the commit ID."""
    return commit_name[:6]


def get_status(source_path: str = None, stage_path: str = None, commit_path: str = None) -> dict[str, list[str] | str | None]:
    """Return the current state of your wit working directory and staging area.

    Args:
        source_path (str, optional): Source folder path. Defaults to None.
        stage_path (str, optional): Stage folder path. Defaults to None.
        commit_path (str, optional): Last commit folder path. Defaults to None.

    Returns:
        dict[str, list[str] | str | None]: Status.
    """
    find_wit_folder()
    references_data: dict[str, str | None] = get_references_data()
    parent: str = references_data["HEAD"]
    source_path: str = source_path or os.getcwd()
    stage_path: str = stage_path or os.path.join(source_path, BASE_FOLDER_NAME, SUB_FOLDER_NAMES["staging_area"])
    commit_path: str = commit_path or os.path.join(source_path, BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"], parent or "")
    all_status: dict[str, list[str] | str | None] = {
                  "Current commit:": parent, 
                  "Changes to be committed:": [], 
                  "Changes not staged for commit:": [], 
                  "Untracked files:": [], 
                  }
    source_files: list[str] = create_files_list(source_path, os.path.join(source_path, BASE_FOLDER_NAME))
    stage_files: list[str] = create_files_list(stage_path)
    commit_files: list[str] = create_files_list(commit_path)
    for file in stage_files:
        if file not in commit_files:
            all_status["Changes to be committed:"].append(file)
        elif not filecmp.cmp(os.path.join(stage_path, file), os.path.join(commit_path, file)):
                all_status["Changes to be committed:"].append(file)
        if file in source_files:
            if not filecmp.cmp(os.path.join(source_path, file), os.path.join(stage_path, file)):
                all_status["Changes not staged for commit:"].append(file)
            source_files.remove(file)
    all_status["Untracked files:"] = source_files
    return all_status


def create_commit_file_data(folder_path: str, parent: str, message: str, second_parent: str | None = None) -> None:
    """Write commit data file.

    Args:
        folder_path (str): Commit name with path.
        parent (str): Parent of commit.
        message (str): Commit description.
        second_parent (str, optional): Second parent. Defaults to None.

    Returns:
        None.
    """
    if second_parent is not None:
        parent += f", {second_parent}"
    with open(f"{folder_path}.txt", "w") as file:
        file.write(f"""parent={parent}\ndate={datetime.now():%a %b %d %H:%M:%S %Y} {time.strftime("%z")}\nmessage={message}""")

    
def commit(message: str, second_parent: str | None = None) -> None:
    """Commit the changes to images folder.

    Args:
        message (str): Commit description.
        second_parent (str | None, optional): Second parent. Defaults to None.

    Raises:
        FileExistsError: If nothing added to commit or commit already exist.
    """
    find_wit_folder()
    source_path: str = os.path.abspath(os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["staging_area"]))
    destination_path: str = os.path.abspath(os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"]))
    references_data: dict[str, str | None] = get_references_data()
    parent: str = references_data["HEAD"]
    status: dict[str, list[str] | str | None] = get_status()
    if status["Current commit:"] is None and status["Changes to be committed:"] == []:
        raise FileExistsError("Nothing added to commit (use `wit add` to track).")
    if status["Changes to be committed:"] == []:
        raise FileExistsError("Image already exist.")
    folder_name: str = get_new_folder_name()
    folder_path: str = os.path.join(destination_path, folder_name)
    create_commit_file_data(folder_path, parent, message, second_parent)
    shutil.copytree(source_path, folder_path, dirs_exist_ok=True)
    references_data["HEAD"] = folder_name
    current_branch: str = get_activated_branch()
    if references_data.get(current_branch, "") == parent:
        references_data[current_branch] = folder_name
    update_references_file(references_data)
    print(f"New commit created: {get_short_commit_name(folder_name)}")


def print_status() -> None:
    """Prints the current state of your wit working directory and staging area."""
    status_data: dict[str, list[str] | str | None] = get_status()
    for state, data in status_data.items():
        print(state)
        if isinstance(data, list) and data != []:
            for file in data:
                print(f"\t{os.path.relpath(file)}")
        else:
            print(f"\t{data or None}")
        print()


def update_stage_area(source_path: str) -> None:
    """Replace current files in stage area with updated files.

    Args:
        source_path (str): Path of new content.
    """
    staging_area: str = os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["staging_area"])
    shutil.rmtree(staging_area)
    shutil.copytree(source_path, staging_area)


def check_for_changes(status_data: dict[str, list[str] | str | None]) -> None:
    """Prints error if There are files that have not yet been add/commit.

    Args:
        status_data (dict[str, list[str]  |  str  |  None]): Current status.
    """
    if status_data["Changes to be committed:"] != [] or status_data["Changes not staged for commit:"] != []:
        raise ValueError("ERROR! \nThere are files that have not yet been add/commit. \nPlease run add/commit commands and try again.")


def checkout(id: str, ignore: bool = False) -> None:
    """Updates files in the working tree to match the version in the id.

    Args:
        id (str): The id or name of commit.
        ignore (bool, optional): Whether to check if there are changes or not (used in merge commends). Defaults to False.
    """
    find_wit_folder()
    check_for_commits()
    id = id.lower()
    references_data: dict[str, str | None] = get_references_data()
    if id in references_data.keys():
        update_activated_branch_file(id)
        id = references_data[id]
    else:
        update_activated_branch_file("")
    source_path: str = os.path.abspath(os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"], id))
    destination_path: str = os.getcwd()
    status_data: dict[str, list[str] | str | None] = get_status()
    if not ignore:
        check_for_changes(status_data)
    base_folder: str = os.path.join(destination_path, BASE_FOLDER_NAME)
    for dir, _, files in os.walk(destination_path, topdown=False):
        if not dir.startswith(base_folder):
            for file in files:
                file_in_stage = os.path.join(dir, file)
                if os.path.relpath(file_in_stage, destination_path) not in status_data["Untracked files:"]:
                    os.remove(file_in_stage)
            if len(os.listdir(dir)) == 0 and dir != destination_path:
                os.rmdir(dir)
    shutil.copytree(source_path, destination_path, dirs_exist_ok=True)
    references_data["HEAD"] = id
    update_references_file(references_data)
    update_stage_area(source_path)


def get_parent(commit: str) -> list[str]:
    """Return commit parent\s."""
    try:
        with open(os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"], f"{commit}.txt"), "r") as file:
            file_data: list = file.read().split("\n")
            return file_data[0].removeprefix("parent=").split(", ")
    except FileNotFoundError:
        raise FileNotFoundError("Commit data not found.")


def get_current_commit_tree(head: str, distance: int = 0) -> list[tuple[str, str, int]]:
    """Get current commit tree.

    Args:
        head (str): Head of tree.
        distance (int, optional): distance between head and parent. Defaults to 0.

    Returns:
        list[tuple[str, str, int]]: Tree of commits(commit, parent, distance).
    """
    commit_tree: list[tuple[str, str, int]] = []
    file: str = head
    while file != "None":
        parent: list[str] = get_parent(file)
        if len(parent) > 1:
            commit_tree.append((file, parent[1], distance))
            commit_tree.extend(get_current_commit_tree(parent.pop(1), distance))
        commit_tree.append((file, parent[0], distance))
        file = parent[0]
        distance += 1
    return commit_tree


def get_all_commit_tree() -> list[tuple[str, str, int]]:
    """Get all trees of all commits.

    Returns:
        list[tuple[str, str, int]]: Trees of commits(commit, parent, distance=0).
    """
    dir: str = os.path.join(os.getcwd(), BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"])
    commit_tree: list[tuple[str, str, int]] = []
    for file in os.listdir(dir):
        if os.path.isdir(os.path.join(dir, file)):
            parent = get_parent(file)
            if len(parent) > 1:
                commit_tree.append((file, parent[1], 0))
            commit_tree.append((file, parent[0], 0))
    return commit_tree


def show_graph(all: bool = False) -> None:
    """Show commit graph.

    Args:
        all (bool, optional): If True show all commits trees. Defaults to False.
    """
    find_wit_folder()
    check_for_commits()
    references_data: dict[str, str | None] = get_references_data()
    head: str = references_data["HEAD"]
    if all:
        all_commits_and_parent: list[tuple[str, str], int] = get_all_commit_tree()
    else:
        all_commits_and_parent: list[tuple[str, str, int]] = get_current_commit_tree(head)
    dot = graphviz.Digraph(directory=os.path.abspath(os.path.join(BASE_FOLDER_NAME, "graphs")))
    dot.attr(rankdir="RL")
    dot.attr("node", style="filled", color="Aqua", shape="circle")
    dot.attr("edge", style="bold")
    all_commit: set[str] = set()
    for commit, parent, _ in all_commits_and_parent:
        dot.node(commit, commit[:6])
        all_commit.add(commit)
        if parent != "None":
            dot.node(parent, parent[:6])
            dot.edge(commit, parent)
    for name in references_data.keys():
        if references_data[name] in all_commit:
            dot.node(name, "", style="invis")
            dot.edge(name, references_data[name], label=name)
    dot.view()


def branch(name: str) -> None:
    """Create a branch."""
    find_wit_folder()
    name = name.lower()
    references_data: dict[str, str | None] = get_references_data()
    if name in references_data.keys() or \
       name in os.listdir(os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"])):
        print("The branch name already taken.\nPlease try different name.")
        return
    references_data[name] = references_data["HEAD"]
    update_references_file(references_data)
    print(f"New branch created: `{name}`.\nUse `checkout {name}` to activate.")


def file_lines_generator(file_path: str) -> Iterator[str]:
    """Yield lines from file.

    Args:
        file_path (str): File path.

    Yields:
        Iterator[str]: Line.
    """
    try:
        # utf-8 or cp862 and still sometimes there are Errors.
        with open(file_path, "r", encoding="utf-8") as file:
            file: list[str] = file.readlines()
        for line in file:
            yield line
    except FileNotFoundError:
        yield ""


def merge_files_by_lines(current_file_path: str, merge_file_path: str, parent_file_path: str, last_commit: str) -> None:
    """Merge two files into one version by compare lines.

    Args:
        current_file_path (str): The current file.
        merge_file_path (str): The file to merge into current file.
        parent_file_path (str): The common base file for merge and current.
        last_commit (str): The last commit id.
    """
    current_file: Iterator[str] = file_lines_generator(current_file_path)
    merge_file: Iterator[str] = file_lines_generator(merge_file_path)
    parent_file: Iterator[str] = file_lines_generator(parent_file_path)
    fixed_file: str = ""
    for merge_file_line in merge_file:
        try:
            parent_file_line: str = next(parent_file)
        except StopIteration:
            parent_file_line = ""
        try:
            current_file_line: str = next(current_file)
        except StopIteration:
            current_file_line = ""
        if merge_file_line == current_file_line:
            fixed_file += merge_file_line
        elif merge_file_line == parent_file_line:
            fixed_file += current_file_line
        elif current_file_line == parent_file_line:
            fixed_file += merge_file_line
        else:
            update_stage_area(os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"], last_commit))
            raise ValueError(f"Conflict between file -> `{os.path.basename(current_file_path)}`")
    for line in current_file:
        fixed_file += line
    with open(current_file_path, "w") as file:
        file.write(fixed_file)


def merge_files_by_data(current_file_in_stage: str, file_path_in_commit_to_merge: str, file_path_in_shared_parent: str, last_commit: str) -> None:
    """Merge two files by compare there data.

    Args:
        current_file_in_stage (str): The current file.
        file_path_in_commit_to_merge (str): The file to merge into current file.
        file_path_in_shared_parent (str): The common base file for merge and current.
        last_commit (str): The last commit id.
    """
    if filecmp.cmp(current_file_in_stage, file_path_in_commit_to_merge):
        shutil.copy2(file_path_in_commit_to_merge, current_file_in_stage)
    elif filecmp.cmp(current_file_in_stage, file_path_in_shared_parent):
        shutil.copy2(file_path_in_commit_to_merge, current_file_in_stage)
    elif filecmp.cmp(file_path_in_commit_to_merge, file_path_in_shared_parent):
        shutil.copy2(current_file_in_stage, current_file_in_stage)
    else:
        update_stage_area(os.path.join(BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"], last_commit))
        raise ValueError(f"Conflict between file -> `{os.path.basename(current_file_in_stage)}`")


def get_shared_parent(name: str) -> str:
    """get commits shared parent."""
    references_data: dict[str, str | None] = get_references_data()
    current_commit: list[tuple[str, str, int]] = get_current_commit_tree(references_data["HEAD"])
    name_commit: list[tuple[str, str, int]] = get_current_commit_tree(name)
    shared_parent: str = ""
    shared_parent_distance: int = len(current_commit)+ len(name_commit)
    for commit, _, distance in current_commit:
        for parent, _, distance_2 in name_commit:
            distance_between: int = distance + distance_2
            if commit == parent and distance_between < shared_parent_distance:
                shared_parent = commit
                shared_parent_distance = distance_between
    return shared_parent


def merge(name_to_merge: str) -> None:
    """Merge between two branches\commits."""
    find_wit_folder()
    check_for_commits()
    status_data: dict[str, list[str] | str | None] = get_status()
    check_for_changes(status_data)
    commit_to_merge = name_to_merge.lower()
    references_data: dict[str, str | None] = get_references_data()
    if commit_to_merge in references_data.keys():
        commit_to_merge = references_data[commit_to_merge]
    if status_data["Current commit:"] == commit_to_merge:
        return
    shared_parent: str = get_shared_parent(commit_to_merge)
    commit_to_merge_path: str = os.path.join(os.getcwd(), BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"], commit_to_merge)
    shared_parent_path: str = os.path.join(os.getcwd(), BASE_FOLDER_NAME, SUB_FOLDER_NAMES["images"], shared_parent)
    status = get_status(commit_to_merge_path, shared_parent_path, "")
    current_commit_and_destination_path: str = os.path.join(os.getcwd(), BASE_FOLDER_NAME, SUB_FOLDER_NAMES["staging_area"])
    all_changes: list[str] = status["Changes not staged for commit:"] + status["Untracked files:"]
    for file in all_changes:
        current_file_in_stage: str = os.path.join(current_commit_and_destination_path, file)
        file_path_in_commit_to_merge: str = os.path.join(commit_to_merge_path, file)
        if os.path.exists(current_file_in_stage):
            file_path_in_shared_parent: str = os.path.join(shared_parent_path, file)
            try:
                with open(current_file_in_stage, "r", encoding="utf-8") as f:
                    f.readline()
            except UnicodeDecodeError:
                merge_files_by_data(current_file_in_stage, file_path_in_commit_to_merge, file_path_in_shared_parent, status_data["Current commit:"])
            else:
                merge_files_by_lines(current_file_in_stage, file_path_in_commit_to_merge, file_path_in_shared_parent, status_data["Current commit:"])
        else:
            os.makedirs(current_file_in_stage.removesuffix(os.path.basename(file)), exist_ok=True)
            shutil.copy2(file_path_in_commit_to_merge, current_file_in_stage)
    commit(f"Merge {commit_to_merge} with {status['Current commit:']}", commit_to_merge)
    status = get_status()
    checkout(status['Current commit:'], ignore=True)


def print_wit_welcome() -> None:
    """Print wit welcome message."""
    print("""Welcome to wit. 
is a version control system that tracks changes in any set of computer files,
usually used for coordinating work among programmers who are collaboratively developing source code during software development.
              
Use: python `wit_path` <commend> <argument>

Supports the following commands:
init, add <path>, commit <message>, status, checkout <commit\\branch>, graph(--all, optional), branch <commit\\branch>, merge <commit\\branch>""")


def main(args):
    if len(args) < 2:
        print_wit_welcome()
        return
    if args[1] == "init":
        init()
    elif args[1] == "add":
        if len(args) < 3:
            raise TypeError("`add` commend missing 1 required argument - `path`.")
        add(args[2])
    elif args[1] == "commit":
        if len(args) < 3:
            raise TypeError("`commit` commend missing 1 required argument - `message`.")
        commit(args[2])
    elif args[1] == "status":
        print_status()
    elif args[1] == "checkout":
        if len(args) < 3:
            raise TypeError("`checkout` commend missing 1 required argument - `commit ID`.")
        checkout(args[2])
    elif args[1] == "graph":
        if len(args) == 3 and args[2] == "--all":
            show_graph(True)
        else:
            show_graph()
    elif args[1] == "branch":
        if len(args) < 3:
            raise TypeError("`branch` commend missing 1 required argument - `NAME`.")
        branch(args[2])
    elif args[1] == "merge":
        if len(args) < 3:
            raise TypeError("`merge` commend missing 1 required argument - `BRANCH_NAME`.")
        merge(args[2])
    else:
        print("Commend not found.")


if __name__ == "__main__":
    main(sys.argv)
