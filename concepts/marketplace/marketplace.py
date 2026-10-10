from dotenv import load_dotenv
import json
import os
import sqlite3

from openai import OpenAI
import gradio as gr

load_dotenv()

gemini = OpenAI(
    api_key=os.environ["GOOGLE_API_KEY"],
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)

gemini_model = "gemini-3.5-flash-lite"

ollama = OpenAI(
    api_key="ollama",
    base_url="http://localhost:11434/v1",
)

ollama_model = "gpt-oss"

client = gemini
model = gemini_model

database_file = "concepts/marketplace.db"


def create_products_table():
    conn = sqlite3.connect(database_file)
    with conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def get_products_by_price_range(min_price, max_price):
    conn = sqlite3.connect(database_file)
    with conn:
        cursor = conn.execute(
            """
            SELECT * FROM products
            WHERE price BETWEEN ? AND ?
            """,
            (min_price, max_price),
        )
        return cursor.fetchall()


def get_products_by_category(category):
    conn = sqlite3.connect(database_file)
    with conn:
        cursor = conn.execute(
            """
            SELECT * FROM products
            WHERE category = ?
            """,
            (category,),
        )
        return cursor.fetchall()


def get_product_by_id(product_id):
    conn = sqlite3.connect(database_file)
    with conn:
        cursor = conn.execute(
            """
            SELECT * FROM products
            WHERE id = ?
            """,
            (product_id,),
        )
        return cursor.fetchone()


def get_all_products():
    conn = sqlite3.connect(database_file)
    with conn:
        cursor = conn.execute("SELECT * FROM products")
        return cursor.fetchall()


def update_product(product_id, name=None, category=None, description=None, price=None):
    conn = sqlite3.connect(database_file)
    with conn:
        product = get_product_by_id(product_id)
        if not product:
            return f"Product with ID {product_id} not found."

        updated_name = name if name is not None else product[1]
        updated_category = category if category is not None else product[2]
        updated_description = description if description is not None else product[3]
        updated_price = price if price is not None else product[4]

        conn.execute(
            """
            UPDATE products
            SET name = ?, category = ?, description = ?, price = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (updated_name, updated_category, updated_description, updated_price, product_id),
        )

        conn.commit()

        return get_product_by_id(product_id)


def insert_product(name, category, description, price):
    conn = sqlite3.connect(database_file)
    with conn:
        cursor = conn.execute(
            """
            INSERT INTO products (name, category, description, price)
            VALUES (?, ?, ?, ?)
            """,
            (name, category, description, price),
        )
        product_id = cursor.lastrowid
        conn.commit()

    return get_product_by_id(product_id)

def get_all_categories():
    conn = sqlite3.connect(database_file)
    with conn:
        cursor = conn.execute(
            """
            SELECT DISTINCT category FROM products
            """
        )
        return [row[0] for row in cursor.fetchall()]


SYSTEM_PROMPT = """
Você é um assistente útil que fornece informações sobre produtos em um mercado.
"""


def handle_tool_calls(message):
    responses = []
    for toolcall in message.tool_calls or []:
        tool_name = toolcall.function.name
        tool_args = json.loads(toolcall.function.arguments)

        if tool_name not in tools_dict:
            responses.append(
                {
                    "role": "tool",
                    "tool_call_id": toolcall.id,
                    "content": f"Tool '{tool_name}' not found.",
                }
            )
            continue

        tool_result = tools_dict[tool_name](**tool_args)
        responses.append(
            {
                "role": "tool",
                "tool_call_id": toolcall.id,
                "content": str(tool_result),
            }
        )

    return responses


def chat(message, history, model=model, client=client):
    history = [{"role": h["role"], "content": h["content"]} for h in history]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": message}]
    response = client.chat.completions.create(model=model, messages=messages, tools=tools)

    while response.choices[0].finish_reason == "tool_calls":
        current_message = response.choices[0].message
        tool_responses = handle_tool_calls(current_message)

        messages.append(current_message)
        messages.extend(tool_responses)

        response = client.chat.completions.create(model=model, messages=messages, tools=tools)

    return response.choices[0].message.content


def update_product_tool(product_id, name=None, category=None, description=None, price=None):
    update_product(product_id, name, category, description, price)
    return f"Product with ID {product_id} has been updated."


def insert_product_tool(name, category, description, price):
    result = insert_product(name, category, description, price)
    return f"Product '{name}' has been inserted with ID {result[0]}."


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_products_by_price_range",
            "description": "Retrieve products within a specified price range.",
            "parameters": {
                "type": "object",
                "properties": {
                    "min_price": {"type": "number", "description": "Minimum price"},
                    "max_price": {"type": "number", "description": "Maximum price"},
                },
                "required": ["min_price", "max_price"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_products_by_category",
            "description": "Retrieve products by category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "Product category"},
                },
                "required": ["category"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_by_id",
            "description": "Retrieve a product by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID"},
                },
                "required": ["product_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_products",
            "description": "Retrieve all products in the database.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_product_tool",
            "description": "Update a product's details by its ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_id": {"type": "integer", "description": "Product ID"},
                    "name": {"type": "string", "description": "New product name"},
                    "category": {"type": "string", "description": "New product category"},
                    "description": {"type": "string", "description": "New product description"},
                    "price": {"type": "number", "description": "New product price"},
                },
                "required": ["product_id"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "insert_product_tool",
            "description": "Insert a new product into the database.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Product name"},
                    "category": {"type": "string", "description": "Product category"},
                    "description": {"type": "string", "description": "Product description"},
                    "price": {"type": "number", "description": "Product price"},
                },
                "required": ["name", "category", "description", "price"],
                "additionalProperties": False,
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_categories",
            "description": "Retrieve all unique product categories.",
            "parameters": {
                "type": "object",
                "properties": {},
                "additionalProperties": False,
            },
        },
    }
]

tools_dict = {
    "get_products_by_price_range": get_products_by_price_range,
    "get_products_by_category": get_products_by_category,
    "get_product_by_id": get_product_by_id,
    "get_all_products": get_all_products,
    "update_product_tool": update_product_tool,
    "insert_product_tool": insert_product_tool,
    "get_all_categories": get_all_categories,
}

create_products_table()


if __name__ == "__main__":
    gr.ChatInterface(
        fn=chat,
        title="Marketplace Updater",
        description="Pergunte sobre os produtos do estoque.",
    ).launch(share=True, inbrowser=True)