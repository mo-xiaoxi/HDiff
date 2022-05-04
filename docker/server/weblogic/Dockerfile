 # setting base image
FROM ubuntu:20.04

 # new a directory for sshd to run
RUN mkdir -p /var/run/sshd
RUN apt-get update && apt-get install -y ca-certificates

COPY ./sources.list /etc/apt/

 # installing ssh server
RUN apt-get update
RUN apt-get install -y openssh-server

 # installing sudo
RUN apt-get install -y sudo vim git curl software-properties-common

 # make ssh services use IPv4 to let X11 forwarding work correctly
RUN echo AddressFamily inet >> /etc/ssh/sshd_config

 # defining user account imformation
ARG username=ubuntu
ARG userpasswd=toor

 # adding user
RUN useradd -ms /bin/bash $username && (echo $username:$userpasswd | chpasswd)

 # adding user to sudo group
RUN adduser $username sudo

RUN mkdir /home/ubuntu/jdk /home/ubuntu/weblogic /home/ubuntu/base_domain
COPY ./ROOT.war /home/ubuntu/base_domain/ROOT.war
COPY ./createDomain.py /home/ubuntu/base_domain/createDomain.py
RUN chown -R ubuntu:ubuntu /home/ubuntu/
 # setting running application
CMD /usr/sbin/sshd -D