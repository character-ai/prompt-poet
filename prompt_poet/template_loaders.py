"""A Prompt Poet (PP) template registry."""

import os
import logging
import jinja2 as j2

from abc import ABC, abstractmethod
from jinja2 import BaseLoader
from google.cloud import storage


logger = logging.getLogger(__name__)

GCS_TEMPLATE_LOADER_PREFIX = "gcs://"


class TemplateLoader(ABC):
    """Base class for template loaders.

    This abstract class defines the interface for loading templates from various sources.
    Concrete implementations should handle specific template loading scenarios like
    local filesystem, remote filesystem, etc.
    """
    @abstractmethod
    def load(self) -> j2.Template:
        """Load and return a Jinja2 template from the source."""
        pass

    @abstractmethod
    def id(self) -> str:
        """Generate a unique identifier for this template loader configuration."""
        pass


def _parse_template_path(template_path: str) -> tuple[str, str]:
    """Parse the template path to determine the template source."""
    template_dir, template_name = os.path.split(template_path)
    if not template_dir:
        template_dir = "."
    return template_dir, template_name


class LocalFSTemplateLoader(TemplateLoader):
    """Template loader for loading templates from the local filesystem."""

    def __init__(self, template_path: str):
        self._template_dir, self._template_name = _parse_template_path(template_path)

    def load(self) -> j2.Template:
        try:
            loader = j2.FileSystemLoader(searchpath=self._template_dir)
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {self._template_name=} {self._template_dir=}"
            )

        env = j2.Environment(loader=loader)
        template = env.get_template(self._template_name)
        return template

    def id(self):
        return f"{self._template_dir}/{self._template_name}"


class LocalPackageTemplateLoader(TemplateLoader):
    """Template loader for loading templates from Python packages."""
    def __init__(self, package_name: str, template_path: str):
        self._template_dir, self._template_name = _parse_template_path(template_path)
        self._package_name = package_name

    def load(self) -> j2.Template:
        try:
            loader = j2.PackageLoader(
                package_name=self._package_name, package_path=self._template_dir
            )
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {self._template_name=} {self._template_dir=} {self._package_name=}"
            )
        env = j2.Environment(loader=loader)
        template = env.get_template(self._template_name)
        return template

    def id(self):
        return f"{self._package_name}:{self._template_dir}/{self._template_name}"


class CacheLoader(BaseLoader):
    """CacheLoader for Jinja2."""
    def __init__(self, mapping):
        self.mapping = mapping

    def get_source(self, environment, template):
        def uptodate():
            return True

        if template not in self.mapping:
            raise j2.TemplateNotFound(template)

        return self.mapping[template], template, uptodate


class GCSDictTemplateLoader(TemplateLoader):
    def __init__(self, bucket_name: str, template_path: str, gcs_client: storage.Client, status_file_path: str | None = None):
        self._bucket_name = bucket_name
        self._gcs_client = gcs_client
        self._template_dir, self._template_name = _parse_template_path(template_path)
        self._mapping = {}
        self._generation_data = {}
        self._status_file = status_file_path
        self._status_file_generation = None

    def _is_stale(self, blob: storage.Blob) -> bool:
        """Check if the file needs to be downloaded."""
        local_generation = self._generation_data.get(blob.name)
        return local_generation != blob.generation

    def _download(self):
        """Download all files from the specified GCS directory to the local cache."""
        bucket = self._gcs_client.bucket(self._bucket_name)
        if self._status_file:
            blob = bucket.blob(self._status_file)
            try:
                blob.download_as_text()
                generation = blob.generation
                if generation == self._status_file_generation:
                    return
                self._status_file_generation = generation
            except Exception as e:
                logger.warning(f"Failed to check on the status file {self._status_file}: {e}")

        blobs = bucket.list_blobs(prefix=self._template_dir)
        for blob in blobs:
            if blob.name.endswith("/"):
                continue
            if not _is_yaml_jinja(blob.name):
                logger.warning(f"Not a YAML file: {blob.name}")
                continue
            if self._is_stale(blob):
                # Remove prefix and leading slash
                relative_path = os.path.relpath(blob.name, start=self._template_dir)
                source = blob.download_as_text()
                self._mapping[relative_path] = source
                self._generation_data[blob.name] = blob.generation

    def load(self) -> j2.Template:
        try:
            self._download()
            loader = CacheLoader(mapping=self._mapping)
            env = j2.Environment(loader=loader, auto_reload=False)
            template = env.get_template(self._template_name)
            return template
        except j2.TemplateNotFound as ex:
            raise j2.TemplateNotFound(
                f"Template not found: {ex} {self._template_name=} {self._template_dir=}"
            )
        except Exception as ex:
            raise Exception(f"Error while loading template: {ex} {self._template_name=} {self._template_dir=}")

    def id(self) -> str:
        return f"{GCS_TEMPLATE_LOADER_PREFIX}{self._bucket_name}/{self._template_dir}/{self._template_name}"


def _is_yaml_jinja(filename):
    """
    Check if the given file is a YAML file processed with Jinja2.

    Args:
    filename (str): The name of the file to check.

    Returns:
    bool: True if the file ends with '.yml.j2', '.yaml.j2', '.yml.jinja2', or '.yaml.jinja2', False otherwise.
    """
    valid_extensions = ['.yml.j2', '.yaml.j2', '.yml.jinja2', '.yaml.jinja2']
    return any(filename.endswith(ext) for ext in valid_extensions)
