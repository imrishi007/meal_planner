#!/usr/bin/env python3
import csv
import random
from datetime import datetime

random.seed(12345)

# Define all 200 meals
meals_data = []

# Cuisine plan
cuisine_targets = {
    'North Indian': 40,
    'South Indian': 28,
    'Gujarati and Western Indian': 22,
    'Maharashtrian and other regional Indian cuisines': 25,
    'Indo-Chinese': 25,
    'Simple Italian/Continental': 20,
    'Pan-Indian staples and other practical hostel meals': 40
}

# Allergen mapping
allergen_map = {
    'milk': ['curd', 'paneer', 'cheese', 'raita', 'butter'],
    'wheat/gluten': ['roti', 'paratha', 'poori', 'thepla', 'pasta', 'noodles', 'bread', 'pav'],
    'soy': ['soy chunks', 'tofu'],
    'peanuts': [],
}

def get_allergens(components):
    allergens = set()
    comp_lower = ' '.join(components).lower()
    if any(x in comp_lower for x in ['curd', 'paneer', 'cheese', 'raita', 'butter', 'milk']):
        allergens.add('milk')
    if any(x in comp_lower for x in ['roti', 'paratha', 'poori', 'thepla', 'pasta', 'noodles', 'bread', 'pav', 'macaroni']):
        allergens.add('wheat/gluten')
    if any(x in comp_lower for x in ['soy chunks', 'tofu', 'soya']):
        allergens.add('soy')
    if not allergens:
        return 'none'
    return ';'.join(sorted(list(allergens)))

meal_id = 1

