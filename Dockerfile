FROM python:3-alpine as setup

WORKDIR /usr/financial/src

ENV FLASK_APP=financial

COPY requirements.txt ./
RUN \
    apk add --no-cache libstdc++ postgresql-libs && \
    apk add --no-cache --virtual .build-deps g++ musl-dev postgresql-dev && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt && \
    apk --purge del .build-deps

FROM setup

WORKDIR /usr/financial/src

COPY . .

EXPOSE 8080

ENTRYPOINT [ "waitress-serve", "--call", "financial:create_app" ]