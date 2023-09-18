from functions import VariableMonitor
from functions_test2 import click_click


# Observer function to react to variable changes
def on_variable_change(new_value):
    print("Variable has changed to:", new_value)
    # Perform actions based on the variable change
    # Add your logic here


# Create an instance of VariableMonitor
variable_monitor = VariableMonitor()

# Add the observer
variable_monitor.add_observer(on_variable_change)

if __name__ == "__main__":
    # Modify the variable in functions.py to simulate a change
    variable_monitor.value = 10

    # Modify the variable again to simulate another change
    variable_monitor.value = 20
    click_click(variable_monitor)