# NORTH INDIAN (40)
north_indian_meals = [
    # Breakfast/Lunch/Dinner
    ("Roti + Dal Tadka + Aloo Gobi", "breakfast", ["Roti", "Dal Tadka", "Aloo Gobi"], "breakfast;lunch;dinner", 22, 420, 18, 52, 14, 4.2),
    ("Roti + Chole Masala + Salad", "lunch", ["Roti", "Chole Masala", "Salad"], "lunch;dinner", 28, 485, 24, 58, 16, 4.3),
    ("Roti + Rajma Masala + Salad", "lunch", ["Roti", "Rajma Masala", "Salad"], "lunch;dinner", 28, 495, 26, 57, 16, 4.4),
    ("Roti + Bhindi Masala + Salad", "lunch", ["Roti", "Bhindi Masala", "Salad"], "lunch;dinner", 22, 385, 14, 48, 14, 4.1),
    ("Roti + Mixed Veg Curry + Salad", "lunch", ["Roti", "Mixed Vegetable Curry", "Salad"], "lunch;dinner", 20, 375, 13, 47, 13, 4.0),
    ("Roti + Paneer Bhurji + Salad", "breakfast", ["Roti", "Paneer Bhurji", "Salad"], "breakfast;lunch;dinner", 35, 465, 24, 36, 26, 4.5),
    ("Roti + Cabbage Sabzi + Salad", "lunch", ["Roti", "Cabbage Sabzi", "Salad"], "lunch;dinner", 18, 335, 10, 45, 11, 3.9),
    ("Roti + Dal Fry + Bhindi Sabzi", "lunch", ["Roti", "Dal Fry", "Bhindi Sabzi"], "lunch;dinner", 24, 445, 20, 54, 15, 4.2),
    ("Rajma Rice + Salad", "lunch", ["Rajma", "Steamed Rice", "Salad"], "lunch;dinner", 26, 520, 28, 68, 16, 4.5),
    ("Chole Rice + Salad", "lunch", ["Chole Masala", "Steamed Rice", "Salad"], "lunch;dinner", 26, 510, 26, 66, 16, 4.4),
    ("Dal Tadka Rice + Salad", "lunch", ["Dal Tadka", "Steamed Rice", "Salad"], "lunch;dinner", 22, 475, 22, 65, 13, 4.2),
    ("Dal Fry Rice + Aloo Sabzi", "lunch", ["Dal Fry", "Steamed Rice", "Aloo Sabzi"], "lunch;dinner", 24, 495, 21, 67, 15, 4.1),
    ("Kadhi Rice + Salad", "lunch", ["Gujarati Kadhi", "Steamed Rice", "Salad"], "lunch;dinner", 20, 425, 16, 58, 14, 4.0),
    ("Veg Pulao + Raita", "lunch", ["Vegetable Pulao", "Raita"], "lunch;dinner", 28, 485, 16, 62, 19, 4.2),
    ("Jeera Rice + Dal Tadka + Aloo Gobi", "lunch", ["Jeera Rice", "Dal Tadka", "Aloo Gobi"], "lunch;dinner", 26, 510, 23, 65, 17, 4.3),
    ("Poori + Aloo Bhaji", "breakfast", ["Poori", "Aloo Bhaji"], "breakfast", 24, 465, 10, 55, 23, 4.1),
    ("Aloo Paratha + Curd", "breakfast", ["Aloo Paratha", "Curd"], "breakfast", 28, 425, 14, 48, 19, 4.3),
    ("Paneer Paratha + Curd", "breakfast", ["Paneer Paratha", "Curd"], "breakfast", 38, 495, 24, 44, 28, 4.6),
    ("Plain Paratha + Curd + Pickle", "breakfast", ["Plain Paratha", "Curd", "Pickle"], "breakfast;lunch", 24, 375, 12, 42, 17, 4.0),
    ("Methi Paratha + Curd", "breakfast", ["Methi Paratha", "Curd"], "breakfast", 26, 385, 13, 44, 17, 4.2),
    ("Dal Makhani + Roti + Salad", "dinner", ["Dal Makhani", "Roti", "Salad"], "lunch;dinner", 38, 545, 25, 56, 28, 4.6),
    ("Kala Chana Masala + Roti + Salad", "lunch", ["Kala Chana Masala", "Roti", "Salad"], "lunch;dinner", 26, 475, 28, 52, 16, 4.3),
    ("Lobia Masala + Roti + Salad", "lunch", ["Lobia Masala", "Roti", "Salad"], "lunch;dinner", 24, 455, 26, 50, 15, 4.2),
    ("Aloo Matar + Roti + Salad", "lunch", ["Aloo Matar", "Roti", "Salad"], "lunch;dinner", 22, 425, 16, 54, 15, 4.1),
    ("Baingan Bharta + Roti + Salad", "dinner", ["Baingan Bharta", "Roti", "Salad"], "lunch;dinner", 20, 365, 12, 46, 13, 4.0),
    ("Gobi Aloo + Roti + Salad", "lunch", ["Gobi Aloo", "Roti", "Salad"], "lunch;dinner", 22, 395, 14, 50, 14, 4.1),
    ("Tinda Masala + Roti + Salad", "lunch", ["Tinda Masala", "Roti", "Salad"], "lunch;dinner", 20, 355, 12, 46, 12, 4.0),
    ("Roti + Dal Tadka + Cabbage Sabzi", "lunch", ["Roti", "Dal Tadka", "Cabbage Sabzi"], "lunch;dinner", 22, 415, 19, 51, 13, 4.1),
    ("Roti + Rajma + Mixed Veg", "dinner", ["Roti", "Rajma Masala", "Mixed Vegetable Curry"], "lunch;dinner", 30, 525, 28, 59, 19, 4.4),
    ("Veg Biryani + Raita", "dinner", ["Vegetable Biryani", "Raita"], "lunch;dinner", 32, 545, 16, 72, 19, 4.3),
    ("Jeera Rice + Rajma + Salad", "lunch", ["Jeera Rice", "Rajma Masala", "Salad"], "lunch;dinner", 28, 535, 28, 67, 18, 4.4),
    ("Dal Makhani + Jeera Rice", "dinner", ["Dal Makhani", "Jeera Rice"], "lunch;dinner", 36, 555, 24, 66, 25, 4.6),
    ("Chole + Poori", "breakfast", ["Chole Masala", "Poori"], "breakfast;lunch", 28, 485, 19, 56, 22, 4.2),
    ("Aloo Gobi + Paratha + Curd", "breakfast", ["Aloo Gobi", "Paratha", "Curd"], "breakfast;lunch", 28, 445, 16, 52, 19, 4.2),
    ("Mix Veg Paratha + Curd", "breakfast", ["Mix Veg Paratha", "Curd"], "breakfast", 28, 415, 16, 48, 18, 4.3),
    ("Palak Dal + Roti + Salad", "lunch", ["Palak Dal", "Roti", "Salad"], "lunch;dinner", 22, 415, 24, 48, 12, 4.2),
    ("Arhar Dal + Rice + Aloo Sabzi", "lunch", ["Arhar Dal", "Steamed Rice", "Aloo Sabzi"], "lunch;dinner", 24, 495, 23, 65, 14, 4.2),
    ("Roti + Masoor Dal + Cauliflower Sabzi", "dinner", ["Roti", "Masoor Dal", "Cauliflower Sabzi"], "lunch;dinner", 22, 415, 22, 49, 13, 4.1),
    ("Kadai Paneer + Roti + Salad", "dinner", ["Kadai Paneer", "Roti", "Salad"], "lunch;dinner", 42, 535, 26, 42, 32, 4.7),
    ("Paneer Butter Masala + Roti", "dinner", ["Paneer Butter Masala", "Roti"], "lunch;dinner", 45, 565, 25, 41, 38, 4.8),
]

