"""ragkit - the SOC Copilot RAG assistant for AI Bootcamp Lab 4.

Standard library only. Modules:
  config      paths, model names, policy toggles
  documents   load Markdown, split into labelled chunks
  embeddings  text -> vectors (Ollama or built-in TF-IDF)
  store       JSON vector store with optional permission filter
  identity    users, tokens, groups
  cache       answer cache
  llm         Ollama chat client
  assistant   the RAG pipeline
  pipeline    explore the indexing pipeline stage by stage
  ingest / ask / attack / policy / doctor / reset   command-line entry points
"""
