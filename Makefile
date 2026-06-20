.PHONY: install run gst clean

PYTHON ?= python3
VENV ?= .venv
PIP := $(VENV)/bin/pip
STREAMLIT := $(VENV)/bin/streamlit

install:
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

run:
	$(STREAMLIT) run app.py

gst: run

clean:
	rm -rf $(VENV) __pycache__ gst_signer/__pycache__ .streamlit
