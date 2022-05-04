FROM centos:7

MAINTAINER Reyes Ruiz <reyes_ruiz@digitalruiz.com>

ENV container docker

WORKDIR /tmp
RUN yum clean all && yum update -y
RUN yum install vim wget telnet bind-utils net-tools lsof pkgconfig libtool gcc gcc-c++ make \
	openssl openssl-devel tcl tcl-devel pcre pcre-devel libcap libcap-devel \
	flex hwloc hwloc-devel lua ncurses ncurses-devel curl libcurl-devel autoconf automake \
	libunwind libunwind-devel bzip2 expat-devel centos-release-scl -y
RUN yum install devtoolset-7-gcc-c++ -y
RUN yum clean all && yum update -y
RUN wget https://archive.apache.org/dist/trafficserver/trafficserver-8.0.2.tar.bz2
RUN tar -xvf trafficserver-8.0.2.tar.bz2

WORKDIR /tmp/trafficserver-8.0.2
RUN autoreconf -if
RUN scl enable devtoolset-7 './configure --prefix=/opt/ts'
RUN scl enable devtoolset-7 'make && make check && make install'

WORKDIR /tmp
RUN rm -rf trafficserver-8.0.2*

COPY entry.sh /tmp/entry.sh

EXPOSE 8080

ENTRYPOINT ["bash", "/tmp/entry.sh"]