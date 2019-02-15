#!/usr/bin/env python
"""VaultHelper aids migration from k8s secrets to Vault.
"""


import click
import hvac
from base64 import b64decode
from kubernetes import client, config


@click.command()
@click.argument('k8s_secret_name')
@click.argument('vault_secret_path')
@click.option('--url', envvar='VAULT_ADDR',
              help="URL of Vault endpoint.")
@click.option('--token', envvar='VAULT_TOKEN',
              help="Vault token to use.")
@click.option('--cacert', envvar='VAULT_CAPATH',
              help="Path to Vault CA certificate.")
def standalone(url, token, cacert, k8s_secret_name, vault_secret_path):
    client = SecretCopier(url, token, cacert)
    client.copy_k8s_to_vault(k8s_secret_name, vault_secret_path)


class SecretCopier(object):
    def __init__(self, url, token, cacert):
        if not url and token and cacert:
            raise ValueError("All of Vault URL, Vault Token, and Vault CA " +
                             "path must be present, either in the " +
                             "or as options.")
        self.vault_client = self.get_vault_client(url, token, cacert)
        self.k8s_client = self.get_k8s_client()
        self.current_context = config.list_kube_config_contexts()[1]
        self.namespace = self.current_context['context']['namespace']

    def get_vault_client(self, url, token, cacert):
        """Acquire a Vault client.
        """
        client = hvac.Client(url=url, token=token, verify=cacert)
        assert client.is_authenticated()
        return client

    def get_k8s_client(self):
        config.load_kube_config()
        k8s_client = client.CoreV1Api()
        return k8s_client

    def read_k8s_secret(self, k8s_secret_name):
        secret = self.k8s_client.read_namespaced_secret(
            k8s_secret_name,
            self.namespace)
        data = secret.data
        for k in data:
            v = data[k]
            data[k] = b64decode(v).decode('utf-8')
        self.secret = data

    def write_vault_secret(self, vault_secret_path):
        for k in self.secret:
            self.vault_client.write(vault_secret_path + "/" + k,
                                    value=self.secret[k])

    def copy_k8s_to_vault(self, k8s_secret_name, vault_secret_path):
        self.read_k8s_secret(k8s_secret_name)
        self.write_vault_secret(vault_secret_path)


if __name__ == '__main__':
    standalone()
