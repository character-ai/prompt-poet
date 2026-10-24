"""Templating engine for rendering Jinja templates."""

import logging
import os
import warnings

import jinja2 as j2

from template_loaders import LocalPackageTemplateLoader, LocalFSTemplateLoader, TemplateLoader
from template_registry import TemplateRegistry


class Template:
    """A Prompt Poet (PP) template originally represented as a valid *.yaml.j2 file.

    :param template_path: (deprecated) The path to the template file on disk.
    :param template_loader: A `TemplateLoader` instance for loading templates.
    :param package_name: (deprecated) The name of a python package used to find `template_path`.
    :param raw_template: A Prompt Poet template file represented as a string.
    :param logger: An optional logger to be used by `Template` and passed to
        downstream components
    :param from_cache: Whether or not to retrieve the template from a cache.
    :param from_examples: Whether or not to use the Prompt Poet (PP) provided
        examples.
    """

    def __init__(
        self,
        template_path: str = None,
        template_loader: TemplateLoader = None,
        package_name: str = None,
        raw_template: str = None,
        logger: logging.LoggerAdapter = None,
        from_cache: bool = False,
        from_examples: bool = False,
    ):
        """Initialize the template object."""
        if raw_template and template_path:
            raise ValueError(
                f"Cannot provide both {raw_template=} and {template_path=}."
            )
        if template_path:
            warnings.warn(
                "`template_path` is deprecated and will be removed in a future release. "
                "Use `template_loader` instead.",
                DeprecationWarning,
                stacklevel=2
            )

        if package_name:
            warnings.warn(
                "`package_name` is deprecated and will be removed in a future release. "
                "Use `template_loader` instead.",
                DeprecationWarning,
                stacklevel=2
            )

        if template_path:
            (
                self._template_dir,
                self._template_name,
                template_path,
            ) = self._parse_template_path(template_path, from_examples=from_examples)
        self._package_name = package_name
        if template_loader:
            self._template_loader = template_loader
        else:
            # To be backward compatible.
            if self._package_name:
                self._template_loader = LocalPackageTemplateLoader(self._package_name, template_path)
            else:
                self._template_loader = LocalFSTemplateLoader(template_path)
        self._raw_template = raw_template
        self._provided_logger = logger
        self._from_cache = from_cache
        self._from_examples = from_examples
        self._template = None
        self._rendered_template = None

        self._load_template()

    def render_template(self, template_data: dict) -> str:
        """Render the jinja template with the provided template_data data.

        Fills the loaded template with the provided data. This is an
        idempotent operation.
        """
        if not self._template:
            raise ValueError(f"Template not loaded: {self._template=}")

        self._rendered_template = self._template.render(template_data)
        return self._rendered_template

    @property
    def rendered_template(self) -> j2.Template:
        """The template after the jinja2 syntax has been rendered."""
        return self._rendered_template

    @property
    def template(self) -> j2.Template:
        """The original yml.j2 template object, not rendered."""
        return self._template

    @property
    def logger(self) -> str:
        """The logger to be used by this module."""
        if self._provided_logger:
            return self._provided_logger

        return logging.getLogger(__name__)

    @property
    def template_name(self) -> str:
        """The name of the template file.

        Deprecated: This property will be removed in a future release.
        """
        return self._template_name

    @property
    def template_dir(self) -> str:
        """The directory housing the template file.

        Deprecated: This property will be removed in a future release.
        """
        return self._template_dir

    @property
    def template_package_name(self) -> str:
        """The name of the package housing the template file."""
        return self._package_name

    @property
    def template_id(self) -> str:
        """The id of the template associated with the template loader."""
        return self._template_loader.id()

    def _load_template(self):
        """Load a jinja2 template."""
        if self._raw_template:
            self._template = j2.Template(self._raw_template)
        else:
            registry = TemplateRegistry(logger=self._provided_logger)
            self._template = registry.get_template(
                template_loader=self._template_loader,
                use_cache=self._from_cache,
            )

    def _parse_template_path(
        self, template_path: str, from_examples: bool = False
    ) -> tuple[str, str, str]:
        """Parse the template path to determine the template source."""
        template_dir, template_name = os.path.split(template_path)
        if from_examples:
            if template_dir:
                self.logger.warning(
                    "Using examples from the Prompt Poet package. Overriding the provided directory."
                )
            template_dir = os.path.abspath(
                os.path.join(os.path.dirname(__file__), "examples")
            )
        if not template_dir:
            template_dir = "."
        return template_dir, template_name, os.path.join(template_dir, template_name)
