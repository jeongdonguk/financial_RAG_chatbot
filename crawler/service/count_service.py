import db.crud.crud as crud

async def get_count(db, model):
    return await crud.get_count(db, model)