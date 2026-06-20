# danmwallace.podman.dashy

Deploys [Dashy](https://dashy.to/), a self-hosted homelab dashboard, as a Podman Quadlet on Fedora. The dashboard config is rendered from an Ansible Jinja2 template and mounted read-only into the container at `/app/user-data/conf.yml`. Traefik handles TLS termination via the Cloudflare cert resolver; the container listens on port 8080 and joins the existing `proxy_network` Quadlet network.

The rendered config groups all homelab services into four sections — **Homelab Tools** (IT Tools, Semaphore, Arcane), **AI & Automation** (LibreChat, n8n, Hermes Gateway on ai01 and ai-master), **Public Sites** (Portfolio, WSB Pulse), and **Infrastructure** (Traefik dashboards). All service items run with `statusCheck: true` except the Traefik dashboards, which are internal and unreachable from the browser.

## Requirements

- Ansible >= 2.16
- Collection: `containers.podman >= 1.11.0`
- Target host: Fedora with Podman installed and the `proxy_network` Quadlet network already up (the `danmwallace.podman.traefik` role creates it)
- A Cloudflare TLS cert resolver configured in Traefik (for HTTPS)

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `dashy_hostname` | str | yes | — | Public hostname for the Dashy web interface (e.g. `home.wallace.boston`). |
| `dashy_data_dir` | str | no | `/opt/podman/dashy` | Host directory where the rendered config file is stored. |
| `dashy_image` | str | no | `docker.io/lissy93/dashy:latest` | Fully-qualified container image for Dashy. |
| `dashy_it_tools_hostname` | str | yes | — | Hostname for IT Tools (on util01). |
| `dashy_semaphore_hostname` | str | yes | — | Hostname for Semaphore (on util01). |
| `dashy_arcane_hostname` | str | yes | — | Hostname for Arcane secrets manager (on util01). |
| `dashy_traefik_util01_hostname` | str | yes | — | Hostname for the Traefik dashboard on util01. |
| `dashy_librechat_hostname` | str | yes | — | Hostname for LibreChat (on ai01). |
| `dashy_n8n_hostname` | str | yes | — | Hostname for n8n (on ai01). |
| `dashy_hermes_gateway_ai01_hostname` | str | yes | — | Hostname for Hermes Gateway on ai01. |
| `dashy_hermes_gateway_aimaster_hostname` | str | yes | — | Hostname for Hermes Gateway on ai-master. |
| `dashy_portfolio_hostname` | str | yes | — | Hostname for the portfolio site (on web01). |
| `dashy_wsb_hostname` | str | yes | — | Hostname for WSB Pulse (on web01). |
| `dashy_traefik_ai01_hostname` | str | yes | — | Hostname for the Traefik dashboard on ai01. |
| `dashy_traefik_aimaster_hostname` | str | yes | — | Hostname for the Traefik dashboard on ai-master. |

All variables are hostnames; none require vault storage.

## Dependencies

None declared in `meta/main.yml`. In practice the target host needs:
- The `proxy_network` Podman network (created by `danmwallace.podman.traefik`)
- The other service hostnames passed via variables above to be resolvable from the browser

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
        dashy_traefik_util01_hostname: trfk.util01.wallace.boston
        dashy_librechat_hostname: ai.wallace.boston
        dashy_n8n_hostname: agents.wallace.boston
        dashy_hermes_gateway_ai01_hostname: hermes-gateway-ai01.wallace.boston
        dashy_hermes_gateway_aimaster_hostname: hermes-gateway-ai-master.wallace.boston
        dashy_portfolio_hostname: danwallace.engineer
        dashy_wsb_hostname: wsb.wallace.boston
        dashy_traefik_ai01_hostname: trfk.ai01.wallace.boston
        dashy_traefik_aimaster_hostname: trfk.ai-master.wallace.boston
```

## What the Role Does

1. Creates `{{ dashy_data_dir }}` (default `/opt/podman/dashy`) with mode `0755`.
2. Renders `dashy-config.yml.j2` to `{{ dashy_data_dir }}/config.yml` (mode `0644`). Changes here trigger the `Restart dashy` handler.
3. Renders `dashy.container.j2` to `/etc/containers/systemd/dashy.container` (mode `0644`). Changes here also trigger the `Restart dashy` handler.
4. Enables and starts `dashy.service` via systemd with `daemon_reload: true`.

The `Restart dashy` handler calls `systemctl restart dashy.service` with `daemon_reload: true` when either the config or the Quadlet unit changes.

## Notes

The rendered config file is mounted into the container as read-only with the SELinux relabelling flag (`{{ dashy_data_dir }}/config.yml:/app/user-data/conf.yml:ro,Z`). Dashy has no authentication — the instance is intended for internal network access only. Do not expose `dashy_hostname` to the public internet without adding an auth layer.

Traefik dashboard items (`dashy_traefik_*_hostname`) are rendered with `statusCheck: false` because those URLs are on internal subdomains unreachable from the browser at status-check time.

## License

MIT
