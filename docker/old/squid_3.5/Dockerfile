FROM ubuntu:18.04

# install squid 3
RUN apt update
RUN apt install ca-certificates -y
RUN cp /etc/apt/sources.list /etc/apt/sources.list.bak
COPY res/squid.conf /etc/squid/squid.conf
COPY res/sources.list /etc/apt/sources.list
RUN apt update && apt install squid -y
RUN squid -zN
	
CMD ["squid", "-N", "-f", "/etc/squid/squid.conf"]
	
EXPOSE 8080
