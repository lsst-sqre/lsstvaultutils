# CLI command to allow manipulation of secrets in the same relative place
#  across Vault enclaves.
from typing import List

import click

from .vaultconfig import VaultConfig


@click.group()
@click.option("--vault-address", "-a")
@click.option("--secret-name", "-n", required=True)
@click.option("--secret-file", "-s")
@click.option("--vault-file", "-v", required=True)
@click.option("--omit", "-o", multiple=True)
@click.option("--dry-run", "-x", is_flag=True)
@click.pass_context
def standalone(
    ctx: click.Context,
    vault_address: str,
    secret_name: str,
    secret_file: str,
    vault_file: str,
    omit: List[str],
    dry_run: bool,
) -> None:
    """A tool to manipulate secrets in the same relative location across
    vault enclaves.

    --vault-address is a string representing a URL for a Vault implementation,
    e.g. "vault.lsst.codes".  If unspecified, the value of the environment
    variable VAULT_ADDR will be used.  It that isn't specified either, the
    default of "http://localhost:8200" will be used.

    --secret-name is a string representing the name of the secret relative to
    the top of the enclave, e.g. "pull-secret".

    --secret-file is only used with the "add" command.  It is a path
    to a JSON document that specifies the contents of the secret you
    want to inject, as a single object with key-value pairs, each pair
    being the name of the item within the secret and its value.

    --vault-file is a path to a file that contains a JSON document that is a
    list of enclaves (each one being a dict whose only key is the name of
    the top of the vault path for the enclave, and whose values are pair of
    dicts, "read" and "write", each a dict containing two keys, "accessor"
    and "id", whose values are the vault accessor and the vault token for
    its respective context within the enclave).  Not by coincidence, this
    is the form in which the vault document exists in SQuaRE's 1password.

    --omit may be specified multiple times; each time it is specified, it is
    the name of the enclave to skip when updating vaults.  This is helpful,
    for example, to *not* put the SQuaRE docker pull password into third-party
    implementations that rely on vault.lsst.codes.

    --dry-run is a boolean flag; if it is set, no change to the vault will
    actually be made, although the tool will report on the changes it
    would have done.

    """
    ctx.ensure_object(dict)
    ctx.obj["vault_config"] = VaultConfig(
        vault_address=vault_address, vault_file=vault_file, skip_list=omit
    )
    ctx.obj["options"] = {
        "secret_name": secret_name,
        "dry_run": dry_run,
        "secret_file": secret_file,
    }


@standalone.command()
@click.pass_context
def add(ctx: click.Context) -> None:
    """
    Add a secret across enclaves.

    secret-file is a path to a JSON document that specifies the contents of
    the secret you want to inject, as a single object with key-value pairs,
    each pair being the name of the item within the secret and its value.
    """
    vc = ctx.obj["vault_config"]
    sf = ctx.obj["options"]["secret_file"]
    if not sf:
        raise RuntimeError("Command 'add' requires '--secret-file'")
    vc.load_secret(sf)
    opts = ctx.obj["options"]
    vc.add_secrets(secret_name=opts["secret_name"], dry_run=opts["dry_run"])


@standalone.command()
@click.pass_context
def remove(ctx: click.Context) -> None:
    """
    Remove a secret from multiple enclaves.
    """
    vc = ctx.obj["vault_config"]
    opts = ctx.obj["options"]
    vc.remove_secrets(secret_name=opts["secret_name"], dry_run=opts["dry_run"])
