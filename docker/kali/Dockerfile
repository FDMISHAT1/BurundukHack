FROM debian:bookworm-slim

# Kali-like pentesting workstation
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash coreutils grep sed awk findutils procps net-tools \
    iputils-ping iproute2 curl wget netcat-openbsd nmap dnsutils \
    openssh-client vim nano less file tree \
    python3 python3-pip gcc make git \
    whois traceroute tcpdump socat \
    tar gzip bzip2 xz-utils zip unzip \
    diffutils patch bc dc \
    man-db manpages \
    sudo passwd \
    && rm -rf /var/lib/apt/lists/*

# Create pentester user
RUN useradd -m -s /bin/bash -G sudo pentester && \
    echo "pentester:pentester" | chpasswd && \
    echo "pentester ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers

# Setup realistic environment
RUN echo 'export PS1="\u@kali:\w\$ "' >> /home/pentester/.bashrc && \
    echo 'alias ll="ls -lah"' >> /home/pentester/.bashrc && \
    echo 'alias la="ls -la"' >> /home/pentester/.bashrc && \
    mkdir -p /home/pentester/loot /home/pentester/.ssh

COPY motd /etc/motd
RUN echo "cat /etc/motd" >> /home/pentester/.bashrc

USER pentester
WORKDIR /home/pentester

# Keep container alive
CMD ["sleep", "infinity"]
