没有官方 docker ， ubuntu 给了一个，应该能用，算是个 LTS 版本，但不是最新版本，

关键配置在 squid.conf#1907 行
```
http_port 3128 accel defaultsite=echo-server no-vhost # 3128 为 squid 监听端口， echo-server 为后端 Host
cache_peer echo-server parent 8001 0 originserver name=myAccel # 需要配置好转发的 Host 的端口
logformat httpd %>ru %rp "%{Host}>h"
access_log /var/log/squid/access.log httpd
```

报文格式
```
200 "http://echo-server/?id=1" "echo-server"
```

日志位置: /var/log/squid/access.log

配置页面： http://www.squid-cache.org/Doc/config/logformat/