# Ubuntu 24.04 as `wsl --install -d Ubuntu-24.04` leaves it: systemd on, the
# first account in sudo with a password, no Docker Engine. The Docker CLI that
# Docker Desktop's WSL integration provides waits in /opt/desktop-cli until the
# harness turns integration on; WSLg's display is stood in for by Xvfb.
FROM docker:28-cli AS desktop-cli
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends systemd systemd-sysv dbus sudo python3 less iproute2 procps \
      ca-certificates locales tzdata file xz-utils gzip bash-completion xvfb \
      libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libcups2t64 libdrm2 libgtk-3-0t64 libnotify4 libnss3 \
      libxcomposite1 libxdamage1 libxrandr2 libxtst6 libgbm1 xdg-utils \
 && rm -rf /var/lib/apt/lists/* \
 && (userdel -r ubuntu 2>/dev/null || true)
RUN useradd -m -s /bin/bash -G sudo learner && echo 'learner:learner-pass' | chpasswd \
 && systemctl mask systemd-logind.service getty.target console-getty.service \
 && systemctl mask systemd-binfmt.service proc-sys-fs-binfmt_misc.automount proc-sys-fs-binfmt_misc.mount \
 && mkdir -p /mnt/c/Windows/system32 /mnt/c/Windows/System32/Wbem /mnt/c/Windows/System32/WindowsPowerShell/v1.0 \
      /mnt/wslg/runtime-dir /mnt/wsl/docker-desktop/shared-sockets /usr/lib/wsl/lib /opt/desktop-cli/cli-plugins
COPY --from=desktop-cli /usr/local/bin/docker /opt/desktop-cli/docker
COPY --from=desktop-cli /usr/local/libexec/docker/cli-plugins/docker-compose /opt/desktop-cli/cli-plugins/docker-compose
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
