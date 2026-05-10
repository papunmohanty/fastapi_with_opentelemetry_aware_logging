"""Simple dice roll FastAPI app using a custom OpenTelemetry-aware logger.

This application uses ``otel_logger.get_logger`` to create a single logger
instance. The custom logger is intentionally designed to let application code
use familiar methods like ``logger.info()`` and ``logger.error()`` without
manually managing OpenTelemetry spans.

Examples:

    from otel_logger import get_logger

    logger = get_logger("diceroller")
    logger.info("Starting dice roll")

    result = 4
    logger.info(
        "Rolled dice value %s",
        result,
        span_name="roll",
        span_attributes={"roll.value": result},
    )

    try:
        raise ValueError("unexpected")
    except Exception as exc:
        logger.error("Error during execution: %s", exc)
        logger.exception("Caught exception during dice roll")

By default, ``get_logger`` does not start spans for every log call. To create
spans automatically for every log level, use ``auto_start_spans=True``:

    logger = get_logger("diceroller", auto_start_spans=True)
    logger.warning("This log will also create a warning span")
"""

from fastapi import FastAPI
from random import randint
import copy

from otel_logger import get_logger

logger = get_logger("diceroller-service")

# Initialize FastAPI app
app = FastAPI()

dice_roll = [[], [], []]


@app.get("/rolldice")
async def roll_dice():
    count = 0

    # Roll dice and distribute result into three separate lists
    while count < 15:
        if count < 5:
            dice_roll[0].append(roll())  # Append to the first list
        elif count < 10:
            dice_roll[1].append(roll())  # Append to the second list
        else:
            dice_roll[2].append(roll())  # Append to the third list
        count += 1

    # Store the result to return
    result = copy.deepcopy(dice_roll)

    # Clear the dice_roll lists for the next function call AFTER returning the result
    dice_roll[0].clear()
    dice_roll[1].clear()
    dice_roll[2].clear()

    # Return the result
    return {"dice_rolls": result}


def roll():
    result = randint(1, 6)
    logger.info(
        f"Rolled dice value {result}",
        span_name="roll",
        span_attributes={"roll.value": result},
    )
    return result
