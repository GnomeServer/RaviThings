# Arch Linux ARM (aarch64), booting systemd natively, with the packages the
# guide's step 2 installs already present. Docker is left to the guide.
# DisableSandbox: container builds block the Landlock rules pacman's download
# sandbox needs; a real machine doesn't need this.
FROM menci/archlinuxarm:latest
RUN printf '\n[options]\nDisableSandbox\n' >> /etc/pacman.conf \
 && pacman -Syu --noconfirm \
 && pacman -S --noconfirm --needed systemd sudo iproute2 git python curl ca-certificates diffutils less \
 && rm -rf /var/cache/pacman/pkg/*
RUN useradd -m -s /bin/bash -G wheel learner \
 && echo 'learner:learner-pass' | chpasswd \
 && printf '%%wheel ALL=(ALL:ALL) ALL\n' > /etc/sudoers.d/10-wheel && chmod 440 /etc/sudoers.d/10-wheel \
 && systemctl mask systemd-logind.service getty.target console-getty.service \
 && systemctl mask systemd-binfmt.service proc-sys-fs-binfmt_misc.automount proc-sys-fs-binfmt_misc.mount
# systemd-binfmt would flush the Docker VM's global binfmt handlers at boot.
STOPSIGNAL SIGRTMIN+3
CMD ["/usr/lib/systemd/systemd"]
