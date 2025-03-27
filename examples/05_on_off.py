from stateless import StateMachine

# --- States (using strings) ---
ON = "On"
OFF = "Off"

# --- Triggers (using characters) ---
TOGGLE = " "

# --- State Machine Setup ---
# Instantiate a new state machine in the 'OFF' state
on_off_switch = StateMachine[str, str](OFF)  # Specify types as str, str

# Configure states
on_off_switch.configure(OFF).permit(TOGGLE, ON)
on_off_switch.configure(ON).permit(TOGGLE, OFF)

# --- Usage ---
print("Press <space> to toggle the switch. Any other key will exit.")

while True:
    print(f"Switch is in state: {on_off_switch.state}")
    # In a real console app, you'd read a key press here.
    # For this example, we'll simulate toggling.
    # Simulating a key press:
    pressed = input("Press space to toggle, other key to exit: ")

    # Check if user wants to exit
    if pressed != TOGGLE:
        break

    # Use the Fire method with the trigger as payload
    try:
        on_off_switch.fire(pressed)
    except Exception as e:
        print(f"Error: {e}")  # Should not happen in this simple config

print("Exiting.")
