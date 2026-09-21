# Comandos do dia a dia - ver README.md pro contexto (endpoints, exemplos
# de curl) e docs/ARCHITECTURE.md pras camadas. `make` ou `make help`
# lista tudo isto na tela.

PYTHON := .venv/Scripts/python.exe

.PHONY: help venv install run lint typecheck test indexar sincronizar-imagens clean

help:
	@echo "Setup"
	@echo "  make venv                  cria .venv/"
	@echo "  make install               pip install -r requirements.txt"
	@echo ""
	@echo "Rodar"
	@echo "  make run                   uvicorn app.main:app --reload - http://localhost:8000/docs"
	@echo ""
	@echo "Qualidade (mesmos comandos do README)"
	@echo "  make lint                  ruff check app tests"
	@echo "  make typecheck             mypy app"
	@echo "  make test                  pytest -q --cov (fail_under=70)"
	@echo ""
	@echo "Scripts utilitários (precisam de DATABASE_URL/VOYAGE_API_KEY etc no .env)"
	@echo "  make indexar               scripts/indexar_acervo.py - popula o índice do chatbot"
	@echo "  make sincronizar-imagens   scripts/sincronizar_imagens.py --dry-run"
	@echo ""
	@echo "make clean                 limpa __pycache__, .pytest_cache, .mypy_cache, .ruff_cache"

venv:
	python -m venv .venv

install:
	$(PYTHON) -m pip install -r requirements.txt

run:
	$(PYTHON) -m uvicorn app.main:app --reload

lint:
	$(PYTHON) -m ruff check app tests

typecheck:
	$(PYTHON) -m mypy app

test:
	$(PYTHON) -m pytest -q --cov

indexar:
	$(PYTHON) -m scripts.indexar_acervo

sincronizar-imagens:
	$(PYTHON) -m scripts.sincronizar_imagens --dry-run

clean:
	rm -rf __pycache__ .pytest_cache .mypy_cache .ruff_cache
