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

### Tokens

Token IDs and accessors are stored under 
`secret/delegated/:subsystem:/:team:/:category:/:instance:/:role:/:type:`
where `role` is one of `read`, `write`, or `admin` and `type` is one of
`id` or `accessor`.  These secrets are only accessible to an
administrative user (such as the one that created the token trio in the
first place).

There are three tokens for each path, comprising the "token trio".
These are `read`, `write`, and `admin`.

At the moment, `admin` is not particularly useful.  It will eventually
be used for delegation of further token-granting privileges within a
secret tree, but that will require a fairly sophisticated use of Vault
entities, roles, and templated policies, and is regarded as a possible
future enhancement rather than a near-term priority.

It is our intention that a runtime system have access to the `read`
token to be able to read (but not update) secrets, and that the
administrators of such a system have access to the `write` token to
create and update secrets.  We have provided a tool that allows easy
copying of Kubernetes secrets to and from Vault.

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

