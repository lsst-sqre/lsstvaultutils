#!/usr/bin/env python
"""tokenadmin uses the SQuaRE taxonomy to create or revoke a trio of access
tokens for a particular path in the Vault secret space, and stores those
token IDs in a place accessible to a Vault admin token (or removes them).
"""
import click
import hvac
import logging
from .timeformatter import TimeFormatter

POLICY_ROOT = "policy/delegated"
SECRET_ROOT = "secret/delegated"


@click.command()
@click.argument('verb')
@click.argument('vault_secret_path')
@click.option('--url', envvar='VAULT_ADDR',
              help="URL of Vault endpoint.")
@click.option('--token', envvar='VAULT_TOKEN',
              help="Vault token to use.")
@click.option('--cacert', envvar='VAULT_CAPATH',
              help="Path to Vault CA certificate.")
@click.option('--ttl', envvar="VAULT_TTL", default="8766h",
              help="TTL for tokens [ 1 year = \"8776h\" ]")
@click.option('--debug', envvar='DEBUG', is_flag=True,
              help="Enable debugging.")
def standalone(verb, vault_secret_path, url, token, cacert, ttl, debug):
    """Run as standalone program.
    """
    client = AdminTool(url, token, cacert, ttl, debug)
    client.execute(verb, vault_secret_path)


def strip_slashes(path):
    """Strip leading and trailing slashes.
    """
    while path[0] == '/':
        path = path[1:]
    while path[-1] == '/':
        path = path[:-1]
    return path


