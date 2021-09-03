up:
	docker-compose up -d
build:
	docker-compose build
build-single:
	docker build -t wallkiller:latest .
push-single: build-single
	docker push wallkiller:latest
test:
	docker-compose exec walker ./test.sh

# auto_ali:
# 	ssh aliwa mkdir -p /home/osint/wall/app/data
# 	scp ytoo_updater aliwa:/home/osint/wall/
# 	scp settings.ali.py aliwa:/home/osint/wall/settings.py
# 	scp fabfile.py aliwa:/home/osint/wall/fabfile.py
# 	ssh aliwa 'pip3 install pip -U'
# 	ssh aliwa 'pip3 install fabric jinja2'
auto_office:
	ssh officewa mkdir -p /home/osint/wall/app/data
	scp ytoo_updater officewa:/home/osint/wall/
	scp settings.office.py officewa:/home/osint/wall/settings.py
	scp fabfile.py officewa:/home/osint/wall/fabfile.py
	ssh officewa 'pip3 install pip -U'
	ssh officewa 'pip3 install fabric jinja2'
update_office: auto_office
	ssh officewa 'cd /home/osint/wall/ && fab update'
translator:
	(cd app && make build-translator push-translator)
	fab sync-images
debug:
	INVOKE_DEBUG=true fab check