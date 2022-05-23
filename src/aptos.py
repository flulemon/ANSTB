import logging
import socket
from contextlib import closing
from datetime import datetime, timedelta
from typing import Iterable, Optional

import requests
from prometheus_client.parser import text_string_to_metric_families


class Aptos:
    """Aptos node information"""
    def __init__(self, host: str, update_frequency: timedelta = timedelta(hours=1), api_port: int = 8080, 
                 metrics_port: Optional[int] = 9101, seed_port: Optional[int] = 6180, proto: str = 'http') -> None:
        """
        Initialize Aptos node

        Args:
            host (str): Aptos node host
            update_frequency (timedelta, optional): Update information frequency. Defaults to timedelta(hours=1).
            api_port (int, optional): API port to use. Defaults to 8080.
            metrics_port (Optional[int], optional): Metrics port to use. Defaults to 9101.
            seed_port (Optional[int], optional): Seed port to use. Defaults to 6180.
            proto (str, optional): Protocol (http or https) to use to communicate with the node. Defaults to 'http'.
        """
        self.__proto = proto
        self.__host = host
        self.__update_frequency: timedelta = update_frequency if update_frequency else timedelta(hours=1)
        self.__api_port = api_port
        self.__metrics_port = metrics_port
        self.__seed_port = seed_port
        self.__last_updated: Optional[datetime] = None
        self.chain_id: Optional[int] = None
        self.epoch: Optional[int] = None
        self.ledger_version: Optional[str] = None
        self.ledger_timestamp: Optional[str] = None
        self.api_port_opened: Optional[bool] = None
        self.metrics_port_opened: Optional[bool] = None
        self.seed_port_opened: Optional[bool] = None
        self.synced: Optional[bool] = None
        self.error: Optional[str] = None
        self.logger = logging.getLogger(__name__)
        self.out_of_sync_threshold = 10

    def __test_port(self, port: Optional[int]) -> bool:
        """
        Test if node port is opened or not

        Args:
            port (Optional[int]): Port to test

        Returns:
            bool: True if connection to given port was successful
        """
        if port is None:
            return True
        self.logger.debug(f'testing port {self.__host}:{port}')
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(5)
            return sock.connect_ex((self.__host, port)) == 0

    def __update_ledger_version(self):
        """
        Update information about ledger version and current chain ID

        Raises:
            Exception: If node returned non 200 code
        """
        if not self.__test_port(self.__api_port):
            return
        self.logger.debug(f'updating ledger version {self.__proto}://{self.__host}:{self.__api_port}')
        info = requests.get(f'{self.__proto}://{self.__host}:{self.__api_port}', timeout=5)
        if info.status_code != 200:
            raise Exception(f"Couldn't retrieve API ledger info")
        info = info.json()
        self.chain_id = info["chain_id"]
        self.epoch = info["epoch"]
        self.ledger_version = int(info["ledger_version"])
        self.ledger_timestamp = int(info["ledger_timestamp"])

    @staticmethod
    def __first_or_none(iterable: Iterable):
        """
        Helper function to get first element of iterable or None

        Args:
            iterable (Iterable): Iterable to get first item from

        Returns:
            _type_: First item or None
        """
        return next(iter(iterable), None) if iterable else None

    def __update_synced(self):
        """
        Update syncronization status of node

        Raises:
            Exception: If metrics endpoint returned non 200 status code
            Exception: If metrics about syncronization were not present
        """
        if not self.__metrics_port or not self.__test_port(self.__metrics_port):
            return
        self.logger.debug(f'updating synced status {self.__proto}://{self.__host}:{self.__metrics_port}/metrics')
        metrics = requests.get(f'{self.__proto}://{self.__host}:{self.__metrics_port}/metrics', timeout=5)
        if metrics.status_code != 200:
            raise Exception(f"Couldn't retrieve node metrics")
        metrics = list(text_string_to_metric_families(metrics.text))
        sync_metrics = self.__first_or_none(m for m in metrics if m.name == 'aptos_state_sync_version')
        if not sync_metrics:
            raise Exception(f"Sync metrics are not defined")
        synced = self.__first_or_none(m for m in sync_metrics.samples if m.labels['type'] == 'synced')
        applied = self.__first_or_none(m for m in sync_metrics.samples if m.labels['type'] == 'executed_transactions')
        # let the node be out of sync for a little bit
        self.synced = None if not synced or not applied else abs(synced.value - applied.value) < self.out_of_sync_threshold
        

    def update(self):
        """Update node information"""
        if self.__last_updated and datetime.utcnow() - self.__last_updated <= self.__update_frequency:
            return
        try:
            self.api_port_opened = self.__test_port(self.__api_port)
            self.metrics_port_opened = self.__test_port(self.__metrics_port)
            self.seed_port_opened = self.__test_port(self.__seed_port)
            self.__update_ledger_version()
            self.__update_synced()
            self.__last_updated = datetime.utcnow()
        except Exception as e:
            self.error = e.message
