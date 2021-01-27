up:
	docker-compose up -d
build:
	docker-compose build
build-single:
	docker build -t wallkiller:latest .
test:
	docker-compose exec walker ./test.sh