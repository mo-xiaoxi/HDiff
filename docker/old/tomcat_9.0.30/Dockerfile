FROM tomcat:9.0.30
RUN mkdir -p /usr/local/tomcat/webapps/ROOT
COPY ./html/* /usr/local/tomcat/webapps/ROOT
EXPOSE 8080

# req_path: /index.html