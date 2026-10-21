#!/usr/bin/env python3
import csv
import random

random.seed(12345)

meals_data = []
meal_id = 69  # Continue from where we left off

def get_allergens(components):
    allergens = set()
    comp_lower = ' '.join(components).lower()
    if any(x in comp_lower for x in ['curd', 'paneer', 'cheese', 'raita', 'butter', 'milk', 'malai']):
        allergens.add('milk')
    if any(x in comp_lower for x in ['roti', 'paratha', 'poori', 'thepla', 'pasta', 'noodles', 'bread', 'pav', 'macaroni', 'dosa', 'idli', 'upma', 'vada']):
        allergens.add('wheat/gluten')
    if any(x in comp_lower for x in ['soy chunks', 'tofu', 'soya']):
        allergens.add('soy')
    if not allergens:
        return 'none'
    return ';'.join(sorted(list(allergens)))

# GUJARATI AND WESTERN INDIAN (22) - starting at 69
gujarati = [
    ("Thepla + Curd + Pickle", "breakfast", ["Thepla", "Curd", "Pickle"], "breakfast", 22, 375, 14, 48, 14, 4.2),
    ("Thepla + Chunda + Curd", "breakfast", ["Thepla", "Chunda", "Curd"], "breakfast", 24, 395, 14, 52, 14, 4.3),
    ("Dhokla + Chutney", "breakfast", ["Dhokla", "Green Chutney"], "breakfast", 18, 285, 12, 42, 8, 4.2),
    ("Handvo + Chutney", "breakfast", ["Handvo", "Green Chutney"], "breakfast", 26, 425, 16, 52, 18, 4.4),
    ("Gujarati Kadhi + Rice", "lunch", ["Gujarati Kadhi", "Steamed Rice"], "lunch;dinner", 20, 375, 12, 48, 14, 4.0),
    ("Sev Tameta + Roti", "lunch", ["Sev Tameta", "Roti"], "lunch;dinner", 26, 435, 14, 52, 19, 4.2),
    ("Dal Dhokli + Salad", "lunch", ["Dal Dhokli", "Salad"], "lunch;dinner", 26, 455, 20, 58, 15, 4.3),
    ("Khichdi + Kadhi + Pickle", "lunch", ["Khichdi", "Gujarati Kadhi", "Pickle"], "lunch;dinner", 24, 425, 16, 56, 14, 4.2),
    ("Bajra Rotla + Ringna No Olo + Buttermilk", "lunch", ["Bajra Rotla", "Ringna No Olo", "Buttermilk"], "lunch;dinner", 28, 445, 18, 56, 16, 4.3),
    ("Undhiyu + Puri", "dinner", ["Undhiyu", "Puri"], "dinner", 38, 545, 16, 64, 28, 4.6),
    ("Roti + Shaak + Dal + Rice", "lunch", ["Roti", "Gujarati Shaak", "Dal", "Steamed Rice"], "lunch;dinner", 28, 495, 22, 64, 16, 4.3),
    ("Khandvi + Chutney", "breakfast", ["Khandvi", "Green Chutney"], "breakfast", 22, 325, 14, 36, 14, 4.3),
    ("Muthiya + Kadhi", "lunch", ["Muthiya", "Gujarati Kadhi"], "lunch;dinner", 24, 385, 16, 48, 14, 4.2),
    ("Rotla + Dal + Shaak", "dinner", ["Bajra Rotla", "Dal", "Gujarati Shaak"], "dinner", 26, 425, 20, 52, 14, 4.2),
    ("Farsan Platter + Kadhi", "snack", ["Farsan", "Gujarati Kadhi"], "lunch", 28, 445, 16, 56, 18, 4.1),
    ("Bhakhri + Shaak + Curd", "breakfast", ["Bhakhri", "Aloo Shaak", "Curd"], "breakfast;lunch", 26, 425, 14, 52, 18, 4.2),
    ("Tava Thepla + Potato Shaak", "breakfast", ["Thepla", "Aloo Shaak"], "breakfast;lunch", 24, 395, 12, 52, 16, 4.2),
    ("Khichdi + Kadhi + Ghee", "dinner", ["Khichdi", "Gujarati Kadhi"], "lunch;dinner", 22, 425, 14, 58, 16, 4.1),
    ("Dal Rice + Shaak + Salad", "lunch", ["Dal", "Steamed Rice", "Gujarati Shaak", "Salad"], "lunch;dinner", 24, 465, 22, 60, 14, 4.2),
    ("Mag Ni Dal + Rice", "lunch", ["Mag Ni Dal", "Steamed Rice"], "lunch;dinner", 22, 445, 24, 58, 12, 4.2),
    ("Roti + Ringna Bateta + Dal", "dinner", ["Roti", "Ringna Bateta", "Dal"], "lunch;dinner", 26, 455, 20, 56, 16, 4.3),
    ("Sev Khamani + Chutney", "breakfast", ["Sev Khamani", "Green Chutney"], "breakfast", 24, 415, 16, 50, 17, 4.3),
]

