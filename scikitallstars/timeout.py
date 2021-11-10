from functools import wraps


def on_timeout(limit, handler, hint=None):
    def notify_handler(signum, frame):
        handler(
            "'%s' terminated since it did not finish in %d second(s)." % (hint, limit)
        )

    def __decorator(function):
        def __wrapper(*args, **kwargs):
            import signal

            signal.signal(signal.SIGALRM, notify_handler)
            signal.alarm(limit)
            result = function(*args, **kwargs)
            signal.alarm(0)
            return result

        return wraps(function)(__wrapper)

    return __decorator

def handler_func(msg):
    print(msg)
