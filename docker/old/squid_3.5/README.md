# Squid

容器内监听端口为 8080，配置了正向代理。

在调用 build.sh 后，一个可用的启用命令为： ``docker run -it --rm -p 8888:8080 squid3_5``，设置浏览器代理为 127.0.0.1:8888 即可使用 squid 进行正向代理。
