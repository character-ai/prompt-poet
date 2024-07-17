"""A Prompt Poet (PP) template registry."""

import logging
import os

import jinja2 as j2
from cachetools import TTLCache

CACHE_MAX_SIZE = 100
CACHE_TTL_SECS = 30


class TemplateRegistry:
    """A Prompt Poet (PP) template registry."""

    _instance = None

    def __new__(cls, *args, **kwargs):
        """Singleton pattern that allows arbitrary arguments."""
        if cls._instance is None:
            cls._instance = super(TemplateRegistry, cls).__new__(cls)
            # Initialize _instance's attributes
            cls._instance._initialized = False

        return cls._instance

    def __init__(
        self,
        logger: logging.LoggerAdapter = None,
        reset: bool = False,
        cache_max_size: int = CACHE_MAX_SIZE,
        cache_ttl_secs: int = CACHE_TTL_SECS,
    ):
        """Initialize template engine."""
        self._provided_logger = logger

        if not self._initialized or reset:
            self._cache = TTLCache(maxsize=cache_max_size, ttl=cache_ttl_secs)
            self._default_template = None
            self._initialized = True

    def get_template(
        self,
        template_name: str,
        template_dir: str,
        package_name: str = None,
        use_cache: bool = False,
    ) -> j2.Template:
        """Get template from cache or load from disk.

        :param template_name: The name of the file containing the raw template.
        :param template_dir: The path to the directory housing the file
            `template_name`.
        :param package_name: An optional parameter indicating to find
            `template_name` within `template_dir` within a python package
            `package_name`.
        :param use_examples: An optional parameter indicating to use the
            examples packaged into the the Prompt Poet package.
        :param use_cache: An optional parameter indicating to use the
            examples packaged into the the Prompt Poet package.
        """
        if template_dir.endswith("/"):
            raise ValueError(
                f"template_dir must not end with a '/'. Found: {template_dir}"
            )

        cache_key = self._build_cache_key(
            template_name=template_name,
            template_dir=template_dir,
            package_name=package_name,
        )

        load_from_disk = not use_cache or cache_key not in self._cache

        if load_from_disk:
            self._cache[cache_key] = self._load_template(
                template_name, template_dir=template_dir, package_name=package_name
            )

        return self._cache[cache_key]

    @property
    def logger(self) -> str:
        """The logger to be used by this module."""
        if self._provided_logger:
            return self._provided_logger

        return logging.getLogger(__name__)

    def _build_cache_key(
        self, template_name: str, template_dir: str, package_name: str
    ) -> str:
        key = f"{template_dir}/{template_name}"
        if package_name:
            key = f"{package_name}:{key}"
        return key

    def _load_template(
        self,
        template_name: str,
        template_dir: str = None,
        package_name: str = None,
    ) -> j2.Template:
        """Load template from disk."""
        loader = None
        if template_dir is None and package_name is None:
            raise ValueError(
                "Either `template_dir` or `package_name` must be provided."
            )

        try:
            if package_name is not None:
                loader = j2.PackageLoader(
                    package_name=package_name, package_path=template_dir
                )
            else:
                loader = j2.FileSystemLoader(searchpath=template_dir)
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {template_name=} {template_dir=} {package_name=}"
            )

        env = j2.Environment(loader=loader)
        template = env.get_template(template_name)
        return template