for name, mtype, comps, smtypes, cost, cal, prot, carb, fat, rat in gujarati:
    if meal_id > 68 + 22: break
    allergens = get_allergens(comps)
    meals_data.append({
        'meal_id': f'M{meal_id:03d}',
        'meal_name': name,
        'primary_cuisine': 'Gujarati and Western Indian',
        'secondary_cuisine_tags': '',
        'meal_type': 'lunch' if mtype == 'snack' else mtype,
        'suitable_meal_types': smtypes if smtypes != 'snack' else 'lunch',
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
        'prep_time_minutes': random.randint(15, 35),
        'kitchen_load': random.choice(['low', 'medium']),
        'allergens': allergens,
        'data_source': 'recipe_estimated_from_IFCT_USDA',
        'data_quality': 'recipe_estimated'
    })
    meal_id += 1

# MAHARASHTRIAN AND OTHER REGIONAL (25)
maharashtrian = [
    ("Poha + Jalebi", "breakfast", ["Poha", "Jalebi"], "breakfast", 20, 415, 8, 62, 16, 4.2),
    ("Poha + Chutney + Tea", "breakfast", ["Poha", "Green Chutney"], "breakfast", 16, 325, 8, 48, 12, 4.0),
    ("Misal Pav", "breakfast", ["Misal", "Pav"], "breakfast;lunch", 28, 485, 24, 52, 22, 4.6),
    ("Pav Bhaji", "lunch", ["Pav Bhaji", "Pav"], "breakfast;lunch;dinner", 26, 465, 14, 58, 21, 4.5),
    ("Usal Pav", "breakfast", ["Usal", "Pav"], "breakfast;lunch", 24, 425, 22, 48, 16, 4.4),
    ("Vada Pav", "breakfast", ["Vada Pav"], "breakfast;lunch", 22, 415, 12, 52, 19, 4.4),
    ("Sabudana Khichdi", "breakfast", ["Sabudana Khichdi"], "breakfast", 24, 425, 4, 62, 19, 4.2),
    ("Thalipeeth + Curd + Butter", "breakfast", ["Thalipeeth", "Curd"], "breakfast;lunch", 28, 425, 16, 48, 19, 4.4),
    ("Pithla Bhakri + Thecha", "lunch", ["Pithla", "Bhakri", "Thecha"], "lunch;dinner", 24, 425, 22, 46, 18, 4.4),
    ("Zunka Bhakri", "lunch", ["Zunka", "Bhakri"], "lunch;dinner", 22, 385, 20, 42, 16, 4.3),
    ("Varan Bhat + Aloo Bhaaji", "lunch", ["Varan", "Steamed Rice", "Aloo Bhaaji"], "lunch;dinner", 22, 455, 20, 62, 14, 4.2),
    ("Masale Bhat + Raita", "lunch", ["Masale Bhat", "Raita"], "lunch;dinner", 26, 485, 16, 64, 18, 4.3),
    ("Batata Vada + Chutney", "breakfast", ["Batata Vada", "Green Chutney"], "breakfast;lunch", 20, 385, 8, 48, 18, 4.3),
    ("Kanda Poha + Chutney", "breakfast", ["Kanda Poha", "Green Chutney"], "breakfast", 16, 335, 8, 48, 12, 4.1),
    ("Sheera", "breakfast", ["Sheera"], "breakfast", 18, 385, 6, 52, 17, 4.0),
    ("Aloo Wadi + Kadhi", "lunch", ["Aloo Wadi", "Kadhi"], "lunch;dinner", 26, 445, 16, 52, 20, 4.3),
    ("Matki Usal + Rice", "lunch", ["Matki Usal", "Steamed Rice"], "lunch;dinner", 24, 455, 26, 52, 14, 4.3),
    ("Rassa Bhaji + Bhakri", "dinner", ["Rassa Bhaji", "Bhakri"], "dinner", 26, 445, 18, 52, 18, 4.3),
    ("Kothimbir Vadi + Chutney", "snack", ["Kothimbir Vadi", "Green Chutney"], "breakfast;lunch", 22, 395, 14, 48, 17, 4.2),
    ("Dalimbi Usal + Pav", "breakfast", ["Dalimbi Usal", "Pav"], "breakfast;lunch", 26, 445, 24, 48, 16, 4.4),
    ("Bhel Puri Style Mix", "snack", ["Puffed Rice Mix"], "breakfast;lunch", 14, 245, 6, 38, 8, 3.9),
    ("Patodi Rassa", "dinner", ["Patodi Rassa", "Roti"], "dinner", 28, 465, 18, 52, 22, 4.4),
    ("Shengdana Chutney + Bhakri + Thecha", "lunch", ["Bhakri", "Shengdana Chutney"], "lunch;dinner", 22, 445, 18, 48, 24, 4.3),
    ("Amti Bhat", "lunch", ["Amti", "Steamed Rice"], "lunch;dinner", 22, 445, 22, 56, 14, 4.2),
    ("Kolhapuri Veg + Bhakri", "dinner", ["Kolhapuri Veg", "Bhakri"], "dinner", 28, 475, 18, 54, 22, 4.4),
]

