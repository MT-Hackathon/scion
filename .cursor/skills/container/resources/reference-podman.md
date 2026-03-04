# Podman Reference

State infrastructure uses Podman. These patterns differ from Docker.

## Rootless by Default

No `sudo` required. Files created by containers owned by current user:

```bash
podman run -v ./data:/data alpine touch /data/file.txt
ls -la ./data/file.txt  # owned by your user, not root
```

## Daemonless Architecture

No background service. Each CLI command spawns its own process:

```bash
# No "podman start" needed - just run commands directly
podman run --rm alpine echo "hello"
```

## CI/CD Integration

GitLab runners use `AHSPODMAN` tag. Build templates at:

```text
Enterprise/DOA/SITSD/ATSB/AHS/ahs-hosted-deployment-projects/software-factory/applications
├── SITSD/DOA.SITSD.Podman/doa.sitsd.build.yml      # nonprod
└── SITSD/DOA.SITSD.Podman/doa.sitsd.build.web.yml  # prod
```

## Systemd Integration

Generate service units for container auto-start:

```bash
podman generate systemd --name mycontainer --files
mv container-mycontainer.service ~/.config/systemd/user/
systemctl --user enable container-mycontainer.service
```

## Docker Compatibility

For scripts expecting `docker` command:

```bash
alias docker=podman
```

## Podman Compose

Use `podman-compose` or `podman compose` (built-in since 4.1):

```bash
podman compose up -d
podman compose logs -f
podman compose down
```
