from injector import Injector, Module, provider, singleton, inject
from kubernetes import client, config
import os

from kubernetes.config import ConfigException
from loguru import logger
from kubernetes.client import ApiClient


class KubeModule(Module):
    """Dependency injection module for Kubernetes client."""
    def __init__(self):
        self.client = None

    @provider
    @singleton
    def get_kube_client(self) -> ApiClient:
        """Get a Kubernetes API client."""
        logger.debug("Loading Kubernetes configuration")
        try:
            logger.debug("Loading in-cluster Kubernetes configuration")
            config.load_incluster_config()
            return client.ApiClient()
        except ConfigException:
            pass

        logger.trace(f"Loading kubeconfig from {os.getenv('KUBECONFIG')}")
        config.load_kube_config(os.getenv("KUBECONFIG"))

        return client.ApiClient()
