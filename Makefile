VENV_DIR := venv
PYTHON := python3
PIP := $(VENV_DIR)/bin/pip

.PHONY: all install clean

all: install

$(VENV_DIR)/bin/activate:
	$(PYTHON) -m venv $(VENV_DIR)

install: $(VENV_DIR)/bin/activate
	$(PIP) install --upgrade pip
	$(PIP) install pymysql flet flet-desktop flet-lottie cryptography

clean:
	rm -rf $(VENV_DIR)
