# LSST Vault Utilities

This package is a set of Vault utilities useful for the LSST use case.

## LSST Vault Hierarchy

These tools are intended to work with a specific taxonomic hierarchy,
detailed below.

### Secrets

The primary use case for the LSST vault has been to act as a repository
for Kubernetes secrets.  Those are organized as follows:

```
secret/k8s_operator/:instance:
```

These secrets are typically created and injected at cluster creation
time; in the case of the LSP deployment, this is scripted.  We
use [Vault
Secrets Operator](https://github.com/ricoberger/vault-secrets-operator)
to automatically manage the translation of vault secrets into Kubernetes
secrets.

The secondary, more flexible, use case is to use the LSST vault as a
generalized key-value store.

When used in this mode, the LSST vault is organized with secrets under
`secret` as follows:

```
secret/:subsystem:/:team:/:category:/:instance:
```

Each of these vault paths, terminating in `:instance:` is referred to as
an enclave in our nomenclature.  An enclave has both a read and a write
token.

The way an enclave is used is that the user will populate the secret
tree under that enclave with the write token, and then use the read
token for automated data retrieval.  In the case of
`vault-secrets-operator` it is the read key that should be used to
populate K8s secrets from the vault secrets.

Note that secrets in an enclave are *not* accessible to the
administrative user that created the enclave, its token pair, and its
policies.  Those secrets are only accessed through either the enclave's
read or its write token.

## Usage

### Tokens

The first thing to do, with an administrative token, is to create a
delegator token which will be the token used to run the Vault token
provisioning tools.  Use [delegator.hcl](delegator.hcl) as the input to
create a policy for this.  Then create a token with that new delegator
policy attached.

Token IDs and accessors are stored under
`secret/delegated/:subsystem:/:team:/:category:/:instance:/:role:/:type:`
where `role` is one of `read` or `write` and `type` is one of `id` or
`accessor`.  These secrets are only accessible to an administrative user
(such as the one that created the token pair in the first place, which
should be the token attached to the `delegator` policy created
above).

There are two tokens for each enclave, comprising the "token pair".
These are `read` and `write`.

It is our intention that a runtime system have access to the `read`
token to be able to read (but not update) secrets, and that the
administrators of such a system have access to the `write` token to
create, update, and remove secrets.

We previously provided a tool that allowed easy copying of Kubernetes
secrets to and from Vault.  That tool has now been removed, because
`vault-secrets-operator` is a Kubernetes operator that provides
automated synchronization of secrets.

### Policies

Policies are stored as
`delegated/:subsystem:/:team:/:category:/:instance:/:role:` where role
is one of `read` or `write`.  The administrative user that
creates or revokes the token pair is also responsible for creating and
destroying these policies.

## Classes

The package name is `lsstvaultutils`.  Its functional classes are:

1. `AdminTool` -- this highly LSST-specific class allows you to specify a
   path under the Vault secret store, and it will generate two tokens
   (read and write) for manipulating secrets under the path.  It
   stores those under secret/delegated, so that an admin can find (and,
   if need be, revoke) them later.  It also manages revoking those
   tokens and removing them from the secret/delegated path.  Options
   exist to, if manipulating tokens on a path that already exist, revoke
   the old tokens and overwrite with new ones, or to remove the secret
   data at the same time as the tokens are revoked.  There is also a
   function to display the IDs and accessors of the token pair
   associated with the path.

2. `VaultConfig` -- this is another very LSST-specific class which is
   useful for adding or removing secrets at a given path across multiple
   vault enclaves.
   
3. `RecursiveDeleter` -- this adds a recursive deletion feature to Vault
   for removing a whole secret tree at a time.
   
There is also a TimeFormatter class that exists only to add milliseconds
to the debugging logs.  There is a convenience function, `getLogger`,
that provides an interface to get a standardized logger for these tools and
classes.

## Programs

The major functionality of these classes is also exposed as standalone
programs.

1. `tokenadmin` -- Create or revoke token sets for a given Vault secret
   path, or display the token IDs and accessors for that path.

2. `multisecret` -- Create or remove a secret path across multiple Vault
   enclaves.  This is useful when adding a new feature to a K8s-managed
   Science Platform application, for instance.

3. `vaultrmrf` -- Remove a Vault secret path and everything underneath
   it.  As is implied by the name, this is a fairly dangerous operation.

## Example Workflow

We will go through a workflow that exercises `tokenadmin` and
`vaultrmrf` by creating a token pair, creating some secrets, deleting a
secret tree, and finally deleting the token pair.

### Create a token pair.

First we'll create a token pair for a hierarchy at `dm/test`.  (Note
that we have omitted a level of hierarchy to make the output slightly
more readable; `dm/square/test` would be more realistic.)  We ensure
that `VAULT_ADDR` and `VAULT_CAPATH` are set correctly, and that
`VAULT_TOKEN` is set to an appropriate administrative token.  We're
going to use `debug` to get an idea of what's going on during the
process, and we will use the `display` option to print JSON representing
the tokens.

