import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from time import sleep

import settings
from aptos import Aptos
from model import NodeWatch
from storage import Storage


class Watcher:
    """Service for updating nodes' status"""
    def __init__(self, threads: int, storage: Storage, update_frequency: timedelta = timedelta(seconds=10),
                 max_check_age: timedelta = timedelta(minutes=5)) -> None:
        """
        Initialize service

        Args:
            threads (int): Number of threads to update nodes' statuses
            storage (Storage): Storage of node watches
            update_frequency (timedelta, optional): Waiting times between watcher ticks. Defaults to timedelta(seconds=10).
            max_check_age (timedelta, optional): Maximum node watch status age. Defaults to timedelta(minutes=5).
        """
        self.executor = ThreadPoolExecutor(max_workers=threads)
        self.storage = storage
        self.update_frequency = update_frequency
        self.max_check_age = max_check_age
        self.logger = logging.getLogger(__name__)

    @staticmethod
    def default() -> 'Watcher':
        """Default watcher initialized using settings from environment variables"""
        return Watcher(
            threads=settings.WATCHER_THREADS, 
            storage=Storage.default()
        )

    def __update_node_status(self, node_watch: NodeWatch):
        """
        Update node status

        Args:
            node_watch (NodeWatch): Node watch definition
        """
        self.logger.info(f'updating node status: {node_watch.ip}')
        try:
            node = Aptos(host=node_watch.ip)
            node.update()
            errors = []

            if not node.seed_port_opened:
                errors.append('Seed port is closed')
            if not node.metrics_port_opened:
                errors.append('Metrics port is closed')
            elif node.synced is False:
                errors.append('Not synced')

            if not node.api_port_opened:
                errors.append('API port is closed')
            
            errors.sort()

            is_ok = not errors
            has_modified = (
                node_watch.is_ok is None
                or is_ok != node_watch.is_ok
                or errors != node_watch.errors
            )
            node_watch.is_ok = is_ok
            node_watch.checked = int(datetime.utcnow().timestamp())
            node_watch.modified = int(datetime.utcnow().timestamp()) if has_modified else node_watch.modified
            node_watch.errors = errors
            self.storage.upsert_node_watch(node_watch)
            self.logger.info(f'node status: {node_watch.ip} - {"OK" if is_ok else "Alarming"} - {len(errors)} errors')
        except Exception as e:
            self.logger.error(f'error updating node {node_watch.ip} status: {e}')

    def run(self):
        """Tick function"""
        while True:
            for node_watch in self.storage.get_node_watches_to_run(self.max_check_age):
                self.logger.info(f'sumbiting job to update node status: {node_watch.ip}')
                self.executor.submit(self.__update_node_status, node_watch)
            sleep(self.update_frequency.total_seconds())


if __name__ == '__main__':
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG)
    Watcher.default().run()
