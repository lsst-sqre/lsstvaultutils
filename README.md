# LSST Vault Utilities

This package is a set of Vault utilities useful for the LSST use case.

## LSST Vault Hierarchy

These tools are intended to work with a specific taxonomic hierarchy,
detailed below.

### Secrets

The current plan is for the LSST vault to be organized with secrets
under `secret` as follows:

`secret/:subsystem:/:team:/:category:/:instance:`

As an example, secrets for the `jupyterlabdemo.lsst.codes` instance of
the LSST Science Platform Notebook Aspect are stored in
`secret/dm/square/jellybean/jupyterlabdemo.lsst.codes`.  Underneath that
there are `hub`, `proxy`, and `tls` secret folders, each of which has a
number of individual secrets,
e.g. `secret/dm/square/jellybean/jupyterlabdemo.lsst.codes/hub/oauth_secret`.

Note that these secrets are *not* accessible to the administrative user
that created the token trio and policies.  They are accessed through one
of those tokens.

We assume that each secret has its own folder, whose name is the secret
key, inside of which the keyname is `value`.  This makes translating
back and forth between Vault secrets and Kubernetes secrets (which have
multiple key-value pairs) much easier.

### Tokens

Token IDs and accessors are stored under 
`secret/delegated/:subsystem:/:team:/:category:/:instance:/:role:/:type:`
where `role` is one of `read`, `write`, or `admin` and `type` is one of
`id` or `accessor`.  These secrets are only accessible to an
administrative user (such as the one that created the token trio in the
first place).

There are three tokens for each path, comprising the "token trio".
These are `read`, `write`, and `admin`.

At the moment, `admin` is only useful for deleting secret trees (`write`
can create new secrets, or update existing secrets, but not delete
existing secrets entirely).  It will eventually be used for delegation of
further token-granting privileges within a secret tree, but that will
require a fairly sophisticated use of Vault entities, roles, and
templated policies, and is regarded as a possible future enhancement
rather than a near-term priority.

It is our intention that a runtime system have access to the `read`
token to be able to read (but not update) secrets, and that the
administrators of such a system have access to the `write` token to
create and update secrets and the `admin` token to remove trees of
secrets.  We have provided a tool that allows easy copying of Kubernetes
secrets to and from Vault.

### Policies

Policies are stored as
`delegated/:subsystem:/:team:/:category:/:instance:/:role:` where role
is one of `read`, `write`, or `admin`.  The administrative user that
creates or revokes the token trio is also responsible for creating and
destroying these policies.

## Classes

The package name is `lsstvaultutils`.  Its functional classes are:

1. `SecretCopier` -- this copies secrets between the current Kubernetes
   context and a Vault instance.
   
2. `AdminTool` -- this highly LSST-specific class allows you to specify a
   path under the Vault secret store, and it will generate three tokens
   (read, write, and admin) for manipulating secrets under the path.  It
   stores those under secret/delegated, so that an admin can find (and,
   if need be, revoke) them later.  It also manages revoking those
   tokens and removing them from the secret/delegated path.  Options
   exist to, if manipulating tokens on a path that already exist, revoke
   the old tokens and overwrite with new ones, or to remove the secret
   data at the same time as the tokens are revoked.  There is also a
   function to display the IDs and accessors of the token trio
   associated with the path.
   
3. `RecursiveDeleter` -- this adds a recursive deletion feature to Vault
   for removing a whole secret tree at a time.
   
There is also a TimeFormatter class that exists only to add milliseconds
to the debugging logs.  There is a convenience function, `getLogger`,
that provides an interface to get a standardized logger for these tools and
classes.

## Programs

The major functionality of these classes is also exposed as standalone
programs.

1. `copyk2v` -- copy the contents of a  Kubernetes secret to a Vault
   secret path.

2. `copyv2k` -- copy a set of Vault secrets at a specified path to a
   Kubernetes secret.
   
3. `tokenadmin` -- Create or revoke token sets for a given Vault secret
   path, or display the token IDs and accessors for that path.
   
4. `vaultrmrf` -- Remove a Vault secret path and everything underneath
   it.  As is implied by the name, this is a fairly dangerous operation.

