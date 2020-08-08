# RoboCup_Simulator

![Python package](https://github.com/MelbourneHighSchool/RoboCup_Simulator/workflows/Python%20package/badge.svg)

If you want to make changes to this repository, please complete https://forms.office.com/Pages/ResponsePage.aspx?id=h42eJG9AWU2cviWaMsGmARjoL0O6BYlNl-nkrUuf9BZUOEhIVkJPTkhXMTgyRUZQVFRKOUgxUTZPMi4u. If you just want to run the simulator, don't worry about it.

## Setup
To get this project running, you need to install some packages. Assuming you have python installed, run:

    python -m pip install -r requirements.txt

If this gives errors with pygame, you can check this: https://www.pygame.org/wiki/GettingStarted

## Running

### Simulation

To run the simulation, use the command:

    python sim.py robots/bot.yaml

This should load up the soccer field with a bot that does nothing. If you want to have a play around you can instead use `robots/controllable.yaml`. Use the arrow keys to move, and press 'r' to rotate. (The controllable example will NOT work with ev3 scripts that control the motors!)

You can also load up multiple robots by simply specifying the paths of each bot (separated by spaces). If you want to change the sensor locations/colour and what not, try making your own bot based on `robots/bot.yaml`.

### EV3 Scripts

To attach an ev3 script, use the following command.

    python attach.py ev3code.py robot-id

Replacing `ev3code.py` with the name of your code, and `robot-id` with the Robot's ID (Leaving this blank will default to the first robot). Right clicking a robot will copy it's ID to the clipboard, so you can paste it into the command.

## Problems

Find any issues with the simulator? Feel free to make an issue here: https://github.com/MelbourneHighSchool/RoboCup_Simulator/issues
