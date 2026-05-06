import asyncio
import sys

sys.path.insert(0, 'backend')

from app.core.database import connect_db, close_db
from app.core.database import get_db
from app.core.fiscal import current_fiscal_year_label
from app.services.rag_service import rag_service


async def main():
    await connect_db()
    fiscal_year = sys.argv[1] if len(sys.argv) > 1 else current_fiscal_year_label()
    result = await rag_service.train_fiscal_year(get_db(), fiscal_year)
    print(result)
    await close_db()


if __name__ == '__main__':
    asyncio.run(main())
