import json
import os
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional

import hvac


class Verb(Enum):
    ADD = 1
    REMOVE = 2


@dataclass
class Keyset:
    """Contains "accessor" and "id" tokens for a Vault path."""

    accessor: str
    id: str


@dataclass
class Enclave:
    """Maps a Vault path to 'read' and 'write' Keysets.  The 'Enclave' is
    simply a particular vault path with its own Keysets, e.g.
    'k8s_operator/nublado.lsst.codes'
    """

    name: str
    read: Keyset
    write: Keyset


class VaultConfig:
    """Contains the vault address (a URL represented as a string), the
    secret to be added, which is a dict mapping strings to strings
    (but can be None, if you're deleting a secret from a path), the
    rendered-to-memory JSON document representing all the vault paths
    and tokens, and the list of vault paths to not update.

    """

    def __init__(
        self,
        vault_address: Optional[str],
        vault_file: str,
        skip_list: Optional[List[str]],
        secret_file: Optional[str] = None,
    ):
        self.vault_address: Optional[str] = os.getenv("VAULT_ADDR")
        self.secret: Optional[Dict[str, str]] = None
        self.enclaves: Dict[str, Enclave] = {}
        if vault_address:
            self.vault_address = vault_address
        if secret_file:
            self.load_secret(secret_file)

        with open(vault_file, "r") as f:
            vault_dict = json.load(f)
        for item in vault_dict:
            name: str = list(item.keys())[0]
            if skip_list and name in skip_list:
                continue
            read_k = Keyset(**item[name]["read"])
            write_k = Keyset(**item[name]["write"])
            enclave = Enclave(name=name, read=read_k, write=write_k)
            self.enclaves[name] = enclave

    def load_secret(self, secret_file: str) -> None:
        with open(secret_file, "r") as f:
            self.secret = json.load(f)

    def _get_write_key_for_enclave(self, enclave: Enclave) -> str:
        """Given a loaded Vault enclave, return its write key."""
        return enclave.write.id

    def get_enclave_for_path(self, vault_path: str) -> Optional[Enclave]:
        """Given a Vault path (e.g. 'k8s_operator/nublado.lsst.codes'),
        return the associated enlave.
        """
        return self.enclaves.get(vault_path)

    def add_secrets(self, secret_name: str, dry_run: bool = False) -> None:
        self._change_secrets(
            verb=Verb.ADD, secret_name=secret_name, dry_run=dry_run
        )

    def remove_secrets(self, secret_name: str, dry_run: bool = False) -> None:
        self._change_secrets(
            verb=Verb.REMOVE, secret_name=secret_name, dry_run=dry_run
        )

    def _change_secrets(
        self, verb: Verb, secret_name: str, dry_run: bool = False
    ) -> None:
        for name in self.enclaves:
            self._change_secret(
                verb=verb,
                enclave=self.enclaves[name],
                secret_name=secret_name,
                dry_run=dry_run,
            )

    def add_secret(
        self, enclave: Enclave, secret_name: str, dry_run: bool = False
    ) -> None:
        self._change_secret(
            verb=Verb.ADD,
            enclave=enclave,
            secret_name=secret_name,
            dry_run=dry_run,
        )

    def remove_secret(
        self, enclave: Enclave, secret_name: str, dry_run: bool = False
    ) -> None:
        self._change_secret(
            verb=Verb.REMOVE,
            enclave=enclave,
            secret_name=secret_name,
            dry_run=dry_run,
        )

    def _change_secret(
        self,
        verb: Verb,
        enclave: Enclave,
        secret_name: str,
        dry_run: bool = False,
    ) -> None:
        client = hvac.Client(url=self.vault_address)
        client.token = self._get_write_key_for_enclave(enclave)
        assert client.is_authenticated()
        secret_path = "{}/{}".format(enclave.name, secret_name)
        vstr = "add"
        if verb == Verb.REMOVE:
            vstr = "remove"
        if dry_run:
            print(
                "Dry run: {} secret at ".format(vstr)
                + "{}/{}".format(self.vault_address, secret_path)
            )
        else:
            if verb == Verb.REMOVE:
                client.secrets.kv.v2.delete_metadata_and_all_versions(
                    path=secret_path
                )
            else:
                client.secrets.kv.v2.create_or_update_secret(
                    path=secret_path, secret=self.secret
                )
