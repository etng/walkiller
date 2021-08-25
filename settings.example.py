hosts = [
        'localhost',
]
name=""
log_filename='proxy_manager.log'
nginx_host = 'localhost'
nginx_config_file = '/home/me/nginx/conf.d/default.conf'
nginx_restart_command = 'cd /home/me/nginx/ && ./start.sh'
work_dir = '/home/me/blocked-app'
ytoo_subscribe_url = "https://ytoo.xyz/modules/servers/V2raySocks/osubscribe.php?sid=11111&token=copyfromconsole&sip002=1"
default_ss_obfs_host = ''
default_ss_password = ''
default_ss_method = ''
service_base_port = 11000
max_proxy_per_ip = 0
base_ss_port = 10060
base_polipo_port = 10010
dingtalk_token= ""
dingtalk_prefix= "打扰一下："
docker_compose_tpl_txt = '''
version: '3'
services:
{% for killer in killers %}
{% set i = loop.index0 %}
  walker{{ i+1 }}:
    image: etng/wallkiller-base:latest
    restart: unless-stopped
    ports:
      - "{{ killer['ss_port']  }}:{{ killer['ss_port'] }}"
      - "{{ killer['polipo_port'] }}:{{ killer['polipo_port'] }}"
    command: ["/sbin/runsvdir", '/services']
    volumes:
      - /etc/hostname:/etc/host_name:ro
    environment:
      POLIPO_PORT: "{{ killer['polipo_port']}}"
      SS_PORT: "{{ killer['ss_port'] }}"
      SS_SERVER: "{{ killer['ss_server'] }}"
      SS_SERVER_PORT:  "{{ killer['ss_server_port'] }}"
      SS_PASSWORD: "{{ killer['ss_password'] }}"
      SS_METHOD: "{{ killer['ss_method']  }}"
      DINGTALK_TOKEN: "{{ dingtalk_token }}"
      DINGTALK_PREFIX: "{{ dingtalk_prefix }}"
      SS_OBFS_HOST: "{{ killer['ss_obfs_host'] }}"
  {{app_name}}{{ i+1 }}:
    image: {{ app_image }}
    restart: unless-stopped
    ports:
      - "{{ killer['service_port'] }}:{{ app_port }}"
    environment:
      PROXY_SERVER: "http://walker{{ i+1 }}:{{ killer['polipo_port'] }}"
{% endfor %}
'''
app_name='my_blocked_app'
app_image= 'my/blocked-app:latest'
app_port=9080
pp_notify_token=""
pp_notify_topic=""