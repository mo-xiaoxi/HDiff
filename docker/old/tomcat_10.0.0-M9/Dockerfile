FROM tomcat:10.0.0-M9
RUN mkdir -p /usr/local/tomcat/webapps/ROOT
COPY ./html/* /usr/local/tomcat/webapps/ROOT
EXPOSE 8080

# req_path: /index.html