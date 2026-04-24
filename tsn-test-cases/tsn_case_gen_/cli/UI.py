import json
import tkinter as tk
from tkinter import filedialog, messagebox

def save_config():
    # Build the list of traffic types from each instance
    traffic_types = []
    for instance in traffic_instances:
        traffic_type = instance["traffic_type_var"].get()
        if traffic_type == "BEST-EFFORT":
             # Only include fields relevant to BEST-EFFORT
            traffic_types.append({
                "name": traffic_type,
                "PCP-list": list(map(int, instance["pcp_list_var"].get().split(','))),
                "number": int(instance["number_var"].get()),
                "min_packet_size": int(instance["min_packet_size_var"].get()),
                "max_packet_size": int(instance["max_packet_size_var"].get()),
                "bidirectional": instance["bidirectional_var"].get() == "True"
            })
        elif traffic_type == "AUDIO/VOICE":
            # Only include fields relevant to AUDIO/VOICE
            traffic_types.append({
                "name": traffic_type,
                "PCP-list": list(map(int, instance["pcp_list_var"].get().split(','))),
                "number": int(instance["number_var"].get()),
                "min_delay": int(instance["min_delay_var"].get()),
                "max_delay": int(instance["max_delay_var"].get()),
                "min_packet_size": int(instance["min_packet_size_var"].get()),
                "max_packet_size": int(instance["max_packet_size_var"].get()),
                "bidirectional": instance["bidirectional_var"].get() == "True"
            })
        else:
            traffic_types.append({
                "name": instance["traffic_type_var"].get(),
                "PCP-list": list(map(int, instance["pcp_list_var"].get().split(','))),
                "number": int(instance["number_var"].get()),
                "redundant_number": int(instance["redundant_number_var"].get()),
                "redundant_routes": int(instance["redundant_routes_var"].get()),
                "cycle_time": {
                    "cycle_time_units": instance["cycle_time_units_var"].get(),
                    "choose_list": True,
                    "cycle_time_list": [int(x) for x in instance["cycle_time_list_var"].get().split(',')],
                    "min_cycle_time": int(instance["min_cycle_time_var"].get()),
                    "max_cycle_time": int(instance["max_cycle_time_var"].get())
                },
                "min_delay": int(instance["min_delay_var"].get()),
                "max_delay": int(instance["max_delay_var"].get()),
                "min_packet_size": int(instance["min_packet_size_var"].get()),
                "max_packet_size": int(instance["max_packet_size_var"].get()),
                "bidirectional": instance["bidirectional_var"].get() == "True"
            })
    
    config = {
        "delay_units": delay_units_var.get(),
        "general": {
            "output_directory": output_directory_var.get(),
            "num_test_cases": int(num_test_cases_var.get()),
            "num_domains": int(num_domains_var.get()),
            "topology_size": {
                "num_switches": int(num_switches_var.get()),
                "num_end_systems": int(num_end_systems_var.get()),
                "end_systems_per_switch": [
                    int(es_per_switch_min_var.get()),
                    int(es_per_switch_max_var.get())
                ]
            },
            "cross_domain_streams": int(cross_domain_streams_var.get()),
            "test_case_naming": test_case_naming_var.get()
        },
        "network": {
            "topology_type": topology_type_var.get(),
            "parameters": parameters_var.get(),
            "default_bandwidth_mbps": int(default_bandwidth_var.get()),
            "constraints": {
                "max_path_length": int(max_path_length_var.get())
            }
        },
        "routing": {
            "consider_link_utilization": consider_link_utilization_var.get() == "True"
        },
        "domain_connections": {
            "type": domain_connection_type_var.get(),
            "connections_per_domain_pair": int(connections_per_domain_pair_var.get())
        },
        "traffic": {
            "types": traffic_types
        }
    }

    file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])
    if file_path:
        with open(file_path, "w") as file:
            json.dump(config, file, indent=2)
        messagebox.showinfo("Success", "Configuration saved successfully!")
        root.destroy()

