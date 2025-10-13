import asyncio


# Async wrappers for PyMongo sync methods using asyncio executor
async def async_insert_one(collection, document):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: collection.insert_one(document))


async def async_find_one(collection, filter):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, lambda: collection.find_one(filter))