I am using a `vaultutils` virtualenv with the `lsstvaultutils` package
installed, and the `vault` CLI is on my path.

    (vaultutils) adam@ixitxachitl:~$ tokenadmin create --debug --display dm/test
    2019-03-04 14:45:52.625 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Debug logging started.
    2019-03-04 14:45:52.625 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting Vault client for 'https://35.184.246.111'.
    2019-03-04 14:45:52.939 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Vault Client is authenticated.
    2019-03-04 14:45:52.939 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policies and tokens for 'dm/test'.
    2019-03-04 14:45:52.939 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policies for 'dm/test'.
    2019-03-04 14:45:52.939 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Checking for existence of policy 'delegated/dm/test'.
    2019-03-04 14:45:53.109 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policy for 'dm/test/read'.
    2019-03-04 14:45:53.109 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy string:  path "secret/data/dm/test/*" {
       capabilities = ["read"]
     }
     path "secret/metadata/dm/test/*" {
       capabilities = ["read","list"]
     }

    2019-03-04 14:45:53.109 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy path: delegated/dm/test/read
    2019-03-04 14:45:53.535 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policy for 'dm/test/write'.
    2019-03-04 14:45:53.535 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy string:  path "secret/data/dm/test" {
       capabilities = ["read", "create", "update", "delete"]
     }
     path "secret/data/dm/test/*" {
       capabilities = ["read", "create", "update", "delete"]
     }
     path "secret/metadata/dm/test/*" {
       capabilities = ["list", "read", "update","delete"]
     }
     path "secret/metadata/dm/test" {
       capabilities = ["list", "read", "update","delete"]
     }
     path "secret/delete/dm/test/*" {
       capabilities = ["update"]
     }
     path "secret/undelete/dm/test/*" {
       capabilities = ["update"]
     }
     path "secret/destroy/dm/test/*" {
       capabilities = ["update"]
     }

    2019-03-04 14:45:53.535 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy path: delegated/dm/test/write
    2019-03-04 14:45:54.217 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating token for 'dm/test/read'.
    2019-03-04 14:45:54.217 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin |  - policies '['delegated/dm/test/read']'.
    2019-03-04 14:45:55.630 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Writing token store for 'dm/test/read'.
    2019-03-04 14:45:55.630 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin |  'delegated/dm/test/read' -> 's.3nyTeqdWiINKIKNtuoIDtD9D'.
    2019-03-04 14:45:56.840 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating token for 'dm/test/write'.
    2019-03-04 14:45:56.840 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin |  - policies '['delegated/dm/test/write']'.
    2019-03-04 14:45:58.171 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Writing token store for 'dm/test/write'.
    2019-03-04 14:45:58.171 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin |  'delegated/dm/test/write' -> 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 14:45:59.335 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting tokens for 'dm/test'.
    {
        "dm/test": {
            "read": {
                "accessor": "1WRccTQEebkqx78t37EyVztK",
                "id": "s.3nyTeqdWiINKIKNtuoIDtD9D"
            },
            "write": {
                "accessor": "8LvOhKiGFJf9qYNIgOXrb8Ik",
                "id": "s.4l4eDdLMyD436RsjRqlI11cD"
            }
        }
    }


