from io import StringIO
from csv import DictReader
from sqlalchemy.dialects.postgresql import insert
from filter import Filter


empty_params = {}


def parse_order_by(table, order_by):
    if isinstance(order_by, str):
        return table.c[order_by].asc()

    result = []
    for ordering in order_by:
        if isinstance(ordering, str):
            result.append(table.c[ordering].asc())
        else:
            field, order = ordering
            result.append(getattr(table.c[field], order)())
    return result


# TODO: Wrap the whole process in transaction somehow
class Serializer:
    def __init__(self, connection, table):
        self.table = table
        self.conn = connection

    def execute(self, query, *args, **kwargs):
        return self.conn.execute(query, *args, **kwargs)

    def first(self, params=empty_params, order_by=None):
        query = self.table.select()
        if order_by is not None:
            query = query.order_by(*parse_order_by(self.table, order_by))
        if len(params) > 0:
            query = query.where(Filter(self.table, params).compile())
        result = self.execute(query)
        row = result.first()
        return row and dict(row.items())

    def get_all(self, params=empty_params, order_by=None):
        query = self.table.select()
        if order_by is not None:
            query = query.order_by(*parse_order_by(self.table, order_by))
        if len(params) > 0:
            query = query.where(Filter(self.table, params).compile())
        result = self.execute(query)
        return list(dict(r.items()) for r in result)

    def get(self, id):
        pk_name = self.table.primary_key.columns.values()[0].name
        query = self.table.select().where(self.table.c[pk_name] == id)
        result = self.execute(query)
        r = next(result, None)
        return r and dict(r.items())

    def exists(self, params):
        return self.table.exists().where(
            Filter(self.table, params).compile()
        ).scalar()

    def post(self, data):
        query = self.table.insert().values(**data)
        result = self.execute(query)
        return result.inserted_primary_key[0]
        # return self.get(result.inserted_primary_key[0])

    def put(self, id, data):
        pk_name = self.table.primary_key.columns.values()[0].name
        query = self.table.update().where(self.table.c[pk_name] == id).\
            values(**data)
        self.execute(query)
        return id
        # return self.get(id)

    def delete(self, id):
        pk_name = self.table.primary_key.columns.values()[0].name
        query = self.table.delete().where(self.table.c[pk_name] == id)
        self.execute(query)

    def post_csv(self, data):
        str_file = StringIO(data)
        reader = DictReader(str_file, delimiter=',')
        count = 0
        for row in reader:
            # Use postgresql.insert to use on_conflict_do_update
            query = insert(self.table).values(**row)
            pk_name = self.table.primary_key.columns.values()[0].name
            row.pop(pk_name)
            query = query.on_conflict_do_update(
                index_elements=[self.table.c[pk_name]],
                set_=row,
            )
            self.execute(query)
            count += 1

        return {
            'status': 'success',
            'updated_rows': count,
        }
