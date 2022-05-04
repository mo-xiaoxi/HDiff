FROM haproxy

# Not verify. Use docker compose first.
# RUN set -x	&& \
# 	apk upgrade --update					&&  \
#     apk add bash ca-certificates rsyslog    &&  \
# 	mkdir -p /etc/rsyslog.d/				&&  \
# 	touch /var/log/haproxy.log				&&  \
# 	ln -sf /dev/stdout /var/log/haproxy.log

USER root
RUN apt update && apt install -y netcat
# COPY ./haproxy.cfg /usr/local/etc/haproxy/haproxy.cfg

# CMD ["haproxy", "-f", "/usr/local/etc/haproxy/haproxy.cfg"]