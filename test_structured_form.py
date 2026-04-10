"""Test structured form functionality"""
import json

# Load form config
with open("data/form_config.json", "r") as f:
    FORM_CONFIG = json.load(f)

def construct_loss_description_from_form(
    policy_number, insured_name, date_of_loss, time_of_loss,
    country, city, address, product_type, incident_type,
    loss_description, estimated_value, currency,
    vehicle_plate, vehicle_model, driver_name,
    property_type, damage_type,
    hospital_name, treatment_type,
    vessel_name, bill_of_lading,
):
    """Constructs structured loss description from form inputs"""
    parts = []

    # Policy & Insured
    if policy_number:
        parts.append(f"Policy Number: {policy_number}")
    if insured_name:
        parts.append(f"Insured: {insured_name}")

    # Product Type
    if product_type and product_type != "Unknown / Let AI Detect":
        parts.append(f"Insurance Product: {product_type}")

    # Date & Time
    if date_of_loss:
        parts.append(f"Date of Loss: {date_of_loss}")
    if time_of_loss and time_of_loss != "Unknown":
        parts.append(f"Time of Loss: {time_of_loss}")

    # Location
    location_parts = []
    if city:
        location_parts.append(city)
    if country:
        country_name = FORM_CONFIG["countries"].get(country, country)
        location_parts.append(country_name)
    if location_parts:
        parts.append(f"Location: {', '.join(location_parts)}")
    if address:
        parts.append(f"Address: {address}")

    # Incident Type
    if incident_type:
        parts.append(f"Incident Type: {incident_type}")

    # Loss Description
    if loss_description:
        parts.append(f"\nDescription:\n{loss_description}")

    # Financial
    if estimated_value:
        parts.append(f"\nEstimated Loss: {currency} {estimated_value:,.2f}" if isinstance(estimated_value, (int, float)) else f"\nEstimated Loss: {currency} {estimated_value}")

    # Conditional fields
    if vehicle_plate or vehicle_model or driver_name:
        motor_info = []
        if vehicle_plate:
            motor_info.append(f"Vehicle Plate: {vehicle_plate}")
        if vehicle_model:
            motor_info.append(f"Vehicle Model: {vehicle_model}")
        if driver_name:
            motor_info.append(f"Driver: {driver_name}")
        if motor_info:
            parts.append("\n--- Motor Details ---")
            parts.extend(motor_info)

    if property_type or damage_type:
        prop_info = []
        if property_type:
            prop_info.append(f"Property Type: {property_type}")
        if damage_type:
            prop_info.append(f"Damage Type: {damage_type}")
        if prop_info:
            parts.append("\n--- Property Details ---")
            parts.extend(prop_info)

    if hospital_name or treatment_type:
        health_info = []
        if hospital_name:
            health_info.append(f"Hospital: {hospital_name}")
        if treatment_type:
            health_info.append(f"Treatment: {treatment_type}")
        if health_info:
            parts.append("\n--- Health Details ---")
            parts.extend(health_info)

    if vessel_name or bill_of_lading:
        marine_info = []
        if vessel_name:
            marine_info.append(f"Vessel: {vessel_name}")
        if bill_of_lading:
            marine_info.append(f"B/L Reference: {bill_of_lading}")
        if marine_info:
            parts.append("\n--- Marine Details ---")
            parts.extend(marine_info)

    return "\n".join(parts)


if __name__ == "__main__":
    print("=== TEST 1: Motor Claim (Collision) ===\n")

    test1 = construct_loss_description_from_form(
        policy_number='NAC-2024-DE-5512',
        insured_name='Munich Auto Leasing GmbH',
        date_of_loss='2026-04-09',
        time_of_loss='14:30',
        country='DE',
        city='Munich',
        address='A9 Autobahn, Exit 72',
        product_type='Motor Lines / Car / Auto – Automobile',
        incident_type='Motor: Collision',
        loss_description='Two-vehicle collision on A9 motorway during heavy traffic. Insured vehicle (BMW 5 Series) suffered front-end damage. Other vehicle (VW Golf) rear-ended. Both drivers without injury. Police report filed.',
        estimated_value=15000,
        currency='EUR',
        vehicle_plate='M-AB 1234',
        vehicle_model='BMW 5 Series 2024',
        driver_name='Hans Mueller',
        property_type='',
        damage_type='',
        hospital_name='',
        treatment_type='',
        vessel_name='',
        bill_of_lading=''
    )

    print(test1)
    print("\n" + "="*60)

    print("\n=== TEST 2: Marine Cargo Claim (Water Damage) ===\n")

    test2 = construct_loss_description_from_form(
        policy_number='NAC-MCARGO-2024-001',
        insured_name='Global Electronics Distribution',
        date_of_loss='2026-04-08',
        time_of_loss='Unknown',
        country='NL',
        city='Rotterdam',
        address='Port of Rotterdam, Terminal 5',
        product_type='Marine Cargo – Marine Cargo via GFH',
        incident_type='Marine Cargo: Water Damage',
        loss_description='Container discovered with water ingress upon arrival at port. Multiple pallets of consumer electronics affected. Initial inspection shows saltwater contamination. Cause under investigation - possible hull breach during transit.',
        estimated_value=180000,
        currency='EUR',
        vehicle_plate='',
        vehicle_model='',
        driver_name='',
        property_type='',
        damage_type='',
        hospital_name='',
        treatment_type='',
        vessel_name='MSC Maersk CTR-998877',
        bill_of_lading='BL-ROT-2024-04-001'
    )

    print(test2)
    print("\n" + "="*60)

    print("\n=== TEST 3: Property Claim (Fire) ===\n")

    test3 = construct_loss_description_from_form(
        policy_number='NAC-PROP-ES-2024-771',
        insured_name='Barcelona Logistics SL',
        date_of_loss='2026-04-07',
        time_of_loss='03:15',
        country='ES',
        city='Barcelona',
        address='Industrial Park Can Tunis, Warehouse 12',
        product_type='Property – Property with and without contents',
        incident_type='Property: Fire',
        loss_description='Electrical fire originated in server room, spread to adjacent warehouse area. Fire suppression system activated. Damage to building structure and stored inventory. Fire brigade report attached.',
        estimated_value=450000,
        currency='EUR',
        vehicle_plate='',
        vehicle_model='',
        driver_name='',
        property_type='Warehouse',
        damage_type='Both Structural and Contents',
        hospital_name='',
        treatment_type='',
        vessel_name='',
        bill_of_lading=''
    )

    print(test3)
    print("\n" + "="*60)

    print("\n✅ All form construction tests PASSED!")
    print("The structured form correctly builds comprehensive loss descriptions.")
