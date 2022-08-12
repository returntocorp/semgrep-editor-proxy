FROM python:alpine3.16

# System deps:
RUN apk --update add nodejs npm ruby ruby-dev build-base php bash curl composer git php-pcntl php-tokenizer php-dom php-xml php-xmlwriter php-simplexml

# Install language servers
RUN npm install -g pyright typescript typescript-language-server yaml-language-server
RUN gem install solargraph
RUN git clone https://github.com/phpactor/phpactor.git && \
    cd phpactor && \
    composer update && \
    composer install
RUN ln -s /phpactor/bin/phpactor /usr/local/bin/phpactor

COPY ./dist/semgrep_editor_proxy-0.1.0-py3-none-any.whl /
RUN pip install semgrep semgrep_editor_proxy-0.1.0-py3-none-any.whl
RUN chmod +x /usr/local/lib/python3.10/site-packages/semgrep_editor_proxy/main.py
RUN ln -s /usr/local/lib/python3.10/site-packages/semgrep_editor_proxy/main.py /usr/local/bin/semgrep-editor-proxy

