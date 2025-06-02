from datetime import datetime, timedelta

def is_tree_watered(last_watered):
    """
    Check if the tree is currently watered.
    
    Args:
        last_watered: The datetime when the tree was last watered
        
    Returns:
        bool: True if the tree is still watered, False otherwise
    """
    if not last_watered:
        return False
    
    # Calculate if 5 hours have passed since last watering
    watering_duration = timedelta(hours=5)
    now = datetime.now()
    
    return (now - last_watered) < watering_duration

def is_auto_water_active(auto_water_until):
    """
    Check if auto watering is active.
    
    Args:
        auto_water_until: The datetime until auto watering is active
        
    Returns:
        bool: True if auto watering is active, False otherwise
    """
    if not auto_water_until:
        return False
    
    now = datetime.now()
    
    return auto_water_until > now

def calculate_cf_income(tree, duration_hours):
    """
    Calculate CF income based on tree level and duration.
    
    Args:
        tree: The tree object with level and income_per_hour
        duration_hours: Duration in hours to calculate income for
        
    Returns:
        float: CF income amount
    """
    return tree.income_per_hour * duration_hours

def check_upgrade_requirements(tree):
    """
    Check if the tree meets requirements for an upgrade.
    
    Args:
        tree: The tree object with branches_collected and level
        
    Returns:
        bool: True if tree can be upgraded, False otherwise
    """
    level_requirements = {
        1: 5,   # 5 branches for level 2
        2: 12,  # 12 branches for level 3
        3: 30,  # 30 branches for level 4
        4: 75   # 75 branches for level 5
    }
    
    # Tree is already max level
    if tree.level >= 5:
        return False
        
    return tree.branches_collected >= level_requirements.get(tree.level, 0) 