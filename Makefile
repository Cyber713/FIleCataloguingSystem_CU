all: install

install:
	pip install --upgrade pip
	pip install pymysql
	pip install flet
	pip install flet-desktop
	pip install flet-lottie
	pip install cryptography
	@echo "Installation completed successfully!"

run3:
	python3 src/main.py

run:
	python src/main.py


