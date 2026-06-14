# danmwallace.podman.librechat

Deploys [LibreChat](https://www.librechat.ai/) and its four supporting services as
rootful Podman Quadlet (systemd) units on Fedora Server. The role manages the full
stack: a pgvector/Postgres database (`librechat-vectordb`) for RAG embeddings, a
Meilisearch instance (`librechat-meilisearch`) for conversation search, the RAG API
service (`librechat-rag-api`), and the main LibreChat API (`librechat-api`). All four
containers share a dedicated Podman network (`librechat.network`) so they can reach
each other by container name.

The LibreChat API container also joins a second network (`proxy_network`) and carries
Traefik labels, making it immediately reachable over HTTPS via an external Traefik
reverse proxy with a Cloudflare certificate resolver. MongoDB is not deployed by this
role; an external MongoDB URI must be supplied. An optional bind mount lets the host's
Obsidian vault be indexed by the RAG pipeline.

## Requirements

- Fedora Server (any current release) with Podman and systemd-container support.
- A running Traefik reverse proxy on the `proxy_network` Podman network.
- An external MongoDB instance reachable from the host (URI supplied via vault).
- Ansible ≥ 2.16.
- Collection dependencies: `containers.podman ≥ 1.11.0`, `ansible.posix ≥ 1.5.0`,
  `community.general ≥ 8.0.0`.

## Role Variables

| Variable | Type | Required | Default | Description |
|---|---|---|---|---|
| `librechat_hostname` | str | yes | — | Hostname for the LibreChat web interface (e.g. `chat.example.com`). Used in Traefik router rule. |
| `librechat_data_dir` | str | no | `/opt/podman/librechat` | Host base directory for all LibreChat data volumes. |
| `librechat_port` | int | no | `3080` | Port the LibreChat API container listens on; used in the Traefik load balancer label. |
| `librechat_api_image` | str | no | `ghcr.io/danny-avila/librechat:latest` | Container image for the LibreChat API service. |
| `librechat_mongo_uri` | str | yes | — | MongoDB connection URI for LibreChat. **Supply from vault.** |
| `librechat_jwt_secret` | str | yes | — | Secret key for JWT session token signing. Generate with `openssl rand -hex 32`. **Supply from vault.** |
| `librechat_jwt_refresh_secret` | str | yes | — | Secret key for JWT refresh token signing (must differ from `librechat_jwt_secret`). Generate with `openssl rand -hex 32`. **Supply from vault.** |
| `librechat_creds_key` | str | yes | — | 32-byte hex key for credential encryption at rest. Generate with `openssl rand -hex 32`. **Supply from vault.** |
| `librechat_creds_iv` | str | yes | — | 16-byte hex IV for credential encryption at rest. Generate with `openssl rand -hex 16`. **Supply from vault.** |
| `librechat_meilisearch_image` | str | no | `docker.io/getmeili/meilisearch:v1.7.3` | Container image for the Meilisearch service. |
| `librechat_meili_master_key` | str | yes | — | Master key for Meilisearch authentication. **Supply from vault.** |
| `librechat_vectordb_image` | str | no | `docker.io/ankane/pgvector:latest` | Container image for the pgvector/Postgres service. |
| `librechat_vectordb_postgres_db` | str | no | `mydatabase` | Postgres database name for the vectordb service. |
| `librechat_vectordb_postgres_user` | str | no | `myuser` | Postgres username for the vectordb service. |
| `librechat_vectordb_postgres_password` | str | yes | — | Postgres password for the vectordb service. **Supply from vault.** |
| `librechat_ragapi_image` | str | no | `ghcr.io/danny-avila/librechat-rag-api-dev-lite:latest` | Container image for the RAG API service. |
| `librechat_obsidian_mount_enabled` | bool | no | `false` | When `true`, bind-mounts the Obsidian vault path into the api container. |
| `librechat_obsidian_mount_path` | str | no | `""` | Absolute host path to the Obsidian vault. Only used when `librechat_obsidian_mount_enabled` is `true`. |

## Dependencies

None (no role-level Galaxy dependencies). Collection-level dependencies are declared
in `galaxy.yml`:

- `containers.podman >= 1.11.0`
- `ansible.posix >= 1.5.0`
- `community.general >= 8.0.0`

## Example Playbook

```yaml
- name: Deploy LibreChat
  hosts: ai_servers
  become: true
  vars_files:
    - vault.yml
  roles:
    - role: danmwallace.podman.librechat
      vars:
        librechat_hostname: chat.example.com
        librechat_data_dir: /opt/podman/librechat
        librechat_mongo_uri: "{{ vault_librechat_mongo_uri }}"
        librechat_jwt_secret: "{{ vault_librechat_jwt_secret }}"
        librechat_jwt_refresh_secret: "{{ vault_librechat_jwt_refresh_secret }}"
        librechat_creds_key: "{{ vault_librechat_creds_key }}"
        librechat_creds_iv: "{{ vault_librechat_creds_iv }}"
        librechat_meili_master_key: "{{ vault_librechat_meili_master_key }}"
        librechat_vectordb_postgres_password: "{{ vault_librechat_vectordb_postgres_password }}"
        # Optional: expose the Obsidian vault to the RAG pipeline
        librechat_obsidian_mount_enabled: true
        librechat_obsidian_mount_path: /home/dan/Documents/Obsidian
```

## What the Role Does

1. **Assert required secrets** — fails fast if any of `librechat_jwt_secret`,
   `librechat_jwt_refresh_secret`, `librechat_creds_key`, or `librechat_creds_iv`
   are empty strings.
2. **Create base data directory** (`librechat_data_dir`, mode `0755`, owned by root).
3. **Create container-writable subdirectories** — `images/` and `logs/` are owned
   by UID/GID 1000 (the in-container user).
4. **Create sidecar data directories** — `meilisearch/` and `vectordb/`, owned by
   root.
5. **Render `librechat.yaml`** — the LibreChat application config file (from
   `librechat.yaml.j2`) is written to `librechat_data_dir`; triggers restart on
   change.
6. **Deploy `librechat.network` Quadlet unit** — creates the shared Podman network
   definition at `/etc/containers/systemd/librechat.network`.
7. **Render `librechat-vectordb.container`** — pgvector Quadlet unit with Postgres
   environment and data volume; triggers restart on change.
8. **Render `librechat-meilisearch.container`** — Meilisearch Quadlet unit with
   master key and data volume; triggers restart on change.
9. **Render `librechat-rag-api.container`** — RAG API Quadlet unit wired to
   vectordb and Meilisearch; triggers restart on change.
10. **Render `librechat-api.container`** — main LibreChat API Quadlet unit, joined
    to both `librechat.network` and `proxy_network`, carrying Traefik labels;
    triggers restart on change.
11. **Enable and start `librechat-vectordb.service`** — triggers `daemon_reload` to
    activate any new Quadlet unit files, then starts the service.
12. **Enable and start `librechat-meilisearch.service`**.
13. **Enable and start `librechat-rag-api.service`**.
14. **Enable and start `librechat-api.service`**.

Any change to a Quadlet unit file or to `librechat.yaml` notifies the `Restart
librechat` handler, which restarts all four services in order (vectordb →
meilisearch → rag-api → api).

## Notes

- The `librechat-api` container starts only after both `librechat-meilisearch` and
  `librechat-rag-api` are up (`After=` in the unit file). The RAG API itself waits
  on `librechat-vectordb`.
- Traefik integration relies on `proxy_network` existing before the role runs and on
  the Traefik container watching that network for label-based routing. The certificate
  resolver is named `cloudflare`.
- Steps 11–14 are tagged `molecule-notest` and are skipped during Molecule runs
  because Quadlet unit files are not loaded inside the test container. The handler
  shares the same tag for the same reason.
- If `librechat_obsidian_mount_enabled` is `true`, the vault path is mounted at the
  same absolute path inside the container (`host_path:host_path`), so paths embedded
  in documents resolve correctly.

## License

MIT
