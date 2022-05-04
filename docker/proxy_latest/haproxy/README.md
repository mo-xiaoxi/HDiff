因为使用了 docker compose ，所以需要先把 echo server build 起来，作为 echo-server 镜像供 haproxy 使用，可以修改 docker-compose.yml 文件做修改。
目前输出到了 docker logs 当中，按照`URI PATH HOST`的顺序，输出格式如下：
```
172.18.0.1:38270 [13/Nov/2021:13:07:33.394] /?id=1 / {localhost:9013} "GET /?id=1 HTTP/1.1"
```
日志位置: /var/log/haproxy.log