import logging
import time


def time_it(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        execution_time = end_time - start_time
        logging.info(
            f"Function '{func.__name__}' executed in {execution_time:.4f} seconds"
        )
        print(f"Function '{func.__name__}' executed in {execution_time:.4f} seconds")
        return result

    return wrapper


def indian_number_format(number):
    """
    Format a number with thousand separators in the Indian numbering system.

    Args:
    number (int, float, or str): The number to be formatted.

    Returns:
    str: The number formatted with Indian-style thousand separators.
    """
    # Convert to float if input is a string
    if isinstance(number, str):
        number = float(number)

    # Split the number into integer and decimal parts
    if isinstance(number, float):
        integer_part, decimal_part = str(number).split(".")
    else:
        integer_part, decimal_part = str(number), ""

    # Reverse the integer part string
    integer_part = integer_part[::-1]

    # Add separators
    groups = []
    groups.append(integer_part[:3])
    integer_part = integer_part[3:]
    while integer_part:
        groups.append(integer_part[:2])
        integer_part = integer_part[2:]

    # Join the groups and reverse back
    formatted_integer = ",".join(groups)[::-1]

    return formatted_integer

