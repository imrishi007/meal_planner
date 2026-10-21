#!/usr/bin/env python3
import csv
import random

random.seed(12345)

meals_data = []
meal_id = 141

def get_allergens(components):
    allergens = set()
    comp_lower = ' '.join(components).lower()
    if any(x in comp_lower for x in ['curd', 'paneer', 'cheese', 'raita', 'butter', 'milk', 'malai', 'cream']):
        allergens.add('milk')
    if any(x in comp_lower for x in ['roti', 'paratha', 'poori', 'thepla', 'pasta', 'noodles', 'bread', 'pav', 'macaroni', 'dosa', 'idli', 'upma', 'vada']):
        allergens.add('wheat/gluten')
    if any(x in comp_lower for x in ['soy chunks', 'tofu', 'soya']):
        allergens.add('soy')
    if not allergens:
        return 'none'
    return ';'.join(sorted(list(allergens)))

# SIMPLE ITALIAN/CONTINENTAL (20)
italian = [
    ("Tomato Pasta with Vegetables", "dinner", ["Tomato Sauce Pasta", "Mixed Vegetables"], "lunch;dinner", 28, 425, 14, 58, 16, 4.1),
    ("White Sauce Pasta with Vegetables", "dinner", ["White Sauce Pasta", "Mixed Vegetables"], "lunch;dinner", 34, 485, 18, 54, 24, 4.3),
    ("Masala Macaroni", "dinner", ["Masala Macaroni", "Vegetables"], "lunch;dinner", 26, 415, 12, 58, 15, 4.2),
    ("Vegetable Macaroni in Tomato Sauce", "dinner", ["Vegetable Macaroni", "Tomato Sauce"], "lunch;dinner", 26, 405, 12, 56, 15, 4.1),
    ("Spicy Veg Pasta", "dinner", ["Spicy Vegetable Pasta"], "lunch;dinner", 28, 425, 14, 56, 17, 4.2),
    ("Cheese Pasta with Vegetables", "dinner", ["Cheese Pasta", "Mixed Vegetables"], "lunch;dinner", 38, 515, 22, 54, 28, 4.4),
    ("Veg Grilled Sandwich", "breakfast", ["Grilled Vegetable Sandwich"], "breakfast;lunch", 24, 375, 14, 44, 17, 4.2),
    ("Cheese and Tomato Sandwich", "breakfast", ["Cheese Tomato Sandwich"], "breakfast;lunch", 28, 415, 18, 42, 21, 4.3),
    ("Corn and Cheese Sandwich", "breakfast", ["Corn Cheese Sandwich"], "breakfast;lunch", 30, 425, 19, 42, 22, 4.3),
    ("Aloo Sandwich", "breakfast", ["Aloo Sandwich"], "breakfast;lunch", 22, 375, 10, 50, 16, 4.1),
    ("Veg Mayo Sandwich", "breakfast", ["Vegetable Mayo Sandwich"], "breakfast;lunch", 26, 415, 12, 48, 21, 4.2),
    ("Pasta Salad with Vegetables", "lunch", ["Vegetable Pasta Salad"], "breakfast;lunch", 28, 385, 14, 46, 18, 4.1),
    ("Red Sauce Penne with Veg", "dinner", ["Red Sauce Penne", "Mixed Vegetables"], "lunch;dinner", 30, 445, 16, 58, 18, 4.3),
    ("Mushroom Pasta", "dinner", ["Mushroom Pasta in White Sauce"], "lunch;dinner", 36, 495, 18, 54, 26, 4.4),
    ("Veg and Cheese Panini Style Sandwich", "lunch", ["Grilled Veg Cheese Sandwich"], "breakfast;lunch", 32, 455, 20, 44, 24, 4.4),
    ("Broccoli Pasta", "dinner", ["Broccoli Tomato Pasta"], "lunch;dinner", 30, 435, 18, 56, 18, 4.2),
    ("Mixed Veg Toast", "breakfast", ["Vegetable Toast"], "breakfast;lunch", 22, 345, 14, 38, 16, 4.1),
    ("Spinach and Corn Pasta", "dinner", ["Spinach Corn Pasta"], "lunch;dinner", 32, 465, 20, 52, 22, 4.3),
    ("Club Style Veg Sandwich", "breakfast", ["Club Vegetable Sandwich"], "breakfast;lunch", 28, 425, 16, 48, 20, 4.3),
    ("Arrabbiata Pasta with Veg", "dinner", ["Arrabbiata Vegetable Pasta"], "lunch;dinner", 28, 415, 14, 56, 16, 4.2),
]