def update_scroll_region():
    content_frame.update_idletasks()
    canvas.config(scrollregion=canvas.bbox("all"))

# List to keep track of traffic-related widgets
traffic_widgets_rest = []
traffic_widgets_best_effort = []
traffic_widgets_audio_voice = []

def create_traffic_widgets():
    # Clear existing list
    traffic_widgets_rest.clear()
    # Create widgets within the traffic_frame
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "PCP-list (comma-separated):", pcp_list_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Number:", number_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Cycle Time Units:", cycle_time_units_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Cycle Time List (comma-separated):", cycle_time_list_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Min Cycle Time:", min_cycle_time_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Max Cycle Time:", max_cycle_time_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Min Delay:", min_delay_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Max Delay:", max_delay_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Min Packet Size:", min_packet_size_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Max Packet Size:", max_packet_size_var))
    traffic_widgets_rest.append(create_label_entry_in_frame(traffic_frame, "Bidirectional:", bidirectional_var))
    
def create_Best_effort_traffic_widgets():
    # Clear existing list
    traffic_widgets_best_effort.clear()
    traffic_widgets_best_effort.append(create_label_entry_in_frame(traffic_frame, "PCP-list (comma-separated):", pcp_list_var))
    traffic_widgets_best_effort.append(create_label_entry_in_frame(traffic_frame, "Number:", number_var))
    traffic_widgets_best_effort.append(create_label_entry_in_frame(traffic_frame, "Min Packet Size:", min_packet_size_var))
    traffic_widgets_best_effort.append(create_label_entry_in_frame(traffic_frame, "Max Packet Size:", max_packet_size_var))
    traffic_widgets_best_effort.append(create_label_entry_in_frame(traffic_frame, "Bidirectional:", bidirectional_var))
    
def create_audio_voice_traffic_widgets():
    traffic_widgets_audio_voice.clear()
    traffic_widgets_audio_voice.append(create_label_entry_in_frame(traffic_frame, "PCP-list (comma-separated):", pcp_list_var))
    traffic_widgets_audio_voice.append(create_label_entry_in_frame(traffic_frame, "Number:", number_var))
    traffic_widgets_audio_voice.append(create_label_entry_in_frame(traffic_frame, "Min Delay:", min_delay_var))
    traffic_widgets_audio_voice.append(create_label_entry_in_frame(traffic_frame, "Max Delay:", max_delay_var))
    traffic_widgets_audio_voice.append(create_label_entry_in_frame(traffic_frame, "Min Packet Size:", min_packet_size_var))
    traffic_widgets_audio_voice.append(create_label_entry_in_frame(traffic_frame, "Max Packet Size:", max_packet_size_var))
    traffic_widgets_audio_voice.append(create_label_entry_in_frame(traffic_frame, "Bidirectional:", bidirectional_var))

root = tk.Tk()
root.title("Config File Editor")

# Create a canvas widget
canvas = tk.Canvas(root)
canvas.pack(side="left", fill="both", expand=True)

# Add a scrollbar linked to the canvas
scrollbar = tk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollbar.pack(side="right", fill="y")

canvas.config(yscrollcommand=scrollbar.set)

# Create a frame to hold the content, this will be placed inside the canvas
content_frame = tk.Frame(canvas)
canvas.create_window((0, 0), window=content_frame, anchor="nw")

def create_label_entry(label_text, variable):
    frame = tk.Frame(content_frame)
    frame.pack(fill="x", padx=5, pady=2)
    label = tk.Label(frame, text=label_text, width=25, anchor="w")
    label.pack(side="left")
    entry = tk.Entry(frame, textvariable=variable, width=30)
    entry.pack(side="right", fill="x", expand=True)
    return entry

# General configuration fields
delay_units_var = tk.StringVar(value="MICRO_SECOND")
create_label_entry("Delay Units:", delay_units_var)

