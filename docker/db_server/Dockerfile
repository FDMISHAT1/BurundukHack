FROM alpine:3.19

RUN apk add --no-cache bash openssh shadow sudo coreutils procps net-tools mariadb python3

RUN ssh-keygen -A && mkdir -p /run/sshd && sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config && sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config

RUN adduser -D -s /bin/bash dbadmin && echo 'dbadmin:dbadmin' | chpasswd

CMD ["sleep", "infinity"]