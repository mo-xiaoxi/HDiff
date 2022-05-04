FROM ubuntu:20.04

WORKDIR /tmp
COPY ./sources.list /etc/apt/sources.list
RUN apt update && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y tzdata && \
    apt install -y automake binutils wget && \
    apt build-dep -y squid
RUN wget http://www.squid-cache.org/Versions/v5/squid-5.3.tar.gz && tar -xvf squid-5.3.tar.gz

WORKDIR /tmp/squid-5.3
RUN ./configure --prefix=/usr \
    --localstatedir=/var \
    --libexecdir=${prefix}/lib/squid \
    --datadir=${prefix}/share/squid \
    --sysconfdir=/etc/squid \
    --with-default-user=proxy \
    --with-logdir=/var/log/squid \
    --with-pidfile=/var/run/squid.pid
RUN make && make install
RUN squid -z && chmod 777 -R /var/log

CMD ["/usr/sbin/squid", "-N", "-d1"]