for name, mtype, comps, smtypes, cost, cal, prot, carb, fat, rat in maharashtrian:
    if meal_id > 68 + 22 + 25: break
    allergens = get_allergens(comps)
    meals_data.append({
        'meal_id': f'M{meal_id:03d}',
        'meal_name': name,
        'primary_cuisine': 'Maharashtrian and other regional Indian cuisines',
        'secondary_cuisine_tags': '',
        'meal_type': 'lunch' if mtype == 'snack' else mtype,
        'suitable_meal_types': smtypes if smtypes != 'snack' else 'breakfast;lunch',
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
        'prep_time_minutes': random.randint(10, 30),
        'kitchen_load': random.choice(['low', 'medium']),
        'allergens': allergens,
        'data_source': 'recipe_estimated_from_IFCT_USDA',
        'data_quality': 'recipe_estimated'
    })
    meal_id += 1

# INDO-CHINESE (25)
indo_chinese = [
    ("Vegetable Hakka Noodles", "dinner", ["Vegetable Hakka Noodles"], "lunch;dinner", 28, 425, 12, 58, 16, 4.2),
    ("Vegetable Fried Rice", "dinner", ["Vegetable Fried Rice"], "lunch;dinner", 26, 415, 12, 56, 15, 4.2),
    ("Schezwan Fried Rice", "dinner", ["Schezwan Vegetable Fried Rice"], "lunch;dinner", 28, 435, 12, 58, 17, 4.3),
    ("Vegetable Chow Mein", "dinner", ["Vegetable Chow Mein"], "lunch;dinner", 28, 425, 12, 56, 17, 4.2),
    ("Gobi Manchurian with Fried Rice", "dinner", ["Gobi Manchurian", "Vegetable Fried Rice"], "lunch;dinner", 36, 485, 14, 62, 22, 4.4),
    ("Veg Manchurian with Fried Rice", "dinner", ["Vegetable Manchurian", "Vegetable Fried Rice"], "lunch;dinner", 36, 485, 16, 60, 22, 4.4),
    ("Chilli Paneer with Fried Rice", "dinner", ["Chilli Paneer", "Vegetable Fried Rice"], "lunch;dinner", 42, 525, 22, 56, 28, 4.6),
    ("Chilli Potato with Noodles", "dinner", ["Chilli Potato", "Vegetable Hakka Noodles"], "lunch;dinner", 32, 455, 10, 62, 19, 4.3),
    ("Schezwan Noodles", "dinner", ["Schezwan Vegetable Noodles"], "lunch;dinner", 28, 435, 12, 58, 17, 4.3),
    ("Veg Spring Roll Meal", "snack", ["Vegetable Spring Rolls"], "breakfast;lunch", 28, 395, 10, 48, 19, 4.2),
    ("Honey Chilli Potato", "snack", ["Honey Chilli Potato"], "lunch;dinner", 26, 425, 6, 58, 20, 4.3),
    ("Mushroom Fried Rice", "dinner", ["Mushroom Fried Rice"], "lunch;dinner", 28, 425, 14, 54, 16, 4.3),
    ("Veg American Chopsuey", "dinner", ["Vegetable American Chopsuey"], "lunch;dinner", 32, 445, 12, 58, 19, 4.3),
    ("Paneer Fried Rice", "dinner", ["Paneer Fried Rice"], "lunch;dinner", 34, 465, 18, 54, 21, 4.4),
    ("Chilli Gobi with Noodles", "dinner", ["Chilli Gobi", "Vegetable Hakka Noodles"], "lunch;dinner", 32, 455, 12, 60, 19, 4.3),
    ("Veg Manchurian Dry with Noodles", "dinner", ["Vegetable Manchurian", "Vegetable Hakka Noodles"], "lunch;dinner", 34, 465, 14, 60, 20, 4.4),
    ("Schezwan Paneer Fried Rice", "dinner", ["Schezwan Paneer Fried Rice"], "lunch;dinner", 38, 495, 20, 56, 25, 4.5),
    ("Babycorn Manchurian with Rice", "dinner", ["Babycorn Manchurian", "Vegetable Fried Rice"], "lunch;dinner", 36, 485, 14, 62, 22, 4.4),
    ("Veg Triple Schezwan Fried Rice", "dinner", ["Triple Schezwan Fried Rice"], "lunch;dinner", 34, 475, 14, 62, 20, 4.4),
    ("Crispy Veg with Noodles", "dinner", ["Crispy Vegetables", "Vegetable Hakka Noodles"], "lunch;dinner", 34, 465, 12, 60, 22, 4.3),
    ("Chilli Mushroom with Fried Rice", "dinner", ["Chilli Mushroom", "Vegetable Fried Rice"], "lunch;dinner", 36, 475, 16, 58, 22, 4.4),
    ("Schezwan Potato with Noodles", "dinner", ["Schezwan Potato", "Vegetable Hakka Noodles"], "lunch;dinner", 30, 445, 10, 60, 19, 4.3),
    ("Veg Burnt Garlic Noodles", "dinner", ["Burnt Garlic Vegetable Noodles"], "lunch;dinner", 28, 425, 12, 56, 17, 4.2),
    ("Manchurian Fried Rice Combo", "dinner", ["Vegetable Manchurian", "Schezwan Fried Rice"], "lunch;dinner", 38, 505, 16, 64, 23, 4.5),
    ("Chilli Paneer with Hakka Noodles", "dinner", ["Chilli Paneer", "Vegetable Hakka Noodles"], "lunch;dinner", 44, 545, 24, 56, 30, 4.7),
]