for name, mtype, comps, smtypes, cost, cal, prot, carb, fat, rat in north_indian_meals:
    if meal_id > 40: break
    allergens = get_allergens(comps)
    meals_data.append({
        'meal_id': f'M{meal_id:03d}',
        'meal_name': name,
        'primary_cuisine': 'North Indian',
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
        'prep_time_minutes': random.randint(15, 40),
        'kitchen_load': random.choice(['medium', 'high']),
        'allergens': allergens,
        'data_source': 'recipe_estimated_from_IFCT_USDA',
        'data_quality': 'recipe_estimated'
    })
    meal_id += 1

# Continue with other cuisines...
# For brevity, I'll generate the rest systematically
# SOUTH INDIAN (28)
south_indian = [
    ("Idli Sambar + Chutney", "breakfast", ["Idli", "Sambar", "Coconut Chutney"], "breakfast", 16, 325, 16, 42, 9, 4.4),
    ("Masala Dosa + Sambar + Chutney", "breakfast", ["Masala Dosa", "Sambar", "Coconut Chutney"], "breakfast", 24, 425, 14, 52, 17, 4.6),
    ("Plain Dosa + Sambar + Chutney", "breakfast", ["Plain Dosa", "Sambar", "Coconut Chutney"], "breakfast", 20, 375, 13, 48, 14, 4.4),
    ("Uttapam + Sambar + Chutney", "breakfast", ["Vegetable Uttapam", "Sambar", "Coconut Chutney"], "breakfast", 22, 385, 15, 48, 14, 4.4),
    ("Rava Upma + Chutney", "breakfast", ["Rava Upma", "Coconut Chutney"], "breakfast", 18, 375, 10, 48, 16, 4.0),
    ("Vegetable Upma + Chutney", "breakfast", ["Vegetable Upma", "Coconut Chutney"], "breakfast", 16, 345, 10, 44, 14, 4.0),
    ("Pongal + Sambar + Chutney", "breakfast", ["Ven Pongal", "Sambar", "Coconut Chutney"], "breakfast", 22, 425, 14, 52, 18, 4.3),
    ("Lemon Rice + Sambar", "lunch", ["Lemon Rice", "Sambar"], "breakfast;lunch", 18, 385, 12, 54, 14, 4.1),
    ("Tomato Rice + Curd", "lunch", ["Tomato Rice", "Curd"], "breakfast;lunch", 18, 375, 12, 50, 14, 4.1),
    ("Tamarind Rice + Sambar", "lunch", ["Tamarind Rice", "Sambar"], "lunch;dinner", 18, 385, 13, 52, 14, 4.1),
    ("Curd Rice + Pickle", "breakfast", ["Curd Rice", "Pickle"], "breakfast;lunch", 16, 325, 10, 38, 14, 4.0),
    ("Sambar Rice + Curd", "lunch", ["Sambar Rice", "Curd"], "lunch;dinner", 20, 425, 18, 56, 14, 4.2),
    ("Rava Dosa + Sambar + Chutney", "breakfast", ["Rava Dosa", "Sambar", "Coconut Chutney"], "breakfast", 22, 395, 12, 48, 16, 4.4),
    ("Onion Uttapam + Sambar + Chutney", "breakfast", ["Onion Uttapam", "Sambar", "Coconut Chutney"], "breakfast", 24, 405, 14, 50, 16, 4.5),
    ("Idli + Vada + Sambar + Chutney", "breakfast", ["Idli", "Medu Vada", "Sambar", "Coconut Chutney"], "breakfast", 28, 485, 18, 56, 22, 4.7),
    ("Set Dosa + Sambar + Chutney", "breakfast", ["Set Dosa", "Sambar", "Coconut Chutney"], "breakfast", 22, 395, 13, 50, 15, 4.5),
    ("Rice + Sambar + Cabbage Poriyal", "lunch", ["Steamed Rice", "Sambar", "Cabbage Poriyal"], "lunch;dinner", 22, 445, 19, 58, 14, 4.2),
    ("Rice + Rasam + Poriyal + Curd", "lunch", ["Steamed Rice", "Rasam", "Beans Poriyal", "Curd"], "lunch;dinner", 24, 435, 18, 54, 16, 4.2),
    ("Rice + Dal Sambar + Avial", "lunch", ["Steamed Rice", "Sambar", "Avial"], "lunch;dinner", 26, 475, 20, 60, 17, 4.4),
    ("Mysore Masala Dosa + Sambar + Chutney", "breakfast", ["Mysore Masala Dosa", "Sambar", "Coconut Chutney"], "breakfast", 28, 455, 15, 54, 19, 4.7),
    ("Rava Kesari + Upma Combo", "breakfast", ["Rava Upma", "Rava Kesari"], "breakfast", 24, 485, 10, 68, 19, 4.2),
    ("Bisibele Bath + Raita", "lunch", ["Bisibele Bath", "Raita"], "lunch;dinner", 28, 515, 18, 66, 19, 4.4),
    ("Tomato Bath + Curd", "breakfast", ["Tomato Bath", "Curd"], "breakfast;lunch", 20, 395, 12, 54, 14, 4.1),
    ("Puliyogare + Curd", "lunch", ["Puliyogare", "Curd"], "breakfast;lunch", 20, 415, 12, 58, 15, 4.2),
    ("Adai + Sambar + Chutney", "breakfast", ["Adai Dosa", "Sambar", "Coconut Chutney"], "breakfast", 24, 435, 22, 48, 16, 4.4),
    ("Rice + Mor Kuzhambu + Poriyal", "lunch", ["Steamed Rice", "Mor Kuzhambu", "Cabbage Poriyal"], "lunch;dinner", 24, 455, 18, 56, 18, 4.3),
    ("Vegetable Sambar + Idli Combo", "breakfast", ["Idli", "Vegetable Sambar", "Chutney"], "breakfast", 18, 345, 16, 44, 10, 4.3),
    ("Upma + Kesari Combo", "breakfast", ["Vegetable Upma", "Kesari"], "breakfast", 22, 455, 10, 64, 18, 4.1),
]