### Add some secrets

First, set Vault to use the `write` token:

```
export VAULT_TOKEN="s.4l4eDdLMyD436RsjRqlI11cD"
```

I like JSON output, so I'm going to set:

```
export VAULT_FORMAT=json
```

Then use the vault client to add some secrets:


	(vaultutils) adam@ixitxachitl:~$ vault kv put secret/dm/test/group1/foo value=bar
    {
      "request_id": "0a814bd2-e95d-cf1c-9018-c00173668e3d",
      "lease_id": "",
      "lease_duration": 0,
      "renewable": false,
      "data": {
        "created_time": "2019-03-04T21:51:07.616034224Z",
        "deletion_time": "",
        "destroyed": false,
        "version": 1
      },
      "warnings": null
    }
    (vaultutils) adam@ixitxachitl:~$ vault kv put secret/dm/test/group1/baz value=quux
    {
      "request_id": "38c65e0d-735d-db9a-c2d6-840bdd4dff65",
      "lease_id": "",
      "lease_duration": 0,
      "renewable": false,
      "data": {
        "created_time": "2019-03-04T21:51:34.991913644Z",
        "deletion_time": "",
        "destroyed": false,
        "version": 1
      },
      "warnings": null
    }
    (vaultutils) adam@ixitxachitl:~$ vault kv put secret/dm/test/group2/king value=fink
    {
      "request_id": "12753857-25f2-a27a-3d65-badc18805d07",
      "lease_id": "",
      "lease_duration": 0,
      "renewable": false,
      "data": {
        "created_time": "2019-03-04T21:51:45.645224365Z",
        "deletion_time": "",
        "destroyed": false,
        "version": 1
      },
      "warnings": null
    }

Read one back:

    (vaultutils) adam@ixitxachitl:~$ vault kv get secret/dm/test/group1/baz
    {
      "request_id": "03ef8ba1-3eb2-2962-d4c6-ebaf595e3387",
      "lease_id": "",
      "lease_duration": 0,
      "renewable": false,
      "data": {
        "data": {
          "value": "quux"
        },
        "metadata": {
          "created_time": "2019-03-04T21:51:34.991913644Z",
          "deletion_time": "",
          "destroyed": false,
          "version": 1
        }
      },
      "warnings": null
    }

### Recursively remove a secret tree

Let's say we didn't really want those secrets after all.  We can easily
remove the tree with the `vaultrmrf` command and the write token.

    (vaultutils) adam@ixitxachitl:~$ vaultrmrf --debug dm/test/copy1
    2019-03-04 15:05:47.920 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-03-04 15:05:47.920 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-03-04 15:05:48.164 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/copy1' recursively.
    2019-03-04 15:05:48.269 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'dm/test/copy1'
    2019-03-04 15:05:48.269 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': 'f6774de1-cb8c-76ed-8425-7963b5d95d76', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['baz', 'foo']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:05:48.269 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/copy1/baz' recursively.
    2019-03-04 15:05:48.369 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/copy1/baz' as leaf node.
    2019-03-04 15:05:48.369 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:05:48.703 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/copy1/foo' recursively.
    2019-03-04 15:05:48.809 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/copy1/foo' as leaf node.
    2019-03-04 15:05:48.809 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:05:49.123 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/copy1' as leaf node.
    2019-03-04 15:05:49.123 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.


Trying to read the secret now will show it's gone:

    (vaultutils) adam@ixitxachitl:~$ vault kv get secret/dm/test/copy1/foo
    No value found at secret/data/dm/test/copy1/foo

### Revoke Token Pair and remove data

Now we will clean up:

