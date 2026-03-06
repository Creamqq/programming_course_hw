#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import numpy as np
import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
from flask import Flask, render_template, request, jsonify
import base64
from io import BytesIO
import threading
import time

app = Flask(__name__)

# Parameters for heat equation
alpha = 0.01
x_min, x_max = 0, 1
t_min, t_max = 0, 1
n_hidden = 4

# Global variables
params = None
loss_history = []
boundary_loss_history = []
physics_loss_history = []
is_training = False
training_thread = None

# Generate training data
def generate_training_data():
    x_boundary = np.array([[0.0], [1.0], [0.0], [0.5], [1.0]])
    t_boundary = np.array([[0.5], [0.5], [0.0], [0.0], [0.0]])
    u_boundary = np.array([[0.0], [0.0], [0.0], [1.0], [0.0]])
    x_collocation = np.array([[0.25], [0.5], [0.75]])
    t_collocation = np.array([[0.25], [0.5], [0.75]])
    return (x_boundary, t_boundary, u_boundary), (x_collocation, t_collocation)

# Neural network forward pass
def forward_pass(X, params):
    n_input = 2
    n_output = 1
    idx = 0
    w1 = params[idx:idx+n_input*n_hidden].reshape(n_input, n_hidden)
    idx += n_input*n_hidden
    b1 = params[idx:idx+n_hidden]
    idx += n_hidden
    w2 = params[idx:idx+n_hidden*n_output].reshape(n_hidden, n_output)
    idx += n_hidden*n_output
    b2 = params[idx:idx+n_output]
    z1 = np.dot(X, w1) + b1
    a1 = np.tanh(z1)
    z2 = np.dot(a1, w2) + b2
    return z2

# Compute derivative using finite difference
def compute_derivative(f, X, epsilon=1e-4):
    n = X.shape[0]
    derivative = np.zeros(n)
    for i in range(n):
        X_plus = X.copy()
        X_plus[i] += epsilon
        X_minus = X.copy()
        X_minus[i] -= epsilon
        derivative[i] = (f(X_plus) - f(X_minus)) / (2 * epsilon)
    return derivative

# Compute residual of heat equation
def compute_residual(params, x, t):
    n = x.shape[0]
    residual = np.zeros(n)
    for i in range(n):
        def u(X):
            return forward_pass(X.reshape(1, 2), params)[0, 0]
        X = np.array([x[i, 0], t[i, 0]])
        def u_t_func(X):
            return compute_derivative(u, X)[1]
        u_t = u_t_func(X)
        def u_x_func(X):
            return compute_derivative(u, X)[0]
        u_x = u_x_func(X)
        def u_xx_func(X):
            return compute_derivative(u_x_func, X)[0]
        u_xx = u_xx_func(X)
        residual[i] = u_t - alpha * u_xx
    return residual

# Loss function
def loss_function(params, boundary_data, collocation_data):
    x_boundary, t_boundary, u_boundary = boundary_data
    x_collocation, t_collocation = collocation_data
    X_boundary = np.concatenate([x_boundary, t_boundary], axis=1)
    u_pred_boundary = forward_pass(X_boundary, params)
    boundary_loss = np.mean((u_pred_boundary - u_boundary)**2)
    residual = compute_residual(params, x_collocation, t_collocation)
    physics_loss = np.mean(residual**2)
    total_loss = boundary_loss + physics_loss
    return total_loss, boundary_loss, physics_loss

# Gradient descent optimizer
def gradient_descent(params, boundary_data, collocation_data, learning_rate=1e-2, epochs=100):
    global loss_history, boundary_loss_history, physics_loss_history
    loss_history = []
    boundary_loss_history = []
    physics_loss_history = []
    
    for epoch in range(epochs):
        if not is_training:
            break
        current_loss, boundary_loss, physics_loss = loss_function(params, boundary_data, collocation_data)
        grad = np.zeros_like(params)
        epsilon = 1e-6
        for i in range(len(params)):
            params_plus = params.copy()
            params_plus[i] += epsilon
            params_minus = params.copy()
            params_minus[i] -= epsilon
            loss_plus, _, _ = loss_function(params_plus, boundary_data, collocation_data)
            loss_minus, _, _ = loss_function(params_minus, boundary_data, collocation_data)
            grad[i] = (loss_plus - loss_minus) / (2 * epsilon)
        params -= learning_rate * grad
        loss_history.append(current_loss)
        boundary_loss_history.append(boundary_loss)
        physics_loss_history.append(physics_loss)
        time.sleep(0.01)
    return params

