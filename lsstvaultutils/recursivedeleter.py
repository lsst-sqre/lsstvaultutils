#!/usr/bin/env python
"""RecursiveDeleter removes an entire secret tree from Vault.
"""

import logging
import click
import hvac
from .timeformatter import TimeFormatter


@click.command()
@click.argument('vault_secret_path')
@click.option('--url', envvar='VAULT_ADDR',
              help="URL of Vault endpoint.")
@click.option('--token', envvar='VAULT_TOKEN',
              help="Vault token to use.")
@click.option('--cacert', envvar='VAULT_CAPATH',
              help="Path to Vault CA certificate.")
@click.option('--debug', envvar='DEBUG', is_flag=True,
              help="Enable debugging.")
def standalone(vault_secret_path, url, token, cacert, debug):
    client = RecursiveDeleter(url, token, cacert, debug)
    client.recursive_delete(vault_secret_path)


class RecursiveDeleter(object):
    """Class to remove a whole secret tree from Vault.
    """

    def __init__(self, url, token, cacert, debug):
        logger = logging.getLogger(__name__)
        if debug:
            logger.setLevel(logging.DEBUG)
        ch = logging.StreamHandler()
        if debug:
            ch.setLevel(logging.DEBUG)
        formatter = TimeFormatter(
            '%(asctime)s [%(levelname)s] %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S.%F %Z(%z)')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        self.logger = logger
        if debug:
            self.logger.debug("Debug logging started.")
        if not url and token and cacert:
            raise ValueError("All of Vault URL, Vault Token, and Vault CA " +
                             "path must be present, either in the " +
                             "or as options.")
        self.vault_client = self.get_vault_client(url, token, cacert)

    def get_vault_client(self, url, token, cacert):
        """Acquire a Vault client.
        """
        self.logger.debug("Acquiring Vault client for '%s'." % url)
        client = hvac.Client(url=url, token=token, verify=cacert)
        assert client.is_authenticated()
        return client

    def recursive_delete(self, path):
        """Delete path and everything under it.
        """
        self.logger.debug("Removing '%s' recursively." % path)
        pkeys = []
        resp = self.vault_client.list(path)
        if resp:
            self.logger.debug("Removing tree rooted at '%s'" % path)
            pkeys = resp["data"]["keys"]
            for item in [(path + "/" + x) for x in pkeys]:
                self.recursive_delete(item)
        else:
            self.logger.debug("Removing '%s' as leaf node." % path)
            self.vault_client.delete(path)


if __name__ == '__main__':
    standalone()