for name, mtype, comps, smtypes, cost, cal, prot, carb, fat, rat in indo_chinese:
    if meal_id > 68 + 22 + 25 + 25: break
    allergens = get_allergens(comps)
    meals_data.append({
        'meal_id': f'M{meal_id:03d}',
        'meal_name': name,
        'primary_cuisine': 'Indo-Chinese',
        'secondary_cuisine_tags': '',
        'meal_type': 'lunch' if mtype == 'snack' else mtype,
        'suitable_meal_types': smtypes if smtypes != 'snack' else 'lunch;dinner',
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
        'prep_time_minutes': random.randint(12, 25),
        'kitchen_load': random.choice(['medium', 'high']),
        'allergens': allergens,
        'data_source': 'recipe_estimated_from_IFCT_USDA',
        'data_quality': 'recipe_estimated'
    })
    meal_id += 1

# Write current progress
fieldnames = ['meal_id', 'meal_name', 'primary_cuisine', 'secondary_cuisine_tags', 
              'meal_type', 'suitable_meal_types', 'meal_components', 'is_veg',
              'cost_per_serving_inr', 'calories_kcal', 'protein_g', 'carbs_g', 'fat_g',
              'student_rating', 'rating_source', 'rating_count', 'prep_time_minutes',
              'kitchen_load', 'allergens', 'data_source', 'data_quality']

# Read existing and merge
try:
    with open('hostel_meal_dataset.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        existing = list(reader)
    all_meals = existing + meals_data
except:
    all_meals = meals_data

with open('hostel_meal_dataset.csv', 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for meal in all_meals:
        writer.writerow(meal)

print(f'Now have {len(all_meals)} meals total')
print(f'Added {len(meals_data)} meals, next meal_id would be {meal_id}')