class AdminTool(object):
    """Class to build and destroy token hierarchy in LSST taxonomy.
    """

    def __init__(self, url, token, cacert, ttl='8766h', debug=False):
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
        self.ttl = ttl
        if not url and token and cacert:
            raise ValueError("All of Vault URL, Vault Token, and Vault CA " +
                             "path must be present, either in the " +
                             "or as options.")
        self.vault_client = self.get_vault_client(url, token, cacert)

    def get_vault_client(self, url, token, cacert):
        """Acquire a Vault client.
        """
        self.logger.debug("Getting Vault client for '%s'." % url)
        client = hvac.Client(url=url, token=token, verify=cacert)
        assert client.is_authenticated()
        self.logger.debug("Vault Client is authenticated.")
        self.token = token
        self.url = url
        self.cacert = cacert
        return client

    def execute(self, verb, secret_path):
        """Create or revoke a set of tokens for a path.
        """
        verb = verb.lower()
        secret_path = strip_slashes(secret_path)
        if verb == 'create':
            self.create(secret_path)
            return
        if verb == 'revoke':
            self.revoke(secret_path)
            return
        raise ValueError("Verb must be either 'create' or 'revoke'.")

    def create(self, path):
        """Create policies and token set for path.
        """
        self.logger.debug("Creating policies and tokens for '%s'." % path)
        self.create_secret_policies(path)
        self.create_tokens(path)

    def revoke(self, path):
        """Remove policies and token set for path.
        """
        self.logger.debug("Revoking tokens and removing policies for" +
                          " '%s'." % path)
        self.delete_tokens(path)
        self.destroy_secret_policies(path)

    def create_secret_policies(self, path):
        """Create policies for path.
        """
        self.logger.debug("Creating policies for '%s'." % path)
        polpath = POLICY_ROOT + "/" + path
        for pol in ["read", "write", "admin"]:
            self.create_secret_policy(polpath, pol)

    def create_secret_policy(self, path, pol):
        """Create specific policy ('read', 'write', 'admin') for path.
        """
        pols = ["read", "write", "admin"]
        polstr = ""
        if pol not in pols:
            raise ValueError("Policy must be one of %r" % pols)
        if pol == "admin":
            for sub in ["", "/*"]:
                if sub:
                    polstr += "\n"
                polstr += " path \"secret/%s%s\" {\n" % (path, sub)
                polstr += "   capabilities = [\"create\", \"read\","
                polstr += "  \"update\", \"delete\", \"list\"]\n }\n"
            # This policy lets it delete ALL the tokens, not just children
            #  polstr += " path \"auth/token/*\" {\n"
            #  polstr += "   capabilities = [\"create\", \"read\","
            #  polstr += "  \"update\", \"delete\", \"list\"]\n }\n"
        elif pol == "write":
            polstr += " path \"secret/%s/*\" {\n" % path
            polstr += "   capabilities = [\"read\", \"create\","
            polstr += " \"update\"]\n }\n"
        elif pol == "read":
            polstr += " path \"secret/%s/*\" {\n" % path
            polstr += "   capabilities = [\"read\" ]\n }\n"
        self.logger.debug("Creating policy for '%s/%s'." % (path, pol))
        self.logger.debug("Policy string: %s" % polstr)
        self.vault_client._sys.create_or_update_policy(path + "/" + pol,
                                                       polstr)

    def destroy_secret_policies(self, path):
        """Destroy policies for secret path.
        """
        polpath = POLICY_ROOT + "/" + path
        for pol in ["admin", "read", "write"]:
            self.logger.debug("Deleting policy for %s/%s." % (path, pol))
            self.vault_client._sys.delete_policy(polpath + "/" + pol)

    def create_tokens(self, path):
        """Create set of tokens for path.
        """
        admin_tok = self.create_admin_token(path)
        self.create_rw_tokens(admin_tok, path)

    def create_admin_token(self, path):
        """Create admin token for path.
        """
        # Admin token needs all three policies because child tokens must
        #  have subset of parent policies (not parent policy content), even
        #  though the admin policy is a strict superset of both read and
        #  write policies.
        #
        # Since we're not creating the read/write tokens as children of the
        #  admin, it doesn't really matter.
        policies = [(POLICY_ROOT + "/" + path + "/" + x) for x in
                    ["read", "write", "admin"]]
        self.logger.debug("Creating 'admin' token for '%s'." % path)
        self.logger.debug(" - with policies '%r'." % policies)
        resp = self.vault_client.create_token(ttl=self.ttl,
                                              policies=policies)
        auth = resp.get("auth")
        tok = auth.get("client_token")
        resp = self.vault_client.lookup_token(token=tok)
        tok_id = resp["data"]["id"]
        accessor = resp["data"]["accessor"]
        self.store_token(tok_id, accessor, "admin", path)
        return tok_id

    def create_rw_tokens(self, admin_tok, path):
        """Create read and write tokens for path, using admin token as parent.
        """
        # Create using admin token as parent token
        # client = hvac.Client(url=self.url, verify=self.cacert,
        #                     token=admin_tok)
        # assert client.is_authenticated()
        # That works, but if we have the policy set to allow token manipulation
        #  we can delete all tokens.  We need to set roles.
        #
        # For now, we just use the admin client we were starting with.
        client = self.vault_client
        for role in ["read", "write"]:
            policies = [(POLICY_ROOT + "/" + path + "/" + role)]
            self.logger.debug("Creating token for '%s/%s'." % (path, role))
            self.logger.debug(" - policies '%r'." % policies)
            resp = client.create_token(ttl=self.ttl, policies=policies)
            auth = resp["auth"]
            tok = auth["client_token"]
            resp = client.lookup_token(token=tok)
            tok_id = resp["data"]["id"]
            accessor = resp["data"]["accessor"]
            self.store_token(tok_id, accessor, role, path)

    def store_token(self, tok_id, accessor, role, path):
        """Store token id and accessor for path/role combo.
        """
        roles = ["read", "write", "admin"]
        if role not in roles:
            raise ValueError("Role must be one of %r" % roles)
        toksec = SECRET_ROOT + "/" + path + "/" + role
        self.logger.debug("Writing token store for '%s/%s'." % (path, role))
        self.vault_client.write(toksec + "/id",
                                value=tok_id)
        self.vault_client.write(toksec + "/accessor",
                                value=accessor)

    def delete_tokens(self, path):
        """Revoke tokens for path and remove token id store.
        """
        tok_store = SECRET_ROOT + "/" + path
        for role in ["read", "write", "admin"]:
            this_tok = tok_store + "/" + role
            id_secpath = this_tok + "/id"
            self.logger.debug("Requesting ID for '%s' token for '%s'." % (
                role, path))
            token = self.vault_client.read(id_secpath)["data"]["value"]
            self.logger.debug("Deleting '%s' token for '%s'." % (
                role, path))
            self.vault_client.revoke_token(token=token)
            self.logger.debug("Deleting token store for '%s/%s'." % (
                path, role))
            self.vault_client.delete(id_secpath)
            self.vault_client.delete(this_tok + "/accessor")
            self.vault_client.delete(this_tok)
        self.logger.debug("Deleting token store for '%s'." % path)
        self.vault_client.delete(tok_store)


if __name__ == '__main__':
    standalone()
