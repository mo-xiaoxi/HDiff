FROM ruby
COPY main.rb main.rb
RUN gem install webrick -v 1.6.1
EXPOSE 8080

CMD ["ruby", "main.rb"]

# req_path: /index.html
