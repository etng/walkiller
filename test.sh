#!/bin/sh -e
curl -x socks5://localhost:1080 -v ip.fm
curl -x http://localhost:1088 -v ip.fm