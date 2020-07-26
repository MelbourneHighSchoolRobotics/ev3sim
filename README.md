# RoboCup_Simulator

![Python package](https://github.com/MelbourneHighSchool/RoboCup_Simulator/workflows/Python%20package/badge.svg)

To contribute to this project, please complete https://forms.office.com/Pages/ResponsePage.aspx?id=h42eJG9AWU2cviWaMsGmARjoL0O6BYlNl-nkrUuf9BZUOEhIVkJPTkhXMTgyRUZQVFRKOUgxUTZPMi4u.

## Running

In general you can run the script as follows:

    python run.py --preset=preset_file.yaml robot1.yaml robot2.yaml

Where `preset_file.yaml` is the path to a simulation preset, and `robot1.yaml`, ... and robot definitions. `--preset` will default to the soccer simulation, requiring 2/4 robots to be spawned.

For more information try running `python run.py --help`

If you want to try a few demos of what the simulation is capable of, then try the following:

    python .\run.py --preset=presets/field_no_teams.yaml robot/examples/controllable.yaml

Use Arrow keys to control the above bot.

    python run.py --preset=presets/field_no_teams.yaml robot/examples/motor_example.yaml

    python run.py --preset=presets/field_no_teams.yaml robot/examples/ultrasonic_example.yaml    
