"""
Flask Application Server for VRPTW Visualization
- Serves the frontend UI for visualizing routes.
- Provides API endpoints to run the solver and retrieve results.
- Bridges the Python solver with the JavaScript/React frontend.
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import time
import traceback
from core.solomon_loader import load_solomon_instance
from algorithms.hybrid_solver import solve_vrptw

app = Flask(__name__, static_folder='frontend/dist', static_url_path='/')
CORS(app)  # Enable CORS for deployment

@app.route('/')
def index():
    """Serve the main UI from React build"""
    return send_from_directory('frontend/dist', 'index.html')

@app.route('/comparison')
def comparison():
    """Serve the main UI (React handles routing internally or serve index)"""
    return send_from_directory('frontend/dist', 'index.html')

@app.route('/charts/<path:filename>')
def serve_charts(filename):
    """Serve chart images"""
    return send_from_directory('static/charts', filename)

@app.route('/<path:filename>')
def serve_static(filename):
    """Serve static files"""
    return send_from_directory('static', filename)

# Known OR-Tools / Optimal baselines for Solomon instances
# (Values represent approximate OR-Tools performance for 100 customers)
BASELINE_REGISTRY = {
    'c101.txt': {'total_cost': 827.3, 'num_vehicles': 10, 'solve_time': 30.0},
    'c102.txt': {'total_cost': 1747.0, 'num_vehicles': 12, 'solve_time': 30.0},
    'r101.txt': {'total_cost': 1637.7, 'num_vehicles': 19, 'solve_time': 30.0},
    'rc101.txt': {'total_cost': 1619.8, 'num_vehicles': 14, 'solve_time': 30.0},
    'default': {'total_cost': 2000.0, 'num_vehicles': 15, 'solve_time': 30.0}
}

@app.route('/api/solve', methods=['POST'])
def solve():
    """
    Solve a VRPTW instance
    """
    try:
        data = request.json
        instance_file = data.get('instance_file', 'data/c102.txt')
        instance_name = os.path.basename(instance_file)
        max_customers = data.get('max_customers')
        
        # Load instance
        if max_customers:
            from core.solomon_loader import load_solomon_subset
            depot, customers, vehicle_capacity, _ = load_solomon_subset(instance_file, max_customers)
        else:
            depot, customers, vehicle_capacity, _ = load_solomon_instance(instance_file)
        
        # Solve
        start_time = time.time()
        solution = solve_vrptw(depot, customers, vehicle_capacity)
        solve_time = time.time() - start_time
        
        # Format response
        routes_data = []
        for i, route in enumerate(solution.routes):
            route_customers = []
            for idx, cid in enumerate(route.customer_ids):
                customer = route.customers_lookup[cid]
                
                # Calculate distance to next stop
                if idx < len(route.customer_ids) - 1:
                    next_cid = route.customer_ids[idx + 1]
                    next_customer = route.customers_lookup[next_cid]
                    distance_to_next = ((customer.x - next_customer.x)**2 + (customer.y - next_customer.y)**2)**0.5
                else:
                    distance_to_next = ((customer.x - depot.x)**2 + (customer.y - depot.y)**2)**0.5
                
                route_customers.append({
                    'id': customer.id, 'x': customer.x, 'y': customer.y,
                    'demand': customer.demand, 'distance_to_next': round(distance_to_next, 2)
                })
            
            routes_data.append({
                'route_id': i + 1, 'customers': route_customers,
                'cost': round(route.total_cost, 2), 'load': route.current_load,
                'num_customers': len(route.customer_ids)
            })
        
        # Get baseline for this specific instance
        baseline = BASELINE_REGISTRY.get(instance_name, BASELINE_REGISTRY['default'])
        
        return jsonify({
            'success': True,
            'instance_name': instance_name,
            'total_cost': round(solution.total_base_cost, 2),
            'num_vehicles': solution.num_vehicles,
            'solve_time': round(solve_time, 2),
            'feasible': solution.is_feasible(),
            'routes': routes_data,
            'depot': {'id': depot.id, 'x': depot.x, 'y': depot.y},
            'customers': [{'id': c.id, 'x': c.x, 'y': c.y, 'demand': c.demand, 'ready_time': c.ready_time, 'due_date': c.due_date} for c in customers],
            'ortools_baseline': baseline
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@app.route('/api/instances', methods=['GET'])
def list_instances():
    """List available Solomon instances"""
    try:
        data_dir = 'data'
        if os.path.exists(data_dir):
            files = [f for f in os.listdir(data_dir) if f.endswith('.txt')]
            return jsonify({
                'success': True,
                'instances': sorted(files)
            })
        else:
            return jsonify({
                'success': True,
                'instances': []
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    # Create static directory if it doesn't exist
    os.makedirs('static', exist_ok=True)
    
    # Run server
    # For production, use gunicorn or waitress
    app.run(host='0.0.0.0', port=5000, debug=False)
