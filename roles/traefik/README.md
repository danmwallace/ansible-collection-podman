# danmwallace.podman.traefik

Deploys [Traefik](https://traefik.io/) v3 as a rootful Podman Quadlet container unit on
Fedora Server, running `docker.io/library/traefik:{{ traefik_version }}` (default
`v3.7.13`). Traefik publishes port 443 on the host and redirects `:80 → :443` inside the
container; TLS certificates come from Let's Encrypt via the Cloudflare DNS-01 ACME
challenge and are stored in `{{ traefik_data_dir }}/letsencrypt/acme.json`.

The role creates a `proxy_network` Quadlet network unit at
`/etc/containers/systemd/proxy_network.network`. Other Podman services that need to be
proxied attach to this network (systemd names it `systemd-proxy_network`) and are
discovered through the Podman socket, which is mounted read-only from
`/run/podman/podman.sock` to the Docker-compatible path `/var/run/docker.sock`.
Static configuration is rendered to `{{ traefik_data_dir }}/traefik.yml` and dynamic
configuration (middlewares, server transports, TLS options) to
`{{ traefik_data_dir }}/conf.d/dynamic_conf.yml`, which the file provider watches with
live reload.

## Requirements

- Ansible >= 2.16
- Fedora Server with Podman and the systemd Quadlet generator (`podman >= 4.4`), with
  the rootful Podman socket available at `/run/podman/podman.sock`
- The `containers.podman >= 1.11.0`, `ansible.posix >= 1.5.0`, and
  `community.general >= 8.0.0` collections (declared as collection-level dependencies
  of `danmwallace.podman`)
- A Cloudflare account and a DNS API token with `Zone.DNS` write on the target zone

## Role Variables

| Variable | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `traefik_version` | str | no | `v3.7.13` | Traefik image tag pulled from `docker.io/library/traefik`. |
| `traefik_hostname` | str | yes | — | Hostname for the Traefik dashboard (e.g. `traefik.example.com`). |
| `traefik_data_dir` | str | no | `/opt/podman/traefik` | Host directory for Traefik config files and Let's Encrypt data. |
| `traefik_cloudflare_email` | str | yes | — | Cloudflare account email for the ACME DNS challenge (`CF_API_EMAIL` and the ACME account email). |
| `traefik_cloudflare_api_token` | str | yes | — | Cloudflare DNS API token (`CF_DNS_API_TOKEN`, needs `Zone.DNS` write). **Supply from vault.** |

## Dependencies

None declared in `meta/main.yml`. Downstream roles that expose services through Traefik
must attach their containers to the `proxy_network` network created by this role and
set `traefik.*` labels on their Quadlet units.

## Example Playbook

```yaml
- hosts: fedora_servers
  become: true
  roles:
    - role: danmwallace.podman.traefik
      vars:
        traefik_hostname: traefik.example.com
        traefik_cloudflare_email: ops@example.com
        traefik_cloudflare_api_token: "{{ vault_traefik_cloudflare_api_token }}"
```

## What the Role Does

1. Creates `{{ traefik_data_dir }}`, `{{ traefik_data_dir }}/letsencrypt`, and
   `{{ traefik_data_dir }}/conf.d` with mode `0755`.
2. Touches `{{ traefik_data_dir }}/letsencrypt/acme.json` with mode `0600`, preserving
   timestamps if the file already exists (so re-runs are idempotent).
3. Renders the static configuration from `traefik.yml.j2` to
   `{{ traefik_data_dir }}/traefik.yml` (mode `0600`). Notifies `Restart traefik` on
   change.
4. Renders the dynamic configuration from `dynamic_conf.yml.j2` to
   `{{ traefik_data_dir }}/conf.d/dynamic_conf.yml` (mode `0600`). Notifies
   `Restart traefik` on change.
5. Writes `/etc/containers/systemd/proxy_network.network`, a minimal Quadlet network unit
   labelled `managed_by=ansible` (mode `0644`).
6. Renders `/etc/containers/systemd/traefik.container` from `traefik.container.j2`
   (mode `0644`): the image pin, published ports, config and socket mounts,
   `SecurityLabelDisable=true`, the Cloudflare credentials as environment variables,
   and the dashboard router labels. Notifies `Restart traefik` on change.
7. Enables and starts `traefik.service` with `daemon_reload: true`.

A `Restart traefik` handler fires when the static config, dynamic config, or container
unit changes, reloading the daemon and restarting `traefik.service`.

## Notes

### Published ports

| Host bind | Container port | Purpose |
| --- | --- | --- |
| `0.0.0.0:443` | 443 | `websecure` entrypoint (HTTPS) |
| `127.0.0.1:8081` | 8081 | Loopback-only publish; no entrypoint is bound to it in `traefik.yml` |

Port 80 is not published on the host; the `web` entrypoint's permanent redirect to
`websecure` only applies to traffic that reaches the container. Publish port 80 if HTTP
is not already redirected upstream.

### Dashboard

`api.dashboard: true` with `api.insecure: false`; the dashboard is exposed only as the
`api@internal` service on the `traefik` router at `Host(\`{{ traefik_hostname }}\`)`
over `websecure`. No authentication middleware is attached by this role.

### Static configuration

The Docker provider uses `exposedByDefault: false` (services opt in with
`traefik.enable=true`) and `network: systemd-proxy_network`. The `cloudflare` ACME
resolver uses the DNS-01 challenge with `delayBeforeCheck: 0` and resolvers
`1.1.1.1:53` / `1.0.0.1:53`. Logging is `INFO`, access logging is enabled, and version
checks and anonymous usage reporting are disabled.

### Dynamic configuration

`dynamic_conf.yml.j2` contains no Jinja2 substitutions. It ships a `secure-headers`
middleware (HSTS with preload, `X-Frame-Options: SAMEORIGIN`, `nosniff`,
`referrerPolicy: same-origin`, `X-Forwarded-Proto: https`), a `compression` middleware,
a `rate-limit` middleware (average 100, burst 50), and a default TLS options block
enforcing TLS 1.2+ with three explicit ECDHE cipher suites. It also defines a
`unifi-insecure-transport` server transport with `insecureSkipVerify: true`, intended
only for backends with self-signed certificates (the UniFi controller on 8443); do not
reference it from other services.

### Podman socket

The container mounts the rootful Podman socket read-only and sets
`SecurityLabelDisable=true` so it can read the socket under SELinux enforcing. Anything
with access to that socket effectively has root on the host; keep the dashboard and the
host's port 443 behind a trusted network or add an auth middleware.

### Molecule

Tasks tagged `molecule-notest` (the enable/start task and the restart handler) are
skipped in Molecule scenarios because Quadlet units are not generated in the test
container. The handler also suppresses the "Could not find the requested service" error
so Molecule runs pass cleanly.

## License

MIT