## Example Workflow

We will go through a workflow that exercises all of the standalone
programs, by creating a token trio, creating some secrets, copying the
secrets from Vault to Kubernetes and back again, deleting a secret tree,
and finally deleting the token trio.

### Create a token trio.

First we'll create a token trio for a hierarchy at `dm/square/test`.  We
ensure that `VAULT_ADDR` and `VAULT_CAPATH` are set correctly, and that
`VAULT_TOKEN` is set to an appropriate administrative token.  We're
going to use `debug` to get an idea of what's going on during the
process, and we will use the `display` option to print JSON representing
the tokens.

I am using a `vaultutils` virtualenv with the `lsstvaultutils` package
installed, and the `vault` CLI is on my path.

    (vaultutils) adam@ixitxachitl:~/Documents/src/vault/policies$ tokenadmin create --debug --display dm/square/test
    2019-02-21 13:44:20.005 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Debug logging started.
    2019-02-21 13:44:20.006 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting Vault client for 'https://35.184.246.111'.
    2019-02-21 13:44:20.301 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Vault Client is authenticated.
    2019-02-21 13:44:20.301 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policies and tokens for 'dm/square/test'.
    2019-02-21 13:44:20.301 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policies for 'dm/square/test'.
    2019-02-21 13:44:20.301 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Checking for existence of policy 'delegated/dm/square/test'.
    2019-02-21 13:44:20.453 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policy for 'dm/square/test/read'.
    2019-02-21 13:44:20.454 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy string:  path "secret/dm/square/test/*" {
       capabilities = ["read", "list"]
     }
    
    2019-02-21 13:44:20.454 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy path: delegated/dm/square/test/read
    2019-02-21 13:44:20.775 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policy for 'dm/square/test/write'.
    2019-02-21 13:44:20.775 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy string:  path "secret/dm/square/test/*" {
       capabilities = ["read", "create", "update", "list"]
     }
    
    2019-02-21 13:44:20.775 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy path: delegated/dm/square/test/write
    2019-02-21 13:44:21.248 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating policy for 'dm/square/test/admin'.
    2019-02-21 13:44:21.248 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy string:  path "secret/dm/square/test" {
       capabilities = ["create", "read",  "update", "delete", "list"]
     }
    
     path "secret/dm/square/test/*" {
       capabilities = ["create", "read",  "update", "delete", "list"]
     }
    
    2019-02-21 13:44:21.248 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Policy path: delegated/dm/square/test/admin
    2019-02-21 13:44:21.841 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating 'admin' token for 'dm/square/test'.
    2019-02-21 13:44:21.842 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin |  - with policies '['delegated/dm/square/test/read', 'delegated/dm/square/test/write', 'delegated/dm/square/test/admin']'.
    2019-02-21 13:44:23.341 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Writing token store for 'dm/square/test/admin'.
    2019-02-21 13:44:23.967 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating token for 'dm/square/test/read'.
    2019-02-21 13:44:23.968 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin |  - policies '['delegated/dm/square/test/read']'.
    2019-02-21 13:44:25.418 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Writing token store for 'dm/square/test/read'.
    2019-02-21 13:44:26.193 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Creating token for 'dm/square/test/write'.
    2019-02-21 13:44:26.193 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin |  - policies '['delegated/dm/square/test/write']'.
    2019-02-21 13:44:27.800 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Writing token store for 'dm/square/test/write'.
    2019-02-21 13:44:28.529 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting tokens for 'dm/square/test'.
    {
        "dm/square/test": {
            "admin": {
                "accessor": "2qXdEripn2UAzINM8kdX1KrI",
                "id": "s.qybEuRzvJtzxhZK9zBa6gsJQ"
            },
            "read": {
                "accessor": "5z1Vy0AMw5Y7cGdExtSqgCIW",
                "id": "s.6JQ0zz6w6atlD1kcgisru3tY"
            },
            "write": {
                "accessor": "69QkGnTKaKLGzRAtxSUxj7pn",
                "id": "s.4BSfsSFrdpC9QnfzaBcgPp1M"
            }
        }
    }

### Add some secrets

