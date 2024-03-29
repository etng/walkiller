FROM alpine:3.9

ARG TZ='Asia/Shanghai'

ENV TZ ${TZ}
ENV SS_LIBEV_VERSION v3.2.4
ENV KCP_VERSION 20190109
ENV SS_DOWNLOAD_URL https://github.com/shadowsocks/shadowsocks-libev.git
ENV OBFS_DOWNLOAD_URL https://github.com/shadowsocks/simple-obfs.git
ENV V2RAY_PLUGIN_DOWNLOAD_URL https://github.com/shadowsocks/v2ray-plugin/releases/download/v1.0/v2ray-plugin-linux-amd64-8cea1a3.tar.gz
ENV KCP_DOWNLOAD_URL https://github.com/xtaci/kcptun/releases/download/v${KCP_VERSION}/kcptun-linux-amd64-${KCP_VERSION}.tar.gz
ENV LINUX_HEADERS_DOWNLOAD_URL=http://dl-cdn.alpinelinux.org/alpine/v3.7/main/x86_64/linux-headers-4.4.6-r2.apk
ENV POLIPO_CLONE_URL=https://github.com/jech/polipo.git
ENV POLIPO_PORT=1088
ENV SS_PORT=1080
ENV SS_SERVER=""
ENV SS_SERVER_PORT=8338
ENV SS_PASSWORD=""
ENV SS_METHOD="chacha20-ietf"
ENV SS_OBFS_HOST=""
ENV SC_KEY=
ENV NOTIFY_URL=

RUN apk upgrade \
    && apk add \
        bash \
        tzdata \
        rng-tools \
        curl \
        git \
        vim \
        tar \
        runit \
    && apk add --virtual .build-deps \
        autoconf \
        automake \
        build-base \
        c-ares-dev \
        libev-dev \
        libtool \
        libsodium-dev \
        mbedtls-dev \
        pcre-dev \
        texinfo \
    && curl -sSL ${LINUX_HEADERS_DOWNLOAD_URL} > /linux-headers-4.4.6-r2.apk \
    && apk add --virtual .build-deps-kernel /linux-headers-4.4.6-r2.apk \
    && git clone ${SS_DOWNLOAD_URL} \
    && (cd shadowsocks-libev \
    && git checkout tags/${SS_LIBEV_VERSION} -b ${SS_LIBEV_VERSION} \
    && git submodule update --init --recursive \
    && ./autogen.sh \
    && ./configure --prefix=/usr --disable-documentation \
    && make install) \
    && git clone ${OBFS_DOWNLOAD_URL} \
    && (cd simple-obfs \
    && git submodule update --init --recursive \
    && ./autogen.sh \
    && ./configure --disable-documentation \
    && make install) \
    && git clone ${POLIPO_CLONE_URL} \
    && (cd polipo \
    && make -sj \
    && make install) \
    && curl -o v2ray_plugin.tar.gz -sSL ${V2RAY_PLUGIN_DOWNLOAD_URL} \
    && tar -zxf v2ray_plugin.tar.gz \
    && mv v2ray-plugin_linux_amd64 /usr/bin/v2ray-plugin \
    && curl -sSLO ${KCP_DOWNLOAD_URL} \
    && tar -zxf kcptun-linux-amd64-${KCP_VERSION}.tar.gz \
    && mv server_linux_amd64 /usr/bin/kcpserver \
    && mv client_linux_amd64 /usr/bin/kcpclient \
    && ln -sf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo ${TZ} > /etc/timezone \
    && apk del .build-deps .build-deps-kernel \
	&& apk add --no-cache \
      $(scanelf --needed --nobanner /usr/bin/ss-* /usr/local/bin/obfs-* \
      | awk '{ gsub(/,/, "\nso:", $2); print "so:" $2 }' \
      | sort -u) \
    && rm -rf /linux-headers-4.4.6-r2.apk \
        kcptun-linux-amd64-${KCP_VERSION}.tar.gz \
        shadowsocks-libev \
        simple-obfs \
        polipo \
        v2ray_plugin.tar.gz \
        /var/cache/apk/*
EXPOSE 1080 1088
ADD services /services
ADD test.sh /root/test.sh
ADD monitor.sh /root/monitor.sh
WORKDIR /root/
CMD ["/sbin/runsvdir", '/services']
