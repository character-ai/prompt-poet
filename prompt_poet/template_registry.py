"""A Prompt Poet (PP) template registry."""

import logging
import threading
import time

import jinja2 as j2

from template_loaders import TemplateLoader

CACHE_MAX_SIZE = 100
TEMPLATE_REFRESH_INTERVAL_SECS = 30


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
            template_refresh_interval_secs: int = TEMPLATE_REFRESH_INTERVAL_SECS,
    ):
        """Initialize template engine."""
        self._provided_logger = logger

        if not self._initialized or reset:
            # In the case of reset, try to remove the background refresh thread.
            self._stop_background_thread_if_running()
            self._template_cache = {}
            self._cache_max_size = cache_max_size
            self._template_refresh_interval_secs = template_refresh_interval_secs
            self._default_template = None
            self._template_loader_cache = {}
            self._stop_event = threading.Event()
            self._thread = threading.Thread(target=self._load_internal, daemon=True)
            self._thread.start()
            # Initiation done.
            self._initialized = True

    def _load_internal(self):
        """Load the template from GCS and update cache."""
        while not self._stop_event.is_set():
            cache_keys = list(self._template_loader_cache.keys())
            if len(cache_keys) > self._cache_max_size:
                excess = len(cache_keys) - self._cache_max_size
                for key in cache_keys[:excess]:
                    self._template_loader_cache.pop(key, None)
                    self._template_cache.pop(key, None)
                cache_keys = cache_keys[excess:]

            for cache_key in cache_keys:
                try:
                    template_loader = self._template_loader_cache[cache_key]
                    self._template_cache[cache_key] = template_loader.load()
                except Exception as ex:
                    self.logger.error(f"Error loading template for template with id: {cache_key}: {ex}")
            time.sleep(self._template_refresh_interval_secs)

    def get_template(
            self,
            template_loader: TemplateLoader,
            use_cache: bool = False,
    ) -> j2.Template:
        """Get template from cache or load from disk.

        :param template_loader: A TemplateLoader instance that handles loading the template
            from its source.
        :param use_cache: Whether to use cached template if available. If False or the
            template is not in cache, it will be loaded from disk.
        :return: The loaded template
        """
        if not use_cache:
            return template_loader.load()

        cache_key = template_loader.id()
        if cache_key not in self._template_cache:
            self._template_loader_cache[cache_key] = template_loader
            self._template_cache[cache_key] = template_loader.load()
        return self._template_cache[cache_key]

    @property
    def logger(self):
        """The logger to be used by this module."""
        if self._provided_logger:
            return self._provided_logger

        return logging.getLogger(__name__)

    def shutdown(self):
        """Public method to gracefully shut down the background thread."""
        self._stop_background_thread_if_running()

    def _stop_background_thread_if_running(self):
        """Stop the background thread if it's running."""
        # Handle partial initiation or reset.
        if hasattr(self, '_stop_event') and self._stop_event and not self._stop_event.is_set():
            self._stop_event.set()
            if hasattr(self, '_thread') and self._thread and self._thread.is_alive():
                self._thread.join(timeout=5)
