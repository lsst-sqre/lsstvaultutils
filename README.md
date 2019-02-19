# LSST Vault Utilities

This package is a set of Vault utilities useful for the LSST use case.

## Classes

The package name is `lsstvaultutils`.  Its functional classes are:

1. `SecretCopier` -- this copies secrets between the current Kubernetes
   context and a Vault instance.
   
2. `TokenAdmin` -- this highly LSST-specific class allows you to specify a
   path under the Vault secret store, and it will generate three tokens
   (read, write, and admin) for manipulating secrets under the path.  It
   stores those under secret/delegated, so that an admin can find (and,
   if need be, revoke) them later.  It also manages revoking those
   tokens and removing them from the secret/delegated path.
   
3. `RecursiveDeleter` -- this adds a recursive deletion feature to Vault
   for removing a whole secret tree at a time.
   
There is also a TimeFormatter class that exists only to add milliseconds
to the debugging logs.

## Programs

The major functionality of these classes is also exposed as standalone
programs.

1. `copyk2v` -- copy a Kubernetes secret to a Vault secret path.

2. `copyv2k` -- copy a set of Vault secrets at a specified path to a
   Kubernetes secret.
   
3. `tokenadmin` -- Creating or revoke token sets for a given Vault secret
   path.
   
4. `vaultrmrf` -- Remove a Vault secret path and everything underneath it.
