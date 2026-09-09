"""Chatbot do acervo — RAG (Retrieval-Augmented Generation).

Fase 1: só o acervo já existente (`app/data/*.json`) entra no índice. Livros
em PDF ficam para uma fase seguinte (ver `scripts/indexar_pdf.py`, ainda não
criado).

Princípio inegociável do módulo inteiro: a resposta nunca vem do que o
modelo de linguagem "sabe" — só dos trechos recuperados do próprio acervo.
Sem trecho relevante, a resposta é "não encontrei isso no acervo", nunca uma
tentativa de ser útil inventando.
"""