We go back to an administrative token to revoke our token pair (by
setting `VAULT_TOKEN` to an appropriate value), and while we're at it we
will clean up the data we inserted into vault as well.

    (vaultutils) adam@ixitxachitl:~$ tokenadmin revoke --delete-data --debug dm/test2019-03-04 15:08:12.888 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Debug logging started.
    2019-03-04 15:08:12.888 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting Vault client for 'https://35.184.246.111'.
    2019-03-04 15:08:13.147 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Vault Client is authenticated.
    2019-03-04 15:08:13.147 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Revoking tokens and removing policies for 'dm/test'.
    2019-03-04 15:08:13.147 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting write token for 'dm/test'.
    2019-03-04 15:08:13.147 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Reading value from 'delegated/dm/test/write/id'.
    2019-03-04 15:08:13.208 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Got data: {'request_id': 'e5084c92-f404-7338-f776-47f1d8ee5980', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'data': {'value': 's.4l4eDdLMyD436RsjRqlI11cD'}, 'metadata': {'created_time': '2019-03-04T21:45:58.325211493Z', 'deletion_time': '', 'destroyed': False, 'version': 1}}, 'wrap_info': None, 'warnings': None, 'auth': None}
    2019-03-04 15:08:13.208 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-03-04 15:08:13.208 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-03-04 15:08:13.498 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting data under 'dm/test'.
    2019-03-04 15:08:13.498 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test' recursively.
    2019-03-04 15:08:13.638 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'dm/test'
    2019-03-04 15:08:13.638 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '661160b2-6916-62f5-ae29-8da0d576d841', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['group1/', 'group2/']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:13.638 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group1' recursively.
    2019-03-04 15:08:13.907 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'dm/test/group1'
    2019-03-04 15:08:13.907 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '02e65063-64e2-8ca9-1532-f3aaf1eaeeb5', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['baz', 'foo']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:13.908 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group1/baz' recursively.
    2019-03-04 15:08:14.262 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group1/baz' as leaf node.
    2019-03-04 15:08:14.262 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:08:14.729 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group1/foo' recursively.
    2019-03-04 15:08:14.906 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group1/foo' as leaf node.
    2019-03-04 15:08:14.906 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:08:15.409 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group1' as leaf node.
    2019-03-04 15:08:15.409 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:08:15.560 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group2' recursively.
    2019-03-04 15:08:15.716 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'dm/test/group2'
    2019-03-04 15:08:15.716 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '9a9f23d3-f5cf-10c7-e18c-2f54a848e3e7', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['king']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:15.716 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group2/king' recursively.
    2019-03-04 15:08:15.866 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group2/king' as leaf node.
    2019-03-04 15:08:15.866 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:08:16.480 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test/group2' as leaf node.
    2019-03-04 15:08:16.480 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:08:16.623 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'dm/test' as leaf node.
    2019-03-04 15:08:16.623 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.4l4eDdLMyD436RsjRqlI11cD'.
    2019-03-04 15:08:16.765 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Requesting ID for 'read' token for 'dm/test'.
    2019-03-04 15:08:16.826 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Tokendata: {'request_id': '845ca454-5b0e-9518-9029-bf221c771e4f', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'data': {'value': 's.3nyTeqdWiINKIKNtuoIDtD9D'}, 'metadata': {'created_time': '2019-03-04T21:45:55.802574394Z', 'deletion_time': '', 'destroyed': False, 'version': 1}}, 'wrap_info': None, 'warnings': None, 'auth': None}
    2019-03-04 15:08:16.827 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting 'read' token for 'dm/test'.
    2019-03-04 15:08:18.393 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Requesting ID for 'write' token for 'dm/test'.
    2019-03-04 15:08:18.454 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Tokendata: {'request_id': '5f3aae99-59f4-618b-cf1c-cb9bc3b39478', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'data': {'value': 's.4l4eDdLMyD436RsjRqlI11cD'}, 'metadata': {'created_time': '2019-03-04T21:45:58.325211493Z', 'deletion_time': '', 'destroyed': False, 'version': 1}}, 'wrap_info': None, 'warnings': None, 'auth': None}
    2019-03-04 15:08:18.455 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting 'write' token for 'dm/test'.
    2019-03-04 15:08:19.845 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting token store for 'dm/test'.
    2019-03-04 15:08:19.846 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-03-04 15:08:19.846 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-03-04 15:08:19.846 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-03-04 15:08:19.846 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-03-04 15:08:20.085 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Recursive delete of: 'delegated/dm/test'
    2019-03-04 15:08:20.085 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test' recursively.
    2019-03-04 15:08:20.085 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test' recursively.
    2019-03-04 15:08:20.199 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'delegated/dm/test'
    2019-03-04 15:08:20.199 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'delegated/dm/test'
    2019-03-04 15:08:20.199 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '5c1f33cf-8878-a5c8-a884-1f5cda607fa6', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['read/', 'write/']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:20.199 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '5c1f33cf-8878-a5c8-a884-1f5cda607fa6', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['read/', 'write/']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:20.199 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read' recursively.
    2019-03-04 15:08:20.199 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read' recursively.
    2019-03-04 15:08:20.317 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'delegated/dm/test/read'
    2019-03-04 15:08:20.317 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'delegated/dm/test/read'
    2019-03-04 15:08:20.317 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '4d18f739-1ee7-c413-6b9a-1766f6f300de', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['accessor', 'id']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:20.317 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '4d18f739-1ee7-c413-6b9a-1766f6f300de', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['accessor', 'id']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:20.317 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/accessor' recursively.
    2019-03-04 15:08:20.317 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/accessor' recursively.
    2019-03-04 15:08:20.422 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/accessor' as leaf node.
    2019-03-04 15:08:20.422 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/accessor' as leaf node.
    2019-03-04 15:08:20.422 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:20.422 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:20.856 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/id' recursively.
    2019-03-04 15:08:20.856 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/id' recursively.
    2019-03-04 15:08:20.971 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/id' as leaf node.
    2019-03-04 15:08:20.971 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read/id' as leaf node.
    2019-03-04 15:08:20.972 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:20.972 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:21.406 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read' as leaf node.
    2019-03-04 15:08:21.406 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/read' as leaf node.
    2019-03-04 15:08:21.406 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:21.406 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:21.492 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write' recursively.
    2019-03-04 15:08:21.492 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write' recursively.
    2019-03-04 15:08:21.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'delegated/dm/test/write'
    2019-03-04 15:08:21.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'delegated/dm/test/write'
    2019-03-04 15:08:21.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '8446aa1b-3d86-3b0d-eb55-01a9fe0e1cad', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['accessor', 'id']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:21.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | resp = '{'request_id': '8446aa1b-3d86-3b0d-eb55-01a9fe0e1cad', 'lease_id': '', 'renewable': False, 'lease_duration': 0, 'data': {'keys': ['accessor', 'id']}, 'wrap_info': None, 'warnings': None, 'auth': None}'
    2019-03-04 15:08:21.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/accessor' recursively.
    2019-03-04 15:08:21.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/accessor' recursively.
    2019-03-04 15:08:21.707 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/accessor' as leaf node.
    2019-03-04 15:08:21.707 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/accessor' as leaf node.
    2019-03-04 15:08:21.708 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:21.708 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:22.120 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/id' recursively.
    2019-03-04 15:08:22.120 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/id' recursively.
    2019-03-04 15:08:22.224 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/id' as leaf node.
    2019-03-04 15:08:22.224 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write/id' as leaf node.
    2019-03-04 15:08:22.224 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:22.224 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:22.673 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write' as leaf node.
    2019-03-04 15:08:22.673 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test/write' as leaf node.
    2019-03-04 15:08:22.673 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:22.673 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:22.761 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test' as leaf node.
    2019-03-04 15:08:22.761 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'delegated/dm/test' as leaf node.
    2019-03-04 15:08:22.761 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:22.761 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Using token 's.86o9UFmo4bbd4yxs1pWHS2Z1'.
    2019-03-04 15:08:22.856 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting policy for 'delegated/dm/test/read'.
    2019-03-04 15:08:23.039 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting policy for 'delegated/dm/test/write'.

