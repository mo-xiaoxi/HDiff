# Proxy Latest

具体 README 参见 docker/proxy/README.md，这里只将版本更改为了最新稳定版，更改时间：2021/12/7

## log 日志

### Apache

* 版本： 2.4.51
* 日志路径： `/usr/local/apache2/logs/access.log`
* 格式： `"HOST" "FL"`
* 参考： https://httpd.apache.org/docs/current/mod/mod_log_config.html#formats

### Nginx

* 版本： 1.21.0
* 日志路径： `/var/log/nginx/access.log`
* 格式： `"HOST" "REQ"`
* 参考： http://nginx.org/en/docs/http/ngx_http_core_module.html#var_status

### Apache Traffic Server

* 版本： 9.1.1
* 日志路径： `/opt/ats/var/log/trafficserver/ats.log`
* 格式： `"HOST" "REQ"`

### Squid

* 版本： 5.3
* 日志路径： `/var/log/squid/access.log`
* 格式： `"HOST" "URI"`

### Haproxy——日志似乎有问题

* 版本： 2.5.0
* 日志路径： `/var/log/haproxy.log`
* 日志容器名： `rsyslog`
* 格式： `"{HOST}" "REQ"`
* 参考： http://cbonte.github.io/haproxy-dconv/2.4/configuration.html#8.2.4 ，注意这是 2.4 的文档

### Varnish

* 版本： 7.1.0
* 日志路径： `/var/log/varnish/varnishncsa.log`
* 格式： `"HOST" "FL"`