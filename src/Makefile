.PHONY: install clean build

install:
	pip install -r requirements.txt --target ./.target

clean:
	rm -rf ./.target

build: install
	cp index.py ./.target
