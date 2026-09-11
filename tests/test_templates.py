from pathlib import Path

import pytest
from jinja2 import Environment, FileSystemLoader


@pytest.mark.parametrize("autoescape", [False, True])
def test_settings_template_renders_literal_percentages(autoescape):
	template_dir = Path(__file__).parents[1] / "octoprint_octopod" / "templates"
	environment = Environment(
		loader=FileSystemLoader(str(template_dir)),
		extensions=["jinja2.ext.i18n"],
		autoescape=autoescape,
	)
	environment.install_gettext_callables(
		lambda message: message,
		lambda singular, plural, count: singular if count == 1 else plural,
		newstyle=True,
	)

	rendered = environment.get_template("octopod_settings.jinja2").render()

	assert "Every 25%" in rendered
	assert "Every 50%" in rendered
