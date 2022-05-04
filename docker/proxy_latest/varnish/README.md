折腾了蛮久，varnish 比较特殊，官方推荐用两个 container 做，用映射文件来写 log ，并且 Log Format 没有 URI 选项，所以直接打印了 HTTP 第一行，需要做一些解析
格式如下：
```
"localhost:9013" 200 "GET http://localhost:9013/?id=1 HTTP/1.1"
```
日志位置: ./logs/varnishncsa.log or /var/log/varnish/varnishncsa.log


docker-compose up 需要调用：

```
docker exec -it varnish_varnish_1 varnishncsa -D -a -w /var/log/varnish/varnishncsa.log -F '"%{Host}i" %s \"%r\"'
```