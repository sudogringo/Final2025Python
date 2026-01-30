
import asyncio
import json
import os
import sys
from dotenv import load_dotenv
import httpx

# --- Configuration ---
# Load environment variables from .env file
load_dotenv()
API_BASE_URL = os.getenv("API_BASE_URL")

async def upload_data_via_api():
    """
    Uploads categories and products to the database via the API endpoints.
    """
    if not API_BASE_URL:
        print("Error: API_BASE_URL environment variable not set.")
        print("Please create or update your .env file with API_BASE_URL=<your-render-app-url>")
        return

    async with httpx.AsyncClient(base_url=API_BASE_URL) as client:
        # --- Health Check ---
        try:
            print(f"Checking API health at {API_BASE_URL}/health_check/...")
            health_response = await client.get("/health_check/")
            health_response.raise_for_status()
            print("API is healthy. Proceeding with data upload.")
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"Error: API health check failed: {e}")
            print("Please ensure your Render application is running and the API_BASE_URL is correct.")
            return

        # --- Upload Categories ---
        print("\n--- Uploading Categories ---")
        try:
            with open("categories.json", "r") as f:
                categories_data = json.load(f)
        except FileNotFoundError:
            print("Error: categories.json not found. Please ensure it's in the project root.")
            return

        for cat_data in categories_data:
            payload = {"name": cat_data["name"]}
            try:
                # Check if category already exists by trying to create it
                response = await client.post("/categories/", json=payload)
                if response.status_code == 409: # Conflict
                     print(f"Category '{cat_data['name']}' already exists. Skipping.")
                elif response.status_code == 201: # Created
                    print(f"Successfully created category: {cat_data['name']}")
                else:
                    response.raise_for_status() # Raise exception for other errors
            except httpx.HTTPStatusError as e:
                print(f"Error creating category '{cat_data['name']}': {e.response.text}")
        
        # --- Fetch Categories to Map Names to IDs ---
        print("\nFetching all categories to map names to IDs for products...")
        try:
            response = await client.get("/categories/")
            response.raise_for_status()
            all_categories = response.json()
            # The response is a list of dicts, e.g. [{'id': 1, 'name': 'Celulares'}, ...]
            category_name_to_id = {cat["name"]: cat["id_key"] for cat in all_categories}
            print("Category mapping successful.")
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            print(f"Fatal Error: Could not fetch categories from the API: {e}")
            return


        # --- Upload Products ---
        print("\n--- Uploading Products ---")
        try:
            with open("stock.json", "r") as f:
                products_data = json.load(f)
        except FileNotFoundError:
            print("Error: stock.json not found. Please ensure it's in the project root.")
            return
            
        # Create a mapping from old category id_key to category name
        category_id_key_to_name = {cat["id_key"]: cat["name"] for cat in categories_data}

        for prod_data in products_data:
            category_name = category_id_key_to_name.get(prod_data["category_id"])
            if not category_name:
                print(f"Warning: Could not find a category name for product '{prod_data['name']}' with old id_key {prod_data['category_id']}. Skipping.")
                continue

            category_db_id = category_name_to_id.get(category_name)
            if not category_db_id:
                print(f"Warning: Could not find a database ID for category '{category_name}'. Did it fail to create? Skipping product '{prod_data['name']}'.")
                continue

            product_payload = {
                "name": prod_data["name"],
                "price": prod_data["price"],
                "stock": prod_data["stock"],
                "category_id": category_db_id,
                "description": prod_data.get("description"),
                "image": prod_data.get("image")
            }

            try:
                response = await client.post("/products/", json=product_payload)
                if response.status_code == 409: # Conflict
                    print(f"Product '{prod_data['name']}' already exists. Skipping.")
                elif response.status_code == 201: # Created
                    print(f"Successfully created product: {prod_data['name']}")
                else:
                    response.raise_for_status()
            except httpx.HTTPStatusError as e:
                print(f"Error creating product '{prod_data['name']}': {e.response.text}")

    print("\nData upload process finished.")

if __name__ == "__main__":
    # Check if httpx is installed
    try:
        import httpx
    except ImportError:
        print("Error: 'httpx' library is not installed.")
        print("Please install it by running: pip install httpx")
        sys.exit(1)
        
    asyncio.run(upload_data_via_api())
