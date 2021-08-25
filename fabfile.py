import json
import os
import yaml
from random import shuffle
import re
from fabric import task
from fabric import SerialGroup as Group
from fabric import ThreadingGroup
from fabric import Connection
import subprocess
from jinja2 import Template
from datetime import datetime, timedelta
import settings
import requests
import shlex
import logging
from functools import partial
logging.basicConfig(
    filename=settings.log_filename,
    level=logging.INFO,
    format= '[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger('proxy_manager')
docker_compose_tpl =Template(settings.docker_compose_tpl_txt, trim_blocks=True)
batch_tips = "\nif this is not in batch update, you should compose it"

def showBool(b):
    return 'yes' if b else 'no'

def notify_pp(title='', body='', template='html', token='', topic=''):
    if not token:
        logger.warn('skip notify with empty token')
        return False
    if token:
        logger.debug('sending pp notify')
        response = requests.post('http://www.pushplus.plus/send?token='+token, json={
            'title': title,
            'template': template,
            'topic': topic,
            'content': body,
        })
        logger.info(f'notify result {response.status_code} {response.text}')
        logger.info('sent pp notify')

def markdownTable(rows, *cols):
    if not cols:
        cols = rows[0].keys()
    lines = []
    lines.append(' | '.join(cols))
    lines.append(' | '.join(['---'] * len(cols)))
    for row in rows:
        lines.append(' | '.join([f'{row[_]}' for _ in cols]))
    return "\n".join(map(lambda _: f'| {_} |', lines))

notify = partial(notify_pp, token=settings.pp_notify_token, topic=settings.pp_notify_topic)


def clean_proxy_name(name):
    name = name.strip()
    name = re.sub(r'^(标准|特殊|高级|购物)\s*(.+?)', r'\2', name)
    name = re.sub(r'\s*\[?\d+(\.\d+)?\]?$', '', name)
    return name.strip()

def isTranslateServiceOnline(api_server):
    try:
        response = requests.post(f'{api_server}/api/v1/translator', json={
            'text': 'Please say hello to everybody in English.',
            'dest': '',
        })
    except Exception as e:
        logging.error(f'fail to do request for {e}')
        return False
    if response.status_code !=200:
        return False
    data = response.json()
    if not data['data'].get('text_trans'):
        return False
    # logger.info(data['data'].get('text_trans'))
    return True

def isProxyOk(proxy):
    try:
        command = ['curl',
        '-k',
        # '-v',
        '-sSL',
        '-x',
            proxy,
            'ip.fm',
            ]
        logger.debug(" ".join(command))
        res = subprocess.check_output(command)
        logger.debug(res.decode('utf-8').strip())
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"curl error: {e}")
        return False

@task
def check(c):
    for host in settings.hosts:
        c = Connection(host)
        logger.info(f'checking host {host}')
        with c.cd(settings.work_dir):
            r = c.run('docker-compose ps', hide=True)
            if r.ok:
                logger.debug(r.stdout)
            else:
                logger.error('fail for {r.stderr}')
    logger.info("node check done")

@task
def restart_nginx(c):
    conn = Connection(settings.nginx_host)
    conn.get(settings.nginx_config_file, 'nginx.host.conf')
    upstreams = open('upstreams.txt').read()
    prefix=  '#hosts begin'
    suffix = '#hosts end'
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    comment = f'#updated at {now}'
    content = open('nginx.host.conf').read()
    with open(f'nginx.host.{settings.nginx_host}.conf', 'w') as f:
        f.write(re.sub(prefix + r'(.*)' + suffix, lambda m: "\n".join([prefix,comment,upstreams,comment,suffix]), content, flags=re.DOTALL))
    conn.put(f'nginx.host.{settings.nginx_host}.conf', settings.nginx_config_file)
    conn.run(settings.nginx_restart_command)
    notify(title=f"{settings.name}translate server nginx restarted", body="please check related port for availability")

