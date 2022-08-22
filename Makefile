install-deps:
	-python3 setup.py install

install-dev:
	-pip3 install -e .[dev]

build-dist:
	-pyinstaller cli.py --name stackmate

lint:
	-find . -name '*.py' | xargs pylint -E -j 5

run-tests:
	-py.test

docker-images:
	- docker build --rm -t stackmate/stackmate-deployer:0.1 -f dockerfiles/deployer.dockerfile . \
		&& cd dockerfiles \
		&& docker build --rm -t stackmate/stackmate-base:0.2 -f base-ansible-ubuntu-20.04.dockerfile .

push-images:
	- docker push stackmate/stackmate-base:0.2
	- docker push stackmate/stackmate-deployer:0.1