# Training thread function
def train_thread_func(learning_rate, epochs):
    global params, is_training, alpha, n_hidden
    try:
        boundary_data, collocation_data = generate_training_data()
        n_input = 2
        n_output = 1
        total_params = n_input * n_hidden + n_hidden + n_hidden * n_output + n_output
        params = np.random.randn(total_params) * 0.1
        params = gradient_descent(params, boundary_data, collocation_data, learning_rate=learning_rate, epochs=epochs)
    except Exception as e:
        print(f"Training error: {e}")
    finally:
        is_training = False

# Convert plot to base64
def plot_to_base64(fig):
    buffer = BytesIO()
    fig.savefig(buffer, format='png', dpi=100)
    buffer.seek(0)
    image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    plt.close(fig)
    return f"data:image/png;base64,{image_base64}"

# Get loss history plot
def get_loss_history_plot():
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(loss_history, label='Total Loss')
    ax.plot(boundary_loss_history, label='Boundary Loss')
    ax.plot(physics_loss_history, label='Physics Loss')
    ax.set_title('Training Loss History')
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Loss')
    ax.set_yscale('log')
    ax.legend()
    ax.grid(True, alpha=0.3)
    return plot_to_base64(fig)

# Get prediction comparison plot
def get_prediction_comparison_plot():
    n_points = 50
    x = np.linspace(x_min, x_max, n_points)
    t = np.linspace(t_min, t_max, n_points)
    X, T = np.meshgrid(x, t)
    input_data = np.concatenate([X.reshape(-1, 1), T.reshape(-1, 1)], axis=1)
    U_pred = forward_pass(input_data, params).reshape(n_points, n_points)
    U_analytical = np.sin(np.pi * X) * np.exp(-alpha * np.pi**2 * T)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    im1 = ax1.imshow(U_pred, extent=[x_min, x_max, t_min, t_max], origin='lower', cmap='viridis')
    ax1.set_title('PINN Prediction')
    ax1.set_xlabel('x')
    ax1.set_ylabel('t')
    fig.colorbar(im1, ax=ax1)
    im2 = ax2.imshow(U_analytical, extent=[x_min, x_max, t_min, t_max], origin='lower', cmap='viridis')
    ax2.set_title('Analytical Solution')
    ax2.set_xlabel('x')
    ax2.set_ylabel('t')
    fig.colorbar(im2, ax=ax2)
    return plot_to_base64(fig)

# Get 3D temperature plot
def get_3d_temperature_plot():
    n_points = 30
    x = np.linspace(x_min, x_max, n_points)
    t = np.linspace(t_min, t_max, n_points)
    X, T = np.meshgrid(x, t)
    input_data = np.concatenate([X.reshape(-1, 1), T.reshape(-1, 1)], axis=1)
    U_pred = forward_pass(input_data, params).reshape(n_points, n_points)
    U_analytical = np.sin(np.pi * X) * np.exp(-alpha * np.pi**2 * T)
    fig = plt.figure(figsize=(12, 10))
    ax1 = fig.add_subplot(211, projection='3d')
    ax1.plot_surface(X, T, U_pred, cmap='viridis')
    ax1.set_title('PINN Prediction (3D)')
    ax1.set_xlabel('x')
    ax1.set_ylabel('t')
    ax1.set_zlabel('u')
    ax2 = fig.add_subplot(212, projection='3d')
    ax2.plot_surface(X, T, U_analytical, cmap='viridis')
    ax2.set_title('Analytical Solution (3D)')
    ax2.set_xlabel('x')
    ax2.set_ylabel('t')
    ax2.set_zlabel('u')
    return plot_to_base64(fig)

