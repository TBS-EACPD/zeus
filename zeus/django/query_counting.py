from django.db import connection


class QueryCollector:
    """
        usage:

        from django.db import connection
        qc = QueryCollector()
        with connection.execute_wrapper(qc):
            do_queries()
        # Now we can print the log.
        print(qc.queries)
    """

    def __init__(self):
        self.queries = []

    def __call__(self, execute, sql, params, many, context):
        current_query = {"sql": sql, "params": params, "many": many}
        try:
            result = execute(sql, params, many, context)
        except Exception as e:
            current_query["status"] = "error"
            current_query["exception"] = e
            raise
        else:
            current_query["status"] = "ok"
            return result
        finally:
            self.queries.append(current_query)


class QueryCounter:
    """
        usage: 
            with QueryCounter() as qc:
                # arbitrary code that execs sql 
            
            assert( qc.count < 10 )
    """

    def __init__(self):
        self.query_collector = QueryCollector()
        self.connection_ctx_manager = connection.execute_wrapper(self.query_collector)

    def __enter__(self):
        self.connection_ctx_manager.__enter__()

    def __exit__(self, *excp):
        self.connection_ctx_manager.__exit__(*excp)
        self.count = len(self.query_collector.queries)


class MaxQueryCountExceededError(Exception):
    pass


class assert_max_queries:
    """
        usage:

        with assert_max_queries(n):
            ... code_that_should_make_up_to_n_queries
    """

    def __init__(self, max_queries: int):
        self.qc = QueryCounter()
        self.max_queries = max_queries

    def __enter__(self):
        self.qc.__enter__()

    def __exit__(self, *excp):
        self.qc.__exit__(*excp)
        if self.qc.count > self.max_queries:
            raise MaxQueryCountExceededError(
                f"Expected a maximum of {self.max_queries} but got {self.qc.count} queries"
            )