And now the system is back in the state in which we started.

### Verifying token deletion

We can try an operation to see that the tokens have been revoked.  Set
up the (now-revoked) read token: `export
VAULT_TOKEN="s.3nyTeqdWiINKIKNtuoIDtD9D"`.  Then try the same read we
previously ran again:

    (vaultutils) adam@ixitxachitl:~$ vault kv get secret/dm/test/group1/baz
    Error making API request.

    URL: GET https://35.184.246.111/v1/sys/internal/ui/mounts/secret/dm/test/group1/baz
    Code: 403. Errors:

    * permission denied

### Using multisecret

In this workflow, we will use `multisecret` to add a secret to a
Kubernetes `vault-secrets-operator` path.  We will add it to two enclaves,
`data-dev.lsst.cloud` and `nublado.lsst.codes`, verify that the secrets
were created, and then remove them, also with `multisecret`.

First we ensure we have `lsstvaultutils` installed into our active
environment (that's what the `(lvu)` at the front of the prompt tells
us) and then we run `multisecret --help`:

	Usage: multisecret [OPTIONS] COMMAND [ARGS]...

	  A tool to manipulate secrets in the same relative location across vault
	  enclaves.

	  --vault-address is a string representing a URL for a Vault implementation,
	  e.g. "vault.lsst.codes".  If unspecified, the value of the environment
	  variable VAULT_ADDR will be used.  It that isn't specified either, the
	  default of "http://localhost:8200" will be used.

	  --secret-name is a string representing the name of the secret relative to
	  the top of the enclave, e.g. "pull-secret".

	  --secret-file is only used with the "add" command.  It is a path to a JSON
	  document that specifies the contents of the secret you want to inject, as
	  a single object with key-value pairs, each pair being the name of the item
	  within the secret and its value.

	  --vault-file is a path to a file that contains a JSON document that is a
	  list of enclaves (each one being a dict whose only key is the name of the
	  top of the vault path for the enclave, and whose values are pair of dicts,
	  "read" and "write", each a dict containing two keys, "accessor" and "id",
	  whose values are the vault accessor and the vault token for its respective
	  context within the enclave).  Not by coincidence, this is the form in
	  which the vault document exists in SQuaRE's 1password.

	  --omit may be specified multiple times; each time it is specified, it is
	  the name of the enclave to skip when updating vaults.  This is helpful,
	  for example, to *not* put the SQuaRE docker pull password into third-party
	  implementations that rely on vault.lsst.codes.

	  --dry-run is a boolean flag; if it is set, no change to the vault will
	  actually be made, although the tool will report on the changes it would
	  have done.

	Options:
	  -a, --vault-address TEXT
	  -n, --secret-name TEXT    [required]
	  -s, --secret-file TEXT
	  -v, --vault-file TEXT     [required]
	  -o, --omit TEXT
	  -x, --dry-run
	  --help                    Show this message and exit.

	Commands:
	  add     Add a secret across enclaves.
	  remove  Remove a secret from multiple enclaves.

