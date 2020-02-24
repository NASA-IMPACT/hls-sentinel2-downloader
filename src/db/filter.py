from sqlalchemy import and_


class Filter:
    def __init__(self, table, params):
        self.table = table
        self.params = params

    def _handle_clause(self, key, value):
        field = self.table.c[key]
        if '.' in key:
            key, op = key.split('.')
            if op == 'ge':
                return field > value
            if op == 'le':
                return field < value
            if op == 'gte':
                return field >= value
            if op == 'lte':
                return field <= value
        return field == value

    def compile(self):
        params = self.params

        where_clauses = [
            self._handle_clause(key, value)
            for (key, value) in params.items()
        ]

        if len(where_clauses) == 1:
            return where_clauses[0]
        else:
            return and_(*where_clauses)
