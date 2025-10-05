"""Prompt loader using Jinja2 templates."""

import os
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


def render_prompt(template_name: str, **context) -> str:
    """
    Render a prompt template with the given context.

    Args:
        template_name: Name of the template file (without .jinja extension)
        **context: Variables to pass to the template

    Returns:
        Rendered prompt string
    """
    # Get the directory of this file (src/prompts/)
    prompts_dir = Path(__file__).parent
    templates_dir = prompts_dir / "templates"

    # Create Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(),
        trim_blocks=True,
        lstrip_blocks=True,
    )

    # Load and render template
    template = env.get_template(f"{template_name}.jinja")
    return template.render(**context)