Let's set up a working directory to hold our configuration and configure
vault:

    (lvu) adam@air-wired:~/git/lsstvaultutils$ mkdir -p ~/Documents/src/vault-doc-test
    (lvu) adam@air-wired:~/git/lsstvaultutils$ cd ~/Documents/src/vault-doc-test
    (lvu) adam@air-wired:~/Documents/src/vault-doc-test$ export VAULT_ADDR="https://vault.lsst.codes"
    (lvu) adam@air-wired:~/Documents/src/vault-doc-test$ export VAULT_FORMAT="json"
    (lvu) adam@air-wired:~/Documents/src/vault-doc-test$

Armed with this knowledge, we prepare a multi-enclave file.  We will
call it `vault-nb-idf` and its contents will look like the following,
except with actual keys.

	[
	  {
		"k8s_operator/nublado.lsst.codes": {
		  "read": {
			"accessor": "[REDACTED]",
			"id": "[REDACTED]"
		  },
		  "write": {
			"accessor": "[REDACTED]",
			"id": "[REDACTED]"
		  }
		}
	  },
	  {
		"k8s_operator/data-dev.lsst.cloud": {
		  "read": {
			"accessor": "[REDACTED]",
			"id": "[REDACTED]"
		  },
		  "write": {
			"accessor": "[REDACTED]",
			"id": "[REDACTED]"
		  }
		}
	  }
	]

