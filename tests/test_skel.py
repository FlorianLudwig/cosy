import cosy.cli_skel


GITIGNORE_MIGRATE = """
# an existing gitignore file which is not genereted by cosy
some-really-special-path

# some path already in cosy
*.egg
"""

GITIGNORE_UPDATE = """## This file is managed by cosy [https://github.com/FlorianLudwig/cosy]
##
## Only make changes by hand below the project specific session.

## -- Project Specific --
some-really-special-path

## -- Generic --
some-really-old-stuff-here
"""


def test_patch_gitignore():
    new = cosy.cli_skel.patch_gitignore("")

    assert new.startswith("## This file is managed by cosy")

    updated = cosy.cli_skel.patch_gitignore(GITIGNORE_UPDATE)

    assert updated.startswith("## This file is managed by cosy")
    assert "## -- Generic --\n" in updated
    assert "some-really-special-path" in updated
    assert "some-really-old-stuff-here" not in updated
    assert "dist/" in updated


    migrate = cosy.cli_skel.patch_gitignore(GITIGNORE_MIGRATE)
    assert "## -- Generic --\n" in migrate
    assert "some-really-special-path" in migrate
    assert migrate.count("*.egg\n") == 1