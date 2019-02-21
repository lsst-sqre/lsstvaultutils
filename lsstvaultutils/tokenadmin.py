#!/usr/bin/env python
"""tokenadmin uses the SQuaRE taxonomy and an amdin token to create or
revoke a trio of access tokens for a particular path in the Vault
secret space, and stores those token IDs in a place accessible to a
Vault admin token (or removes them).

"""
import click
import hvac
import json
from hvac.exceptions import InvalidPath
from .recursivedeleter import RecursiveDeleter
from .timeformatter import getLogger

POLICY_ROOT = "delegated"
TOKEN_SECRET_ROOT = "secret/delegated"


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
@click.option('--overwrite', envvar='VAULT_OVERWRITE', is_flag=True,
              help="Revoke existing tokens/overwrite existing policies. " +
              "Only useful with 'create'.")
@click.option('--display', is_flag=True, help="Display token list after " +
              "creation. Only useful with 'create'.")
@click.option('--delete-data', is_flag=True, help="Delete data in tree " +
              " after token revocation. Only useful with 'revoke'.")
@click.option('--debug', envvar='DEBUG', is_flag=True,
              help="Enable debugging.")
def standalone(verb, vault_secret_path, url, token, cacert, ttl, overwrite,
               display, delete_data, debug):
    """Manage tokens that allow access to and control over a particular
    Vault secret path.  Verbs are 'create', 'revoke', and 'display'.
    """
    client = AdminTool(url, token, cacert, ttl, overwrite, display,
                       delete_data, debug)
    client.execute(verb, vault_secret_path)


def strip_slashes(path):
    """Strip leading and trailing slashes.
    """
    while path[0] == '/':
        path = path[1:]
    while path[-1] == '/':
        path = path[:-1]
    return path


def strip_leading_secret(path):
    """Strip leading 'secret/'
    """
    if path[:7].lower() == 'secret/':
        path = path[7:]
    while path[-1] == '/':
        path = path[:-1]
    if not path:
        raise ValueError("A non-root secret path must be specified.")
    return path