Next we'll create the payload.  `testcase.json` contains simply:

    { "foo": "bar" }

Let's verify that our new secret (which we will call simply `test`) does
not exist in either enclave yet.  I have put the read tokens into other
shell variables that are, for obvious reasons, not in this document:

	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv list secret/k8s_operator/data-dev.lsst.cloud
	[
	  "cert-manager",
	  "gafaelfawr",
	  "log",
	  "mobu",
	  "nublado",
	  "nublado2",
	  "postgres",
	  "pull-secret",
	  "tap"
	]
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ export VAULT_TOKEN=${NLC_READ_TOKEN}
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv list secret/k8s_operator/nublado.lsst.codes
	[
	  "cert-manager",
	  "gafaelfawr",
	  "jwt_authorizer",
	  "mobu",
	  "nublado",
	  "postgres",
	  "tap"
	]

Let's run it with `--dry-run` first to make sure it looks correct:

	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ multisecret --vault-address=https://vault.lsst.codes --secret-name test --secret-file testcase.json --vault-file vault-nb-idf.json --dry-run add
	Dry run: add secret at https://vault.lsst.codes/k8s_operator/nublado.lsst.codes/test
	Dry run: add secret at https://vault.lsst.codes/k8s_operator/data-dev.lsst.cloud/test

Seems right.  Repeat without `--dry-run`.

	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ multisecret --vault-address=https://vault.lsst.codes --secret-name test --secret-file testcase.json --vault-file vault-nb-idf.json add
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$

Verify that the secrets were made:

	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ export VAULT_TOKEN=${DLC_READ_TOKEN}
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv get secret/k8s_operator/data-dev.lsst.cloud/test
	{
	  "request_id": "bb53344a-31e9-81d3-32c2-5f2f895d7554",
	  "lease_id": "",
	  "lease_duration": 0,
	  "renewable": false,
	  "data": {
		"data": {
		  "foo": "bar"
		},
		"metadata": {
		  "created_time": "2020-12-10T19:18:58.345274962Z",
		  "deletion_time": "",
		  "destroyed": false,
		  "version": 1
		}
	  },
	  "warnings": null
	}
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ export VAULT_TOKEN=${NLC_READ_TOKEN}
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv get secret/k8s_operator/nublado.lsst.codes/test
	{
	  "request_id": "5f69665d-e8ca-f9a3-aa69-5fe12c1784c0",
	  "lease_id": "",
	  "lease_duration": 0,
	  "renewable": false,
	  "data": {
		"data": {
		  "foo": "bar"
		},
		"metadata": {
		  "created_time": "2020-12-10T19:18:57.631480686Z",
		  "deletion_time": "",
		  "destroyed": false,
		  "version": 1
		}
	  },
	  "warnings": null
	}

And now destroy them:

	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ multisecret --vault-address=https://vault.lsst.codes --secret-name test --vault-file vault-nb-idf.json remove
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$

And verify they no longer exist:

	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ export VAULT_TOKEN=${DLC_READ_TOKEN}
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv get secret/k8s_operator/data-dev.lsst.cloud/test
	No value found at secret/data/k8s_operator/data-dev.lsst.cloud/test
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv list secret/k8s_operator/data-dev.lsst.cloud
	[
	  "cert-manager",
	  "gafaelfawr",
	  "log",
	  "mobu",
	  "nublado",
	  "nublado2",
	  "postgres",
	  "pull-secret",
	  "tap"
	]
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ export VAULT_TOKEN=${NLC_READ_TOKEN}
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv get secret/k8s_operator/nublado.lsst.codes/test
	No value found at secret/data/k8s_operator/nublado.lsst.codes/test
	(lvu) adam@air-wired:~/Documents/src/vault-doc-test$ vault kv list secret/k8s_operator/nublado.lsst.codes
	[
	  "cert-manager",
	  "gafaelfawr",
	  "jwt_authorizer",
	  "mobu",
	  "nublado",
	  "postgres",
	  "tap"
	]
