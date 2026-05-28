import asyncio
import sys
sys.path.insert(0, ".")

from backend.database import get_db
from backend.routers.applications import list_applications

async def main():
    try:
        db_gen = get_db()
        db = await anext(db_gen)
        
        apps = await list_applications("demo-user-1", db=db)
        print("Apps:", apps)
    except Exception as e:
        import traceback
        traceback.print_exc()

asyncio.run(main())
