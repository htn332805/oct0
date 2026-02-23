# Security Considerations (Current Implementation)

- **Dynamic imports**: step node modules are loaded from disk; libraries must be trusted.
- **Shell execution**: avoid `os.system` with concatenated strings; prefer `subprocess.run` with args.
- **Parameter file integrity**: parameter JSON controls runtime flow; validate schema before use.
- **Locking behavior**: handle lock timeouts with explicit errors to avoid silent failures.
- **Secrets**: do not hardcode credentials in layout scripts; use environment variables or secret stores.
