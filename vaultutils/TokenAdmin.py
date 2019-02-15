#!/usr/bin/env python
"""TokenAdmin uses the SQuaRE taxonomy to create or revoke a trio of access
tokens for a particular path in the Vault secret space, and stores those
token IDs in a place accessible to a Vault admin token.
"""


import click
import hvac


@click.command()
@click.argument('verb')
@click.argument('vault_secret_path')
@click.option('--url', envvar='VAULT_ADDR',
              help="URL of Vault endpoint.")
@click.option('--token', envvar='VAULT_TOKEN',
              help="Vault token to use.")
@click.option('--cacert', envvar='VAULT_CAPATH',
              help="Path to Vault CA certificate.")
def standalone(verb, vault_secret_path, url, token, cacert):
    client = AdminTool(url, token, cacert)
    client.execute(verb, vault_secret_path)


class AdminTool(object):
    def __init__(self, url, token, cacert):
        if not url and token and cacert:
            raise ValueError("All of Vault URL, Vault Token, and Vault CA " +
                             "path must be present, either in the " +
                             "or as options.")
        self.vault_client = self.get_vault_client(url, token, cacert)

    def get_vault_client(self, url, token, cacert):
        """Acquire a Vault client.
        """
        client = hvac.Client(url=url, token=token, verify=cacert)
        assert client.is_authenticated()
        return client

    def execute(self, verb, secret_path):
        verb = verb.lower()
        if verb == 'create':
            self.create(secret_path)
            return
        if verb == 'revoke':
            self.revoke(secret_path)
            return
        raise ValueError("Verb must be either 'create' or 'revoke'.")

    def write_vault_secret(self, vault_secret_path):
        # for k in self.secret:
        #    self.vault_client.write(vault_secret_path + "/" + k,
        #                            value=self.secret[k])
        pass


if __name__ == '__main__':
    standalone()
