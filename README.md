# EMA Digital Twin & Health Monitoring System
**Authors:** Maria Eduarda Nascimento Andrade & Meryem Hamamouch

<div align="center"> <img src="https://img.shields.io/badge/Node--RED-%238F0000.svg?style=for-the-badge&logo=node-red&logoColor=white" alt="Node-RED" /> <img src="https://img.shields.io/badge/mosquitto-%233C5280.svg?style=for-the-badge&logo=eclipsemosquitto&logoColor=white" alt="Mosquitto" /> <img src="https://img.shields.io/badge/python-%233670A0.svg?style=for-the-badge&logo=python&logoColor=ffdd54" alt="Python" /> <img src="https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white" alt="Docker" /> </div>



## Overview
This repository contains a real-time simulation and monitoring system for Electromechanical Actuators (EMAs), structured around an MQTT messaging architecture. The application's core consists of a physical simulator (`physical-EMA-simulator.py`) that models the actuator's dynamic, thermal, and degradation behaviors, publishing continuous telemetry metrics to a local broker.

Complementing the system, a logging script (`data-logger.py`) automatically captures and stores this data in a structured CSV file for subsequent analysis, while a diagnostic monitor (`diagnostic-monitor.py`) analyzes the telemetry stream both passively and actively. Together, these tools simulate failure scenarios and provide early detection of operational anomalies based on statistical thresholds and friction deviations.

## Real-Time Visualization & Monitoring (Node-RED)
To provide immediate insights into the system's behavior, a **Node-RED dashboard** is integrated into the architecture. It subscribes to the MQTT broker to parse the live telemetry JSON payloads and visualize the data in real-time. The graphical interface features responsive gauges and time-series charts, allowing users to actively monitor critical physical parameters—such as position, velocity, electrical current, and temperature. This visualization layer ensures immediate feedback on the EMA's operational state and makes the impact of mechanical degradation visually apparent as the simulation unfolds.

## Acknowledgments & Inspiration
The mathematical models and diagnostic algorithms implemented in this project are heavily inspired by the methodologies presented in the thesis by B. Wauthion[cite: 13]. Specifically, this project adapts advanced concepts from the research, including the EMA friction torque models[cite: 14], the use of the Dual Extended Kalman Filter (DEKF) for passive in-flight fault detection[cite: 14], and the application of the Generalized Likelihood Ratio (GLR) algorithm for active fault detection[cite: 15].