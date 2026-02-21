import os
import sys
from importlib import import_module

import interpreter.utils.settings as prefs
import libs.testium as tm

_cached_versions = {}

def repo_rev(path):
    ret = _cached_versions.get(path, None)
    if ret:
        return ret
    git = import_module("git")
    repo = git.Repo(path, search_parent_directories=True)
    if repo.bare:
        ret ="Warning Bare repo: {}, modifications cannot be tracked !".format(path)
    else:
        ret = getSubmoduleVersion(git, repo)
        _cached_versions.update({path: ret})
    repo.close()
    return ret

def get_version(path :str)-> str:
    if prefs.settings.git_supported:
        try:
            return repo_rev(path)
        except:
            return "Warning : {} not versioned".format(path)
    else:
        return "Warning git not supported in your settings, version of {} unknown".format(path)

def get_testium_version():
    # case where we're executing from an Appimage
    if 'APPIMAGE' in os.environ:
        ver = 'unknown'
        if 'SEQUENCER_REV' in os.environ:
            ver = os.getenv('SEQUENCER_REV')
        return (ver + " (binary release)")

    # case where we're executing from pyinstaller exe
    if getattr(sys, 'frozen', False):
        file_path = os.path.join(sys._MEIPASS, "VERSION")
        with open(file_path, 'r') as file:
            ver = file.read()
        return (ver + " (binary release)")

    # Executed from sources
    try:
        if prefs.settings.git_supported:
            git = import_module("git")
            path = tm.get_main_dir()
            try:
                return repo_rev(path)
            except git.InvalidGitRepositoryError:
                pkg_rec = import_module("pkg_resources")
                try:
                    ret = pkg_rec.get_distribution("testium").version
                    _cached_versions.update({path: ret})
                    return str(ret) + " (wheel release)"
                except:
                    return "Warning : testium not versioned"
        else:
            return "Warning git not supported in your settings, version of testium is unknown."
    except:
        return ("Unknown")

def get_modifications(path : str)-> str:

    if prefs.settings.git_supported:
        git = import_module("git")
        modifs = ""
        try:
            repo = git.Repo(path, search_parent_directories=True)
            for item in repo.index.diff(None):
                modifs = modifs + '"' + item.a_path + '"' + ' (modified)\n'
            for item in repo.untracked_files:
                modifs = modifs + '"' + item + '"' + ' (untracked)\n'
            repo.close()
            return modifs
        except git.InvalidGitRepositoryError:
            return "Warning : {} not versioned".format(path)
    else:
        return "Warning git not supported in your settings, version of {} unknown".format(path)

def getSubmoduleVersion(git, repo) -> str:
    v = ""
    for subM in repo.iter_submodules(ignore_self=False):
        try:
            v = v + getCommitVsTag(subM.module()) + "\n"
        except git.InvalidGitRepositoryError:
            v = v +"{} not versioned".format(subM.module().git_dir) + "\n"
    return v

def getCommitVsTag(repo) -> str:
    sha = repo.head.object.hexsha
    short_sha = repo.git.rev_parse(sha, short=12)
    url = change = ''

    # check if a tag or no
    t = None
    for tag in repo.tags:
        # Try excepted added after crash encountered because of strange tag
        try:
            if tag.commit == repo.head.commit:
                t = tag
        except:
            pass

    if repo.is_dirty():
        change = '(M)'
    try:
        url = "".join(repo.remote().urls)
    except:
        pass
    if t:
        ret = "tag {}".format(t.name)
    else:
        branch = ""
        if not repo.head.is_detached:
            branch = repo.active_branch.name
        else:
            for h in repo.heads:
                if h.commit == repo.head.commit:
                    branch = "detached from " + h.name
        ret = "{}{}, commit {}".format(branch, change, short_sha)
    if url:
        ret = ret + " from : " + url
    repo.close()
    return ret