First, set Vault to use the `write` token:

`export VAULT_TOKEN="s.4BSfsSFrdpC9QnfzaBcgPp1M"`

I like JSON output, so I'm going to set:

`export VAULT_FORMAT=json`

Then use the vault client to add some secrets:

    (vaultutils) adam@ixitxachitl:/tmp$ vault write secret/dm/square/test/group1/foo value=bar
    (vaultutils) adam@ixitxachitl:/tmp$ vault write secret/dm/square/test/group1/baz value=quux
    (vaultutils) adam@ixitxachitl:/tmp$ vault write secret/dm/square/test/group2/king value=fink


Read one back:

    adam@ixitxachitl:/tmp$ vault read secret/dm/square/test/group1/baz
    {
      "request_id": "66f57c17-b127-7476-6f89-060cc64daf94",
      "lease_id": "",
      "lease_duration": 2764800,
      "renewable": false,
      "data": {
        "value": "quux"
      },
      "warnings": null
    }

### Copy secrets to Kubernetes

Now let's create Kubernetes secrets from these.  Do whatever you need to
do in order to get a current authenticated Kubernetes context.

Switch to the "read" token--we don't need to use a write token to copy
from Vault to Kubernetes, as long as our Kubernetes user can create
secrets.

`export VAULT_TOKEN="s.6JQ0zz6w6atlD1kcgisru3tY"`

    (vaultutils) adam@ixitxachitl:/tmp$ copyv2k --debug secret/dm/square/test/group1 testg1
    2019-02-21 14:03:14.861 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Debug logging started.
    2019-02-21 14:03:14.861 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Acquiring Vault client for 'https://35.184.246.111'.
    2019-02-21 14:03:15.165 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Acquiring k8s client.
    /Users/adam/Documents/src/Venvs/vaultutils/lib/python3.7/site-packages/google/auth/_default.py:66: UserWarning: Your application has authenticated using end user credentials from Google Cloud SDK. We recommend that most server applications use service accounts instead. If your application continues to use end user credentials from Cloud SDK, you might receive a "quota exceeded" or "API not enabled" error. For more information about service accounts, see https://cloud.google.com/docs/authentication/
      warnings.warn(_CLOUD_SDK_CREDENTIALS_WARNING)
    2019-02-21 14:03:16.849 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Reading secret from 'secret/dm/square/test/group1'.
    2019-02-21 14:03:17.025 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | 'secret/dm/square/test/group1' is a set of values.
    2019-02-21 14:03:17.527 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Determining whether secret 'testg1'exists in namespace 'jupyterlabdemo'.
    2019-02-21 14:03:17.943 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Secret not found.
    2019-02-21 14:03:17.943 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Base64-encoding secret data
    2019-02-21 14:03:17.944 MST(-0700) [DEBUG] lsstvaultutils.secretcopier | Creating secret.

Repeat the process for the second group; we'll omit --debug this time.

    (vaultutils) adam@ixitxachitl:/tmp$ copyv2k secret/dm/square/test/group2 testg2
    (vaultutils) adam@ixitxachitl:/tmp$

Now let's see if the copy worked.

    (vaultutils) adam@ixitxachitl:/tmp$ kubectl get -o yaml secret testg2
    apiVersion: v1
    data:
      king: Zmluaw==
    kind: Secret
    metadata:
      creationTimestamp: 2019-02-21T21:04:37Z
      name: testg2
      namespace: jupyterlabdemo
      resourceVersion: "8474295"
      selfLink: /api/v1/namespaces/jupyterlabdemo/secrets/testg2
      uid: 4c0e5949-361c-11e9-a1ce-42010a800032
    type: Opaque
	
Decode that secret:

    (vaultutils) adam@ixitxachitl:/tmp$ echo -n Zmluaw== | base64 -D -
    fink

### Copy secret from Kubernetes to Vault

Go back to the "write" token:

    export VAULT_TOKEN="s.4BSfsSFrdpC9QnfzaBcgPp1M"

Copy the secret to a new Vault path:

    (vaultutils) adam@ixitxachitl:/tmp$ copyk2v testg1 secret/dm/square/test/copy1