for name, mtype, comps, smtypes, cost, cal, prot, carb, fat, rat in italian:
    if meal_id > 140 + 20: break
    allergens = get_allergens(comps)
    meals_data.append({
        'meal_id': f'M{meal_id:03d}',
        'meal_name': name,
        'primary_cuisine': 'Simple Italian/Continental',
        'secondary_cuisine_tags': '',
        'meal_type': mtype,
        'suitable_meal_types': smtypes,
        'meal_components': ';'.join(comps),
        'is_veg': 'true',
        'cost_per_serving_inr': cost,
        'calories_kcal': cal,
        'protein_g': prot,
        'carbs_g': carb,
        'fat_g': fat,
        'student_rating': rat,
        'rating_source': 'synthetic',
        'rating_count': 0,
        'prep_time_minutes': random.randint(10, 20),
        'kitchen_load': random.choice(['low', 'medium']),
        'allergens': allergens,
        'data_source': 'recipe_estimated_from_IFCT_USDA',
        'data_quality': 'recipe_estimated'
    })
    meal_id += 1

# PAN-INDIAN STAPLES (40)
pan_indian = [
    ("Dal Rice", "lunch", ["Dal", "Steamed Rice"], "lunch;dinner", 16, 425, 20, 58, 12, 4.0),
    ("Roti Sabzi", "lunch", ["Roti", "Seasonal Sabzi"], "lunch;dinner", 18, 335, 12, 44, 11, 4.0),
    ("Khichdi", "lunch", ["Khichdi"], "breakfast;lunch;dinner", 18, 375, 14, 52, 12, 4.1),
    ("Khichdi + Curd", "lunch", ["Khichdi", "Curd"], "breakfast;lunch;dinner", 20, 395, 16, 50, 15, 4.1),
    ("Dal Khichdi + Pickle", "dinner", ["Dal Khichdi", "Pickle"], "breakfast;lunch;dinner", 20, 415, 18, 54, 14, 4.2),
    ("Veg Pulao", "lunch", ["Vegetable Pulao"], "lunch;dinner", 24, 425, 12, 58, 16, 4.1),
    ("Chana Rice", "lunch", ["Chana Masala", "Steamed Rice"], "lunch;dinner", 24, 485, 26, 62, 14, 4.3),
    ("Soy Chunks Curry + Rice", "dinner", ["Soy Chunks Curry", "Steamed Rice"], "lunch;dinner", 28, 485, 38, 48, 18, 4.3),
    ("Soy Chunks Curry + Roti", "dinner", ["Soy Chunks Curry", "Roti"], "lunch;dinner", 26, 445, 36, 42, 16, 4.3),
    ("Moong Dal + Rice + Sabzi", "lunch", ["Moong Dal", "Steamed Rice", "Seasonal Sabzi"], "lunch;dinner", 24, 475, 26, 58, 14, 4.2),
    ("Roti + Dal + Sabzi", "dinner", ["Roti", "Dal", "Seasonal Sabzi"], "lunch;dinner", 22, 425, 20, 52, 14, 4.2),
    ("Sprouts Salad Meal", "breakfast", ["Mixed Sprouts", "Vegetables"], "breakfast;lunch", 18, 245, 20, 24, 10, 3.9),
    ("Moong Dal Cheela + Curd", "breakfast", ["Moong Dal Cheela", "Curd"], "breakfast", 22, 325, 22, 28, 12, 4.2),
    ("Besan Cheela + Curd", "breakfast", ["Besan Cheela", "Curd"], "breakfast", 22, 335, 18, 30, 16, 4.1),
    ("Mix Veg Cheela + Curd", "breakfast", ["Mix Veg Cheela", "Curd"], "breakfast", 24, 345, 18, 32, 16, 4.2),
    ("Oatmeal Upma", "breakfast", ["Oatmeal Vegetable Upma"], "breakfast", 18, 275, 12, 32, 12, 4.0),
    ("Dalia Khichdi", "breakfast", ["Dalia Khichdi"], "breakfast;lunch;dinner", 18, 325, 12, 48, 10, 4.1),
    ("Dalia + Curd", "breakfast", ["Dalia", "Curd"], "breakfast;lunch", 20, 345, 14, 44, 14, 4.1),
    ("Veg Khichdi + Kadhi", "dinner", ["Vegetable Khichdi", "Kadhi"], "lunch;dinner", 22, 425, 18, 52, 18, 4.2),
    ("Toor Dal + Rice + Pickle", "lunch", ["Toor Dal", "Steamed Rice", "Pickle"], "lunch;dinner", 20, 455, 22, 60, 12, 4.2),
    ("Urad Dal + Rice + Sabzi", "dinner", ["Urad Dal", "Steamed Rice", "Seasonal Sabzi"], "lunch;dinner", 24, 475, 24, 58, 14, 4.2),
    ("Roti + Moong Dal + Aloo Sabzi", "lunch", ["Roti", "Moong Dal", "Aloo Sabzi"], "lunch;dinner", 22, 425, 22, 50, 14, 4.2),
    ("Chana Dal + Rice + Bhindi Sabzi", "dinner", ["Chana Dal", "Steamed Rice", "Bhindi Sabzi"], "lunch;dinner", 24, 475, 26, 56, 15, 4.2),
    ("Sabzi + Paratha + Curd", "breakfast", ["Seasonal Sabzi", "Paratha", "Curd"], "breakfast;lunch", 26, 425, 16, 50, 18, 4.2),
    ("Green Moong Dal + Rice", "lunch", ["Green Moong Dal", "Steamed Rice"], "lunch;dinner", 22, 455, 26, 54, 12, 4.3),
    ("Matar Paneer + Roti", "dinner", ["Matar Paneer", "Roti"], "lunch;dinner", 36, 485, 26, 42, 26, 4.5),
    ("Mixed Dal + Rice", "lunch", ["Mixed Dal", "Steamed Rice"], "lunch;dinner", 22, 455, 24, 58, 14, 4.2),
    ("Rajma Chawal", "lunch", ["Rajma", "Steamed Rice"], "lunch;dinner", 24, 495, 28, 64, 15, 4.4),
    ("Kadi Chawal", "lunch", ["Kadhi", "Steamed Rice"], "lunch;dinner", 20, 415, 16, 56, 14, 4.1),
    ("Aloo Gobi + Roti + Dal", "dinner", ["Aloo Gobi", "Roti", "Dal"], "lunch;dinner", 24, 445, 20, 54, 15, 4.2),
    ("Soya Chunk Pulao", "lunch", ["Soya Chunk Vegetable Pulao"], "lunch;dinner", 28, 475, 28, 52, 18, 4.3),
    ("Mushroom Masala + Roti", "dinner", ["Mushroom Masala", "Roti"], "lunch;dinner", 28, 425, 16, 48, 20, 4.2),
    ("Capsicum Aloo + Roti + Curd", "lunch", ["Capsicum Aloo", "Roti", "Curd"], "lunch;dinner", 26, 425, 16, 50, 18, 4.2),
    ("Jeera Aloo + Poori", "breakfast", ["Jeera Aloo", "Poori"], "breakfast;lunch", 26, 455, 10, 56, 22, 4.1),
    ("Lauki Chana Dal", "dinner", ["Lauki Chana Dal"], "lunch;dinner", 22, 395, 22, 48, 12, 4.1),
    ("Pumpkin Sabzi + Roti + Dal", "dinner", ["Pumpkin Sabzi", "Roti", "Dal"], "lunch;dinner", 24, 425, 20, 52, 14, 4.2),
    ("Mix Veg + Dal + Roti + Rice", "lunch", ["Mixed Vegetable Curry", "Dal", "Roti", "Steamed Rice"], "lunch;dinner", 30, 545, 24, 70, 19, 4.3),
    ("Paneer Bhurji + Paratha + Curd", "breakfast", ["Paneer Bhurji", "Paratha", "Curd"], "breakfast;lunch;dinner", 40, 505, 26, 48, 29, 4.6),
    ("Sprouts Poha", "breakfast", ["Sprouts Poha"], "breakfast", 20, 335, 16, 42, 12, 4.1),
    ("Veggie Upma with Nuts", "breakfast", ["Vegetable Upma"], "breakfast", 20, 375, 12, 48, 16, 4.1),
]

