# danmwallace.podman.librechat

Deploys [LibreChat](https://www.librechat.ai/) and its three sidecars as rootful Podman
Quadlet (systemd) units on Fedora Server: a pgvector/Postgres database
(`librechat-vectordb`) for RAG embeddings, a [Meilisearch](https://www.meilisearch.com/)
instance (`librechat-meilisearch`) for conversation search, the RAG API
(`librechat-rag-api`), and the LibreChat API itself (`librechat-api`). Unit files land in
`/etc/containers/systemd/`; persistent data lives under `librechat_data_dir`
(`/opt/podman/librechat` by default) in `meilisearch/`, `vectordb/`, `images/`, and
`logs/`. All four containers share a dedicated `librechat.network` so they reach each
other by container name.

Runtime configuration is split across two rendered files: `librechat.yaml` (the
LibreChat app config, currently only custom Hermes endpoints) and `librechat.env`, a
full LibreChat `.env` rendered from several hundred `librechat_*` variables and passed
to the API container via `EnvironmentFile=`. The API container additionally joins
`proxy_network` and carries Traefik labels (`websecure` entrypoint, `cloudflare` cert
resolver, backend port `librechat_port`), so it is reachable over HTTPS as soon as an
external Traefik is watching that network. MongoDB is **not** deployed by this role; an
external `librechat_mongo_uri` must be supplied. An optional bind mount exposes the
host's Obsidian vault to the RAG pipeline.

## Requirements

- Ansible >= 2.16
- Controller collections: `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`,
  `community.general >= 8.0.0` (declared in the collection's `galaxy.yml`)
- Target host: Fedora with Podman and Quadlet support (`/etc/containers/systemd/`),
  systemd, and `become` privileges
- An existing `proxy_network` Podman network with a Traefik instance watching it
  (typically from `danmwallace.podman.traefik`)
- An external MongoDB reachable from the host

## Role Variables

Only the variables declared in `meta/argument_specs.yml` are listed here.
`defaults/main.yml` additionally exposes several hundred `librechat_*` pass-through
variables (one per LibreChat `.env` key: providers, OAuth/SAML/LDAP, rate limits, Redis,
S3, MCP, ...) that render into `librechat.env`; consult that file for the full set. Keys
left as `""` render empty and fall back to LibreChat's own defaults.

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `librechat_hostname` | str | yes | — | Hostname for the LibreChat web interface (e.g. chat.example.com). |
| `librechat_data_dir` | str | no | `/opt/podman/librechat` | Host base directory for all LibreChat data volumes. |
| `librechat_port` | int | no | `3080` | Port the LibreChat API container listens on (used for Traefik load balancer config). |
| `librechat_api_image` | str | no | `ghcr.io/danny-avila/librechat:v0.8.7` | Container image for the LibreChat API service. |
| `librechat_mongo_uri` | str | yes | — | MongoDB connection URI for LibreChat. **Supply from vault.** |
| `librechat_meilisearch_image` | str | no | `docker.io/getmeili/meilisearch:v1.53.2` | Container image for the Meilisearch service. |
| `librechat_meilisearch_upgrade_db` | bool | no | `true` | When true, sets MEILI_UPGRADE_DB=true on the Meilisearch container so it migrates the persisted database in place on first start after an image bump (--upgrade-db, stable since Meilisearch v1.51). |
| `librechat_meili_master_key` | str | yes | — | Master key for Meilisearch authentication. **Supply from vault.** |
| `librechat_meili_host` | str | no | `http://librechat-meilisearch:7700` | URL for the Meilisearch service as seen from the LibreChat API container. Defaults to the Podman container name on the librechat network. |
| `librechat_vectordb_image` | str | no | `docker.io/pgvector/pgvector:0.8.6-pg17` | Container image for the vectordb (pgvector/Postgres) service. |
| `librechat_vectordb_postgres_db` | str | no | `mydatabase` | Postgres database name for the vectordb service. |
| `librechat_vectordb_postgres_user` | str | no | `myuser` | Postgres username for the vectordb service. |
| `librechat_vectordb_postgres_password` | str | yes | — | Postgres password for the vectordb service. **Supply from vault.** |
| `librechat_jwt_secret` | str | yes | — | Secret key for JWT session token signing. Generate with `openssl rand -hex 32`. **Supply from vault.** |
| `librechat_jwt_refresh_secret` | str | yes | — | Secret key for JWT refresh token signing (must differ from librechat_jwt_secret). Generate with `openssl rand -hex 32`. **Supply from vault.** |
| `librechat_creds_key` | str | yes | — | 32-byte hex key for credential encryption at rest. Generate with `openssl rand -hex 32`. **Supply from vault.** |
| `librechat_creds_iv` | str | yes | — | 16-byte hex IV for credential encryption at rest. Generate with `openssl rand -hex 16`. **Supply from vault.** |
| `librechat_ragapi_image` | str | no | `ghcr.io/danny-avila/librechat-rag-api-dev-lite:v0.9.0` | Container image for the LibreChat RAG API service. |
| `librechat_rag_port` | int | no | `8000` | Port the RAG API service listens on. Used to set RAG_PORT in the env file. |
| `librechat_rag_api_url` | str | no | `http://librechat-rag-api:8000` | URL for the RAG API service as seen from the LibreChat API container. Defaults to the Podman container name on the librechat network. |
| `librechat_obsidian_mount_enabled` | bool | no | `false` | When true, bind-mounts the Obsidian vault path into the api container. |
| `librechat_obsidian_mount_path` | str | no | `""` | Absolute path to the Obsidian vault on the host. Only used when librechat_obsidian_mount_enabled is true. |
| `librechat_allow_social_login` | bool | no | `false` | Enable OAuth/social login providers (Google, OpenID, etc.). |
| `librechat_allow_social_registration` | bool | no | `false` | Allow new user registration via social login providers. |
| `librechat_allow_email_login` | bool | no | `false` | Enable local email/password login. |
| `librechat_allow_registration` | bool | no | `false` | Allow new user self-registration via email/password. |
| `librechat_anthropic_api_key` | str | no | `""` | Anthropic API key. **Supply from vault.** |
| `librechat_anthropic_models` | str | no | `""` | Comma-separated list of Anthropic models to offer. |
| `librechat_endpoints` | str | no | `""` | Comma-separated list of enabled endpoints. E.g. "azureOpenAI,anthropic,agents,azureAssistants". |
| `librechat_app_title` | str | no | `LibreChat` | Application title shown in the browser tab and header. |
| `librechat_openid_client_id` | str | no | `""` | OpenID Connect / Entra ID application (client) ID. |
| `librechat_openid_client_secret` | str | no | `""` | OpenID Connect / Entra ID client secret. **Supply from vault.** |
| `librechat_openid_issuer` | str | no | `""` | OpenID Connect issuer URL (e.g. https://login.microsoftonline.com/<tenant>/v2.0/). |
| `librechat_openid_session_secret` | str | no | `""` | Session secret for the OpenID Connect strategy. **Supply from vault.** |
| `librechat_openid_scope` | str | no | `openid profile email offline_access` | Space-separated OpenID Connect scopes to request. |
| `librechat_openid_button_label` | str | no | `""` | Label shown on the OpenID Connect login button (e.g. "Sign-in with Microsoft"). |
| `librechat_openid_image_url` | str | no | `""` | URL of the icon shown on the OpenID Connect login button. |
| `librechat_openid_callback_url` | str | no | `/oauth/openid/callback` | Callback path for the OpenID Connect provider redirect. |
| `librechat_openid_required_role` | str | no | `""` | Group/role ID that a user must have in the ID token to be granted access. Leave blank to allow all authenticated users. |
| `librechat_openid_required_role_token_kind` | str | no | `""` | Token kind to inspect for the required role ("id" or "access"). |
| `librechat_openid_required_role_parameter_path` | str | no | `""` | JSON path in the token where group/role IDs are found (e.g. "groups"). |
| `librechat_google_client_id` | str | no | `""` | Google OAuth 2.0 client ID. |
| `librechat_google_client_secret` | str | no | `""` | Google OAuth 2.0 client secret. **Supply from vault.** |
| `librechat_google_callback_url` | str | no | `/oauth/google/callback` | Callback path for the Google OAuth redirect. |
| `librechat_hermes_personal_enabled` | bool | no | `false` | When true, registers Hermes Personal as a custom endpoint in librechat.yaml. |
| `librechat_hermes_personal_url` | str | no | `""` | Base URL of the Hermes Personal gateway API (e.g. https://hermes-api-ai01.wallace.boston). |
| `librechat_hermes_personal_api_key` | str | no | `""` | Bearer token for the Hermes Personal API. Must match hermes_api_server_key on ai01. **Supply from vault.** |
| `librechat_hermes_infra_enabled` | bool | no | `false` | When true, registers Hermes Infra as a custom endpoint in librechat.yaml. |
| `librechat_hermes_infra_url` | str | no | `""` | Base URL of the Hermes Infra gateway API (e.g. https://hermes-api-ai-master.wallace.boston). |
| `librechat_hermes_infra_api_key` | str | no | `""` | Bearer token for the Hermes Infra API. Must match hermes_api_server_key on ai-master. **Supply from vault.** |

## Dependencies

None declared in `meta/main.yml`. Practically, the host needs Podman, the
`proxy_network` Quadlet network, and a running Traefik that routes by container label
(see `danmwallace.podman.traefik`).

## Example Playbook

```yaml
- name: Deploy LibreChat
  hosts: ai_servers
  become: true
  roles:
    - role: danmwallace.podman.librechat
      vars:
        librechat_hostname: chat.example.com
        librechat_mongo_uri: "{{ vault_librechat_mongo_uri }}"
        librechat_jwt_secret: "{{ vault_librechat_jwt_secret }}"
        librechat_jwt_refresh_secret: "{{ vault_librechat_jwt_refresh_secret }}"
        librechat_creds_key: "{{ vault_librechat_creds_key }}"
        librechat_creds_iv: "{{ vault_librechat_creds_iv }}"
        librechat_meili_master_key: "{{ vault_librechat_meili_master_key }}"
        librechat_vectordb_postgres_password: "{{ vault_librechat_vectordb_postgres_password }}"
        librechat_endpoints: "anthropic,agents"
        librechat_anthropic_api_key: "{{ vault_librechat_anthropic_api_key }}"
        # Optional: expose the Obsidian vault to the RAG pipeline
        librechat_obsidian_mount_enabled: true
        librechat_obsidian_mount_path: /home/dan/Documents/Obsidian
```

## What the Role Does

1. **Asserts required secrets** — fails fast if `librechat_jwt_secret`,
   `librechat_jwt_refresh_secret`, `librechat_creds_key`, or `librechat_creds_iv` is
   empty.
2. **Ensures the base data directory** `librechat_data_dir` exists (`0755`, root).
3. **Ensures container-writable directories** `images/` and `logs/` exist, owned by
   UID/GID 1000 (the in-container user).
4. **Ensures sidecar data directories** `meilisearch/` and `vectordb/` exist (root).
5. **Renders `librechat.yaml`** into `librechat_data_dir` (`0644`).
6. **Deploys the `librechat.network` Quadlet unit** to
   `/etc/containers/systemd/librechat.network`.
7. **Renders `librechat-vectordb.container`** (pgvector image, Postgres env, `vectordb/`
   volume).
8. **Renders `librechat-meilisearch.container`** (Meilisearch image, master key,
   `meilisearch/` volume, `MEILI_UPGRADE_DB` when `librechat_meilisearch_upgrade_db`).
9. **Renders `librechat-rag-api.container`** (wired to `librechat-vectordb`, `RAG_PORT`
   8000).
10. **Renders `librechat.env`** into `librechat_data_dir` (`0640`, root; task runs with
    `no_log` because it contains every secret).
11. **Renders `librechat-api.container`** (both networks, Traefik labels, config/images/
    logs volumes, optional Obsidian mount, `EnvironmentFile=librechat.env`).
12. **Enables and starts `librechat-vectordb.service`** with a `daemon_reload` so new
    Quadlet units are generated.
13. **Enables and starts `librechat-meilisearch.service`**.
14. **Enables and starts `librechat-rag-api.service`**.
15. **Enables and starts `librechat-api.service`**.

Any change to a Quadlet unit, `librechat.yaml`, or `librechat.env` notifies the
`Restart librechat` handler, which restarts all four services in order (vectordb ->
meilisearch -> rag-api -> api) with a `daemon_reload`.

## Upgrading Postgres (vectordb) and Meilisearch

Both sidecars keep their state under `librechat_data_dir` (`vectordb/` and
`meilisearch/`), and that state survives image bumps. The role only re-renders the unit
and restarts the service; **it does not migrate data**. Bumping a pin over existing data
is therefore an operator task, and both services fail to start (rather than corrupt data)
when the on-disk format does not match the new image.

**Postgres / pgvector.** The pin encodes the Postgres major (`0.8.6-pg17`). Postgres
cannot open a data directory from a different major, so before changing the `-pgNN`
suffix of `librechat_vectordb_image`, `pg_dumpall` from the *running* old container,
move `vectordb/` aside, deploy the new image onto an empty `vectordb/`, and restore.
Check `vectordb/PG_VERSION` against the pin if `librechat-vectordb.service` fails on
`database files are incompatible with server`. Bumping the pgvector version within the
same Postgres major (e.g. `0.8.5-pg17` -> `0.8.6-pg17`) needs no migration.

**Meilisearch.** A Meilisearch database is only readable by the version that wrote it.
With `librechat_meilisearch_upgrade_db: true` (the default) the container starts with
`MEILI_UPGRADE_DB=true` (`--upgrade-db`, stable since v1.51; formerly
`--experimental-dumpless-upgrade`) and upgrades `meilisearch/` in place on first start
after a bump. This works only when the *source* database was created by v1.12 or newer;
older databases make the new version fail with `Database version X.Y.Z is too old to be
upgraded via --upgrade-db`. In that case run the original image once more, create a
dump via `POST /dumps`, start the new image on an empty `meilisearch/` with
`--import-dump`, then return to the role-managed unit. Multi-minor jumps within the
supported range (e.g. v1.48 -> v1.53) are fine; v1.50 fixed a migration failure from
<= v1.48 on indexes containing empty synonyms. Downgrades are not supported, so snapshot
`meilisearch/` before bumping if you want a rollback path.

## Notes

- **Image pins.** All four images are pinned to release tags; bump them deliberately and
  read the upgrade section above first.
- **Start order.** `librechat-api` starts after `librechat-meilisearch` and
  `librechat-rag-api` (`After=`); `librechat-rag-api` waits on `librechat-vectordb`.
- **Traefik.** Routing relies on `proxy_network` existing before the role runs and the
  labels use `traefik.docker.network=systemd-proxy_network` (Quadlet's generated network
  name). The certificate resolver is named `cloudflare`.
- **Hermes endpoints.** When `librechat_hermes_personal_enabled` or
  `librechat_hermes_infra_enabled` is true, `librechat.yaml.j2` also references
  `librechat_hermes_personal_model` / `librechat_hermes_infra_model`, which have no
  default — supply them alongside the URL and API key or the template fails to render.
- **Obsidian mount.** The vault is mounted at the same absolute path inside the
  container (`host_path:host_path:z`) so document paths resolve identically.
- **Molecule.** The service start tasks and the restart handlers are tagged
  `molecule-notest` because Quadlet units are not generated inside the test container;
  the scenario verifies rendered files and permissions only.

## License

MIT
