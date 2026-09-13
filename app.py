@app.route('/api/simulate-policy', methods=['POST'])
def simulate_policy():
    data = request.json or {}
    origin = data.get('origin', 'BOM').strip().upper()
    destination = data.get('destination', 'DEL').strip().upper()
    fuel_val = float(data.get('fuel', 4.2))
    fest_val = float(data.get('festival', 3.1))
    climate_val = float(data.get('climate', 0.0))
    tax_val = float(data.get('taxes', 0.0))

    route_key = f"{origin}-{destination}"
    mult = DISTANCE_FACTORS.get(route_key, DISTANCE_FACTORS.get(f"{destination}-{origin}", 1.0))
    
    # Route-specific elasticity scaling factor
    route_elasticity = 0.9 + (mult * 0.1)
    
    f_impact = round(fuel_val * route_elasticity, 1)
    fe_impact = round(fest_val * route_elasticity, 1)
    c_impact = round(climate_val * route_elasticity, 1)
    t_impact = round(tax_val * route_elasticity, 1)

    total_cpi = round(1.5 + f_impact + fe_impact + c_impact + t_impact, 1)

    return jsonify({
        'route': route_key,
        'fuel_impact': f_impact,
        'festival_impact': fe_impact,
        'climate_impact': c_impact,
        'tax_impact': t_impact,
        'total_cpi': total_cpi
    })
