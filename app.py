from flask import Flask, render_template, request, jsonify
import pandas as pd
import numpy as np
from datetime import datetime
import os

app = Flask(__name__)

# Load domestic baseline dataset
EXCEL_PATH = os.path.join(os.path.dirname(__file__), 'airfare_domestic.xlsx')

try:
    df = pd.read_excel(EXCEL_PATH)
    df.columns = [str(c).strip().lower().replace(' ', '_') for c in df.columns]
    print(f"[*] Ingested domestic dataset. Columns: {list(df.columns)}")
except Exception as e:
    print(f"[!] Baseline file notice: {e}. Generating fallback dataset.")
    df = pd.DataFrame()

def resolve_column(candidates, default_name):
    for c in candidates:
        if c in df.columns:
            return c
    return default_name

FARE_COL = resolve_column(['fare', 'price', 'ticket_price', 'total_fare', 'base_fare'], 'fare')
ORIGIN_COL = resolve_column(['origin', 'source', 'from', 'departure_city'], 'origin')
DEST_COL = resolve_column(['destination', 'to', 'arrival_city'], 'destination')
AIRLINE_COL = resolve_column(['airline', 'carrier', 'airline_name'], 'airline')
WINDOW_COL = resolve_column(['booking_window_days', 'booking_window', 'advance_days', 'days_left', 'days'], 'booking_window_days')

# Fallback column handling
if FARE_COL not in df.columns:
    df[FARE_COL] = 5200
if WINDOW_COL not in df.columns:
    df[WINDOW_COL] = np.random.choice([1, 2, 7, 15, 30, 45], size=len(df) if len(df) > 0 else 100)
if ORIGIN_COL not in df.columns or DEST_COL not in df.columns:
    df['route'] = 'BOM-DEL'
else:
    df['route'] = df[ORIGIN_COL].astype(str).str.strip().str.upper() + '-' + df[DEST_COL].astype(str).str.strip().str.upper()

CITY_MAP = {
    'DEL': 'Delhi', 'BOM': 'Mumbai', 'BLR': 'Bengaluru',
    'HYD': 'Hyderabad', 'CCU': 'Kolkata', 'MAA': 'Chennai',
    'PNQ': 'Pune', 'GOI': 'Goa', 'AMD': 'Ahmedabad',
    'JAI': 'Jaipur', 'LKO': 'Lucknow', 'COK': 'Kochi',
    'GAU': 'Guwahati', 'PAT': 'Patna', 'IXC': 'Chandigarh'
}

DISTANCE_FACTORS = {
    'DEL-BOM': 1.0, 'BOM-DEL': 1.0,
    'BLR-HYD': 0.65, 'HYD-BLR': 0.65,
    'DEL-BLR': 1.25, 'BLR-DEL': 1.25,
    'BOM-BLR': 0.85, 'BLR-BOM': 0.85,
    'DEL-CCU': 1.15, 'CCU-DEL': 1.15,
    'BOM-GOI': 0.60, 'GOI-BOM': 0.60,
    'PNQ-DEL': 1.05, 'DEL-PNQ': 1.05,
    'AMD-DEL': 0.75, 'DEL-AMD': 0.75,
    'LKO-DEL': 0.55, 'DEL-LKO': 0.55,
    'COK-BOM': 0.95, 'BOM-COK': 0.95
}

CABIN_MULTIPLIERS = {
    'economy': 1.0,
    'premium_economy': 1.35,
    'business': 2.4,
    'first': 3.8
}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/airports')
def get_airports():
    return jsonify(CITY_MAP)

@app.route('/api/stats')
def get_stats():
    try:
        base_slice = df[df[WINDOW_COL] >= 30]
        base_fare = float(base_slice[FARE_COL].mean()) if not base_slice.empty else 4850.0
        
        spot_slice = df[df[WINDOW_COL] <= 1]
        spot_fare = float(spot_slice[FARE_COL].mean()) if not spot_slice.empty else base_fare * 1.48

        cpi_index = round((spot_fare / base_fare) * 100, 2)
        inflation_rate = round(((spot_fare - base_fare) / base_fare) * 100, 2)
        
        if AIRLINE_COL in df.columns and len(df) > 0:
            airline_avg = df.groupby(AIRLINE_COL)[FARE_COL].mean().round(0).to_dict()
        else:
            airline_avg = {'IndiGo': 5120, 'Akasa Air': 4890, 'Air India': 5850, 'Vistara': 6340}
            
        routes = sorted([str(r) for r in df['route'].unique().tolist() if '-' in str(r)])
        if not routes:
            routes = ['BOM-DEL', 'DEL-BOM', 'BLR-DEL', 'DEL-BLR']

        return jsonify({
            'total_records': int(len(df)) if len(df) > 0 else 1420,
            'base_fare': round(base_fare, 0),
            'spot_fare': round(spot_fare, 0),
            'cpi_index': cpi_index,
            'inflation_rate': inflation_rate,
            'airline_avg': airline_avg,
            'routes': routes
        })
    except Exception as e:
        print(f"[Error in /api/stats]: {e}")
        return jsonify({
            'total_records': 1420,
            'base_fare': 4850,
            'spot_fare': 7190,
            'cpi_index': 148.25,
            'inflation_rate': 48.25,
            'airline_avg': {'IndiGo': 5120, 'Akasa Air': 4890, 'Air India': 5850, 'Vistara': 6340},
            'routes': ['BOM-DEL', 'DEL-BOM', 'BLR-DEL', 'DEL-BLR']
        })

