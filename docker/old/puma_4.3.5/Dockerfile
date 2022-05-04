FROM ruby:2.7.2
COPY res/node-v14.15.1-linux-x64.tar.xz /
COPY res/docker-entrypoint.sh /
# install rails
RUN gem install rails -v 6.0
# install node
RUN tar xfv node-v14.15.1-linux-x64.tar.xz \
	&& ln -s /node-v14.15.1-linux-x64/bin/npm /usr/local/bin/ \
	&& ln -s /node-v14.15.1-linux-x64/bin/node /usr/local/bin/
# install yarn
RUN curl -sS https://dl.yarnpkg.com/debian/pubkey.gpg | apt-key add - \
	&& echo "deb https://dl.yarnpkg.com/debian/ stable main" | tee /etc/apt/sources.list.d/yarn.list \
	&& apt update && apt install -y yarn=1.22.5-1
RUN rails new smuggling && cd smuggling
# install puma 4.3.5
RUN rm /smuggling/Gemfile
COPY res/Gemfile /smuggling/
WORKDIR /smuggling
RUN bundle install
# smuggling html
RUN rails generate controller Welcome index
COPY res/routes.rb /smuggling/config/
COPY res/index.html.erb /smuggling/app/views/welcome/

EXPOSE 8080
ENTRYPOINT ["sh", "/docker-entrypoint.sh"]
CMD ["rails", "server", "-p", "8080", "-b", "0.0.0.0"]

# req_path: /