class AdminTool(object):
    """Class to build and destroy token hierarchy in LSST taxonomy.
    """

    def __init__(self, url, token, cacert, ttl='8766h', overwrite=False,
                 display=False, delete_data=False, debug=False):
        self.logger = getLogger(name=__name__, debug=debug)
        self.logger.debug("Debug logging started.")
        self.ttl = ttl
        self.overwrite = overwrite
        self.debug = debug
        self.display = display
        self.delete_data = delete_data
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
        secret_path = strip_leading_secret(secret_path)
        if verb == 'create':
            self.create(secret_path)
            return
        if verb == 'revoke':
            self.revoke(secret_path)
            return
        if verb == 'display':
            self.display_tokens(secret_path)
            return
        raise ValueError("Verb must be one of 'create', 'revoke', or" +
                         " 'display'.")

    def create(self, path):
        """Create policies and token set for path.
        """
        self.logger.debug("Creating policies and tokens for '%s'." % path)
        self.create_secret_policies(path)
        self.create_tokens(path)
        if self.display:
            self.display_tokens(path)

    def revoke(self, path):
        """Remove policies and token set for path.
        """
        self.logger.debug("Revoking tokens and removing policies for" +
                          " '%s'." % path)
        if self.delete_data:
            token_path = (TOKEN_SECRET_ROOT + "/" + path + "/admin/id")
            self.logger.debug("Getting admin token for '%s'." % path)
            token_id = self.vault_client.read(token_path)["data"]["value"]
            dc = RecursiveDeleter(self.url, token_id, self.cacert,
                                  self.debug)
            dpath = "secret/" + path
            self.logger.debug("Deleting data under '%s'." % dpath)
            dc.recursive_delete(dpath)
        self.delete_tokens(path)
        self.destroy_secret_policies(path)

    def display_tokens(self, path):
        """Print tokens and accessors for path in JSON format on stdout.
        """
        self.logger.debug("Getting tokens for '%s'." % path)
        token = {}
        for pol in "read", "write", "admin":
            token[pol] = {}
            for item in "id", "accessor":
                tpath = (TOKEN_SECRET_ROOT + "/" + path + "/" + pol +
                         "/" + item)
                token[pol][item] = self.vault_client.read(tpath)[
                    "data"]["value"]
        displayval = {}
        displayval[path] = token
        print(json.dumps(displayval, sort_keys=True, indent=4))

    def create_secret_policies(self, path):
        """Create policies for path.
        """
        self.logger.debug("Creating policies for '%s'." % path)
        if self.check_policy_existence(path) and not self.overwrite:
            self.logger.warning("Policy for path '%s' already exists." % path)
            return
        for pol in ["read", "write", "admin"]:
            self.create_secret_policy(path, pol)

    def check_policy_existence(self, path):
        ppath = POLICY_ROOT + "/" + path
        self.logger.debug("Checking for existence of policy '%s'." % ppath)
        try:
            there = self.vault_client._sys.read_policy(ppath)
        except InvalidPath:
            return False
        if there:
            return True
        return False

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
            polstr += " \"update\", \"list\"]\n }\n"
        elif pol == "read":
            polstr += " path \"secret/%s/*\" {\n" % path
            polstr += "   capabilities = [\"read\", \"list\"]\n }\n"
        self.logger.debug("Creating policy for '%s/%s'." % (path, pol))
        ppath = POLICY_ROOT + "/" + path + "/" + pol
        self.logger.debug("Policy string: %s" % polstr)
        self.logger.debug("Policy path: %s" % ppath)
        self.vault_client._sys.create_or_update_policy(ppath, polstr)

    def destroy_secret_policies(self, path):
        """Destroy policies for secret path.
        """
        polpath = POLICY_ROOT + "/" + path
        for pol in ["admin", "read", "write"]:
            ppath = polpath + "/" + pol
            self.logger.debug("Deleting policy for '%s'." % ppath)
            self.vault_client._sys.delete_policy(ppath)

    def create_tokens(self, path):
        """Create set of tokens for path.
        """
        if self.check_token_existence(path):
            self.logger.warning("Tokens for path '%s' already exist." % path)
            if not self.overwrite:
                self.logger.warning("Not overwriting.")
                return
            self.logger.warning(
                "Revoking existing tokens for path '%s'." % path)
            self.revoke(path)
        admin_tok = self.create_admin_token(path)
        self.create_rw_tokens(admin_tok, path)

    def check_token_existence(self, path):
        there = self.vault_client.list(TOKEN_SECRET_ROOT + "/" + path)
        if there:
            return True
        return False

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
        toksec = TOKEN_SECRET_ROOT + "/" + path + "/" + role
        self.logger.debug("Writing token store for '%s/%s'." % (path, role))
        self.vault_client.write(toksec + "/id",
                                value=tok_id)
        self.vault_client.write(toksec + "/accessor",
                                value=accessor)

    def delete_tokens(self, path):
        """Revoke tokens for path and remove token id store.
        """
        tok_store = TOKEN_SECRET_ROOT + "/" + path
        for role in ["read", "write", "admin"]:
            this_tok = tok_store + "/" + role
            id_secpath = this_tok + "/id"
            self.logger.debug("Requesting ID for '%s' token for '%s'." % (
                role, path))
            tokendata = self.vault_client.read(id_secpath)
            if tokendata:
                token = tokendata["data"]["value"]
            else:
                self.logger.warning(
                    "Cannot find token ID for '%s'." % this_tok)
                continue
            self.logger.debug("Deleting '%s' token for '%s'." % (
                role, path))
            self.vault_client.revoke_token(token=token)
        self.logger.debug("Deleting token store for '%s'." % path)
        dc = RecursiveDeleter(self.url, self.token, self.cacert, self.debug)
        dc.recursive_delete(tok_store)


if __name__ == '__main__':
    standalone()