output_directory_var = tk.StringVar(value="simulations")
create_label_entry("Output Directory:", output_directory_var)

num_test_cases_var = tk.StringVar(value="3")
create_label_entry("Number of Test Cases:", num_test_cases_var)

num_domains_var = tk.StringVar(value="1")
create_label_entry("Number of Domains:", num_domains_var)

num_switches_var = tk.StringVar(value="10")
create_label_entry("Number of Switches:", num_switches_var)

num_end_systems_var = tk.StringVar(value="20")
create_label_entry("Number of End Systems:", num_end_systems_var)

es_per_switch_min_var = tk.StringVar(value="0")
es_per_switch_max_var = tk.StringVar(value="4")
create_label_entry("End Systems per Switch (Min):", es_per_switch_min_var)
create_label_entry("End Systems per Switch (Max):", es_per_switch_max_var)

cross_domain_streams_var = tk.StringVar(value="0")
create_label_entry("Cross Domain Streams:", cross_domain_streams_var)

test_case_naming_var = tk.StringVar(value="test_case_{}")
create_label_entry("Test Case Naming:", test_case_naming_var)

topology_type_var = tk.StringVar(value="mesh_graph")
create_label_entry("Topology Type:", topology_type_var)

parameters_var = tk.StringVar(value="{'n': 4, 'm': 4 }")
create_label_entry("Parameters:", parameters_var)

default_bandwidth_var = tk.StringVar(value="1000")
create_label_entry("Default Bandwidth (Mbps):", default_bandwidth_var)

max_path_length_var = tk.StringVar(value="5")
create_label_entry("Max Path Length:", max_path_length_var)

consider_link_utilization_var = tk.StringVar(value="True")
create_label_entry("Consider Link Utilization:", consider_link_utilization_var)

domain_connection_type_var = tk.StringVar(value="line")
create_label_entry("Domain Connection Type:", domain_connection_type_var)

connections_per_domain_pair_var = tk.StringVar(value="2")
create_label_entry("Connections per Domain Pair:", connections_per_domain_pair_var)

# Traffic Configuration Fields (initially hidden)
traffic_type_var = tk.StringVar(value="Choose Traffic Type")
traffic_type_dropdown = tk.OptionMenu(content_frame, traffic_type_var, "ISOCHRONOUS", "CYCLIC-SYNCHRONOUS", "CYCLIC-ASYNCHRONOUS", "NETWORK-CONTROL","ALARMS-AND-EVENTS","DIAGNOSTICS","VIDEO", "BEST-EFFORT", "AUDIO/VOICE")

traffic_type_var.trace_add("write", lambda *args: toggle_traffic_fields())

# Create a dedicated frame for traffic fields inside the content frame
traffic_frame = tk.Frame(content_frame)
traffic_frame.pack(fill="x", padx=5, pady=2)

def clear_traffic_frame():
    # Destroy all children widgets in the traffic frame
    for widget in traffic_frame.winfo_children():
        widget.destroy()

def toggle_traffic_fields(*args):
    if traffic_type_var.get() == "Choose Traffic Type":
        return

    clear_traffic_frame()

    if traffic_type_var.get() == "BEST-EFFORT":
        create_Best_effort_traffic_widgets()
        for widget in traffic_widgets_best_effort:
            widget.master = traffic_frame
            widget.pack(fill="x", padx=5, pady=2)
    elif traffic_type_var.get() == "AUDIO/VOICE":
        create_audio_voice_traffic_widgets()
        for widget in traffic_widgets_best_effort:
            widget.master = traffic_frame
            widget.pack(fill="x", padx=5, pady=2)
    else:
        create_traffic_widgets()
        for widget in traffic_widgets_rest:
            widget.master = traffic_frame
            widget.pack(fill="x", padx=5, pady=2)

    update_scroll_region()

