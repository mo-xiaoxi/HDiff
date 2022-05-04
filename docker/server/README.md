# Host 测试环境说明

容器列表如下：

* php
* nginx
* apache
* lighttpd
* tomcat：待加入 php

可以在 docker-compose.yml 中直接更改容器版本。

## 使用方式

* 启动脚本

```
docker-compose up  # 前台启动
docker-compose up -d  # 后台启动
```

* 注意 IIS 和 weblogic 都是手动搭建的，不在 docker-compose 处启动。

## 规定

* 除了 php 命名为 "php-fpm"，容器名均以 "-server" 作为结尾，例如 nginx 对应 "nginx-server"；
* php 文件映射到每个容器的 `/var/www/html` 目录下（部分不方便配置的除外，例如 tomcat，这个也没有什么影响）；
* 匹配到 '/' 时应该使用 '/index.php'，其它路径不太方便重定向到 index.php 可以不做；
* 返回格式为形如 `{"URI": <URI with Query String>, "HOST": <Host>}` 的 JSON 格式。

## 端口映射

* php: 9050:9000，提供 fastcgi 服务，注意这里的 9050 仅作为一种调试方案提供给主机，其它容器应当使用 host-php:9000 进行访问

web server 服务:

* nginx: 9051:80
* apache: 9052:80
* lighttpd: 9053:80
* tomcat: 9054:80

# 踩坑

* php-fpm 使用时，CGI 的输入仅为脚本路径，具体的 .php 脚本应该存放在 php 对应的容器中。当然为了方便(例如可以显示默认页面等)，这里对所有容器都将 `./www` 映射进去了。
