# LLM Automation Concepts

This repository is a collection of small experiments and proofs of concept for building automation with large language models (LLMs). The current concept is a conversational marketplace assistant that demonstrates model tool calling against a SQLite product catalog.

## Current concept: Marketplace updater

The experiment lives in [`concepts/marketplace/marketplace-updater.ipynb`](concepts/marketplace/marketplace-updater.ipynb). It uses a Gradio chat interface so a user can ask questions about products in Portuguese or request changes to product details. The notebook configures either the Gemini API (through its OpenAI-compatible endpoint) or a local Ollama server, and uses the OpenAI Python client for both.

The catalog is stored in [`concepts/marketplace/marketplace.db`](concepts/marketplace/marketplace.db). Its `products` table contains an ID, name, category, description, price, and creation/update timestamps. The notebook seeds sample products and defines database operations to:

- list all products;
- find products by category, ID, or price range;
- update a product's name, category, description, or price by ID.

These operations are exposed to the model as function tools. The model can request a lookup or update, the notebook runs the corresponding SQLite operation, and its result is returned to the model for a natural-language response. Example prompts in the notebook include finding products in a price range and changing a product's price.

## Running the experiment

Use Python 3.12 or newer and install the project dependencies from `pyproject.toml` (or `requirements.txt`). For Gemini, set `GOOGLE_API_KEY` in a local `.env` file. For Ollama, run the local server and make the configured model available. The notebook currently selects Gemini by default; change its `client` and `model` assignments to switch providers. Open and run the notebook cells in order to start the Gradio chat interface.

## Scope

This is an exploratory notebook rather than a production application. It uses a local sample database, and the current tool definitions and flow are intended to demonstrate LLM function calling and database-backed updates. Review the notebook before using it with real catalog data or exposing it beyond a local experiment.
