# Ubuntu 24.04 as a fresh desktop install leaves it, minus the GUI:
# systemd boots, the first account is in the sudo group with a password,
# the desktop's libraries and FUSE 3 are present, Xvfb stands in for the
# display, and the guide installs git, curl, and everything else itself.
FROM ubuntu:24.04
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends systemd systemd-sysv dbus sudo python3 less iproute2 procps \
      ca-certificates locales tzdata file xz-utils gzip bash-completion fuse3 \
      libasound2t64 libatk-bridge2.0-0t64 libatk1.0-0t64 libcups2t64 libdrm2 libgtk-3-0t64 libnotify4 libnss3 libxcomposite1 libxdamage1 libxrandr2 libxtst6 xdg-utils xvfb \
 && rm -rf /var/lib/apt/lists/* \
 && userdel -r ubuntu 2>/dev/null || true
RUN useradd -m -s /bin/bash -G sudo learner && echo 'learner:learner-pass' | chpasswd \
 && systemctl mask systemd-logind.service getty.target console-getty.service \
 && systemctl mask systemd-binfmt.service proc-sys-fs-binfmt_misc.automount proc-sys-fs-binfmt_misc.mount
# systemd-binfmt would flush the Docker VM's global binfmt handlers (amd64 emulation) at boot.
STOPSIGNAL SIGRTMIN+3
CMD ["/sbin/init"]