for name, mtype, comps, smtypes, cost, cal, prot, carb, fat, rat in pan_indian:
    if meal_id > 160 + 40: break  # should reach 200
    allergens = get_allergens(comps)
    meals_data.append({
        'meal_id': f'M{meal_id:03d}',
        'meal_name': name,
        'primary_cuisine': 'Pan-Indian staples and other practical hostel meals',
        'secondary_cuisine_tags': '',
        'meal_type': mtype,
        'suitable_meal_types': smtypes,
        'meal_components': ';'.join(comps),
        'is_veg': 'true',
        'cost_per_serving_inr': cost,
        'calories_kcal': cal,
        'protein_g': prot,
        'carbs_g': carb,
        'fat_g': fat,
        'student_rating': rat,
        'rating_source': 'synthetic',
        'rating_count': 0,
        'prep_time_minutes': random.randint(10, 25),
        'kitchen_load': random.choice(['low', 'medium']),
        'allergens': allergens,
        'data_source': 'recipe_estimated_from_IFCT_USDA',
        'data_quality': 'recipe_estimated'
    })
    meal_id += 1

# Read existing and merge all
fieldnames = ['meal_id', 'meal_name', 'primary_cuisine', 'secondary_cuisine_tags', 
              'meal_type', 'suitable_meal_types', 'meal_components', 'is_veg',
              'cost_per_serving_inr', 'calories_kcal', 'protein_g', 'carbs_g', 'fat_g',
              'student_rating', 'rating_source', 'rating_count', 'prep_time_minutes',
              'kitchen_load', 'allergens', 'data_source', 'data_quality']

try:
    with open('hostel_meal_dataset.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing = list(reader)
    all_meals = existing + meals_data
except Exception as e:
    print(f'Error: {e}')
    all_meals = meals_data

# Ensure we have exactly 200
if len(all_meals) > 200:
    all_meals = all_meals[:200]

with open('hostel_meal_dataset.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for meal in all_meals:
        writer.writerow(meal)

print(f'Final: {len(all_meals)} meals total')
if all_meals:
    print(f'Meal IDs from {all_meals[0]["meal_id"]} to {all_meals[-1]["meal_id"]}')
