class NoOpTracer:
    def capture_lambda_handler(self, func=None, **kwargs):
        if func is None:

            def wrapper(f):
                return f

            return wrapper
        return func

    def capture_method(self, func=None, **kwargs):
        if func is None:

            def wrapper(f):
                return f

            return wrapper
        return func

    def put_annotation(self, key, value):
        pass

    def put_metadata(self, key, value):
        pass
