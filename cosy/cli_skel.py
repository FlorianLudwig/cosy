import importlib.resources
import functools

import typer

import cosy.project


app = typer.Typer()


@functools.lru_cache(maxsize=1)
def _gitignore_template():
    return importlib.resources.read_text("cosy.skel", "gitignore")


def patch_gitignore(text: str) -> str:
    template = _gitignore_template()

    generic_pos = text.find("## -- Generic --\n")
    project_specific_pos = text.find("## -- Project Specific --\n")

    if project_specific_pos != -1:
        project_specific_pos += 26  # length of separator
    else:
        # if not found, start at beginning
        project_specific_pos = 0

        # migrate from existing config and remove duplicated lines
        template_lines = set(template.split("\n"))
        text_lines = []
        for line in text.split("\n"):
            if line not in template_lines:
                text_lines.append(line)
        
        text = "\n".join(text_lines)

    project_specific_text = text[project_specific_pos:generic_pos].strip()
    
    return template.format(project_specific_text=project_specific_text)


@app.command()
def update():
    project = cosy.project.find()
    gitignore_path = project.data.path / ".gitignore"
    if gitignore_path.is_file():
        gitignore_text = gitignore_path.read_text()
    else:
        gitignore_text = ""
    
    gitignore_text_updated = patch_gitignore(gitignore_text)

    if gitignore_text_updated != gitignore_text:
        gitignore_path.write_text(gitignore_text_updated)
        print(f"{gitignore_path} updated")