# Get temperature at times plot
def get_temperature_at_times_plot():
    n_points = 100
    x = np.linspace(x_min, x_max, n_points)
    t_times = [0, 0.1, 0.25, 0.5, 0.75, 1.0]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    colors = plt.cm.viridis(np.linspace(0, 1, len(t_times)))
    for i, t in enumerate(t_times):
        t_test = np.full((n_points, 1), t)
        x_test = x.reshape(-1, 1)
        input_data = np.concatenate([x_test, t_test], axis=1)
        U_pred = forward_pass(input_data, params).flatten()
        ax1.plot(x, U_pred, color=colors[i], linewidth=2, label=f't = {t:.2f}')
    ax1.set_xlabel('x', fontsize=12)
    ax1.set_ylabel('Temperature u(x,t)', fontsize=12)
    ax1.set_title('PINN Prediction at Different Times')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(x_min, x_max)
    ax1.set_ylim(-0.1, 1.1)
    for i, t in enumerate(t_times):
        U_analytical = np.sin(np.pi * x) * np.exp(-alpha * np.pi**2 * t)
        ax2.plot(x, U_analytical, color=colors[i], linewidth=2, label=f't = {t:.2f}')
    ax2.set_xlabel('x', fontsize=12)
    ax2.set_ylabel('Temperature u(x,t)', fontsize=12)
    ax2.set_title('Analytical Solution at Different Times')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(x_min, x_max)
    ax2.set_ylim(-0.1, 1.1)
    return plot_to_base64(fig)

# Get error heatmap plot
def get_error_heatmap_plot():
    n_points = 50
    x = np.linspace(x_min, x_max, n_points)
    t = np.linspace(t_min, t_max, n_points)
    X, T = np.meshgrid(x, t)
    input_data = np.concatenate([X.reshape(-1, 1), T.reshape(-1, 1)], axis=1)
    U_pred = forward_pass(input_data, params).reshape(n_points, n_points)
    U_analytical = np.sin(np.pi * X) * np.exp(-alpha * np.pi**2 * T)
    error = np.abs(U_pred - U_analytical)
    fig, ax = plt.subplots(figsize=(10, 6))
    im = ax.imshow(error, extent=[x_min, x_max, t_min, t_max], origin='lower', cmap='hot', aspect='auto')
    ax.set_xlabel('x', fontsize=12)
    ax.set_ylabel('t', fontsize=12)
    ax.set_title('Absolute Error: |PINN - Analytical|')
    fig.colorbar(im, ax=ax, label='Error')
    return plot_to_base64(fig)

# Get loss evolution plot
def get_loss_evolution_plot():
    fig, ax = plt.subplots(figsize=(10, 6))
    epochs = np.arange(1, len(loss_history) + 1)
    ax.fill_between(epochs, loss_history, alpha=0.5, label='Total Loss', color='blue')
    ax.fill_between(epochs, boundary_loss_history, alpha=0.5, label='Boundary Loss', color='green')
    ax.fill_between(epochs, physics_loss_history, alpha=0.5, label='Physics Loss', color='red')
    ax.set_xlabel('Epoch', fontsize=12)
    ax.set_ylabel('Loss', fontsize=12)
    ax.set_title('Loss Evolution During Training')
    ax.set_yscale('log')
    ax.legend()
    ax.grid(True, alpha=0.3)
    return plot_to_base64(fig)