# Update the creation functions so that widgets are added to traffic_frame
def create_label_entry_in_frame(frame, label_text, variable):
    subframe = tk.Frame(frame)
    subframe.pack(fill="x", padx=5, pady=2)
    label = tk.Label(subframe, text=label_text, width=25, anchor="w")
    label.pack(side="left")
    entry = tk.Entry(subframe, textvariable=variable, width=30)
    entry.pack(side="right", fill="x", expand=True)
    return subframe

pcp_list_var = tk.StringVar(value="4")

number_var = tk.StringVar(value="1")

# Add redundant properties for each traffic type
redundant_number_var = tk.StringVar(value="3")

redundant_routes_var = tk.StringVar(value="2")

cycle_time_units_var = tk.StringVar(value="MICRO_SECOND")

cycle_time_list_var = tk.StringVar(value="50000,100000,500000,1000000")

min_cycle_time_var = tk.StringVar(value="50000")

max_cycle_time_var = tk.StringVar(value="1000000")

min_delay_var = tk.StringVar(value="50000")

max_delay_var = tk.StringVar(value="1000000")

min_packet_size_var = tk.StringVar(value="50")

max_packet_size_var = tk.StringVar(value="500")

bidirectional_var = tk.StringVar(value="False")

# Global list to hold each traffic instance's variables
traffic_instances = []

# Container for traffic instances
traffic_container = tk.Frame(content_frame)
traffic_container.pack(fill="x", padx=5, pady=5)

def add_traffic_instance():
    # Create a frame for this traffic instance
    instance_frame = tk.Frame(traffic_container, relief="groove", bd=2)
    instance_frame.pack(fill="x", padx=5, pady=5)
    
    # Create a new set of variables for this instance.
    inst_vars = {
        "traffic_type_var": tk.StringVar(value="Choose Traffic Type"),
        "pcp_list_var": tk.StringVar(value="4"),
        "number_var": tk.StringVar(value="1"),
        "redundant_number_var": tk.StringVar(value="3"),
        "redundant_routes_var": tk.StringVar(value="2"),
        "cycle_time_units_var": tk.StringVar(value="MICRO_SECOND"),
        "cycle_time_list_var": tk.StringVar(value="50000,100000,500000,1000000"),
        "min_cycle_time_var": tk.StringVar(value="50000"),
        "max_cycle_time_var": tk.StringVar(value="1000000"),
        "min_delay_var": tk.StringVar(value="50000"),
        "max_delay_var": tk.StringVar(value="1000000"),
        "min_packet_size_var": tk.StringVar(value="50"),
        "max_packet_size_var": tk.StringVar(value="500"),
        "bidirectional_var": tk.StringVar(value="False")
    }
    
    # OptionMenu for choosing the traffic type.
    traffic_type_dropdown = tk.OptionMenu(
        instance_frame, 
        inst_vars["traffic_type_var"],
        "ISOCHRONOUS", "CYCLIC-SYNCHRONOUS", "CYCLIC-ASYNCHRONOUS",
        "NETWORK-CONTROL", "ALARMS-AND-EVENTS", "DIAGNOSTICS",
        "VIDEO", "BEST-EFFORT", "AUDIO/VOICE"
    )
    traffic_type_dropdown.pack(fill="x", padx=5, pady=2)
    
    # Create a sub-frame that will hold the traffic fields widgets
    fields_frame = tk.Frame(instance_frame)
    fields_frame.pack(fill="x", padx=5, pady=2)
    
    # When the traffic type changes, update the instance's fields.
    def update_instance_fields(*args):
        # Clear existing widgets from the fields_frame
        for widget in fields_frame.winfo_children():
            widget.destroy()
        if inst_vars["traffic_type_var"].get() == "BEST-EFFORT":
            create_Best_effort_traffic_widgets_instance(fields_frame, inst_vars)
        elif inst_vars["traffic_type_var"].get() == "AUDIO/VOICE":
            create_audio_voice_traffic_widgets_instance(fields_frame, inst_vars)
        elif inst_vars["traffic_type_var"].get() != "Choose Traffic Type":
            create_traffic_widgets_instance(fields_frame, inst_vars)
        
        update_scroll_region()
    
    inst_vars["traffic_type_var"].trace_add("write", update_instance_fields)
    
    update_instance_fields()
    
    traffic_instances.append(inst_vars)

