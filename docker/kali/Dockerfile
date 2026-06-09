FROM alpine:3.19

RUN apk add --no-cache bash coreutils grep sed gawk findutils procps net-tools iputils iproute2 curl wget nmap-ncat nmap bind-tools openssh-client vim nano less file tree python3 gcc make git whois traceroute tcpdump socat tar gzip bzip2 xz zip unzip diffutils patch bc sudo shadow


RUN echo "export PS1=\"\\u@kali:\\w\\$ \"" >> /etc/bash.bashrc
RUN adduser -D -s /bin/bash pentester 2>/dev/null; echo 'pentester:pentester' | chpasswd
RUN echo 'pentester ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers
USER pentester
WORKDIR /home/pentester
RUN mkdir -p loot .ssh

CMD ["sleep", "infinity"]