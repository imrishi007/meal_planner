import pandas as pd
import random

random.seed(42)  # for reproducibility

def main():
    meals = []
    meal_id_counter = 1
    
    # Cuisine distribution as specified
    cuisine_plan = [
        ('North Indian', 40),
        ('South Indian', 28),
        ('Gujarati and Western Indian', 22),
        ('Maharashtrian and other regional Indian cuisines', 25),
        ('Indo-Chinese', 25),
        ('Simple Italian/Continental', 20),
        ('Pan-Indian staples and other practical hostel meals', 40),
    ]
    
    # North Indian dishes
    north_indian = [
        ('Roti + Dal Tadka + Seasonal Vegetables', 'breakfast;lunch', ['Roti', 'Dal Tadka', 'Seasonal Vegetables']),
        ('Roti + Chole Masala', 'lunch;dinner', ['Roti', 'Chole Masala']),
        ('Roti + Rajma Masala', 'lunch;dinner', ['Roti', 'Rajma Masala']),
        ('Roti + Aloo Gobi', 'lunch;dinner', ['Roti', 'Aloo Gobi']),
        ('Roti + Bhindi Masala', 'lunch;dinner', ['Roti', 'Bhindi Masala']),
        ('Roti + Mixed Vegetable Curry', 'lunch;dinner', ['Roti', 'Mixed Vegetable Curry']),
        ('Roti + Paneer Bhurji', 'breakfast;lunch;dinner', ['Roti', 'Paneer Bhurji']),
        ('Roti + Cabbage Sabzi', 'lunch;dinner', ['Roti', 'Cabbage Sabzi']),
        ('Rajma Rice + Salad', 'lunch;dinner', ['Rajma', 'Steamed Rice', 'Salad']),
        ('Chole Rice + Salad', 'lunch;dinner', ['Chole Masala', 'Steamed Rice', 'Salad']),
        ('Dal Tadka Rice + Salad', 'lunch;dinner', ['Dal Tadka', 'Steamed Rice', 'Salad']),
        ('Kadhi Rice + Salad', 'lunch;dinner', ['Gujarati Kadhi', 'Steamed Rice', 'Salad']),
        ('Vegetable Pulao + Raita', 'lunch;dinner', ['Vegetable Pulao', 'Raita']),
        ('Jeera Rice + Dal Fry', 'lunch;dinner', ['Jeera Rice', 'Dal Fry']),
        ('Poori + Aloo Bhaji', 'breakfast', ['Poori', 'Aloo Bhaji']),
        ('Aloo Paratha + Curd', 'breakfast', ['Aloo Paratha', 'Curd']),
        ('Paneer Paratha + Curd', 'breakfast', ['Paneer Paratha', 'Curd']),
        ('Plain Paratha + Curd + Pickle', 'breakfast;lunch', ['Plain Paratha', 'Curd', 'Pickle']),
        ('Dal Makhani + Roti + Salad', 'lunch;dinner', ['Dal Makhani', 'Roti', 'Salad']),
        ('Kala Chana + Roti + Salad', 'lunch;dinner', ['Kala Chana Masala', 'Roti', 'Salad']),
    ]
    # Extend north indian
    while len(north_indian) < 50:  # buffer
        pass
    
    # Build systematically
    # Let's create all 200 properly
    
if __name__ == '__main__':
    main()