def create_traffic_widgets_instance(frame, vars_dict):
    # Regular traffic widgets
    create_label_entry_in_frame(frame, "PCP-list (comma-separated):", vars_dict["pcp_list_var"])
    create_label_entry_in_frame(frame, "Number:", vars_dict["number_var"])
    create_label_entry_in_frame(frame, "Cycle Time Units:", vars_dict["cycle_time_units_var"])
    create_label_entry_in_frame(frame, "Cycle Time List (comma-separated):", vars_dict["cycle_time_list_var"])
    create_label_entry_in_frame(frame, "Min Cycle Time:", vars_dict["min_cycle_time_var"])
    create_label_entry_in_frame(frame, "Max Cycle Time:", vars_dict["max_cycle_time_var"])
    create_label_entry_in_frame(frame, "Min Delay:", vars_dict["min_delay_var"])
    create_label_entry_in_frame(frame, "Max Delay:", vars_dict["max_delay_var"])
    create_label_entry_in_frame(frame, "Min Packet Size:", vars_dict["min_packet_size_var"])
    create_label_entry_in_frame(frame, "Max Packet Size:", vars_dict["max_packet_size_var"])
    create_label_entry_in_frame(frame, "Bidirectional:", vars_dict["bidirectional_var"])

def create_Best_effort_traffic_widgets_instance(frame, vars_dict):
    # Best-effort traffic widgets
    create_label_entry_in_frame(frame, "PCP-list (comma-separated):", vars_dict["pcp_list_var"])
    create_label_entry_in_frame(frame, "Number:", vars_dict["number_var"])
    create_label_entry_in_frame(frame, "Min Packet Size:", vars_dict["min_packet_size_var"])
    create_label_entry_in_frame(frame, "Max Packet Size:", vars_dict["max_packet_size_var"])
    create_label_entry_in_frame(frame, "Bidirectional:", vars_dict["bidirectional_var"])
    
def create_audio_voice_traffic_widgets_instance(frame, vars_dict):
    # Audio/voice traffic widgets
    create_label_entry_in_frame(frame, "PCP-list (comma-separated):", vars_dict["pcp_list_var"])
    create_label_entry_in_frame(frame, "Number:", vars_dict["number_var"])
    create_label_entry_in_frame(frame, "Min Delay:", vars_dict["min_delay_var"])
    create_label_entry_in_frame(frame, "Max Delay:", vars_dict["max_delay_var"])
    create_label_entry_in_frame(frame, "Min Packet Size:", vars_dict["min_packet_size_var"])
    create_label_entry_in_frame(frame, "Max Packet Size:", vars_dict["max_packet_size_var"])
    create_label_entry_in_frame(frame, "Bidirectional:", vars_dict["bidirectional_var"])


# Button to add a new traffic type instance
add_traffic_button = tk.Button(content_frame, text="Add Traffic Type", command=add_traffic_instance)
add_traffic_button.pack(pady=5)

# Save button
save_button = tk.Button(content_frame, text="Save Config", command=save_config)
save_button.pack(pady=10)

# Update the scroll region to the content height after all elements are packed
content_frame.update_idletasks()
canvas.config(scrollregion=canvas.bbox("all"))

def on_mousewheel(event):
    if event.delta > 0:
        canvas.yview_scroll(-1, "units")
    else:
        canvas.yview_scroll(1, "units")

# Bind the mouse wheel event
root.bind_all("<MouseWheel>", on_mousewheel)


# Set the initial size of the window
root.geometry("800x600")

root.mainloop()
