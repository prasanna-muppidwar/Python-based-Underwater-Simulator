import streamlit as st
import xml.etree.ElementTree as ET
import numpy as np
from scipy.integrate import solve_ivp
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import json
import io

# Functions for URDF Parsing and Simulation
def parse_urdf_to_json(urdf_file_path):
    def parse_element(element):
        parsed_data = {"tag": element.tag, "attributes": element.attrib, "children": []}
        for child in element:
            parsed_data["children"].append(parse_element(child))
        if element.text and element.text.strip():
            parsed_data["text"] = element.text.strip()
        return parsed_data

    try:
        tree = ET.parse(urdf_file_path)
        root = tree.getroot()
        urdf_json = parse_element(root)
        return urdf_json
    except Exception as e:
        st.error(f"Error parsing URDF file: {e}")
        return None

def extract_vehicle_parameters(urdf_json):
    vehicle_params = {"links": [], "joints": [], "mass": 0, "inertia": np.zeros((3, 3))}
    def traverse_node(node):
        if node["tag"] == "link":
            vehicle_params["links"].append(node["attributes"]["name"])
        if node["tag"] == "joint":
            vehicle_params["joints"].append({
                "name": node["attributes"]["name"],
                "type": node["attributes"]["type"],
                "parent": next((child["attributes"]["link"] for child in node["children"] if child["tag"] == "parent"), None),
                "child": next((child["attributes"]["link"] for child in node["children"] if child["tag"] == "child"), None),
                "axis": next((child["attributes"]["xyz"] for child in node["children"] if child["tag"] == "axis"), "0 0 0")
            })
        if node["tag"] == "inertial":
            mass_node = next((child for child in node["children"] if child["tag"] == "mass"), None)
            inertia_node = next((child for child in node["children"] if child["tag"] == "inertia"), None)
            if mass_node:
                vehicle_params["mass"] += float(mass_node["attributes"]["value"])
            if inertia_node:
                vehicle_params["inertia"] += np.diag([float(inertia_node["attributes"].get("ixx", 0)),
                                                      float(inertia_node["attributes"].get("iyy", 0)),
                                                      float(inertia_node["attributes"].get("izz", 0))])
        for child in node["children"]:
            traverse_node(child)

    traverse_node(urdf_json)
    return vehicle_params

def vehicle_dynamics(t, state, params):
    """
    Computes the vehicle dynamics using extracted parameters.
    """
    position = state[:3]
    linear_velocity = state[3:6]
    angular_velocity = state[6:9]

    # Compute forces and torques (simplified dynamics model)
    drag_force = -params["drag_coeff"] * linear_velocity
    forces = params["thrust"] + drag_force
    torques = -params["torque_coeff"] * angular_velocity

    # Accelerations
    linear_acceleration = forces / params["mass"]
    angular_acceleration = np.linalg.inv(params["inertia"]).dot(torques)

    # Derivatives
    dposition_dt = linear_velocity
    dlinear_velocity_dt = linear_acceleration
    dangular_velocity_dt = angular_acceleration 

    return np.concatenate((dposition_dt, dlinear_velocity_dt, dangular_velocity_dt))

def simulate(vehicle_params, initial_state, t_span):
    params = {
        "mass": vehicle_params["mass"],
        "inertia": vehicle_params["inertia"],
        "drag_coeff": np.array([0.1, 0.1, 0.2]),
        "torque_coeff": np.array([0.05, 0.05, 0.05]),
        "thrust": np.array([10.0, 5.0, 0.0])
    }
    
    solution = solve_ivp(
        fun=lambda t, y: vehicle_dynamics(t, y, params),
        t_span=t_span,
        y0=initial_state,
        method="RK45",
        t_eval=np.linspace(t_span[0], t_span[1], 100)
    )
    return solution

def visualize_trajectory(solution):
    states = solution.y
    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.plot(states[0], states[1], states[2], label="Trajectory")
    ax.set_xlabel("X (m)")
    ax.set_ylabel("Y (m)")
    ax.set_zlabel("Z (m)")
    ax.set_title("3D Trajectory")
    ax.legend()
    return fig

# Streamlit UI
st.title("Simu2VITA-inspired Simulator")
st.markdown("Upload a URDF file, extract its parameters, simulate motion, and visualize the trajectory.")

# File Upload
uploaded_file = st.file_uploader("Upload a URDF file", type=["urdf"])
if uploaded_file is not None:
    urdf_json = parse_urdf_to_json(io.StringIO(uploaded_file.getvalue().decode("utf-8")))
    if urdf_json:
        st.subheader("Extracted Parameters")
        vehicle_params = extract_vehicle_parameters(urdf_json)
        st.json(vehicle_params)

        # Simulation Options
        st.subheader("Simulation Configuration")
        initial_state = st.text_input(
            "Initial State (x, y, z, vx, vy, vz, wx, wy, wz)", 
            value="0, 0, 0, 0, 0, 0, 0, 0, 0"
        )
        t_span = st.slider("Time Span (seconds)", 0, 100, (0, 20), step=1)
        
        if st.button("Simulate"):
            try:
                initial_state = np.array([float(x) for x in initial_state.split(",")])
                solution = simulate(vehicle_params, initial_state, t_span)
                st.success("Simulation completed!")
                st.pyplot(visualize_trajectory(solution))
            except Exception as e:
                st.error(f"Error during simulation: {e}")