for name, mtype, comps, smtypes, cost, cal, prot, carb, fat, rat in south_indian:
    if meal_id > 40 + 28: break
    allergens = get_allergens(comps)
    prep_time = random.randint(10, 30)
    kitchen_load = random.choice(['low', 'medium'])
    meals_data.append({
        'meal_id': f'M{meal_id:03d}',
        'meal_name': name,
        'primary_cuisine': 'South Indian',
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
        'prep_time_minutes': prep_time,
        'kitchen_load': kitchen_load,
        'allergens': allergens,
        'data_source': 'recipe_estimated_from_IFCT_USDA',
        'data_quality': 'recipe_estimated'
    })
    meal_id += 1

# Write to CSV
fieldnames = ['meal_id', 'meal_name', 'primary_cuisine', 'secondary_cuisine_tags', 
              'meal_type', 'suitable_meal_types', 'meal_components', 'is_veg',
              'cost_per_serving_inr', 'calories_kcal', 'protein_g', 'carbs_g', 'fat_g',
              'student_rating', 'rating_source', 'rating_count', 'prep_time_minutes',
              'kitchen_load', 'allergens', 'data_source', 'data_quality']

with open('hostel_meal_dataset.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for meal in meals_data:
        writer.writerow(meal)

print(f'Generated {len(meals_data)} meals so far')
print(f'Meal IDs from {meals_data[0]["meal_id"]} to {meals_data[-1]["meal_id"]}')
