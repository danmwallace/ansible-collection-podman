# danmwallace.podman.traefik

Deploys [Traefik](https://traefik.io/) v3 as a Podman Quadlet container unit on Fedora Server.
Traefik runs as a systemd-managed container that listens on ports 443 (HTTPS) and 8081 (dashboard),
with port 80 redirected to HTTPS by the static configuration. TLS certificates are obtained
automatically via the Cloudflare DNS-01 ACME challenge and stored in
`{{ traefik_data_dir }}/letsencrypt/acme.json`.

The role creates a `proxy_network` Quadlet network unit at
`/etc/containers/systemd/proxy_network.network`. Other Podman services that need to be
proxied should attach to this network (`systemd-proxy_network`). Traefik discovers them via
the Podman socket mounted at `/run/podman/podman.sock`, exposed as the Docker-compatible
socket inside the container. Dynamic configuration (middlewares, TLS options) is rendered
from a file provider at `/etc/traefik/dynamic_conf.yml` with live-reload enabled.

## Requirements

- Ansible >= 2.16
- Podman installed and the Podman socket available at `/run/podman/podman.sock` on the target host
- `systemd` with Quadlet support (Podman >= 4.4, standard on Fedora 38+)
- A Cloudflare account with a DNS API token scoped to `Zone.DNS` write on the target zone

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `traefik_version` | str | no | `v3.6.2` | Traefik image tag pulled from `docker.io/library/traefik`. |
| `traefik_hostname` | str | yes | — | Hostname for the Traefik dashboard (e.g. `traefik.example.com`). |
| `traefik_data_dir` | str | no | `/opt/podman/traefik` | Host directory for Traefik config files and Let's Encrypt data. |
| `traefik_cloudflare_email` | str | yes | — | Cloudflare account email for the ACME DNS challenge. **Supply from vault.** |
| `traefik_cloudflare_api_token` | str | yes | — | Cloudflare DNS API token (Zone.DNS write scope). **Supply from vault.** |

## Dependencies

None declared in `meta/main.yml`. The target host must have Podman installed with the
user-accessible socket at `/run/podman/podman.sock`. Downstream roles that expose services
through Traefik must attach their containers to the `proxy_network` network created by this role.

## Example Playbook

```yaml
- hosts: fedora_servers
  become: true
  roles:
    - role: danmwallace.podman.traefik
      vars:
        traefik_hostname: traefik.example.com
        traefik_cloudflare_email: "{{ vault_traefik_cloudflare_email }}"
        traefik_cloudflare_api_token: "{{ vault_traefik_cloudflare_api_token }}"
```

## What the Role Does

1. Creates `{{ traefik_data_dir }}` and `{{ traefik_data_dir }}/letsencrypt` with mode `0755`.
2. Touches `{{ traefik_data_dir }}/letsencrypt/acme.json` with mode `0600`, preserving timestamps if the file already exists.
3. Renders the Traefik static configuration (`traefik.yml`) to `{{ traefik_data_dir }}/traefik.yml` (mode `0600`); notifies the restart handler on change.
4. Renders the dynamic configuration (`dynamic_conf.yml`) to `{{ traefik_data_dir }}/dynamic_conf.yml` (mode `0600`); notifies the restart handler on change.
5. Writes the `proxy_network` Quadlet network unit to `/etc/containers/systemd/proxy_network.network` (mode `0644`).
6. Renders the `traefik.container` Quadlet unit to `/etc/containers/systemd/traefik.container` (mode `0644`); notifies the restart handler on change.
7. Runs `systemctl daemon-reload` and enables + starts `traefik.service`.

A `Restart traefik` handler fires when the static config, dynamic config, or container unit
changes, reloading the daemon and restarting `traefik.service`.

## Notes

### Published ports

| Host port | Container port | Protocol |
| --- | --- | --- |
| 443 | 443 | TCP (HTTPS) |
| 8081 | 8081 | TCP (dashboard) |

Port 80 is not published at the host level; the static config redirects `:80 → :443` inside
the container. Expose port 80 on the host if your network does not redirect HTTP at the
firewall before it reaches this host.

### Dynamic configuration

`dynamic_conf.yml` is not templated with Jinja2 variables — it is a static file rendered by a
template with no substitutions. It ships a `secure-headers` middleware (HSTS, XSS protection,
`X-Frame-Options: SAMEORIGIN`), a `compression` middleware, a `rate-limit` middleware
(100 req/s, burst 50), an `insecure-transport` server transport, and a TLS options block
enforcing TLS 1.2+ with three explicit cipher suites.

### Molecule

Tasks tagged `molecule-notest` (enable/start the service, and the restart handler) are skipped
in Molecule scenarios because Quadlet units are not available in the container environment.
The handler also suppresses the "Could not find the requested service" error specifically to
allow Molecule runs to pass cleanly.

## License

MIT
