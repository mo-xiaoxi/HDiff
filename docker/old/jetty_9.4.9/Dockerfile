FROM jetty:9.4.9
RUN mkdir -p /var/lib/jetty/webapps/root
COPY ./html/* /var/lib/jetty/webapps/root/
EXPOSE 8080
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["java","-jar","/usr/local/jetty/start.jar"]

# req_path: /index.html