Read a value (we _could_ switch to the Vault `read` token, but we don't
have to--`write` is also allowed to read) back:

    (vaultutils) adam@ixitxachitl:/tmp$ vault read secret/dm/square/test/copy1/foo
    {
      "request_id": "afab6814-6dd0-c9c5-7b5c-022344b681cf",
      "lease_id": "",
      "lease_duration": 2764800,
      "renewable": false,
      "data": {
        "value": "bar"
      },
      "warnings": null
    }

### Recursively remove a secret tree

Let's say we didn't really want to do that last copy.  We can easily
remove the tree.

First we need to use the admin token: `export
VAULT_TOKEN=s.qybEuRzvJtzxhZK9zBa6gsJQ"`

Then we can use the `vaultrmrf` command to delete the tree.

    (vaultutils) adam@ixitxachitl:/tmp$ vaultrmrf --debug secret/dm/square/test/copy1
    2019-02-21 14:25:07.012 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-02-21 14:25:07.012 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-02-21 14:25:07.261 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/copy1' recursively.
    2019-02-21 14:25:07.391 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/dm/square/test/copy1'
    2019-02-21 14:25:07.391 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/copy1/baz' recursively.
    2019-02-21 14:25:07.503 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/copy1/baz' as leaf node.
    2019-02-21 14:25:07.691 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/copy1/foo' recursively.
    2019-02-21 14:25:07.820 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/copy1/foo' as leaf node.

Trying to read the secret now will show it's gone (`admin` can read just as well as `write` can):

    (vaultutils) adam@ixitxachitl:/tmp$ vault read secret/dm/square/test/copy1/foo
    No value found at secret/dm/square/test/copy1/foo

### Revoke Token Trio and remove data

Now we will clean up:

    (vaultutils) adam@ixitxachitl:/tmp$ kubectl delete secret testg1 testg2
    secret "testg1" deleted
    secret "testg2" deleted

