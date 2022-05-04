FROM ubuntu:18.04

COPY res/dart_2.7.1-1_amd64.deb /
COPY res/main.dt /

# install dart
RUN dpkg -i dart_2.7.1-1_amd64.deb

EXPOSE 8080
CMD ["dart", "main.dt"]

# req_path: /