@task
def update(c):
    update_subscribe(c)
    compose(c)
    restart_nginx(c)
    check(c)

@task
def update_subscribe(c):
    result = subprocess.check_output(['./ytoo_updater', '-url', settings.ytoo_subscribe_url])
    proxies = []
    for line in result.splitlines():
        if line:
            proxy = json.loads(line)
            proxy.setdefault('name', '')
            ss_obfs_host = settings.default_ss_obfs_host
            try:
                ss_obfs_host = proxy.get('plugin', {}).get('obfs-host', settings.default_ss_obfs_host)
            except:
                pass
            proxies.append({
                'name': proxy['name'],
                'ss_server': proxy['host'],
                'ss_server_port': proxy['port'],
                'ss_area': proxy['name'],
                'ss_method': proxy.get('method', settings.default_ss_method),
                'ss_password': proxy.get('password', proxy.get('passwd', settings.default_ss_password)),
                'ss_obfs_host': ss_obfs_host,
            })
    proxy_cnt = len(proxies)
    ip_cnt = len(settings.hosts)
    proxy_per_ip = int(proxy_cnt/ip_cnt)
    logger.info(f"got {proxy_cnt} proxies, we have {len(settings.hosts)} hosts, so {proxy_per_ip} proxies per host")
    if settings.max_proxy_per_ip and proxy_per_ip > settings.max_proxy_per_ip:
        proxy_per_ip = settings.max_proxy_per_ip
        logger.info(f"proxies per host {proxy_per_ip} > max proxies per host setting {settings.max_proxy_per_ip}, so update proxies per host to proxy_per_ip")
        shuffle(proxies)
    offset = 0
    monitor_endpoints = []
    upstreams = []
    for host in settings.hosts:
        logger.info(f'updating work node {host}')
        ss_port = settings.base_ss_port
        polipo_port = settings.base_polipo_port
        service_port = settings.service_base_port
        killers = []
        for i, proxy in enumerate(proxies[offset:offset+proxy_per_ip]):
            killers.append(dict(proxy, ss_port=ss_port, polipo_port=polipo_port,service_port=service_port))
            upstreams.append(f'# {proxy["name"]} \nserver {host}:{service_port};')

            monitor_endpoints.append({
                'name': f'{host} worker{i+1}  {proxy["name"]}',
                'stop': f'ssh root@{host} docker-compose -f { settings.work_dir}/docker-compose.yml stop walker{i+1} translator{i+1}',
                'socks5': f'socks5://{host}:{ss_port}',
                'http': f'http://{host}:{polipo_port}',
                'service': f'http://{host}:{service_port}',
                'area': clean_proxy_name(proxy['name']),
            })
            ss_port +=1
            polipo_port +=1
            service_port +=1
        with open(f'docker-compose.{host}.yml', 'w') as f:
            f.write(docker_compose_tpl.render(
                ip=host,
                killers=killers,
                dingtalk_token=settings.dingtalk_token,
                dingtalk_prefix=settings.dingtalk_prefix,
                notify_url=settings.notify_url,
                app_image=settings.app_image,
                app_name=settings.app_name,
                app_port=settings.app_port,
            ))
        offset+=proxy_per_ip
    with open(f'monitor_endpoints.json', 'w') as f:
        f.write(json.dumps(monitor_endpoints, ensure_ascii=False, indent=2))
    with open('upstreams.txt', 'w') as f:
        f.write("\n".join(upstreams))
    logging.info('done')
    notify(title=f"{settings.name} proxy update done", body="\n".join([
        f"* `proxy_cnt`: {proxy_cnt} ",
        f"* `host_cnt`: {ip_cnt} ",
        f"* `proxy_per_host`: {proxy_per_ip}",
        f"* `proxy_used_cnt`: {len(monitor_endpoints)}",
        batch_tips,
    ]), template="markdown")


