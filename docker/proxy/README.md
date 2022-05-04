# Proxy

## 运行方式

注意如果对 docker-compose.yml 有修改，请同时修改子目录和当前目录下的内容，以便可以支持单个和所有容器的运行。

### 运行单个 proxy

* 之后只需要进入 echo 以外的子目录，运行 `docker-compose up` 即可启动相应 proxy 和 echo 容器
* 对于 Varnish，如果需要文件打印 log，需要再运行 `docker exec varnish_varnish_1 varnishncsa -D -a -w /var/log/varnish/varnishncsa.log -F '"%{Host}i" %s \"%r\"'`
* 启动之后，统一规定 9013 端口对应为 proxy 端口，9014 端口对应为 echo-server 端口

### 运行所有 proxy

* 在当前目录下运行 `docker-compose up` 即可，具体端口配置请见当前目录下的 docker-compose.yml，从 8002 开始对 proxy 端口编号
* 由于 Varnish 比较特殊，需要运行 `docker exec proxy_varnish_1 varnishncsa -D -a -w /var/log/varnish/varnishncsa.log -F '"%{Host}i" %s \"%r\"'`

如果是MAC系统，需要运行：`docker exec proxy-varnish-1 varnishncsa -D -a -w /var/log/varnish/varnishncsa.log -F '"%{Host}i" %s \"%r\"'`

## 约定和要求

### 表述约定

为方便，在下面表述中约定：

* REQ (REQuest) 表示整个请求
* FL（First Line）表示请求首行
* QS (Query String) 表示查询字符串
* URI 表示请求的完整路径（可能含 QS）
* PATH 表示请求的路径（可能含 QS)，与 URI 的区别为不包括可能存在的 `http://xxx` 部分
* HOST 表示 proxy 理解的目标 host

### 要求

* 格式应为 `"HOST" "xxx" "xxx" ...`，即 `"HOST"` 需要放在最前面，后面的若干个 xxx 中其一必须包含实际的 Query String，建议是用配置中的 Requst(整个请求) 或者 First Line(请求首行)，没有时可以用配置中的 URI/Path + Query String。另外 Haproxy 中的 HOST 格式为 `"{<host>}"`（即多了一个中括号），需在代码中处理；
* 日志存储在容器内部即可，需要在下面的 ”log 日志“ 部分指明容器内部日志的路径，可以映射到外部用于调试。

关于容器：

* 需要同时在子目录和当前目录下维护 docker-compose.yml，以便于两种模式的运行；
* 在 docker-compose.yml 中，echo 容器统一命名为 echo-server；
* 规定子目录下的 docker-compose.yml 中，9013 端口映射到 proxy，9014 端口映射到 echo-server 端口。当前目录下的 docker-compose.yml 从 8002 开始按顺序映射 proxy。
* 如果 log 文件在另一个容器中，务必指明该容器名

## log 日志

### Apache

* 版本： 2.4.47
* 日志路径： `/usr/local/apache2/logs/access.log`
* 格式： `"HOST" "FL"`
* 参考： https://httpd.apache.org/docs/current/mod/mod_log_config.html#formats

### Nginx

* 版本： 1.21.0
* 日志路径： `/var/log/nginx/access.log`
* 格式： `"HOST" "REQ"`
* 参考： http://nginx.org/en/docs/http/ngx_http_core_module.html#var_status

### Apache Traffic Server

* 版本： 8.0.5
* 日志路径： `/opt/ats/var/log/trafficserver/ats.log`
* 格式： `"HOST" "REQ"`
* 参考： https://docs.trafficserver.apache.org/en/8.1.x/admin-guide/logging/formatting.en.html ，注意这是 8.1.x 的文档

### Squid

* 版本： 4.13
* 日志路径： `/var/log/squid/access.log`
* 格式： `"HOST" "URI"`
* 参考： http://www.squid-cache.org/Versions/v4/cfgman/logformat.html ，注意这是 v4 的文档

### Haproxy

* 版本： 2.4.0
* 日志路径： `/var/log/haproxy.log`
* 日志容器名： `rsyslog`
* 格式： `"{HOST}" "REQ"`
* 参考： http://cbonte.github.io/haproxy-dconv/2.4/configuration.html#8.2.4 ，注意这是 2.4 的文档

### Varnish

* 版本： 6.5.1
* 日志路径： `/var/log/varnish/varnishncsa.log`
* 格式： `"HOST" "FL"`