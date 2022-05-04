FROM php:7.2.5

COPY res/install_composer.sh /
RUN apt update && apt install wget -y
RUN bash install_composer.sh
RUN wget https://get.symfony.com/cli/installer -O - | bash
RUN apt install git -y \
	&& git config --global user.email "315629555@qq.com" \
	&& git config --global user.name "yangyaru"
RUN /root/.symfony/bin/symfony new smuggling && cd smuggling
WORKDIR smuggling
COPY res/routes.yaml config/
COPY res/SmugglingController.php src/Controller/

EXPOSE 8080
CMD ["/root/.symfony/bin/symfony", "server:start", "-port=8080", "--no-interaction"]

# req_path: /
