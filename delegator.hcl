# Admin delegated tokens
    path "auth/token" {
      capabilities = ["read"]
    }

    path "auth/token/*" {
      capabilities = ["create", "read", "update", "delete", "list", "sudo"]
    }

    # List existing policies for delegated tokens
    path "sys/policy/delegated"
    {
      capabilities = ["read","list"]
    }

    path "sys/policies/acl/delegated"
    {
      capabilities = ["read", "list"]
    }

    # Create and manage ACL policies
    path "sys/policy/delegated/*"
    {
      capabilities = ["create", "read", "update", "delete", "list"]
    }

    # Create and manage ACL policies
    path "sys/policies/acl/delegated/*"
    {
      capabilities = ["create", "read", "update", "delete", "list"]
    }

    # List, create, update, and delete key/value secrets mapping delegated IDs
    path "secret/delegated/*"
    {
      capabilities = ["create", "read", "update", "delete", "list"]
    }

    # List, create, update, and delete key/value secrets mapping delegated IDs
    path "secret/data/delegated/*"
    {
      capabilities = ["create", "read", "update", "delete", "list"]
    }

    # Delete key/value secrets mapping delegated IDs
    path "secret/delete/delegated/*"
    {
      capabilities = ["update"]
    }
    # Undelete key/value secrets mapping delegated IDs
    path "secret/undelete/delegated/*"
    {
      capabilities = ["update"]
    }
    # Destroy versions
    path "secret/destroy/delegated/*"
    {
      capabilities = ["update"]
    }

    # List, create, update, and delete key/value secrets mapping delegated IDs
    path "secret/metadata/delegated/*"
    {
      capabilities = ["create", "read", "update", "delete", "list"]
    }