@task
def sync_images(c):
    hosts = [_ for _ in settings.hosts if _!="localhost"]
    g = ThreadingGroup(*hosts)
    logger.info('image ETL begin')
    for image, filename in settings.images.items():
        logger.info(f'pulling image {image}')
        subprocess.check_call(['docker', 'pull', image])
    if not len(hosts):
        logger.info("no host other than localhost,skip image ETL(EXTRACT-TRANSFER-LOAD)")
    else:
        for image, filename in settings.images.items():
            logger.info(f"extracting image {image} as {filename}")
            with open(f'app/data/{filename}', 'wb') as f:
                ps = subprocess.Popen(('docker', 'image', 'save', image), stdout=subprocess.PIPE)
                output = subprocess.Popen(('xz'), stdin=ps.stdout, stdout=f)
                ps.wait()
            logger.info(f"transferring image {filename} to hosts")
            g.remove
            g.put(f"app/data/{filename}", os.path.join(settings.work_dir, "images", filename))
        logger.info('images sent, loading')
        for host in hosts:
            conn = Connection(host)
            logger.info(f"loading image {filename} at host {host}")
            with conn.cd(settings.work_dir):
                for image, filename in settings.images.items():
                    conn.run(f"xz -d -k -c images/{filename}|docker image load ")
    logging.info("image ETL end")
    notify(title=f"{settings.name} docker images sync done", body=batch_tips)

@task
def compose(c):
    logging.info("service compose begin")
    failed_logs = [
        'sorry, some errors happend',
    ]
    template='html'
    for host in settings.hosts:
        conn = Connection(host)
        with conn.cd(settings.work_dir):
            logger.info(f'composing {host}')
            res = conn.put(f'docker-compose.{host}.yml', os.path.join(settings.work_dir, 'docker-compose.yml'))
            try:
                conn.run('docker-compose down --remove-orphans')
            except Exception as e:
                logger.warn(f"fail to stop containers for {e} at {host}")
                failed_logs.append(f"{host} fail for {e}")
            try:
                conn.run('COMPOSE_HTTP_TIMEOUT=120 docker-compose up -d --remove-orphans')
            except Exception as e:
                logger.warn(f"fail to start containers for {e} at {host}")
                failed_logs.append(f"{host} fail for {e}")
    body = 'everything is ok'
    if len(failed_logs)>1:
        body = "\n".join(failed_logs)
        template = 'markdown'
    notify(title=f"{settings.name} service compose done", body=body, template='html')
    logging.info("service compose end")

@task
def test(c):
    logger.info("node test begin")
    monitor_endpoints = json.load(open('monitor_endpoints.json'))
    offline_endpoints = []
    for endpoint in monitor_endpoints:
        logger.info(f"checking {endpoint['name']}")
        proxyOnline = isProxyOk(endpoint['http'])
        translatorOnline = isTranslateServiceOnline(endpoint['service'])
        logger.info(f'translate online: {showBool(translatorOnline)} proxy online: {showBool(proxyOnline)}')
        if not translatorOnline or not proxyOnline:
            logger.info(f"offline endpoint: {endpoint['name']}")
            offline_endpoints.append(endpoint)
    if len(offline_endpoints):
        logger.info(f'{len(offline_endpoints)} node offline')
        for offline_endpoint in offline_endpoints:
            logger.info(f"disable node: {offline_endpoint['name']}")
            logger.debug(f"disable now: {offline_endpoint['stop']}")
            subprocess.check_output(shlex.split(offline_endpoint['stop']))
        remains_cnt =  len(monitor_endpoints) - len(offline_endpoints)
        content = "\n".join([
            f'### 部分节点有问题，已经禁用',
            f'剩余 {remains_cnt} 节点在线',
            f'#### 问题节点列表',
            markdownTable(offline_endpoints, 'name', 'http', 'service'),
        ])
        notify(title=f'{settings.name}翻译用代理检查完毕', body=content, template='markdown')
    else:
        logger.info('all nodes online')
        notify(title=f'{settings.name}翻译用代理检查完毕', body='所有节点完好', template='html')
    logger.info("node test end")