# Get boundary check plot
def get_boundary_check_plot():
    n_points = 50
    x = np.linspace(x_min, x_max, n_points)
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    t = 0
    t_test = np.full((n_points, 1), t)
    x_test = x.reshape(-1, 1)
    input_data = np.concatenate([x_test, t_test], axis=1)
    U_pred = forward_pass(input_data, params).flatten()
    U_analytical = np.sin(np.pi * x) * np.exp(-alpha * np.pi**2 * t)
    ax1.plot(x, U_pred, 'b-', linewidth=2, label='PINN Prediction')
    ax1.plot(x, U_analytical, 'r--', linewidth=2, label='Analytical')
    ax1.set_xlabel('x', fontsize=12)
    ax1.set_ylabel('u(x,0)', fontsize=12)
    ax1.set_title('Initial Condition u(x,0) = sin(πx)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    t_vals = np.linspace(t_min, t_max, n_points)
    x_zero = np.zeros((n_points, 1))
    t_test = t_vals.reshape(-1, 1)
    input_data = np.concatenate([x_zero, t_test], axis=1)
    U_at_x0 = forward_pass(input_data, params).flatten()
    x_one = np.ones((n_points, 1))
    input_data = np.concatenate([x_one, t_test], axis=1)
    U_at_x1 = forward_pass(input_data, params).flatten()
    ax2.plot(t_vals, U_at_x0, 'b-', linewidth=2, label='u(0,t) - PINN')
    ax2.plot(t_vals, U_at_x1, 'g-', linewidth=2, label='u(1,t) - PINN')
    ax2.axhline(y=0, color='r', linestyle='--', linewidth=1, label='BC = 0')
    ax2.set_xlabel('t', fontsize=12)
    ax2.set_ylabel('u(0,t) and u(1,t)', fontsize=12)
    ax2.set_title('Boundary Conditions at x=0 and x=1')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    return plot_to_base64(fig)

# Get test results
def get_test_results():
    test_points = [[0.0, 0.0], [0.5, 0.0], [1.0, 0.0], [0.0, 0.5], [1.0, 0.5], [0.25, 0.25], [0.5, 0.25], [0.75, 0.25]]
    results = []
    for point in test_points:
        x, t = point
        X = np.array([[x, t]])
        u_pred = forward_pass(X, params)[0, 0]
        u_analytical = np.sin(np.pi * x) * np.exp(-alpha * np.pi**2 * t)
        results.append({"x": round(x, 2), "t": round(t, 2), "prediction": round(u_pred, 6), "analytical": round(u_analytical, 6)})
    return results

# Home page
@app.route('/')
def index():
    return render_template('index.html')

# Train API
@app.route('/train', methods=['POST'])
def train():
    global is_training, alpha, n_hidden, training_thread
    data = request.json
    alpha = data.get('alpha', 0.01)
    learning_rate = data.get('learning_rate', 0.01)
    epochs = data.get('epochs', 100)
    n_hidden = data.get('hidden_neurons', 4)
    is_training = True
    training_thread = threading.Thread(target=train_thread_func, args=(learning_rate, epochs))
    training_thread.daemon = True
    training_thread.start()
    return jsonify({"status": "training started"})

# Stop training
@app.route('/stop', methods=['POST'])
def stop():
    global is_training
    is_training = False
    return jsonify({"status": "training stopped"})

# Get status
@app.route('/status', methods=['GET'])
def status():
    if loss_history:
        return jsonify({
            "is_training": is_training,
            "epoch": len(loss_history),
            "loss": loss_history[-1] if loss_history else 0,
            "boundary_loss": boundary_loss_history[-1] if boundary_loss_history else 0,
            "physics_loss": physics_loss_history[-1] if physics_loss_history else 0
        })
    return jsonify({"is_training": is_training, "epoch": 0, "loss": 0, "boundary_loss": 0, "physics_loss": 0})

# Get results
@app.route('/results', methods=['GET'])
def results():
    if params is None:
        return jsonify({"error": "Model not trained yet"})
    
    return jsonify({
        "loss_history": get_loss_history_plot(),
        "prediction_comparison": get_prediction_comparison_plot(),
        "three_d_temperature": get_3d_temperature_plot(),
        "temperature_at_times": get_temperature_at_times_plot(),
        "error_heatmap": get_error_heatmap_plot(),
        "loss_evolution": get_loss_evolution_plot(),
        "boundary_check": get_boundary_check_plot(),
        "test_results": get_test_results()
    })

if __name__ == '__main__':
    print('Starting PINN Web Application...')
    print('Running on http://localhost:8081/')
    app.run(debug=False, host='0.0.0.0', port=8081)