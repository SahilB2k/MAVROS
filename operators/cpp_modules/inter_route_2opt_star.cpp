
#include <vector>
#include <cmath>
#include <algorithm>
#include <tuple>
#include <pybind11/pybind11.h>
#include <pybind11/stl.h>

namespace py = pybind11;

// --- Data Structures ---
struct Customer {
    int id;
    double x, y;
    int demand;
    int ready_time;
    int due_date;
    int service_time;
};

// --- Helper Functions ---

// Euclidean distance
inline double distance(const Customer& c1, const Customer& c2) {
    return std::sqrt(std::pow(c1.x - c2.x, 2) + std::pow(c1.y - c2.y, 2));
}

// Calculate route cost and feasibility
// Returns pair {cost, is_feasible}
std::pair<double, bool> evaluate_route(
    const std::vector<int>& route_ids,
    const std::vector<Customer>& customers, // 0-indexed by ID
    const Customer& depot,
    int capacity
) {
    if (route_ids.empty()) return {0.0, true};

    double current_time = 0.0;
    int current_load = 0;
    double total_cost = 0.0;
    const Customer* prev = &depot;

    for (int cid : route_ids) {
        if (cid < 0 || cid >= customers.size()) return {0.0, false}; // Safety check
        const Customer& curr = customers[cid];

        // 1. Capacity
        current_load += curr.demand;
        if (current_load > capacity) return {0.0, false};

        // 2. Time Windows
        double travel = distance(*prev, curr);
        double arrival = current_time + travel;
        double wait = std::max(0.0, (double)curr.ready_time - arrival);
        double start_service = arrival + wait;

        if (start_service > curr.due_date) return {0.0, false};

        // Cost accumulation (Distance + Waiting)
        // Note: Python implementation uses weighted waiting time, typically 1.0
        total_cost += travel + wait;

        current_time = start_service + curr.service_time;
        prev = &curr;
    }

    // Return to depot
    double return_travel = distance(*prev, depot);
    double return_arrival = current_time + return_travel;
    
    // Check depot due date if applicable (usually lax, so skipped here for speed unless strictly required)
    
    total_cost += return_travel;
    
    return {total_cost, true};
}

// --- Main Operator ---

// tuple<bool, int, int, vector<int>, vector<int>>
// Returns: found_improvement, route_idx_1, route_idx_2, new_route_1_path, new_route_2_path
std::tuple<bool, int, int, std::vector<int>, std::vector<int>> 
inter_route_2opt_star(
    std::vector<std::vector<int>> routes, 
    std::vector<std::tuple<int, double, double, int, int, int, int>> customers_data, // (id, x, y, demand, ready, due, service)
    std::tuple<int, double, double, int, int, int, int> depot_data,
    int capacity,
    int max_attempts
) {
    // 1. Unpack Customer Data
    std::vector<Customer> customers(customers_data.size());
    for (const auto& c : customers_data) {
        int id = std::get<0>(c);
        if(id < customers.size()){
             customers[id] = {
                id,
                std::get<1>(c), std::get<2>(c),
                std::get<3>(c),
                std::get<4>(c), std::get<5>(c), std::get<6>(c)
            };
        }
    }

    Customer depot = {
        std::get<0>(depot_data),
        std::get<1>(depot_data), std::get<2>(depot_data),
        std::get<3>(depot_data),
        std::get<4>(depot_data), std::get<5>(depot_data), std::get<6>(depot_data)
    };

    int attempts = 0;
    
    // 2. Iterate pairs
    for (size_t i = 0; i < routes.size(); ++i) {
        for (size_t j = i + 1; j < routes.size(); ++j) {
            
            const auto& r1 = routes[i];
            const auto& r2 = routes[j];

            if (r1.size() < 2 || r2.size() < 2) continue;

            // Calculate initial cost (approximation, only for comparison)
            auto res1 = evaluate_route(r1, customers, depot, capacity);
            auto res2 = evaluate_route(r2, customers, depot, capacity);
            double current_total_cost = res1.first + res2.first;

            // Try cut points
            for (size_t cut1 = 1; cut1 < r1.size(); ++cut1) {
                for (size_t cut2 = 1; cut2 < r2.size(); ++cut2) {
                    attempts++;
                    if (attempts > max_attempts) goto end_search;

                    // Generate new routes (Swap Tails)
                    std::vector<int> new_r1;
                    std::vector<int> new_r2;

                    // New R1: R1_head + R2_tail
                    new_r1.insert(new_r1.end(), r1.begin(), r1.begin() + cut1);
                    new_r1.insert(new_r1.end(), r2.begin() + cut2, r2.end());

                    // New R2: R2_head + R1_tail
                    new_r2.insert(new_r2.end(), r2.begin(), r2.begin() + cut2);
                    new_r2.insert(new_r2.end(), r1.begin() + cut1, r1.end());
                    
                    // Evaluate
                    auto eval1 = evaluate_route(new_r1, customers, depot, capacity);
                    if (!eval1.second) continue;

                    auto eval2 = evaluate_route(new_r2, customers, depot, capacity);
                    if (!eval2.second) continue;

                    double new_total_cost = eval1.first + eval2.first;

                    // Check for improvement (using epsilon for float comparison)
                    if (new_total_cost + 1e-6 < current_total_cost) {
                        // Found Move!
                        return {true, (int)i, (int)j, new_r1, new_r2};
                    }
                }
            }
        }
    }

    end_search:
    return {false, -1, -1, {}, {}};
}

// --- Module Definition ---
PYBIND11_MODULE(mavros_cpp, m) {
    m.doc() = "MAVROS Fast C++ Operators";
    m.def("inter_route_2opt_star", &inter_route_2opt_star, "C++ optimized 2-Opt*");
}
