# danmwallace.podman.dashy

Deploys [Dashy](https://dashy.to/), a self-hosted homelab dashboard, as a rootful Podman Quadlet on Fedora. The dashboard config is rendered from an Ansible Jinja2 template to `{{ dashy_data_dir }}/config.yml` and mounted read-only into the container at `/app/user-data/conf.yml`. The container runs `docker.io/lissy93/dashy:{{ dashy_version }}` (default `4.6.0`), listens on port 8080, and joins the existing `proxy_network` Quadlet network. Traefik terminates TLS via the Cloudflare cert resolver and routes `dashy_hostname` to the container; no ports are published on the host.

The rendered config groups the homelab into four sections — **Homelab Tools** (IT Tools, Semaphore), **AI & Automation** (LibreChat, n8n, Hermes Gateway and Hermes Dashboard on ai01 and ai-master), **Public Sites** (Portfolio, WSB Pulse), and **Infrastructure** (Traefik dashboards on util01/ai01/ai-master, Arcane on util01 and ai01, Uptime Kuma). Every item has `statusCheck: true` except the Traefik dashboards, which are internal and unreachable from the browser. The Hermes Gateway and Hermes Dashboard items override the probe target with `statusCheckUrl` (`/health` and `/auth/password-login` respectively) because their root URLs redirect.

## Requirements

- Ansible >= 2.16
- Collection: `containers.podman >= 1.11.0` (declared in the collection's `galaxy.yml`)
- Target host: Fedora with Podman installed and the `proxy_network` Quadlet network already up (the `danmwallace.podman.traefik` role creates it)
- A Cloudflare TLS cert resolver configured in Traefik (for HTTPS)

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `dashy_hostname` | str | yes | — | Hostname for the Dashy web interface (e.g. `home.wallace.boston`). |
| `dashy_data_dir` | str | no | `/opt/podman/dashy` | Host directory for the rendered Dashy config file. |
| `dashy_version` | str | no | `4.6.0` | Image tag for the Dashy container image. |
| `dashy_image` | str | no | `docker.io/lissy93/dashy:{{ dashy_version }}` | Fully-qualified container image for Dashy. Override to use a mirror or digest. |
| `dashy_it_tools_hostname` | str | yes | — | Hostname for IT Tools (on util01). |
| `dashy_semaphore_hostname` | str | yes | — | Hostname for Semaphore (on util01). |
| `dashy_arcane_hostname` | str | yes | — | Hostname for Arcane (on util01). |
| `dashy_arcane_ai01_hostname` | str | yes | — | Hostname for Arcane (on ai01). |
| `dashy_uptime_kuma_hostname` | str | yes | — | Hostname for Uptime Kuma (on util01). |
| `dashy_traefik_util01_hostname` | str | yes | — | Hostname for the Traefik dashboard on util01. |
| `dashy_librechat_hostname` | str | yes | — | Hostname for LibreChat (on ai01). |
| `dashy_n8n_hostname` | str | yes | — | Hostname for n8n (on ai01). |
| `dashy_hermes_gateway_ai01_hostname` | str | yes | — | Hostname for Hermes Gateway on ai01. |
| `dashy_hermes_gateway_aimaster_hostname` | str | yes | — | Hostname for Hermes Gateway on ai-master. |
| `dashy_hermes_dash_ai01_hostname` | str | yes | — | Hostname for the Hermes Dashboard on ai01. |
| `dashy_hermes_dash_aimaster_hostname` | str | yes | — | Hostname for the Hermes Dashboard on ai-master. |
| `dashy_portfolio_hostname` | str | yes | — | Hostname for the portfolio site (on web01). |
| `dashy_wsb_hostname` | str | yes | — | Hostname for WSB Pulse (on web01). |
| `dashy_traefik_ai01_hostname` | str | yes | — | Hostname for the Traefik dashboard on ai01. |
| `dashy_traefik_aimaster_hostname` | str | yes | — | Hostname for the Traefik dashboard on ai-master. |

All required variables are hostnames; none need vault storage.

## Dependencies

None declared in `meta/main.yml`. In practice the target host needs:

- The `proxy_network` Podman network (created by `danmwallace.podman.traefik`)
- The service hostnames above to be resolvable from the browser, since status checks run client-side

## Example Playbook

```yaml
- hosts: util
  become: true
  roles:
    - role: danmwallace.podman.dashy
      vars:
        dashy_hostname: home.wallace.boston
        dashy_it_tools_hostname: tools.wallace.boston
        dashy_semaphore_hostname: semaphore.wallace.boston
        dashy_arcane_hostname: arcane.wallace.boston
        dashy_arcane_ai01_hostname: arcane.ai01.wallace.boston
        dashy_uptime_kuma_hostname: uptime.wallace.boston
        dashy_traefik_util01_hostname: trfk.util01.wallace.boston
        dashy_librechat_hostname: ai.wallace.boston
        dashy_n8n_hostname: agents.wallace.boston
        dashy_hermes_gateway_ai01_hostname: hermes-gateway-ai01.wallace.boston
        dashy_hermes_gateway_aimaster_hostname: hermes-gateway-ai-master.wallace.boston
        dashy_hermes_dash_ai01_hostname: hermes-ai01.wallace.boston
        dashy_hermes_dash_aimaster_hostname: hermes-ai-master.wallace.boston
        dashy_portfolio_hostname: danwallace.engineer
        dashy_wsb_hostname: wsb.wallace.boston
        dashy_traefik_ai01_hostname: trfk.ai01.wallace.boston
        dashy_traefik_aimaster_hostname: trfk.ai-master.wallace.boston
```

## What the Role Does

1. Creates `{{ dashy_data_dir }}` (default `/opt/podman/dashy`) with mode `0755`.
2. Renders `dashy-config.yml.j2` to `{{ dashy_data_dir }}/config.yml` (mode `0644`). Changes trigger the `Restart dashy` handler.
3. Renders `dashy.container.j2` to `/etc/containers/systemd/dashy.container` (mode `0644`). Changes also trigger the `Restart dashy` handler.
4. Enables and starts `dashy.service` via systemd with `daemon_reload: true`.

The `Restart dashy` handler runs `systemctl restart dashy.service` with `daemon_reload: true` when either the config or the Quadlet unit changes.

## Notes

**Config schema since Dashy 4.5.0.** Upstream now derives each section's ID from a slug of its `name`, so every section must have a `name` and it must be unique within the page — the JSON schema rejects a config that breaks this. The bundled template satisfies this (four distinct section names). Per-user visibility keys also moved under `displayData` (`showForGroups`, `showForRoles`, `hideForGroups`, `hideForRoles`); the old keys still work in 4.x but are slated for removal in the next major. If you extend `dashy-config.yml.j2`, keep section names unique and use the new `displayData` keys. Dashy also stopped serving dot-prefixed files from `user-data` and parses `conf.yml` as strict YAML 1.2, neither of which affects the rendered config.

**Read-only config mount.** The rendered config is mounted with `:ro,Z`, so edits made in Dashy's built-in UI editor cannot be written back — change the template and re-run the role instead.

**No authentication.** The role configures no auth in Dashy. The instance is intended for internal-network access; do not expose `dashy_hostname` to the public internet without an auth layer in front of it.

**Traefik dashboard items** (`dashy_traefik_*_hostname`) are rendered with `statusCheck: false` because those URLs are on internal subdomains unreachable from the browser at status-check time.

## License

MIT
