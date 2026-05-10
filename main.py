from fastapi import FastAPI
from random import randint
import copy

from opentelemetry import trace

tracer = trace.get_tracer("diceroller.tracer")


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

    # Clear the dice_roll lists for the  next function call AFTER returning the result
    dice_roll[0].clear()
    dice_roll[1].clear()
    dice_roll[2].clear()

    # Return the result
    return {"dice_rolls": result}


def roll():
    with tracer.start_as_current_span("roll") as roll_span:
        result = randint(1, 6)
        roll_span.set_attribute("roll.value", result)
        return result
