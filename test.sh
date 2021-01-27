#!/bin/sh -e
curl -x socks5://localhost:${SS_PORT} -v ip.fm
curl -x http://localhost:${POLIPO_PORT} -v ip.fm