from api.app.reliability import run_reliability_probe


class Row:
    def __init__(self, **values):
        self.__dict__.update(values)


class Query:
    def __init__(self, rows):
        self.rows = rows

    def result(self):
        return self.rows


class FakeClient:
    def __init__(self):
        self.queries = 0
        self.inserted = []

    def query(self, _sql):
        self.queries += 1
        if self.queries == 1:
            return Query([Row(fact_rows=50000, clean_rows=14, quarantine_rows=7)])
        return Query([Row(n=1)])

    def insert_rows_json(self, table, rows):
        self.inserted.append((table, rows))
        return []


def test_reliability_probe_persists_and_verifies_receipt():
    client = FakeClient()
    result = run_reliability_probe(client)

    assert result["result"] == "SUCCESS"
    assert result["final_verification"] is True
    assert result["receipt_persisted"] is True
    assert result["checks"]["fact_rows"] == 50000
    assert len(client.inserted) == 1
