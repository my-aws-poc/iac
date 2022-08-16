import time


def blocked_until(executor, condition, sleep_time=10, timeout=300):
    """
    Block until the condition return True
    :param executor: t function
    :param condition: t -> bool
    :param sleep_time: int
    :param timeout: int
    :return: t
    """
    start = time.time()
    while time.time() - start < timeout:
        res = executor()
        if condition(res):
            return res
        time.sleep(sleep_time)
    raise Exception('BlockedUntil timeout.')
