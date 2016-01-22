import random
import string


def generate_random_client_id(len):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(23-len))