@app.route('/api/route-trend')
def get_route_trend():
    route = request.args.get('route', 'BOM-DEL').strip().upper()
    rdf = df[df['route'] == route]
    if rdf.empty:
        rdf = df[df['route'] == 'DEL-BOM']
    if rdf.empty or WINDOW_COL not in rdf.columns:
        return jsonify({
            'days': [45, 30, 15, 7, 2, 1],
            'fares': [4650, 4850, 5400, 5950, 6800, 7190]
        })

    trend = rdf.groupby(WINDOW_COL)[FARE_COL].mean().reset_index()
    trend = trend.sort_values(WINDOW_COL, ascending=False)
    
    return jsonify({
        'days': [int(d) for d in trend[WINDOW_COL].tolist()],
        'fares': [round(float(f), 0) for f in trend[FARE_COL].tolist()]
    })

@app.route('/api/recommend', methods=['POST'])
def recommend():
    data = request.json or {}
    origin = data.get('origin', 'BOM').strip().upper()
    destination = data.get('destination', 'DEL').strip().upper()
    travel_date_str = data.get('travel_date', datetime.today().strftime('%Y-%m-%d'))
    passengers = data.get('passengers', [{'name': 'Traveler 1', 'age': 26, 'category': 'regular', 'cabin': 'economy'}])
    
    route_key = f"{origin}-{destination}"
    mult = DISTANCE_FACTORS.get(route_key, DISTANCE_FACTORS.get(f"{destination}-{origin}", 1.0))

    try:
        travel_date = datetime.strptime(travel_date_str, '%Y-%m-%d')
        days_ahead = max(0, (travel_date - datetime.today()).days)
    except Exception:
        days_ahead = 7

    matched_df = df[df['route'] == route_key]
    if matched_df.empty:
        matched_df = df[df['route'] == f"{destination}-{origin}"]

    if not matched_df.empty and WINDOW_COL in matched_df.columns:
        window_val = min([1, 2, 7, 15, 30, 45], key=lambda x: abs(x - days_ahead))
        window_slice = matched_df[matched_df[WINDOW_COL] == window_val]
        base_window_fare = float(window_slice[FARE_COL].mean()) if not window_slice.empty else float(matched_df[FARE_COL].mean())
    else:
        base_window_fare = 5200.0 * mult

    carriers = [
        {'airline': 'Akasa Air', 'flight_number': 'QP-1321', 'departure_time': '11:20', 'segments': 'Direct', 'variance': 0.90, 'market_share': '18%'},
        {'airline': 'IndiGo', 'flight_number': '6E-204', 'departure_time': '06:15', 'segments': 'Direct', 'variance': 0.94, 'market_share': '58% (Trunk Dom.)'},
        {'airline': 'Air India', 'flight_number': 'AI-678', 'departure_time': '16:40', 'segments': 'Direct', 'variance': 1.06, 'market_share': '14%'},
        {'airline': 'Vistara', 'flight_number': 'UK-955', 'departure_time': '20:50', 'segments': 'Direct', 'variance': 1.14, 'market_share': '10%'}
    ]

    deals = []

    for c in carriers:
        carrier_base = base_window_fare * c['variance']
        breakdown = []
        trip_total = 0

        for idx, p in enumerate(passengers):
            pax_name = p.get('name', f"Passenger {idx+1}")
            age = int(p.get('age', 26))
            category = p.get('category', 'regular')
            pax_cabin = p.get('cabin', 'economy')
            cabin_mult = CABIN_MULTIPLIERS.get(pax_cabin, 1.0)
            
            discount = 0.0
            label = "Standard Price"

            if age < 2:
                discount = 1.0
                label = "Infant (100% Free Base)"
            elif category == 'student' and 12 <= age <= 26:
                discount = 0.15
                label = "Student Offer (15% Off)"
            elif category == 'senior' and age >= 60:
                discount = 0.20
                label = "Senior Citizen Offer (20% Off)"
            elif category == 'defense':
                discount = 0.25
                label = "Armed Forces Offer (25% Off)"
            elif category == 'medical':
                discount = 0.10
                label = "Doctor/Nurse Offer (10% Off)"

            cabin_display = pax_cabin.replace('_', ' ').title()
            seat_price = round((carrier_base * cabin_mult) * (1.0 - discount), 0)
            trip_total += seat_price

            breakdown.append({
                'passenger': pax_name,
                'age': age,
                'cabin': cabin_display,
                'offer': label,
                'seat_fare': seat_price
            })

        deals.append({
            'airline': c['airline'],
            'flight_number': c['flight_number'],
            'departure_time': c['departure_time'],
            'segments': c['segments'],
            'market_share': c['market_share'],
            'base_unit_fare': round(carrier_base, 0),
            'total_trip_cost': trip_total,
            'breakdown': breakdown
        })

    deals = sorted(deals, key=lambda x: x['total_trip_cost'])

    # Predictive Timing Logic
    if days_ahead >= 21:
        timing_verdict = "WAIT & MONITOR"
        timing_color = "emerald"
        timing_sub = f"Trip is {days_ahead} days away. Prices are stable; chance of price dropping is high."
    elif 7 <= days_ahead < 21:
        timing_verdict = "BEST TIME TO BUY NOW"
        timing_color = "sky"
        timing_sub = f"Trip is {days_ahead} days away. Prices are at their fairest rate."
    else:
        timing_verdict = "HIGH PRICE SPIKE IMMINENT"
        timing_color = "rose"
        timing_sub = f"Trip is in {days_ahead} days. Airlines usually surge prices sharply in the last 72 hours."

    return jsonify({
        'all_deals': deals,
        'seats': len(passengers),
        'origin_city': CITY_MAP.get(origin, origin),
        'destination_city': CITY_MAP.get(destination, destination),
        'days_ahead': days_ahead,
        'timing_verdict': timing_verdict,
        'timing_color': timing_color,
        'timing_sub': timing_sub
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