We go back to an administrative token to revoke our token trio (by
setting `VAULT_TOKEN` to an appropriate value), and while we're at it we
will clean up the data we inserted into vault as well.

    (vaultutils) adam@ixitxachitl:/tmp$ tokenadmin revoke --delete-data --debug dm/square/test
    2019-02-21 14:10:36.758 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Debug logging started.
    2019-02-21 14:10:36.758 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting Vault client for 'https://35.184.246.111'.
    2019-02-21 14:10:37.042 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Vault Client is authenticated.
    2019-02-21 14:10:37.042 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Revoking tokens and removing policies for 'dm/square/test'.
    2019-02-21 14:10:37.042 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Getting admin token for 'dm/square/test'.
    2019-02-21 14:10:37.140 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-02-21 14:10:37.141 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-02-21 14:10:37.383 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting data under 'secret/dm/square/test'.
    2019-02-21 14:10:37.383 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test' recursively.
    2019-02-21 14:10:37.493 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/dm/square/test'
    2019-02-21 14:10:37.493 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group1/' recursively.
    2019-02-21 14:10:37.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/dm/square/test/group1'
    2019-02-21 14:10:37.603 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group1/baz' recursively.
    2019-02-21 14:10:37.716 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group1/baz' as leaf node.
    2019-02-21 14:10:38.030 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group1/foo' recursively.
    2019-02-21 14:10:38.134 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group1/foo' as leaf node.
    2019-02-21 14:10:38.421 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group2/' recursively.
    2019-02-21 14:10:38.534 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/dm/square/test/group2'
    2019-02-21 14:10:38.534 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group2/king' recursively.
    2019-02-21 14:10:38.648 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/dm/square/test/group2/king' as leaf node.
    2019-02-21 14:10:38.825 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Requesting ID for 'read' token for 'dm/square/test'.
    2019-02-21 14:10:38.922 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting 'read' token for 'dm/square/test'.
    2019-02-21 14:10:40.323 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Requesting ID for 'write' token for 'dm/square/test'.
    2019-02-21 14:10:40.433 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting 'write' token for 'dm/square/test'.
    2019-02-21 14:10:42.022 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Requesting ID for 'admin' token for 'dm/square/test'.
    2019-02-21 14:10:42.122 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting 'admin' token for 'dm/square/test'.
    2019-02-21 14:10:43.437 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting token store for 'dm/square/test'.
    2019-02-21 14:10:43.438 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-02-21 14:10:43.438 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Debug logging started.
    2019-02-21 14:10:43.438 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-02-21 14:10:43.438 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Acquiring Vault client for 'https://35.184.246.111'.
    2019-02-21 14:10:43.679 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test' recursively.
    2019-02-21 14:10:43.679 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test' recursively.
    2019-02-21 14:10:43.844 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test'
    2019-02-21 14:10:43.844 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test'
    2019-02-21 14:10:43.844 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/' recursively.
    2019-02-21 14:10:43.844 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/' recursively.
    2019-02-21 14:10:43.964 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test/admin'
    2019-02-21 14:10:43.964 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test/admin'
    2019-02-21 14:10:43.964 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/accessor' recursively.
    2019-02-21 14:10:43.964 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/accessor' recursively.
    2019-02-21 14:10:44.079 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/accessor' as leaf node.
    2019-02-21 14:10:44.079 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/accessor' as leaf node.
    2019-02-21 14:10:44.252 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/id' recursively.
    2019-02-21 14:10:44.252 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/id' recursively.
    2019-02-21 14:10:44.353 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/id' as leaf node.
    2019-02-21 14:10:44.353 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/admin/id' as leaf node.
    2019-02-21 14:10:44.535 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/' recursively.
    2019-02-21 14:10:44.535 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/' recursively.
    2019-02-21 14:10:44.651 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test/read'
    2019-02-21 14:10:44.651 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test/read'
    2019-02-21 14:10:44.651 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/accessor' recursively.
    2019-02-21 14:10:44.651 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/accessor' recursively.
    2019-02-21 14:10:44.757 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/accessor' as leaf node.
    2019-02-21 14:10:44.757 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/accessor' as leaf node.
    2019-02-21 14:10:44.963 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/id' recursively.
    2019-02-21 14:10:44.963 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/id' recursively.
    2019-02-21 14:10:45.075 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/id' as leaf node.
    2019-02-21 14:10:45.075 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/read/id' as leaf node.
    2019-02-21 14:10:45.255 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/' recursively.
    2019-02-21 14:10:45.255 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/' recursively.
    2019-02-21 14:10:45.372 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test/write'
    2019-02-21 14:10:45.372 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing tree rooted at 'secret/delegated/dm/square/test/write'
    2019-02-21 14:10:45.372 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/accessor' recursively.
    2019-02-21 14:10:45.372 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/accessor' recursively.
    2019-02-21 14:10:45.480 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/accessor' as leaf node.
    2019-02-21 14:10:45.480 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/accessor' as leaf node.
    2019-02-21 14:10:45.657 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/id' recursively.
    2019-02-21 14:10:45.657 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/id' recursively.
    2019-02-21 14:10:45.793 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/id' as leaf node.
    2019-02-21 14:10:45.793 MST(-0700) [DEBUG] lsstvaultutils.recursivedeleter | Removing 'secret/delegated/dm/square/test/write/id' as leaf node.
    2019-02-21 14:10:45.990 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting policy for 'delegated/dm/square/test/admin'.
    2019-02-21 14:10:46.212 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting policy for 'delegated/dm/square/test/read'.
    2019-02-21 14:10:46.439 MST(-0700) [DEBUG] lsstvaultutils.tokenadmin | Deleting policy for 'delegated/dm/square/test/write'.

And now the system is back in the state we started from.

### Verifying token deletion

We can try an operation to see that the tokens have been revoked.  Set
up the (revoked) read token: `export
VAULT_TOKEN="s.6JQ0zz6w6atlD1kcgisru3tY"`.  Then try the same read we
previously ran again:

    (vaultutils) adam@ixitxachitl:/tmp$ vault read secret/dm/square/test/group1/baz
    Error reading secret/dm/square/test/group1/baz: Error making API request.
    
    URL: GET https://35.184.246.111/v1/secret/dm/square/test/group1/baz
    Code: 403. Errors:
    
    * permission denied

