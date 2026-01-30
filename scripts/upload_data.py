
import asyncio
import json
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from config.database import Base
from models.category import Category
from models.product import Product
from repositories.category_repository import CategoryRepository
from repositories.product_repository import ProductRepository
from services.category_service import CategoryService
from services.product_service import ProductService
from schemas.category_schema import CategoryCreate
from schemas.product_schema import ProductCreate

async def upload_data():
    """
    Connects to the database and uploads categories and products from JSON files.
    """
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        print("Error: DATABASE_URL environment variable not set.")
        print("Please create a .env file with DATABASE_URL=<your-render-db-url>")
        return

    print("Connecting to the database...")
    engine = create_async_engine(database_url)
    AsyncSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

    async with AsyncSessionLocal() as db:
        print("Connection successful.")
        
        # Instantiate repositories and services
        category_repo = CategoryRepository(db)
        product_repo = ProductRepository(db)
        
        # The services require a repository instance
        category_service = CategoryService(category_repo)
        product_service = ProductService(product_repo)

        # --- Upload Categories ---
        print("\nUploading categories...")
        try:
            with open("categories.json", "r") as f:
                categories_data = json.load(f)
        except FileNotFoundError:
            print("Error: categories.json not found in the project root.")
            return

        for cat_data in categories_data:
            existing_category = await category_repo.find_by_name(cat_data["name"])
            if existing_category:
                print(f"Category '{cat_data['name']}' already exists. Skipping.")
            else:
                category_create = CategoryCreate(name=cat_data["name"])
                await category_service.create(category_create)
                print(f"Successfully created category: {cat_data['name']}")

        # --- Upload Products ---
        print("\nUploading products...")
        try:
            with open("stock.json", "r") as f:
                products_data = json.load(f)
        except FileNotFoundError:
            print("Error: stock.json not found in the project root.")
            return
            
        for prod_data in products_data:
            existing_product = await product_repo.find_by_name(prod_data["name"])
            if existing_product:
                print(f"Product '{prod_data['name']}' already exists. Skipping.")
            else:
                # Find the corresponding category from the database to ensure FK consistency
                category = await category_repo.find_by_name(categories_data[prod_data["category_id"] - 1]["name"])
                if not category:
                    print(f"Error: Could not find category for product '{prod_data['name']}'. Make sure categories are loaded correctly.")
                    continue

                product_create = ProductCreate(
                    name=prod_data["name"],
                    price=prod_data["price"],
                    stock=prod_data["stock"],
                    category_id=category.id, # Use the ID from the database
                    description=prod_data.get("description")
                )
                await product_service.create(product_create)
                print(f"Successfully created product: {prod_data['name']}")
    
    print("\nData upload process finished.")

if __name__ == "__main__":
    asyncio.run(upload_data())
